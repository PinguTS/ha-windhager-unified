"""System information export for the Windhager integration.

Collects full LON discovery results and XML label files from the device,
packages them into a ZIP archive, and writes it to the HA config directory.

The export runs as a background task so the service call returns immediately.
API calls are throttled to avoid overwhelming the embedded device.

IMPLEMENTATION ASSUMPTION: /res/xml/ is served as an Apache-style HTML
directory listing.  This is not documented in Swagger but was observed on
RC7030-class devices.  See labels/__init__.py for the parsing logic.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import zipfile
from asyncio import Task
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from homeassistant.components.persistent_notification import (
    async_create as pn_create,
)
from homeassistant.components.persistent_notification import (
    async_dismiss as pn_dismiss,
)
from homeassistant.core import HomeAssistant

from .discovery import DiscoveryResult, discover, serialize_discovered_datapoints_for_config
from .entity_metadata import parse_datapoint_metadata
from .labels import parse_res_xml_index

if TYPE_CHECKING:
    from .coordinator import WindhagerCoordinator

_LOGGER = logging.getLogger(__name__)

# Notification IDs
_NOTIF_PROGRESS = "windhager_export_progress"
_NOTIF_RESULT = "windhager_export_result"

# Delay between individual REST calls during XML download (seconds).
# Keeps the embedded device from being overwhelmed.
_INTER_REQUEST_DELAY_S: float = 0.3


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def async_start_export(
    hass: HomeAssistant,
    coordinator: WindhagerCoordinator,
) -> None:
    """Spawn a background export task, preventing concurrent runs.

    Returns immediately; the export runs in the background and posts
    a persistent notification on completion or failure.
    """
    existing: Task[None] | None = getattr(coordinator, "export_task", None)
    if existing is not None and not existing.done():
        raise RuntimeError("An export is already in progress for this device")

    async def _run() -> None:
        try:
            zip_path = await _export(hass, coordinator)
            pn_dismiss(hass, _NOTIF_PROGRESS)
            pn_create(
                hass,
                (
                    f"Export complete.\n\n"
                    f"ZIP saved to: `{zip_path}`\n\n"
                    "You can download it via the file editor, Samba, or SSH."
                ),
                title="Windhager Export Complete",
                notification_id=_NOTIF_RESULT,
            )
        except Exception as err:
            _LOGGER.exception("Export failed")
            pn_dismiss(hass, _NOTIF_PROGRESS)
            pn_create(
                hass,
                f"Export failed: {err}",
                title="Windhager Export Failed",
                notification_id=_NOTIF_RESULT,
            )

    coordinator.export_task = hass.async_create_background_task(_run(), "windhager_unified_export")


# ---------------------------------------------------------------------------
# Core export logic
# ---------------------------------------------------------------------------


async def _export(hass: HomeAssistant, coordinator: WindhagerCoordinator) -> Path:
    """Run the full export and return the path of the created ZIP."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    zip_name = f"windhager_export_{timestamp}.zip"
    export_dir = Path(hass.config.config_dir) / "windhager_export"

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, export_dir.mkdir, 0o755, True, True)

    zip_path = export_dir / zip_name

    # Step 1: Discovery scan
    _progress(hass, "Step 1/3: Running LON network scan… (this may take a minute)")
    result = await discover(
        coordinator.api_client,
        experience_tier=None,  # None → expert: full walk, no level filter
    )
    if result.warnings:
        for w in result.warnings:
            _LOGGER.warning("export: discovery warning: %s", w)

    # Step 2: Download XML files
    _progress(hass, "Step 2/3: Downloading XML label files from device…")
    xml_files = await _download_xml_files(hass, coordinator)

    # Step 3: Build ZIP
    _progress(hass, "Step 3/3: Building ZIP archive…")
    yaml_bytes = await loop.run_in_executor(None, _build_discovery_yaml, result)
    meta_bytes = await loop.run_in_executor(None, _build_meta_json, result, coordinator, timestamp)
    await loop.run_in_executor(None, _write_zip, zip_path, yaml_bytes, meta_bytes, xml_files)

    _LOGGER.info("export: wrote %s", zip_path)
    return zip_path


# ---------------------------------------------------------------------------
# XML download (throttled, sequential)
# ---------------------------------------------------------------------------


