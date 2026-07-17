#!/usr/bin/env python3
"""List writable datapoints that remain read-only sensors."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OIDS = ROOT / "custom_components" / "windhager_unified" / "oids.yaml"


def _parse_bound(value):
    if value is None:
        return None
    raw = str(value).strip().strip("'\"")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _has_usable_range(dp: dict) -> bool:
    mn = _parse_bound(dp.get("min_value"))
    mx = _parse_bound(dp.get("max_value"))
    if mn is None or mx is None:
        return False
    if dp.get("unverified"):
        return False
    return not (mn == mx == 0.0)


def _is_datetime(dp: dict) -> bool:
    unit_id = dp.get("unit_id")
    legacy = str(dp.get("unit", "")).strip().lower()
    return unit_id in (20, 21) or legacy in ("date", "time")


def main() -> int:
    with OIDS.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    dps = data.get("datapoints", [])
    stuck = []
    for dp in dps:
        if dp.get("write_protected", True):
            continue
        if dp.get("entity_role") == "command":
            continue  # becomes a button
        if dp.get("unverified"):
            stuck.append((dp, "unverified"))
            continue
        if _is_datetime(dp):
            stuck.append((dp, "datetime"))
            continue
        has_enum = bool(dp.get("enum_values"))
        if has_enum:
            continue  # becomes a select
        if _has_usable_range(dp):
            # Could become a number or switch, but only if live format is confirmed.
            # Without confirmed format it stays a sensor.
            mn = _parse_bound(dp.get("min_value"))
            mx = _parse_bound(dp.get("max_value"))
            if mn == 0.0 and mx == 1.0:
                continue  # becomes a switch
            stuck.append((dp, "numeric config without confirmed live format"))
            continue
        stuck.append((dp, "no enum and no usable range"))

    print(f"Writable datapoints stuck as read-only sensors: {len(stuck)}")
    for dp, reason in stuck:
        name = dp.get("i18n", {}).get("en", "") or dp.get("key", "")
        print(f"  {dp['oid']} {dp['key']}: {name} ({reason})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
