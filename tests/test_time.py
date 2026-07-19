"""Tests for the time platform."""

from __future__ import annotations

from datetime import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from custom_components.windhager_unified.const import DOMAIN
from custom_components.windhager_unified.time import (
    WindhagerLONTimeDescription,
    WindhagerLONTimeEntity,
    async_setup_entry,
)


@pytest.fixture
def mock_coordinator():
    coordinator = MagicMock()
    coordinator.data = {"lon_time": time(16, 53)}
    coordinator.has_enum_labels.return_value = False
    coordinator.get_function_block_device_info.return_value = {
        "identifiers": {(DOMAIN, "test_id_fb_1_65_0")},
        "name": "Boiler",
        "manufacturer": "Windhager",
        "via_device": (DOMAIN, "test_id"),
    }
    coordinator.lon_numeric_format_confirmed.return_value = False
    coordinator.api_client.async_put_datapoint = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_id"
    entry.data = {"host": "http://test-host"}
    return entry


@pytest.fixture
def writable_time_dp():
    return {
        "oid": "1/65/0/2/72/0",
        "key": "lon_time",
        "unit_id": 21,
        "unit": None,
        "device_class": None,
        "state_class": None,
        "i18n": {"en": "Heating Start"},
        "hint_node": "LogWIN",
        "experience_minimum": "comfort",
        "write_protected": False,
    }


@pytest.fixture
def write_protected_time_dp():
    return {
        "oid": "1/65/0/2/72/0",
        "key": "lon_time",
        "unit_id": 21,
        "unit": None,
        "device_class": None,
        "state_class": None,
        "i18n": {"en": "Heating Start"},
        "hint_node": "LogWIN",
        "experience_minimum": "comfort",
        "write_protected": True,
    }


def _description(dp):
    return WindhagerLONTimeDescription(
        key=dp["key"],
        translation_key=dp["key"].replace(".", "_"),
        name=dp["i18n"]["en"],
        oid=dp["oid"],
        datapoint=dp,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=True,
    )


def test_time_entity_native_value(mock_coordinator, mock_entry, writable_time_dp):
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    assert entity.native_value == time(16, 53)


def test_time_entity_native_value_none_when_no_data(mock_coordinator, mock_entry, writable_time_dp):
    mock_coordinator.data = None
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    assert entity.native_value is None


async def test_time_entity_set_value_writes_hhmm(mock_coordinator, mock_entry, writable_time_dp):
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    await entity.async_set_value(time(18, 30))
    mock_coordinator.api_client.async_put_datapoint.assert_awaited_once_with(
        ["1", "65", "0", "2", "72", "0"], "18:30"
    )
    mock_coordinator.async_request_refresh.assert_awaited_once()


async def test_time_entity_set_value_raises_on_api_error(
    mock_coordinator, mock_entry, writable_time_dp
):
    from custom_components.windhager_unified.exceptions import WindhagerError

    mock_coordinator.api_client.async_put_datapoint.side_effect = WindhagerError("Boom")
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    with pytest.raises(HomeAssistantError, match="Boom"):
        await entity.async_set_value(time(18, 30))


async def test_time_entity_set_value_raises_on_bad_oid(
    mock_coordinator, mock_entry, writable_time_dp
):
    writable_time_dp["oid"] = "bad-oid"
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    with pytest.raises(HomeAssistantError, match="Invalid OID"):
        await entity.async_set_value(time(18, 30))


def test_time_entity_suggested_object_id(mock_coordinator, mock_entry, writable_time_dp):
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    assert entity.suggested_object_id == "lon_time"


def test_time_entity_unique_id_is_md5(mock_coordinator, mock_entry, writable_time_dp):
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    assert entity.unique_id is not None
    assert len(entity.unique_id) == 32


def test_time_entity_config_category(mock_coordinator, mock_entry, writable_time_dp):
    desc = _description(writable_time_dp)
    entity = WindhagerLONTimeEntity(mock_coordinator, mock_entry, desc)
    assert entity.entity_category == EntityCategory.CONFIG


def test_async_setup_entry_creates_time_entity_for_writable_time(
    mock_coordinator, mock_entry, writable_time_dp
):
    mock_coordinator.datapoints = [writable_time_dp]
    mock_coordinator.get_entity_name = MagicMock(return_value="Heating Start")

    hass = MagicMock()
    hass.config.language = "en"
    from custom_components.windhager_unified.const import DOMAIN as _DOMAIN

    hass.data = {_DOMAIN: {mock_entry.entry_id: mock_coordinator}}
    mock_entry.options = {}

    added_entities: list = []

    def _add(entities, *args, **kwargs):
        added_entities.extend(entities)

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_setup_entry(hass, mock_entry, _add))

    assert len(added_entities) == 1
    assert isinstance(added_entities[0], WindhagerLONTimeEntity)


def test_async_setup_entry_skips_write_protected_time(
    mock_coordinator, mock_entry, write_protected_time_dp
):
    mock_coordinator.datapoints = [write_protected_time_dp]
    mock_coordinator.get_entity_name = MagicMock(return_value="Heating Start")

    hass = MagicMock()
    hass.config.language = "en"
    from custom_components.windhager_unified.const import DOMAIN as _DOMAIN

    hass.data = {_DOMAIN: {mock_entry.entry_id: mock_coordinator}}
    mock_entry.options = {}

    added_entities: list = []

    def _add(entities, *args, **kwargs):
        added_entities.extend(entities)

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_setup_entry(hass, mock_entry, _add))

    assert len(added_entities) == 0


def test_async_setup_entry_skips_date_and_numeric_datapoints(
    mock_coordinator, mock_entry, writable_time_dp
):
    mock_coordinator.datapoints = [
        writable_time_dp,
        {
            "oid": "1/65/0/2/70/0",
            "key": "lon_date",
            "unit_id": 20,
            "write_protected": True,
        },
        {
            "oid": "1/65/0/0/0/0",
            "key": "logwin.boiler_temp",
            "unit": "°C",
            "write_protected": True,
        },
    ]
    mock_coordinator.get_entity_name = MagicMock(return_value="Entity")

    hass = MagicMock()
    hass.config.language = "en"
    from custom_components.windhager_unified.const import DOMAIN as _DOMAIN

    hass.data = {_DOMAIN: {mock_entry.entry_id: mock_coordinator}}
    mock_entry.options = {}

    added_entities: list = []

    def _add(entities, *args, **kwargs):
        added_entities.extend(entities)

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_setup_entry(hass, mock_entry, _add))

    assert len(added_entities) == 1
    assert isinstance(added_entities[0], WindhagerLONTimeEntity)
