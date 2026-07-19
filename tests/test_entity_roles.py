"""Tests for LON entity role classification."""

from __future__ import annotations

from custom_components.windhager_unified.const import (
    ROLE_COMMAND,
    ROLE_CONFIG,
    ROLE_DIAGNOSTIC,
    ROLE_MEASUREMENT,
)
from custom_components.windhager_unified.entity_roles import (
    command_write_value,
    format_write_value,
    identity_device_info_field,
    numeric_format_confirmed,
    resolve_config_platform,
    resolve_role,
)


def test_read_only_datapoint_is_measurement():
    dp = {"write_protected": True, "key": "k"}
    assert resolve_role(dp) == ROLE_MEASUREMENT


def test_unverified_writable_stays_measurement():
    dp = {
        "write_protected": False,
        "unverified": True,
        "min_value": "0",
        "max_value": "100",
    }
    assert resolve_role(dp) == ROLE_MEASUREMENT


def test_verified_writable_becomes_config():
    dp = {
        "write_protected": False,
        "min_value": "10.0",
        "max_value": "50.0",
        "step": "1.0",
    }
    assert resolve_role(dp) == ROLE_CONFIG
    assert resolve_config_platform(dp, has_enum=False, numeric_format_confirmed=True) == "number"


def test_boolean_writable_becomes_switch():
    dp = {"write_protected": False, "min_value": "0", "max_value": "1"}
    assert resolve_config_platform(dp, has_enum=False, numeric_format_confirmed=False) == "switch"


def test_enum_writable_becomes_select():
    dp = {"write_protected": False, "min_value": "0", "max_value": "3"}
    assert resolve_config_platform(dp, has_enum=True, numeric_format_confirmed=False) == "select"


def test_explicit_command_role():
    dp = {"entity_role": ROLE_COMMAND, "write_protected": False}
    assert resolve_role(dp) == ROLE_COMMAND


def test_identity_datapoint_is_diagnostic():
    dp = {
        "write_protected": True,
        "i18n": {"en": "Software version firing automate", "de": "Softwareversion"},
    }
    assert resolve_role(dp) == ROLE_DIAGNOSTIC
    assert identity_device_info_field(dp) == "sw_version"


def test_numeric_format_requires_live_reading():
    dp = {"min_value": "10.0", "max_value": "50.0"}
    assert numeric_format_confirmed(dp, None) is False
    assert numeric_format_confirmed(dp, "21.5") is True


def test_number_without_confirmed_format_stays_sensor_platform():
    dp = {
        "write_protected": False,
        "min_value": "10.0",
        "max_value": "50.0",
        "step": "0.5",
    }
    assert resolve_config_platform(dp, has_enum=False, numeric_format_confirmed=False) is None


def test_format_write_value_respects_raw_precision():
    dp = {"step": "0.1"}
    assert format_write_value(dp, 21.5, raw_format="21.5") == "21.5"


def test_command_write_value_default():
    assert command_write_value({}) == "1"
    assert command_write_value({"command_value": "2"}) == "2"
