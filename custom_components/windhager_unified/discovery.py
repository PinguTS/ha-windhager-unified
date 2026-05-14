"""LON network discovery for the Windhager integration.

Orchestrates:
  1. GET /InfoWinHeartbeat/api/1.0/kesselwahl/selected — boiler family detection.
  2. Topology:
     - easy tiers (essential/comfort/advanced): GET /api/1.0/lookup/{subnet}.
     - expert/service: trigger /api/1.0/scan/nodes/* state machine first, then
       fall through to GET /api/1.0/nodes for the node list.
  3. For each node, lookup walk (functions → levels → positions) with
     per-fctType tier-based levelId filtering (see ``tier_lookup``).
  4. Classify functions into functional groups using MapToInstance.xml + a
     hard-coded FUNCTION_TYPE_GROUPS table for types not in MapToInstance.

All API paths come from Swagger 1.2 source files in docs/swagger/.

ASSUMPTION for boiler-family mapping: kesselwahl id values are mapped to
product-family names based on the documented enum in
InfoWinHeartbeat_1.0_kesselwahl.json. The id→HA-friendly-name lookup goes
beyond what Swagger documents — it is a best-effort label.

ASSUMPTION for scan state-machine terminal status: the device returns a JSON
object with a field whose value indicates completion; we treat any response
containing "idle", "done", "ready", or "scan_done" (case-insensitive) as
terminal.  The full raw status is logged at DEBUG on first receipt so real
device shapes can be captured.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from xml.etree import ElementTree as ET

from .exceptions import WindhagerApiError, WindhagerAuthError
from .labels import LabelCatalog
from .tier_lookup import (
    GN_MN_OVERRIDES,
    allowed_levels_for_tier,
    experience_minimum_from_discovery,
    uses_easy_lookup_discovery,
)

if TYPE_CHECKING:
    from .api_client import WindhagerApiClient

_LOGGER = logging.getLogger(__name__)

_MAP_TO_INSTANCE_PATH = Path(__file__).parent / "labels" / "MapToInstance.xml"

# Limit the lookup walk to avoid hammering the device
MAX_LEVELS = 200
MAX_POSITIONS = 20

# Scan state-machine parameters (expert/service setup)
# ASSUMPTION: any response value that contains one of these substrings
# (case-insensitive) indicates the scan has reached a terminal/idle state.
_SCAN_TERMINAL_KEYWORDS: frozenset[str] = frozenset({"idle", "done", "ready", "scan_done"})
_SCAN_POLL_INTERVAL_S: float = 1.0
_SCAN_TIMEOUT_S: float = 60.0

# ---------------------------------------------------------------------------
# Boiler family mapping
# Documented in InfoWinHeartbeat_1.0_kesselwahl.json (enum of id values).
# ASSUMPTION: the product-family labels below are best-effort — Swagger only
# documents the numeric id, not the friendly product name.
# ---------------------------------------------------------------------------
KESSELWAHL_FAMILY: dict[int, str] = {
    1: "BioWIN / PuroWIN (Pellets)",
    2: "LogWIN (Holz)",
    3: "DuoWIN (Kombikessel)",
    4: "HackWIN (Hackschnitzel)",
    5: "OelWIN (Öl)",
    6: "None",
    7: "MB1",
    8: "MB2",
}

# ---------------------------------------------------------------------------
# Function-type → group mapping
# fct_type values 0/1/2 come from StaticNavAssignment.xml.
# fct_type 4/12/13 come from MapToInstance.xml.
# Additional types derived from live device data and EbenenTexte_en.xml.
#
# ASSUMPTIONS (labelled per entry):
#   fctType 10 = boiler primary function (LogWIN / BioWIN2 observed live).
#   fctType 14 = UMUMLZ heating-circuit controller (EbenenTexte fcttyp id="14",
#                level names include "Room temperature", "Heating circuit" etc.).
#   fctType 15 = WVF PUFFER buffer/shift-valve controller (EbenenTexte id="15",
#                levels include "Buffer temperature", "Boiler temperature" etc.).
#                NOTE: oids.yaml uses group "central" for fct_type 15 entries —
#                discovery emits "buffer" for consistency with EbenenTexte;
#                the mismatch with the static catalogue is tracked separately.
#   fctType 16 = B-PLM boiler loading pump / burner controller
#                (EbenenTexte id="16", levels include "Boiler-Buffer temperature",
#                "Buffer loading pump", "Burner control" etc.).
#                NOTE: oids.yaml uses group "buffer" for fct_type 16 entries —
#                discovery emits "boiler_loading_pump"; tracked separately.
# ---------------------------------------------------------------------------
FUNCTION_TYPE_GROUPS: dict[int, str] = {
    0: "boiler",              # main boiler function (StaticNavAssignment ftype 0)
    1: "heating_circuit",     # heating circuit (StaticNavAssignment ftype 1)
    2: "dhw",                 # domestic hot water (StaticNavAssignment ftype 2)
    4: "cascade",             # Kaskadenmanager (MapToInstance type 4)
    10: "boiler",             # boiler (LogWIN / BioWIN2 primary function)
    12: "io5500",             # IO5500 expansion module (MapToInstance type 12)
    13: "solar",              # Solar ES (MapToInstance type 13)
    14: "heating_circuit",    # UMUMLZ heating-circuit controller (EbenenTexte id=14)
    15: "buffer",             # WVF PUFFER buffer/shift-valve controller (EbenenTexte id=15)
    16: "boiler_loading_pump",# B-PLM boiler loading pump (EbenenTexte id=16)
    18: "boiler",             # alternate boiler type (StaticNavAssignment ftype 18)
    19: "dhw",                # alternate DHW type (StaticNavAssignment ftype 19)
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class DiscoveredDatapoint:
    """One LON datapoint position discovered via lookup."""

    oid: str
    level_id: int
    write_prot: bool
    type_id: int
    unit_id: int
    experience_minimum: str
    api_name: str | None = None
    function_name: str | None = None

    def to_option_dict(self) -> dict[str, Any]:
        """Serialize for Home Assistant ``config_entry.options``."""
        d = asdict(self)
        return d


@dataclass
class DiscoveredFunction:
    fct_id: int
    fct_type: int
    name: str
    locked: bool = False
    datapoints: list[DiscoveredDatapoint] = field(default_factory=list)


@dataclass
class DiscoveredNode:
    node_id: int
    subnet: int
    name: str
    neuron_id: str
    program_id: str
    functions: list[DiscoveredFunction] = field(default_factory=list)


@dataclass
class DiscoveredGroup:
    id: str  # stable slug, e.g. "heating_circuit", "boiler"
    label: str  # human-readable label
    fct_type: int
    node_ids: list[int] = field(default_factory=list)
    datapoints: list[DiscoveredDatapoint] = field(default_factory=list)


@dataclass
class DiscoveryResult:
    boiler_id: int | None
    boiler_name: str | None
    nodes: list[DiscoveredNode] = field(default_factory=list)
    groups: list[DiscoveredGroup] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MapToInstance loader
# ---------------------------------------------------------------------------


def _load_map_to_instance() -> dict[int, str]:
    """Parse MapToInstance.xml, return {fct_type: desc}."""
    result: dict[int, str] = {}
    path = _MAP_TO_INSTANCE_PATH
    if not path.exists():
        _LOGGER.warning("discovery: MapToInstance.xml not found at %s", path)
        return result
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as err:
        _LOGGER.warning("discovery: could not parse MapToInstance.xml: %s", err)
        return result
    for entry in root.findall("entry"):
        try:
            fct_type = int(entry.get("type", "-1"))
        except ValueError:
            continue
        desc = entry.get("desc", f"type_{fct_type}")
        result[fct_type] = desc
    return result


def serialize_discovered_datapoints_for_config(result: DiscoveryResult) -> list[dict[str, Any]]:
    """Flatten ``DiscoveredGroup`` datapoints for ``config_entry.options``."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for grp in result.groups:
        for dp in grp.datapoints:
            if dp.oid in seen:
                continue
            seen.add(dp.oid)
            row = dp.to_option_dict()
            row["group"] = grp.id
            out.append(row)
    return out


