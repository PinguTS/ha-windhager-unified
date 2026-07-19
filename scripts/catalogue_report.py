#!/usr/bin/env python3
"""Generate catalogue classification report."""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OIDS = ROOT / "custom_components" / "windhager_unified" / "oids.yaml"


def main() -> int:
    with OIDS.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    dps = data.get("datapoints", [])
    classified = [dp for dp in dps if dp.get("data_role")]
    unknown = [dp for dp in dps if not dp.get("data_role")]
    writable_readonly = [
        dp
        for dp in dps
        if dp.get("write_protected") is False and dp.get("data_role") in ("measurement", "unknown")
    ]

    print(f"Total: {len(dps)}  classified: {len(classified)}  unknown: {len(unknown)}")
    print("\nClassified model-relevant datapoints:")
    for dp in classified:
        role = dp.get("data_role")
        temporal = dp.get("temporal_semantics")
        model = dp.get("model_role")
        history = dp.get("history_importance")
        name = dp.get("i18n", {}).get("en", "") or dp.get("key", "")
        print(f"  {dp['oid']} {dp['key']}: {name} -> {role}/{temporal}/{model}/{history}")

    print("\nUncertain datapoints (remain unknown):")
    for dp in unknown:
        name = dp.get("i18n", {}).get("en", "") or dp.get("key", "")
        print(f"  {dp['oid']} {dp['key']}: {name}")

    print("\nWritable values currently not exposed through a writable platform (still sensors):")
    for dp in writable_readonly:
        name = dp.get("i18n", {}).get("en", "") or dp.get("key", "")
        print(f"  {dp['oid']} {dp['key']}: {name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
