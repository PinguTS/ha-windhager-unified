"""Tests for the merged sensor platform (LON + RestAPI)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass

from custom_components.windhager_unified.const import DOMAIN
from custom_components.windhager_unified.sensor import (
    WindhagerLONSensor,
    WindhagerLONSensorDescription,
    WindhagerRestAPISensor,
    WindhagerRestAPISensorDescription,
    async_setup_entry,
)


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {
        "logwin.boiler_temp": 75.5,
        "heartbeat.status": "active",
    }
    # Sensors use has_enum_labels to decide whether to perform enum lookup;
    # default to False so non-enum tests see raw values.
    coordinator.has_enum_labels.return_value = False
    coordinator.datapoints = [
        {
            "oid": "1/65/0/0/0/0",
            "key": "logwin.boiler_temp",
            "unit": "°C",
            "device_class": "temperature",
            "state_class": "measurement",
            "i18n": {"en": "Boiler Temperature"},
            "hint_node": "LogWIN",
        }
    ]
    coordinator.restapi_endpoints = {
        "heartbeat": [
            {
                "endpoint": "/InfoWinHeartbeat/api/1.0/heartbeat",
                "key": "heartbeat.status",
                "entity_type": "sensor",
                "i18n": {"en": "Heartbeat Status"},
                "device_class": None,
                "state_class": None,
            }
        ]
    }
    return coordinator


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_id"
    entry.data = {"host": "http://test-host"}
    return entry


# ---------------------------------------------------------------------------
# LON sensor
# ---------------------------------------------------------------------------


def test_lon_sensor_native_value(mock_coordinator, mock_entry):
    desc = WindhagerLONSensorDescription(
        key="logwin.boiler_temp",
        name="Boiler Temperature",
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        oid="1/65/0/0/0/0",
        hint_node="LogWIN",
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.native_value == 75.5


def test_lon_sensor_returns_none_when_no_data(mock_coordinator, mock_entry):
    mock_coordinator.data = None
    desc = WindhagerLONSensorDescription(
        key="logwin.boiler_temp",
        name="Boiler Temperature",
        oid="1/65/0/0/0/0",
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.native_value is None


def test_lon_sensor_unique_id_is_md5(mock_coordinator, mock_entry):
    desc = WindhagerLONSensorDescription(
        key="logwin.boiler_temp",
        name="Boiler Temperature",
        oid="1/65/0/0/0/0",
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.unique_id is not None
    assert len(sensor.unique_id) == 32
    assert sensor.suggested_object_id == "logwin_boiler_temp"


def test_lon_sensor_suggested_object_id_matches_stable_key(mock_coordinator, mock_entry):
    """Repeated VarIdent labels must not drive entity_id; slug uses the unique datapoint key."""
    desc_a = WindhagerLONSensorDescription(
        key="lon_1_16_0_20_126_0",
        name="20-126",
        oid="1/16/0/20/126/0",
    )
    desc_b = WindhagerLONSensorDescription(
        key="lon_1_16_1_20_126_0",
        name="20-126",
        oid="1/16/1/20/126/0",
    )
    sensor_a = WindhagerLONSensor(mock_coordinator, mock_entry, desc_a)
    sensor_b = WindhagerLONSensor(mock_coordinator, mock_entry, desc_b)
    assert sensor_a.suggested_object_id == "lon_1_16_0_20_126_0"
    assert sensor_b.suggested_object_id == "lon_1_16_1_20_126_0"
    assert sensor_a.suggested_object_id != sensor_b.suggested_object_id


def test_lon_sensor_device_info(mock_coordinator, mock_entry):
    desc = WindhagerLONSensorDescription(
        key="logwin.boiler_temp",
        name="Boiler Temperature",
        oid="1/65/0/0/0/0",
        hint_node="LogWIN",
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.device_info["identifiers"] == {(DOMAIN, "test_id")}
    assert sensor.device_info["manufacturer"] == "Windhager"
    assert sensor.device_info["model"] == "LogWIN"


# ---------------------------------------------------------------------------
# RestAPI sensor
# ---------------------------------------------------------------------------


def test_restapi_sensor_native_value(mock_coordinator, mock_entry):
    desc = WindhagerRestAPISensorDescription(
        key="heartbeat.status",
        name="Heartbeat Status",
        endpoint="/InfoWinHeartbeat/api/1.0/heartbeat",
        group="heartbeat",
    )
    sensor = WindhagerRestAPISensor(mock_coordinator, mock_entry, desc)
    assert sensor.native_value == "active"


def test_restapi_sensor_device_info_uses_group(mock_coordinator, mock_entry):
    desc = WindhagerRestAPISensorDescription(
        key="heartbeat.status",
        name="Heartbeat Status",
        endpoint="/InfoWinHeartbeat/api/1.0/heartbeat",
        group="heartbeat",
    )
    sensor = WindhagerRestAPISensor(mock_coordinator, mock_entry, desc)
    assert sensor.device_info["identifiers"] == {(DOMAIN, "test_id_heartbeat")}
    assert "heartbeat" in sensor.device_info["name"].lower()


# ---------------------------------------------------------------------------
# Experience-tier entity_registry_enabled_default tests
# ---------------------------------------------------------------------------


def test_lon_sensor_essential_enabled_by_default(mock_coordinator, mock_entry):
    """Essential-minimum sensors must be enabled by default."""
    desc = WindhagerLONSensorDescription(
        key="logwin.boiler_temp",
        name="Boiler Temperature",
        oid="1/65/0/0/0/0",
        entity_registry_enabled_default=True,
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.entity_description.entity_registry_enabled_default is True


def test_lon_sensor_expert_disabled_by_default(mock_coordinator, mock_entry):
    """Expert-minimum sensors should be registered but disabled by default."""
    desc = WindhagerLONSensorDescription(
        key="lon_expert",
        name="Expert Sensor",
        oid="1/65/0/0/99/0",
        entity_registry_enabled_default=False,
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.entity_description.entity_registry_enabled_default is False


def test_restapi_sensor_service_tier_entity_disabled(mock_coordinator, mock_entry):
    """Service-minimum REST sensors must have entity_registry_enabled_default=False
    when the user is at essential or comfort tier."""
    desc = WindhagerRestAPISensorDescription(
        key="admin.settings",
        name="System Settings",
        endpoint="/WsAdmin/api/1.0/settings",
        group="admin",
        entity_registry_enabled_default=False,
    )
    sensor = WindhagerRestAPISensor(mock_coordinator, mock_entry, desc)
    assert sensor.entity_description.entity_registry_enabled_default is False


# ---------------------------------------------------------------------------
# Date/time sensor (unit_id 20/21) — TIMESTAMP device class
# ---------------------------------------------------------------------------


def test_lon_date_sensor_gets_timestamp_device_class(mock_coordinator, mock_entry):
    """Sensor for a date datapoint (unit_id 20) must use TIMESTAMP, no unit."""
    desc = WindhagerLONSensorDescription(
        key="lon_date",
        name="Date",
        oid="1/65/0/2/70/0",
        device_class=SensorDeviceClass.TIMESTAMP,
        native_unit_of_measurement=None,
        state_class=None,
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.entity_description.device_class == SensorDeviceClass.TIMESTAMP
    assert sensor.entity_description.native_unit_of_measurement is None
    assert sensor.entity_description.state_class is None


def test_lon_date_sensor_returns_datetime_from_coordinator(mock_coordinator, mock_entry):
    """native_value passes through a datetime object stored by the coordinator."""
    expected = datetime(2026, 5, 18, tzinfo=timezone.utc)
    mock_coordinator.data["lon_date"] = expected
    desc = WindhagerLONSensorDescription(
        key="lon_date",
        name="Date",
        oid="1/65/0/2/70/0",
        device_class=SensorDeviceClass.TIMESTAMP,
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.native_value == expected


def test_lon_time_sensor_returns_datetime_from_coordinator(mock_coordinator, mock_entry):
    """native_value passes through a datetime object for a time datapoint."""
    expected = datetime(2026, 5, 18, 16, 53, tzinfo=timezone.utc)
    mock_coordinator.data["lon_time"] = expected
    desc = WindhagerLONSensorDescription(
        key="lon_time",
        name="Time",
        oid="1/65/0/2/72/0",
        device_class=SensorDeviceClass.TIMESTAMP,
    )
    sensor = WindhagerLONSensor(mock_coordinator, mock_entry, desc)
    assert sensor.native_value == expected


def test_async_setup_entry_date_datapoint_gets_timestamp_class(mock_coordinator, mock_entry):
    """async_setup_entry must assign TIMESTAMP class and no unit to date datapoints."""
    mock_coordinator.datapoints = [
        {
            "oid": "1/65/0/2/70/0",
            "key": "lon_date",
            "unit_id": 20,
            "unit": None,
            "device_class": None,
            "state_class": None,
            "i18n": {"en": "Date"},
            "hint_node": "LogWIN",
            "experience_minimum": "comfort",
        }
    ]
    mock_coordinator.restapi_endpoints = {}
    mock_coordinator.has_enum_labels.return_value = False
    mock_coordinator.get_entity_name = MagicMock(return_value="Date")
    mock_coordinator.get_enum_options.return_value = []

    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {mock_entry.data.get("domain", "windhager_unified"): {}}
    # Wire up hass.data[DOMAIN][entry_id] -> coordinator
    from custom_components.windhager_unified.const import DOMAIN as _DOMAIN
    hass.data = {_DOMAIN: {mock_entry.entry_id: mock_coordinator}}
    mock_entry.options = {}

    added_entities: list = []

    def _add(entities, *args, **kwargs):
        added_entities.extend(entities)

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_setup_entry(hass, mock_entry, _add))

    assert len(added_entities) == 1
    sensor = added_entities[0]
    desc = sensor.entity_description
    assert desc.device_class == SensorDeviceClass.TIMESTAMP
    assert desc.native_unit_of_measurement is None
    assert desc.state_class is None
