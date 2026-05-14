"""Select platform — RestAPI-backed selects."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_EXPERIENCE_LEVEL,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM,
    DOMAIN,
    EXPERIENCE_TIERS,
)
from .coordinator import WindhagerCoordinator
from .exceptions import WindhagerError


def _is_enabled_default(experience_minimum: str | None, selected_tier: str) -> bool:
    min_tier = experience_minimum or DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up RestAPI selects from a config entry."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

    selected_tier = entry.options.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL)
    lang = hass.config.language

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
