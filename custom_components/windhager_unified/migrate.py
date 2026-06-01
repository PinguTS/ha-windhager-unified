"""Config-entry migration helpers."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import yaml
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_HOST,
    ROLE_COMMAND,
    ROLE_CONFIG,
)
from .entity_roles import resolve_config_platform, resolve_role
from .labels import LabelCatalog

_LOGGER = logging.getLogger(__name__)

_YAML_BASE = Path(__file__).parent


def _lon_unique_id(host: str, oid: str, key: str) -> str:
    return hashlib.md5(f"{host}_{oid}_{key}".encode()).hexdigest()


def _load_all_datapoints() -> list[dict[str, Any]]:
    path = _YAML_BASE / "oids.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return list(data.get("datapoints") or [])


def _control_unique_ids(host: str, catalog: LabelCatalog | None) -> set[str]:
    """Return unique_ids for datapoints that are no longer read-only sensors."""
    ids: set[str] = set()
    for dp in _load_all_datapoints():
        oid = str(dp.get("oid", ""))
        key = str(dp.get("key", ""))
        if not oid or not key:
            continue
        has_enum = False
        if catalog is not None:
            parts = oid.split("/")
            if len(parts) == 6:
                try:
                    gn, mn = int(parts[3]), int(parts[4])
                    has_enum = catalog.has_enum_labels(gn, mn)
                except ValueError:
                    pass
        role = resolve_role(dp, has_enum=has_enum)
        if role == ROLE_COMMAND:
            ids.add(_lon_unique_id(host, oid, key))
            continue
        if role == ROLE_CONFIG:
            platform = resolve_config_platform(
                dp,
                has_enum=has_enum,
                numeric_format_confirmed=True,
            )
            if platform in ("number", "select", "switch"):
                ids.add(_lon_unique_id(host, oid, key))
    return ids


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Remove stale sensor entities replaced by control platforms."""
    if config_entry.version >= 2:
        return True

    _LOGGER.info(
        "Migrating Windhager config entry %s to version 2 (entity role cleanup)",
        config_entry.entry_id,
    )

    host = config_entry.data.get(CONF_HOST, "unknown")
    catalog = LabelCatalog.load()
    control_ids = _control_unique_ids(host, catalog)

    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, config_entry.entry_id):
        if entity.domain != "sensor":
            continue
        if entity.unique_id in control_ids:
            _LOGGER.debug(
                "Removing stale sensor entity %s (unique_id=%s)",
                entity.entity_id,
                entity.unique_id,
            )
            registry.async_remove(entity.entity_id)

    hass.config_entries.async_update_entry(config_entry, version=2)
    return True
