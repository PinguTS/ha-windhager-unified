"""Tests for the LON scan state-machine (_run_full_lon_scan) and api_client scan methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.windhager_unified.api_client import WindhagerApiClient
from custom_components.windhager_unified.discovery import (
    _is_scan_terminal,
    _run_full_lon_scan,
    discover,
)
from custom_components.windhager_unified.exceptions import WindhagerApiError

# ---------------------------------------------------------------------------
# _is_scan_terminal helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (None, False),
        ({}, False),
        ({"state": "SCANNING"}, False),
        ({"state": "IDLE"}, True),
        ({"state": "Done"}, True),
        ({"state": "READY"}, True),
        ({"status": "SCAN_DONE"}, True),
        ({"msg": "scan done."}, True),
        ({"code": 0, "msg": "running"}, False),
    ],
)
def test_is_scan_terminal(payload, expected):
    assert _is_scan_terminal(payload) == expected


# ---------------------------------------------------------------------------
# _run_full_lon_scan: happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_full_lon_scan_happy_path():
    """Verify the full cmd sequence: initscan → start → scanNodes → postScan → scanDone → quit."""
    client = AsyncMock()
    client.async_put_scan_cmd = AsyncMock(return_value={})
    # Status flips: first two polls return SCANNING, third returns DONE
    client.async_get_scan_status = AsyncMock(
        side_effect=[
            {"state": "SCANNING"},
            {"state": "SCANNING"},
            {"state": "DONE"},
        ]
    )
    warnings: list[str] = []

    with patch(
        "custom_components.windhager_unified.discovery._SCAN_POLL_INTERVAL_S", 0
    ):
        await _run_full_lon_scan(client, warnings)

    assert warnings == []
    cmd_calls = [c.args[0] for c in client.async_put_scan_cmd.call_args_list]
    assert cmd_calls == ["initscan", "start", "scanNodes", "postScan", "scanDone", "quit"]


# ---------------------------------------------------------------------------
# _run_full_lon_scan: timeout — quit still sent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_full_lon_scan_timeout_sends_quit():
    """On timeout the state machine must still receive quit."""
    client = AsyncMock()
    client.async_put_scan_cmd = AsyncMock(return_value={})
    # Status never becomes terminal
    client.async_get_scan_status = AsyncMock(return_value={"state": "SCANNING"})
    warnings: list[str] = []

    with (
        patch("custom_components.windhager_unified.discovery._SCAN_POLL_INTERVAL_S", 0),
        patch("custom_components.windhager_unified.discovery._SCAN_TIMEOUT_S", 0.01),
    ):
        await _run_full_lon_scan(client, warnings)

    assert any("did not complete" in w for w in warnings)
    cmd_calls = [c.args[0] for c in client.async_put_scan_cmd.call_args_list]
    assert "quit" in cmd_calls


# ---------------------------------------------------------------------------
# _run_full_lon_scan: status poll HTTP error — abort, quit still sent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_full_lon_scan_status_error_aborts_gracefully():
    """HTTP error on status poll → warning added, quit still sent."""
    client = AsyncMock()
    client.async_put_scan_cmd = AsyncMock(return_value={})
    client.async_get_scan_status = AsyncMock(
        side_effect=WindhagerApiError("Server error", status=500)
    )
    warnings: list[str] = []

    with patch("custom_components.windhager_unified.discovery._SCAN_POLL_INTERVAL_S", 0):
        await _run_full_lon_scan(client, warnings)

    assert any("scan status poll failed" in w for w in warnings)
    cmd_calls = [c.args[0] for c in client.async_put_scan_cmd.call_args_list]
    assert "quit" in cmd_calls


# ---------------------------------------------------------------------------
# _run_full_lon_scan: initscan fails — abort, quit still sent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_full_lon_scan_initscan_failure_sends_quit():
    """If initscan raises, the scan aborts and quit is sent best-effort."""
    client = AsyncMock()
    client.async_put_scan_cmd = AsyncMock(
        side_effect=WindhagerApiError("Device busy", status=503)
    )
    warnings: list[str] = []

    with patch("custom_components.windhager_unified.discovery._SCAN_POLL_INTERVAL_S", 0):
        await _run_full_lon_scan(client, warnings)

    assert any("scan aborted" in w for w in warnings)
    # quit must have been attempted despite the failure
    cmd_calls = [c.args[0] for c in client.async_put_scan_cmd.call_args_list]
    assert "quit" in cmd_calls


# ---------------------------------------------------------------------------
# discover() with expert tier: scan is triggered before nodes_flat
# ---------------------------------------------------------------------------


@pytest.fixture
def _basic_nodes():
    return [
        {
            "nodeId": 65,
            "subnet": 1,
            "name": "LogWIN",
            "neuronId": "deadbeef",
            "programId": "prog65",
        }
    ]


@pytest.fixture
def _basic_lookup_response():
    return {
        "functions": [
            {"fctId": 0, "fctType": 10, "name": "LogWIN", "lock": False},
        ]
    }


@pytest.mark.asyncio
async def test_discover_expert_triggers_lon_scan(_basic_nodes, _basic_lookup_response):
    """discover() with expert tier must run the scan before fetching nodes."""
    client = AsyncMock()
    client.async_get_kesselwahl_selected.return_value = {"id": 2}
    client.async_put_scan_cmd = AsyncMock(return_value={})
    client.async_get_scan_status = AsyncMock(return_value={"state": "DONE"})
    client.async_get_nodes_flat.return_value = _basic_nodes
    client.async_get_node_details.return_value = _basic_lookup_response
    client.async_get_functions.return_value = []
    client.async_get_datapoints_in_level.return_value = []

    with (
        patch(
            "custom_components.windhager_unified.discovery._load_map_to_instance",
            return_value={},
        ),
        patch("custom_components.windhager_unified.discovery._SCAN_POLL_INTERVAL_S", 0),
    ):
        result = await discover(client, experience_tier="expert")

    client.async_put_scan_cmd.assert_called()
    scan_cmds = [c.args[0] for c in client.async_put_scan_cmd.call_args_list]
    assert "initscan" in scan_cmds
    assert "quit" in scan_cmds
    # Node list must also have been fetched
    client.async_get_nodes_flat.assert_called_once()
    assert len(result.nodes) == 1


@pytest.mark.asyncio
async def test_discover_essential_does_not_trigger_lon_scan(_basic_nodes):
    """Easy tiers must NOT trigger the scan state machine."""
    client = AsyncMock()
    client.async_get_kesselwahl_selected.return_value = {"id": 2}
    client.async_get_nodes.return_value = [
        {**n, "functions": [{"fctId": 0, "fctType": 10, "name": "n", "lock": False}]}
        for n in _basic_nodes
    ]
    client.async_get_functions.return_value = []
    client.async_get_datapoints_in_level.return_value = []

    with patch(
        "custom_components.windhager_unified.discovery._load_map_to_instance",
        return_value={},
    ):
        await discover(client, experience_tier="essential")

    client.async_put_scan_cmd.assert_not_called()


# ---------------------------------------------------------------------------
# api_client: async_put_scan_cmd validates the documented cmd enum
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_client_put_scan_cmd_valid():
    """async_put_scan_cmd must accept any documented cmd without raising ValueError."""
    client = WindhagerApiClient(
        host="http://192.0.2.1",
        username="user",
        password="pass",
    )
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.content_type = "application/json"
    mock_resp.json = AsyncMock(return_value={})

    # aiohttp session.request() is used as `async with`, not awaited directly.
    # Use a MagicMock for request so it returns the CM synchronously.
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.request.return_value = mock_cm
    client._session = mock_session

    # Should not raise
    await client.async_put_scan_cmd("initscan")
    await client.async_put_scan_cmd("quit")


@pytest.mark.asyncio
async def test_api_client_put_scan_cmd_invalid_raises():
    """async_put_scan_cmd must raise ValueError for undocumented cmd strings."""
    client = WindhagerApiClient(
        host="http://192.0.2.1",
        username="user",
        password="pass",
    )
    with pytest.raises(ValueError, match="Invalid scan cmd"):
        await client.async_put_scan_cmd("notAValidCmd")
