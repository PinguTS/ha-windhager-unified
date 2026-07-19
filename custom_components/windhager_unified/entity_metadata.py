"""Central, typed metadata parser for Windhager datapoints.

This module turns the flat YAML fields declared on each LON datapoint and
RestAPI endpoint into validated Home Assistant and domain-semantic metadata.
It is intentionally a pure data/validation layer with no I/O.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import EntityCategory

from .const import (
    DEFAULT_LON_EXPERIENCE_MINIMUM,
    EXPERIENCE_TIERS,
)

_LOGGER = logging.getLogger(__name__)


class DataRole(StrEnum):
    """Domain role of a datapoint value."""

    MEASUREMENT = "measurement"
    SETPOINT = "setpoint"
    CONFIGURATION = "configuration"
    OPERATING_STATE = "operating_state"
    ACTUATOR_STATE = "actuator_state"
    COMMAND = "command"
    COUNTER = "counter"
    FORECAST = "forecast"
    DERIVED = "derived"
    DIAGNOSTIC = "diagnostic"
    UNKNOWN = "unknown"


class TemporalSemantics(StrEnum):
    """How a datapoint's value evolves over time."""

    SAMPLED = "sampled"
    STEP = "step"
    EVENT = "event"
    COUNTER = "counter"
    SNAPSHOT = "snapshot"
    NONE = "none"


class ModelRole(StrEnum):
    """Intended use for a datapoint in future heating models."""

    FEATURE = "feature"
    TARGET = "target"
    CONTEXT = "context"
    EVENT = "event"
    CONTROL = "control"
    IGNORE = "ignore"
    UNKNOWN = "unknown"


class ParameterScope(StrEnum):
    """Classification of a writable datapoint by who should change it."""

    USER = "user"  # Day-to-day operational controls (setpoints, modes)
    CONFIG = "config"  # True configuration parameters (min/max limits)
    INSTALLER = "installer"  # System-type/installer parameters (pump control, PWM)


class HistoryImportance(StrEnum):
    """Recommendation for history collection and export."""

    CRITICAL = "critical"
    STANDARD = "standard"
    LOW = "low"
    NONE = "none"


# Attributes that carry static catalogue metadata. They must be excluded from
# Recorder attribute storage so history rows stay small and metadata changes do
# not create spurious state-change events. The primary state is never included.
UNRECORDED_SEMANTIC_ATTRIBUTES: Final = frozenset(
    {
        "windhager_data_role",
        "windhager_temporal_semantics",
        "windhager_model_role",
        "windhager_history_importance",
        "windhager_oid",
        "windhager_write_protected",
    }
)


@dataclass(frozen=True, slots=True)
class DatapointMetadata:
    """Validated Home Assistant and semantic metadata for a single datapoint."""

    # Home Assistant entity metadata
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    unit: str | None = None
    suggested_display_precision: int | None = None
    icon: str | None = None
    entity_category: EntityCategory | None = None
    enabled_by_default: bool | None = None

    # Domain semantic metadata
    data_role: DataRole = DataRole.UNKNOWN
    temporal_semantics: TemporalSemantics = TemporalSemantics.NONE
    model_role: ModelRole = ModelRole.UNKNOWN
    history_importance: HistoryImportance = HistoryImportance.STANDARD
    # ponytail: explicit flag needed because the archive must only collect
    # catalogue entries that were deliberately classified. A missing YAML key
    # must not make a datapoint eligible even though the parser defaults to
    # STANDARD.
    history_importance_explicit: bool = False

    # Warning flags produced while parsing. Used for tests; never blocks setup.
    warnings: list[str] = field(default_factory=list, repr=False, compare=False)

    def has_numeric_state(self) -> bool:
        """Best-effort check whether the primary state is numeric."""
        return self.state_class is not None or self.device_class in {
            SensorDeviceClass.TEMPERATURE,
            SensorDeviceClass.HUMIDITY,
            SensorDeviceClass.PRESSURE,
            SensorDeviceClass.ENERGY,
            SensorDeviceClass.POWER,
            SensorDeviceClass.WATER,
            SensorDeviceClass.GAS,
            SensorDeviceClass.CURRENT,
            SensorDeviceClass.VOLTAGE,
        }


