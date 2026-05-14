"""Tests for custom_components/windhager_unified/discovery.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.windhager_unified.discovery import (
    DiscoveredDatapoint,
    DiscoveredGroup,
    DiscoveryResult,
    _classify_fct_type,
    _group_label,
    discover,
    serialize_discovered_datapoints_for_config,
)
from custom_components.windhager_unified.exceptions import WindhagerApiError, WindhagerAuthError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    client = AsyncMock()
    # Provide safe defaults for scan methods so expert-tier discover() calls don't block.
    # The scan state machine is exercised separately in test_lon_scan.py.
    client.async_put_scan_cmd = AsyncMock(return_value={})
    client.async_get_scan_status = AsyncMock(return_value={"state": "DONE"})
    return client


@pytest.fixture(autouse=True)
def fast_scan(monkeypatch):
    """Patch scan timing constants so poll loops complete immediately in tests."""
    monkeypatch.setattr("custom_components.windhager_unified.discovery._SCAN_POLL_INTERVAL_S", 0)
    monkeypatch.setattr("custom_components.windhager_unified.discovery._SCAN_TIMEOUT_S", 1.0)


def _nodes_response():
    return [
        {
            "nodeId": 65,
            "subnet": 1,
            "name": "LogWIN",
            "neuronId": "deadbeef",
            "programId": "prog65",
        }
    ]


def _lookup_node_response():
    """Simulate a node detail response with two functions."""
    return {
        "functions": [
            {"fctId": 0, "fctType": 0, "name": "Boiler", "locked": False},
            {"fctId": 1, "fctType": 1, "name": "Heizkreis 1", "locked": False},
        ]
    }


def _lookup_levels_response():
    # Live devices use {"id": N, "count": M} — legacy tests kept with "levelId" fallback too
    return [{"id": 155, "count": 4}, {"id": 156, "count": 10}]


def _lookup_positions_response():
    # Real API returns the full OID field; the 4th segment is groupNr, not levelId.
    return [
        {
            "OID": "/1/65/0/0/15/0",
            "groupNr": 0,
            "memberNr": 15,
            "name": "00-015",
            "stepId": 0,
            "subtypeId": -1,
            "typeId": 13,
            "unitId": 1,
            "writeProt": True,
        },
        {
            "OID": "/1/65/0/0/16/0",
            "groupNr": 0,
            "memberNr": 16,
            "name": "00-016",
            "stepId": 0,
            "subtypeId": -1,
            "typeId": 13,
            "unitId": 1,
            "writeProt": True,
        },
    ]


# ---------------------------------------------------------------------------
# Helper classification
# ---------------------------------------------------------------------------


def test_classify_known_fct_type():
    assert _classify_fct_type(0, {}) == "boiler"
    assert _classify_fct_type(1, {}) == "heating_circuit"
    assert _classify_fct_type(2, {}) == "dhw"
    assert _classify_fct_type(4, {}) == "cascade"
    assert _classify_fct_type(10, {}) == "boiler"
    # fctType 14: UMUMLZ heating-circuit controller (EbenenTexte fcttyp id=14)
    assert _classify_fct_type(14, {}) == "heating_circuit"
    # fctType 15: WVF PUFFER buffer/shift-valve (EbenenTexte fcttyp id=15)
    assert _classify_fct_type(15, {}) == "buffer"
    # fctType 16: B-PLM boiler loading pump (EbenenTexte fcttyp id=16)
    assert _classify_fct_type(16, {}) == "boiler_loading_pump"


def test_classify_unknown_fct_type():
    result = _classify_fct_type(99, {})
    assert result == "unknown_99"


def test_classify_from_map_to_instance():
    result = _classify_fct_type(42, {42: "CustomModule"})
    assert result == "custommodule"


def test_group_label_friendly():
    assert "Boiler" in _group_label(0, "boiler", {})
    assert "circuit" in _group_label(1, "heating_circuit", {}).lower()


def test_group_label_unknown():
    label = _group_label(99, "unknown_99", {})
    assert "99" in label


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_happy_path(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 2, "name": "Holz"}
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = _lookup_node_response()
    mock_client.async_get_functions.return_value = _lookup_levels_response()
    mock_client.async_get_datapoints_in_level.return_value = _lookup_positions_response()

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client)

    assert result.boiler_id == 2
    assert "LogWIN" in result.boiler_name or "Holz" in result.boiler_name
    assert len(result.nodes) == 1
    assert result.nodes[0].node_id == 65
    assert len(result.groups) >= 1


# ---------------------------------------------------------------------------
# Corner: kesselwahl 404 → boiler_family = None, discovery continues
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_kesselwahl_404(mock_client):
    mock_client.async_get_kesselwahl_selected.side_effect = WindhagerApiError(
        "Not found", status=404
    )
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = _lookup_node_response()
    mock_client.async_get_functions.return_value = _lookup_levels_response()
    mock_client.async_get_datapoints_in_level.return_value = _lookup_positions_response()

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client)

    assert result.boiler_id is None
    assert result.boiler_name is None
    assert len(result.nodes) == 1


# ---------------------------------------------------------------------------
# Corner: empty subnets → no groups
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_empty_nodes(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 1, "name": "Pellets"}
    mock_client.async_get_nodes_flat.return_value = []

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client)

    assert result.groups == []
    assert result.nodes == []


# ---------------------------------------------------------------------------
# Corner: unknown fctType=99 → emitted as unknown_99
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_unknown_fct_type(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 1}
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = {
        "functions": [{"fctId": 0, "fctType": 99, "name": "Mystery", "locked": False}]
    }
    mock_client.async_get_functions.return_value = {"levels": []}
    mock_client.async_get_datapoints_in_level.return_value = {"positions": []}

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client)

    group_ids = [g.id for g in result.groups]
    assert "unknown_99" in group_ids


# ---------------------------------------------------------------------------
# Corner: HTTP 401 mid-walk → WindhagerAuthError propagates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_auth_error_propagates(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 1}
    mock_client.async_get_nodes_flat.side_effect = WindhagerAuthError("Unauthorized")

    with (
        patch(
            "custom_components.windhager_unified.discovery._load_map_to_instance",
            return_value={},
        ),
        pytest.raises(WindhagerAuthError),
    ):
        await discover(mock_client)


# ---------------------------------------------------------------------------
# Corner: malformed JSON (non-dict) in one level response → skip, others ok
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_malformed_lookup_level(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 1}
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = _lookup_node_response()

    call_count = 0

    async def levels_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return "not-a-dict"  # malformed
        return _lookup_levels_response()

    mock_client.async_get_functions.side_effect = levels_side_effect
    mock_client.async_get_datapoints_in_level.return_value = _lookup_positions_response()

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client)

    # Discovery should complete without raising
    assert len(result.nodes) == 1


# ---------------------------------------------------------------------------
# Tier-scoped discovery (lookup subnet + level filter)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_expert_uses_nodes_flat(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 1}
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = _lookup_node_response()
    mock_client.async_get_functions.return_value = _lookup_levels_response()
    mock_client.async_get_datapoints_in_level.return_value = _lookup_positions_response()

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        await discover(mock_client, experience_tier="expert")

    mock_client.async_get_nodes_flat.assert_called_once()
    mock_client.async_get_nodes.assert_not_called()


@pytest.mark.asyncio
async def test_discover_essential_uses_lookup_subnet_filters_levels(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 1}
    mock_client.async_get_nodes.return_value = [
        {
            "nodeId": 65,
            "subnet": 1,
            "name": "LogWIN",
            "neuronId": "n",
            "programId": "p",
            "functions": [
                {"fctId": 0, "fctType": 10, "name": "LogWIN", "lock": False},
            ],
        }
    ]
    # Live format: {id, count} — both 100 and 157 should be filtered for essential/fctType 10
    mock_client.async_get_functions.return_value = [
        {"id": 100, "count": 2},
        {"id": 156, "count": 10},
        {"id": 157, "count": 5},
    ]
    mock_client.async_get_datapoints_in_level.return_value = [
        {
            "OID": "/1/65/0/0/15/0",
            "groupNr": 0,
            "memberNr": 15,
            "name": "00-015",
            "typeId": 13,
            "unitId": 1,
            "writeProt": True,
        }
    ]

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        await discover(mock_client, experience_tier="essential")

    mock_client.async_get_nodes.assert_called_once_with("1")
    mock_client.async_get_nodes_flat.assert_not_called()
    level_ids = [c.args[3] for c in mock_client.async_get_datapoints_in_level.call_args_list]
    assert "100" not in level_ids
    assert "156" in level_ids
    assert "157" not in level_ids


@pytest.mark.asyncio
async def test_discover_lookup_subnet_empty_falls_back_to_nodes_flat(mock_client):
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 1}
    mock_client.async_get_nodes.return_value = []
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = _lookup_node_response()
    mock_client.async_get_functions.return_value = _lookup_levels_response()
    mock_client.async_get_datapoints_in_level.return_value = _lookup_positions_response()

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        await discover(mock_client, experience_tier="comfort")

    mock_client.async_get_nodes_flat.assert_called_once()


def test_serialize_discovered_datapoints_for_config():
    dp = DiscoveredDatapoint(
        oid="1/65/0/0/15/0",
        level_id=156,
        write_prot=True,
        type_id=13,
        unit_id=1,
        experience_minimum="essential",
        api_name="00-015",
        function_name="LogWIN",
    )
    grp = DiscoveredGroup(id="boiler", label="Boiler", fct_type=10, datapoints=[dp])
    result = DiscoveryResult(boiler_id=None, boiler_name=None, groups=[grp])
    rows = serialize_discovered_datapoints_for_config(result)
    assert len(rows) == 1
    assert rows[0]["oid"] == dp.oid
    assert rows[0]["group"] == "boiler"
    assert rows[0]["function_name"] == "LogWIN"


# ---------------------------------------------------------------------------
# Phase 1: OID field parsing from real API responses
# ---------------------------------------------------------------------------

# Exact lookup/1/65/0/156 payload from a live LogWIN system
_LIVE_LEVEL_156_RESPONSE = [
    {
        "OID": "/1/65/0/12/38/0",
        "groupNr": 12,
        "memberNr": 38,
        "name": "12-038",
        "stepId": 0,
        "subtypeId": 9,
        "timestamp": "2026-05-13 23:40:19",
        "typeId": 30,
        "unitId": 0,
        "writeProt": True,
    },
    {
        "OID": "/1/65/0/2/81/0",
        "groupNr": 2,
        "maxValue": "65535",
        "memberNr": 81,
        "minValue": "0",
        "name": "02-081",
        "step": "1",
        "stepId": 0,
        "subtypeId": -1,
        "timestamp": "2026-05-13 23:40:19",
        "typeId": 4,
        "unit": "h",
        "unitId": 5,
        "value": "11481",
        "writeProt": True,
    },
    {
        "OID": "/1/65/0/0/15/0",
        "groupNr": 0,
        "maxValue": "327.6",
        "memberNr": 15,
        "minValue": "-273.1",
        "name": "00-015",
        "step": "0.1",
        "stepId": 0,
        "subtypeId": -1,
        "timestamp": "2026-05-13 23:40:20",
        "typeId": 13,
        "unit": "°C",
        "unitId": 1,
        "value": "62.3",
        "writeProt": True,
    },
    {
        "OID": "/1/65/0/20/112/0",
        "groupNr": 20,
        "maxValue": "65535",
        "memberNr": 112,
        "minValue": "0",
        "name": "20-112",
        "step": "1",
        "stepId": 0,
        "subtypeId": -1,
        "timestamp": "2026-05-13 23:40:20",
        "typeId": 4,
        "unitId": 0,
        "value": "1672",
        "writeProt": True,
    },
]


@pytest.mark.asyncio
async def test_discover_uses_api_oid_field(mock_client):
    """OIDs collected during discovery must come from the API OID field, not synthesised."""
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 2, "name": "Holz"}
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = {
        "functions": [
            {"fctId": 0, "fctType": 10, "name": "LogWIN", "lock": False},
        ]
    }
    mock_client.async_get_functions.return_value = [{"id": 156, "count": 10}]
    mock_client.async_get_datapoints_in_level.return_value = _LIVE_LEVEL_156_RESPONSE

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client, experience_tier="expert")

    all_oids = {dp.oid for grp in result.groups for dp in grp.datapoints}
    assert "1/65/0/12/38/0" in all_oids, "groupNr=12 OID must be used, not levelId"
    assert "1/65/0/2/81/0" in all_oids
    assert "1/65/0/0/15/0" in all_oids
    assert "1/65/0/20/112/0" in all_oids
    # Synthesised OID (wrong) must not appear
    assert "1/65/0/156/0/0" not in all_oids


@pytest.mark.asyncio
async def test_discover_skips_malformed_oid(mock_client):
    """Datapoints with malformed or absent OID field are skipped, walk continues."""
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 2}
    mock_client.async_get_nodes_flat.return_value = _nodes_response()
    mock_client.async_get_node_details.return_value = {
        "functions": [{"fctId": 0, "fctType": 10, "name": "LogWIN", "lock": False}]
    }
    mock_client.async_get_functions.return_value = [{"id": 156, "count": 3}]
    mock_client.async_get_datapoints_in_level.return_value = [
        # Missing OID entirely
        {"groupNr": 0, "memberNr": 1, "name": "00-001", "typeId": 13, "unitId": 1},
        # OID with wrong segment count
        {"OID": "/1/65/0/0", "groupNr": 0, "memberNr": 2, "name": "00-002"},
        # Valid OID — should be collected
        {
            "OID": "/1/65/0/0/15/0",
            "groupNr": 0,
            "memberNr": 15,
            "name": "00-015",
            "typeId": 13,
            "unitId": 1,
            "writeProt": True,
        },
    ]

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client, experience_tier="expert")

    all_oids = {dp.oid for grp in result.groups for dp in grp.datapoints}
    assert "1/65/0/0/15/0" in all_oids
    assert len(all_oids) == 1, "Only the valid OID must be collected"


@pytest.mark.asyncio
async def test_discover_gn_mn_override_applied(mock_client):
    """GN_MN_OVERRIDES from groups_config.yaml must override experience_minimum.

    Datapoint gn=4, mn=92 (Software-Version) is on level 156 (experience_minimum
    would normally be "essential").  The bundled groups_config.yaml overrides it
    to "service".
    """
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 2, "name": "Holz"}
    mock_client.async_get_nodes_flat.return_value = [{"subnet": 1, "nodeId": 65, "name": "LogWIN"}]
    mock_client.async_get_node_details.return_value = {
        "functions": [{"fctId": 0, "fctType": 10, "name": "LogWIN", "lock": False}]
    }
    mock_client.async_get_functions.return_value = [{"id": 156, "count": 2}]
    mock_client.async_get_datapoints_in_level.return_value = [
        # Normal temperature reading: gn=0, mn=15 → essential (no override)
        {
            "OID": "/1/65/0/0/15/0",
            "groupNr": 0,
            "memberNr": 15,
            "name": "00-015",
            "typeId": 13,
            "unitId": 1,
            "writeProt": True,
        },
        # Software-Version: gn=4, mn=92 → overridden to "service"
        {
            "OID": "/1/65/0/4/92/0",
            "groupNr": 4,
            "memberNr": 92,
            "name": "04-092",
            "typeId": 30,
            "unitId": 0,
            "writeProt": True,
        },
    ]

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client, experience_tier="expert")

    dp_by_oid = {dp.oid: dp for grp in result.groups for dp in grp.datapoints}
    assert "1/65/0/0/15/0" in dp_by_oid
    assert dp_by_oid["1/65/0/0/15/0"].experience_minimum == "essential"

    assert "1/65/0/4/92/0" in dp_by_oid
    assert (
        dp_by_oid["1/65/0/4/92/0"].experience_minimum == "service"
    ), "gn=4 mn=92 (Software-Version) must be promoted to 'service' by gn_mn_overrides"


@pytest.mark.asyncio
async def test_discover_gn_mn_override_inactive_when_no_match(mock_client):
    """Datapoints not in GN_MN_OVERRIDES keep their level-derived experience_minimum."""
    mock_client.async_get_kesselwahl_selected.return_value = {"id": 2}
    mock_client.async_get_nodes_flat.return_value = [{"subnet": 1, "nodeId": 65, "name": "LogWIN"}]
    mock_client.async_get_node_details.return_value = {
        "functions": [{"fctId": 0, "fctType": 10, "name": "LogWIN", "lock": False}]
    }
    mock_client.async_get_functions.return_value = [{"id": 156, "count": 1}]
    mock_client.async_get_datapoints_in_level.return_value = [
        # gn=0 mn=7 — not in GN_MN_OVERRIDES; level 156 → essential
        {
            "OID": "/1/65/0/0/7/0",
            "groupNr": 0,
            "memberNr": 7,
            "name": "00-007",
            "typeId": 13,
            "unitId": 1,
            "writeProt": True,
        },
    ]

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        result = await discover(mock_client, experience_tier="expert")

    dp_by_oid = {dp.oid: dp for grp in result.groups for dp in grp.datapoints}
    assert "1/65/0/0/7/0" in dp_by_oid
    assert dp_by_oid["1/65/0/0/7/0"].experience_minimum == "essential"
