"""Time platform — writable LON wall-clock time datapoints.

ASSUMPTION: the device accepts time writes in the same HH:MM format returned by
GET /api/1.0/datapoint.  Swagger documents the PUT `value` parameter only as an
opaque string, so this format is an assumption, not a documented contract.  If
a future firmware version requires a different format, writes will fail visibly
with HomeAssistantError instead of silently corrupting the datapoint.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import time
from typing import Any

from homeassistant.components.time import TimeEntity, TimeEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WindhagerCoordinator
from .entity_metadata import (
    DatapointMetadata,
    effective_experience_minimum,
    enabled_default,
    parameter_scope,
    parse_datapoint_metadata,
    scope_entity_category,
    semantic_state_attributes,
)
from .exceptions import WindhagerError
from .lon_entity_helpers import lon_device_info, lon_suggested_object_id, lon_unique_id
from .lon_values import format_lon_time, is_writable_time_datapoint

_LOGGER = logging.getLogger(__name__)


@dataclass
class WindhagerLONTimeDescription(TimeEntityDescription):
    """Description for a LON OID-based time entity."""

    oid: str = ""
    datapoint: dict[str, Any] | None = None
    metadata: DatapointMetadata | None = None


class WindhagerLONTimeEntity(CoordinatorEntity[WindhagerCoordinator], TimeEntity):
    """Writable wall-clock time LON datapoint."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _unrecorded_attributes = frozenset(
        {
            "windhager_data_role",
            "windhager_temporal_semantics",
            "windhager_model_role",
            "windhager_history_importance",
            "windhager_oid",
            "windhager_write_protected",
        }
    )

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
        description: WindhagerLONTimeDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._datapoint = description.datapoint or {}
        self._attr_unique_id = lon_unique_id(entry, description.oid, description.key or "")
        self._attr_device_info = lon_device_info(coordinator, entry, self._datapoint)
        self._metadata = description.metadata

    @property
    def suggested_object_id(self) -> str | None:
        key = self.entity_description.key
        return lon_suggested_object_id(key) if key else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._metadata is None:
            return None
        return semantic_state_attributes(self._metadata, self._datapoint)

    @property
    def native_value(self) -> time | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.entity_description.key or "")

    async def async_set_value(self, value: time) -> None:
        oid = str(self._datapoint.get("oid", ""))
        oid_parts = oid.split("/")
        if len(oid_parts) != 6:
            raise HomeAssistantError(f"Invalid OID '{oid}' for time datapoint")
        payload = format_lon_time(value)
        try:
            await self.coordinator.api_client.async_put_datapoint(oid_parts, payload)
        except WindhagerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LON time entities from a config entry."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[TimeEntity] = []
    lang = hass.config.language

    for datapoint in coordinator.datapoints:
        if not is_writable_time_datapoint(datapoint):
            continue

        oid = str(datapoint["oid"])
        scope = parameter_scope(datapoint)
        exp_min = effective_experience_minimum(datapoint, scope)
        i18n = datapoint.get("i18n", {})
        metadata = parse_datapoint_metadata(datapoint)
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        description = WindhagerLONTimeDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            icon=metadata.icon,
            oid=oid,
            datapoint=datapoint,
            metadata=metadata,
            entity_category=scope_entity_category(metadata, scope),
            entity_registry_enabled_default=enabled_default(metadata, exp_min),
        )
        entities.append(WindhagerLONTimeEntity(coordinator, entry, description))

    async_add_entities(entities)
