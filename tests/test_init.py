"""Tests for __init__.py: setup, unload, and set_datapoint service."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.windhager_unified.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

_ENTRY_DATA = {
    CONF_HOST: "http://test-host",
    CONF_USERNAME: "user",
    CONF_PASSWORD: "pass",
    CONF_VERIFY_SSL: False,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}


def _mock_coordinator(hass):
    """Return a coordinator mock that passes the connectivity probe."""
    from custom_components.windhager_unified.coordinator import WindhagerCoordinator

    coord = WindhagerCoordinator(
        hass=hass,
        host="http://test-host",
        username="user",
        password="pass",
        verify_ssl=False,
        scan_interval=30,
    )
    coord.api_client.async_init = AsyncMock()
    coord.api_client.async_close = AsyncMock()
    coord.api_client.async_get_subnets = AsyncMock(return_value={"subnets": []})
    coord.async_initialize_catalog = AsyncMock()
    coord.async_refresh = AsyncMock()
    coord.last_update_success = True
    coord.data = {}
    return coord


async def test_setup_entry_stores_coordinator(hass):
    entry = MagicMock()
    entry.entry_id = "test"
    entry.data = _ENTRY_DATA
    entry.options = {}
    # Actually schedule the background refresh coroutine so the AsyncMock
    # coroutine is awaited and no RuntimeWarning is leaked.
    entry.async_create_background_task = lambda _hass, coro, _name: asyncio.create_task(coro)

    with (
        patch(
            "custom_components.windhager_unified.WindhagerCoordinator",
            return_value=_mock_coordinator(hass),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        from custom_components.windhager_unified import async_setup_entry

        result = await async_setup_entry(hass, entry)

    assert result is True
    assert "test" in hass.data.get(DOMAIN, {})


async def test_unload_entry_closes_session(hass):
    coord = _mock_coordinator(hass)
    hass.data.setdefault(DOMAIN, {})["test_entry"] = coord
    hass.services.async_register(DOMAIN, "set_datapoint", lambda c: None)

    entry = MagicMock()
    entry.entry_id = "test_entry"

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_unload_platforms",
        new_callable=AsyncMock,
        return_value=True,
    ):
        from custom_components.windhager_unified import async_unload_entry

        result = await async_unload_entry(hass, entry)

    assert result is True
    assert "test_entry" not in hass.data[DOMAIN]
    coord.api_client.async_close.assert_awaited_once()


async def _setup_service(hass):
    """Set up the integration and return the mock coordinator plus entry."""
    entry = MagicMock()
    entry.entry_id = "test"
    entry.data = _ENTRY_DATA
    entry.options = {}
    entry.async_create_background_task = lambda _hass, coro, _name: asyncio.create_task(coro)

    coord = _mock_coordinator(hass)
    coord.api_client.async_put_datapoint = AsyncMock(return_value=None)
    coord.api_client.async_get_datapoint = AsyncMock(return_value={"value": "1"})

    with (
        patch(
            "custom_components.windhager_unified.WindhagerCoordinator",
            return_value=coord,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        from custom_components.windhager_unified import async_setup_entry

        await async_setup_entry(hass, entry)

    return coord, entry


async def test_set_datapoint_accepts_leading_slash(hass):
    coord, _entry = await _setup_service(hass)
    await hass.services.async_call(
        DOMAIN,
        "set_datapoint",
        {"oid": "/1/60/2/50/5/0", "value": "4"},
        blocking=True,
    )
    coord.api_client.async_put_datapoint.assert_awaited_once()
    assert coord.api_client.async_put_datapoint.await_args[0][0] == [
        "1",
        "60",
        "2",
        "50",
        "5",
        "0",
    ]
    assert coord.api_client.async_put_datapoint.await_args[0][1] == "4"


async def test_set_datapoint_accepts_dotted_oid(hass):
    coord, _entry = await _setup_service(hass)
    await hass.services.async_call(
        DOMAIN,
        "set_datapoint",
        {"oid": "1.60.2.50.5.0", "value": "4"},
        blocking=True,
    )
    coord.api_client.async_put_datapoint.assert_awaited_once()
    assert coord.api_client.async_put_datapoint.await_args[0][0] == [
        "1",
        "60",
        "2",
        "50",
        "5",
        "0",
    ]


async def test_set_datapoint_invalid_oid_raises(hass):
    await _setup_service(hass)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "set_datapoint",
            {"oid": "/1/60/2/50", "value": "4"},
            blocking=True,
        )
