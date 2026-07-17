"""Multi-step config flow and options flow for the Windhager integration.

Steps (initial setup):
  1. user       — host / credentials / SSL / scan_interval
  2. experience — select experience tier (essential … service)
  3. discover   — progress indicator; runs LON network discovery
  4. groups     — multi-select from discovered functional groups
  5. finish     — persists options and creates the config entry

Options flow (reconfigure):
  - tier / groups / scan_interval / verify_ssl / refresh_labels
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api_client import WindhagerApiClient
from .const import (
    CONF_ADHOC_OIDS,
    CONF_DISCOVERED_DATAPOINTS,
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
    CONF_HISTORY_RETENTION_DAYS,
    CONF_HISTORY_SAMPLE_INTERVAL,
    CONF_HISTORY_STORAGE_MODE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_REFRESH_LABELS,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    CONFIG_ENTRY_VERSION,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_HISTORY_SAMPLE_INTERVAL,
    DEFAULT_HISTORY_STORAGE_MODE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EXPERIENCE_TIERS,
    HISTORY_MODE_HOME_ASSISTANT,
    HISTORY_STORAGE_MODES,
    MAX_HISTORY_RETENTION_DAYS,
    MAX_HISTORY_SAMPLE_INTERVAL,
    MIN_HISTORY_RETENTION_DAYS,
    MIN_HISTORY_SAMPLE_INTERVAL,
)
from .discovery import (
    DiscoveredGroup,
    DiscoveryResult,
    discover,
    serialize_discovered_datapoints_for_config,
)
from .exceptions import WindhagerAuthError, WindhagerConnectionError, WindhagerTimeoutError
from .tier_lookup import get_tier_defaults

_LOGGER = logging.getLogger(__name__)

_TIER_DEFAULT_GROUPS: dict[str, set[str]] = get_tier_defaults()


def _default_groups_for_tier(tier: str, all_group_ids: list[str]) -> list[str]:
    """Return the group IDs that should be pre-checked for the given tier."""
    defaults = _TIER_DEFAULT_GROUPS.get(tier, set())
    if not defaults:
        return list(all_group_ids)  # select all for expert/service
    return [g for g in all_group_ids if g in defaults]


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Multi-step config flow for Windhager."""

    VERSION = CONFIG_ENTRY_VERSION

    def __init__(self) -> None:
        self._user_data: dict[str, Any] = {}
        self._discovery: DiscoveryResult | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        return OptionsFlowHandler(config_entry)

    # ------------------------------------------------------------------
    # Step 1 — credentials
    # ------------------------------------------------------------------

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            resolved_host, errors = await _probe_host(
                hass=self.hass,
                host=user_input[CONF_HOST],
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                verify_ssl=user_input[CONF_VERIFY_SSL],
            )
            if not errors:
                unique_id = hashlib.md5(resolved_host.encode()).hexdigest()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                self._user_data = {**user_input, CONF_HOST: resolved_host}
                return await self.async_step_experience()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): cv.string,
                    vol.Required(CONF_USERNAME, default="Service"): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                    vol.Optional(CONF_VERIFY_SSL, default=False): cv.boolean,
                    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                        vol.Coerce(int), vol.Range(min=10, max=300)
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "docs_url": "https://github.com/PinguTS/ha-windhager-unified/blob/main/docs/user/setup.md"
            },
        )

    # ------------------------------------------------------------------
    # Step 2 — experience tier
    # ------------------------------------------------------------------

    async def async_step_experience(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            self._user_data[CONF_EXPERIENCE_LEVEL] = user_input[CONF_EXPERIENCE_LEVEL]
            return await self.async_step_discover()

        return self.async_show_form(
            step_id="experience",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EXPERIENCE_LEVEL, default=DEFAULT_EXPERIENCE_LEVEL): vol.In(
                        list(EXPERIENCE_TIERS)
                    ),
                }
            ),
        )

    # ------------------------------------------------------------------
    # Step 3 — discovery (progress)
    # ------------------------------------------------------------------

    async def async_step_discover(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if self._discovery is None:
            client = WindhagerApiClient(
                host=self._user_data[CONF_HOST],
                username=self._user_data[CONF_USERNAME],
                password=self._user_data[CONF_PASSWORD],
                verify_ssl=self._user_data.get(CONF_VERIFY_SSL, False),
            )
            try:
                async with client:
                    tier = self._user_data.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL)
                    self._discovery = await discover(client, experience_tier=tier)
            except WindhagerAuthError:
                return await self.async_step_user()
            except Exception as err:
                _LOGGER.warning("Config flow: discovery failed: %s", err)
                self._discovery = DiscoveryResult(boiler_id=None, boiler_name=None)

        return await self.async_step_groups()

    # ------------------------------------------------------------------
    # Step 4 — groups
    # ------------------------------------------------------------------

    async def async_step_groups(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        discovery = self._discovery or DiscoveryResult(boiler_id=None, boiler_name=None)
        groups: list[DiscoveredGroup] = discovery.groups
        tier = self._user_data.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL)

        all_group_ids = [g.id for g in groups]

        if user_input is not None:
            selected = user_input.get(CONF_GROUPS, all_group_ids)
            self._user_data[CONF_GROUPS] = selected
            return await self.async_step_history()

        default_selected = _default_groups_for_tier(tier, all_group_ids)
        # Use SelectSelector with translation_key so HA resolves group labels from
        # the translation files; g.label is the English fallback for unknown slugs.
        group_selector = SelectSelector(
            SelectSelectorConfig(
                options=[SelectOptionDict(value=g.id, label=g.label) for g in groups],
                multiple=True,
                mode=SelectSelectorMode.LIST,
                translation_key="groups",
            )
        )

        return self.async_show_form(
            step_id="groups",
            data_schema=vol.Schema(
                {vol.Optional(CONF_GROUPS, default=default_selected): group_selector}
            ),
            description_placeholders={
                "tier": tier,
                "boiler": discovery.boiler_name or "unknown",
            },
        )

    # ------------------------------------------------------------------
    # Step 5 — history storage profile
    # ------------------------------------------------------------------

    async def async_step_history(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            mode = user_input[CONF_HISTORY_STORAGE_MODE]
            self._user_data[CONF_HISTORY_STORAGE_MODE] = mode
            if mode == HISTORY_MODE_HOME_ASSISTANT:
                return await self._async_create_entry()
            return await self.async_step_history_advanced()

        mode_selector = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=m, label=m.replace("_", " ").title())
                    for m in HISTORY_STORAGE_MODES
                ],
                mode=SelectSelectorMode.LIST,
                translation_key=CONF_HISTORY_STORAGE_MODE,
            )
        )
        return self.async_show_form(
            step_id="history",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HISTORY_STORAGE_MODE,
                        default=DEFAULT_HISTORY_STORAGE_MODE,
                    ): mode_selector,
                }
            ),
        )

    async def async_step_history_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._user_data[CONF_HISTORY_SAMPLE_INTERVAL] = user_input[CONF_HISTORY_SAMPLE_INTERVAL]
            self._user_data[CONF_HISTORY_RETENTION_DAYS] = user_input[CONF_HISTORY_RETENTION_DAYS]
            return await self._async_create_entry()

        return self.async_show_form(
            step_id="history_advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HISTORY_SAMPLE_INTERVAL,
                        default=DEFAULT_HISTORY_SAMPLE_INTERVAL,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_HISTORY_SAMPLE_INTERVAL,
                            max=MAX_HISTORY_SAMPLE_INTERVAL,
                        ),
                    ),
                    vol.Optional(
                        CONF_HISTORY_RETENTION_DAYS,
                        default=DEFAULT_HISTORY_RETENTION_DAYS,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_HISTORY_RETENTION_DAYS,
                            max=MAX_HISTORY_RETENTION_DAYS,
                        ),
                    ),
                }
            ),
        )

    async def _async_create_entry(self) -> FlowResult:
        """Create the config entry after all setup steps have collected data."""
        disc = self._discovery or DiscoveryResult(boiler_id=None, boiler_name=None)
        options: dict[str, Any] = {
            CONF_EXPERIENCE_LEVEL: self._user_data.get(
                CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL
            ),
            CONF_GROUPS: self._user_data.get(CONF_GROUPS, []),
            CONF_SCAN_INTERVAL: self._user_data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            CONF_VERIFY_SSL: self._user_data.get(CONF_VERIFY_SSL, False),
            CONF_REFRESH_LABELS: False,
            CONF_DISCOVERED_DATAPOINTS: serialize_discovered_datapoints_for_config(disc),
            CONF_ADHOC_OIDS: [],
            CONF_HISTORY_STORAGE_MODE: self._user_data.get(
                CONF_HISTORY_STORAGE_MODE, DEFAULT_HISTORY_STORAGE_MODE
            ),
            CONF_HISTORY_SAMPLE_INTERVAL: self._user_data.get(
                CONF_HISTORY_SAMPLE_INTERVAL, DEFAULT_HISTORY_SAMPLE_INTERVAL
            ),
            CONF_HISTORY_RETENTION_DAYS: self._user_data.get(
                CONF_HISTORY_RETENTION_DAYS, DEFAULT_HISTORY_RETENTION_DAYS
            ),
        }
        return self.async_create_entry(
            title=DEFAULT_NAME,
            data={
                CONF_HOST: self._user_data[CONF_HOST],
                CONF_USERNAME: self._user_data[CONF_USERNAME],
                CONF_PASSWORD: self._user_data[CONF_PASSWORD],
            },
            options=options,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        return await self.async_step_user(import_data)


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow — change tier, groups, scan_interval, SSL, label refresh, history."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry
        self._pending_options: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        current = dict(self.config_entry.options or {})

        if user_input is not None:
            merged = {**current, **user_input}
            mode = merged.get(
                CONF_HISTORY_STORAGE_MODE,
                current.get(CONF_HISTORY_STORAGE_MODE, DEFAULT_HISTORY_STORAGE_MODE),
            )
            if mode != HISTORY_MODE_HOME_ASSISTANT and (
                CONF_HISTORY_SAMPLE_INTERVAL not in user_input
                or CONF_HISTORY_RETENTION_DAYS not in user_input
            ):
                # Archive mode selected; collect advanced settings before saving.
                self._pending_options = merged
                return await self.async_step_history_advanced()

            merged.setdefault(
                CONF_DISCOVERED_DATAPOINTS, current.get(CONF_DISCOVERED_DATAPOINTS, [])
            )
            merged.setdefault(CONF_ADHOC_OIDS, current.get(CONF_ADHOC_OIDS, []))
            return self.async_create_entry(title="", data=merged)

        # Build group selector from existing options; if empty, omit the field.
        existing_groups: list[str] = current.get(CONF_GROUPS) or []

        mode_selector = SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=m, label=m.replace("_", " ").title())
                    for m in HISTORY_STORAGE_MODES
                ],
                mode=SelectSelectorMode.LIST,
                translation_key=CONF_HISTORY_STORAGE_MODE,
            )
        )

        schema_dict: dict[Any, Any] = {
            vol.Optional(
                CONF_EXPERIENCE_LEVEL,
                default=current.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL),
            ): vol.In(list(EXPERIENCE_TIERS)),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
            vol.Optional(
                CONF_VERIFY_SSL,
                default=current.get(CONF_VERIFY_SSL, False),
            ): cv.boolean,
            vol.Optional(
                CONF_REFRESH_LABELS,
                default=current.get(CONF_REFRESH_LABELS, False),
            ): cv.boolean,
            vol.Optional(
                CONF_HISTORY_STORAGE_MODE,
                default=current.get(CONF_HISTORY_STORAGE_MODE, DEFAULT_HISTORY_STORAGE_MODE),
            ): mode_selector,
        }
        if existing_groups:
            # Use SelectSelector so HA resolves group labels from translation files.
            group_selector = SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(
                            value=g,
                            label=g.replace("_", " ").title(),
                        )
                        for g in existing_groups
                    ],
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                    translation_key="groups",
                )
            )
            schema_dict[vol.Optional(CONF_GROUPS, default=existing_groups)] = group_selector

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
        )

    async def async_step_history_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            merged = {**self._pending_options, **user_input}
            current = dict(self.config_entry.options or {})
            merged.setdefault(
                CONF_DISCOVERED_DATAPOINTS, current.get(CONF_DISCOVERED_DATAPOINTS, [])
            )
            merged.setdefault(CONF_ADHOC_OIDS, current.get(CONF_ADHOC_OIDS, []))
            return self.async_create_entry(title="", data=merged)

        current = dict(self.config_entry.options or {})
        return self.async_show_form(
            step_id="history_advanced",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_HISTORY_SAMPLE_INTERVAL,
                        default=current.get(
                            CONF_HISTORY_SAMPLE_INTERVAL, DEFAULT_HISTORY_SAMPLE_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_HISTORY_SAMPLE_INTERVAL,
                            max=MAX_HISTORY_SAMPLE_INTERVAL,
                        ),
                    ),
                    vol.Optional(
                        CONF_HISTORY_RETENTION_DAYS,
                        default=current.get(
                            CONF_HISTORY_RETENTION_DAYS, DEFAULT_HISTORY_RETENTION_DAYS
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_HISTORY_RETENTION_DAYS,
                            max=MAX_HISTORY_RETENTION_DAYS,
                        ),
                    ),
                }
            ),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _try_connect(
    host: str,
    username: str,
    password: str,
    verify_ssl: bool,
) -> dict[str, str]:
    """Attempt a single connection and return an errors dict (empty = success)."""
    client = WindhagerApiClient(
        host=host, username=username, password=password, verify_ssl=verify_ssl
    )
    try:
        async with client:
            await client.async_test_connection()
        return {}
    except WindhagerAuthError:
        _LOGGER.debug("Config flow: authentication failed for %s", host)
        return {"base": "invalid_auth"}
    except (WindhagerConnectionError, WindhagerTimeoutError) as err:
        _LOGGER.debug("Config flow: cannot connect to %s: %s", host, err)
        return {"base": "cannot_connect"}
    except Exception as err:
        _LOGGER.exception("Config flow: unexpected error for %s: %s", host, err)
        return {"base": "unknown"}


