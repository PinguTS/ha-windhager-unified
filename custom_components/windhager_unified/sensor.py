"""Sensor platform — LON OID sensors and RestAPI sensors."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import time
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_LON_EXPERIENCE_MINIMUM,
    DEFAULT_REST_SENSOR_EXPERIENCE_MINIMUM,
    DOMAIN,
    ROLE_CONFIG,
    ROLE_DIAGNOSTIC,
    ROLE_MEASUREMENT,
)
from .coordinator import WindhagerCoordinator
from .entity_metadata import (
    DatapointMetadata,
    enabled_default,
    parse_datapoint_metadata,
    semantic_state_attributes,
)
from .entity_roles import resolve_config_platform, resolve_role
from .lon_entity_helpers import lon_device_info, lon_unique_id
from .lon_values import (
    format_lon_time,
    is_date_datapoint,
    is_datetime_datapoint,
    is_time_datapoint,
    is_writable_time_datapoint,
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LON OID sensor
# ---------------------------------------------------------------------------


@dataclass
class WindhagerLONSensorDescription(SensorEntityDescription):
    """Description for a LON OID-based sensor."""

    oid: str = ""
    hint_node: str | None = None
    datapoint: dict[str, Any] | None = None
    metadata: DatapointMetadata | None = None


class WindhagerLONSensor(CoordinatorEntity[WindhagerCoordinator], SensorEntity):
    """Sensor entity backed by a LON OID datapoint."""

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
        description: WindhagerLONSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        dp = description.datapoint or {
            "oid": description.oid,
            "hint_node": description.hint_node,
            "key": description.key,
        }
        self._attr_unique_id = lon_unique_id(entry, description.oid, description.key)
        self._attr_device_info = lon_device_info(coordinator, entry, dp)
        self._metadata = description.metadata

    @property
    def suggested_object_id(self) -> str | None:
        """Stable registry slug from the datapoint key.

        VarIdent / i18n labels repeat across nodes and functions. Home Assistant
        otherwise builds ``entity_id`` from the human-readable name, which collides
        and produces ``_2``, ``_3`` suffixes for distinct OIDs.
        """
        return self.entity_description.key.replace(".", "_")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose static semantic metadata for diagnostics and future export."""
        if self._metadata is None:
            return None
        dp = self.entity_description.datapoint or {}
        return semantic_state_attributes(self._metadata, dp)

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
        # Write-protected time datapoints are kept as plain string sensors so
        # the UI shows "16:00" instead of an ISO time or a relative timestamp.
        dp = self.entity_description.datapoint or {}
        if is_writable_time_datapoint(dp) is False and is_time_datapoint(dp):
            return format_lon_time(raw) if isinstance(raw, time) else raw
        return raw


# ---------------------------------------------------------------------------
# RestAPI sensor
# ---------------------------------------------------------------------------


@dataclass
class WindhagerRestAPISensorDescription(SensorEntityDescription):
    """Description for a RestAPI endpoint sensor."""

    endpoint: str = ""
    group: str = ""
    metadata: DatapointMetadata | None = None


