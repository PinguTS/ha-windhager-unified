#!/usr/bin/env python3
"""Annotate oids.yaml with entity_role and device_info_field."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OIDS = ROOT / "custom_components" / "windhager_unified" / "oids.yaml"

COMMAND_LABELS = {
    "freigabe starten",
    "enable",
    "autorisation démarrage",
    "avviamento",
}


def _text(dp: dict) -> str:
    i18n = dp.get("i18n") or {}
    return " ".join(str(i18n.get(l, "")).lower() for l in ("en", "de", "fr", "it"))


def _identity_field(text: str) -> str | None:
    if "software version" in text or "softwareversion" in text:
        return "sw_version"
    if "hardware version" in text or "version hw" in text:
        return "hw_version"
    if "kesseltyp" in text or "kesseltype" in text or "boiler type" in text:
        return "model"
    if "serial" in text or "seriennummer" in text:
        return "serial_number"
    return None


def main() -> None:
    data = yaml.safe_load(OIDS.read_text(encoding="utf-8"))
    dps = data["datapoints"]
    stats = {"diagnostic": 0, "command": 0, "config": 0}

    for dp in dps:
        text = _text(dp)
        ident = _identity_field(text)
        if ident:
            dp["entity_role"] = "diagnostic"
            dp["device_info_field"] = ident
            stats["diagnostic"] += 1
            continue

        if dp.get("entity_role") == "command":
            stats["command"] += 1
            continue

        en = str((dp.get("i18n") or {}).get("en", "")).lower()
        de = str((dp.get("i18n") or {}).get("de", "")).lower()
        if en in COMMAND_LABELS or de in COMMAND_LABELS:
            dp["entity_role"] = "command"
            dp.setdefault("command_value", "1")
            stats["command"] += 1
            continue

        if dp.get("write_protected") is False and not dp.get("unverified"):
            # Explicit config role for verified writable entries (derivation also handles this).
            if dp.get("entity_role") not in ("measurement", "diagnostic", "command"):
                dp["entity_role"] = "config"
                stats["config"] += 1

    meta = data.setdefault("meta", {})
    meta["version"] = int(meta.get("version", 5)) + 1

    OIDS.write_text(yaml.dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print("Updated", OIDS)
    print("Stats:", stats)


if __name__ == "__main__":
    main()
