"""Select platform — RestAPI-backed selects."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
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
class WindhagerRestAPISelectDescription(SelectEntityDescription):
    """Description for a RestAPI select."""

    endpoint: str = ""
    group: str = ""
    options: list[str] = field(default_factory=list)


class WindhagerRestAPISelect(CoordinatorEntity[WindhagerCoordinator], SelectEntity):
    """Select entity backed by a RestAPI endpoint."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
        description: WindhagerRestAPISelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_options = description.options
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
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self.entity_description.key)
        return value if value in self._attr_options else None

    async def async_select_option(self, option: str) -> None:
        desc = self.entity_description
        try:
            await self.coordinator.api_client.async_request(
                "PUT", desc.endpoint, params={"value": option}
            )
        except WindhagerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


# ---------------------------------------------------------------------------
# LON OID select
# ---------------------------------------------------------------------------


@dataclass
class WindhagerLONSelectDescription(SelectEntityDescription):
    """Description for a LON enum select."""

    oid: str = ""
    datapoint: dict[str, Any] | None = None


class WindhagerLONSelect(CoordinatorEntity[WindhagerCoordinator], SelectEntity):
    """Select entity for a writable LON enum datapoint."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
        description: WindhagerLONSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._datapoint = description.datapoint or {}
        self._attr_options = list(description.options or [])
        self._attr_unique_id = lon_unique_id(entry, description.oid, description.key or "")
        self._attr_device_info = lon_device_info(coordinator, entry, self._datapoint)

    @property
    def suggested_object_id(self) -> str | None:
        key = self.entity_description.key
        return lon_suggested_object_id(key) if key else None

    @property
    def current_option(self) -> str | None:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self.entity_description.key or "")
        if raw is None:
            return None
        oid = self.entity_description.oid
        lang = self.hass.config.language if self.hass else "en"
        label = self.coordinator.get_enum_label(oid, raw, lang)
        if label in self._attr_options:
            return label
        return None

    async def async_select_option(self, option: str) -> None:
        oid = self.entity_description.oid
        lang = self.hass.config.language if self.hass else "en"
        enum_id = self.coordinator.get_enum_id(oid, option, lang)
        if enum_id is None:
            raise HomeAssistantError(f"Unknown option '{option}' for {oid}")
        try:
            oid_parts = oid.split("/")
            # ASSUMPTION A: enum write uses integer id as string.
            await self.coordinator.api_client.async_put_datapoint(oid_parts, str(enum_id))
        except WindhagerError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RestAPI and LON selects from a config entry."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

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
            != "select"
        ):
            continue
        exp_min = datapoint.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
        i18n = datapoint.get("i18n", {})
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        options = coordinator.get_enum_options(oid, lang)
        description = WindhagerLONSelectDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            oid=oid,
            datapoint=datapoint,
            options=options,
            entity_registry_enabled_default=_is_lon_enabled_default(exp_min, selected_tier),
        )
        entities.append(WindhagerLONSelect(coordinator, entry, description))

    for group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep_cfg in endpoints:
            if ep_cfg.get("entity_type") != "select":
                continue
            exp_min = ep_cfg.get("experience_minimum", DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM)
            i18n = ep_cfg.get("i18n", {})
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPISelectDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                endpoint=ep_cfg["endpoint"],
                group=group_name,
                options=ep_cfg.get("options", []),
                entity_registry_enabled_default=_is_enabled_default(exp_min, selected_tier),
            )
            entities.append(WindhagerRestAPISelect(coordinator, entry, description))

    async_add_entities(entities)
