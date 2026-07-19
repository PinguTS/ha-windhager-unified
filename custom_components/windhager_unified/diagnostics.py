"""Diagnostics support for Windhager."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DISCOVERED_DATAPOINTS,
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
    CONF_HISTORY_RETENTION_DAYS,
    CONF_HISTORY_SAMPLE_INTERVAL,
    CONF_HISTORY_STORAGE_MODE,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_HISTORY_SAMPLE_INTERVAL,
    DEFAULT_HISTORY_STORAGE_MODE,
    DOMAIN,
    HISTORY_MODE_ALL_MARKED,
    HISTORY_MODE_CRITICAL,
    HISTORY_MODE_HOME_ASSISTANT,
)
from .coordinator import WindhagerCoordinator
from .discovery import KESSELWAHL_FAMILY
from .entity_metadata import HistoryImportance, parse_datapoint_metadata
from .history_writer import HistoryArchiveWriter

_LOGGER = logging.getLogger(__name__)

_REDACTED = {CONF_PASSWORD, CONF_USERNAME, "host"}


def _redact_archive_path(path: str) -> str:
    """Redact the config directory and entry ID from the archive path."""
    try:
        parts = path.split("/")
        if len(parts) >= 2:
            return f"[REDACTED]/{parts[-2]}/{parts[-1]}"
    except Exception:
        pass
    return "[REDACTED]"


def _count_eligible_datapoints(datapoints: list[dict[str, Any]], storage_mode: str) -> int:
    """Return how many coordinator datapoints are eligible for the archive."""
    if storage_mode == HISTORY_MODE_HOME_ASSISTANT:
        return 0
    count = 0
    for dp in datapoints:
        meta = parse_datapoint_metadata(dp)
        if not meta.history_importance_explicit:
            continue
        if (
            storage_mode == HISTORY_MODE_CRITICAL
            and meta.history_importance is HistoryImportance.CRITICAL
        ) or (
            storage_mode == HISTORY_MODE_ALL_MARKED
            and meta.history_importance
            in (HistoryImportance.CRITICAL, HistoryImportance.STANDARD, HistoryImportance.LOW)
        ):
            count += 1
    return count


def _metadata_summary(dp: dict[str, Any]) -> dict[str, Any]:
    """Return a redacted metadata summary for a datapoint."""
    meta = parse_datapoint_metadata(dp)
    return {
        "oid": dp.get("oid"),
        "key": dp.get("key"),
        "write_protected": dp.get("write_protected"),
        "data_role": str(meta.data_role.value),
        "temporal_semantics": str(meta.temporal_semantics.value),
        "model_role": str(meta.model_role.value),
        "history_importance": str(meta.history_importance.value),
        "device_class": meta.device_class.value if meta.device_class else None,
        "state_class": meta.state_class.value if meta.state_class else None,
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Credentials (host, username, password) are redacted.
    neuronId and other per-device network addresses are not included.
    """
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    options = entry.options or {}

    # Summarise discovered datapoints without leaking personal/network data:
    # emit only OID, group, fct_type and experience_minimum per entry.
    discovered_raw: list[dict[str, Any]] = options.get(CONF_DISCOVERED_DATAPOINTS) or []
    discovered_summary = [
        {
            "oid": dp.get("oid"),
            "group": dp.get("group"),
            "experience_minimum": dp.get("experience_minimum"),
        }
        for dp in discovered_raw
    ]

    # Collect the fctType values seen across discovered datapoints for quick diagnosis
    fct_types_seen = sorted(
        {dp.get("fct_type") for dp in discovered_raw if dp.get("fct_type") is not None}
    )

    # Boiler family from coordinator's discover result (stored in options)
    boiler_id: int | None = None
    for dp in discovered_raw:
        if dp.get("boiler_id") is not None:
            boiler_id = dp["boiler_id"]
            break
    boiler_name = KESSELWAHL_FAMILY.get(boiler_id or -1) if boiler_id is not None else None

    storage_mode = options.get(CONF_HISTORY_STORAGE_MODE, DEFAULT_HISTORY_STORAGE_MODE)
    sample_interval = options.get(CONF_HISTORY_SAMPLE_INTERVAL, DEFAULT_HISTORY_SAMPLE_INTERVAL)
    retention_days = options.get(CONF_HISTORY_RETENTION_DAYS, DEFAULT_HISTORY_RETENTION_DAYS)
    eligible_count = _count_eligible_datapoints(coordinator.datapoints, storage_mode)

    archive_data = hass.data.get(DOMAIN, {}).get(f"{entry.entry_id}_archive")
    writer: HistoryArchiveWriter | None = (
        archive_data.get("writer") if isinstance(archive_data, dict) else None
    )
    archive_info = None
    if writer is not None:
        try:
            archive_info = await writer.repository.async_get_archive_info(eligible_count)
        except Exception as err:
            _LOGGER.debug("Failed to collect archive diagnostics: %s", err)

    archive_diag: dict[str, Any] = {
        "history_storage_mode": storage_mode,
        "history_sample_interval": sample_interval,
        "history_retention_days": retention_days,
    }
    if archive_info is not None:
        archive_diag.update(
            {
                "database_path": _redact_archive_path(archive_info.database_path),
                "schema_version": archive_info.schema_version,
                "size_bytes": archive_info.size_bytes,
                "row_count": archive_info.row_count,
                "oldest_timestamp": (
                    archive_info.oldest_timestamp.isoformat()
                    if archive_info.oldest_timestamp
                    else None
                ),
                "newest_timestamp": (
                    archive_info.newest_timestamp.isoformat()
                    if archive_info.newest_timestamp
                    else None
                ),
                "last_successful_write": (
                    archive_info.last_successful_write.isoformat()
                    if archive_info.last_successful_write
                    else None
                ),
                "last_error": archive_info.last_error,
                "eligible_datapoint_count": archive_info.eligible_datapoint_count,
                "archived_datapoint_count": archive_info.archived_datapoint_count,
            }
        )
    else:
        archive_diag.update(
            {
                "database_path": None,
                "schema_version": None,
                "size_bytes": None,
                "row_count": None,
                "oldest_timestamp": None,
                "newest_timestamp": None,
                "last_successful_write": None,
                "last_error": None,
                "eligible_datapoint_count": eligible_count,
                "archived_datapoint_count": None,
            }
        )

    return {
        "config_entry": async_redact_data(dict(entry.data), _REDACTED),
        "options": async_redact_data(dict(options), _REDACTED),
        "experience": {
            "level": options.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL),
            "selected_groups": sorted(options.get(CONF_GROUPS) or []),
        },
        "boiler": {
            "id": boiler_id,
            "family": boiler_name,
        },
        "discovery": {
            "datapoints_count": len(discovered_raw),
            "fct_types_seen": fct_types_seen,
            "datapoints_summary": discovered_summary,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "datapoints_count": len(coordinator.datapoints),
            "restapi_groups": list(coordinator.restapi_endpoints.keys()),
            "restapi_endpoints_count": sum(len(v) for v in coordinator.restapi_endpoints.values()),
            "unknown_oids": sorted(coordinator.unknown_oids),
            "suspended_oids": sorted(coordinator._timeout_suspension.keys()),
            "metadata_summary": [_metadata_summary(dp) for dp in coordinator.datapoints],
            "data": coordinator.data,
        },
        "archive": archive_diag,
    }
