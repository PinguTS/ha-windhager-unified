"""Tests for WindhagerCoordinator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.windhager_unified.coordinator import (
    WindhagerCoordinator,
    _normalize_lon_datapoint_value,
    _passes_tier,
    _tier_index,
)
from custom_components.windhager_unified.exceptions import (
    WindhagerApiError,
    WindhagerAuthError,
    WindhagerConnectionError,
)
from custom_components.windhager_unified.tier_lookup import GN_MN_OVERRIDES

MINIMAL_OIDS = [
    {
        "oid": "1/65/0/0/0/0",
        "key": "logwin.boiler_temp",
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "i18n": {"en": "Boiler Temperature", "de": "Kesseltemperatur"},
        "hint_node": "LogWIN",
        "group": "boiler",
        "fct_type": 10,
        "experience_minimum": "essential",
    }
]

MINIMAL_RESTAPI = {
    "heartbeat": [
        {
            "endpoint": "/InfoWinHeartbeat/api/1.0/heartbeat",
            "key": "heartbeat.status",
            "entity_type": "sensor",
            "name": "Heartbeat Status",
            "i18n": {"en": "Heartbeat Status", "de": "Heartbeat Status"},
            "group": "heartbeat",
            "experience_minimum": "advanced",
        }
    ]
}


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.loop = MagicMock()
    return hass


@pytest.fixture
def coordinator(mock_hass):
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://test-host",
        username="user",
        password="pass",
        verify_ssl=False,
        scan_interval=30,
        experience_level="advanced",  # advanced sees essential LON + advanced REST
    )
    coord._apply_static_config(MINIMAL_OIDS, MINIMAL_RESTAPI)
    return coord


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


def test_coordinator_loads_datapoints(coordinator):
    assert coordinator.datapoints == MINIMAL_OIDS


def test_coordinator_loads_restapi_endpoints(coordinator):
    assert "heartbeat" in coordinator.restapi_endpoints


def test_coordinator_host(coordinator):
    assert coordinator.api_client.host == "http://test-host"


# ---------------------------------------------------------------------------
# Data update — LON polling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_lon_datapoint_success(coordinator):
    coordinator.api_client.async_get_datapoint = AsyncMock(return_value={"value": 75.5})
    coordinator.api_client.async_get_heartbeat = AsyncMock(return_value={"status": "ok"})

    with patch.object(coordinator, "_call_restapi_endpoint", new_callable=AsyncMock) as mock_rest:
        mock_rest.return_value = {"status": "ok"}
        result = await coordinator._async_update_data()

    assert result["logwin.boiler_temp"] == 75.5


@pytest.mark.asyncio
async def test_update_lon_datapoint_hyphen_string_becomes_none(coordinator):
    """API may return '-' for unavailable numeric readings (documented value: string)."""
    coordinator.api_client.async_get_datapoint = AsyncMock(return_value={"value": "-"})
    with patch.object(coordinator, "_call_restapi_endpoint", new_callable=AsyncMock) as mock_rest:
        mock_rest.return_value = None
        result = await coordinator._async_update_data()

    assert result.get("logwin.boiler_temp") is None


def test_normalize_lon_datapoint_value_hyphen_and_blank():
    assert _normalize_lon_datapoint_value("-") is None
    assert _normalize_lon_datapoint_value(" - ") is None
    assert _normalize_lon_datapoint_value("") is None
    assert _normalize_lon_datapoint_value("  ") is None
    assert _normalize_lon_datapoint_value("42") == "42"
    assert _normalize_lon_datapoint_value(42) == 42
    assert _normalize_lon_datapoint_value(42.5) == 42.5
    assert _normalize_lon_datapoint_value(None) is None


@pytest.mark.asyncio
async def test_update_lon_single_failure_does_not_abort(coordinator):
    """A failing LON datapoint should log a warning, not raise UpdateFailed."""
    coordinator.api_client.async_get_datapoint = AsyncMock(
        side_effect=WindhagerConnectionError("no route")
    )
    with patch.object(coordinator, "_call_restapi_endpoint", new_callable=AsyncMock) as mock_rest:
        mock_rest.return_value = None
        result = await coordinator._async_update_data()

    # Key absent (not set to None) when fetch fails
    assert "logwin.boiler_temp" not in result


@pytest.mark.asyncio
async def test_update_auth_failure_raises_update_failed(coordinator):
    """Auth errors should bubble up as UpdateFailed."""
    from homeassistant.helpers.update_coordinator import UpdateFailed

    coordinator.api_client.async_get_datapoint = AsyncMock(
        side_effect=WindhagerAuthError("bad password")
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


# ---------------------------------------------------------------------------
# Data update — RestAPI sensors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_restapi_sensor_success(coordinator):
    coordinator.api_client.async_get_datapoint = AsyncMock(return_value={"value": 75.5})
    coordinator.api_client.async_get_heartbeat = AsyncMock(return_value={"status": "active"})

    result = await coordinator._async_update_data()

    assert result.get("heartbeat.status") == "active"


@pytest.mark.asyncio
async def test_update_restapi_sensor_failure_continues(coordinator):
    """A RestAPI sensor failure should not stop the full update cycle."""
    coordinator.api_client.async_get_datapoint = AsyncMock(return_value={"value": 75.5})
    coordinator.api_client.async_get_heartbeat = AsyncMock(
        side_effect=WindhagerConnectionError("timeout")
    )

    result = await coordinator._async_update_data()
    # LON data should still be present
    assert result["logwin.boiler_temp"] == 75.5
    # Heartbeat absent — not None
    assert "heartbeat.status" not in result


# ---------------------------------------------------------------------------
# _call_restapi_endpoint dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_system_time(coordinator):
    coordinator.api_client.async_get_system_time = AsyncMock(
        return_value={"time": "2024-01-01T00:00:00Z"}
    )
    result = await coordinator._call_restapi_endpoint("/WsAdmin/api/1.0/systemtime")
    assert result == {"time": "2024-01-01T00:00:00Z"}


@pytest.mark.asyncio
async def test_dispatch_heartbeat(coordinator):
    coordinator.api_client.async_get_heartbeat = AsyncMock(return_value={"status": "ok"})
    result = await coordinator._call_restapi_endpoint("/InfoWinHeartbeat/api/1.0/heartbeat")
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_dispatch_generic_fallback(coordinator):
    coordinator.api_client.async_request = AsyncMock(return_value={"custom": True})
    result = await coordinator._call_restapi_endpoint("/some/unknown/endpoint")
    coordinator.api_client.async_request.assert_called_once_with("GET", "/some/unknown/endpoint")
    assert result == {"custom": True}


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def test_load_yaml_missing_file():
    result = WindhagerCoordinator._load_yaml(Path("/nonexistent/path.yaml"), "datapoints")
    assert result == []


def test_load_yaml_invalid_root_key(tmp_path):
    f = tmp_path / "test.yaml"
    f.write_text("other_key: []\n")
    result = WindhagerCoordinator._load_yaml(f, "datapoints")
    assert result == []


# ---------------------------------------------------------------------------
# Tier index helpers
# ---------------------------------------------------------------------------


def test_tier_index_ordering():
    assert _tier_index("essential") < _tier_index("comfort")
    assert _tier_index("comfort") < _tier_index("advanced")
    assert _tier_index("advanced") < _tier_index("expert")
    assert _tier_index("expert") < _tier_index("service")


def test_passes_tier_true():
    assert _passes_tier("essential", "essential", "expert") is True
    assert _passes_tier("essential", "service", "expert") is True
    assert _passes_tier("comfort", "comfort", "expert") is True
    assert _passes_tier("advanced", "service", "expert") is True


def test_passes_tier_false():
    assert _passes_tier("advanced", "essential", "expert") is False
    assert _passes_tier("service", "expert", "service") is False
    assert _passes_tier("expert", "comfort", "expert") is False


# ---------------------------------------------------------------------------
# Experience tier filtering on init
# ---------------------------------------------------------------------------


def test_coordinator_filters_by_experience_essential(mock_hass):
    """Essential tier only sees essential-minimum datapoints."""
    all_oids = [
        {**MINIMAL_OIDS[0], "experience_minimum": "essential"},
        {
            **MINIMAL_OIDS[0],
            "key": "expert_dp",
            "oid": "1/65/0/0/1/0",
            "experience_minimum": "expert",
        },
    ]
    all_restapi = {
        "heartbeat": [
            {**MINIMAL_RESTAPI["heartbeat"][0], "experience_minimum": "advanced"},
        ]
    }
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://test",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="essential",
    )
    coord._apply_static_config(all_oids, all_restapi)

    keys = [dp["key"] for dp in coord.datapoints]
    assert "logwin.boiler_temp" in keys
    assert "expert_dp" not in keys
    # REST heartbeat (advanced) should be filtered out at essential
    assert "heartbeat" not in coord.restapi_endpoints


def test_coordinator_filters_by_group(mock_hass):
    """With groups=["heating_circuit"], boiler datapoints are excluded."""
    all_oids = [
        {**MINIMAL_OIDS[0], "group": "boiler", "experience_minimum": "essential"},
        {
            **MINIMAL_OIDS[0],
            "key": "hc_dp",
            "oid": "1/65/0/1/0/0",
            "group": "heating_circuit",
            "experience_minimum": "essential",
        },
    ]
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://test",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="expert",
        groups=["heating_circuit"],
    )
    coord._apply_static_config(all_oids, {})

    keys = [dp["key"] for dp in coord.datapoints]
    assert "hc_dp" in keys
    assert "logwin.boiler_temp" not in keys


# ---------------------------------------------------------------------------
# unknown_oids tracking (404 → recorded, not retried)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_oids_tracked_on_404(coordinator):

    coordinator.api_client.async_get_datapoint = AsyncMock(
        side_effect=WindhagerApiError("not found", status=404)
    )
    with patch.object(coordinator, "_call_restapi_endpoint", new_callable=AsyncMock) as mock_rest:
        mock_rest.return_value = None
        await coordinator._async_update_data()

    assert "1/65/0/0/0/0" in coordinator.unknown_oids


@pytest.mark.asyncio
async def test_unknown_oids_not_set_for_non_404(coordinator):
    coordinator.api_client.async_get_datapoint = AsyncMock(
        side_effect=WindhagerConnectionError("timeout")
    )
    with patch.object(coordinator, "_call_restapi_endpoint", new_callable=AsyncMock) as mock_rest:
        mock_rest.return_value = None
        await coordinator._async_update_data()

    assert "1/65/0/0/0/0" not in coordinator.unknown_oids


# ---------------------------------------------------------------------------
# Discovery whitelist + ad-hoc coercion
# ---------------------------------------------------------------------------


def test_coerce_adhoc_entries_string_and_dict():
    assert WindhagerCoordinator._coerce_adhoc_entries(None) == []
    assert WindhagerCoordinator._coerce_adhoc_entries(["1/2/3/4/5/6"]) == [
        {"oid": "1/2/3/4/5/6", "group": "boiler"}
    ]
    rows = WindhagerCoordinator._coerce_adhoc_entries([{"oid": "1/1/1/1/1/1", "group": "buffer"}])
    assert rows == [{"oid": "1/1/1/1/1/1", "group": "buffer"}]


def test_build_lon_datapoints_easy_tier_whitelist(mock_hass):
    """Essential + non-empty discovered list restricts YAML OIDs to the whitelist."""
    all_oids = [
        {
            "oid": "1/1/0/0/0/0",
            "key": "k1",
            "group": "boiler",
            "experience_minimum": "essential",
            "i18n": {"en": "A"},
        },
        {
            "oid": "1/2/0/0/0/0",
            "key": "k2",
            "group": "boiler",
            "experience_minimum": "essential",
            "i18n": {"en": "B"},
        },
    ]
    discovered = [{"oid": "1/1/0/0/0/0", "group": "boiler", "experience_minimum": "essential"}]
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://test",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="essential",
        discovered_datapoints=discovered,
    )
    coord._apply_static_config(all_oids, {})
    assert [d["key"] for d in coord.datapoints] == ["k1"]


def test_build_lon_datapoints_expert_adds_discovery_only_synthetic(mock_hass):
    all_oids = [
        {
            "oid": "1/1/0/0/0/0",
            "key": "k1",
            "group": "boiler",
            "experience_minimum": "expert",
            "i18n": {"en": "A"},
        },
    ]
    discovered = [
        {
            "oid": "9/9/0/9/9/0",
            "group": "boiler",
            "experience_minimum": "comfort",
            "api_name": "Extra",
            "type_id": 1,
            "unit_id": 2,
            "write_prot": True,
        }
    ]
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://test",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="expert",
        discovered_datapoints=discovered,
    )
    coord._apply_static_config(all_oids, {})
    keys = {d["oid"]: d for d in coord.datapoints}
    assert "1/1/0/0/0/0" in keys
    assert "9/9/0/9/9/0" in keys
    assert keys["9/9/0/9/9/0"].get("discovered") is True


def test_build_lon_datapoints_discovery_gap_preserves_yaml_unit(mock_hass):
    """When discovery fills a gap for an OID known in oids.yaml but blocked by tier,
    the yaml metadata (unit, device_class, i18n) must be used — not a bare synthetic.

    Reproduces: Puffertemperatur Oben/Unten (experience_minimum=expert in oids.yaml)
    appearing without °C unit at comfort tier because discovery created a
    _synthetic_lon_datapoint_from_discovery_row (unit=None) instead of borrowing
    the yaml entry's unit.
    """
    yaml_entry = {
        "oid": "1/16/0/0/15/0",
        "key": "lon_1_16_0_0_15_0",
        "group": "buffer",
        "experience_minimum": "expert",  # would be filtered at comfort tier
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "i18n": {"de": "Puffertemperatur Oben", "en": "Accumulator-temp. top"},
    }
    # Discovery found the same OID and assessed it as essential
    discovered = [
        {
            "oid": "1/16/0/0/15/0",
            "group": "buffer",
            "experience_minimum": "essential",
            "api_name": "00-015",
            "type_id": 13,
            "unit_id": 1,
            "write_prot": True,
        }
    ]
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://test",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="comfort",  # below expert → yaml entry is filtered out
        discovered_datapoints=discovered,
    )
    coord._apply_static_config([yaml_entry], {})
    assert len(coord.datapoints) == 1
    dp = coord.datapoints[0]
    assert dp["oid"] == "1/16/0/0/15/0"
    assert dp.get("unit") == "°C", "unit must be preserved from oids.yaml"
    assert dp.get("device_class") == "temperature"
    assert dp.get("i18n", {}).get("de") == "Puffertemperatur Oben"


# ---------------------------------------------------------------------------
# _deduplicate_cross_node
# ---------------------------------------------------------------------------


def _dp(oid: str, group: str) -> dict:
    return {"oid": oid, "group": group, "key": f"k_{oid}"}


def test_deduplicate_same_node_different_fct_kept():
    """HC1 and HC2 on the same node must not be deduplicated."""
    hc1 = _dp("1/15/0/3/50/0", "heating_circuit")  # node 15, fct 0
    hc2 = _dp("1/15/1/3/50/0", "heating_circuit")  # node 15, fct 1
    result = WindhagerCoordinator._deduplicate_cross_node([hc1, hc2])
    oids = {d["oid"] for d in result}
    assert "1/15/0/3/50/0" in oids
    assert "1/15/1/3/50/0" in oids


def test_deduplicate_cross_node_canonical_group_buffer(tmp_path):
    """Buffer temperature from multiple nodes: only the buffer-group instance is kept."""
    assert (0, 15) in GN_MN_OVERRIDES, "canonical_group for 0:15 must be configured"
    assert GN_MN_OVERRIDES[(0, 15)]["canonical_group"] == "buffer"

    boiler_inst = _dp("1/65/0/0/15/0", "boiler")  # node 65
    buffer_inst = _dp("1/16/0/0/15/0", "buffer")  # node 16
    hc1_inst = _dp("1/15/0/0/15/0", "heating_circuit")
    hc2_inst = _dp("1/15/1/0/15/0", "heating_circuit")

    result = WindhagerCoordinator._deduplicate_cross_node(
        [boiler_inst, buffer_inst, hc1_inst, hc2_inst]
    )
    oids = {d["oid"] for d in result}
    assert "1/16/0/0/15/0" in oids, "buffer-group (node 16) instance must be kept"
    assert "1/65/0/0/15/0" not in oids, "boiler node duplicate must be removed"
    assert "1/15/0/0/15/0" not in oids
    assert "1/15/1/0/15/0" not in oids


def test_deduplicate_cross_node_canonical_group_boiler():
    """Boiler temperature: only the boiler-group instance is kept."""
    assert (0, 7) in GN_MN_OVERRIDES
    assert GN_MN_OVERRIDES[(0, 7)]["canonical_group"] == "boiler"

    boiler_inst = _dp("1/65/0/0/7/0", "boiler")
    pump_inst = _dp("1/16/1/0/7/0", "boiler_loading_pump")
    buffer_inst = _dp("1/16/0/0/7/0", "buffer")

    result = WindhagerCoordinator._deduplicate_cross_node([boiler_inst, pump_inst, buffer_inst])
    oids = {d["oid"] for d in result}
    assert "1/65/0/0/7/0" in oids
    assert "1/16/1/0/7/0" not in oids
    assert "1/16/0/0/7/0" not in oids


def test_deduplicate_cross_node_fallback_when_canonical_missing():
    """If the canonical group is not in the result, all instances are kept."""
    # Use 0:15 (canonical=buffer), but supply no buffer instance.
    boiler_inst = _dp("1/65/0/0/15/0", "boiler")
    hc_inst = _dp("1/15/0/0/15/0", "heating_circuit")

    result = WindhagerCoordinator._deduplicate_cross_node([boiler_inst, hc_inst])
    oids = {d["oid"] for d in result}
    # Both kept because canonical group "buffer" was not found.
    assert "1/65/0/0/15/0" in oids
    assert "1/15/0/0/15/0" in oids


def test_deduplicate_cross_node_no_canonical_configured():
    """Pairs without canonical_group config keep all instances unchanged."""
    # gn=99, mn=99 — not in GN_MN_OVERRIDES
    a = _dp("1/10/0/99/99/0", "boiler")
    b = _dp("1/20/0/99/99/0", "buffer")

    result = WindhagerCoordinator._deduplicate_cross_node([a, b])
    assert len(result) == 2


# ---------------------------------------------------------------------------
# _compute_oid_disambiguators
# ---------------------------------------------------------------------------


def test_compute_disambiguators_unique_gn_mn_no_suffix():
    """Datapoints with unique (gn, mn) must not get a suffix."""
    dps = [
        {"oid": "1/65/0/0/7/0"},  # gn=0 mn=7
        {"oid": "1/65/0/0/15/0"},  # gn=0 mn=15 — only once
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert result == {}


def test_compute_disambiguators_different_nodes_sorted_by_node():
    """Multi-node duplicates without function_name fall back to numeric suffixes."""
    dps = [
        {"oid": "1/65/0/0/7/0"},  # node 65
        {"oid": "1/10/0/0/7/0"},  # node 10 — lower, gets "1"
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert result["1/10/0/0/7/0"] == "1"  # node 10 first
    assert result["1/65/0/0/7/0"] == "2"  # node 65 second


def test_compute_disambiguators_same_node_different_fct():
    """HC1 and HC2 (same node, different fct) without function_name → numeric."""
    dps = [
        {"oid": "1/15/0/3/50/0"},  # node 15 fct 0
        {"oid": "1/15/1/3/50/0"},  # node 15 fct 1
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert result["1/15/0/3/50/0"] == "1"
    assert result["1/15/1/3/50/0"] == "2"


def test_compute_disambiguators_three_nodes():
    """Three-way cross-node duplicate without function_name → suffixes 1, 2, 3."""
    dps = [
        {"oid": "1/65/0/23/87/0"},  # node 65
        {"oid": "1/16/0/23/87/0"},  # node 16
        {"oid": "1/15/0/23/87/0"},  # node 15
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert set(result.values()) == {"1", "2", "3"}
    assert result["1/15/0/23/87/0"] == "1"
    assert result["1/16/0/23/87/0"] == "2"
    assert result["1/65/0/23/87/0"] == "3"


def test_compute_disambiguators_unique_function_names():
    """Two boilers with distinct function names → labels are the names themselves."""
    dps = [
        {"oid": "1/10/0/0/7/0", "function_name": "BioWIN"},
        {"oid": "1/65/0/0/7/0", "function_name": "LogWIN"},
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert result["1/10/0/0/7/0"] == "BioWIN"
    assert result["1/65/0/0/7/0"] == "LogWIN"


def test_compute_disambiguators_duplicate_function_names_get_counter():
    """When two function blocks share the same name a counter is appended."""
    dps = [
        {"oid": "1/15/0/3/50/0", "function_name": "Kessel"},
        {"oid": "1/65/0/3/50/0", "function_name": "Kessel"},
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert result["1/15/0/3/50/0"] == "Kessel 1"
    assert result["1/65/0/3/50/0"] == "Kessel 2"


def test_compute_disambiguators_hc_unique_names():
    """HC1 / HC2 already have distinct function names — used as-is."""
    dps = [
        {"oid": "1/15/0/3/50/0", "function_name": "Heizkreis 1"},
        {"oid": "1/15/1/3/50/0", "function_name": "Heizkreis 2"},
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert result["1/15/0/3/50/0"] == "Heizkreis 1"
    assert result["1/15/1/3/50/0"] == "Heizkreis 2"


def test_compute_disambiguators_partial_function_names_falls_back_to_number():
    """If any datapoint lacks a function_name, all fall back to numeric suffixes."""
    dps = [
        {"oid": "1/10/0/0/7/0", "function_name": "BioWIN"},
        {"oid": "1/65/0/0/7/0"},  # no function_name
    ]
    result = WindhagerCoordinator._compute_oid_disambiguators(dps)
    assert result["1/10/0/0/7/0"] == "1"
    assert result["1/65/0/0/7/0"] == "2"


# ---------------------------------------------------------------------------
# get_entity_name
# ---------------------------------------------------------------------------


def test_get_entity_name_no_disambiguation(mock_hass):
    """When a (gn, mn) is unique, get_entity_name returns the base name."""
    oids = [
        {
            "oid": "1/65/0/0/7/0",
            "key": "k",
            "group": "boiler",
            "experience_minimum": "essential",
            "i18n": {"en": "Boiler Temp"},
        }
    ]
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://t",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="advanced",
    )
    coord._apply_static_config(oids, {})
    name = coord.get_entity_name("1/65/0/0/7/0", "en", {"en": "Boiler Temp"}, "k")
    assert name == "Boiler Temp"
    assert "(1)" not in name


def test_get_entity_name_with_numeric_disambiguation(mock_hass):
    """Without function_name the fallback is a parenthesised number suffix."""
    oids = [
        {
            "oid": "1/10/0/0/7/0",
            "key": "k",
            "group": "boiler",
            "experience_minimum": "essential",
            "i18n": {"en": "Boiler Temp"},
        },
        {
            "oid": "1/65/0/0/7/0",
            "key": "k2",
            "group": "boiler",
            "experience_minimum": "essential",
            "i18n": {"en": "Boiler Temp"},
        },
    ]
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://t",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="advanced",
    )
    coord._apply_static_config(oids, {})
    name_10 = coord.get_entity_name("1/10/0/0/7/0", "en", {"en": "Boiler Temp"}, "k")
    name_65 = coord.get_entity_name("1/65/0/0/7/0", "en", {"en": "Boiler Temp"}, "k2")
    assert name_10 == "Boiler Temp (1)"
    assert name_65 == "Boiler Temp (2)"


def test_get_entity_name_with_function_name_prefix(mock_hass):
    """With function_name the prefix pattern 'FunctionName Base' is used."""
    oids = [
        {
            "oid": "1/10/0/0/7/0",
            "key": "k",
            "group": "boiler",
            "experience_minimum": "essential",
            "i18n": {"en": "Kesseltemperatur"},
            "function_name": "BioWIN",
        },
        {
            "oid": "1/65/0/0/7/0",
            "key": "k2",
            "group": "boiler",
            "experience_minimum": "essential",
            "i18n": {"en": "Kesseltemperatur"},
            "function_name": "LogWIN",
        },
    ]
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://t",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="advanced",
    )
    coord._apply_static_config(oids, {})
    name_10 = coord.get_entity_name("1/10/0/0/7/0", "en", {"en": "Kesseltemperatur"}, "k")
    name_65 = coord.get_entity_name("1/65/0/0/7/0", "en", {"en": "Kesseltemperatur"}, "k2")
    assert name_10 == "BioWIN Kesseltemperatur"
    assert name_65 == "LogWIN Kesseltemperatur"


def test_deduplicate_heating_circuit_flow_temp_keeps_both_instances():
    """HC1 and HC2 flow temperatures are distinct physical sensors — both kept."""
    assert (1, 7) in GN_MN_OVERRIDES
    assert GN_MN_OVERRIDES[(1, 7)]["canonical_group"] == "heating_circuit"

    pump_inst = _dp("1/16/1/1/7/0", "boiler_loading_pump")  # different node
    buf_inst = _dp("1/16/0/1/7/0", "buffer")  # different node
    hc1_inst = _dp("1/15/0/1/7/0", "heating_circuit")  # node 15, fct 0
    hc2_inst = _dp("1/15/1/1/7/0", "heating_circuit")  # node 15, fct 1

    result = WindhagerCoordinator._deduplicate_cross_node([pump_inst, buf_inst, hc1_inst, hc2_inst])
    oids = {d["oid"] for d in result}
    # HC1 and HC2 both kept (same node, different fct = same canonical node)
    assert "1/15/0/1/7/0" in oids
    assert "1/15/1/1/7/0" in oids
    # Non-HC nodes dropped
    assert "1/16/1/1/7/0" not in oids
    assert "1/16/0/1/7/0" not in oids


# ---------------------------------------------------------------------------
# Enum label integration (coordinator helpers)
# ---------------------------------------------------------------------------


def _make_coord_with_catalog(mock_hass):
    """Return a minimal coordinator with a real LabelCatalog loaded."""
    from custom_components.windhager_unified.labels import LabelCatalog

    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://t",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="advanced",
    )
    coord.label_catalog = LabelCatalog.load()
    return coord


def test_coordinator_has_enum_labels_known(mock_hass):
    """OID 1/65/0/2/1/0 (gn=2, mn=1) has enum labels in the bundled XML."""
    coord = _make_coord_with_catalog(mock_hass)
    assert coord.has_enum_labels("1/65/0/2/1/0") is True


def test_coordinator_has_enum_labels_unknown(mock_hass):
    """OID with unknown (gn, mn) has no enum labels."""
    coord = _make_coord_with_catalog(mock_hass)
    assert coord.has_enum_labels("1/65/0/9999/9999/0") is False


def test_coordinator_get_enum_label_returns_name(mock_hass):
    """gn=2, mn=1, eid=8 → English 'Modulation mode'."""
    coord = _make_coord_with_catalog(mock_hass)
    label = coord.get_enum_label("1/65/0/2/1/0", "8", "en")
    assert label is not None
    assert "modulation" in label.lower()


def test_coordinator_get_enum_label_integer_value(mock_hass):
    """Integer raw value is accepted as well as string."""
    coord = _make_coord_with_catalog(mock_hass)
    assert coord.get_enum_label("1/65/0/2/1/0", 8, "en") is not None


def test_coordinator_get_enum_label_unknown_eid_returns_none(mock_hass):
    """Unknown enum id returns None (sensor shows Unknown in HA)."""
    coord = _make_coord_with_catalog(mock_hass)
    assert coord.get_enum_label("1/65/0/2/1/0", 9999, "en") is None


def test_coordinator_get_enum_label_non_integer_value_returns_none(mock_hass):
    """Non-integer raw value (e.g. temperature string) returns None gracefully."""
    coord = _make_coord_with_catalog(mock_hass)
    assert coord.get_enum_label("1/65/0/2/1/0", "23.5", "en") is None


def test_coordinator_get_enum_options_non_empty(mock_hass):
    """Options list for gn=2, mn=1 is non-empty and contains strings."""
    coord = _make_coord_with_catalog(mock_hass)
    opts = coord.get_enum_options("1/65/0/2/1/0", "en")
    assert len(opts) > 0
    assert all(isinstance(o, str) for o in opts)


def test_coordinator_get_enum_options_no_catalog(mock_hass):
    """Returns empty list when catalog is not loaded."""
    coord = WindhagerCoordinator(
        hass=mock_hass,
        host="http://t",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="advanced",
    )
    # label_catalog is None by default before async_initialize_catalog
    assert coord.get_enum_options("1/65/0/2/1/0", "en") == []
