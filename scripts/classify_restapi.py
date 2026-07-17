#!/usr/bin/env python3
"""Programmatically classify RestAPI endpoints in restapi_endpoints.yaml."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "custom_components" / "windhager_unified" / "restapi_endpoints.yaml"

# Per-endpoint key annotations: (data_role, temporal_semantics, model_role, history_importance, icon)
ANNOTATIONS: dict[str, tuple[str, str, str, str, str | None]] = {
    "heartbeat.status": ("diagnostic", "snapshot", "context", "low", "mdi:heart-pulse"),
    "heartbeat.start": ("command", "event", "control", "low", "mdi:play-circle"),
    "heartbeat.stop": ("command", "event", "control", "low", "mdi:stop-circle"),
    "fehlerlog.list": ("diagnostic", "snapshot", "event", "critical", "mdi:alert-box"),
    "fehlerlog.reset": ("command", "event", "control", "low", "mdi:playlist-remove"),
    "system.lookup": ("diagnostic", "snapshot", "context", "low", "mdi:lan"),
    "vpn.status": ("diagnostic", "snapshot", "context", "low", "mdi:vpn"),
    "dynip.check": ("diagnostic", "snapshot", "context", "low", "mdi:ip-network"),
    "systemtime.current": ("diagnostic", "snapshot", "context", "low", "mdi:clock-outline"),
    "systemtime.ntp_servers": ("configuration", "step", "context", "low", "mdi:server-network"),
    "systemtime.ntp_selected": ("configuration", "step", "context", "low", "mdi:server-network"),
    "systemtime.timezone": ("configuration", "step", "context", "low", "mdi:map-clock"),
    "admin.led_status": ("diagnostic", "snapshot", "context", "low", "mdi:led-on"),
    "admin.settings": ("diagnostic", "snapshot", "context", "low", "mdi:cog"),
    "kesselwahl.selected": ("configuration", "step", "context", "standard", "mdi:boiler"),
    "kesselwahl.list": ("diagnostic", "snapshot", "context", "low", "mdi:boiler"),
}


def main() -> int:
    with YAML_PATH.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    assert isinstance(data, dict) and "restapi_endpoints" in data, "invalid restapi_endpoints.yaml"

    changed = 0
    for group, endpoints in data["restapi_endpoints"].items():
        for ep in endpoints:
            key = ep.get("key")
            if key not in ANNOTATIONS:
                continue
            role, temporal, model, history, icon = ANNOTATIONS[key]
            ep["data_role"] = role
            ep["temporal_semantics"] = temporal
            ep["model_role"] = model
            ep["history_importance"] = history
            if icon and "icon" not in ep:
                ep["icon"] = icon
            changed += 1

    with YAML_PATH.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(
            data,
            fh,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    print(f"Updated {changed} endpoints in {YAML_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
