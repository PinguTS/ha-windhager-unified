"""Tests for config flow and options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries

from custom_components.windhager_unified.const import (
    CONF_ADHOC_OIDS,
    CONF_DISCOVERED_DATAPOINTS,
    CONF_HISTORY_STORAGE_MODE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HISTORY_MODE_HOME_ASSISTANT,
)
from custom_components.windhager_unified.exceptions import (
    WindhagerAuthError,
    WindhagerConnectionError,
    WindhagerTimeoutError,
)

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
    """Patch WindhagerApiClient so no real HTTP is made."""
    with patch("custom_components.windhager_unified.config_flow.WindhagerApiClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance
        yield instance


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


async def test_config_flow_success(hass, mock_client):
    """Full success path through the multi-step config flow."""
    from custom_components.windhager_unified.const import CONF_EXPERIENCE_LEVEL, CONF_GROUPS
    from custom_components.windhager_unified.discovery import DiscoveryResult

    mock_client.async_test_connection = AsyncMock(return_value=True)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = DiscoveryResult(boiler_id=None, boiler_name=None, groups=[])
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=_USER_INPUT
        )
        assert result["step_id"] == "experience"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_EXPERIENCE_LEVEL: "essential"}
        )
        # Navigate through discover/groups/history steps until entry is created
        while result.get("type") == "form" and result.get("step_id") != "groups":
            result = await hass.config_entries.flow.async_configure(result["flow_id"])

        if result.get("step_id") == "groups":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_GROUPS: []}
            )

        # Complete the new history storage step (default = Home Assistant only).
        if result.get("step_id") == "history":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
            )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_HOST] == "http://192.0.2.10"

    entries = hass.config_entries.async_entries(DOMAIN)
    assert entries
    assert CONF_DISCOVERED_DATAPOINTS in entries[0].options
    assert CONF_ADHOC_OIDS in entries[0].options
    assert entries[0].options[CONF_ADHOC_OIDS] == []


# ---------------------------------------------------------------------------
# Auth failure → invalid_auth error
# ---------------------------------------------------------------------------


async def test_config_flow_invalid_auth(hass, mock_client):
    mock_client.async_test_connection = AsyncMock(side_effect=WindhagerAuthError("bad"))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    assert result2["type"] == "form"
    assert result2["errors"]["base"] == "invalid_auth"


# ---------------------------------------------------------------------------
# Connection failure → cannot_connect error
# ---------------------------------------------------------------------------


async def test_config_flow_cannot_connect(hass, mock_client):
    mock_client.async_test_connection = AsyncMock(side_effect=WindhagerConnectionError("no route"))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    assert result2["type"] == "form"
    assert result2["errors"]["base"] == "cannot_connect"


async def test_config_flow_timeout(hass, mock_client):
    mock_client.async_test_connection = AsyncMock(side_effect=WindhagerTimeoutError("timed out"))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    assert result2["type"] == "form"
    assert result2["errors"]["base"] == "cannot_connect"


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


async def test_options_flow_changes_scan_interval(hass, mock_client):
    from custom_components.windhager_unified.const import CONF_EXPERIENCE_LEVEL, CONF_GROUPS
    from custom_components.windhager_unified.discovery import DiscoveryResult

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
        if result.get("step_id") == "history":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
            )

    entries = hass.config_entries.async_entries(DOMAIN)
    assert entries
    entry = entries[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 60,
            CONF_VERIFY_SSL: True,
            CONF_EXPERIENCE_LEVEL: "essential",
            "refresh_labels_from_device": False,
            CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT,
        },
    )
    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_SCAN_INTERVAL] == 60
    assert CONF_DISCOVERED_DATAPOINTS in result2["data"]
    assert result2["data"][CONF_DISCOVERED_DATAPOINTS] == []


async def test_config_flow_discover_passes_experience_tier(hass, mock_client):
    """``discover`` must receive the user's selected experience tier."""
    from custom_components.windhager_unified.const import CONF_EXPERIENCE_LEVEL, CONF_GROUPS
    from custom_components.windhager_unified.discovery import DiscoveryResult

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
            result["flow_id"], user_input={CONF_EXPERIENCE_LEVEL: "comfort"}
        )
        while result.get("type") == "form" and result.get("step_id") != "groups":
            result = await hass.config_entries.flow.async_configure(result["flow_id"])
        if result.get("step_id") == "groups":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_GROUPS: []}
            )
        if result.get("step_id") == "history":
            await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
            )

    disc.assert_awaited()
    assert disc.await_args.kwargs["experience_tier"] == "comfort"
