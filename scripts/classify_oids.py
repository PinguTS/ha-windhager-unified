#!/usr/bin/env python3
"""Programmatically classify model-relevant OIDs in oids.yaml.

This is a one-off catalogue-maintenance script, not part of the integration.
It edits the YAML in place, preserving order and formatting.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "custom_components" / "windhager_unified" / "oids.yaml"

# Semantic annotations keyed by OID. A tuple orders the new keys after existing ones.
# (data_role, temporal_semantics, model_role, history_importance, optional extra dict)
ANNOTATIONS: dict[str, tuple[str, str, str, str, dict | None]] = {
    # Measurements: temperatures
    "1/15/0/0/0/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:thermometer"}),
    "1/15/1/0/0/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:thermometer"}),
    "1/15/0/3/23/0": ("measurement", "sampled", "feature", "critical", None),
    "1/15/1/3/23/0": ("measurement", "sampled", "feature", "critical", None),
    "1/15/0/4/13/0": ("measurement", "sampled", "feature", "critical", None),
    "1/15/1/4/13/0": ("measurement", "sampled", "feature", "critical", None),
    "1/15/0/0/15/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/15/0/0/16/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/15/0/0/17/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/15/1/0/15/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/15/1/0/16/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/15/1/0/17/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/16/0/0/15/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/16/0/0/16/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/16/0/0/17/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/16/1/0/15/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/16/1/0/16/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/16/1/0/17/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/65/0/0/15/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/65/0/0/16/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/65/0/0/17/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:storage-tank"}),
    "1/16/0/0/7/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:fire"}),
    "1/16/1/0/7/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:fire"}),
    "1/65/0/0/7/0": ("measurement", "sampled", "feature", "critical", {"icon": "mdi:fire"}),
    "1/16/0/0/8/0": ("measurement", "sampled", "feature", "critical", None),
    "1/16/1/0/8/0": ("measurement", "sampled", "feature", "critical", None),
    "1/65/0/0/11/0": ("measurement", "sampled", "feature", "critical", None),
    "1/65/0/0/45/0": ("measurement", "sampled", "feature", "critical", None),
    # 1/15/0/3/13/0 Flow is writable -> setpoint (flow temperature target)
    "1/15/0/3/13/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:water-boiler"}),
    "1/15/1/3/13/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:water-boiler"}),
    # Setpoints
    "1/15/0/1/1/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:thermostat"}),
    "1/15/0/1/2/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:thermostat"}),
    "1/15/1/1/1/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:thermostat"}),
    "1/15/1/1/2/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:thermostat"}),
    "1/16/0/20/17/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:thermostat"}),
    "1/16/1/1/15/0": ("setpoint", "step", "control", "critical", {"icon": "mdi:thermostat"}),
    "1/16/0/1/8/0": ("setpoint", "step", "control", "critical", None),
    "1/16/1/1/8/0": ("setpoint", "step", "control", "critical", None),
    "1/15/0/4/13/0": ("setpoint", "step", "control", "critical", None),
    "1/15/1/4/13/0": ("setpoint", "step", "control", "critical", None),
    # Configuration: heating curve
    "1/15/0/3/1/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/15/1/3/1/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/15/0/3/12/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/15/1/3/12/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/15/0/7/2/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/15/0/7/8/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/15/1/7/2/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/15/1/7/8/0": ("configuration", "step", "context", "critical", {"icon": "mdi:chart-bell-curve"}),
    "1/65/0/12/40/0": ("configuration", "step", "context", "critical", {"icon": "mdi:fire"}),
    # Operating states
    "1/65/0/2/1/0": ("operating_state", "event", "event", "critical", {"icon": "mdi:state-machine"}),
    "1/60/0/2/1/0": ("operating_state", "event", "event", "critical", {"icon": "mdi:state-machine"}),
    "1/15/0/3/50/0": ("operating_state", "event", "event", "critical", {"icon": "mdi:calendar-week"}),
    "1/15/1/3/50/0": ("operating_state", "event", "event", "critical", {"icon": "mdi:calendar-week"}),
    "1/16/1/1/100/0": ("operating_state", "event", "event", "critical", {"icon": "mdi:flare"}),
    # Actuator states
    "1/15/0/1/20/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:pump"}),
    "1/15/1/1/20/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:pump"}),
    "1/15/0/1/66/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:pump"}),
    "1/15/1/1/66/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:pump"}),
    "1/16/1/1/22/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:pump"}),
    "1/15/0/1/21/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:valve"}),
    "1/15/1/1/21/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:valve"}),
    "1/16/0/1/102/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:valve"}),
    "1/16/1/1/102/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:valve"}),
    "1/16/0/22/50/0": ("actuator_state", "event", "event", "critical", {"icon": "mdi:pump"}),
    # Counters
    "1/65/0/2/81/0": ("counter", "counter", "feature", "critical", {"icon": "mdi:counter"}),
    "1/60/0/2/80/0": ("counter", "counter", "feature", "standard", {"icon": "mdi:counter"}),
    # Diagnostic alarms
    "1/65/0/2/0/0": ("diagnostic", "event", "event", "critical", {"icon": "mdi:alert"}),
    "1/60/0/2/0/0": ("diagnostic", "event", "event", "critical", {"icon": "mdi:alert"}),
}

# OIDs where state_class: measurement should be removed because the value is a
# setpoint, configuration, or actuator state. The parser would also drop these
# on enum/timestamp/actuator entities, but explicit YAML correctness is clearer.
REMOVE_STATE_CLASS: set[str] = {
    "1/15/0/1/1/0",
    "1/15/0/1/2/0",
    "1/15/1/1/1/0",
    "1/15/1/1/2/0",
    "1/16/0/20/17/0",
    "1/16/1/1/15/0",
    "1/16/0/1/8/0",
    "1/16/1/1/8/0",
    "1/15/0/4/13/0",
    "1/15/1/4/13/0",
    "1/15/0/3/1/0",
    "1/15/1/3/1/0",
    "1/15/0/3/12/0",
    "1/15/1/3/12/0",
    "1/15/0/7/2/0",
    "1/15/0/7/8/0",
    "1/15/1/7/2/0",
    "1/15/1/7/8/0",
    "1/65/0/12/40/0",
    "1/65/0/2/1/0",
    "1/60/0/2/1/0",
    "1/15/0/3/50/0",
    "1/15/1/3/50/0",
    "1/16/1/1/100/0",
    "1/16/0/22/50/0",
    "1/16/1/1/22/0",
    "1/15/0/1/21/0",
    "1/15/1/1/21/0",
    "1/15/0/1/20/0",
    "1/15/1/1/20/0",
    "1/15/0/1/66/0",
    "1/15/1/1/66/0",
    "1/16/0/1/102/0",
    "1/16/1/1/102/0",
    "1/65/0/2/0/0",
    "1/60/0/2/0/0",
}

# Suggested display precision for temperature entries that have a unit and no
# precision set yet. We leave non-temperature values alone.
PRECISION_1C_OIDS: set[str] = {
    "1/15/0/0/0/0",
    "1/15/1/0/0/0",
    "1/15/0/4/13/0",
    "1/15/1/4/13/0",
    "1/15/0/0/15/0",
    "1/15/0/0/16/0",
    "1/15/0/0/17/0",
    "1/15/1/0/15/0",
    "1/15/1/0/16/0",
    "1/15/1/0/17/0",
    "1/16/0/0/15/0",
    "1/16/0/0/16/0",
    "1/16/0/0/17/0",
    "1/16/1/0/15/0",
    "1/16/1/0/16/0",
    "1/16/1/0/17/0",
    "1/65/0/0/15/0",
    "1/65/0/0/16/0",
    "1/65/0/0/17/0",
    "1/16/0/0/7/0",
    "1/16/1/0/7/0",
    "1/65/0/0/7/0",
    "1/16/0/0/8/0",
    "1/16/1/0/8/0",
    "1/65/0/0/11/0",
    "1/65/0/0/45/0",
    "1/15/0/3/13/0",
    "1/15/1/3/13/0",
    "1/15/0/1/1/0",
    "1/15/0/1/2/0",
    "1/15/1/1/1/0",
    "1/15/1/1/2/0",
    "1/16/0/20/17/0",
    "1/16/1/1/15/0",
    "1/16/0/1/8/0",
    "1/16/1/1/8/0",
    "1/15/0/3/1/0",
    "1/15/1/3/1/0",
    "1/15/0/3/12/0",
    "1/15/1/3/12/0",
    "1/15/0/7/2/0",
    "1/15/0/7/8/0",
    "1/15/1/7/2/0",
    "1/15/1/7/8/0",
    "1/65/0/12/40/0",
}


def _ordered_insert(dp: dict, key: str, value) -> None:
    """Insert key after existing keys while preserving YAML file order."""
    if key in dp:
        dp[key] = value
        return
    dp[key] = value


def main() -> int:
    with YAML_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, dict) and "datapoints" in data, "invalid oids.yaml"

    changed = 0
    for dp in data["datapoints"]:
        oid = dp.get("oid")
        if not oid:
            continue

        # Unverified entries are kept as unknown; do not guess semantics.
        if dp.get("unverified"):
            continue

        if oid in REMOVE_STATE_CLASS and dp.get("state_class") is not None:
            dp["state_class"] = None
            changed += 1

        if oid in PRECISION_1C_OIDS and dp.get("unit") == "°C" and "suggested_display_precision" not in dp:
            dp["suggested_display_precision"] = 1
            changed += 1

        if oid not in ANNOTATIONS:
            continue

        data_role, temporal, model, history, extras = ANNOTATIONS[oid]
        _ordered_insert(dp, "data_role", data_role)
        _ordered_insert(dp, "temporal_semantics", temporal)
        _ordered_insert(dp, "model_role", model)
        _ordered_insert(dp, "history_importance", history)
        if extras:
            for k, v in extras.items():
                if k not in dp:
                    dp[k] = v
                    changed += 1
        changed += 1

    data["meta"]["version"] = 7

    with YAML_PATH.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            data,
            fh,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    print(f"Updated {changed} entries in {YAML_PATH}; version {data['meta']['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
