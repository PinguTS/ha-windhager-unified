"""Tests for lon_values helper module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from custom_components.windhager_unified.lon_values import (
    is_datetime_datapoint,
    parse_lon_datetime_value,
)

_UTC = timezone.utc

# ---------------------------------------------------------------------------
# is_datetime_datapoint
# ---------------------------------------------------------------------------


def test_is_datetime_datapoint_unit_id_20():
    assert is_datetime_datapoint({"unit_id": 20}) is True


def test_is_datetime_datapoint_unit_id_21():
    assert is_datetime_datapoint({"unit_id": 21}) is True


def test_is_datetime_datapoint_other_unit_id():
    assert is_datetime_datapoint({"unit_id": 1}) is False
    assert is_datetime_datapoint({"unit_id": 0}) is False
    assert is_datetime_datapoint({"unit_id": -1}) is False


def test_is_datetime_datapoint_legacy_unit_string_20():
    """Catalogue entries that pre-date unit_id cleanup still have unit: '20'."""
    assert is_datetime_datapoint({"unit": "20"}) is True


def test_is_datetime_datapoint_legacy_unit_string_21():
    assert is_datetime_datapoint({"unit": "21"}) is True


def test_is_datetime_datapoint_unit_id_takes_precedence():
    """unit_id is checked first; legacy unit string is ignored when unit_id present."""
    assert is_datetime_datapoint({"unit_id": 1, "unit": "20"}) is False
    assert is_datetime_datapoint({"unit_id": 20, "unit": "1"}) is True


def test_is_datetime_datapoint_no_fields():
    assert is_datetime_datapoint({}) is False
    assert is_datetime_datapoint({"unit": "°C"}) is False


# ---------------------------------------------------------------------------
# parse_lon_datetime_value — date (unit_id 20)
# ---------------------------------------------------------------------------

_DATE_DP = {"unit_id": 20}
_TIME_DP = {"unit_id": 21}

_FIXED_NOW = datetime(2026, 5, 18, 12, 0, tzinfo=_UTC)
_FIXED_AS_LOCAL = lambda naive: naive.replace(tzinfo=_UTC)  # noqa: E731


def test_parse_date_valid():
    with patch(
        "custom_components.windhager_unified.lon_values.dt_util.as_local",
        side_effect=_FIXED_AS_LOCAL,
    ):
        result = parse_lon_datetime_value("18.05.2026", _DATE_DP)
    assert isinstance(result, datetime)
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 18
    assert result.tzinfo is not None


def test_parse_date_invalid_format():
    assert parse_lon_datetime_value("2026-05-18", _DATE_DP) is None


def test_parse_time_valid():
    with (
        patch(
            "custom_components.windhager_unified.lon_values.dt_util.now",
            return_value=_FIXED_NOW,
        ),
        patch(
            "custom_components.windhager_unified.lon_values.dt_util.as_local",
            side_effect=_FIXED_AS_LOCAL,
        ),
    ):
        result = parse_lon_datetime_value("16:53", _TIME_DP)
    assert isinstance(result, datetime)
    assert result.hour == 16
    assert result.minute == 53
    assert result.date().year == 2026
    assert result.tzinfo is not None


def test_parse_time_invalid_format():
    with patch(
        "custom_components.windhager_unified.lon_values.dt_util.now",
        return_value=_FIXED_NOW,
    ):
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
    with patch(
        "custom_components.windhager_unified.lon_values.dt_util.as_local",
        side_effect=_FIXED_AS_LOCAL,
    ):
        result = parse_lon_datetime_value("01.01.2024", dp)
    assert result is not None
    assert result.year == 2024


def test_parse_time_via_legacy_unit_string():
    dp = {"unit": "21"}
    with (
        patch(
            "custom_components.windhager_unified.lon_values.dt_util.now",
            return_value=_FIXED_NOW,
        ),
        patch(
            "custom_components.windhager_unified.lon_values.dt_util.as_local",
            side_effect=_FIXED_AS_LOCAL,
        ),
    ):
        result = parse_lon_datetime_value("08:00", dp)
    assert result is not None
    assert result.hour == 8
