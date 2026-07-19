"""Classify LON datapoints into Home Assistant entity roles and platforms."""

from __future__ import annotations

from typing import Any

from .const import (
    DEFAULT_COMMAND_VALUE,
    ROLE_COMMAND,
    ROLE_CONFIG,
    ROLE_DIAGNOSTIC,
    ROLE_MEASUREMENT,
)
from .lon_values import is_datetime_datapoint

# Identity label substrings (en/de) -> DeviceInfo field name.
_IDENTITY_DEVICE_INFO_FIELDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("software version", "softwareversion"), "sw_version"),
    (("hardware version", "version hw"), "hw_version"),
    (("kesseltyp", "kesseltype", "boiler type"), "model"),
    (("serial", "seriennummer"), "serial_number"),
)


def _label_text(datapoint: dict[str, Any]) -> str:
    i18n = datapoint.get("i18n") or {}
    parts = [str(i18n.get(lang, "")) for lang in ("en", "de")]
    return " ".join(p.lower() for p in parts if p)


def identity_device_info_field(datapoint: dict[str, Any]) -> str | None:
    """Return DeviceInfo field for identity datapoints, or None."""
    text = _label_text(datapoint)
    for needles, field in _IDENTITY_DEVICE_INFO_FIELDS:
        if any(n in text for n in needles):
            return field
    explicit = datapoint.get("device_info_field")
    if isinstance(explicit, str) and explicit:
        return explicit
    return None


def _parse_bound(value: Any) -> float | None:
    if value is None:
        return None
    raw = str(value).strip().strip("'\"")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _has_usable_range(datapoint: dict[str, Any]) -> bool:
    mn = _parse_bound(datapoint.get("min_value"))
    mx = _parse_bound(datapoint.get("max_value"))
    if mn is None or mx is None:
        return False
    if datapoint.get("unverified"):
        return False
    return not (mn == mx == 0.0)


def _is_boolean_range(datapoint: dict[str, Any]) -> bool:
    mn = _parse_bound(datapoint.get("min_value"))
    mx = _parse_bound(datapoint.get("max_value"))
    return mn == 0.0 and mx == 1.0


def resolve_role(datapoint: dict[str, Any], *, has_enum: bool = False) -> str:
    """Return the HA entity role for a LON datapoint."""
    explicit = datapoint.get("entity_role")
    if explicit in (ROLE_MEASUREMENT, ROLE_DIAGNOSTIC, ROLE_CONFIG, ROLE_COMMAND):
        return explicit

    if identity_device_info_field(datapoint) is not None:
        return ROLE_DIAGNOSTIC

    if datapoint.get("write_protected", True):
        return ROLE_MEASUREMENT

    if datapoint.get("unverified"):
        return ROLE_MEASUREMENT

    if is_datetime_datapoint(datapoint):
        return ROLE_MEASUREMENT

    if has_enum or _has_usable_range(datapoint):
        return ROLE_CONFIG

    return ROLE_MEASUREMENT


def resolve_config_platform(
    datapoint: dict[str, Any],
    *,
    has_enum: bool = False,
    numeric_format_confirmed: bool = False,
) -> str | None:
    """Return HA platform for a config-role datapoint, or None if not writable."""
    if resolve_role(datapoint, has_enum=has_enum) != ROLE_CONFIG:
        return None

    if is_datetime_datapoint(datapoint):
        return None

    if has_enum:
        return "select"

    if _is_boolean_range(datapoint):
        return "switch"

    if _has_usable_range(datapoint) and numeric_format_confirmed:
        return "number"

    return None


def infer_decimal_places(raw: str) -> int | None:
    """Infer decimal places from a raw device string."""
    text = raw.strip()
    if not text or all(c in "-." for c in text):
        return None
    if "." in text:
        return len(text.split(".", 1)[1])
    return 0


def numeric_format_confirmed(datapoint: dict[str, Any], raw_value: Any) -> bool:
    """Return True when a numeric write format can be inferred from a live reading.

    ASSUMPTION C: the device accepts writes using the same decimal precision as
    the GET response string.  Until a parseable numeric raw value is observed,
    numeric config datapoints stay read-only sensors.
    """
    if raw_value is None:
        return False
    raw = str(raw_value).strip()
    if not raw or all(c in "-." for c in raw):
        return False
    try:
        float(raw.replace(",", "."))
    except ValueError:
        return False
    return infer_decimal_places(raw) is not None


def format_write_value(
    datapoint: dict[str, Any],
    value: float | int | str | bool,
    *,
    raw_format: str | None = None,
) -> str:
    """Format a value for PUT /api/1.0/datapoint (opaque string per Swagger)."""
    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, str):
        return value

    step = datapoint.get("step")
    decimals: int | None = None
    if raw_format is not None:
        decimals = infer_decimal_places(raw_format)
    if decimals is None and step is not None:
        step_str = str(step).strip()
        decimals = len(step_str.split(".", 1)[1].rstrip("0")) or 0 if "." in step_str else 0

    try:
        num = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"Cannot format non-numeric value {value!r}") from err

    if decimals is None:
        if float(num).is_integer():
            return str(int(num))
        return str(num)

    formatted = f"{num:.{decimals}f}"
    if decimals == 0:
        return str(int(round(num)))
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def command_write_value(datapoint: dict[str, Any]) -> str:
    """Return the PUT value for a command-role datapoint."""
    value = datapoint.get("command_value", DEFAULT_COMMAND_VALUE)
    return str(value)


def validate_numeric_in_range(datapoint: dict[str, Any], value: float) -> None:
    """Raise ValueError when value is outside documented min/max."""
    mn = _parse_bound(datapoint.get("min_value"))
    mx = _parse_bound(datapoint.get("max_value"))
    if mn is not None and value < mn:
        raise ValueError(f"Value {value} below minimum {mn}")
    if mx is not None and value > mx:
        raise ValueError(f"Value {value} above maximum {mx}")


def parse_catalog_float(value: Any) -> float | None:
    """Parse min/max/step from catalogue strings."""
    if value is None:
        return None
    try:
        return float(str(value).strip().strip("'\""))
    except ValueError:
        return None
