#!/usr/bin/env python3
"""Generate docs/integrator/rest-api.md and docs/integrator/swagger-coverage.md
from the Swagger 1.2 source files in docs/swagger/.

Run inside the devcontainer / Docker test image:

    python scripts/build_docs.py

Output files are written relative to the repository root.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SWAGGER_DIR = REPO_ROOT / "docs" / "swagger"
OUT_DIR = REPO_ROOT / "docs" / "integrator"

INTEGRATION_SERVICES = {"RestApiRC7030", "InfoWinHeartbeat", "WsAdmin"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_resource_files() -> list[dict]:
    """Return all resource files (those that have `apis` + `basePath` + operations)."""
    result = []
    for path in sorted(SWAGGER_DIR.glob("*.json")):
        with path.open() as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                print(f"  SKIP {path.name}: {exc}", file=sys.stderr)
                continue
        # api-docs files list sub-resources but carry no operations
        if "resourcePath" not in data:
            continue
        # Must have at least one operation
        has_ops = any(
            op
            for api in data.get("apis", [])
            for op in api.get("operations", [])
        )
        if not has_ops:
            continue
        data["_source_file"] = path.name
        result.append(data)
    return result


def _service_name(source_file: str) -> str:
    """Extract the service name from a filename like RestApiRC7030_1.0_nodes.json."""
    return source_file.split("_")[0]


def _service_version(source_file: str) -> str:
    parts = source_file.split("_")
    return parts[1] if len(parts) > 1 else "?"


def _used_by_integration(service: str) -> bool:
    return service in INTEGRATION_SERVICES


def _type_str(prop: dict) -> str:
    if "$ref" in prop:
        return f"`{prop['$ref']}`"
    t = prop.get("type", "?")
    if t == "array":
        items = prop.get("items", {})
        inner = items.get("$ref") or items.get("type") or "?"
        return f"array[`{inner}`]"
    return t


def _parameters_table(parameters: list[dict]) -> str:
    if not parameters:
        return ""
    lines = ["| Name | In | Type | Required | Description |",
             "| ---- | -- | ---- | -------- | ----------- |"]
    for p in parameters:
        name = p.get("name", "")
        location = p.get("paramType", p.get("in", ""))
        ptype = _type_str(p)
        required = "yes" if p.get("required") else "no"
        desc = p.get("description", "").replace("\n", " ")
        lines.append(f"| `{name}` | {location} | {ptype} | {required} | {desc} |")
    return "\n".join(lines)


def _models_section(models: dict) -> str:
    if not models:
        return ""
    lines = ["### Models\n"]
    for model_id, model in sorted(models.items()):
        lines.append(f"#### `{model_id}`\n")
        desc = model.get("description", "")
        if desc:
            lines.append(f"{desc}\n")
        props = model.get("properties", {})
        if props:
            lines.append("| Property | Type | Description |")
            lines.append("| -------- | ---- | ----------- |")
            for pname, pdef in sorted(props.items()):
                ptype = _type_str(pdef)
                pdesc = pdef.get("description", pdef.get("descripton", "")).replace("\n", " ")
                lines.append(f"| `{pname}` | {ptype} | {pdesc} |")
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# rest-api.md
# ---------------------------------------------------------------------------


def build_rest_api_md(resources: list[dict]) -> str:
    lines: list[str] = [
        "# Windhager REST API Reference",
        "",
        "Generated from Swagger 1.2 source files in `docs/swagger/`.",
        "Do not edit by hand — run `python scripts/build_docs.py` to regenerate.",
        "",
    ]

    # Group by service
    services: dict[str, list[dict]] = {}
    for r in resources:
        svc = _service_name(r["_source_file"])
        services.setdefault(svc, []).append(r)

    for svc_name in sorted(services):
        resources_for_svc = services[svc_name]
        used = _used_by_integration(svc_name)
        badge = " *(used by integration)*" if used else ""
        ver = _service_version(resources_for_svc[0]["_source_file"])
        lines += [
            f"## {svc_name} v{ver}{badge}",
            "",
        ]

        for resource in sorted(resources_for_svc, key=lambda r: r.get("resourcePath", "")):
            base = resource.get("basePath", "")
            resource_path = resource.get("resourcePath", "")
            models = resource.get("models", {})

            for api in resource.get("apis", []):
                path = api.get("path", "")
                full_url = base + path
                for op in api.get("operations", []):
                    method = op.get("method", "GET")
                    summary = op.get("summary", "")
                    notes = op.get("notes", "")
                    nickname = op.get("nickname", "")
                    ret_type = op.get("type", "")
                    ret_items = op.get("items", {})
                    if ret_type == "array" and ret_items:
                        inner = ret_items.get("$ref") or ret_items.get("type") or "?"
                        ret_type = f"array[`{inner}`]"

                    lines += [
                        f"### `{method} {full_url}`",
                        "",
                    ]
                    if summary:
                        lines.append(f"**{summary}**")
                        lines.append("")
                    if notes:
                        lines.append(notes)
                        lines.append("")
                    if nickname:
                        lines.append(f"*Nickname:* `{nickname}`  ")
                    if ret_type:
                        lines.append(f"*Returns:* {ret_type}")
                    lines.append("")

                    params = op.get("parameters", [])
                    if params:
                        lines.append(_parameters_table(params))
                        lines.append("")

            if models:
                lines.append(_models_section(models))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# swagger-coverage.md
# ---------------------------------------------------------------------------


def build_swagger_coverage_md(resources: list[dict]) -> str:
    lines: list[str] = [
        "# Swagger Coverage Report",
        "",
        "Generated from Swagger 1.2 source files in `docs/swagger/`.",
        "Do not edit by hand — run `python scripts/build_docs.py` to regenerate.",
        "",
        "## Summary",
        "",
        "| Service | Version | Resource | Method | Path | Used by Integration |",
        "| ------- | ------- | -------- | ------ | ---- | ------------------- |",
    ]

    total = 0
    covered = 0

    for resource in resources:
        svc = _service_name(resource["_source_file"])
        ver = _service_version(resource["_source_file"])
        base = resource.get("basePath", "")
        used = "yes" if _used_by_integration(svc) else "no"

        for api in resource.get("apis", []):
            path = api.get("path", "")
            full_url = base + path
            for op in api.get("operations", []):
                method = op.get("method", "GET")
                total += 1
                if _used_by_integration(svc):
                    covered += 1
                resource_path = resource.get("resourcePath", "")
                lines.append(
                    f"| {svc} | {ver} | {resource_path} | `{method}` | `{full_url}` | {used} |"
                )

    lines += [
        "",
        "## Totals",
        "",
        f"- Total documented endpoints: **{total}**",
        f"- Endpoints in services used by this integration: **{covered}**",
        f"- Services not used by this integration: see rows with `no` above",
        "",
        "## Services used by the integration",
        "",
        "| Service | Notes |",
        "| ------- | ----- |",
        "| `RestApiRC7030` | LON datapoints, nodes, lookup, config, scan |",
        "| `InfoWinHeartbeat` | Boiler selection (kesselwahl), heartbeat |",
        "| `WsAdmin` | System time, LED, firmware update, user management |",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading Swagger resource files from {SWAGGER_DIR} ...")
    resources = _load_resource_files()
    print(f"  Found {len(resources)} resource files with operations.")

    rest_api_path = OUT_DIR / "rest-api.md"
    print(f"Writing {rest_api_path} ...")
    rest_api_path.write_text(build_rest_api_md(resources), encoding="utf-8")

    coverage_path = OUT_DIR / "swagger-coverage.md"
    print(f"Writing {coverage_path} ...")
    coverage_path.write_text(build_swagger_coverage_md(resources), encoding="utf-8")

    print("Done.")


if __name__ == "__main__":
    main()
