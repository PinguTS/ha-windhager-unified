"""Tests for diagnostics — credentials must be redacted."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.windhager_unified.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    DOMAIN,
)
from custom_components.windhager_unified.diagnostics import async_get_config_entry_diagnostics

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.data = {
        CONF_HOST: "http://192.0.2.10",
        CONF_USERNAME: "Service",
        CONF_PASSWORD: "supersecret",
    }
    entry.options = {}
    return entry


@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.last_update_success = True
    coord.datapoints = []
    coord.restapi_endpoints = {"heartbeat": []}
    coord.data = {"heartbeat.status": "ok"}
    return coord


async def test_diagnostics_redacts_credentials(hass, mock_entry, mock_coordinator):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator

    result = await async_get_config_entry_diagnostics(hass, mock_entry)

    config = result["config_entry"]
    assert config[CONF_HOST] == "**REDACTED**"
    assert config[CONF_USERNAME] == "**REDACTED**"
    assert config[CONF_PASSWORD] == "**REDACTED**"


async def test_diagnostics_includes_coordinator_state(hass, mock_entry, mock_coordinator):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_entry.entry_id] = mock_coordinator

    result = await async_get_config_entry_diagnostics(hass, mock_entry)

    coord = result["coordinator"]
    assert coord["last_update_success"] is True
    assert "heartbeat" in coord["restapi_groups"]
    assert coord["data"] == {"heartbeat.status": "ok"}
