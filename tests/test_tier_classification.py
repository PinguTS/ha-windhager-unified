"""Tests for tier ↔ lookup levelId mapping (``tier_lookup``)."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from custom_components.windhager_unified.tier_lookup import (
    _FALLBACK_FCTTYPE_LEVEL_TIERS,
    _FALLBACK_TIER_DEFAULTS,
    GN_MN_OVERRIDES,
    _load_groups_config,
    allowed_levels_for_tier,
    experience_minimum_from_discovery,
    get_tier_defaults,
    uses_easy_lookup_discovery,
)

# ---------------------------------------------------------------------------
# Legacy compatibility: TIER_LEVEL_FILTER still maps boiler (fctType 9/10) levels
# ---------------------------------------------------------------------------


def test_allowed_levels_essential_fcttype_10():
    levels = allowed_levels_for_tier("essential", fct_type=10)
    assert levels is not None
    assert 155 in levels
    assert 156 in levels
    assert 157 not in levels  # comfort-only
    assert 158 not in levels  # service-only


def test_allowed_levels_comfort_fcttype_10():
    levels = allowed_levels_for_tier("comfort", fct_type=10)
    assert levels is not None
    assert 155 in levels
    assert 156 in levels
    assert 157 in levels
    assert 158 not in levels  # service-only


def test_allowed_levels_service_fcttype_10():
    levels = allowed_levels_for_tier("service", fct_type=10)
    assert levels is None  # unrestricted for service


def test_allowed_levels_level159_service_only():
    """Level 159 observed on live hardware — assumed service-only."""
    essential = allowed_levels_for_tier("essential", fct_type=10)
    service = allowed_levels_for_tier("service", fct_type=10)
    assert essential is not None and 159 not in essential
    assert service is None  # service = unrestricted (None)


def test_allowed_levels_expert_unrestricted():
    assert allowed_levels_for_tier("expert", fct_type=10) is None
    assert allowed_levels_for_tier("expert", fct_type=14) is None
    assert allowed_levels_for_tier("expert") is None


def test_allowed_levels_unknown_fcttype_returns_none():
    """Unknown fctType: allow all levels (writeProt heuristic handles datapoints)."""
    assert allowed_levels_for_tier("essential", fct_type=99) is None
    assert allowed_levels_for_tier("comfort", fct_type=None) is None


# ---------------------------------------------------------------------------
# fctType 14 (heating circuit / UMUMLZ) — essential must allow temperature levels
# ---------------------------------------------------------------------------


def test_allowed_levels_essential_fcttype_14_temperature_levels():
    """Essential must allow temperature-reading levels for heating circuit."""
    levels = allowed_levels_for_tier("essential", fct_type=14)
    assert levels is not None
    for reading_level in (96, 113, 114, 115, 116, 117, 118, 120, 121):
        assert reading_level in levels, f"level {reading_level} must be in essential for fctType 14"


def test_allowed_levels_essential_fcttype_14_excludes_service_levels():
    levels = allowed_levels_for_tier("essential", fct_type=14)
    assert levels is not None
    for module_level in (103, 104, 105, 106):
        assert module_level not in levels, f"advanced level {module_level} must not be in essential"


def test_allowed_levels_comfort_fcttype_14_includes_user_settings():
    levels = allowed_levels_for_tier("comfort", fct_type=14)
    assert levels is not None
    for user_level in (97, 98, 99, 100, 101, 102):
        assert user_level in levels, f"comfort level {user_level} must be accessible at comfort"


def test_allowed_levels_advanced_fcttype_14_includes_all():
    levels = allowed_levels_for_tier("advanced", fct_type=14)
    assert levels is not None
    for lvl in range(96, 122):
        assert lvl in levels, f"level {lvl} must be in advanced for fctType 14"


# ---------------------------------------------------------------------------
# fctType 15/16 (buffer / pump)
# ---------------------------------------------------------------------------


def test_allowed_levels_essential_fcttype_15_includes_temperature_readings():
    levels = allowed_levels_for_tier("essential", fct_type=15)
    assert levels is not None
    for reading_level in (96, 99, 100, 104, 105):
        assert reading_level in levels


def test_allowed_levels_essential_fcttype_16_includes_temperature_readings():
    levels = allowed_levels_for_tier("essential", fct_type=16)
    assert levels is not None
    for reading_level in (96, 98, 103):
        assert reading_level in levels


# ---------------------------------------------------------------------------
# uses_easy_lookup_discovery
# ---------------------------------------------------------------------------


def test_uses_easy_lookup_discovery():
    assert uses_easy_lookup_discovery("essential") is True
    assert uses_easy_lookup_discovery("comfort") is True
    assert uses_easy_lookup_discovery("advanced") is True
    assert uses_easy_lookup_discovery("expert") is False
    assert uses_easy_lookup_discovery("service") is False


# ---------------------------------------------------------------------------
# experience_minimum_from_discovery
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level_id", "write_prot", "label", "fct_type", "expected"),
    [
        # boiler fctType 10 levels (via FCTTYPE_LEVEL_TIERS)
        (156, True, None, 10, "essential"),
        (157, True, None, 10, "comfort"),
        (158, True, None, 10, "service"),
        (159, True, None, 10, "service"),
        # heating circuit fctType 14
        (113, True, None, 14, "essential"),  # Room temperature (readings)
        (97, False, None, 14, "comfort"),  # Optimisation
        (103, False, None, 14, "advanced"),  # Module functions
        # unknown fctType falls back to LEVEL_TIER_TABLE (boiler levels) then writeProt
        (156, True, None, None, "essential"),  # legacy boiler level
        (200, True, None, None, "essential"),  # writeProt heuristic
        (200, False, None, None, "comfort"),  # writeProt heuristic
        # level_label "service" wins over all
        (99, True, "Service level", None, "service"),
    ],
)
def test_experience_minimum_from_discovery(
    level_id: int,
    write_prot: bool,
    label: str | None,
    fct_type: int | None,
    expected: str,
) -> None:
    result = experience_minimum_from_discovery(level_id, write_prot, label, fct_type=fct_type)
    assert result == expected


# ---------------------------------------------------------------------------
# YAML loading: _load_groups_config
# ---------------------------------------------------------------------------


def _fake_config_path(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "groups_config.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_load_groups_config_reads_level_tiers(tmp_path: Path) -> None:
    p = _fake_config_path(
        tmp_path,
        """
        level_tiers:
          9:
            155: essential
            157: comfort
            158: service
        gn_mn_overrides: {}
        tier_defaults:
          essential: [boiler]
    """,
    )
    with patch("custom_components.windhager_unified.tier_lookup._GROUPS_CONFIG_PATH", p):
        fcttype_tiers, overrides, tier_defs = _load_groups_config()

    assert fcttype_tiers[9][155] == "essential"
    assert fcttype_tiers[9][157] == "comfort"
    assert fcttype_tiers[9][158] == "service"
    assert overrides == {}
    assert tier_defs == {"essential": {"boiler"}}


def test_load_groups_config_reads_gn_mn_overrides(tmp_path: Path) -> None:
    p = _fake_config_path(
        tmp_path,
        """
        level_tiers:
          9:
            155: essential
        gn_mn_overrides:
          "4:92":
            experience_minimum: service
          "23:87":
            experience_minimum: comfort
        tier_defaults: {}
    """,
    )
    with patch("custom_components.windhager_unified.tier_lookup._GROUPS_CONFIG_PATH", p):
        _, overrides, _ = _load_groups_config()

    assert overrides[(4, 92)] == {"experience_minimum": "service"}
    assert overrides[(23, 87)] == {"experience_minimum": "comfort"}


def test_load_groups_config_fallback_on_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.yaml"
    with patch("custom_components.windhager_unified.tier_lookup._GROUPS_CONFIG_PATH", missing):
        fcttype_tiers, overrides, tier_defs = _load_groups_config()

    assert fcttype_tiers == _FALLBACK_FCTTYPE_LEVEL_TIERS
    assert overrides == {}
    assert tier_defs == _FALLBACK_TIER_DEFAULTS


def test_load_groups_config_fallback_on_invalid_yaml(tmp_path: Path) -> None:
    p = tmp_path / "groups_config.yaml"
    p.write_text("{{not: valid: yaml:", encoding="utf-8")
    with patch("custom_components.windhager_unified.tier_lookup._GROUPS_CONFIG_PATH", p):
        fcttype_tiers, overrides, tier_defs = _load_groups_config()

    assert fcttype_tiers == _FALLBACK_FCTTYPE_LEVEL_TIERS
    assert tier_defs == _FALLBACK_TIER_DEFAULTS


def test_load_groups_config_ignores_invalid_tier_value(tmp_path: Path) -> None:
    p = _fake_config_path(
        tmp_path,
        """
        level_tiers:
          9:
            155: essential
            156: not_a_tier
        gn_mn_overrides:
          "4:92":
            experience_minimum: also_bad
        tier_defaults:
          essential: [boiler]
    """,
    )
    with patch("custom_components.windhager_unified.tier_lookup._GROUPS_CONFIG_PATH", p):
        fcttype_tiers, overrides, _ = _load_groups_config()

    assert fcttype_tiers[9][155] == "essential"
    assert 156 not in fcttype_tiers.get(9, {})
    assert (4, 92) not in overrides


def test_get_tier_defaults_returns_dict() -> None:
    result = get_tier_defaults()
    assert isinstance(result, dict)
    assert "essential" in result
    assert "service" in result


def test_gn_mn_overrides_populated_from_real_config() -> None:
    """The bundled groups_config.yaml must define overrides for 04-092 and 04-093."""
    assert (4, 92) in GN_MN_OVERRIDES, "Software-Version (04-092) must have an override"
    assert (4, 93) in GN_MN_OVERRIDES, "Hardware-Version (04-093) must have an override"
    assert GN_MN_OVERRIDES[(4, 92)]["experience_minimum"] == "service"
    assert GN_MN_OVERRIDES[(4, 93)]["experience_minimum"] == "service"
