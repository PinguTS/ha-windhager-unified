from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import WindhagerApiClient
from .const import (
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_LON_EXPERIENCE_MINIMUM,
    DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM,
    DEFAULT_REST_SENSOR_EXPERIENCE_MINIMUM,
    EXPERIENCE_TIERS,
)
from .exceptions import WindhagerAuthError, WindhagerError
from .labels import LabelCatalog
from .tier_lookup import GN_MN_OVERRIDES, uses_easy_lookup_discovery

_LOGGER = logging.getLogger(__name__)

_YAML_BASE = Path(__file__).parent


def _tier_index(slug: str) -> int:
    """Return the ordinal index of an experience-level slug (0=essential)."""
    try:
        return EXPERIENCE_TIERS.index(slug)
    except ValueError:
        return EXPERIENCE_TIERS.index(DEFAULT_EXPERIENCE_LEVEL)


def _passes_tier(
    experience_minimum: str,
    selected_tier: str,
    default_minimum: str,
) -> bool:
    """Return True when the datapoint/endpoint is visible at the selected tier."""
    minimum = experience_minimum or default_minimum
    return _tier_index(minimum) <= _tier_index(selected_tier)


def _normalize_lon_datapoint_value(value: Any) -> Any:
    """Map API placeholder strings to unknown so numeric HA sensors do not raise.

    GET datapoint documents ``value`` as string (RestApiRC7030_1.0_datapoint).
    Devices may return ``-`` or whitespace when no reading is available.
    """
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped == "-":
            return None
    return value


class WindhagerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Windhager data polling."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool,
        scan_interval: int,
        experience_level: str = DEFAULT_EXPERIENCE_LEVEL,
        groups: list[str] | None = None,
        discovered_datapoints: list[dict[str, Any]] | None = None,
        adhoc_oids: list[Any] | None = None,
    ) -> None:
        self.api_client = WindhagerApiClient(
            host=host,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        self.scan_interval = scan_interval
        self.experience_level = experience_level
        self.selected_groups: set[str] = set(groups) if groups else set()
        self.discovered_datapoints: list[dict[str, Any]] = list(discovered_datapoints or [])
        self.adhoc_entries: list[dict[str, str]] = self._coerce_adhoc_entries(adhoc_oids)
        self.label_catalog: LabelCatalog | None = None

        super().__init__(
            hass,
            logger=_LOGGER,
            name="Windhager",
            update_interval=timedelta(seconds=scan_interval),
        )

        all_datapoints: list[dict[str, Any]] = self._load_yaml(
            _YAML_BASE / "oids.yaml", "datapoints"
        )
        all_restapi: dict[str, list[dict[str, Any]]] = self._load_yaml(
            _YAML_BASE / "restapi_endpoints.yaml", "restapi_endpoints"
        )

        self.datapoints = self._build_lon_datapoints(all_datapoints)
        self.oid_disambiguators: dict[str, str] = self._compute_oid_disambiguators(
            self.datapoints
        )
        self.restapi_endpoints = self._filter_restapi(all_restapi)

        # OIDs that returned 404 (not present on this device) — tracked for diagnostics
        self.unknown_oids: set[str] = set()

        # Background export task — set by export.async_start_export()
        self.export_task: asyncio.Task[None] | None = None

        _LOGGER.debug(
            "Coordinator: tier=%s groups=%s → %d LON datapoints, %d RestAPI groups",
            experience_level,
            sorted(self.selected_groups) if self.selected_groups else "(all)",
            len(self.datapoints),
            len(self.restapi_endpoints),
        )

    # ------------------------------------------------------------------
    # Label catalogue
    # ------------------------------------------------------------------

    async def async_initialize_catalog(self) -> None:
        """Load bundled XML label files into memory (non-blocking)."""
        loop = asyncio.get_running_loop()
        self.label_catalog = await loop.run_in_executor(None, LabelCatalog.load)

    def get_label(self, oid: str, lang: str) -> str | None:
        """Return the VarIdent label for an OID's gn/mn in the requested language.

        Returns ``None`` when the catalog is not loaded, the OID is malformed,
        or no label exists for the (gn, mn, lang) combination.
        """
        if self.label_catalog is None:
            return None
        parts = oid.split("/")
        if len(parts) != 6:
            return None
        try:
            gn, mn = int(parts[3]), int(parts[4])
            return self.label_catalog.var_ident(gn, mn, lang)
        except (ValueError, IndexError):
            return None

    def has_enum_labels(self, oid: str) -> bool:
        """Return True if the catalog contains enum labels for this OID's (gn, mn)."""
        if self.label_catalog is None:
            return False
        parts = oid.split("/")
        if len(parts) != 6:
            return False
        try:
            gn, mn = int(parts[3]), int(parts[4])
            return self.label_catalog.has_enum_labels(gn, mn)
        except (ValueError, IndexError):
            return False

    def get_enum_label(self, oid: str, raw_value: Any, lang: str) -> str | None:
        """Return the human-readable enum label for a raw LON value.

        ``raw_value`` may be an integer or an integer-like string.  Returns
        ``None`` when the catalog is not loaded, the OID is malformed, the
        value is not integer-castable, or no enum entry exists.
        """
        if self.label_catalog is None:
            return None
        parts = oid.split("/")
        if len(parts) != 6:
            return None
        try:
            gn, mn = int(parts[3]), int(parts[4])
            eid = int(raw_value)
            return self.label_catalog.enum_label(gn, mn, eid, lang)
        except (ValueError, IndexError, TypeError):
            return None

    def get_enum_options(self, oid: str, lang: str) -> list[str]:
        """Return all enum option labels for an OID's (gn, mn) in the given language."""
        if self.label_catalog is None:
            return []
        parts = oid.split("/")
        if len(parts) != 6:
            return []
        try:
            gn, mn = int(parts[3]), int(parts[4])
            return self.label_catalog.enum_options(gn, mn, lang)
        except (ValueError, IndexError):
            return []

    def get_entity_name(
        self,
        oid: str,
        lang: str,
        i18n: dict[str, str],
        key: str,
    ) -> str:
        """Return a human-readable name for *oid*, including a node/function prefix
        when the same (gn, mn) measurement appears on more than one node or
        function block after filtering.

        Lookup chain: LabelCatalog → i18n[lang] → i18n["en"] → key.
        Prefix: "{function_name} {base}" — matching HA's own device+entity display
        pattern ("LogWIN Kesseltemperatur").  Falls back to a numeric suffix when
        the function name is unavailable.
        """
        base = self.get_label(oid, lang) or i18n.get(lang) or i18n.get("en") or key
        prefix = self.oid_disambiguators.get(oid)
        if not prefix:
            return base
        # Numeric fallback produces "Name (1)" / "Name (2)"; a real name uses
        # the HA-idiomatic "FunctionName Name" (space-separated prefix).
        if prefix.isdigit():
            return f"{base} ({prefix})"
        return f"{prefix} {base}"

    @staticmethod
    def _compute_oid_disambiguators(
        datapoints: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Return a mapping of OID → disambiguating label for shared (gn, mn) pairs.

        When two sensors report the same measurement type from different nodes
        (multi-boiler) or different function blocks on the same node (HC1/HC2),
        each OID receives a label so entity names stay unique.

        Label priority
        --------------
        1. ``function_name`` stored on the datapoint (e.g. "LogWIN", "Heizkreis 1").
        2. If function names are not unique among the group, a counter is appended
           ("Heizkreis 1" / "Heizkreis 2" are already unique; "Kessel" / "Kessel"
           would become "Kessel 1" / "Kessel 2").
        3. If no function name is available, a plain sequence number is used as a
           fallback so entity names are never silently duplicated.

        Sorting is by (node_id, fct_id) numerically for stable ordering.
        """
        from collections import defaultdict

        # Map each (gn, mn) to the full datapoint dicts that share it.
        by_gn_mn: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for dp in datapoints:
            oid = str(dp.get("oid", ""))
            parts = oid.split("/")
            if len(parts) == 6:
                by_gn_mn[(parts[3], parts[4])].append(dp)

        result: dict[str, str] = {}
        for dps in by_gn_mn.values():
            if len(dps) <= 1:
                continue

            try:
                sorted_dps = sorted(
                    dps,
                    key=lambda d: (
                        int(d["oid"].split("/")[1]),
                        int(d["oid"].split("/")[2]),
                    ),
                )
            except (ValueError, KeyError):
                sorted_dps = list(dps)

            names = [dp.get("function_name") or "" for dp in sorted_dps]

            if all(names):
                # All have function names — check for duplicates within the group.
                name_counts: dict[str, int] = defaultdict(int)
                for n in names:
                    name_counts[n] += 1

                # Second pass: assign unique labels.
                name_seen: dict[str, int] = defaultdict(int)
                for dp, name in zip(sorted_dps, names, strict=True):
                    if name_counts[name] > 1:
                        name_seen[name] += 1
                        result[dp["oid"]] = f"{name} {name_seen[name]}"
                    else:
                        result[dp["oid"]] = name
            else:
                # Fallback: plain sequence number.
                for i, dp in enumerate(sorted_dps):
                    result[dp["oid"]] = str(i + 1)

        return result

    # ------------------------------------------------------------------
    # Filtering helpers
    # ------------------------------------------------------------------

    def _build_lon_datapoints(self, all_datapoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply tier, group, and discovery whitelist; append discovery-only / ad-hoc rows."""
        easy = uses_easy_lookup_discovery(self.experience_level)
        whitelist: set[str] | None = None
        if easy and self.discovered_datapoints:
            whitelist = {str(d["oid"]) for d in self.discovered_datapoints if d.get("oid")}

        result: list[dict[str, Any]] = []

        for dp in all_datapoints:
            if self.selected_groups:
                dp_group = dp.get("group", "")
                if dp_group and dp_group not in self.selected_groups:
                    continue

            exp_min = dp.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
            if not _passes_tier(exp_min, self.experience_level, DEFAULT_LON_EXPERIENCE_MINIMUM):
                continue
            oid = str(dp.get("oid", ""))
            if whitelist is not None and oid and oid not in whitelist:
                continue
            result.append(dp)

        # For each OID in discovered_datapoints that passes tier + group filters,
        # add it if it is not already represented in result.
        #
        # Checking against result_oids (not yaml_by_oid) is intentional: an OID
        # may exist in oids.yaml under a group that is not selected (e.g. "central")
        # while discovery assigned it to a selected group (e.g. "boiler").  In
        # that case the oids.yaml version was filtered out and the OID is absent
        # from result — discovery should fill the gap with the correct group.
        #
        # When the oids.yaml entry exists but was filtered out (e.g. experience_minimum
        # set higher than the current tier), we reuse the yaml entry as the metadata
        # base so that unit, device_class, state_class and i18n labels are preserved.
        # Only group and experience_minimum are overridden from the discovery row.
        yaml_by_oid: dict[str, dict[str, Any]] = {
            str(dp.get("oid", "")): dp for dp in all_datapoints if dp.get("oid")
        }

        # Build OID → function_name map from discovery for later enrichment.
        fn_by_oid: dict[str, str] = {
            str(d["oid"]): str(d["function_name"])
            for d in self.discovered_datapoints
            if d.get("oid") and d.get("function_name")
        }

        result_oids = {str(dp.get("oid", "")) for dp in result}
        if self.discovered_datapoints:
            for row in self.discovered_datapoints:
                oid = str(row.get("oid", ""))
                if not oid or oid in result_oids:
                    continue
                exp_min = row.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
                if not _passes_tier(exp_min, self.experience_level, DEFAULT_LON_EXPERIENCE_MINIMUM):
                    continue
                if self.selected_groups:
                    grp = row.get("group", "")
                    if grp and grp not in self.selected_groups:
                        continue
                # Prefer yaml metadata (unit, device_class, i18n …) when available
                yaml_entry = yaml_by_oid.get(oid)
                if yaml_entry:
                    merged = dict(yaml_entry)
                    merged["group"] = row.get("group") or yaml_entry.get("group") or "boiler"
                    merged["experience_minimum"] = exp_min
                    result.append(merged)
                else:
                    result.append(self._synthetic_lon_datapoint_from_discovery_row(row))
                result_oids.add(oid)

        # Enrich oids.yaml entries with function_name sourced from discovery.
        # Discovery stores the LON function-block name (e.g. "LogWIN", "Heizkreis 1")
        # with each datapoint; oids.yaml entries carry no such context.
        for dp in result:
            if not dp.get("function_name"):
                fn = fn_by_oid.get(str(dp.get("oid", "")))
                if fn:
                    dp["function_name"] = fn

        if self.experience_level in ("expert", "service"):
            for ent in self.adhoc_entries:
                oid = ent["oid"]
                grp = ent.get("group", "boiler")
                if not oid or oid in result_oids:
                    continue
                result.append(self._synthetic_lon_datapoint_from_adhoc_oid(oid, grp))
                result_oids.add(oid)

        return self._deduplicate_cross_node(result)

    @staticmethod
    def _deduplicate_cross_node(
        result: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Remove cross-node duplicates of the same physical LON network variable.

        In a Windhager LON network the same NV (e.g. buffer temperature) is
        exposed by multiple nodes: the buffer controller produces it; the boiler
        and heating circuits receive and re-expose it.  Without deduplication
        the same physical sensor appears as 3–4 separate HA entities.

        Algorithm
        ---------
        Datapoints are grouped by ``(gn, mn)`` (groupNr + memberNr).

        *  Same-node, different-fct instances (e.g. HC1 and HC2 on node 15) are
           never deduplicated — they represent distinct zones / function blocks.

        *  Cross-node duplicates (same gn:mn on different subnet/node IDs) are
           deduplicated when ``GN_MN_OVERRIDES[(gn, mn)]`` defines a
           ``canonical_group``.  Only instance(s) whose ``group`` field matches
           the canonical group are kept.

        *  If the canonical group is not present in the current result (e.g. the
           user did not select that group) all instances are kept — no data is
           silently lost.

        *  If no ``canonical_group`` is configured for a pair, all instances are
           kept unchanged.
        """
        from collections import defaultdict

        def _node_key(oid_str: str) -> tuple[str, str] | None:
            """Return (subnet, node) from an OID string, or None if unparseable."""
            parts = str(oid_str).split("/")
            if len(parts) == 6:
                return parts[0], parts[1]
            return None

        def _gn_mn_key(oid_str: str) -> tuple[str, str] | None:
            parts = str(oid_str).split("/")
            if len(parts) == 6:
                return parts[3], parts[4]
            return None

        by_gn_mn: dict[tuple[str, str], list[tuple[tuple[str, str] | None, dict[str, Any]]]] = (
            defaultdict(list)
        )
        for dp in result:
            key = _gn_mn_key(dp.get("oid", ""))
            if key is None:
                continue
            by_gn_mn[key].append((_node_key(dp.get("oid", "")), dp))

        kept: list[dict[str, Any]] = []

        for (gn, mn), entries in by_gn_mn.items():
            unique_nodes = {node for node, _ in entries if node is not None}

            if len(unique_nodes) <= 1:
                # All on the same node (or unparseable) — keep all as-is.
                kept.extend(dp for _, dp in entries)
                continue

            # Multiple nodes: look up canonical_group override.
            override = GN_MN_OVERRIDES.get((int(gn), int(mn)), {})
            canonical_group = override.get("canonical_group")

            if not canonical_group:
                # No canonical group configured — keep all (no deduplication).
                kept.extend(dp for _, dp in entries)
                continue

            # Identify which node(s) carry the canonical group.
            canonical_nodes = {
                node
                for node, dp in entries
                if dp.get("group") == canonical_group and node is not None
            }

            if not canonical_nodes:
                # Canonical group not in result (e.g. user didn't select it) —
                # keep all as fallback so no value is lost.
                _LOGGER.debug(
                    "dedup: canonical_group=%s not found for gn=%s mn=%s; keeping all %d instances",
                    canonical_group, gn, mn, len(entries),
                )
                kept.extend(dp for _, dp in entries)
                continue

            kept.extend(dp for node, dp in entries if node in canonical_nodes)

        return kept

    @staticmethod
    def _coerce_adhoc_entries(raw: list[Any] | None) -> list[dict[str, str]]:
        """Normalize ``CONF_ADHOC_OIDS`` (legacy list of strings or list of dicts)."""
        out: list[dict[str, str]] = []
        if not raw:
            return out
        for item in raw:
            if isinstance(item, str):
                o = item.strip().replace(".", "/")
                if o:
                    out.append({"oid": o, "group": "boiler"})
            elif isinstance(item, dict) and item.get("oid"):
                o = str(item["oid"]).strip().replace(".", "/")
                if o:
                    out.append({"oid": o, "group": str(item.get("group") or "boiler")})
        return out

    @staticmethod
    def _synthetic_lon_datapoint_from_discovery_row(row: dict[str, Any]) -> dict[str, Any]:
        """Build a minimal ``oids.yaml``-shaped dict from serialized discovery metadata."""
        oid = str(row["oid"])
        key = f"lon_{oid.replace('/', '_')}"
        label = row.get("api_name") or oid
        dp: dict[str, Any] = {
            "oid": oid,
            "key": key,
            "i18n": {"en": label, "de": label, "fr": label, "it": label},
            "hint_node": None,
            "group": row.get("group") or "boiler",
            "experience_minimum": row.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM),
            "unit": None,
            "device_class": None,
            "state_class": "measurement",
            "type_id": row.get("type_id", -1),
            "subtype_id": -1,
            "unit_id": row.get("unit_id", -1),
            "write_protected": row.get("write_prot", True),
            "discovered": True,
        }
        fn = row.get("function_name")
        if fn:
            dp["function_name"] = fn
        return dp

    @staticmethod
    def _synthetic_lon_datapoint_from_adhoc_oid(oid: str, group: str = "boiler") -> dict[str, Any]:
        """Minimal LON datapoint dict for a user-added OID (``add_datapoint`` service)."""
        key = f"lon_{oid.replace('/', '_')}"
        return {
            "oid": oid,
            "key": key,
            "i18n": {"en": oid, "de": oid, "fr": oid, "it": oid},
            "hint_node": None,
            "group": group,
            "experience_minimum": "expert",
            "unit": None,
            "device_class": None,
            "state_class": "measurement",
            "type_id": -1,
            "subtype_id": -1,
            "unit_id": -1,
            "write_protected": True,
            "adhoc": True,
        }

    def _filter_datapoints(self, all_datapoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return only the datapoints visible at the selected tier + groups.

        Deprecated path: prefer ``_build_lon_datapoints``; kept for tests that patch
        internal behaviour.
        """
        result = []
        for dp in all_datapoints:
            if self.selected_groups:
                dp_group = dp.get("group", "")
                if dp_group and dp_group not in self.selected_groups:
                    continue

            exp_min = dp.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
            if not _passes_tier(exp_min, self.experience_level, DEFAULT_LON_EXPERIENCE_MINIMUM):
                continue
            result.append(dp)
        return result

    def _filter_restapi(
        self, all_restapi: dict[str, list[dict[str, Any]]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Return only the REST endpoints visible at the selected tier + groups."""
        if not isinstance(all_restapi, dict):
            return {}
        filtered: dict[str, list[dict[str, Any]]] = {}
        for group_name, endpoints in all_restapi.items():
            # Group filter
            if self.selected_groups and group_name not in self.selected_groups:
                # Check individual endpoint-level group override
                pass

            visible: list[dict[str, Any]] = []
            for ep in endpoints:
                ep_group = ep.get("group") or group_name
                if self.selected_groups and ep_group not in self.selected_groups:
                    continue

                entity_type = ep.get("entity_type", "sensor")
                is_actuator = entity_type in ("button", "switch", "select")
                default_min = (
                    DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM
                    if is_actuator
                    else DEFAULT_REST_SENSOR_EXPERIENCE_MINIMUM
                )
                exp_min = ep.get("experience_minimum", default_min)
                if not _passes_tier(exp_min, self.experience_level, default_min):
                    continue
                visible.append(ep)

            if visible:
                filtered[group_name] = visible
        return filtered

    # ------------------------------------------------------------------
    # YAML loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml(path: Path, root_key: str) -> Any:
        """Load a YAML file and return the value at root_key, or an empty container."""
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            if not isinstance(data, dict) or root_key not in data:
                _LOGGER.error("Invalid YAML at %s: missing root key '%s'", path, root_key)
                return [] if root_key == "datapoints" else {}
            return data[root_key]
        except FileNotFoundError:
            _LOGGER.warning("YAML file not found: %s", path)
            return [] if root_key == "datapoints" else {}
        except Exception as err:
            _LOGGER.error("Failed to load %s: %s", path, err)
            return [] if root_key == "datapoints" else {}

    # ------------------------------------------------------------------
    # Data update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all datapoints and RestAPI sensors in one coordinator cycle."""
        try:
            data: dict[str, Any] = {}

            # --- LON / OID datapoints ---
            for datapoint in self.datapoints:
                oid_str = datapoint.get("oid", "")
                key = datapoint["key"]
                oid_parts = oid_str.split("/")
                if len(oid_parts) != 6:
                    _LOGGER.warning("Skipping datapoint %s: OID '%s' invalid", key, oid_str)
                    continue
                try:
                    result = await self.api_client.async_get_datapoint(oid_parts)
                    if isinstance(result, dict) and "value" in result:
                        data[key] = _normalize_lon_datapoint_value(result["value"])
                    else:
                        _LOGGER.debug("No value in response for %s: %s", key, result)
                except WindhagerAuthError:
                    raise
                except WindhagerError as err:
                    if getattr(err, "status", None) == 404:
                        self.unknown_oids.add(oid_str)
                        _LOGGER.debug("OID %s not present on device (404)", oid_str)
                    else:
                        _LOGGER.warning(
                            "Failed to fetch LON datapoint %s (%s): %s", key, oid_str, err
                        )

            # --- RestAPI sensor endpoints ---
            for _group_name, endpoints in self.restapi_endpoints.items():
                for ep_cfg in endpoints:
                    if ep_cfg.get("entity_type") != "sensor":
                        continue
                    endpoint = ep_cfg["endpoint"]
                    key = ep_cfg["key"]
                    try:
                        result = await self._call_restapi_endpoint(endpoint)
                        if result is not None:
                            data[key] = self._extract_value(result)
                        else:
                            _LOGGER.debug("Empty response for RestAPI sensor %s", key)
                    except WindhagerAuthError:
                        raise
                    except WindhagerError as err:
                        _LOGGER.warning("Failed to fetch RestAPI sensor %s: %s", key, err)

            return data

        except WindhagerAuthError as err:
            raise UpdateFailed(f"Authentication failed: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Windhager: {err}") from err

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _call_restapi_endpoint(self, endpoint: str) -> dict[str, Any] | None:
        """Dispatch a sensor GET call to the matching API client method."""
        _DISPATCH: dict[str, Any] = {
            "/WsAdmin/api/1.0/systemtime": self.api_client.async_get_system_time,
            "/WsAdmin/api/1.0/systemtime/ntpserver": self.api_client.async_get_ntp_servers,
            "/WsAdmin/api/1.0/systemtime/ntpserver/selected": (
                self.api_client.async_get_selected_ntp_server
            ),
            "/WsAdmin/api/1.0/systemtime/timezone": self.api_client.async_get_timezone,
            "/api/1.0/settings": self.api_client.async_get_settings,
            "/api/1.0/settings/allKeys": self.api_client.async_get_all_settings_keys,
            "/WsAdmin/api/1.0/led": self.api_client.async_get_led_status,
            "/InfoWinFehlerlog/api/1.0/fehlerlog": self.api_client.async_get_fehlerlog,
            "/InfoWinHeartbeat/api/1.0/heartbeat": self.api_client.async_get_heartbeat,
            "/WsAdmin/api/1.0/update/factoryReset": self.api_client.async_get_factory_reset_status,
            "/api/1.0/vpn/status": self.api_client.async_get_vpn_status,
            "/api/1.0/DynIP/CheckIP": self.api_client.async_check_dynip,
            "/api/1.0/lookup": self.api_client.async_get_subnets,
        }
        method = _DISPATCH.get(endpoint)
        if method:
            return await method()
        return await self.api_client.async_request("GET", endpoint)

    @staticmethod
    def _extract_value(result: dict[str, Any]) -> Any:
        """Extract a meaningful scalar from a response dict."""
        for key in ("value", "status", "time", "text"):
            if key in result:
                return result[key]
        return str(result)