class WindhagerRestAPISensor(CoordinatorEntity[WindhagerCoordinator], SensorEntity):
    """Sensor entity backed by a RestAPI endpoint."""

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
        self._metadata = description.metadata

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose static semantic metadata for diagnostics and future export."""
        if self._metadata is None:
            return None
        return semantic_state_attributes(
            self._metadata, {"endpoint": self.entity_description.endpoint}
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
    lang = hass.config.language

    # LON OID sensors
    for datapoint in coordinator.datapoints:
        exp_min = datapoint.get("experience_minimum", DEFAULT_LON_EXPERIENCE_MINIMUM)
        i18n = datapoint.get("i18n", {})
        oid = datapoint["oid"]
        has_enum = coordinator.has_enum_labels(oid)
        role = resolve_role(datapoint, has_enum=has_enum)
        config_platform = resolve_config_platform(
            datapoint,
            has_enum=has_enum,
            numeric_format_confirmed=coordinator.lon_numeric_format_confirmed(datapoint),
        )
        if role == ROLE_CONFIG and config_platform is not None:
            continue
        if role not in (ROLE_MEASUREMENT, ROLE_DIAGNOSTIC, ROLE_CONFIG):
            continue

        name = coordinator.get_entity_name(oid, lang, i18n, datapoint["key"])
        metadata = parse_datapoint_metadata(datapoint)

        # Enum-typed datapoints get SensorDeviceClass.ENUM and no unit / state_class.
        # Options are built from the catalog in the current HA language.
        if coordinator.has_enum_labels(oid):
            dc = SensorDeviceClass.ENUM
            sc = None
            unit = None
            options = coordinator.get_enum_options(oid, lang) or None
            # Log any incompatible YAML metadata that we are forced to ignore.
            if metadata.state_class is not None:
                _LOGGER.debug(
                    "Ignoring state_class %r on enum datapoint %s",
                    metadata.state_class.value,
                    oid,
                )
            if metadata.unit is not None:
                _LOGGER.debug("Ignoring unit %r on enum datapoint %s", metadata.unit, oid)
        elif is_writable_time_datapoint(datapoint):
            # Writable wall-clock times are handled by the dedicated time platform,
            # not by the sensor platform.  Skip them here.
            continue
        elif is_date_datapoint(datapoint):
            # Calendar dates are parsed to datetime.date objects by the coordinator.
            # Use the DATE device class so the UI renders absolute dates like
            # "5 October 2025" instead of relative timestamps.
            dc = SensorDeviceClass.DATE
            sc = None
            unit = None
            options = None
            if metadata.state_class is not None:
                _LOGGER.debug(
                    "Ignoring state_class %r on date datapoint %s",
                    metadata.state_class.value,
                    oid,
                )
            if metadata.unit is not None:
                _LOGGER.debug("Ignoring unit %r on date datapoint %s", metadata.unit, oid)
        elif is_datetime_datapoint(datapoint):
            # Write-protected or unverified time datapoints stay as plain string
            # sensors.  They carry no device class, so the UI displays the raw
            # "HH:MM" value without relative-time formatting.
            dc = None
            sc = None
            unit = None
            options = None
            if metadata.state_class is not None:
                _LOGGER.debug(
                    "Ignoring state_class %r on write-protected time datapoint %s",
                    metadata.state_class.value,
                    oid,
                )
            if metadata.unit is not None:
                _LOGGER.debug(
                    "Ignoring unit %r on write-protected time datapoint %s", metadata.unit, oid
                )
        else:
            dc = metadata.device_class
            sc = metadata.state_class
            unit = metadata.unit
            options = None

        entity_category = metadata.entity_category
        if entity_category is None and role == ROLE_DIAGNOSTIC:
            entity_category = EntityCategory.DIAGNOSTIC

        description = WindhagerLONSensorDescription(
            key=datapoint["key"],
            translation_key=datapoint["key"].replace(".", "_"),
            name=name,
            native_unit_of_measurement=unit,
            device_class=dc,
            state_class=sc,
            options=options,
            suggested_display_precision=metadata.suggested_display_precision,
            icon=metadata.icon,
            oid=oid,
            hint_node=datapoint.get("hint_node"),
            datapoint=datapoint,
            metadata=metadata,
            entity_category=entity_category,
            entity_registry_enabled_default=enabled_default(metadata, exp_min),
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
            metadata = parse_datapoint_metadata(ep_cfg)
            name = coordinator.get_entity_name(ep_cfg.get("oid", ""), lang, i18n, ep_cfg["key"])
            description = WindhagerRestAPISensorDescription(
                key=ep_cfg["key"],
                translation_key=ep_cfg["key"].replace(".", "_"),
                name=name,
                device_class=metadata.device_class,
                state_class=metadata.state_class,
                native_unit_of_measurement=metadata.unit,
                suggested_display_precision=metadata.suggested_display_precision,
                icon=metadata.icon,
                endpoint=ep_cfg["endpoint"],
                group=group_name,
                metadata=metadata,
                entity_category=metadata.entity_category,
                entity_registry_enabled_default=enabled_default(metadata, exp_min),
            )
            entities.append(WindhagerRestAPISensor(coordinator, entry, description))

    async_add_entities(entities)
