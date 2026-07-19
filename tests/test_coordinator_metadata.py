"""Tests for semantic metadata survival through discovery merge."""

from __future__ import annotations

from custom_components.windhager_unified.coordinator import WindhagerCoordinator
from custom_components.windhager_unified.entity_metadata import (
    DataRole,
    HistoryImportance,
    ModelRole,
    TemporalSemantics,
    parse_datapoint_metadata,
)


def _make_coordinator(mock_hass, discovered_datapoints=None):
    return WindhagerCoordinator(
        hass=mock_hass,
        host="http://test",
        username="u",
        password="p",
        verify_ssl=False,
        scan_interval=30,
        experience_level="comfort",
        discovered_datapoints=discovered_datapoints,
    )


def test_yaml_semantic_metadata_survives_discovery_gap(mock_hass):
    """Curated semantic metadata must not be erased by discovery."""
    yaml_entry = {
        "oid": "1/16/0/0/15/0",
        "key": "lon_1_16_0_0_15_0",
        "group": "buffer",
        "experience_minimum": "expert",
        "unit": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
        "suggested_display_precision": 1,
        "icon": "mdi:storage-tank",
        "data_role": "measurement",
        "temporal_semantics": "sampled",
        "model_role": "feature",
        "history_importance": "critical",
        "i18n": {"de": "Puffertemperatur Oben", "en": "Accumulator-temp. top"},
    }
    discovered = [
        {
            "oid": "1/16/0/0/15/0",
            "group": "buffer",
            "experience_minimum": "essential",
            "api_name": "00-015",
            "type_id": 13,
            "unit_id": 1,
            "write_prot": True,
        }
    ]
    coord = _make_coordinator(mock_hass, discovered_datapoints=discovered)
    coord._apply_static_config([yaml_entry], {})

    assert len(coord.datapoints) == 1
    dp = coord.datapoints[0]
    meta = parse_datapoint_metadata(dp)
    assert meta.data_role is DataRole.MEASUREMENT
    assert meta.temporal_semantics is TemporalSemantics.SAMPLED
    assert meta.model_role is ModelRole.FEATURE
    assert meta.history_importance is HistoryImportance.CRITICAL
    assert meta.icon == "mdi:storage-tank"
    assert meta.suggested_display_precision == 1


def test_discovery_only_synthetic_gets_default_semantics(mock_hass):
    """An OID not in oids.yaml must receive default semantic metadata."""
    discovered = [
        {
            "oid": "9/9/0/9/9/0",
            "group": "boiler",
            "experience_minimum": "comfort",
            "api_name": "Extra",
            "type_id": 1,
            "unit_id": 2,
            "write_prot": True,
        }
    ]
    coord = _make_coordinator(mock_hass, discovered_datapoints=discovered)
    coord._apply_static_config([], {})

    assert len(coord.datapoints) == 1
    dp = coord.datapoints[0]
    meta = parse_datapoint_metadata(dp)
    assert meta.data_role is DataRole.UNKNOWN
    assert meta.temporal_semantics is TemporalSemantics.NONE
    assert meta.model_role is ModelRole.UNKNOWN
    assert meta.history_importance is HistoryImportance.STANDARD
