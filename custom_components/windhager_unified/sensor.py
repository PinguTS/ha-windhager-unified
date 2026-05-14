"""Sensor platform — LON OID sensors and RestAPI sensors."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_EXPERIENCE_LEVEL,
    DEFAULT_EXPERIENCE_LEVEL,
    DEFAULT_LON_EXPERIENCE_MINIMUM,
    DEFAULT_REST_SENSOR_EXPERIENCE_MINIMUM,
    DOMAIN,
    EXPERIENCE_TIERS,
)
from .coordinator import WindhagerCoordinator


def _is_enabled_default(experience_minimum: str | None, selected_tier: str) -> bool:
    """Entity enabled by default only at essential/comfort/advanced minimum level."""
    min_tier = experience_minimum or DEFAULT_LON_EXPERIENCE_MINIMUM
    min_idx = (
        EXPERIENCE_TIERS.index(min_tier)
        if min_tier in EXPERIENCE_TIERS
        else len(EXPERIENCE_TIERS) - 1
    )
    return min_idx <= 2


_LOGGER = logging.getLogger(__name__)

_DEVICE_CLASS_MAP = {
    "temperature": SensorDeviceClass.TEMPERATURE,
    "timestamp": SensorDeviceClass.TIMESTAMP,
    "humidity": SensorDeviceClass.HUMIDITY,
    "pressure": SensorDeviceClass.PRESSURE,
    "energy": SensorDeviceClass.ENERGY,
    "power": SensorDeviceClass.POWER,
}
_STATE_CLASS_MAP = {
    "measurement": SensorStateClass.MEASUREMENT,
    "total": SensorStateClass.TOTAL,
    "total_increasing": SensorStateClass.TOTAL_INCREASING,
}


# ---------------------------------------------------------------------------
# LON OID sensor
# ---------------------------------------------------------------------------


@dataclass
class WindhagerLONSensorDescription(SensorEntityDescription):
    """Description for a LON OID-based sensor."""

    oid: str = ""
    hint_node: str | None = None


class WindhagerLONSensor(CoordinatorEntity[WindhagerCoordinator], SensorEntity):
    """Sensor entity backed by a LON OID datapoint."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
        description: WindhagerLONSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        host = entry.data.get("host", "unknown")
        self._attr_unique_id = hashlib.md5(
            f"{host}_{description.oid}_{description.key}".encode()
        ).hexdigest()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Windhager",
            manufacturer="Windhager",
            model=description.hint_node or "LogWIN",
        )

    @property
    def suggested_object_id(self) -> str | None:
        """Stable registry slug from the datapoint key.

        VarIdent / i18n labels repeat across nodes and functions. Home Assistant
        otherwise builds ``entity_id`` from the human-readable name, which collides
        and produces ``_2``, ``_3`` suffixes for distinct OIDs.
        """
        return self.entity_description.key.replace(".", "_")

    @property
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        raw = self.coordinator.data.get(self.entity_description.key)
        if raw is None:
            return None
        oid = self.entity_description.oid
        if oid and self.coordinator.has_enum_labels(oid):
            lang = self.hass.config.language if self.hass else "en"
            label = self.coordinator.get_enum_label(oid, raw, lang)
            # Return the label when found; None for unrecognised enum values so
            # HA shows "Unknown" rather than an out-of-options string.
            return label
        return raw


# ---------------------------------------------------------------------------
# RestAPI sensor
# ---------------------------------------------------------------------------


@dataclass
class WindhagerRestAPISensorDescription(SensorEntityDescription):
    """Description for a RestAPI endpoint sensor."""

    endpoint: str = ""
    group: str = ""


class WindhagerRestAPISensor(CoordinatorEntity[WindhagerCoordinator], SensorEntity):
    """Sensor entity backed by a RestAPI endpoint."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WindhagerCoordinator,
        entry: ConfigEntry,
        description: WindhagerRestAPISensorDescription,
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
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.entity_description.key)


# ---------------------------------------------------------------------------
# Platform setup
# ---------------------------------------------------------------------------


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LON and RestAPI sensors from a config entry."""
    coordinator: WindhagerCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    selected_tier = entry.options.get(CONF_EXPERIENCE_LEVEL, DEFAULT_EXPERIENCE_LEVEL)
    lang = hass.config.language

    # LON OID sensors
    for datapoint in coordinator.datapoints:
        exp_min = datapoint.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
        i18n = datapoint.get("i18n", {})
        oid = datapoint["oid"]
        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])

        # Enum-typed datapoints get SensorDeviceClass.ENUM and no unit / state_class.
        # Options are built from the catalog in the current HA language.
        if coordinator.has_enum_labels(oid):
            dc = SensorDeviceClass.ENUM
            sc = None
            unit = None
            options = coordinator.get_enum_options(oid, lang) or None
        else:
            dc = _DEVICE_CLASS_MAP.get(datapoint.get("device_class", ""))
            sc = _STATE_CLASS_MAP.get(datapoint.get("state_class", ""))
            unit = datapoint.get("unit")
            options = None

        description = WindhagerLONSensorDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            native_unit_of_measurement=unit,
            device_class=dc,
            state_class=sc,
            options=options,
            oid=oid,
            hint_node=datapoint.get("hint_node"),
            entity_registry_enabled_default=_is_enabled_default(exp_min, selected_tier),
        )
        entities.append(WindhagerLONSensor(coordinator, entry, description))

    if not entities:
        _LOGGER.debug("No LON datapoints configured; no LON sensors created")

    # RestAPI sensors
    for group_name, endpoints in coordinator.restapi_endpoints.items():
        for ep_cfg in endpoints:
            if ep_cfg.get("entity_type") != "sensor":
                continue
            exp_min = ep_cfg.get("experience_minimum", DEFAULT_REST_SENSOR_EXPERIENCE_MINIMUM)
            i18n = ep_cfg.get("i18n", {})
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPISensorDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                device_class=_DEVICE_CLASS_MAP.get(ep_cfg.get("device_class") or ""),
                state_class=_STATE_CLASS_MAP.get(ep_cfg.get("state_class") or ""),
                endpoint=ep_cfg["endpoint"],
                group=group_name,
                entity_registry_enabled_default=_is_enabled_default(exp_min, selected_tier),
            )
            entities.append(WindhagerRestAPISensor(coordinator, entry, description))

    async_add_entities(entities)
