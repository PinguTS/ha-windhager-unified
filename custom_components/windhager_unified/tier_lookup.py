"""Experience tier ↔ lookup `levelId` mapping (Windhager UI layers).

The three tables below (level_tiers, gn_mn_overrides, tier_defaults) are
loaded at import time from ``groups_config.yaml``.  The hardcoded fallback
constants are used when the file is missing or cannot be parsed.

Tier assignment logic:
  1. ``gn_mn_overrides`` — highest priority, applied after all other lookups.
  2. ``level_tiers``     — maps (fctType, levelId) → minimum tier.
  3. ``level_label``     — if the level name contains "service" → service tier.
  4. Write-protection    — writeProt=True → essential, False → comfort.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)
_GROUPS_CONFIG_PATH = Path(__file__).parent / "groups_config.yaml"

# ---------------------------------------------------------------------------
# Hardcoded fallback tables
# Used when groups_config.yaml is absent or unparseable.
# ---------------------------------------------------------------------------

_FALLBACK_BOILER_LEVEL_TIERS: dict[int, str] = {
    155: "essential",
    156: "essential",
    157: "comfort",
    158: "service",
    159: "service",  # observed live; not in EbenenTexte XML
}

_FALLBACK_HEATING_CIRCUIT_LEVEL_TIERS: dict[int, str] = {
    96: "essential",
    97: "comfort",
    98: "comfort",
    99: "comfort",
    100: "comfort",
    101: "comfort",
    102: "comfort",
    103: "advanced",
    104: "advanced",
    105: "advanced",
    106: "advanced",
    107: "advanced",
    108: "advanced",
    109: "advanced",
    110: "advanced",
    111: "advanced",
    112: "advanced",
    113: "essential",
    114: "essential",
    115: "essential",
    116: "essential",
    117: "essential",
    118: "essential",
    119: "advanced",
    120: "essential",
    121: "essential",
}

_FALLBACK_BUFFER_CONTROLLER_LEVEL_TIERS: dict[int, str] = {
    96: "essential",
    97: "advanced",
    98: "advanced",
    99: "essential",
    100: "essential",
    101: "advanced",
    102: "advanced",
    103: "advanced",
    104: "essential",
    105: "essential",
    106: "advanced",
    107: "advanced",
    108: "advanced",
}

_FALLBACK_BOILER_PUMP_LEVEL_TIERS: dict[int, str] = {
    96: "essential",
    97: "advanced",
    98: "essential",
    99: "advanced",
    100: "advanced",
    101: "advanced",
    102: "advanced",
    103: "essential",
    104: "advanced",
    105: "advanced",
    106: "advanced",
}

_FALLBACK_FCTTYPE_LEVEL_TIERS: dict[int, dict[int, str]] = {
    9: _FALLBACK_BOILER_LEVEL_TIERS,
    10: _FALLBACK_BOILER_LEVEL_TIERS,
    14: _FALLBACK_HEATING_CIRCUIT_LEVEL_TIERS,
    15: _FALLBACK_BUFFER_CONTROLLER_LEVEL_TIERS,
    16: _FALLBACK_BOILER_PUMP_LEVEL_TIERS,
}

_FALLBACK_TIER_DEFAULTS: dict[str, set[str]] = {
    "essential": {"boiler", "heating_circuit"},
    "comfort": {"boiler", "heating_circuit", "dhw", "buffer"},
    "advanced": {"boiler", "heating_circuit", "dhw", "buffer", "boiler_loading_pump", "central"},
    "expert": set(),
    "service": set(),
}

# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_VALID_TIERS = frozenset({"essential", "comfort", "advanced", "expert", "service"})


def _load_groups_config() -> tuple[
    dict[int, dict[int, str]],  # fcttype_level_tiers
    dict[tuple[int, int], dict[str, str]],  # gn_mn_overrides
    dict[str, set[str]],  # tier_defaults
]:
    """Load all three configuration tables from groups_config.yaml.

    Returns the hardcoded fallbacks for any section that is missing or invalid.
    """
    try:
        with _GROUPS_CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data: dict[str, Any] = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        _LOGGER.debug("groups_config.yaml not found; using built-in defaults")
        return _FALLBACK_FCTTYPE_LEVEL_TIERS, {}, _FALLBACK_TIER_DEFAULTS
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Could not read groups_config.yaml: %s — using built-in defaults", err)
        return _FALLBACK_FCTTYPE_LEVEL_TIERS, {}, _FALLBACK_TIER_DEFAULTS

    # --- level_tiers ---
    fcttype_level_tiers: dict[int, dict[int, str]] = {}
    raw_lt = data.get("level_tiers") or {}
    for fct_key, levels in raw_lt.items():
        try:
            fct_int = int(fct_key)
        except (TypeError, ValueError):
            _LOGGER.warning("groups_config.yaml level_tiers: invalid fctType key '%s'", fct_key)
            continue
        if not isinstance(levels, dict):
            continue
        parsed: dict[int, str] = {}
        for lid_key, tier in levels.items():
            try:
                lid_int = int(lid_key)
            except (TypeError, ValueError):
                _LOGGER.warning(
                    "groups_config.yaml level_tiers[%s]: invalid levelId '%s'", fct_int, lid_key
                )
                continue
            tier_str = str(tier)
            if tier_str not in _VALID_TIERS:
                _LOGGER.warning(
                    "groups_config.yaml level_tiers[%s][%s]: unknown tier '%s'",
                    fct_int,
                    lid_int,
                    tier_str,
                )
                continue
            parsed[lid_int] = tier_str
        if parsed:
            fcttype_level_tiers[fct_int] = parsed

    if not fcttype_level_tiers:
        _LOGGER.debug("groups_config.yaml: level_tiers empty; using built-in fallback")
        fcttype_level_tiers = _FALLBACK_FCTTYPE_LEVEL_TIERS

    # --- gn_mn_overrides ---
    gn_mn_overrides: dict[tuple[int, int], dict[str, str]] = {}
    raw_ov = data.get("gn_mn_overrides") or {}
    for key_str, override in raw_ov.items():
        parts = str(key_str).split(":")
        if len(parts) != 2:
            _LOGGER.warning("groups_config.yaml gn_mn_overrides: invalid key '%s'", key_str)
            continue
        try:
            gn, mn = int(parts[0]), int(parts[1])
        except ValueError:
            _LOGGER.warning("groups_config.yaml gn_mn_overrides: invalid key '%s'", key_str)
            continue
        if not isinstance(override, dict):
            continue
        validated: dict[str, str] = {}
        exp_min = override.get("experience_minimum")
        if exp_min is not None:
            if str(exp_min) not in _VALID_TIERS:
                _LOGGER.warning(
                    "groups_config.yaml gn_mn_overrides['%s']: unknown tier '%s'",
                    key_str,
                    exp_min,
                )
            else:
                validated["experience_minimum"] = str(exp_min)
        canonical_group = override.get("canonical_group")
        if canonical_group is not None:
            validated["canonical_group"] = str(canonical_group)
        if validated:
            gn_mn_overrides[(gn, mn)] = validated

    # --- tier_defaults ---
    tier_defaults: dict[str, set[str]] = {}
    raw_td = data.get("tier_defaults") or {}
    for tier, slugs in raw_td.items():
        tier_defaults[str(tier)] = set(slugs) if slugs else set()

    if not tier_defaults:
        tier_defaults = _FALLBACK_TIER_DEFAULTS

    return fcttype_level_tiers, gn_mn_overrides, tier_defaults


# Module-level singletons — loaded once at import time.
FCTTYPE_LEVEL_TIERS, GN_MN_OVERRIDES, _TIER_DEFAULTS = _load_groups_config()

# ---------------------------------------------------------------------------
# Tier ordinal helpers
# ---------------------------------------------------------------------------

_TIER_ORDER: tuple[str, ...] = ("essential", "comfort", "advanced", "expert", "service")


def _tier_index(slug: str) -> int:
    try:
        return _TIER_ORDER.index(slug)
    except ValueError:
        return _TIER_ORDER.index("essential")


# ---------------------------------------------------------------------------
# Legacy aliases kept for backward compatibility
# ---------------------------------------------------------------------------

# fctType 9/10 boiler table — still referenced by some tests / diagnostics.
LEVEL_TIER_TABLE: dict[int, str] = FCTTYPE_LEVEL_TIERS.get(9, _FALLBACK_BOILER_LEVEL_TIERS)

# Per-tier allowed levels for fctType 9/10 only — deprecated; kept for callers
# that have not yet been migrated to the fct_type-aware API.
TIER_LEVEL_FILTER: dict[str, frozenset[int] | None] = {
    "essential": frozenset({155, 156}),
    "comfort": frozenset({155, 156, 157}),
    "advanced": frozenset({155, 156, 157}),
    "expert": None,
    "service": None,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_tier_defaults() -> dict[str, set[str]]:
    """Return the tier → default group-slug mapping from groups_config.yaml."""
    return _TIER_DEFAULTS


def allowed_levels_for_tier(
    tier: str,
    fct_type: int | None = None,
) -> frozenset[int] | None:
    """Return the set of ``levelId`` values allowed for *tier* and *fct_type*.

    Returns ``None`` (unrestricted) when:
    - tier is ``expert`` or ``service`` (always walk everything), or
    - *fct_type* is unknown (rely on per-datapoint ``writeProt`` heuristic).
    """
    if tier in ("expert", "service"):
        return None

    if fct_type is None:
        return None

    level_tiers = FCTTYPE_LEVEL_TIERS.get(fct_type)
    if level_tiers is None:
        return None

    target_idx = _tier_index(tier)
    return frozenset(
        lid for lid, min_tier in level_tiers.items() if _tier_index(min_tier) <= target_idx
    )


def uses_easy_lookup_discovery(tier: str) -> bool:
    """True when topology comes from GET /lookup/{subnet} instead of GET /nodes."""
    return tier in ("essential", "comfort", "advanced")


def experience_minimum_from_discovery(
    level_id: int,
    write_prot: bool,
    level_label: str | None,
    fct_type: int | None = None,
) -> str:
    """Derive ``experience_minimum`` for a datapoint seen only via discovery.

    Curated ``oids.yaml`` entries always win over this when both exist; this is
    used for discovery-only OIDs and for serialising discovery metadata.

    Lookup order:
    1. If ``level_label`` contains "service" → service.
    2. If the (fct_type, level_id) pair has an entry in FCTTYPE_LEVEL_TIERS → use it.
    3. Fallback: legacy LEVEL_TIER_TABLE (fctType 9/10 boiler levels 155–159).
    4. ASSUMPTION: if none of the above match, use ``writeProt`` signal —
       protected → essential (read-only), writable → comfort.

    Note: ``GN_MN_OVERRIDES`` are applied by the caller (discovery._walk_level)
    AFTER this function returns, so they are not consulted here.
    """
    if level_label and "service" in level_label.lower():
        return "service"

    if fct_type is not None:
        level_tiers = FCTTYPE_LEVEL_TIERS.get(fct_type)
        if level_tiers is not None and level_id in level_tiers:
            return level_tiers[level_id]

    if level_id in LEVEL_TIER_TABLE:
        return LEVEL_TIER_TABLE[level_id]

    return "essential" if write_prot else "comfort"
