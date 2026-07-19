"""Tests for LON control platforms."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.windhager_unified.number import (
    WindhagerLONNumber,
    WindhagerLONNumberDescription,
)
from custom_components.windhager_unified.switch import (
    WindhagerLONSwitch,
    WindhagerLONSwitchDescription,
)


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.entry_id = "test_id"
    entry.data = {"host": "http://test-host"}
    return entry


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.data = {"lon_cfg": "1"}
    coord.api_client.async_put_datapoint = AsyncMock()
    coord.async_request_refresh = AsyncMock()
    coord.get_raw_lon_value.return_value = "1"
    coord.get_function_block_device_info.return_value = {
        "identifiers": {("windhager_unified", "test_id_fb_1_15_0")},
        "name": "Central controller",
        "manufacturer": "Windhager",
        "via_device": ("windhager_unified", "test_id"),
    }
    return coord


@pytest.mark.asyncio
async def test_lon_number_writes_formatted_value(mock_coordinator, mock_entry):
    dp = {
        "oid": "1/15/0/3/1/0",
        "key": "lon_cfg",
        "min_value": "10.0",
        "max_value": "50.0",
        "step": "1.0",
    }
    desc = WindhagerLONNumberDescription(
        key="lon_cfg",
        name="Origin",
        oid="1/15/0/3/1/0",
        datapoint=dp,
    )
    entity = WindhagerLONNumber(mock_coordinator, mock_entry, desc)
    await entity.async_set_native_value(25.0)
    mock_coordinator.api_client.async_put_datapoint.assert_awaited_once_with(
        ["1", "15", "0", "3", "1", "0"],
        "25",
    )


@pytest.mark.asyncio
async def test_lon_number_write_failure_raises(mock_coordinator, mock_entry):
    from custom_components.windhager_unified.exceptions import WindhagerApiError

    mock_coordinator.api_client.async_put_datapoint.side_effect = WindhagerApiError("denied")
    dp = {"oid": "1/15/0/3/1/0", "key": "lon_cfg", "min_value": "0", "max_value": "100"}
    entity = WindhagerLONNumber(
        mock_coordinator,
        mock_entry,
        WindhagerLONNumberDescription(key="lon_cfg", name="X", oid="1/15/0/3/1/0", datapoint=dp),
    )
    with pytest.raises(HomeAssistantError):
        await entity.async_set_native_value(10.0)


@pytest.mark.asyncio
async def test_lon_switch_writes_one_and_zero(mock_coordinator, mock_entry):
    dp = {"oid": "1/15/0/2/99/0", "key": "lon_sw"}
    entity = WindhagerLONSwitch(
        mock_coordinator,
        mock_entry,
        WindhagerLONSwitchDescription(key="lon_sw", name="Flag", oid=dp["oid"], datapoint=dp),
    )
    await entity.async_turn_on()
    mock_coordinator.api_client.async_put_datapoint.assert_awaited_with(
        ["1", "15", "0", "2", "99", "0"],
        "1",
    )
    await entity.async_turn_off()
    mock_coordinator.api_client.async_put_datapoint.assert_awaited_with(
        ["1", "15", "0", "2", "99", "0"],
        "0",
    )
