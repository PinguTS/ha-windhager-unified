"""Tests that control platforms (number, switch, select) wire metadata correctly."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory

from custom_components.windhager_unified.const import DOMAIN
from custom_components.windhager_unified.number import (
    WindhagerLONNumber,
    WindhagerLONNumberDescription,
)
from custom_components.windhager_unified.number import (
    async_setup_entry as number_setup_entry,
)
from custom_components.windhager_unified.select import (
    WindhagerLONSelect,
    WindhagerLONSelectDescription,
)
from custom_components.windhager_unified.select import (
    async_setup_entry as select_setup_entry,
)
from custom_components.windhager_unified.switch import (
    WindhagerLONSwitch,
    WindhagerLONSwitchDescription,
)
from custom_components.windhager_unified.switch import (
    async_setup_entry as switch_setup_entry,
)


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {"number_dp": "21.5", "switch_dp": "1", "select_dp": "1"}
    coordinator.has_enum_labels.return_value = False
    coordinator.get_function_block_device_info.return_value = {
        "identifiers": {(DOMAIN, "test_id_fb")},
        "name": "Boiler",
        "manufacturer": "Windhager",
        "via_device": (DOMAIN, "test_id"),
    }
    coordinator.lon_numeric_format_confirmed.return_value = True
    coordinator.get_entity_name = MagicMock(return_value="Test")
    coordinator.get_enum_options.return_value = ["Off", "On"]
    coordinator.get_enum_label.return_value = "On"
    coordinator.get_enum_id.return_value = 1
    coordinator.get_raw_lon_value.return_value = "1"
    coordinator.async_request_refresh = AsyncMock()
    coordinator.restapi_endpoints = {}
    return coordinator


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_id"
    entry.data = {"host": "http://test-host"}
    entry.options = {}
    return entry


def _run_setup(hass, entry, coordinator, setup_fn):
    added = []
    asyncio.get_event_loop().run_until_complete(
        setup_fn(hass, entry, lambda entities, **kw: added.extend(entities))
    )
    return added


# ---------------------------------------------------------------------------
# Number
# ---------------------------------------------------------------------------


def test_number_metadata_wired(mock_coordinator, mock_entry):
    mock_coordinator.datapoints = [
        {
            "oid": "1/15/0/1/1/0",
            "key": "number_dp",
            "unit": "°C",
            "device_class": "temperature",
            "min_value": "10",
            "max_value": "30",
            "step": "0.5",
            "data_role": "setpoint",
            "temporal_semantics": "step",
            "model_role": "control",
            "history_importance": "critical",
            "icon": "mdi:thermostat",
            "entity_category": "config",
            "i18n": {"en": "Setpoint"},
            "experience_minimum": "essential",
            "write_protected": False,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = _run_setup(hass, mock_entry, mock_coordinator, number_setup_entry)
    assert len(added) == 1
    number = added[0]
    desc = number.entity_description
    assert desc.icon == "mdi:thermostat"
    assert desc.entity_category is EntityCategory.CONFIG
    assert number.extra_state_attributes["windhager_data_role"] == "setpoint"
    assert number.extra_state_attributes["windhager_model_role"] == "control"


async def test_number_write_refreshes_and_updates_state(mock_coordinator, mock_entry):
    mock_coordinator.datapoints = [
        {
            "oid": "1/15/0/1/1/0",
            "key": "number_dp",
            "unit": "°C",
            "min_value": "10",
            "max_value": "30",
            "step": "0.5",
            "i18n": {"en": "Setpoint"},
            "experience_minimum": "essential",
            "write_protected": False,
        }
    ]
    mock_coordinator.api_client.async_put_datapoint = AsyncMock()
    desc = WindhagerLONNumberDescription(
        key="number_dp",
        name="Test",
        oid="1/15/0/1/1/0",
        datapoint=mock_coordinator.datapoints[0],
    )
    number = WindhagerLONNumber(mock_coordinator, mock_entry, desc)
    await number.async_set_native_value(22.0)
    mock_coordinator.api_client.async_put_datapoint.assert_awaited_once()
    mock_coordinator.async_request_refresh.assert_awaited_once()


# ---------------------------------------------------------------------------
# Switch
# ---------------------------------------------------------------------------


def test_switch_metadata_wired(mock_coordinator, mock_entry):
    mock_coordinator.datapoints = [
        {
            "oid": "1/0/0/0/0/0",
            "key": "switch_dp",
            "min_value": "0",
            "max_value": "1",
            "data_role": "actuator_state",
            "temporal_semantics": "event",
            "model_role": "event",
            "history_importance": "critical",
            "icon": "mdi:pump",
            "i18n": {"en": "Pump"},
            "experience_minimum": "essential",
            "write_protected": False,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = _run_setup(hass, mock_entry, mock_coordinator, switch_setup_entry)
    assert len(added) == 1
    switch = added[0]
    assert switch.entity_description.icon == "mdi:pump"
    assert switch.extra_state_attributes["windhager_data_role"] == "actuator_state"
    assert switch.is_on is True


async def test_switch_state_transitions(mock_coordinator, mock_entry):
    dp = {
        "oid": "1/0/0/0/0/0",
        "key": "switch_dp",
        "min_value": "0",
        "max_value": "1",
        "write_protected": False,
    }
    desc = WindhagerLONSwitchDescription(
        key="switch_dp", name="Test", oid="1/0/0/0/0/0", datapoint=dp
    )
    switch = WindhagerLONSwitch(mock_coordinator, mock_entry, desc)
    mock_coordinator.api_client.async_put_datapoint = AsyncMock()
    await switch.async_turn_on()
    assert mock_coordinator.api_client.async_put_datapoint.await_args[0][1] == "1"
    mock_coordinator.data["switch_dp"] = "0"
    assert switch.is_on is False


# ---------------------------------------------------------------------------
# Select
# ---------------------------------------------------------------------------


def test_select_metadata_wired(mock_coordinator, mock_entry):
    mock_coordinator.has_enum_labels.return_value = True
    mock_coordinator.datapoints = [
        {
            "oid": "1/65/0/2/1/0",
            "key": "select_dp",
            "data_role": "operating_state",
            "temporal_semantics": "event",
            "model_role": "event",
            "history_importance": "critical",
            "icon": "mdi:state-machine",
            "i18n": {"en": "Phase"},
            "experience_minimum": "essential",
            "write_protected": False,
        }
    ]
    hass = MagicMock()
    hass.config.language = "en"
    hass.data = {DOMAIN: {mock_entry.entry_id: mock_coordinator}}

    added = _run_setup(hass, mock_entry, mock_coordinator, select_setup_entry)
    assert len(added) == 1
    select = added[0]
    assert select.entity_description.icon == "mdi:state-machine"
    assert select.extra_state_attributes["windhager_data_role"] == "operating_state"
    assert select.current_option == "On"


async def test_select_write_refreshes_and_updates_state(mock_coordinator, mock_entry):
    mock_coordinator.has_enum_labels.return_value = True
    dp = {
        "oid": "1/65/0/2/1/0",
        "key": "select_dp",
        "write_protected": False,
    }
    desc = WindhagerLONSelectDescription(
        key="select_dp", name="Test", oid="1/65/0/2/1/0", datapoint=dp, options=["Off", "On"]
    )
    select = WindhagerLONSelect(mock_coordinator, mock_entry, desc)
    mock_coordinator.api_client.async_put_datapoint = AsyncMock()
    await select.async_select_option("On")
    mock_coordinator.api_client.async_put_datapoint.assert_awaited_once()
    mock_coordinator.async_request_refresh.assert_awaited_once()
