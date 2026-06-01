from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ADHOC_OIDS,
    CONF_DISCOVERED_DATAPOINTS,
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import WindhagerCoordinator
from .exceptions import WindhagerAuthError, WindhagerConnectionError, WindhagerTimeoutError
from .migrate import async_migrate_entry  # noqa: F401 — HA migration hook

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _resolve_config_entry(hass: HomeAssistant, call: ServiceCall) -> ConfigEntry:
    """Pick the Windhager config entry for a service call."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        raise HomeAssistantError("No Windhager integration configured")
    entry_id = call.data.get("config_entry_id")
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise HomeAssistantError("Invalid config_entry_id")
        return entry
    if len(entries) == 1:
        return entries[0]
    raise HomeAssistantError(
        "Multiple Windhager integrations: specify config_entry_id in service data"
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Windhager from a config entry."""
    options = entry.options or {}
    coordinator = WindhagerCoordinator(
        hass=hass,
        host=entry.data[CONF_HOST],
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        verify_ssl=options.get(CONF_VERIFY_SSL, entry.data.get(CONF_VERIFY_SSL, True)),
        scan_interval=options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        ),
        experience_level=options.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL),
        groups=options.get(CONF_GROUPS),
        discovered_datapoints=options.get(CONF_DISCOVERED_DATAPOINTS),
        adhoc_oids=options.get(CONF_ADHOC_OIDS),
        entry_id=entry.entry_id,
    )

    # Open session once; persists for the life of this config entry.
    await coordinator.api_client.async_init()
    await coordinator.async_initialize_catalog()

    try:
        await coordinator.async_config_entry_first_refresh()
    except (WindhagerAuthError, WindhagerConnectionError, WindhagerTimeoutError) as err:
        await coordinator.api_client.async_close()
        raise ConfigEntryNotReady(str(err)) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register set_datapoint service
    async def handle_set_datapoint(call: ServiceCall) -> None:
        oid: str = call.data["oid"]
        value: str = call.data["value"]
        oid_parts = oid.replace(".", "/").split("/")
        if len(oid_parts) != 6:
            raise HomeAssistantError(
                f"Invalid OID '{oid}': expected 6 parts separated by '/' or '.'"
            )
        try:
            await coordinator.api_client.async_put_datapoint(oid_parts, value)
        except Exception as err:
            raise HomeAssistantError(f"Failed to set datapoint {oid}: {err}") from err

    hass.services.async_register(DOMAIN, "set_datapoint", handle_set_datapoint)

    async def handle_add_datapoint(call: ServiceCall) -> None:
        """Register an extra OID (GET datapoint); persists to options and reloads."""
        entry = _resolve_config_entry(hass, call)
        coord: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
        oid = str(call.data["oid"]).strip().replace(".", "/")
        parts = oid.split("/")
        if len(parts) != 6:
            raise HomeAssistantError(
                f"Invalid OID '{oid}': expected 6 parts separated by '/' or '.'"
            )
        group = str(call.data.get("group") or "boiler").strip() or "boiler"
        try:
            await coord.api_client.async_get_datapoint(parts)
        except Exception as err:
            raise HomeAssistantError(f"OID not readable on device: {err}") from err

        opts = dict(entry.options or {})
        adhoc_raw = list(opts.get(CONF_ADHOC_OIDS, []))
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in adhoc_raw:
            if isinstance(item, str):
                o = item.replace(".", "/")
                normalized.append({"oid": o, "group": "boiler"})
                seen.add(o)
            elif isinstance(item, dict) and item.get("oid"):
                o = str(item["oid"]).replace(".", "/")
                normalized.append({"oid": o, "group": str(item.get("group") or "boiler")})
                seen.add(o)
        if oid not in seen:
            normalized.append({"oid": oid, "group": group})
        opts[CONF_ADHOC_OIDS] = normalized
        hass.config_entries.async_update_entry(entry, options=opts)
        await hass.config_entries.async_reload(entry.entry_id)

    hass.services.async_register(DOMAIN, "add_datapoint", handle_add_datapoint)

    async def handle_export_system_info(call: ServiceCall) -> None:
        """Start a background LON export; returns immediately."""
        target_entry = _resolve_config_entry(hass, call)
        coord: WindhagerCoordinator = hass.data[DOMAIN][target_entry.entry_id]
        from .export import async_start_export

        try:
            await async_start_export(hass, coord)
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(DOMAIN, "export_system_info", handle_export_system_info)

    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: WindhagerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api_client.async_close()

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "set_datapoint")
            hass.services.async_remove(DOMAIN, "add_datapoint")
            hass.services.async_remove(DOMAIN, "export_system_info")

    return unload_ok