def _oid_label(dp: Mapping[str, Any]) -> str:
    """Return a stable identifier for logging."""
    oid = dp.get("oid") or dp.get("endpoint")
    key = dp.get("key")
    if oid and key:
        return f"{oid} ({key})"
    return str(oid or key or "unknown")


def _as_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "1", "on"):
            return True
        if low in ("false", "no", "0", "off"):
            return False
    return None


def _parse_state_class(value: Any) -> SensorStateClass | None:
    """Map a YAML state_class string to a SensorStateClass, or None."""
    text = _as_string(value)
    if not text:
        return None
    # HA SensorStateClass values are the lowercase slugs, but the enum member
    # names are uppercase. Use the member name for compatibility with older HA.
    name = text.upper().replace("-", "_")
    return getattr(SensorStateClass, name, None)


def _parse_device_class(value: Any) -> SensorDeviceClass | None:
    text = _as_string(value)
    if not text:
        return None
    try:
        return SensorDeviceClass(text.lower())
    except ValueError:
        return None


def _parse_entity_category(value: Any) -> EntityCategory | None:
    text = _as_string(value)
    if not text:
        return None
    try:
        return EntityCategory(text.lower())
    except ValueError:
        return None


def _parse_enum(member: type, value: Any, default: Any) -> Any:
    text = _as_string(value)
    if text is None:
        return default
    try:
        return member(text.lower())
    except ValueError:
        return None