def _normalize_subnet_lookup_nodes(resp: Any) -> list[dict[str, Any]]:
    """Normalize GET /lookup/{subnetId} JSON (array or wrapper) to a list of nodes."""
    if isinstance(resp, list):
        return [x for x in resp if isinstance(x, dict)]
    if isinstance(resp, dict):
        inner = resp.get("nodes") or resp.get("nodeList") or []
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
        # Single node object
        if "nodeId" in resp or "functions" in resp:
            return [resp]
    return []


def _normalize_nodes_flat(resp: Any) -> list[dict[str, Any]]:
    """Normalize GET /api/1.0/nodes response."""
    if isinstance(resp, list):
        return [x for x in resp if isinstance(x, dict)]
    if isinstance(resp, dict) and "nodes" in resp:
        inner = resp["nodes"]
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
    return []


# ---------------------------------------------------------------------------
# LON scan state-machine (expert / service tiers)
# ---------------------------------------------------------------------------


def _is_scan_terminal(status_raw: dict[str, Any] | None) -> bool:
    """Return True when the scan status payload indicates a terminal/idle state.

    ASSUMPTION: any string value anywhere in the JSON object (keys or values)
    that contains one of ``_SCAN_TERMINAL_KEYWORDS`` is treated as done.
    The full payload is logged at DEBUG on first call.
    """
    if status_raw is None:
        return False
    payload_str = str(status_raw).lower()
    return any(kw in payload_str for kw in _SCAN_TERMINAL_KEYWORDS)


