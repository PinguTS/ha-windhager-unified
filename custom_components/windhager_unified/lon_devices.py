"""Home Assistant device grouping for LON function blocks."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .discovery import FUNCTION_TYPE_GROUPS, _group_label

# Static catalogue group slug -> friendly label (matches options selector).
_STATIC_GROUP_LABELS: dict[str, str] = {
    "boiler": "Boiler / Heat generator",
    "buffer": "Buffer / Shift valve",
    "central": "Central controller",
    "heating_circuit": "Heating circuit",
    "dhw": "Domestic hot water",
}


def parse_oid_prefix(oid: str) -> tuple[str, str, str] | None:
    """Return (subnet, node, fct) from a 6-part OID."""
    parts = str(oid).split("/")
    if len(parts) != 6:
        return None
    return parts[0], parts[1], parts[2]


def function_block_identifier(entry_id: str, oid: str) -> str | None:
    """Stable HA device identifier for a LON function block."""
    prefix = parse_oid_prefix(oid)
    if prefix is None:
        return None
    subnet, node, fct = prefix
    return f"{entry_id}_fb_{subnet}_{node}_{fct}"


def function_block_fallback_name(datapoint: dict[str, Any]) -> str:
    """Human-readable device name when discovery did not supply function_name."""
    fn = datapoint.get("function_name")
    if fn:
        return str(fn)

    fct_type = datapoint.get("fct_type")
    group = str(datapoint.get("group") or "")
    if fct_type is not None:
        try:
            fct_int = int(fct_type)
            group_id = FUNCTION_TYPE_GROUPS.get(fct_int, group or f"unknown_{fct_int}")
            return _group_label(fct_int, group_id, {})
        except (TypeError, ValueError):
            pass

    if group in _STATIC_GROUP_LABELS:
        return _STATIC_GROUP_LABELS[group]

    hint = datapoint.get("hint_node")
    if hint:
        return str(hint)

    prefix = parse_oid_prefix(str(datapoint.get("oid", "")))
    if prefix:
        return f"LON {prefix[1]}/{prefix[2]}"
    return "Windhager LON"


def build_function_block_device_info(
    entry_id: str,
    datapoint: dict[str, Any],
    *,
    sw_version: str | None = None,
    hw_version: str | None = None,
    model: str | None = None,
    serial_number: str | None = None,
) -> DeviceInfo:
    """Build DeviceInfo for one LON function block."""
    oid = str(datapoint.get("oid", ""))
    fb_id = function_block_identifier(entry_id, oid)
    name = function_block_fallback_name(datapoint)
    hint = datapoint.get("hint_node")

    info: DeviceInfo = {
        "identifiers": {(DOMAIN, fb_id or entry_id)},
        "name": name,
        "manufacturer": "Windhager",
        "via_device": (DOMAIN, entry_id),
    }
    if hint:
        info["model"] = str(hint)
    if model:
        info["model"] = model
    if sw_version:
        info["sw_version"] = sw_version
    if hw_version:
        info["hw_version"] = hw_version
    if serial_number:
        info["serial_number"] = serial_number
    return info


def hub_device_info(entry_id: str) -> DeviceInfo:
    """Top-level Windhager hub device."""
    return {
        "identifiers": {(DOMAIN, entry_id)},
        "name": "Windhager",
        "manufacturer": "Windhager",
    }
