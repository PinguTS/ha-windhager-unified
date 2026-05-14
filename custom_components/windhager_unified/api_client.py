"""API client for Windhager LON and REST API communication.

All endpoint paths are derived from docs/swagger/ (Swagger 1.2 source files).
Full URL = basePath + apis[].path — no doubled resource segments.
"""

from __future__ import annotations

import hashlib
import logging
import re
import secrets
from typing import Any
from urllib.parse import urlparse

import aiohttp
from aiohttp import ClientTimeout

from .exceptions import (
    WindhagerApiError,
    WindhagerAuthError,
    WindhagerConnectionError,
    WindhagerTimeoutError,
)

_LOGGER = logging.getLogger(__name__)


class WindhagerApiClient:
    """Client for Windhager LON and REST API communication."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 10,
    ) -> None:
        self.host = self._normalize_host(host)
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = ClientTimeout(total=timeout)
        self._session: aiohttp.ClientSession | None = None

    @staticmethod
    def _normalize_host(host: str) -> str:
        """Return a base URL with scheme; strip trailing slash."""
        host = host.strip().rstrip("/")
        if host.startswith(("http://", "https://")):
            return host
        # Default to https:// — Windhager devices commonly use self-signed TLS
        return f"https://{host}"

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def __aenter__(self) -> WindhagerApiClient:
        await self.async_init()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.async_close()

    async def async_init(self) -> None:
        """Open the aiohttp session (idempotent)."""
        if self._session is None:
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl if self.verify_ssl else False)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
            )
            _LOGGER.debug("HTTP session opened for %s (verify_ssl=%s)", self.host, self.verify_ssl)

    async def async_close(self) -> None:
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            _LOGGER.debug("HTTP session closed for %s", self.host)

    # ------------------------------------------------------------------
    # Digest authentication
    # ------------------------------------------------------------------

    def _build_digest_header(
        self,
        method: str,
        url: str,
        realm: str,
        nonce: str,
        qop: str,
    ) -> str:
        parsed = urlparse(url)
        uri = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        cnonce = secrets.token_hex(16)
        nc = "00000001"

        ha1 = hashlib.md5(f"{self.username}:{realm}:{self.password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        response = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()).hexdigest()

        return (
            f'Digest username="{self.username}", realm="{realm}", nonce="{nonce}", '
            f'uri="{uri}", algorithm=MD5, response="{response}", '
            f'qop={qop}, nc={nc}, cnonce="{cnonce}"'
        )

    # ------------------------------------------------------------------
    # Core request
    # ------------------------------------------------------------------

    async def async_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Make an authenticated HTTP request.

        Handles Digest 401 challenge automatically.
        Raises WindhagerAuthError, WindhagerApiError,
        WindhagerTimeoutError, or WindhagerConnectionError.
        """
        if not self._session:
            await self.async_init()

        url = f"{self.host}/{endpoint.lstrip('/')}"
        _LOGGER.debug("→ %s %s", method, url)

        try:
            async with self._session.request(method, url, **kwargs) as resp:
                if resp.status == 401:
                    www_auth = resp.headers.get("WWW-Authenticate", "")
                    if "Digest" not in www_auth:
                        raise WindhagerAuthError("Server requires non-Digest auth (unsupported)")

                    realm_m = re.search(r'realm="([^"]*)"', www_auth)
                    nonce_m = re.search(r'nonce="([^"]*)"', www_auth)
                    qop_m = re.search(r'qop="([^"]*)"', www_auth)

                    if not realm_m or not nonce_m:
                        raise WindhagerAuthError("Malformed Digest challenge from server")

                    realm = realm_m.group(1)
                    nonce = nonce_m.group(1)
                    # qop may be comma-separated; pick first supported value
                    qop_raw = qop_m.group(1) if qop_m else "auth"
                    qop = next(
                        (q.strip() for q in qop_raw.split(",") if q.strip() == "auth"),
                        "auth",
                    )

                    auth_header = self._build_digest_header(method, url, realm, nonce, qop)
                    headers = dict(kwargs.pop("headers", {}))
                    headers["Authorization"] = auth_header
                    kwargs["headers"] = headers

                    async with self._session.request(method, url, **kwargs) as auth_resp:
                        if auth_resp.status == 401:
                            raise WindhagerAuthError("Invalid username or password")
                        if auth_resp.status >= 400:
                            raise WindhagerApiError(
                                f"API {auth_resp.status} on {endpoint}",
                                status=auth_resp.status,
                            )
                        return await self._parse_response(auth_resp)

                if resp.status >= 400:
                    raise WindhagerApiError(f"API {resp.status} on {endpoint}", status=resp.status)
                return await self._parse_response(resp)

        except TimeoutError as err:
            raise WindhagerTimeoutError(f"Timeout calling {endpoint}") from err
        except aiohttp.ClientConnectionError as err:
            raise WindhagerConnectionError(f"Cannot connect to {self.host}: {err}") from err
        except (
            WindhagerAuthError,
            WindhagerApiError,
            WindhagerTimeoutError,
            WindhagerConnectionError,
        ):
            raise
        except aiohttp.ClientError as err:
            raise WindhagerApiError(str(err)) from err

    @staticmethod
    async def _parse_response(resp: aiohttp.ClientResponse) -> dict[str, Any] | None:
        if resp.content_type == "application/json":
            return await resp.json()
        text = await resp.text()
        return {"status": resp.status, "text": text} if text else None

    # ------------------------------------------------------------------
    # LON / Datapoint endpoints  (RestApiRC7030_1.0_datapoint)
    # basePath: /api/1.0
    # ------------------------------------------------------------------

    async def async_get_datapoint(self, oid_parts: list[str]) -> dict[str, Any] | None:
        """GET /api/1.0/datapoint/{subnetId}/{nodeId}/{fctId}/{groupId}/{memberId}/{varInst}"""
        if len(oid_parts) != 6:
            raise ValueError("OID must have exactly 6 parts")
        return await self.async_request("GET", f"/api/1.0/datapoint/{'/'.join(oid_parts)}")

    async def async_put_datapoint(self, oid_parts: list[str], value: str) -> dict[str, Any] | None:
        """PUT /api/1.0/datapoint/.../{varInst} with query param value (RestApiRC7030)."""
        if len(oid_parts) != 6:
            raise ValueError("OID must have exactly 6 parts")
        return await self.async_request(
            "PUT",
            f"/api/1.0/datapoint/{'/'.join(oid_parts)}",
            params={"value": value},
        )

    async def async_get_nv_datapoint(
        self, subnet_id: str, node_id: str, nv_index: str
    ) -> dict[str, Any] | None:
        """GET /api/1.0/datapoint/{subnetId}/{nodeId}/{fctNV}/0/{nvIndex}/0"""
        return await self.async_request(
            "GET", f"/api/1.0/datapoint/{subnet_id}/{node_id}/fctNV/0/{nv_index}/0"
        )

    # ------------------------------------------------------------------
    # Lookup / Topology endpoints  (RestApiRC7030_1.0_lookup)
    # basePath: /api/1.0
    # ------------------------------------------------------------------

    async def async_get_lookup(self, *path_parts: str) -> dict[str, Any] | None:
        """GET /api/1.0/lookup[/{path_parts...}]"""
        endpoint = "/api/1.0/lookup"
        if path_parts:
            endpoint += "/" + "/".join(str(p) for p in path_parts)
        return await self.async_request("GET", endpoint)

    async def async_get_subnets(self) -> dict[str, Any] | None:
        return await self.async_get_lookup()

    async def async_get_nodes(self, subnet_id: str) -> dict[str, Any] | None:
        return await self.async_get_lookup(subnet_id)

    async def async_get_nodes_flat(self) -> list[dict[str, Any]] | None:
        """GET /api/1.0/nodes — flat list of all LON nodes.

        Returns a JSON array of Node objects {nodeId, subnet, name, neuronId,
        programId, devices[]}.  Documented in RestApiRC7030_1.0_nodes.json.
        """
        return await self.async_request("GET", "/api/1.0/nodes")

    async def async_get_node_details(self, subnet_id: str, node_id: str) -> dict[str, Any] | None:
        return await self.async_get_lookup(subnet_id, node_id)

    async def async_get_functions(
        self, subnet_id: str, node_id: str, fct_id: str
    ) -> dict[str, Any] | None:
        return await self.async_get_lookup(subnet_id, node_id, fct_id)

    async def async_get_datapoints_in_level(
        self, subnet_id: str, node_id: str, fct_id: str, level_id: str
    ) -> dict[str, Any] | None:
        return await self.async_get_lookup(subnet_id, node_id, fct_id, level_id)

    async def async_get_nv_list(self, subnet_id: str, node_id: str) -> dict[str, Any] | None:
        """GET /api/1.0/lookup/{subnetId}/{nodeId}/{fctNV}/0"""
        return await self.async_get_lookup(subnet_id, node_id, "fctNV", "0")

    # ------------------------------------------------------------------
    # Settings  (RestApiRC7030_1.0_settings)
    # basePath: /api/1.0
    # ------------------------------------------------------------------

    async def async_get_settings(self, key: str | None = None) -> dict[str, Any] | None:
        """GET /api/1.0/settings  or  /api/1.0/settings/{key}"""
        endpoint = "/api/1.0/settings"
        if key:
            endpoint += f"/{key}"
        return await self.async_request("GET", endpoint)

    async def async_get_all_settings_keys(self) -> dict[str, Any] | None:
        """GET /api/1.0/settings/allKeys"""
        return await self.async_request("GET", "/api/1.0/settings/allKeys")

    async def async_set_logging_level(self, level: str) -> dict[str, Any] | None:
        """PUT /api/1.0/settings/logging/level"""
        return await self.async_request(
            "PUT", "/api/1.0/settings/logging/level", params={"value": level}
        )

    # ------------------------------------------------------------------
    # System time  (WsAdmin_1.0_systemtime)
    # basePath: /WsAdmin/api/1.0
    # ------------------------------------------------------------------

    async def async_get_system_time(self) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/systemtime"""
        return await self.async_request("GET", "/WsAdmin/api/1.0/systemtime")

    async def async_get_ntp_servers(self) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/systemtime/ntpserver"""
        return await self.async_request("GET", "/WsAdmin/api/1.0/systemtime/ntpserver")

    async def async_get_selected_ntp_server(self) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/systemtime/ntpserver/selected"""
        return await self.async_request("GET", "/WsAdmin/api/1.0/systemtime/ntpserver/selected")

    async def async_get_timezone(self) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/systemtime/timezone"""
        return await self.async_request("GET", "/WsAdmin/api/1.0/systemtime/timezone")

    async def async_set_timezone(self, timezone: str) -> dict[str, Any] | None:
        """PUT /WsAdmin/api/1.0/systemtime/timezone"""
        return await self.async_request(
            "PUT", "/WsAdmin/api/1.0/systemtime/timezone", params={"value": timezone}
        )

    # ------------------------------------------------------------------
    # LED  (WsAdmin_1.0_led)
    # basePath: /WsAdmin/api/1.0
    # ------------------------------------------------------------------

    async def async_get_led_status(self) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/led  (returns array of LED objects)"""
        return await self.async_request("GET", "/WsAdmin/api/1.0/led")

    async def async_get_led_by_id(self, led_id: str) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/led/{id}"""
        return await self.async_request("GET", f"/WsAdmin/api/1.0/led/{led_id}")

    async def async_set_led_status(self, led_id: str, status: str) -> dict[str, Any] | None:
        """PUT /WsAdmin/api/1.0/led/{id}"""
        return await self.async_request(
            "PUT", f"/WsAdmin/api/1.0/led/{led_id}", params={"status": status}
        )

    # ------------------------------------------------------------------
    # WsAdmin Settings  (WsAdmin_1.0_settings)
    # basePath: /WsAdmin/api/1.0
    # ------------------------------------------------------------------

    async def async_get_admin_settings(self, key: str | None = None) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/settings  or  /WsAdmin/api/1.0/settings/{key}"""
        endpoint = "/WsAdmin/api/1.0/settings"
        if key:
            endpoint += f"/{key}"
        return await self.async_request("GET", endpoint)

    async def async_set_admin_logging_level(self, level: str) -> dict[str, Any] | None:
        """PUT /WsAdmin/api/1.0/settings/logging/level"""
        return await self.async_request(
            "PUT", "/WsAdmin/api/1.0/settings/logging/level", params={"value": level}
        )

    # ------------------------------------------------------------------
    # Update / Firmware  (WsAdmin_1.0_update)
    # basePath: /WsAdmin/api/1.0
    # ------------------------------------------------------------------

    async def async_get_factory_reset_status(self) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/update/factoryReset"""
        return await self.async_request("GET", "/WsAdmin/api/1.0/update/factoryReset")

    async def async_factory_reset(self, method: str) -> dict[str, Any] | None:
        """PUT /WsAdmin/api/1.0/update/factoryReset/{method}"""
        return await self.async_request("PUT", f"/WsAdmin/api/1.0/update/factoryReset/{method}")

    async def async_get_firmware_info(self, method: str) -> dict[str, Any] | None:
        """GET /WsAdmin/api/1.0/update/firmware/{method}"""
        return await self.async_request("GET", f"/WsAdmin/api/1.0/update/firmware/{method}")

    async def async_post_firmware_update(
        self, method: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """POST /WsAdmin/api/1.0/update/firmware/{method}"""
        return await self.async_request(
            "POST", f"/WsAdmin/api/1.0/update/firmware/{method}", json=data
        )

    async def async_put_firmware_update(
        self, method: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        """PUT /WsAdmin/api/1.0/update/firmware/{method}"""
        return await self.async_request(
            "PUT", f"/WsAdmin/api/1.0/update/firmware/{method}", json=data
        )

    # ------------------------------------------------------------------
    # Fehlerlog  (InfoWinFehlerlog_1.0_fehlerlog)
    # basePath: /InfoWinFehlerlog/api/1.0
    # ------------------------------------------------------------------

    async def async_get_fehlerlog(self) -> dict[str, Any] | None:
        """GET /InfoWinFehlerlog/api/1.0/fehlerlog"""
        return await self.async_request("GET", "/InfoWinFehlerlog/api/1.0/fehlerlog")

    async def async_reset_fehlerlog(self, error_id: str = "0") -> dict[str, Any] | None:
        """PUT /InfoWinFehlerlog/api/1.0/fehlerlog/reset/{id}

        ASSUMPTION: id=0 resets all errors. Verify on real hardware.
        """
        return await self.async_request(
            "PUT", f"/InfoWinFehlerlog/api/1.0/fehlerlog/reset/{error_id}"
        )

    # ------------------------------------------------------------------
    # Heartbeat  (InfoWinHeartbeat_1.0_heartbeat)
    # basePath: /InfoWinHeartbeat/api/1.0
    # ------------------------------------------------------------------

    async def async_get_heartbeat(self) -> dict[str, Any] | None:
        """GET /InfoWinHeartbeat/api/1.0/heartbeat"""
        return await self.async_request("GET", "/InfoWinHeartbeat/api/1.0/heartbeat")

    async def async_start_heartbeat(self) -> dict[str, Any] | None:
        """POST /InfoWinHeartbeat/api/1.0/heartbeat"""
        return await self.async_request("POST", "/InfoWinHeartbeat/api/1.0/heartbeat")

    async def async_stop_heartbeat(self) -> dict[str, Any] | None:
        """DELETE /InfoWinHeartbeat/api/1.0/heartbeat"""
        return await self.async_request("DELETE", "/InfoWinHeartbeat/api/1.0/heartbeat")

    async def async_update_heartbeat(self, subnet_id: str, node_id: str) -> dict[str, Any] | None:
        """PUT /InfoWinHeartbeat/api/1.0/heartbeat/{subnet}/{nodeId}"""
        return await self.async_request(
            "PUT", f"/InfoWinHeartbeat/api/1.0/heartbeat/{subnet_id}/{node_id}"
        )

    # ------------------------------------------------------------------
    # Kesselwahl  (InfoWinHeartbeat_1.0_kesselwahl)
    # basePath: /InfoWinHeartbeat/api/1.0
    # ------------------------------------------------------------------

    async def async_get_kesselwahl(self, method: str) -> dict[str, Any] | None:
        """GET /InfoWinHeartbeat/api/1.0/kesselwahl/{method}"""
        return await self.async_request("GET", f"/InfoWinHeartbeat/api/1.0/kesselwahl/{method}")

    async def async_get_kesselwahl_selected(self) -> dict[str, Any] | None:
        """GET /InfoWinHeartbeat/api/1.0/kesselwahl/selected

        Returns the currently active boiler type as KesselwahlModel {id, name}.
        Documented enum: 1=Pellets, 2=Holz, 3=Kombikessel, 4=Hackschnitzel,
        5=Oel, 6=Nein, 7=MB1, 8=MB2.
        """
        return await self.async_request("GET", "/InfoWinHeartbeat/api/1.0/kesselwahl/selected")

    async def async_get_kesselwahl_list(self) -> dict[str, Any] | None:
        """GET /InfoWinHeartbeat/api/1.0/kesselwahl/list

        Returns all available boiler types supported by the connected controller.
        """
        return await self.async_request("GET", "/InfoWinHeartbeat/api/1.0/kesselwahl/list")

    async def async_put_kesselwahl(
        self, boiler_id: str, option: str | None = None
    ) -> dict[str, Any] | None:
        """PUT /InfoWinHeartbeat/api/1.0/kesselwahl/{id}

        Switch active boiler.  Documented id enum: 1..8 (see kesselwahl Swagger).
        Optional query param option: '0 none' or '1 withServicePin'.
        """
        params: dict[str, str] = {}
        if option is not None:
            params["option"] = option
        return await self.async_request(
            "PUT",
            f"/InfoWinHeartbeat/api/1.0/kesselwahl/{boiler_id}",
            params=params or None,
        )

    # ------------------------------------------------------------------
    # VPN  (RestApiRC7030_1.0_vpn)
    # basePath: /api/1.0/vpn
    # ------------------------------------------------------------------

    async def async_get_vpn_status(self) -> dict[str, Any] | None:
        """GET /api/1.0/vpn/status"""
        return await self.async_request("GET", "/api/1.0/vpn/status")

    # ------------------------------------------------------------------
    # DynIP  (RestApiRC7030_1.0_dynip)
    # basePath: /api/1.0
    # ------------------------------------------------------------------

    async def async_check_dynip(self) -> dict[str, Any] | None:
        """GET /api/1.0/DynIP/CheckIP"""
        return await self.async_request("GET", "/api/1.0/DynIP/CheckIP")

    # ------------------------------------------------------------------
    # Notification  (WsFUP7030_1.0_notification)
    # basePath: /WsFUP7030/api/1.0
    # ------------------------------------------------------------------

    async def async_register_notification(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """POST /WsFUP7030/api/1.0/notification/register"""
        return await self.async_request(
            "POST", "/WsFUP7030/api/1.0/notification/register", json=data
        )

    async def async_unregister_notification(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """POST /WsFUP7030/api/1.0/notification/unregister"""
        return await self.async_request(
            "POST", "/WsFUP7030/api/1.0/notification/unregister", json=data
        )

    # ------------------------------------------------------------------
    # dprecorder  (dprecorder_1.0_recorder)
    # basePath: /dprecorder/api/1.0
    # ------------------------------------------------------------------

    async def async_get_recorder(self, recorder_id: str) -> dict[str, Any] | None:
        """GET /dprecorder/api/1.0/recorder/{id}"""
        return await self.async_request("GET", f"/dprecorder/api/1.0/recorder/{recorder_id}")

    async def async_recorder_action(
        self, action: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """POST /dprecorder/api/1.0/recorder/{action}"""
        return await self.async_request(
            "POST", f"/dprecorder/api/1.0/recorder/{action}", json=data or {}
        )

    # ------------------------------------------------------------------
    # LON Services  (WsFUP7030_1.0_srv0620/0621/0622/0623/1024/1025)
    # basePath: /WsFUP7030/api/1.0
    # ------------------------------------------------------------------

    async def async_get_srv0620(
        self, subnet_id: str, node_id: str, fnct_nbr: str, level_idx: str
    ) -> dict[str, Any] | None:
        """GET /WsFUP7030/api/1.0/srv0620/{subnet}/{nodeId}/{fnctNbr}/{levelIdx}"""
        return await self.async_request(
            "GET", f"/WsFUP7030/api/1.0/srv0620/{subnet_id}/{node_id}/{fnct_nbr}/{level_idx}"
        )

    async def async_post_srv0620(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """POST /WsFUP7030/api/1.0/srv0620"""
        return await self.async_request("POST", "/WsFUP7030/api/1.0/srv0620", json=data)

    async def async_get_srv0621(
        self, subnet_id: str, node_id: str, main_sel: str, sub_sel: str
    ) -> dict[str, Any] | None:
        """GET /WsFUP7030/api/1.0/srv0621/{subnet}/{nodeId}/{mainSel}/{subSel}"""
        return await self.async_request(
            "GET", f"/WsFUP7030/api/1.0/srv0621/{subnet_id}/{node_id}/{main_sel}/{sub_sel}"
        )

    async def async_post_srv0621(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """POST /WsFUP7030/api/1.0/srv0621"""
        return await self.async_request("POST", "/WsFUP7030/api/1.0/srv0621", json=data)

    async def async_get_srv0622(
        self, subnet_id: str, node_id: str, main_sel: str, sub_sel: str
    ) -> dict[str, Any] | None:
        """GET /WsFUP7030/api/1.0/srv0622/{subnet}/{nodeId}/{mainSel}/{subSel}"""
        return await self.async_request(
            "GET", f"/WsFUP7030/api/1.0/srv0622/{subnet_id}/{node_id}/{main_sel}/{sub_sel}"
        )

    async def async_post_srv0622(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """POST /WsFUP7030/api/1.0/srv0622"""
        return await self.async_request("POST", "/WsFUP7030/api/1.0/srv0622", json=data)

    async def async_put_srv0623(self, oid: str, value: str) -> dict[str, Any] | None:
        """PUT /WsFUP7030/api/1.0/srv0623"""
        return await self.async_request(
            "PUT", "/WsFUP7030/api/1.0/srv0623", params={"oid": oid, "value": value}
        )

    async def async_post_srv0623(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """POST /WsFUP7030/api/1.0/srv0623"""
        return await self.async_request("POST", "/WsFUP7030/api/1.0/srv0623", json=data)

    async def async_get_srv1024(
        self,
        subnet_id: str,
        node_id: str,
        fct_id: str,
        group_id: str,
        member_id: str,
        var_inst: str = "0",
    ) -> dict[str, Any] | None:
        """GET WsFUP7030 srv1024 with six OID path segments and optional varInst."""
        return await self.async_request(
            "GET",
            f"/WsFUP7030/api/1.0/srv1024/{subnet_id}/{node_id}/{fct_id}/{group_id}/{member_id}/{var_inst}",
        )

    async def async_put_srv1025(self, oid: str, value: str) -> dict[str, Any] | None:
        """PUT /WsFUP7030/api/1.0/srv1025"""
        return await self.async_request(
            "PUT", "/WsFUP7030/api/1.0/srv1025", params={"oid": oid, "value": value}
        )

    # ------------------------------------------------------------------
    # LON Node Scan  (RestApiRC7030_1.0_scan)
    # basePath: /api/1.0
    # ------------------------------------------------------------------

    # Documented cmd enum from RestApiRC7030_1.0_scan.json
    _SCAN_CMD_ENUM: frozenset[str] = frozenset(
        {
            "initscan",
            "start",
            "stop",
            "scanNodes",
            "queryID",
            "postScan",
            "queryNodeName",
            "queryNodeFunctions",
            "quit",
            "scanDone",
        }
    )

    async def async_get_scan_model(self) -> dict[str, Any] | None:
        """GET /api/1.0/scan/nodes/model — retrieve current LonScanModel."""
        return await self.async_request("GET", "/api/1.0/scan/nodes/model")

    async def async_put_scan_model(self, model: dict[str, Any]) -> dict[str, Any] | None:
        """PUT /api/1.0/scan/nodes/model — set LonScanModel {verbose, auto, groups}."""
        return await self.async_request("PUT", "/api/1.0/scan/nodes/model", json=model)

    async def async_get_scan_status(self) -> dict[str, Any] | None:
        """GET /api/1.0/scan/nodes/status — retrieve current scan state.

        ASSUMPTION: the device returns a JSON object whose structure is
        undocumented in Swagger.  The raw response is logged at DEBUG level on
        first call so real-world shapes can be captured and the terminal-state
        check tightened.
        """
        return await self.async_request("GET", "/api/1.0/scan/nodes/status")

    async def async_put_scan_cmd(self, cmd: str) -> dict[str, Any] | None:
        """PUT /api/1.0/scan/nodes/{cmd} — issue a LonScanStateMachine command.

        cmd must be one of the documented enum values:
        initscan, start, stop, scanNodes, queryID, postScan,
        queryNodeName, queryNodeFunctions, quit, scanDone.
        """
        if cmd not in self._SCAN_CMD_ENUM:
            raise ValueError(
                f"Invalid scan cmd '{cmd}'. Must be one of {sorted(self._SCAN_CMD_ENUM)}"
            )
        return await self.async_request("PUT", f"/api/1.0/scan/nodes/{cmd}")

    # ------------------------------------------------------------------
    # Connection test
    # ------------------------------------------------------------------

    async def async_test_connection(self) -> bool:
        """Test connectivity and authentication.

        Tries GET /api/1.0/lookup (lightest documented endpoint).
        Returns True if a valid (authenticated) response is received.
        """
        try:
            result = await self.async_request("GET", "/api/1.0/lookup")
            return result is not None
        except WindhagerAuthError:
            _LOGGER.debug("Connection test: authentication failed")
            raise
        except (WindhagerTimeoutError, WindhagerConnectionError, WindhagerApiError) as err:
            _LOGGER.debug("Connection test failed: %s", err)
            return False
