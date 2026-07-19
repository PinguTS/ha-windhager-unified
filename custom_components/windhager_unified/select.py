"""Select platform — RestAPI-backed selects and LON enum selects."""

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
class WindhagerRestAPISelectDescription(SelectEntityDescription):
    """Description for a RestAPI select."""

    endpoint: str = ""
    group: str = ""
    options: list[str] = field(default_factory=list)
    metadata: DatapointMetadata | None = None


class WindhagerRestAPISelect(CoordinatorEntity[WindhagerCoordinator], SelectEntity):
    """Select entity backed by a RestAPI endpoint."""

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
        description: WindhagerRestAPISelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_options = description.options
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
    metadata: DatapointMetadata | None = None


class WindhagerLONSelect(CoordinatorEntity[WindhagerCoordinator], SelectEntity):
    """Select entity for a writable LON enum datapoint."""

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
        description: WindhagerLONSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._datapoint = description.datapoint or {}
        self._attr_options = list(description.options or [])
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
        scope = parameter_scope(datapoint)
        exp_min = effective_experience_minimum(datapoint, scope)
        i18n = datapoint.get("i18n", {})
        metadata = parse_datapoint_metadata(datapoint)
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        options = coordinator.get_enum_options(oid, lang)
        description = WindhagerLONSelectDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            oid=oid,
            datapoint=datapoint,
            metadata=metadata,
            options=options,
            icon=metadata.icon,
            entity_category=scope_entity_category(metadata, scope),
            entity_registry_enabled_default=enabled_default(metadata, exp_min),
        )
        entities.append(WindhagerLONSelect(coordinator, entry, description))

    for group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep_cfg in endpoints:
            if ep_cfg.get("entity_type") != "select":
                continue
            exp_min = ep_cfg.get("experience_minimum", DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM)
            i18n = ep_cfg.get("i18n", {})
            metadata = parse_datapoint_metadata(ep_cfg)
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPISelectDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                endpoint=ep_cfg["endpoint"],
                group=group_name,
                options=ep_cfg.get("options", []),
                metadata=metadata,
                icon=metadata.icon,
                entity_category=metadata.entity_category,
                entity_registry_enabled_default=enabled_default(metadata, exp_min),
            )
            entities.append(WindhagerRestAPISelect(coordinator, entry, description))

    async_add_entities(entities)
