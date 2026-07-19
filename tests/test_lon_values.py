"""Tests for lon_values helper module."""

from __future__ import annotations

from datetime import date, time

from custom_components.windhager_unified.lon_values import (
    format_lon_time,
    is_date_datapoint,
    is_datetime_datapoint,
    is_time_datapoint,
    is_writable_time_datapoint,
    parse_lon_datetime_value,
)

# ---------------------------------------------------------------------------
# is_datetime_datapoint / is_date_datapoint / is_time_datapoint
# ---------------------------------------------------------------------------


def test_is_datetime_datapoint_unit_id_20():
    assert is_datetime_datapoint({"unit_id": 20}) is True
    assert is_date_datapoint({"unit_id": 20}) is True
    assert is_time_datapoint({"unit_id": 20}) is False


def test_is_datetime_datapoint_unit_id_21():
    assert is_datetime_datapoint({"unit_id": 21}) is True
    assert is_date_datapoint({"unit_id": 21}) is False
    assert is_time_datapoint({"unit_id": 21}) is True


def test_is_datetime_datapoint_other_unit_id():
    assert is_datetime_datapoint({"unit_id": 1}) is False
    assert is_datetime_datapoint({"unit_id": 0}) is False
    assert is_datetime_datapoint({"unit_id": -1}) is False
    assert is_date_datapoint({"unit_id": 1}) is False
    assert is_time_datapoint({"unit_id": 1}) is False


def test_is_datetime_datapoint_legacy_unit_string_20():
    """Catalogue entries that pre-date unit_id cleanup still have unit: '20'."""
    assert is_datetime_datapoint({"unit": "20"}) is True
    assert is_date_datapoint({"unit": "20"}) is True
    assert is_time_datapoint({"unit": "20"}) is False


def test_is_datetime_datapoint_legacy_unit_string_21():
    assert is_datetime_datapoint({"unit": "21"}) is True
    assert is_date_datapoint({"unit": "21"}) is False
    assert is_time_datapoint({"unit": "21"}) is True


def test_is_datetime_datapoint_unit_id_takes_precedence():
    """unit_id is checked first; legacy unit string is ignored when unit_id present."""
    assert is_datetime_datapoint({"unit_id": 1, "unit": "20"}) is False
    assert is_datetime_datapoint({"unit_id": 20, "unit": "1"}) is True
    assert is_date_datapoint({"unit_id": 20, "unit": "1"}) is True
    assert is_time_datapoint({"unit_id": 21, "unit": "1"}) is True


def test_is_datetime_datapoint_no_fields():
    assert is_datetime_datapoint({}) is False
    assert is_datetime_datapoint({"unit": "°C"}) is False


# ---------------------------------------------------------------------------
# is_writable_time_datapoint
# ---------------------------------------------------------------------------


def test_writable_time_requires_unit_id_21_and_not_protected():
    assert is_writable_time_datapoint({"unit_id": 21, "write_protected": False}) is True


def test_writable_time_rejected_when_write_protected():
    assert is_writable_time_datapoint({"unit_id": 21, "write_protected": True}) is False


def test_writable_time_rejected_when_unverified():
    dp = {"unit_id": 21, "write_protected": False, "unverified": True}
    assert is_writable_time_datapoint(dp) is False


def test_writable_time_rejected_for_date():
    assert is_writable_time_datapoint({"unit_id": 20, "write_protected": False}) is False


# ---------------------------------------------------------------------------
# parse_lon_datetime_value — date (unit_id 20)
# ---------------------------------------------------------------------------

_DATE_DP = {"unit_id": 20}
_TIME_DP = {"unit_id": 21}


def test_parse_date_valid():
    result = parse_lon_datetime_value("18.05.2026", _DATE_DP)
    assert isinstance(result, date)
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 18


def test_parse_date_invalid_format():
    assert parse_lon_datetime_value("2026-05-18", _DATE_DP) is None


def test_parse_time_valid():
    result = parse_lon_datetime_value("16:53", _TIME_DP)
    assert isinstance(result, time)
    assert result.hour == 16
    assert result.minute == 53
    assert result.second == 0


def test_parse_time_invalid_format():
    assert parse_lon_datetime_value("16:53:00", _TIME_DP) is None


# ---------------------------------------------------------------------------
# parse_lon_datetime_value — blank / hyphen / None
# ---------------------------------------------------------------------------


def test_parse_none_value():
    assert parse_lon_datetime_value(None, _DATE_DP) is None


def test_parse_empty_string():
    assert parse_lon_datetime_value("", _DATE_DP) is None


def test_parse_hyphen():
    assert parse_lon_datetime_value("-", _DATE_DP) is None
    assert parse_lon_datetime_value(" - ", _DATE_DP) is None


def test_parse_whitespace():
    assert parse_lon_datetime_value("   ", _TIME_DP) is None


# ---------------------------------------------------------------------------
# parse_lon_datetime_value — legacy unit string fallback
# ---------------------------------------------------------------------------


def test_parse_date_via_legacy_unit_string():
    dp = {"unit": "20"}
    result = parse_lon_datetime_value("01.01.2024", dp)
    assert isinstance(result, date)
    assert result.year == 2024


def test_parse_time_via_legacy_unit_string():
    dp = {"unit": "21"}
    result = parse_lon_datetime_value("08:00", dp)
    assert isinstance(result, time)
    assert result.hour == 8


# ---------------------------------------------------------------------------
# format_lon_time
# ---------------------------------------------------------------------------


def test_format_lon_time():
    assert format_lon_time(time(16, 53)) == "16:53"
    assert format_lon_time(time(8, 5)) == "08:05"
    assert format_lon_time(time(0, 0)) == "00:00"
