"""Number platform — LON-backed configuration numbers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ROLE_CONFIG,
)
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
from .entity_roles import (
    format_write_value,
    parse_catalog_float,
    resolve_config_platform,
    resolve_role,
    validate_numeric_in_range,
)
from .exceptions import WindhagerError
from .lon_entity_helpers import lon_device_info, lon_suggested_object_id, lon_unique_id

_LOGGER = logging.getLogger(__name__)

_DEVICE_CLASS_MAP = {
    "temperature": NumberDeviceClass.TEMPERATURE,
    "humidity": NumberDeviceClass.HUMIDITY,
    "pressure": NumberDeviceClass.PRESSURE,
    "energy": NumberDeviceClass.ENERGY,
    "power": NumberDeviceClass.POWER,
}


@dataclass
class WindhagerLONNumberDescription(NumberEntityDescription):
    """Description for a LON OID-based number."""

    oid: str = ""
    datapoint: dict[str, Any] | None = None
    metadata: DatapointMetadata | None = None


class WindhagerLONNumber(CoordinatorEntity[WindhagerCoordinator], NumberEntity):
    """Writable numeric LON datapoint."""

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
        description: WindhagerLONNumberDescription,
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
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self.entity_description.key or "")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        dp = self._datapoint
        try:
            validate_numeric_in_range(dp, value)
            raw_fmt = self.coordinator.get_raw_lon_value(dp)
            payload = format_write_value(dp, value, raw_format=raw_fmt)
            oid_parts = str(dp.get("oid", "")).split("/")
            await self.coordinator.api_client.async_put_datapoint(oid_parts, payload)
        except (WindhagerError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LON number entities from a config entry."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = []
    lang = hass.config.language

    for datapoint in coordinator.datapoints:
        oid = str(datapoint["oid"])
        has_enum = coordinator.has_enum_labels(oid)
        if resolve_role(datapoint, has_enum=has_enum) != ROLE_CONFIG:
            continue
        if (
            resolve_config_platform(
                datapoint,
                has_enum=has_enum,
                numeric_format_confirmed=coordinator.lon_numeric_format_confirmed(datapoint),
            )
            != "number"
        ):
            continue

        scope = parameter_scope(datapoint)
        exp_min = effective_experience_minimum(datapoint, scope)
        i18n = datapoint.get("i18n", {})
        metadata = parse_datapoint_metadata(datapoint)
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        description = WindhagerLONNumberDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            native_unit_of_measurement=metadata.unit,
            device_class=_DEVICE_CLASS_MAP.get(datapoint.get("device_class", "")),
            native_min_value=parse_catalog_float(datapoint.get("min_value")),
            native_max_value=parse_catalog_float(datapoint.get("max_value")),
            native_step=parse_catalog_float(datapoint.get("step")),
            icon=metadata.icon,
            oid=oid,
            datapoint=datapoint,
            metadata=metadata,
            entity_category=scope_entity_category(metadata, scope),
            entity_registry_enabled_default=enabled_default(metadata, exp_min),
        )
        entities.append(WindhagerLONNumber(coordinator, entry, description))

    async_add_entities(entities)