def parse_datapoint_metadata(dp: Mapping[str, Any]) -> DatapointMetadata:
    """Return validated metadata for a single datapoint or endpoint.

    Invalid values are logged with the affected OID/key and fall back safely.
    One bad entry never prevents the integration from loading.
    """
    oid_label = _oid_label(dp)
    warnings: list[str] = []

    def warn(prop: str, got: Any, action: str) -> None:
        msg = f"Invalid {prop} for {oid_label}: {got!r}; {action}"
        warnings.append(msg)
        _LOGGER.warning(msg)

    def debug_ignore(prop: str, got: Any) -> None:
        msg = f"Ignoring incompatible {prop} for {oid_label}: {got!r}"
        warnings.append(msg)
        _LOGGER.debug(msg)

    # Home Assistant metadata
    device_class = _parse_device_class(dp.get("device_class"))
    state_class = _parse_state_class(dp.get("state_class"))
    unit = _as_string(dp.get("unit"))
    suggested_display_precision = _as_int(dp.get("suggested_display_precision"))
    icon = _as_string(dp.get("icon"))
    entity_category = _parse_entity_category(dp.get("entity_category"))
    enabled_by_default = _as_bool(dp.get("enabled_by_default"))

    if dp.get("device_class") is not None and device_class is None:
        warn("device_class", dp.get("device_class"), "ignored")
    if dp.get("state_class") is not None and state_class is None:
        warn("state_class", dp.get("state_class"), "ignored")
    if dp.get("entity_category") is not None and entity_category is None:
        warn("entity_category", dp.get("entity_category"), "ignored")
    if dp.get("suggested_display_precision") is not None and suggested_display_precision is None:
        warn("suggested_display_precision", dp.get("suggested_display_precision"), "ignored")
    if dp.get("enabled_by_default") is not None and enabled_by_default is None:
        warn("enabled_by_default", dp.get("enabled_by_default"), "ignored")

    # Semantic metadata
    data_role = _parse_enum(DataRole, dp.get("data_role"), default=DataRole.UNKNOWN)
    if dp.get("data_role") is not None and data_role is None:
        data_role = DataRole.UNKNOWN
        warn("data_role", dp.get("data_role"), "falling back to unknown")

    temporal_semantics = _parse_enum(
        TemporalSemantics, dp.get("temporal_semantics"), default=TemporalSemantics.NONE
    )
    if dp.get("temporal_semantics") is not None and temporal_semantics is None:
        temporal_semantics = TemporalSemantics.NONE
        warn("temporal_semantics", dp.get("temporal_semantics"), "falling back to none")

    model_role = _parse_enum(ModelRole, dp.get("model_role"), default=ModelRole.UNKNOWN)
    if dp.get("model_role") is not None and model_role is None:
        model_role = ModelRole.UNKNOWN
        warn("model_role", dp.get("model_role"), "falling back to unknown")

    history_importance_raw = dp.get("history_importance")
    history_importance_explicit = history_importance_raw is not None
    history_importance = _parse_enum(
        HistoryImportance, history_importance_raw, default=HistoryImportance.STANDARD
    )
    if history_importance_explicit and history_importance is None:
        history_importance = HistoryImportance.STANDARD
        warn("history_importance", history_importance_raw, "falling back to standard")

    # Cross-validation: drop or warn on Home Assistant metadata combinations
    if device_class is SensorDeviceClass.ENUM:
        if state_class is not None:
            debug_ignore("state_class on enum device_class", state_class.value)
            state_class = None
        if unit is not None:
            debug_ignore("unit on enum device_class", unit)
            unit = None

    if device_class in (SensorDeviceClass.TIMESTAMP, SensorDeviceClass.DATE):
        if state_class is not None:
            debug_ignore("state_class on timestamp/date device_class", state_class.value)
            state_class = None
        if unit is not None:
            debug_ignore("unit on timestamp/date device_class", unit)
            unit = None

    if (
        state_class in (SensorStateClass.TOTAL, SensorStateClass.TOTAL_INCREASING)
        and device_class is SensorDeviceClass.TEMPERATURE
    ):
        msg = (
            f"Suspicious state_class {state_class.value!r} on temperature device_class "
            f"for {oid_label}; dropped"
        )
        warnings.append(msg)
        _LOGGER.warning(msg)
        state_class = None

    if data_role is DataRole.FORECAST and state_class is SensorStateClass.MEASUREMENT:
        debug_ignore("state_class: measurement on forecast data_role", state_class.value)
        state_class = None

    # Semantic warnings that keep the values
    if data_role is DataRole.OPERATING_STATE and temporal_semantics is TemporalSemantics.SAMPLED:
        msg = f"operating_state with sampled temporal_semantics for {oid_label}; expected event"
        warnings.append(msg)
        _LOGGER.warning(msg)

    if data_role is DataRole.ACTUATOR_STATE and state_class is SensorStateClass.MEASUREMENT:
        msg = (
            f"actuator_state with measurement state_class for {oid_label}; "
            "expected no state_class"
        )
        warnings.append(msg)
        _LOGGER.warning(msg)

    if temporal_semantics is TemporalSemantics.COUNTER and not _looks_numeric(dp, unit):
        msg = f"counter temporal_semantics on non-numeric datapoint for {oid_label}"
        warnings.append(msg)
        _LOGGER.warning(msg)

    if history_importance is HistoryImportance.CRITICAL and model_role is ModelRole.IGNORE:
        msg = f"history_importance: critical with model_role: ignore for {oid_label}"
        warnings.append(msg)
        _LOGGER.warning(msg)

    return DatapointMetadata(
        device_class=device_class,
        state_class=state_class,
        unit=unit,
        suggested_display_precision=suggested_display_precision,
        icon=icon,
        entity_category=entity_category,
        enabled_by_default=enabled_by_default,
        data_role=data_role or DataRole.UNKNOWN,
        temporal_semantics=temporal_semantics or TemporalSemantics.NONE,
        model_role=model_role or ModelRole.UNKNOWN,
        history_importance=history_importance or HistoryImportance.STANDARD,
        history_importance_explicit=history_importance_explicit,
        warnings=warnings,
    )


def _looks_numeric(dp: Mapping[str, Any], unit: str | None) -> bool:
    """Cheap heuristic for the counter-with-nonnumeric warning."""
    return dp.get("type_id") in (13, 14, 15) or unit in (
        "°C",
        "K",
        "%",
        "h",
        "min",
        "kW",
        "W",
        "Wh",
        "kWh",
    )


# ponytail: the scope-tier mapping is intentionally minimal and tied to the
# existing tier system. If more granularity is needed later, move the floors
# into a mapping and make the YAML key authoritative.
_SCOPE_TIER_FLOOR: dict[ParameterScope, str] = {
    ParameterScope.USER: "essential",
    ParameterScope.CONFIG: "expert",
    ParameterScope.INSTALLER: "service",
}


def _tier_floor(scope: ParameterScope | None) -> str | None:
    """Return the minimum experience tier for a parameter scope, or None."""
    if scope is None:
        return None
    return _SCOPE_TIER_FLOOR.get(scope)


