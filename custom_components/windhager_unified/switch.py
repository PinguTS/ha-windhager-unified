"""Switch platform — RestAPI-backed switches."""

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
    CONF_EXPERIENCE_LEVEL,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_LON_EXPERIENCE_MINIMUM,
    DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM,
    DOMAIN,
    EXPERIENCE_TIERS,
    ROLE_CONFIG,
)
from .coordinator import WindhagerCoordinator
from .entity_roles import resolve_config_platform, resolve_role
from .exceptions import WindhagerError
from .lon_entity_helpers import lon_device_info, lon_suggested_object_id, lon_unique_id


def _is_enabled_default(experience_minimum: str | None, selected_tier: str) -> bool:
    min_tier = experience_minimum or DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM
    min_idx = (
        EXPERIENCE_TIERS.index(min_tier)
        if min_tier in EXPERIENCE_TIERS
        else len(EXPERIENCE_TIERS) - 1
    )
    return min_idx <= 2


def _is_lon_enabled_default(experience_minimum: str | None, selected_tier: str) -> bool:
    min_tier = experience_minimum or DEFAULT_LON_EXPERIENCE_MINIMUM
    min_idx = (
        EXPERIENCE_TIERS.index(min_tier)
        if min_tier in EXPERIENCE_TIERS
        else len(EXPERIENCE_TIERS) - 1
    )
    return min_idx <= 2


_LOGGER = logging.getLogger(__name__)


@dataclass
class WindhagerRestAPISwitchDescription(SwitchEntityDescription):
    """Description for a RestAPI switch."""

    endpoint: str = ""
    group: str = ""
    on_value: str = "on"
    off_value: str = "off"


class WindhagerRestAPISwitch(CoordinatorEntity[WindhagerCoordinator], SwitchEntity):
    """Switch entity backed by a RestAPI endpoint."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
        description: WindhagerRestAPISwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
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


class WindhagerLONSwitch(CoordinatorEntity[WindhagerCoordinator], SwitchEntity):
    """Switch entity for a writable 0/1 LON datapoint."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

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

    @property
    def suggested_object_id(self) -> str | None:
        key = self.entity_description.key
        return lon_suggested_object_id(key) if key else None

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

    selected_tier = entry.options.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL)
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
        exp_min = datapoint.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
        i18n = datapoint.get("i18n", {})
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        description = WindhagerLONSwitchDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            oid=oid,
            datapoint=datapoint,
            entity_registry_enabled_default=_is_lon_enabled_default(exp_min, selected_tier),
        )
        entities.append(WindhagerLONSwitch(coordinator, entry, description))

    for group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep_cfg in endpoints:
            if ep_cfg.get("entity_type") != "switch":
                continue
            exp_min = ep_cfg.get("experience_minimum", DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM)
            i18n = ep_cfg.get("i18n", {})
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPISwitchDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                endpoint=ep_cfg["endpoint"],
                group=group_name,
                on_value=ep_cfg.get("on_value", "on"),
                off_value=ep_cfg.get("off_value", "off"),
                entity_registry_enabled_default=_is_enabled_default(exp_min, selected_tier),
            )
            entities.append(WindhagerRestAPISwitch(coordinator, entry, description))

    async_add_entities(entities)
