"""Tests for sensor platform metadata wiring (HA + semantic)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from custom_components.windhager_unified.const import DOMAIN
from custom_components.windhager_unified.sensor import (
    WindhagerLONSensor,
    WindhagerLONSensorDescription,
    async_setup_entry,
)


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {"boiler_temp": 75.5, "pump": "1"}
    coordinator.has_enum_labels.return_value = False
    coordinator.get_function_block_device_info.return_value = {
        "identifiers": {(DOMAIN, "test_id_fb")},
        "name": "Boiler",
        "manufacturer": "Windhager",
        "via_device": (DOMAIN, "test_id"),
    }
    coordinator.lon_numeric_format_confirmed.return_value = False
    coordinator.get_entity_name = MagicMock(return_value="Test Name")
    coordinator.get_enum_options.return_value = []
    coordinator.get_enum_label.return_value = "On"
    coordinator.restapi_endpoints = {}
    return coordinator


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_id"
    entry.data = {"host": "http://test-host"}
    entry.options = {}
    return entry


def test_temperature_sensor_metadata_from_yaml(mock_coordinator, mock_entry):
    mock_coordinator.datapoints = [
        {
            "oid": "1/65/0/0/7/0",
            "key": "boiler_temp",
            "unit": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "suggested_display_precision": 1,
            "icon": "mdi:fire",
            "data_role": "measurement",
            "temporal_semantics": "sampled",
            "model_role": "feature",
            "history_importance": "critical",
            "i18n": {"en": "Boiler temp"},
            "experience_minimum": "essential",
            "write_protected": True,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = []
    asyncio.get_event_loop().run_until_complete(
        async_setup_entry(hass, mock_entry, lambda entities, **kw: added.extend(entities))
    )

    assert len(added) == 1
    sensor = added[0]
    desc = sensor.entity_description
    assert desc.device_class is SensorDeviceClass.TEMPERATURE
    assert desc.state_class is SensorStateClass.MEASUREMENT
    assert desc.native_unit_of_measurement == "°C"
    assert desc.suggested_display_precision == 1
    assert desc.icon == "mdi:fire"
    assert desc.entity_registry_enabled_default is True
    assert sensor.extra_state_attributes["windhager_data_role"] == "measurement"
    assert sensor.extra_state_attributes["windhager_model_role"] == "feature"
    assert sensor._unrecorded_attributes == frozenset(
        {
            "windhager_data_role",
            "windhager_temporal_semantics",
            "windhager_model_role",
            "windhager_history_importance",
            "windhager_oid",
            "windhager_write_protected",
        }
    )


def test_setpoint_sensor_no_state_class_and_recordable(mock_coordinator, mock_entry):
    mock_coordinator.data["room_setpoint"] = 21.5
    mock_coordinator.datapoints = [
        {
            "oid": "1/15/0/1/1/0",
            "key": "room_setpoint",
            "unit": "°C",
            "device_class": "temperature",
            "state_class": None,
            "data_role": "setpoint",
            "temporal_semantics": "step",
            "model_role": "control",
            "history_importance": "critical",
            "i18n": {"en": "Setpoint"},
            "experience_minimum": "essential",
            "write_protected": True,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = []
    asyncio.get_event_loop().run_until_complete(
        async_setup_entry(hass, mock_entry, lambda entities, **kw: added.extend(entities))
    )

    assert len(added) == 1
    sensor = added[0]
    assert sensor.entity_description.state_class is None
    assert sensor.native_value == 21.5
    assert sensor.extra_state_attributes["windhager_data_role"] == "setpoint"


def test_enum_sensor_ignores_incompatible_metadata_and_keeps_options(mock_coordinator, mock_entry):
    mock_coordinator.has_enum_labels.return_value = True
    mock_coordinator.get_enum_options.return_value = ["Off", "On"]
    mock_coordinator.datapoints = [
        {
            "oid": "1/65/0/2/1/0",
            "key": "boiler_phase",
            "state_class": "measurement",
            "unit": "%",
            "data_role": "operating_state",
            "temporal_semantics": "event",
            "model_role": "event",
            "history_importance": "critical",
            "i18n": {"en": "Phase"},
            "experience_minimum": "essential",
            "write_protected": True,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = []
    asyncio.get_event_loop().run_until_complete(
        async_setup_entry(hass, mock_entry, lambda entities, **kw: added.extend(entities))
    )

    assert len(added) == 1
    sensor = added[0]
    desc = sensor.entity_description
    assert desc.device_class is SensorDeviceClass.ENUM
    assert desc.state_class is None
    assert desc.native_unit_of_measurement is None
    assert desc.options == ["Off", "On"]
    assert sensor.extra_state_attributes["windhager_data_role"] == "operating_state"


def test_explicit_entity_category_overrides_diagnostic_role(mock_coordinator, mock_entry):
    mock_coordinator.datapoints = [
        {
            "oid": "1/0/0/0/0/0",
            "key": "diag",
            "i18n": {"en": "Diag"},
            "entity_role": "diagnostic",
            "entity_category": "config",
            "data_role": "diagnostic",
            "experience_minimum": "essential",
            "write_protected": True,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = []
    asyncio.get_event_loop().run_until_complete(
        async_setup_entry(hass, mock_entry, lambda entities, **kw: added.extend(entities))
    )

    assert added[0].entity_description.entity_category is EntityCategory.CONFIG


def test_backward_compat_no_new_fields(mock_coordinator, mock_entry):
    """Backward-compatible datapoint creates the same sensor as before."""
    mock_coordinator.datapoints = [
        {
            "oid": "1/65/0/0/7/0",
            "key": "boiler_temp",
            "unit": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "i18n": {"en": "Boiler temp"},
            "experience_minimum": "essential",
            "write_protected": True,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = []
    asyncio.get_event_loop().run_until_complete(
        async_setup_entry(hass, mock_entry, lambda entities, **kw: added.extend(entities))
    )

    assert len(added) == 1
    sensor = added[0]
    assert sensor.unique_id is not None
    assert sensor.native_value == 75.5
    assert sensor.entity_description.entity_registry_enabled_default is True
    # Defaults should apply without writing them to YAML
    assert sensor.extra_state_attributes["windhager_data_role"] == "unknown"
    assert sensor.extra_state_attributes["windhager_model_role"] == "unknown"


def test_sensor_entity_directly_exposes_attributes(mock_coordinator, mock_entry):
    desc = WindhagerLONSensorDescription(
        key="boiler_temp",
        name="Boiler Temp",
        oid="1/65/0/0/7/0",
        datapoint={"oid": "1/65/0/0/7/0", "write_protected": True},
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    # Without metadata, extra_state_attributes is None
    assert sensor.extra_state_attributes is None
