"""Button platform — RestAPI-backed action buttons and export button."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
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
from .export import async_start_export


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
class WindhagerRestAPIButtonDescription(ButtonEntityDescription):
    """Description for a RestAPI button."""

    endpoint: str = ""
    http_method: str = "POST"
    group: str = ""


class WindhagerRestAPIButton(CoordinatorEntity[WindhagerCoordinator], ButtonEntity):
    """Button entity that calls a RestAPI endpoint when pressed."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
        description: WindhagerRestAPIButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
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

    async def async_press(self) -> None:
        """Execute the button action."""
        desc = self.entity_description
        try:
            await self.coordinator.api_client.async_request(desc.http_method, desc.endpoint)
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
    """Set up RestAPI buttons and the export button from a config entry."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []

    selected_tier = entry.options.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL)
    lang = hass.config.language

    for group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep_cfg in endpoints:
            if ep_cfg.get("entity_type") != "button":
                continue
            exp_min = ep_cfg.get("experience_minimum", DEFAULT_REST_ACTUATOR_EXPERIENCE_MINIMUM)
            i18n = ep_cfg.get("i18n", {})
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPIButtonDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                endpoint=ep_cfg["endpoint"],
                http_method=ep_cfg.get("http_method", "POST"),
                group=group_name,
                entity_registry_enabled_default=_is_enabled_default(exp_min, selected_tier),
            )
            entities.append(WindhagerRestAPIButton(coordinator, entry, description))

    entities.append(WindhagerExportButton(coordinator, entry))

    async_add_entities(entities)
