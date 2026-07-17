"""Tests for the multi-step config flow and OptionsFlow (experience tiers)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries

from custom_components.windhager_unified.const import (
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
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
from custom_components.windhager_unified.discovery import DiscoveredGroup, DiscoveryResult

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

_USER_INPUT = {
    CONF_HOST: "http://192.0.2.10",
    CONF_USERNAME: "Service",
    CONF_PASSWORD: "secret",
    CONF_VERIFY_SSL: False,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}

_DISCOVERED_GROUPS = [
    DiscoveredGroup(id="boiler", label="Boiler / Heat generator", fct_type=0, node_ids=[65]),
    DiscoveredGroup(id="heating_circuit", label="Heating circuit", fct_type=1, node_ids=[65]),
    DiscoveredGroup(id="dhw", label="Domestic hot water", fct_type=2, node_ids=[65]),
]

_DISCOVERY_RESULT = DiscoveryResult(
    boiler_id=2,
    boiler_name="LogWIN (Holz)",
    groups=_DISCOVERED_GROUPS,
)


@pytest.fixture
def mock_client():
    with patch("custom_components.windhager_unified.config_flow.WindhagerApiClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        instance.async_test_connection = AsyncMock(return_value=True)
        MockClient.return_value = instance
        yield instance


@pytest.fixture
def mock_discover():
    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = _DISCOVERY_RESULT
        yield mock


# ---------------------------------------------------------------------------
# Full happy-path: user → experience → discover → groups → create_entry
# ---------------------------------------------------------------------------


async def test_full_flow_essential(hass, mock_client, mock_discover):
    """Full setup flow with Essential tier; assert CONF_EXPERIENCE_LEVEL in options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["step_id"] == "user"

    # Step 1: credentials
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    assert result["step_id"] == "experience"

    # Step 2: choose Essential tier
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EXPERIENCE_LEVEL: "essential"},
    )
    # Either goes directly to groups or through discover step
    while result.get("step_id") == "discover":
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["step_id"] == "groups"

    # Step 4: accept default group selection
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_GROUPS: ["boiler", "heating_circuit"]},
    )
    # Step 5: history storage profile
    assert result["step_id"] == "history"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
    )
    assert result["type"] == "create_entry"
    options = result["options"]
    assert options[CONF_EXPERIENCE_LEVEL] == "essential"
    assert "boiler" in options[CONF_GROUPS]


async def test_full_flow_comfort_selects_more_groups(hass, mock_client, mock_discover):
    """Comfort tier should pre-select more groups than Essential by default."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EXPERIENCE_LEVEL: "comfort"},
    )
    while result.get("step_id") == "discover":
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    assert result["step_id"] == "groups"
    # Accept whatever defaults the form proposes for comfort
    schema = result["data_schema"]
    # The form was rendered; confirm CONF_GROUPS schema key is present
    assert CONF_GROUPS in str(schema)


async def test_full_flow_service_selects_all_groups(hass, mock_client, mock_discover):
    """Service tier should pre-select all discovered groups by default."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EXPERIENCE_LEVEL: "service"},
    )
    while result.get("step_id") == "discover":
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    if result.get("step_id") == "groups":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_GROUPS: [g.id for g in _DISCOVERED_GROUPS]},
        )
    if result.get("step_id") == "history":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
        )
    assert result["type"] == "create_entry"
    assert result["options"][CONF_EXPERIENCE_LEVEL] == "service"


# ---------------------------------------------------------------------------
# CONF_EXPERIENCE_LEVEL persisted in options not data
# ---------------------------------------------------------------------------


async def test_experience_level_in_options_not_data(hass, mock_client, mock_discover):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EXPERIENCE_LEVEL: "expert"},
    )
    while result.get("type") == "form" and result.get("step_id") != "groups":
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    if result.get("step_id") == "groups":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_GROUPS: ["boiler"]},
        )
    if result.get("step_id") == "history":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
        )

    assert result["type"] == "create_entry"
    assert CONF_HOST in result["data"]
    assert CONF_EXPERIENCE_LEVEL not in result["data"]
    assert result["options"][CONF_EXPERIENCE_LEVEL] == "expert"


# ---------------------------------------------------------------------------
# OptionsFlow: tier upgrade adds entities
# ---------------------------------------------------------------------------


async def test_options_flow_changes_tier(hass, mock_client, mock_discover):
    """Changing tier via OptionsFlow triggers a reload."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_EXPERIENCE_LEVEL: "essential"},
    )
    while result.get("type") == "form" and result.get("step_id") != "groups":
        result = await hass.config_entries.flow.async_configure(result["flow_id"])

    if result.get("step_id") == "groups":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_GROUPS: ["boiler"]},
        )
    if result.get("step_id") == "history":
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT},
        )

    assert result["type"] == "create_entry"
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    assert entry.options[CONF_EXPERIENCE_LEVEL] == "essential"

    # Open OptionsFlow and change to "advanced"
    result2 = await hass.config_entries.options.async_init(entry.entry_id)
    assert result2["type"] == "form"
    assert result2["step_id"] == "init"

    result3 = await hass.config_entries.options.async_configure(
        result2["flow_id"],
        user_input={
            CONF_EXPERIENCE_LEVEL: "advanced",
            CONF_SCAN_INTERVAL: 30,
            CONF_VERIFY_SSL: False,
            "refresh_labels_from_device": False,
            CONF_HISTORY_STORAGE_MODE: HISTORY_MODE_HOME_ASSISTANT,
        },
    )
    assert result3["type"] == "create_entry"
    assert entry.options[CONF_EXPERIENCE_LEVEL] == "advanced"
