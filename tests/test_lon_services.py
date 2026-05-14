"""Tests for LON service endpoints (srv0620-0623, srv1024/1025, etc.).

All paths verified against docs/swagger/ (Swagger 1.2 source files).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.windhager_unified.api_client import WindhagerApiClient


@pytest.fixture
def client() -> WindhagerApiClient:
    return WindhagerApiClient(
        host="http://test-host",
        username="test_user",
        password="test_pass",
        verify_ssl=False,
    )


# ---------------------------------------------------------------------------
# srv0620
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_srv0620(client):
    mock = AsyncMock(return_value={"data": "ok"})
    client.async_request = mock
    await client.async_get_srv0620("1", "65", "0", "0")
    mock.assert_called_once_with("GET", "/WsFUP7030/api/1.0/srv0620/1/65/0/0")


@pytest.mark.asyncio
async def test_post_srv0620(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    data = {"subnet": 1, "nodeId": 65, "fnctNbr": 0, "levelIdx": 0}
    await client.async_post_srv0620(data)
    mock.assert_called_once_with("POST", "/WsFUP7030/api/1.0/srv0620", json=data)


# ---------------------------------------------------------------------------
# srv0621
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_srv0621(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    await client.async_get_srv0621("1", "65", "0x01", "0x02")
    mock.assert_called_once_with("GET", "/WsFUP7030/api/1.0/srv0621/1/65/0x01/0x02")


@pytest.mark.asyncio
async def test_post_srv0621(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    data = {"subnet": 1}
    await client.async_post_srv0621(data)
    mock.assert_called_once_with("POST", "/WsFUP7030/api/1.0/srv0621", json=data)


# ---------------------------------------------------------------------------
# srv0622
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_srv0622(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    await client.async_get_srv0622("1", "65", "0x01", "0x02")
    mock.assert_called_once_with("GET", "/WsFUP7030/api/1.0/srv0622/1/65/0x01/0x02")


@pytest.mark.asyncio
async def test_post_srv0622(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    data = {"subnet": 1}
    await client.async_post_srv0622(data)
    mock.assert_called_once_with("POST", "/WsFUP7030/api/1.0/srv0622", json=data)


# ---------------------------------------------------------------------------
# srv0623
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_srv0623(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    data = {"oid": "1/65/0/0/0/0", "value": "42"}
    await client.async_post_srv0623(data)
    mock.assert_called_once_with("POST", "/WsFUP7030/api/1.0/srv0623", json=data)


@pytest.mark.asyncio
async def test_put_srv0623(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    await client.async_put_srv0623("1/65/0/0/0/0", "75.5")
    mock.assert_called_once_with(
        "PUT",
        "/WsFUP7030/api/1.0/srv0623",
        params={"oid": "1/65/0/0/0/0", "value": "75.5"},
    )


# ---------------------------------------------------------------------------
# srv1024 / srv1025
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_srv1024(client):
    mock = AsyncMock(return_value={"value": "75.5"})
    client.async_request = mock
    await client.async_get_srv1024("1", "65", "0", "0", "0", "0")
    mock.assert_called_once_with("GET", "/WsFUP7030/api/1.0/srv1024/1/65/0/0/0/0")


@pytest.mark.asyncio
async def test_put_srv1025(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    await client.async_put_srv1025("1/65/0/0/0/0", "75.5")
    mock.assert_called_once_with(
        "PUT",
        "/WsFUP7030/api/1.0/srv1025",
        params={"oid": "1/65/0/0/0/0", "value": "75.5"},
    )


# ---------------------------------------------------------------------------
# RestAPI admin endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ntp_servers(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    await client.async_get_ntp_servers()
    mock.assert_called_once_with("GET", "/WsAdmin/api/1.0/systemtime/ntpserver")


@pytest.mark.asyncio
async def test_get_selected_ntp_server(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    await client.async_get_selected_ntp_server()
    mock.assert_called_once_with("GET", "/WsAdmin/api/1.0/systemtime/ntpserver/selected")


@pytest.mark.asyncio
async def test_get_factory_reset_status(client):
    mock = AsyncMock(return_value={"status": "ready"})
    client.async_request = mock
    await client.async_get_factory_reset_status()
    mock.assert_called_once_with("GET", "/WsAdmin/api/1.0/update/factoryReset")


@pytest.mark.asyncio
async def test_get_firmware_info(client):
    mock = AsyncMock(return_value={"version": "1.0"})
    client.async_request = mock
    await client.async_get_firmware_info("info")
    mock.assert_called_once_with("GET", "/WsAdmin/api/1.0/update/firmware/info")


@pytest.mark.asyncio
async def test_post_firmware_update(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    data = {"cmd": "start"}
    await client.async_post_firmware_update("update", data)
    mock.assert_called_once_with("POST", "/WsAdmin/api/1.0/update/firmware/update", json=data)


@pytest.mark.asyncio
async def test_check_dynip(client):
    mock = AsyncMock(return_value={})
    client.async_request = mock
    await client.async_check_dynip()
    mock.assert_called_once_with("GET", "/api/1.0/DynIP/CheckIP")
