"""Shared helpers for LON-backed Home Assistant entities."""

from __future__ import annotations

import hashlib
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo

from .coordinator import WindhagerCoordinator
from .entity_roles import resolve_role


def lon_unique_id(entry: ConfigEntry, oid: str, key: str) -> str:
    """Stable unique_id used across all LON entity platforms."""
    host = entry.data.get("host", "unknown")
    return hashlib.md5(f"{host}_{oid}_{key}".encode()).hexdigest()


def lon_suggested_object_id(key: str) -> str:
    """Stable entity registry slug from the datapoint key."""
    return key.replace(".", "_")


def lon_device_info(
    coordinator: WindhagerCoordinator,
    entry: ConfigEntry,
    datapoint: dict[str, Any],
) -> DeviceInfo:
    """Return cached function-block DeviceInfo for a datapoint."""
    return coordinator.get_function_block_device_info(entry.entry_id, datapoint)


def iter_lon_datapoints_by_role(
    coordinator: WindhagerCoordinator,
    *roles: str,
) -> list[dict[str, Any]]:
    """Return datapoints whose resolved role is in ``roles``."""
    out: list[dict[str, Any]] = []
    for dp in coordinator.datapoints:
        oid = str(dp.get("oid", ""))
        role = resolve_role(dp, has_enum=coordinator.has_enum_labels(oid))
        if role in roles:
            out.append(dp)
    return out
