"""Tests for the history storage profile in config flow and options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import InvalidData

from custom_components.windhager_unified.const import (
    CONF_ADHOC_OIDS,
    CONF_DISCOVERED_DATAPOINTS,
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
    CONF_HISTORY_RETENTION_DAYS,
    CONF_HISTORY_SAMPLE_INTERVAL,
    CONF_HISTORY_STORAGE_MODE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_REFRESH_LABELS,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_HISTORY_STORAGE_MODE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HISTORY_MODE_ALL_MARKED,
    HISTORY_MODE_CRITICAL,
    HISTORY_MODE_HOME_ASSISTANT,
)
from custom_components.windhager_unified.discovery import DiscoveryResult

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

_USER_INPUT = {
    CONF_HOST: "http://192.0.2.10",
    CONF_USERNAME: "Service",
    CONF_PASSWORD: "secret",
    CONF_VERIFY_SSL: False,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}


@pytest.fixture
def mock_client():
    with patch("custom_components.windhager_unified.config_flow.WindhagerApiClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance
        yield instance


async def _run_through_groups(hass, mock_client):
    mock_client.async_test_connection = AsyncMock(return_value=True)
    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = DiscoveryResult(boiler_id=None, boiler_name=None, groups=[])
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=_USER_INPUT
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_EXPERIENCE_LEVEL: "essential"}
        )
        while result.get("type") == "form" and result.get("step_id") != "groups":
            result = await hass.config_entries.flow.async_configure(result["flow_id"])
        if result.get("step_id") == "groups":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_GROUPS: []}
            )
    return result


async def test_config_flow_history_step_default(hass, mock_client):
    result = await _run_through_groups(hass, mock_client)
    assert result["type"] == "form"
    assert result["step_id"] == "history"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
    )
    assert result["type"] == "create_entry"
    assert result["options"][CONF_HISTORY_STORAGE_MODE] == HISTORY_MODE_HOME_ASSISTANT


async def test_config_flow_archive_mode_shows_advanced(hass, mock_client):
    result = await _run_through_groups(hass, mock_client)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_CRITICAL},
    )
    assert result["type"] == "form"
    assert result["step_id"] == "history_advanced"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HISTORY_SAMPLE_INTERVAL: 60,
            CONF_HISTORY_RETENTION_DAYS: 90,
        },
    )
    assert result["type"] == "create_entry"
    assert result["options"][CONF_HISTORY_STORAGE_MODE] == HISTORY_MODE_CRITICAL
    assert result["options"][CONF_HISTORY_SAMPLE_INTERVAL] == 60
    assert result["options"][CONF_HISTORY_RETENTION_DAYS] == 90


async def test_config_flow_invalid_advanced_values_rejected(hass, mock_client):
    result = await _run_through_groups(hass, mock_client)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_ALL_MARKED},
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HISTORY_SAMPLE_INTERVAL: 10,  # below minimum
                CONF_HISTORY_RETENTION_DAYS: DEFAULT_HISTORY_RETENTION_DAYS,
            },
        )


async def test_options_flow_preserves_history_mode(hass, mock_client):
    result = await _run_through_groups(hass, mock_client)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
    )
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = entries[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    schema = result["data_schema"].schema
    assert CONF_HISTORY_STORAGE_MODE in {k.schema for k in schema}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_EXPERIENCE_LEVEL: "essential",
            CONF_SCAN_INTERVAL: 60,
            CONF_VERIFY_SSL: True,
            "refresh_labels_from_device": False,
            CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT,
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_HISTORY_STORAGE_MODE] == HISTORY_MODE_HOME_ASSISTANT
    assert result["data"][CONF_DISCOVERED_DATAPOINTS] == []


async def test_options_flow_switch_to_archive_shows_advanced(hass, mock_client):
    result = await _run_through_groups(hass, mock_client)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_EXPERIENCE_LEVEL: "essential",
            CONF_SCAN_INTERVAL: 60,
            CONF_VERIFY_SSL: True,
            "refresh_labels_from_device": False,
            CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_CRITICAL,
        },
    )
    assert result["type"] == "form"
    assert result["step_id"] == "history_advanced"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HISTORY_SAMPLE_INTERVAL: 120,
            CONF_HISTORY_RETENTION_DAYS: 365,
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"][CONF_HISTORY_STORAGE_MODE] == HISTORY_MODE_CRITICAL
    assert result["data"][CONF_HISTORY_SAMPLE_INTERVAL] == 120
    assert result["data"][CONF_HISTORY_RETENTION_DAYS] == 365
    assert result["data"][CONF_DISCOVERED_DATAPOINTS] == []


async def test_existing_entry_without_history_defaults_to_home_assistant(hass, mock_client):
    result = await _run_through_groups(hass, mock_client)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
    )
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    # Simulate a pre-existing entry without history options by mutating the
    # entry directly. This avoids triggering a reload that would try to set up
    # a real connection.
    entry.options = {
        CONF_EXPERIENCE_LEVEL: "essential",
        CONF_GROUPS: [],
        CONF_SCAN_INTERVAL: 30,
        CONF_VERIFY_SSL: False,
        CONF_REFRESH_LABELS: False,
        CONF_DISCOVERED_DATAPOINTS: [],
        CONF_ADHOC_OIDS: [],
    }

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    # Default should be preselected. Voluptuous wraps defaults in a factory.
    schema = result["data_schema"].schema
    mode_field = next(k for k in schema if k.schema == CONF_HISTORY_STORAGE_MODE)
    default = mode_field.default() if callable(mode_field.default) else mode_field.default
    assert default == DEFAULT_HISTORY_STORAGE_MODE