async def _run_full_lon_scan(
    client: WindhagerApiClient,
    warnings: list[str],
) -> None:
    """Trigger the LON scan state machine and wait for completion.

    Sequence (documented in RestApiRC7030_1.0_scan.json):
      PUT initscan → start → scanNodes → poll GET status → postScan → scanDone → quit

    On any error or timeout: logs a warning, sends ``quit`` best-effort to
    release the state machine, then returns so the lookup walk can continue.

    ASSUMPTION: terminal status keywords — see ``_is_scan_terminal``.
    """
    _logged_status_once = False

    async def _cmd(name: str) -> None:
        try:
            await client.async_put_scan_cmd(name)
            _LOGGER.debug("discovery: scan cmd '%s' OK", name)
        except Exception as err:
            raise RuntimeError(f"scan cmd '{name}' failed: {err}") from err

    async def _quit_best_effort() -> None:
        try:
            await client.async_put_scan_cmd("quit")
            _LOGGER.debug("discovery: scan quit sent")
        except Exception as err:
            _LOGGER.debug("discovery: scan quit failed (ignored): %s", err)

    try:
        await _cmd("initscan")
        await _cmd("start")
        await _cmd("scanNodes")

        deadline = asyncio.get_event_loop().time() + _SCAN_TIMEOUT_S
        terminal = False
        nonlocal_flag = {"logged": False}
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(_SCAN_POLL_INTERVAL_S)
            try:
                status = await client.async_get_scan_status()
            except Exception as err:
                warn = f"scan status poll failed: {err}"
                _LOGGER.warning("discovery: %s", warn)
                warnings.append(warn)
                break
            if not nonlocal_flag["logged"]:
                _LOGGER.debug("discovery: scan status (first): %s", status)
                nonlocal_flag["logged"] = True
            if _is_scan_terminal(status):
                terminal = True
                break

        if not terminal:
            warn = f"LON scan did not complete within {_SCAN_TIMEOUT_S:.0f}s; continuing"
            _LOGGER.warning("discovery: %s", warn)
            warnings.append(warn)

        await _cmd("postScan")
        await _cmd("scanDone")

    except Exception as err:
        warn = f"LON scan aborted: {err}"
        _LOGGER.warning("discovery: %s", warn)
        warnings.append(warn)
    finally:
        await _quit_best_effort()


# ---------------------------------------------------------------------------
# Main discovery coroutine
# ---------------------------------------------------------------------------


