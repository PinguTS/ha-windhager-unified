"""Tests for the export module, service handler, and export button.

Covers:
- async_start_export: success, concurrent-export guard
- _export internals: discovery, XML download, ZIP creation
- Service registration and handler in __init__.py
- WindhagerExportButton entity creation and press
"""

from __future__ import annotations

import asyncio
import contextlib
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.windhager_unified.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from custom_components.windhager_unified.discovery import (
    DiscoveredDatapoint,
    DiscoveredFunction,
    DiscoveredGroup,
    DiscoveredNode,
    DiscoveryResult,
)

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENTRY_DATA = {
    CONF_HOST: "http://test-host",
    CONF_USERNAME: "user",
    CONF_PASSWORD: "pass",
    CONF_VERIFY_SSL: False,
    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
}


def _make_coordinator(hass):
    from custom_components.windhager_unified.coordinator import WindhagerCoordinator

    coord = WindhagerCoordinator(
        hass=hass,
        host="http://test-host",
        username="user",
        password="pass",
        verify_ssl=False,
        scan_interval=30,
    )
    coord.api_client.async_init = AsyncMock()
    coord.api_client.async_close = AsyncMock()
    coord.api_client.async_request = AsyncMock(return_value={"text": ""})
    coord.api_client.async_get_subnets = AsyncMock(return_value={"subnets": []})
    coord.async_initialize_catalog = AsyncMock()
    coord.async_refresh = AsyncMock()
    coord.last_update_success = True
    coord.data = {}
    coord.export_task = None
    return coord


def _minimal_discovery_result() -> DiscoveryResult:
    dp = DiscoveredDatapoint(
        oid="1/15/0/0/0/0",
        level_id=0,
        write_prot=True,
        type_id=13,
        unit_id=1,
        experience_minimum="essential",
        api_name="00-000",
    )
    func = DiscoveredFunction(fct_id=0, fct_type=15, name="UMUMLZ", datapoints=[dp])
    node = DiscoveredNode(
        node_id=15,
        subnet=1,
        name="Test Node",
        neuron_id="AABBCC",
        program_id="0001",
        functions=[func],
    )
    group = DiscoveredGroup(
        id="buffer",
        label="Buffer / Shift valve",
        fct_type=15,
        node_ids=[15],
        datapoints=[dp],
    )
    return DiscoveryResult(
        boiler_id=2,
        boiler_name="LogWIN (Holz)",
        nodes=[node],
        groups=[group],
    )


# ---------------------------------------------------------------------------
# _build_discovery_yaml
# ---------------------------------------------------------------------------


def test_build_discovery_yaml_structure():
    import yaml as _yaml

    from custom_components.windhager_unified.export import _build_discovery_yaml

    result = _minimal_discovery_result()
    raw = _build_discovery_yaml(result)
    doc = _yaml.safe_load(raw.decode("utf-8"))

    assert "meta" in doc
    assert "datapoints" in doc
    assert doc["meta"]["boiler_name"] == "LogWIN (Holz)"
    assert len(doc["datapoints"]) == 1
    dp = doc["datapoints"][0]
    assert dp["oid"] == "1/15/0/0/0/0"
    assert dp["group"] == "buffer"
    assert dp["node_id"] == 15
    assert dp["fct_type"] == 15


# ---------------------------------------------------------------------------
# _build_meta_json
# ---------------------------------------------------------------------------


def test_build_meta_json_no_credentials(hass):
    import json

    from custom_components.windhager_unified.export import _build_meta_json

    coord = _make_coordinator(hass)
    result = _minimal_discovery_result()
    raw = _build_meta_json(result, coord, "20260101_120000")
    meta = json.loads(raw.decode("utf-8"))

    assert meta["boiler_name"] == "LogWIN (Holz)"
    assert meta["node_count"] == 1
    assert meta["datapoint_count"] == 1
    # Credential keys must not appear as top-level keys in the exported dict
    assert "password" not in meta
    assert "username" not in meta
    assert "host" not in meta


# ---------------------------------------------------------------------------
# _write_zip
# ---------------------------------------------------------------------------


def test_write_zip_creates_expected_entries(tmp_path):
    from custom_components.windhager_unified.export import _write_zip

    dest = tmp_path / "test.zip"
    _write_zip(
        dest,
        yaml_bytes=b"datapoints: []",
        meta_bytes=b'{"test": 1}',
        xml_files={"Foo_de.xml": "<root/>", "Bar.xml": "<bar/>"},
    )

    assert dest.exists()
    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
    assert "discovery.yaml" in names
    assert "meta.json" in names
    assert "xml/Foo_de.xml" in names
    assert "xml/Bar.xml" in names


