"""Helpers for classifying and parsing Windhager LON datapoint values.

ASSUMPTION: Windhager unit_id 20 encodes calendar dates in DD.MM.YYYY format and
unit_id 21 encodes wall-clock times in HH:MM format.  This is inferred from the
min_value/max_value patterns in oids.yaml (e.g. "01.01.1900" / "31.12.2078" for
unit_id 20) and from live device observations.  The Swagger documentation for
/api/1.0/datapoint describes `value` as an opaque string and does not enumerate
unitId semantics — this mapping is therefore an assumption, not a documented fact.

Risk: a future firmware version could change the format.  On parse failure the
functions return None so the sensor shows "Unknown" rather than crashing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

# Assumption: dt_util.as_local(naive) converts a naive datetime to one with the
# HA default timezone attached. This is the correct HA idiom for producing
# local-timezone-aware datetimes without accessing the private _DEFAULT_TIME_ZONE.
# dt_util.now() gives the current local-aware time, used to infer today's date
# for HH:MM values that carry no date component on the wire.

# Windhager unit_id values that carry date or time strings instead of numbers.
_DATE_UNIT_ID = 20  # DD.MM.YYYY
_TIME_UNIT_ID = 21  # HH:MM


def is_datetime_datapoint(datapoint: dict[str, Any]) -> bool:
    """Return True when a datapoint carries a date or time value.

    Checks unit_id first (authoritative); falls back to the legacy ``unit``
    string ('20' / '21') that some older catalogue entries store.
    """
    unit_id = datapoint.get("unit_id")
    if unit_id is not None:
        return int(unit_id) in (_DATE_UNIT_ID, _TIME_UNIT_ID)
    unit = str(datapoint.get("unit", "")).strip()
    return unit in ("20", "21")


def parse_lon_datetime_value(value: Any, datapoint: dict[str, Any]) -> datetime | None:
    """Parse a raw LON date/time string to a timezone-aware datetime.

    Returns None for blank/hyphen placeholders and on any parse failure.
    The returned datetime is always timezone-aware (HA local timezone).

    For date values (unit_id 20): midnight of the given calendar day in local TZ.
    For time values (unit_id 21): the given wall-clock time on today's date in local TZ.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw == "-":
        return None

    unit_id = datapoint.get("unit_id")
    if unit_id is not None:
        uid = int(unit_id)
    else:
        unit = str(datapoint.get("unit", "")).strip()
        uid = _DATE_UNIT_ID if unit == "20" else (_TIME_UNIT_ID if unit == "21" else -1)

    if uid == _DATE_UNIT_ID:
        return _parse_date(raw)
    if uid == _TIME_UNIT_ID:
        return _parse_time(raw)
    return None


def _parse_date(raw: str) -> datetime | None:
    try:
        naive = datetime.strptime(raw, "%d.%m.%Y")
    except ValueError:
        _LOGGER.debug("lon_values: could not parse date %r", raw)
        return None
    return dt_util.as_local(naive)


def _parse_time(raw: str) -> datetime | None:
    try:
        parsed_time = datetime.strptime(raw, "%H:%M").time()
    except ValueError:
        _LOGGER.debug("lon_values: could not parse time %r", raw)
        return None
    today = dt_util.now().date()
    naive = datetime.combine(today, parsed_time)
    return dt_util.as_local(naive)