async def discover(
    client: WindhagerApiClient,
    experience_tier: str | None = None,
    subnet_id: int = 1,
) -> DiscoveryResult:
    """Run LON network discovery.

    ``experience_tier`` controls topology source and lookup depth:
      * essential / comfort / advanced — GET /lookup/{subnet}, tier-filtered levels
      * expert / service — GET /nodes, full level/position walk (capped)
      * None — same as expert (backward compatible for callers that omit the tier)

    Tolerates partial failures: each step is wrapped so that errors only
    produce warnings rather than aborting the entire discovery.
    HTTP 401 is re-raised immediately.
    """
    tier = experience_tier or "expert"
    result = DiscoveryResult(boiler_id=None, boiler_name=None)
    loop = asyncio.get_running_loop()
    map_to_instance = await loop.run_in_executor(None, _load_map_to_instance)
    label_catalog = await loop.run_in_executor(None, LabelCatalog.load)

    # -----------------------------------------------------------------------
    # Step 1: detect boiler family
    # -----------------------------------------------------------------------
    try:
        kw = await client.async_get_kesselwahl_selected()
        if isinstance(kw, dict):
            result.boiler_id = kw.get("id")
            result.boiler_name = KESSELWAHL_FAMILY.get(result.boiler_id or -1, kw.get("name"))
            _LOGGER.debug("discovery: boiler id=%s name=%s", result.boiler_id, result.boiler_name)
    except WindhagerAuthError:
        raise
    except WindhagerApiError as err:
        if err.status == 404:
            _LOGGER.debug("discovery: kesselwahl/selected returned 404 — boiler unknown")
        else:
            warn = f"kesselwahl/selected failed: {err}"
            _LOGGER.warning("discovery: %s", warn)
            result.warnings.append(warn)
    except Exception as err:
        warn = f"kesselwahl/selected unexpected error: {err}"
        _LOGGER.warning("discovery: %s", warn)
        result.warnings.append(warn)

    # -----------------------------------------------------------------------
    # Step 2: node list (lookup subnet vs scan + flat nodes)
    # -----------------------------------------------------------------------
    nodes_raw: list[dict[str, Any]] = []
    try:
        if uses_easy_lookup_discovery(tier):
            nodes_resp = await client.async_get_nodes(str(subnet_id))
            nodes_raw = _normalize_subnet_lookup_nodes(nodes_resp)
            if not nodes_raw:
                _LOGGER.debug(
                    "discovery: lookup/%s returned no nodes; falling back to /nodes",
                    subnet_id,
                )
                nodes_resp = await client.async_get_nodes_flat()
                nodes_raw = _normalize_nodes_flat(nodes_resp)
        else:
            # expert/service: trigger a fresh LON scan before reading node list
            await _run_full_lon_scan(client, result.warnings)
            nodes_resp = await client.async_get_nodes_flat()
            nodes_raw = _normalize_nodes_flat(nodes_resp)
    except WindhagerAuthError:
        raise
    except Exception as err:
        warn = f"node list failed (tier={tier}): {err}"
        _LOGGER.warning("discovery: %s", warn)
        result.warnings.append(warn)

    if not nodes_raw:
        _LOGGER.debug("discovery: no nodes returned; discovery complete with no groups")
        return result

    # -----------------------------------------------------------------------
    # Step 3: lookup walk per node
    # -----------------------------------------------------------------------
    groups_by_id: dict[str, DiscoveredGroup] = {}

    for node_raw in nodes_raw:
        node = DiscoveredNode(
            node_id=node_raw.get("nodeId", 0),
            subnet=node_raw.get("subnet", subnet_id),
            name=node_raw.get("name", f"node_{node_raw.get('nodeId', '?')}"),
            neuron_id=str(node_raw.get("neuronId", "") or ""),
            program_id=str(node_raw.get("programId", "") or ""),
        )
        functions_inline = node_raw.get("functions")
        if not isinstance(functions_inline, list):
            functions_inline = None
        await _walk_node(
            client,
            node,
            groups_by_id,
            map_to_instance,
            result.warnings,
            functions_inline=functions_inline,
            tier=tier,
            label_catalog=label_catalog,
        )
        result.nodes.append(node)

    result.groups = sorted(groups_by_id.values(), key=lambda g: (g.id, g.fct_type))
    return result


