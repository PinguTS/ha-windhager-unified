"""Tests for WindhagerApiClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.windhager_unified.api_client import WindhagerApiClient
from custom_components.windhager_unified.exceptions import (
    WindhagerAuthError,
    WindhagerConnectionError,
    WindhagerTimeoutError,
)


@pytest.fixture
def client() -> WindhagerApiClient:
    return WindhagerApiClient(
        host="http://test-host",
        username="test_user",
        password="test_pass",
        verify_ssl=False,
        timeout=10,
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_normalize_host_preserves_explicit_scheme():
    c = WindhagerApiClient("http://192.0.2.1", "u", "p")
    assert c.host == "http://192.0.2.1"


def test_normalize_host_adds_https_when_no_scheme():
    c = WindhagerApiClient("192.0.2.1", "u", "p")
    assert c.host == "https://192.0.2.1"


def test_normalize_host_strips_trailing_slash():
    c = WindhagerApiClient("http://192.0.2.1/", "u", "p")
    assert c.host == "http://192.0.2.1"


def test_client_init(client: WindhagerApiClient):
    assert client.host == "http://test-host"
    assert client.username == "test_user"
    assert client.password == "test_pass"
    assert client.verify_ssl is False


# ---------------------------------------------------------------------------
# LON / Datapoint endpoints — correct paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_datapoint_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {"value": 75.5}
        result = await client.async_get_datapoint(["1", "65", "0", "0", "0", "0"])
        assert result == {"value": 75.5}
        mock.assert_called_once_with("GET", "/api/1.0/datapoint/1/65/0/0/0/0")


@pytest.mark.asyncio
async def test_get_datapoint_invalid_oid(client):
    with pytest.raises(ValueError, match="6 parts"):
        await client.async_get_datapoint(["1", "65", "0", "0", "0"])


@pytest.mark.asyncio
async def test_put_datapoint_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "ok"}
        await client.async_put_datapoint(["1", "65", "0", "0", "0", "0"], "80.0")
        mock.assert_called_once_with(
            "PUT",
            "/api/1.0/datapoint",
            json={"OID": "/1/65/0/0/0/0", "value": "80.0"},
        )


@pytest.mark.asyncio
async def test_put_datapoint_coerces_value_to_string(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {"status": "ok"}
        await client.async_put_datapoint(["1", "65", "0", "0", "0", "0"], 4)
        mock.assert_called_once_with(
            "PUT",
            "/api/1.0/datapoint",
            json={"OID": "/1/65/0/0/0/0", "value": "4"},
        )


@pytest.mark.asyncio
async def test_get_nv_datapoint_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {"value": 1}
        await client.async_get_nv_datapoint("1", "65", "5")
        mock.assert_called_once_with("GET", "/api/1.0/datapoint/1/65/fctNV/0/5/0")


# ---------------------------------------------------------------------------
# Lookup endpoints — no doubling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_subnets_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_subnets()
        mock.assert_called_once_with("GET", "/api/1.0/lookup")


@pytest.mark.asyncio
async def test_get_nodes_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_nodes("1")
        mock.assert_called_once_with("GET", "/api/1.0/lookup/1")


@pytest.mark.asyncio
async def test_get_node_details_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_node_details("1", "65")
        mock.assert_called_once_with("GET", "/api/1.0/lookup/1/65")


# ---------------------------------------------------------------------------
# RestAPI endpoints — correct paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_settings_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_settings()
        mock.assert_called_once_with("GET", "/api/1.0/settings")


@pytest.mark.asyncio
async def test_set_logging_level_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_set_logging_level("DEBUG")
        mock.assert_called_once_with(
            "PUT", "/api/1.0/settings/logging/level", params={"value": "DEBUG"}
        )


@pytest.mark.asyncio
async def test_get_system_time_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {"time": "2024-01-01T12:00:00Z"}
        result = await client.async_get_system_time()
        assert result == {"time": "2024-01-01T12:00:00Z"}
        mock.assert_called_once_with("GET", "/WsAdmin/api/1.0/systemtime")


@pytest.mark.asyncio
async def test_get_timezone_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_timezone()
        mock.assert_called_once_with("GET", "/WsAdmin/api/1.0/systemtime/timezone")


@pytest.mark.asyncio
async def test_set_timezone_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_set_timezone("Europe/Berlin")
        mock.assert_called_once_with(
            "PUT", "/WsAdmin/api/1.0/systemtime/timezone", params={"value": "Europe/Berlin"}
        )


@pytest.mark.asyncio
async def test_get_led_status_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = []
        await client.async_get_led_status()
        mock.assert_called_once_with("GET", "/WsAdmin/api/1.0/led")


@pytest.mark.asyncio
async def test_get_fehlerlog_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = []
        await client.async_get_fehlerlog()
        mock.assert_called_once_with("GET", "/InfoWinFehlerlog/api/1.0/fehlerlog")


@pytest.mark.asyncio
async def test_reset_fehlerlog_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_reset_fehlerlog("0")
        mock.assert_called_once_with("PUT", "/InfoWinFehlerlog/api/1.0/fehlerlog/reset/0")


@pytest.mark.asyncio
async def test_get_heartbeat_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_heartbeat()
        mock.assert_called_once_with("GET", "/InfoWinHeartbeat/api/1.0/heartbeat")


@pytest.mark.asyncio
async def test_start_heartbeat_uses_post(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_start_heartbeat()
        mock.assert_called_once_with("POST", "/InfoWinHeartbeat/api/1.0/heartbeat")


@pytest.mark.asyncio
async def test_stop_heartbeat_uses_delete(client):
    """Heartbeat stop must use DELETE, not POST."""
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_stop_heartbeat()
        mock.assert_called_once_with("DELETE", "/InfoWinHeartbeat/api/1.0/heartbeat")


@pytest.mark.asyncio
async def test_get_vpn_status_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_vpn_status()
        mock.assert_called_once_with("GET", "/api/1.0/vpn/status")


@pytest.mark.asyncio
async def test_factory_reset_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_factory_reset("reset")
        mock.assert_called_once_with("PUT", "/WsAdmin/api/1.0/update/factoryReset/reset")


# ---------------------------------------------------------------------------
# LON service endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_srv0620_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_get_srv0620("1", "65", "0", "0")
        mock.assert_called_once_with("GET", "/WsFUP7030/api/1.0/srv0620/1/65/0/0")


@pytest.mark.asyncio
async def test_post_srv0620_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        data = {"subnet": 1}
        await client.async_post_srv0620(data)
        mock.assert_called_once_with("POST", "/WsFUP7030/api/1.0/srv0620", json=data)


@pytest.mark.asyncio
async def test_put_srv0623_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_put_srv0623("1/65/0/0/0/0", "75.5")
        mock.assert_called_once_with(
            "PUT", "/WsFUP7030/api/1.0/srv0623", params={"oid": "1/65/0/0/0/0", "value": "75.5"}
        )


@pytest.mark.asyncio
async def test_put_srv1025_correct_path(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = {}
        await client.async_put_srv1025("1/65/0/0/0/0", "42")
        mock.assert_called_once_with(
            "PUT", "/WsFUP7030/api/1.0/srv1025", params={"oid": "1/65/0/0/0/0", "value": "42"}
        )


# ---------------------------------------------------------------------------
# async_test_connection — uses async_request, not async_get_lookup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_test_connection_success(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.return_value = [{"subnet": 1}]
        result = await client.async_test_connection()
        assert result is True
        mock.assert_called_once_with("GET", "/api/1.0/lookup")


@pytest.mark.asyncio
async def test_test_connection_auth_failure(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.side_effect = WindhagerAuthError("bad creds")
        with pytest.raises(WindhagerAuthError):
            await client.async_test_connection()


@pytest.mark.asyncio
async def test_test_connection_network_failure(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.side_effect = WindhagerConnectionError("no route")
        result = await client.async_test_connection()
        assert result is False


@pytest.mark.asyncio
async def test_test_connection_timeout(client):
    with patch.object(client, "async_request", new_callable=AsyncMock) as mock:
        mock.side_effect = WindhagerTimeoutError("timeout")
        result = await client.async_test_connection()
        assert result is False


# ---------------------------------------------------------------------------
# Kesselwahl helpers  (InfoWinHeartbeat_1.0_kesselwahl.json)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_kesselwahl_selected(client):
    mock = AsyncMock(return_value={"id": 2, "name": "Holz"})
    client.async_request = mock
    result = await client.async_get_kesselwahl_selected()
    mock.assert_called_once_with("GET", "/InfoWinHeartbeat/api/1.0/kesselwahl/selected")
    assert result["id"] == 2


@pytest.mark.asyncio
async def test_get_kesselwahl_list(client):
    mock = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
    client.async_request = mock
    result = await client.async_get_kesselwahl_list()
    mock.assert_called_once_with("GET", "/InfoWinHeartbeat/api/1.0/kesselwahl/list")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_put_kesselwahl_no_option(client):
    mock = AsyncMock(return_value=None)
    client.async_request = mock
    await client.async_put_kesselwahl("2")
    mock.assert_called_once_with("PUT", "/InfoWinHeartbeat/api/1.0/kesselwahl/2", params=None)


@pytest.mark.asyncio
async def test_put_kesselwahl_with_option(client):
    mock = AsyncMock(return_value=None)
    client.async_request = mock
    await client.async_put_kesselwahl("1", option="1 withServicePin")
    mock.assert_called_once_with(
        "PUT",
        "/InfoWinHeartbeat/api/1.0/kesselwahl/1",
        params={"option": "1 withServicePin"},
    )


# ---------------------------------------------------------------------------
# Flat nodes list  (RestApiRC7030_1.0_nodes.json)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_nodes_flat(client):
    expected = [{"nodeId": 65, "subnet": 1, "name": "LogWIN", "neuronId": "", "programId": ""}]
    mock = AsyncMock(return_value=expected)
    client.async_request = mock
    result = await client.async_get_nodes_flat()
    mock.assert_called_once_with("GET", "/api/1.0/nodes")
    assert result == expected
