"""Switch platform — RestAPI-backed switches and LON boolean switches."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM,
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
from .entity_roles import resolve_config_platform, resolve_role
from .exceptions import WindhagerError
from .lon_entity_helpers import lon_device_info, lon_suggested_object_id, lon_unique_id

_LOGGER = logging.getLogger(__name__)


@dataclass
class WindhagerRestAPISwitchDescription(SwitchEntityDescription):
    """Description for a RestAPI switch."""

    endpoint: str = ""
    group: str = ""
    on_value: str = "on"
    off_value: str = "off"
    metadata: DatapointMetadata | None = None


class WindhagerRestAPISwitch(CoordinatorEntity[WindhagerCoordinator], SwitchEntity):
    """Switch entity backed by a RestAPI endpoint."""

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
        description: WindhagerRestAPISwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._metadata = description.metadata
        host = entry.data.get("host", "unknown")
        self._attr_unique_id = hashlib.md5(
            f"{host}_{description.endpoint}_{description.key}".encode()
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

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        value = self.coordinator.data.get(self.entity_description.key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("on", "true", "1", "enabled")
        if isinstance(value, int | float):
            return bool(value)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        desc = self.entity_description
        value = desc.on_value if state else desc.off_value
        try:
            await self.coordinator.api_client.async_request(
                "PUT", desc.endpoint, params={"value": value}
            )
        except WindhagerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


@dataclass
class WindhagerLONSwitchDescription(SwitchEntityDescription):
    """Description for a LON boolean switch."""

    oid: str = ""
    datapoint: dict[str, Any] | None = None
    metadata: DatapointMetadata | None = None


class WindhagerLONSwitch(CoordinatorEntity[WindhagerCoordinator], SwitchEntity):
    """Switch entity for a writable 0/1 LON datapoint."""

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
        description: WindhagerLONSwitchDescription,
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
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        value = self.coordinator.data.get(self.entity_description.key or "")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("on", "true", "1", "enabled")
        if isinstance(value, int | float):
            return bool(value)
        return False

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        value = "1" if state else "0"
        try:
            oid_parts = str(self._datapoint.get("oid", "")).split("/")
            await self.coordinator.api_client.async_put_datapoint(oid_parts, value)
        except WindhagerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RestAPI and LON switches from a config entry."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []
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
            != "switch"
        ):
            continue
        scope = parameter_scope(datapoint)
        exp_min = effective_experience_minimum(datapoint, scope)
        i18n = datapoint.get("i18n", {})
        metadata = parse_datapoint_metadata(datapoint)
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        description = WindhagerLONSwitchDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            oid=oid,
            datapoint=datapoint,
            metadata=metadata,
            icon=metadata.icon,
            entity_category=scope_entity_category(metadata, scope),
            entity_registry_enabled_default=enabled_default(metadata, exp_min),
        )
        entities.append(WindhagerLONSwitch(coordinator, entry, description))

    for group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep_cfg in endpoints:
            if ep_cfg.get("entity_type") != "switch":
                continue
            exp_min = ep_cfg.get("experience_minimum", DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM)
            i18n = ep_cfg.get("i18n", {})
            metadata = parse_datapoint_metadata(ep_cfg)
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPISwitchDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                endpoint=ep_cfg["endpoint"],
                group=group_name,
                on_value=ep_cfg.get("on_value", "on"),
                off_value=ep_cfg.get("off_value", "off"),
                metadata=metadata,
                icon=metadata.icon,
                entity_category=metadata.entity_category,
                entity_registry_enabled_default=enabled_default(metadata, exp_min),
            )
            entities.append(WindhagerRestAPISwitch(coordinator, entry, description))

    async_add_entities(entities)