async def _walk_node(
    client: WindhagerApiClient,
    node: DiscoveredNode,
    groups: dict[str, DiscoveredGroup],
    map_to_instance: dict[int, str],
    warnings: list[str],
    *,
    functions_inline: list[dict[str, Any]] | None,
    tier: str,
    label_catalog: LabelCatalog,
) -> None:
    """Walk the lookup tree for one node, populating ``groups`` in-place."""
    subnet_id = str(node.subnet)
    node_id = str(node.node_id)

    functions_raw: list[Any]
    if functions_inline is not None:
        functions_raw = functions_inline
    else:
        try:
            fcts_resp = await client.async_get_node_details(subnet_id, node_id)
        except WindhagerAuthError:
            raise
        except Exception as err:
            warn = f"lookup/{subnet_id}/{node_id} failed: {err}"
            _LOGGER.warning("discovery: %s", warn)
            warnings.append(warn)
            return

        if not isinstance(fcts_resp, dict):
            _LOGGER.debug("discovery: unexpected lookup response type for node %s", node_id)
            return

        functions_raw = fcts_resp.get("functions") or fcts_resp.get("fcts") or []
        if isinstance(fcts_resp, list):
            functions_raw = fcts_resp

    for fct_raw in functions_raw:
        if not isinstance(fct_raw, dict):
            continue
        fct_id = fct_raw.get("fctId", fct_raw.get("id", 0))
        fct_type = fct_raw.get("fctType", fct_raw.get("type", -1))
        fct_name = fct_raw.get("name", f"fct_{fct_id}")
        locked = bool(fct_raw.get("locked", fct_raw.get("lock", False)))

        func = DiscoveredFunction(
            fct_id=fct_id,
            fct_type=fct_type,
            name=fct_name,
            locked=locked,
        )

        # Classify into group
        group_id = _classify_fct_type(fct_type, map_to_instance)
        group_label = _group_label(fct_type, group_id, map_to_instance)

        if group_id not in groups:
            groups[group_id] = DiscoveredGroup(
                id=group_id,
                label=group_label,
                fct_type=fct_type,
            )
        grp = groups[group_id]
        if node.node_id not in grp.node_ids:
            grp.node_ids.append(node.node_id)

        await _walk_function(
            client,
            node,
            func,
            grp,
            subnet_id,
            node_id,
            str(fct_id),
            warnings,
            tier=tier,
            label_catalog=label_catalog,
        )
        node.functions.append(func)


async def _walk_function(
    client: WindhagerApiClient,
    node: DiscoveredNode,
    func: DiscoveredFunction,
    grp: DiscoveredGroup,
    subnet_id: str,
    node_id: str,
    fct_id: str,
    warnings: list[str],
    *,
    tier: str,
    label_catalog: LabelCatalog,
) -> None:
    """Walk levels under one function, collecting datapoints."""
    try:
        levels_resp = await client.async_get_functions(subnet_id, node_id, fct_id)
    except WindhagerAuthError:
        raise
    except Exception as err:
        _LOGGER.debug(
            "discovery: lookup levels for %s/%s/%s failed: %s",
            subnet_id,
            node_id,
            fct_id,
            err,
        )
        return

    levels_raw: list[Any] = []
    if isinstance(levels_resp, dict):
        levels_raw = levels_resp.get("levels") or levels_resp.get("lvls") or []
    elif isinstance(levels_resp, list):
        levels_raw = levels_resp

    # Per-fctType level filter — resolves to None for expert/service or unknown types
    allowed_levels = allowed_levels_for_tier(tier, fct_type=func.fct_type)

    for idx, level_raw in enumerate(levels_raw):
        if idx >= MAX_LEVELS:
            _LOGGER.debug(
                "discovery: capped levels walk at %d for fct %s/%s/%s",
                MAX_LEVELS,
                subnet_id,
                node_id,
                fct_id,
            )
            break
        if not isinstance(level_raw, dict):
            continue
        level_id = int(level_raw.get("levelId", level_raw.get("id", 0)))
        if allowed_levels is not None and level_id not in allowed_levels:
            continue
        await _walk_level(
            client,
            func,
            grp,
            subnet_id,
            node_id,
            fct_id,
            str(level_id),
            warnings,
            label_catalog=label_catalog,
        )


