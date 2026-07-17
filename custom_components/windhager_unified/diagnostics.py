"""Diagnostics support for Windhager."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DISCOVERED_DATAPOINTS,
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_EXPERIENCE_LEVEL,
    DOMAIN,
)
from .coordinator import WindhagerCoordinator
from .discovery import KESSELWAHL_FAMILY
from .entity_metadata import parse_datapoint_metadata

_REDACTED = {CONF_PASSWORD, CONF_USERNAME, "host"}


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
            "metadata_summary": [_metadata_summary(dp) for dp in coordinator.datapoints],
            "data": coordinator.data,
        },
    }
