"""Helpers for classifying and parsing Windhager LON datapoint values.

ASSUMPTION: Windhager unit_id 20 encodes calendar dates in DD.MM.YYYY format and
unit_id 21 encodes wall-clock times in HH:MM format.  This is inferred from the
min_value/max_value patterns in oids.yaml (e.g. "01.01.1900" / "31.12.2078" for
unit_id 20) and from live device observations.  The Swagger documentation for
/api/1.0/datapoint describes `value` as an opaque string and does not enumerate
unitId semantics — this mapping is therefore an assumption, not a documented fact.

    10|Risk: a future firmware version could change the format.  On parse failure the
functions return None so the sensor shows "Unknown" rather than crashing.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Windhager unit_id values that carry date or time strings instead of numbers.
DATE_UNIT_ID = 20  # DD.MM.YYYY
TIME_UNIT_ID = 21  # HH:MM


def _resolve_unit_id(datapoint: dict[str, Any]) -> int:
    """Return the canonical unit_id for a datapoint, or -1 if unknown."""
    unit_id = datapoint.get("unit_id")
    if unit_id is not None:
        return int(unit_id)
    unit = str(datapoint.get("unit", "")).strip()
    if unit == "20":
        return DATE_UNIT_ID
    if unit == "21":
        return TIME_UNIT_ID
    return -1


def is_datetime_datapoint(datapoint: dict[str, Any]) -> bool:
    """Return True when a datapoint carries a date or time value.

    Checks unit_id first (authoritative); falls back to the legacy ``unit``
    string ('20' / '21') that some older catalogue entries store.
    """
    return _resolve_unit_id(datapoint) in (DATE_UNIT_ID, TIME_UNIT_ID)


def is_date_datapoint(datapoint: dict[str, Any]) -> bool:
    """Return True when a datapoint carries a calendar date value (unit_id 20)."""
    return _resolve_unit_id(datapoint) == DATE_UNIT_ID


def is_time_datapoint(datapoint: dict[str, Any]) -> bool:
    """Return True when a datapoint carries a wall-clock time value (unit_id 21)."""
    return _resolve_unit_id(datapoint) == TIME_UNIT_ID


def is_writable_time_datapoint(datapoint: dict[str, Any]) -> bool:
    """Return True for a writable time datapoint that should become a TimeEntity.

    TimeEntity is an editable UI control, so write-protected or unverified time
    values must stay as plain string sensors instead.
    """
    if not is_time_datapoint(datapoint):
        return False
    if datapoint.get("write_protected", True):
        return False
    return not datapoint.get("unverified")


def parse_lon_datetime_value(value: Any, datapoint: dict[str, Any]) -> date | time | None:
    """Parse a raw LON date/time string to a Python date or time object.

    Returns None for blank/hyphen placeholders and on any parse failure.

    For date values (unit_id 20): a datetime.date.
    For time values (unit_id 21): a datetime.time without a date component,
    so the state does not change every day at midnight.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw == "-":
        return None

    uid = _resolve_unit_id(datapoint)
    if uid == DATE_UNIT_ID:
        return _parse_date(raw)
    if uid == TIME_UNIT_ID:
        return _parse_time(raw)
    return None


def _parse_date(raw: str) -> date | None:
    try:
        return datetime.strptime(raw, "%d.%m.%Y").date()
    except ValueError:
        _LOGGER.debug("lon_values: could not parse date %r", raw)
        return None


def _parse_time(raw: str) -> time | None:
    try:
        return datetime.strptime(raw, "%H:%M").time()
    except ValueError:
        _LOGGER.debug("lon_values: could not parse time %r", raw)
        return None


def format_lon_time(value: time) -> str:
    """Format a datetime.time as the HH:MM string the API expects.

    ASSUMPTION: the device accepts wall-clock time writes in the same HH:MM
    format that GET responses return.  Swagger documents PUT /api/1.0/datapoint
    value as an opaque string, so this format is an assumption, not a documented
    contract.  If the firmware rejects it, the write fails visibly.
    """
    return value.strftime("%H:%M")
