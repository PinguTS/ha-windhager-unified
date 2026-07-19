"""Tests for the options-flow rescan feature."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries

from custom_components.windhager_unified.const import (
    CONF_DISCOVERED_DATAPOINTS,
    CONF_EXCLUDED_OIDS,
    CONF_EXPERIENCE_LEVEL,
    CONF_GROUPS,
    CONF_HOST,
    CONF_NODE_NAMES,
    CONF_PASSWORD,
    CONF_RESCAN,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    HISTORY_MODE_HOME_ASSISTANT,
)
from custom_components.windhager_unified.discovery import (
    DiscoveredDatapoint,
    DiscoveredGroup,
    DiscoveryResult,
)
from custom_components.windhager_unified.exceptions import WindhagerConnectionError

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

_USER_INPUT = {
    CONF_HOST: "http://192.0.2.10",
    CONF_USERNAME: "Service",
    CONF_PASSWORD: "secret",
    CONF_VERIFY_SSL: False,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}


def _dp(oid: str, api_name: str, group: str = "heating_circuit", function_name: str = "HC") -> dict:
    """Build a serialized discovery row as stored in config_entry.options."""
    return {
        "oid": oid,
        "level_id": 1,
        "write_prot": False,
        "type_id": 13,
        "unit_id": 1,
        "experience_minimum": "essential",
        "api_name": api_name,
        "function_name": function_name,
        "group": group,
    }


def _discovered_datapoint(
    oid: str, api_name: str, function_name: str = "HC"
) -> DiscoveredDatapoint:
    return DiscoveredDatapoint(
        oid=oid,
        level_id=1,
        write_prot=False,
        type_id=13,
        unit_id=1,
        experience_minimum="essential",
        api_name=api_name,
        function_name=function_name,
    )


def _discovery_result(
    datapoints: list[DiscoveredDatapoint], group_id: str = "heating_circuit"
) -> DiscoveryResult:
    return DiscoveryResult(
        boiler_id=65,
        boiler_name="Test Boiler",
        groups=[
            DiscoveredGroup(
                id=group_id,
                label=group_id.replace("_", " ").title(),
                fct_type=14,
                node_ids=[15],
                datapoints=datapoints,
            )
        ],
    )


@pytest.fixture
def mock_client():
    """Patch WindhagerApiClient so no real HTTP is made."""
    with patch("custom_components.windhager_unified.config_flow.WindhagerApiClient") as MockClient:
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance
        yield instance


async def _create_config_entry(hass, mock_client):
    """Run the full config flow and return the created entry."""
    mock_client.async_test_connection = AsyncMock(return_value=True)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = _discovery_result([_discovered_datapoint("1/15/0/0/0/0", "00-000")])
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=_USER_INPUT
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_EXPERIENCE_LEVEL: "expert"}
        )
        # discover -> groups
        while result.get("type") == "form" and result.get("step_id") != "groups":
            result = await hass.config_entries.flow.async_configure(result["flow_id"])
        if result.get("step_id") == "groups":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_GROUPS: []}
            )
        if result.get("step_id") == "history":
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                user_input={"history_storage_mode": HISTORY_MODE_HOME_ASSISTANT},
            )

    assert result["type"] == "create_entry"
    entries = hass.config_entries.async_entries(DOMAIN)
    assert entries
    return entries[0]


async def test_options_rescan_finds_new_datapoint(hass, mock_client):
    """A rescan that finds a new datapoint shows it in the review step and adds it."""
    entry = await _create_config_entry(hass, mock_client)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = _discovery_result(
            [
                _discovered_datapoint("1/15/0/0/0/0", "00-000"),
                _discovered_datapoint("1/15/0/3/1/0", "03-001"),
            ]
        )
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EXPERIENCE_LEVEL: "expert",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_VERIFY_SSL: False,
                CONF_RESCAN: True,
                "history_storage_mode": HISTORY_MODE_HOME_ASSISTANT,
            },
        )
        assert result["type"] == "form"
        assert result["step_id"] == "rescan_review"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"keep_new": ["1/15/0/3/1/0"]},
        )
        assert result["type"] == "create_entry"

    oids = {row["oid"] for row in result["data"][CONF_DISCOVERED_DATAPOINTS]}
    assert "1/15/0/0/0/0" in oids
    assert "1/15/0/3/1/0" in oids
    assert result["data"][CONF_EXCLUDED_OIDS] == []
    assert "heating_circuit" in result["data"][CONF_GROUPS]


async def test_options_rescan_excludes_deselected_new_datapoint(hass, mock_client):
    """Deselected new datapoints are stored in excluded_oids and not offered again."""
    entry = await _create_config_entry(hass, mock_client)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = _discovery_result(
            [
                _discovered_datapoint("1/15/0/0/0/0", "00-000"),
                _discovered_datapoint("1/15/0/3/1/0", "03-001"),
            ]
        )
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EXPERIENCE_LEVEL: "expert",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_VERIFY_SSL: False,
                CONF_RESCAN: True,
                "history_storage_mode": HISTORY_MODE_HOME_ASSISTANT,
            },
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"keep_new": []},
        )
        assert result["data"][CONF_EXCLUDED_OIDS] == ["1/15/0/3/1/0"]

    # Second rescan: the excluded OID is not offered again.
    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = _discovery_result(
            [
                _discovered_datapoint("1/15/0/0/0/0", "00-000"),
                _discovered_datapoint("1/15/0/3/1/0", "03-001"),
            ]
        )
        # Update the entry options so the next rescan sees the exclusion.
        hass.config_entries.async_update_entry(entry, options=result["data"])
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EXPERIENCE_LEVEL: "expert",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_VERIFY_SSL: False,
                CONF_RESCAN: True,
                "history_storage_mode": HISTORY_MODE_HOME_ASSISTANT,
            },
        )
        # No changes after excluding the new datapoint, so it should save directly.
        assert result["type"] == "create_entry"

    oids = {row["oid"] for row in result["data"][CONF_DISCOVERED_DATAPOINTS]}
    assert "1/15/0/3/1/0" not in oids


async def test_options_rescan_can_drop_vanished_datapoint(hass, mock_client):
    """Vanished datapoints are kept by default, but can be dropped in review."""
    entry = await _create_config_entry(hass, mock_client)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = _discovery_result([])
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EXPERIENCE_LEVEL: "expert",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_VERIFY_SSL: False,
                CONF_RESCAN: True,
                "history_storage_mode": HISTORY_MODE_HOME_ASSISTANT,
            },
        )
        assert result["step_id"] == "rescan_review"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"keep_vanished": []},
        )
        assert result["type"] == "create_entry"

    oids = {row["oid"] for row in result["data"][CONF_DISCOVERED_DATAPOINTS]}
    assert "1/15/0/0/0/0" not in oids


async def test_options_rescan_no_changes_saves_directly(hass, mock_client):
    """When discovery returns exactly the same OIDs, no review step is shown."""
    entry = await _create_config_entry(hass, mock_client)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = _discovery_result([_discovered_datapoint("1/15/0/0/0/0", "00-000")])
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EXPERIENCE_LEVEL: "expert",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_VERIFY_SSL: False,
                CONF_RESCAN: True,
                "history_storage_mode": HISTORY_MODE_HOME_ASSISTANT,
            },
        )
        assert result["type"] == "create_entry"

    oids = {row["oid"] for row in result["data"][CONF_DISCOVERED_DATAPOINTS]}
    assert "1/15/0/0/0/0" in oids


async def test_options_rescan_failure_returns_to_init(hass, mock_client):
    """A discovery failure during rescan returns to the init step with an error."""
    entry = await _create_config_entry(hass, mock_client)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.side_effect = WindhagerConnectionError("no route")
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EXPERIENCE_LEVEL: "expert",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_VERIFY_SSL: False,
                CONF_RESCAN: True,
                "history_storage_mode": HISTORY_MODE_HOME_ASSISTANT,
            },
        )
        assert result["type"] == "form"
        assert result["step_id"] == "init"
        assert result["errors"]["base"] == "cannot_connect"

    # Options must be unchanged.
    assert {row["oid"] for row in entry.options[CONF_DISCOVERED_DATAPOINTS]} == {"1/15/0/0/0/0"}


async def test_options_rescan_adds_new_group(hass, mock_client):
    """A newly discovered group is appended to the selected groups automatically."""
    entry = await _create_config_entry(hass, mock_client)

    with patch(
        "custom_components.windhager_unified.config_flow.discover",
        new_callable=AsyncMock,
    ) as disc:
        disc.return_value = DiscoveryResult(
            boiler_id=65,
            boiler_name="Test Boiler",
            groups=[
                DiscoveredGroup(
                    id="buffer",
                    label="Buffer",
                    fct_type=15,
                    node_ids=[16],
                    datapoints=[_discovered_datapoint("1/16/0/0/15/0", "00-015", "Buffer")],
                ),
                DiscoveredGroup(
                    id="heating_circuit",
                    label="Heating circuit",
                    fct_type=14,
                    node_ids=[15],
                    datapoints=[_discovered_datapoint("1/15/0/0/0/0", "00-000")],
                ),
            ],
        )
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_EXPERIENCE_LEVEL: "expert",
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                CONF_VERIFY_SSL: False,
                CONF_RESCAN: True,
                "history_storage_mode": HISTORY_MODE_HOME_ASSISTANT,
            },
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={"keep_new": ["1/16/0/0/15/0"]},
        )
        assert result["type"] == "create_entry"

    assert "buffer" in result["data"][CONF_GROUPS]
    assert "heating_circuit" in result["data"][CONF_GROUPS]
    assert result["data"][CONF_NODE_NAMES] == {}