async def _download_xml_files(
    hass: HomeAssistant,
    coordinator: WindhagerCoordinator,
) -> dict[str, str]:
    """Download all XML files from /res/xml/ sequentially with inter-request delays."""
    client = coordinator.api_client

    # Fetch the directory index
    try:
        index_resp = await client.async_request("GET", "/res/xml/")
    except Exception as err:
        _LOGGER.warning("export: could not fetch /res/xml/ index: %s", err)
        return {}

    html = (index_resp or {}).get("text", "") if isinstance(index_resp, dict) else ""
    if not html:
        _LOGGER.warning("export: /res/xml/ returned empty body")
        return {}

    basenames = parse_res_xml_index(html)
    if not basenames:
        _LOGGER.warning("export: no .xml links found in /res/xml/ index")
        return {}

    _LOGGER.debug("export: found %d XML files; downloading sequentially", len(basenames))
    results: dict[str, str] = {}

    for i, basename in enumerate(basenames):
        if i > 0:
            await asyncio.sleep(_INTER_REQUEST_DELAY_S)

        _progress(
            hass,
            f"Step 2/3: Downloading XML files from device… ({i + 1}/{len(basenames)})",
        )

        try:
            resp = await client.async_request("GET", f"/res/xml/{basename}")
        except Exception as err:
            _LOGGER.warning("export: failed to fetch /res/xml/%s: %s", basename, err)
            continue

        text = (resp or {}).get("text", "") if isinstance(resp, dict) else ""
        if not text:
            _LOGGER.warning("export: /res/xml/%s returned empty body; skipping", basename)
            continue

        results[basename] = text
        _LOGGER.debug("export: fetched %s (%d bytes)", basename, len(text))

    return results


# ---------------------------------------------------------------------------
# YAML / JSON generation (runs in executor)
# ---------------------------------------------------------------------------


def _build_discovery_yaml(result: DiscoveryResult) -> bytes:
    """Serialize discovery result to YAML bytes."""
    rows = serialize_discovered_datapoints_for_config(result)

    # Enrich each row with node/function metadata and semantic metadata
    oid_to_extra: dict[str, dict[str, Any]] = {}
    for node in result.nodes:
        for func in node.functions:
            for dp in func.datapoints:
                if dp.oid not in oid_to_extra:
                    oid_to_extra[dp.oid] = {
                        "node_id": node.node_id,
                        "subnet": node.subnet,
                        "node_name": node.name,
                        "neuron_id": node.neuron_id,
                        "program_id": node.program_id,
                        "fct_id": func.fct_id,
                        "fct_type": func.fct_type,
                        "fct_name": func.name,
                    }

    enriched: list[dict[str, Any]] = []
    for row in rows:
        oid = row.get("oid", "")
        extra = oid_to_extra.get(oid, {})
        meta = parse_datapoint_metadata(row)
        semantic = {
            "windhager_data_role": meta.data_role.value,
            "windhager_temporal_semantics": meta.temporal_semantics.value,
            "windhager_model_role": meta.model_role.value,
            "windhager_history_importance": meta.history_importance.value,
        }
        enriched.append({**row, **extra, **semantic})

    doc: dict[str, Any] = {
        "meta": {
            "description": (
                "Windhager LON discovery export. "
                "Submit this file to help improve the integration's oids.yaml catalog."
            ),
            "boiler_id": result.boiler_id,
            "boiler_name": result.boiler_name,
            "warnings": result.warnings or [],
        },
        "datapoints": enriched,
    }

    return yaml.dump(doc, default_flow_style=False, allow_unicode=True).encode("utf-8")


def _build_meta_json(
    result: DiscoveryResult,
    coordinator: WindhagerCoordinator,
    timestamp: str,
) -> bytes:
    """Build meta.json with export metadata. Host/credentials are NOT included."""
    meta: dict[str, Any] = {
        "exported_at": timestamp,
        "integration": "windhager_unified",
        "boiler_id": result.boiler_id,
        "boiler_name": result.boiler_name,
        "node_count": len(result.nodes),
        "datapoint_count": sum(len(grp.datapoints) for grp in result.groups),
        "groups": [
            {"id": grp.id, "label": grp.label, "fct_type": grp.fct_type} for grp in result.groups
        ],
        "warnings": result.warnings or [],
        "note": "Host, username, and password are NOT included in this export.",
    }
    return json.dumps(meta, indent=2, ensure_ascii=False).encode("utf-8")


def _write_zip(
    zip_path: Path,
    yaml_bytes: bytes,
    meta_bytes: bytes,
    xml_files: dict[str, str],
) -> None:
    """Write the ZIP archive to disk (blocking, run in executor)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("discovery.yaml", yaml_bytes)
        zf.writestr("meta.json", meta_bytes)
        for basename, content in xml_files.items():
            zf.writestr(f"xml/{basename}", content.encode("utf-8"))

    zip_path.write_bytes(buf.getvalue())


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _progress(hass: HomeAssistant, message: str) -> None:
    """Update the progress persistent notification."""
    _LOGGER.debug("export: %s", message)
    pn_create(
        hass,
        message,
        title="Windhager Export In Progress",
        notification_id=_NOTIF_PROGRESS,
    )
