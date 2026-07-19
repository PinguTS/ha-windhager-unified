from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_ADHOC_OIDS,
    CONF_DISCOVERED_DATAPOINTS,
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
    CONF_HISTORY_RETENTION_DAYS,
    CONF_HISTORY_SAMPLE_INTERVAL,
    CONF_HISTORY_STORAGE_MODE,
    CONF_HOST,
    CONF_NODE_NAMES,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_HISTORY_SAMPLE_INTERVAL,
    DEFAULT_HISTORY_STORAGE_MODE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HISTORY_MODE_HOME_ASSISTANT,
    PLATFORMS,
)
from .coordinator import WindhagerCoordinator
from .exceptions import WindhagerAuthError, WindhagerConnectionError, WindhagerTimeoutError
from .history_repository import WindhagerHistoryRepository
from .history_writer import HistoryArchiveWriter
from .lon_entity_helpers import lon_unique_id
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


def _history_archive_path(hass: HomeAssistant, entry_id: str) -> Path:
    """Return the integration-owned SQLite archive path for a config entry."""
    return Path(hass.config.path(".storage")) / f"windhager_unified_history_{entry_id}.sqlite"


def _expected_unique_ids(entry: ConfigEntry, coordinator: WindhagerCoordinator) -> set[str]:
    """Return the set of unique_ids that should exist for this config entry.

    Covers LON datapoints and RestAPI endpoints. Entities whose unique_ids are
    not in this set are removed from the entity registry on setup/reload, so
    rescans or tier/group changes do not leave stale entities behind.
    """
    host = entry.data.get(CONF_HOST, "unknown")
    expected: set[str] = set()

    # LON-backed entities.
    for dp in coordinator.datapoints:
        oid = str(dp.get("oid", ""))
        key = str(dp.get("key", ""))
        if oid and key:
            expected.add(lon_unique_id(entry, oid, key))

    # RestAPI-backed entities.
    for _group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep in endpoints:
            endpoint = ep.get("endpoint", "")
            key = ep.get("key", "")
            if not endpoint or not key:
                continue
            entity_type = ep.get("entity_type", "sensor")
            if entity_type == "button":
                http_method = ep.get("http_method", "POST")
                expected.add(
                    hashlib.md5(f"{host}_{http_method}_{endpoint}_{key}".encode()).hexdigest()
                )
            else:
                expected.add(hashlib.md5(f"{host}_{endpoint}_{key}".encode()).hexdigest())

    # Static export button.
    expected.add(f"{entry.entry_id}_export_system_info")
    return expected


async def _async_cleanup_stale_entities(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: WindhagerCoordinator
) -> None:
    """Remove entity registry entries that no longer match active datapoints."""
    expected = _expected_unique_ids(entry, coordinator)
    registry = er.async_get(hass)
    removed = 0
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id not in expected:
            registry.async_remove(entity.entity_id)
            removed += 1
    if removed:
        _LOGGER.info(
            "Removed %d stale Windhager entities after rescan/tier/group change",
            removed,
        )


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
        node_names=options.get(CONF_NODE_NAMES),
        entry_id=entry.entry_id,
    )

    # Open session once; persists for the life of this config entry.
    await coordinator.api_client.async_init()
    await coordinator.async_initialize_catalog()
    await _async_cleanup_stale_entities(hass, entry, coordinator)

    # Use a cheap endpoint as a connectivity / auth probe instead of blocking on
    # the full first refresh. The full refresh can take minutes in expert mode and
    # would cause HA to cancel the setup task. Entities already tolerate empty
    # coordinator data by showing "unknown" until the first cycle completes.
    try:
        await coordinator.api_client.async_get_subnets()
    except (WindhagerAuthError, WindhagerConnectionError, WindhagerTimeoutError) as err:
        await coordinator.api_client.async_close()
        raise ConfigEntryNotReady(str(err)) from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await _async_setup_history_archive(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Kick off the first full refresh in the background so the integration
    # becomes available immediately while the slow expert-mode poll runs.
    entry.async_create_background_task(hass, coordinator.async_refresh(), "windhager_first_refresh")

    # Register set_datapoint service
    async def handle_set_datapoint(call: ServiceCall) -> None:
        oid: str = call.data["oid"]
        value: str = call.data["value"]
        oid_parts = [p for p in str(oid).strip().replace(".", "/").split("/") if p]
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
        parts = [p for p in str(call.data["oid"]).strip().replace(".", "/").split("/") if p]
        oid = "/".join(parts)
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


async def _async_setup_history_archive(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: WindhagerCoordinator,
) -> None:
    """Create and start the dedicated history archive if the user enabled it.

    In ``home_assistant`` mode no archive is opened. Archive failures are
    isolated so the rest of the integration still loads.
    """
    options = entry.options or {}
    storage_mode = options.get(CONF_HISTORY_STORAGE_MODE, DEFAULT_HISTORY_STORAGE_MODE)
    if storage_mode == HISTORY_MODE_HOME_ASSISTANT:
        return

    sample_interval = options.get(CONF_HISTORY_SAMPLE_INTERVAL, DEFAULT_HISTORY_SAMPLE_INTERVAL)
    retention_days = options.get(CONF_HISTORY_RETENTION_DAYS, DEFAULT_HISTORY_RETENTION_DAYS)

    repository = WindhagerHistoryRepository(
        hass=hass,
        database_path=_history_archive_path(hass, entry.entry_id),
        config_entry_id=entry.entry_id,
    )
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repository,
        config_entry_id=entry.entry_id,
        storage_mode=storage_mode,
        sample_interval=sample_interval,
    )

    try:
        await repository.async_initialize()
        await writer.async_start(coordinator.datapoints)
    except Exception as err:
        _LOGGER.error(
            "Failed to initialize history archive for %s: %s. Normal polling continues.",
            entry.entry_id,
            err,
        )
        await repository.async_close()
        return

    async def _process_update() -> None:
        await writer.async_process_update(coordinator.data, coordinator.datapoints)

    cancel_listener = coordinator.async_add_listener(_process_update)

    async def _cleanup(_now: datetime | None = None) -> None:
        try:
            await repository.async_cleanup(retention_days)
        except Exception as err:
            _LOGGER.error("History archive cleanup failed: %s", err)

    # Schedule cleanup once per day. The first run happens after the interval.
    cancel_cleanup = async_track_time_interval(
        hass, _cleanup, timedelta(days=1), name=f"windhager_history_cleanup_{entry.entry_id}"
    )

    # Store archive lifecycle objects under a separate key so services that
    # expect the coordinator directly continue to work.
    hass.data[DOMAIN][f"{entry.entry_id}_archive"] = {
        "repository": repository,
        "writer": writer,
        "cancel_listener": cancel_listener,
        "cancel_cleanup": cancel_cleanup,
    }


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options updates by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: WindhagerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api_client.async_close()

        archive_key = f"{entry.entry_id}_archive"
        archive_data = hass.data[DOMAIN].pop(archive_key, None)
        if archive_data is not None:
            writer: HistoryArchiveWriter | None = archive_data.get("writer")
            repository: WindhagerHistoryRepository | None = archive_data.get("repository")
            cancel_listener = archive_data.get("cancel_listener")
            cancel_cleanup = archive_data.get("cancel_cleanup")
            if writer is not None:
                await writer.async_stop()
            if cancel_listener is not None:
                cancel_listener()
            if cancel_cleanup is not None:
                cancel_cleanup()
            if repository is not None:
                await repository.async_close()

        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, "set_datapoint")
            hass.services.async_remove(DOMAIN, "add_datapoint")
            hass.services.async_remove(DOMAIN, "export_system_info")

    return unload_ok
