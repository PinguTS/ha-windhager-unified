"""Button platform — RestAPI-backed action buttons and export button."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_LON_EXPERIENCE_MINIMUM,
    DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM,
    DOMAIN,
    ROLE_COMMAND,
)
from .coordinator import WindhagerCoordinator
from .entity_metadata import (
    DatapointMetadata,
    enabled_default,
    parse_datapoint_metadata,
    semantic_state_attributes,
)
from .entity_roles import command_write_value, resolve_role
from .exceptions import WindhagerError
from .export import async_start_export
from .lon_entity_helpers import lon_device_info, lon_suggested_object_id, lon_unique_id

_LOGGER = logging.getLogger(__name__)


@dataclass
class WindhagerRestAPIButtonDescription(ButtonEntityDescription):
    """Description for a RestAPI button."""

    endpoint: str = ""
    http_method: str = "POST"
    group: str = ""
    metadata: DatapointMetadata | None = None


class WindhagerRestAPIButton(CoordinatorEntity[WindhagerCoordinator], ButtonEntity):
    """Button entity that calls a RestAPI endpoint when pressed."""

    _attr_has_entity_name = True
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
        description: WindhagerRestAPIButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._metadata = description.metadata
        host = entry.data.get("host", "unknown")
        self._attr_unique_id = hashlib.md5(
            f"{host}_{description.http_method}_{description.endpoint}_{description.key}".encode()
        ).hexdigest()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{description.group}")},
            name=f"Windhager {description.group.replace('_', ' ').title()}",
            manufacturer="Windhager",
            model="LogWIN",
            via_device=(DOMAIN, entry.entry_id),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self._metadata is None:
            return None
        return semantic_state_attributes(
            self._metadata, {"endpoint": self.entity_description.endpoint, "write_protected": False}
        )

    async def async_press(self) -> None:
        """Execute the button action."""
        desc = self.entity_description
        try:
            await self.coordinator.api_client.async_request(desc.http_method, desc.endpoint)
        except WindhagerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


@dataclass
class WindhagerLONButtonDescription(ButtonEntityDescription):
    """Description for a LON command button."""

    oid: str = ""
    datapoint: dict[str, Any] | None = None
    metadata: DatapointMetadata | None = None


class WindhagerLONButton(CoordinatorEntity[WindhagerCoordinator], ButtonEntity):
    """Button that writes a trigger value to a LON command datapoint."""

    _attr_has_entity_name = True
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
        description: WindhagerLONButtonDescription,
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

    async def async_press(self) -> None:
        """Write the command trigger value (ASSUMPTION B)."""
        try:
            oid_parts = str(self._datapoint.get("oid", "")).split("/")
            value = command_write_value(self._datapoint)
            await self.coordinator.api_client.async_put_datapoint(oid_parts, value)
        except WindhagerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


class WindhagerExportButton(CoordinatorEntity[WindhagerCoordinator], ButtonEntity):
    """Button entity that triggers a background system-info export."""

    _attr_has_entity_name = True
    _attr_translation_key = "export_system_info"
    # Opt-in: disabled by default since this is a developer/contributor feature
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_export_system_info"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Windhager",
            manufacturer="Windhager",
        )

    async def async_press(self) -> None:
        """Trigger the background export."""
        try:
            await async_start_export(self.hass, self.coordinator)
        except RuntimeError as err:
            raise HomeAssistantError(str(err)) from err


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RestAPI buttons, LON command buttons, and the export button."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []
    lang = hass.config.language

    for datapoint in coordinator.datapoints:
        oid = str(datapoint["oid"])
        if resolve_role(datapoint, has_enum=coordinator.has_enum_labels(oid)) != ROLE_COMMAND:
            continue
        exp_min = datapoint.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
        i18n = datapoint.get("i18n", {})
        metadata = parse_datapoint_metadata(datapoint)
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        description = WindhagerLONButtonDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            oid=oid,
            datapoint=datapoint,
            metadata=metadata,
            icon=metadata.icon,
            entity_category=metadata.entity_category,
            entity_registry_enabled_default=enabled_default(metadata, exp_min),
        )
        entities.append(WindhagerLONButton(coordinator, entry, description))

    for group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep_cfg in endpoints:
            if ep_cfg.get("entity_type") != "button":
                continue
            exp_min = ep_cfg.get("experience_minimum", DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM)
            i18n = ep_cfg.get("i18n", {})
            metadata = parse_datapoint_metadata(ep_cfg)
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPIButtonDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                endpoint=ep_cfg["endpoint"],
                http_method=ep_cfg.get("http_method", "POST"),
                group=group_name,
                metadata=metadata,
                icon=metadata.icon,
                entity_category=metadata.entity_category,
                entity_registry_enabled_default=enabled_default(metadata, exp_min),
            )
            entities.append(WindhagerRestAPIButton(coordinator, entry, description))

    entities.append(WindhagerExportButton(coordinator, entry))

    async_add_entities(entities)
