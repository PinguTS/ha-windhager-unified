"""Tests for the central entity metadata parser."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from custom_components.windhager_unified.entity_metadata import (
    DataRole,
    HistoryImportance,
    ModelRole,
    TemporalSemantics,
    enabled_default,
    parse_datapoint_metadata,
    semantic_state_attributes,
)

# ---------------------------------------------------------------------------
# Enum parsing
# ---------------------------------------------------------------------------


def test_parse_full_measurement_metadata():
    dp = {
        "oid": "1/16/0/0/15/0",
        "key": "lon_1_16_0_0_15_0",
        "device_class": "temperature",
        "state_class": "measurement",
        "unit": "°C",
        "suggested_display_precision": 1,
        "icon": "mdi:storage-tank",
        "entity_category": "diagnostic",
        "enabled_by_default": True,
        "data_role": "measurement",
        "temporal_semantics": "sampled",
        "model_role": "feature",
        "history_importance": "critical",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.device_class is SensorDeviceClass.TEMPERATURE
    assert meta.state_class is SensorStateClass.MEASUREMENT
    assert meta.unit == "°C"
    assert meta.suggested_display_precision == 1
    assert meta.icon == "mdi:storage-tank"
    assert meta.entity_category is EntityCategory.DIAGNOSTIC
    assert meta.enabled_by_default is True
    assert meta.data_role is DataRole.MEASUREMENT
    assert meta.temporal_semantics is TemporalSemantics.SAMPLED
    assert meta.model_role is ModelRole.FEATURE
    assert meta.history_importance is HistoryImportance.CRITICAL


def test_parse_setpoint_with_null_state_class():
    dp = {
        "oid": "1/15/0/1/1/0",
        "key": "lon_1_15_0_1_1_0",
        "device_class": "temperature",
        "state_class": None,
        "unit": "°C",
        "data_role": "setpoint",
        "temporal_semantics": "step",
        "model_role": "control",
        "history_importance": "critical",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.device_class is SensorDeviceClass.TEMPERATURE
    assert meta.state_class is None
    assert meta.data_role is DataRole.SETPOINT
    assert meta.temporal_semantics is TemporalSemantics.STEP
    assert meta.model_role is ModelRole.CONTROL


def test_parse_configuration_metadata():
    dp = {
        "oid": "example/heating/curve/footpoint",
        "key": "example_footpoint",
        "device_class": "temperature",
        "state_class": None,
        "unit": "°C",
        "data_role": "configuration",
        "temporal_semantics": "step",
        "model_role": "context",
        "history_importance": "critical",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.data_role is DataRole.CONFIGURATION
    assert meta.state_class is None


def test_parse_operating_state_metadata():
    dp = {
        "oid": "1/65/0/2/1/0",
        "key": "lon_1_65_0_2_1_0",
        "state_class": None,
        "data_role": "operating_state",
        "temporal_semantics": "event",
        "model_role": "event",
        "history_importance": "critical",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.data_role is DataRole.OPERATING_STATE
    assert meta.state_class is None
    assert meta.temporal_semantics is TemporalSemantics.EVENT


def test_parse_actuator_state_metadata():
    dp = {
        "oid": "1/16/0/22/50/0",
        "key": "lon_1_16_0_22_50_0",
        "state_class": None,
        "data_role": "actuator_state",
        "temporal_semantics": "event",
        "model_role": "event",
        "history_importance": "critical",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.data_role is DataRole.ACTUATOR_STATE


# ---------------------------------------------------------------------------
# Defaults and missing fields
# ---------------------------------------------------------------------------


def test_parse_missing_fields_use_defaults():
    dp = {"oid": "1/2/3/4/5/6", "key": "lon_test"}
    meta = parse_datapoint_metadata(dp)
    assert meta.device_class is None
    assert meta.state_class is None
    assert meta.unit is None
    assert meta.data_role is DataRole.UNKNOWN
    assert meta.temporal_semantics is TemporalSemantics.NONE
    assert meta.model_role is ModelRole.UNKNOWN
    assert meta.history_importance is HistoryImportance.STANDARD


def test_enabled_default_explicit_yaml_wins():
    meta = parse_datapoint_metadata({"enabled_by_default": False})
    assert enabled_default(meta, "essential") is False


def test_enabled_default_falls_back_to_tier():
    meta = parse_datapoint_metadata({})
    assert enabled_default(meta, "essential") is True
    assert enabled_default(meta, "expert") is False
    assert enabled_default(meta, "service") is False


# ---------------------------------------------------------------------------
# Validation warnings (never fatal)
# ---------------------------------------------------------------------------


def test_invalid_device_class_logs_warning(caplog):
    dp = {"oid": "1/0/0/0/0/0", "device_class": "not_a_real_class"}
    with caplog.at_level(logging.WARNING):
        meta = parse_datapoint_metadata(dp)
    assert meta.device_class is None
    assert any("device_class" in m and "1/0/0/0/0/0" in m for m in caplog.messages)


def test_invalid_state_class_logs_warning(caplog):
    dp = {"oid": "1/0/0/0/0/0", "state_class": "not_a_class"}
    with caplog.at_level(logging.WARNING):
        meta = parse_datapoint_metadata(dp)
    assert meta.state_class is None
    assert any("state_class" in m and "1/0/0/0/0/0" in m for m in caplog.messages)


def test_invalid_enum_value_logs_warning_and_defaults(caplog):
    dp = {
        "oid": "1/0/0/0/0/0",
        "data_role": "nonsense",
        "temporal_semantics": "nonsense",
        "model_role": "nonsense",
        "history_importance": "nonsense",
    }
    with caplog.at_level(logging.WARNING):
        meta = parse_datapoint_metadata(dp)
    assert meta.data_role is DataRole.UNKNOWN
    assert meta.temporal_semantics is TemporalSemantics.NONE
    assert meta.model_role is ModelRole.UNKNOWN
    assert meta.history_importance is HistoryImportance.STANDARD
    assert any("data_role" in m and "1/0/0/0/0/0" in m for m in caplog.messages)


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------


def test_enum_device_class_drops_state_class_and_unit():
    dp = {
        "oid": "1/0/0/0/0/0",
        "device_class": "enum",
        "state_class": "measurement",
        "unit": "°C",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.device_class is SensorDeviceClass.ENUM
    assert meta.state_class is None
    assert meta.unit is None


def test_timestamp_device_class_drops_state_class_and_unit():
    dp = {
        "oid": "1/0/0/0/0/0",
        "device_class": "timestamp",
        "state_class": "measurement",
        "unit": "s",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.device_class is SensorDeviceClass.TIMESTAMP
    assert meta.state_class is None
    assert meta.unit is None


def test_total_state_class_on_temperature_dropped():
    dp = {
        "oid": "1/0/0/0/0/0",
        "device_class": "temperature",
        "state_class": "total_increasing",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.state_class is None


def test_forecast_measurement_state_class_dropped():
    dp = {
        "oid": "1/0/0/0/0/0",
        "data_role": "forecast",
        "state_class": "measurement",
    }
    meta = parse_datapoint_metadata(dp)
    assert meta.data_role is DataRole.FORECAST
    assert meta.state_class is None


def test_operating_state_sampled_warns():
    dp = {
        "oid": "1/0/0/0/0/0",
        "data_role": "operating_state",
        "temporal_semantics": "sampled",
    }
    meta = parse_datapoint_metadata(dp)
    assert any("operating_state" in w and "sampled" in w for w in meta.warnings)


def test_actuator_state_measurement_warns():
    dp = {
        "oid": "1/0/0/0/0/0",
        "data_role": "actuator_state",
        "state_class": "measurement",
    }
    meta = parse_datapoint_metadata(dp)
    assert any("actuator_state" in w for w in meta.warnings)


def test_critical_ignore_warns():
    dp = {
        "oid": "1/0/0/0/0/0",
        "history_importance": "critical",
        "model_role": "ignore",
    }
    meta = parse_datapoint_metadata(dp)
    assert any("critical" in w and "ignore" in w for w in meta.warnings)


# ---------------------------------------------------------------------------
# Semantic attributes
# ---------------------------------------------------------------------------


def test_semantic_state_attributes():
    dp = {"oid": "1/0/0/0/0/0", "write_protected": False}
    meta = parse_datapoint_metadata(dp)
    attrs = semantic_state_attributes(meta, dp)
    assert attrs["windhager_data_role"] == "unknown"
    assert attrs["windhager_temporal_semantics"] == "none"
    assert attrs["windhager_model_role"] == "unknown"
    assert attrs["windhager_history_importance"] == "standard"
    assert attrs["windhager_oid"] == "1/0/0/0/0/0"
    assert attrs["windhager_write_protected"] == "False"


# ---------------------------------------------------------------------------
# RestAPI endpoint parsing
# ---------------------------------------------------------------------------


def test_parse_restapi_endpoint_metadata():
    ep = {
        "endpoint": "/api/1.0/heartbeat",
        "key": "heartbeat.status",
        "data_role": "diagnostic",
        "temporal_semantics": "snapshot",
        "model_role": "context",
        "history_importance": "low",
    }
    meta = parse_datapoint_metadata(ep)
    assert meta.data_role is DataRole.DIAGNOSTIC
    assert meta.temporal_semantics is TemporalSemantics.SNAPSHOT
    assert semantic_state_attributes(meta, ep)["windhager_oid"] == "/api/1.0/heartbeat"