async def _probe_host(
    hass: HomeAssistant,
    host: str,
    username: str,
    password: str,
    verify_ssl: bool,
) -> tuple[str, dict[str, str]]:
    """Resolve the host URL and test the connection.

    When the user enters a bare IP or hostname (no scheme), HTTP (port 80) is
    tried first because Windhager RC7030 web servers commonly listen on plain
    HTTP. HTTPS is attempted as a fallback only if HTTP fails with a connection
    error (not an auth error — a 401 means the address is reachable).

    Returns a ``(resolved_host, errors)`` tuple. ``errors`` is empty on success.
    ``resolved_host`` always includes the scheme so the stored config entry URL
    is unambiguous.
    """
    host = host.strip().rstrip("/")
    has_scheme = host.startswith(("http://", "https://"))

    if has_scheme:
        errors = await _try_connect(host, username, password, verify_ssl)
        return host, errors

    # No scheme — try HTTP first, HTTPS as fallback
    for scheme in ("http", "https"):
        candidate = f"{scheme}://{host}"
        errors = await _try_connect(candidate, username, password, verify_ssl)
        if not errors:
            return candidate, {}
        # Auth failure or unknown error → no point trying the other scheme
        if errors.get("base") in ("invalid_auth", "unknown"):
            return candidate, errors

    # Both schemes failed with connection errors — report the last result
    return f"http://{host}", errors