def test_write_zip_no_xml_files(tmp_path):
    from custom_components.windhager_unified.export import _write_zip

    dest = tmp_path / "empty.zip"
    _write_zip(dest, yaml_bytes=b"datapoints: []", meta_bytes=b"{}", xml_files={})

    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
    assert "discovery.yaml" in names
    assert "meta.json" in names
    # No xml/ entries
    assert not any(n.startswith("xml/") for n in names)


# ---------------------------------------------------------------------------
# _download_xml_files
# ---------------------------------------------------------------------------

_APACHE_INDEX = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html><head><title>Index of /res/xml</title></head><body>
<ul>
<li><a href="/res/">Parent Directory</a></li>
<li><a href="VarIdentTexte_de.xml">VarIdentTexte_de.xml</a></li>
<li><a href="AufzaehlTexte_de.xml">AufzaehlTexte_de.xml</a></li>
</ul></body></html>"""


@pytest.mark.asyncio
async def test_download_xml_files_success(hass):
    from custom_components.windhager_unified.export import _download_xml_files

    coord = _make_coordinator(hass)

    responses = {
        "/res/xml/": {"text": _APACHE_INDEX},
        "/res/xml/VarIdentTexte_de.xml": {"text": "<root/>"},
        "/res/xml/AufzaehlTexte_de.xml": {"text": "<enum/>"},
    }

    async def _fake_request(method, path, **_kwargs):
        return responses.get(path, {"text": ""})

    coord.api_client.async_request = _fake_request

    # Suppress sleep delays in tests
    with patch("custom_components.windhager_unified.export.asyncio.sleep", new_callable=AsyncMock):
        result = await _download_xml_files(hass, coord)

    assert "VarIdentTexte_de.xml" in result
    assert "AufzaehlTexte_de.xml" in result
    assert result["VarIdentTexte_de.xml"] == "<root/>"


@pytest.mark.asyncio
async def test_download_xml_files_partial_failure(hass):
    """When one XML download fails, others continue."""
    from custom_components.windhager_unified.exceptions import WindhagerConnectionError
    from custom_components.windhager_unified.export import _download_xml_files

    coord = _make_coordinator(hass)

    async def _fake_request(method, path, **_kwargs):
        if path == "/res/xml/":
            return {"text": _APACHE_INDEX}
        if "VarIdentTexte" in path:
            raise WindhagerConnectionError("timeout")
        return {"text": "<enum/>"}

    coord.api_client.async_request = _fake_request

    with patch("custom_components.windhager_unified.export.asyncio.sleep", new_callable=AsyncMock):
        result = await _download_xml_files(hass, coord)

    # Failed file absent, successful file present
    assert "VarIdentTexte_de.xml" not in result
    assert "AufzaehlTexte_de.xml" in result


@pytest.mark.asyncio
async def test_download_xml_files_index_failure(hass):
    """When the /res/xml/ index fails, return empty dict."""
    from custom_components.windhager_unified.exceptions import WindhagerConnectionError
    from custom_components.windhager_unified.export import _download_xml_files

    coord = _make_coordinator(hass)
    coord.api_client.async_request = AsyncMock(side_effect=WindhagerConnectionError("err"))

    result = await _download_xml_files(hass, coord)
    assert result == {}


@pytest.mark.asyncio
async def test_download_xml_files_empty_index(hass):
    """When the directory index has no XML links, return empty dict."""
    from custom_components.windhager_unified.export import _download_xml_files

    coord = _make_coordinator(hass)
    coord.api_client.async_request = AsyncMock(return_value={"text": "<html></html>"})

    result = await _download_xml_files(hass, coord)
    assert result == {}


# ---------------------------------------------------------------------------
# async_start_export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_start_export_spawns_task(hass):
    from custom_components.windhager_unified.export import async_start_export

    coord = _make_coordinator(hass)

    with patch(
        "custom_components.windhager_unified.export._export",
        new_callable=AsyncMock,
        return_value=Path("/config/windhager_export/test.zip"),
    ):
        await async_start_export(hass, coord)

    assert coord.export_task is not None
    # Allow the background task to settle
    await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_async_start_export_prevents_concurrent(hass):
    """Calling async_start_export while a task is running raises RuntimeError."""
    from custom_components.windhager_unified.export import async_start_export

    coord = _make_coordinator(hass)

    # Create a never-completing task to simulate a running export
    async def _never():
        await asyncio.sleep(9999)

    coord.export_task = asyncio.get_event_loop().create_task(_never())

    with pytest.raises(RuntimeError, match="already in progress"):
        await async_start_export(hass, coord)

    coord.export_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await coord.export_task


@pytest.mark.asyncio
async def test_async_start_export_rerun_after_completion(hass):
    """A second export is allowed after the first task is done."""
    from custom_components.windhager_unified.export import async_start_export

    coord = _make_coordinator(hass)

    async def _done():
        pass

    done_task = asyncio.get_event_loop().create_task(_done())
    await done_task
    coord.export_task = done_task  # done task

    with patch(
        "custom_components.windhager_unified.export._export",
        new_callable=AsyncMock,
        return_value=Path("/config/windhager_export/test.zip"),
    ):
        await async_start_export(hass, coord)

    assert coord.export_task is not None
    await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# Service handler in __init__.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_service_registered(hass):
    from custom_components.windhager_unified import async_setup_entry

    entry = MagicMock()
    entry.entry_id = "se1"
    entry.data = _ENTRY_DATA
    entry.options = {}
    entry.async_create_background_task = lambda _hass, coro, _name: asyncio.create_task(coro)

    coord = _make_coordinator(hass)

    with (
        patch(
            "custom_components.windhager_unified.WindhagerCoordinator",
            return_value=coord,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        await async_setup_entry(hass, entry)

    assert hass.services.has_service(DOMAIN, "export_system_info")


@pytest.mark.asyncio
async def test_export_service_handler_wraps_error_as_ha_error(hass):
    """Service handler in __init__ wraps RuntimeError → HomeAssistantError."""
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.windhager_unified import async_setup_entry

    entry = MagicMock()
    entry.entry_id = "se2"
    entry.data = _ENTRY_DATA
    entry.options = {}
    entry.async_create_background_task = lambda _hass, coro, _name: asyncio.create_task(coro)

    coord = _make_coordinator(hass)

    with (
        patch(
            "custom_components.windhager_unified.WindhagerCoordinator",
            return_value=coord,
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups",
            new_callable=AsyncMock,
        ),
    ):
        await async_setup_entry(hass, entry)

    # Simulate async_start_export raising RuntimeError (concurrent guard)
    call = MagicMock()
    call.data = {}

    with (
        patch(
            "custom_components.windhager_unified._resolve_config_entry",
            return_value=entry,
        ),
        patch(
            "custom_components.windhager_unified.export.async_start_export",
            side_effect=RuntimeError("An export is already in progress"),
        ),
        pytest.raises(HomeAssistantError, match="already in progress"),
    ):
        await hass.services.async_call(DOMAIN, "export_system_info", {}, blocking=True)


# ---------------------------------------------------------------------------
# WindhagerExportButton
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_button_created(hass):
    from custom_components.windhager_unified.button import WindhagerExportButton

    coord = _make_coordinator(hass)
    entry = MagicMock()
    entry.entry_id = "btn_entry"

    button = WindhagerExportButton(coord, entry)

    assert button.unique_id == "btn_entry_export_system_info"
    assert button.entity_registry_enabled_default is False
    assert button.translation_key == "export_system_info"


@pytest.mark.asyncio
async def test_export_button_press_starts_export(hass):
    from custom_components.windhager_unified.button import WindhagerExportButton

    coord = _make_coordinator(hass)
    entry = MagicMock()
    entry.entry_id = "btn_entry_2"

    button = WindhagerExportButton(coord, entry)
    button.hass = hass

    with patch(
        "custom_components.windhager_unified.button.async_start_export",
        new_callable=AsyncMock,
    ) as mock_export:
        await button.async_press()
        mock_export.assert_awaited_once_with(hass, coord)


@pytest.mark.asyncio
async def test_export_button_press_concurrent_raises_ha_error(hass):
    """RuntimeError from async_start_export is wrapped in HomeAssistantError."""
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.windhager_unified.button import WindhagerExportButton

    coord = _make_coordinator(hass)
    entry = MagicMock()
    entry.entry_id = "btn_entry_3"

    button = WindhagerExportButton(coord, entry)
    button.hass = hass

    with (
        patch(
            "custom_components.windhager_unified.button.async_start_export",
            side_effect=RuntimeError("already in progress"),
        ),
        pytest.raises(HomeAssistantError, match="already in progress"),
    ):
        await button.async_press()