async def _walk_level(
    client: WindhagerApiClient,
    func: DiscoveredFunction,
    grp: DiscoveredGroup,
    subnet_id: str,
    node_id: str,
    fct_id: str,
    level_id: str,
    warnings: list[str],
    *,
    label_catalog: LabelCatalog,
) -> None:
    """Walk positions (datapoints) under one level."""
    try:
        pos_resp = await client.async_get_datapoints_in_level(subnet_id, node_id, fct_id, level_id)
    except WindhagerAuthError:
        raise
    except Exception as err:
        _LOGGER.debug(
            "discovery: lookup positions for %s/%s/%s/%s failed: %s",
            subnet_id,
            node_id,
            fct_id,
            level_id,
            err,
        )
        return

    level_id_int = int(level_id)
    level_label = label_catalog.level_name(func.fct_type, level_id_int, "en")

    positions_raw: list[Any] = []
    if isinstance(pos_resp, dict):
        positions_raw = pos_resp.get("positions") or pos_resp.get("pos") or []
    elif isinstance(pos_resp, list):
        positions_raw = pos_resp

    for idx, pos_raw in enumerate(positions_raw):
        if idx >= MAX_POSITIONS:
            _LOGGER.debug(
                "discovery: capped positions walk at %d for level %s/%s/%s/%s",
                MAX_POSITIONS,
                subnet_id,
                node_id,
                fct_id,
                level_id,
            )
            break
        if not isinstance(pos_raw, dict):
            continue

        # Use the OID field the API already returns; it contains the real groupNr
        # (4th segment), not the levelId.  Synthesising the path with levelId
        # produces wrong OIDs that 404 on every subsequent /datapoint/... call.
        raw_oid = pos_raw.get("OID")
        if raw_oid:
            oid = str(raw_oid).lstrip("/")
            parts = oid.split("/")
            if len(parts) != 6:
                _LOGGER.debug(
                    "discovery: skipping datapoint with malformed OID '%s' in level %s/%s/%s/%s",
                    raw_oid,
                    subnet_id,
                    node_id,
                    fct_id,
                    level_id,
                )
                continue
        else:
            # Fallback for devices that do not return OID (not observed; kept for safety)
            _LOGGER.debug(
                "discovery: datapoint in level %s/%s/%s/%s has no OID field; skipping",
                subnet_id,
                node_id,
                fct_id,
                level_id,
            )
            continue

        write_prot = bool(pos_raw.get("writeProt", pos_raw.get("write_prot", True)))
        type_id = int(pos_raw.get("typeId", pos_raw.get("type_id", -1)) or -1)
        unit_id = int(pos_raw.get("unitId", pos_raw.get("unit_id", -1)) or -1)
        api_name = pos_raw.get("name")
        if api_name is not None:
            api_name = str(api_name)
        exp_min = experience_minimum_from_discovery(
            level_id_int, write_prot, level_label, fct_type=func.fct_type
        )
        # Apply gn_mn_overrides: override experience_minimum for specific gn:mn
        # pairs regardless of node or level, as configured in groups_config.yaml.
        gn_int, mn_int = int(parts[3]), int(parts[4])
        override = GN_MN_OVERRIDES.get((gn_int, mn_int))
        if override:
            exp_min = override.get("experience_minimum", exp_min)
        dp = DiscoveredDatapoint(
            oid=oid,
            level_id=level_id_int,
            write_prot=write_prot,
            type_id=type_id,
            unit_id=unit_id,
            experience_minimum=exp_min,
            api_name=api_name,
            function_name=func.name or None,
        )
        func.datapoints.append(dp)
        if not any(x.oid == oid for x in grp.datapoints):
            grp.datapoints.append(dp)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_fct_type(fct_type: int, map_to_instance: dict[int, str]) -> str:
    """Return a stable group slug for the given fct_type."""
    if fct_type in FUNCTION_TYPE_GROUPS:
        return FUNCTION_TYPE_GROUPS[fct_type]
    if fct_type in map_to_instance:
        return _slugify(map_to_instance[fct_type])
    return f"unknown_{fct_type}"


def _group_label(fct_type: int, group_id: str, map_to_instance: dict[int, str]) -> str:
    """Return a human-readable label for the group."""
    _FRIENDLY: dict[str, str] = {
        "boiler": "Boiler / Heat generator",
        "heating_circuit": "Heating circuit",
        "dhw": "Domestic hot water",
        "cascade": "Cascade manager",
        "io5500": "IO5500",
        "solar": "Solar",
        "central": "Central controller",
        "buffer": "Buffer / Shift valve",
        "boiler_loading_pump": "Boiler loading pump",
    }
    if group_id in _FRIENDLY:
        return _FRIENDLY[group_id]
    if fct_type in map_to_instance:
        return map_to_instance[fct_type]
    if group_id.startswith("unknown_"):
        return f"Unknown group (fctType={fct_type})"
    return group_id.replace("_", " ").title()


def _slugify(text: str) -> str:
    """Convert a description string to a lowercase slug."""
    return text.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