def _max_tier(a: str | None, b: str | None) -> str:
    """Return the more restrictive of two tier slugs."""
    a_idx = EXPERIENCE_TIERS.index(a) if a in EXPERIENCE_TIERS else -1
    b_idx = EXPERIENCE_TIERS.index(b) if b in EXPERIENCE_TIERS else -1
    return EXPERIENCE_TIERS[max(a_idx, b_idx)]


def parameter_scope(dp: Mapping[str, Any]) -> ParameterScope | None:
    """Return the parameter scope for a datapoint, or None if not writable.

    Non-writable datapoints have no scope because they are not controls.
    Explicit YAML ``parameter_scope`` always wins. Otherwise derive from
    ``data_role``:

      setpoint / operating_state / command  -> USER
      configuration                          -> CONFIG
      missing / unknown / other            -> CONFIG (safe default, debug log)
    """
    write_protected = dp.get("write_protected", True)
    if write_protected:
        return None

    explicit = _as_string(dp.get("parameter_scope"))
    if explicit:
        try:
            return ParameterScope(explicit.lower())
        except ValueError:
            _LOGGER.debug(
                "Ignoring unknown parameter_scope %r for %s; falling back to data_role",
                explicit,
                _oid_label(dp),
            )

    data_role = _parse_enum(DataRole, dp.get("data_role"), default=DataRole.UNKNOWN)
    if data_role in (DataRole.SETPOINT, DataRole.OPERATING_STATE, DataRole.COMMAND):
        return ParameterScope.USER
    if data_role is DataRole.CONFIGURATION:
        return ParameterScope.CONFIG

    _LOGGER.debug(
        "No parameter scope for writable datapoint %s; defaulting to config",
        _oid_label(dp),
    )
    return ParameterScope.CONFIG


def effective_experience_minimum(
    dp: Mapping[str, Any],
    scope: ParameterScope | None,
) -> str:
    """Return the effective experience minimum, applying scope tier floors.

    Declared ``experience_minimum`` and the scope floor are combined by picking
    the more restrictive tier. Unknown declared values fall back to the
    default LON experience minimum.
    """
    declared = _as_string(dp.get("experience_minimum")) or DEFAULT_LON_EXPERIENCE_MINIMUM
    if declared not in EXPERIENCE_TIERS:
        declared = DEFAULT_LON_EXPERIENCE_MINIMUM
    floor = _tier_floor(scope)
    if floor is None:
        return declared
    return _max_tier(declared, floor)


def scope_entity_category(
    metadata: DatapointMetadata,
    scope: ParameterScope | None,
) -> EntityCategory | None:
    """Return the entity category implied by the parameter scope.

    Explicit YAML ``entity_category`` always wins. USER-scope controls appear
    in the main device panel (no category); CONFIG and INSTALLER parameters go
    into the Configuration section.
    """
    if metadata.entity_category is not None:
        return metadata.entity_category
    if scope is ParameterScope.USER:
        return None
    return EntityCategory.CONFIG


def enabled_default(metadata: DatapointMetadata, experience_minimum: str | None) -> bool:
    """Return entity_registry_enabled_default for a datapoint.

    Explicit YAML ``enabled_by_default`` always wins. Otherwise fall back to the
    experience tier: essential/comfort/advanced (index <= 2) are enabled by
    default; expert/service are disabled by default.
    """
    if metadata.enabled_by_default is not None:
        return metadata.enabled_by_default

    min_tier = experience_minimum or DEFAULT_LON_EXPERIENCE_MINIMUM
    min_idx = (
        EXPERIENCE_TIERS.index(min_tier)
        if min_tier in EXPERIENCE_TIERS
        else len(EXPERIENCE_TIERS) - 1
    )
    return min_idx <= 2


def semantic_state_attributes(
    metadata: DatapointMetadata,
    dp: Mapping[str, Any],
) -> dict[str, str]:
    """Return static semantic attributes for a datapoint.

    These attributes are meant to be exposed on the live entity and listed in
    diagnostics, but excluded from Recorder attribute storage via
    ``_unrecorded_attributes``.
    """
    return {
        "windhager_data_role": str(metadata.data_role.value),
        "windhager_temporal_semantics": str(metadata.temporal_semantics.value),
        "windhager_model_role": str(metadata.model_role.value),
        "windhager_history_importance": str(metadata.history_importance.value),
        "windhager_oid": str(dp.get("oid", dp.get("endpoint", ""))),
        "windhager_write_protected": str(bool(dp.get("write_protected", True))),
    }
