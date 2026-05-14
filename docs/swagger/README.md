# Windhager REST API — Swagger 1.2 sources

This directory contains the canonical Swagger 1.2 API description files extracted from a
Windhager RC7030 controller. They are the **sole source of truth** for all REST endpoint
paths, HTTP methods, request/response schemas, and status codes used by this integration.

## Naming convention

```
<Service>_<Version>_<Resource>.json
```

Examples: `RestApiRC7030_1.0_datapoint.json`, `InfoWinHeartbeat_1.0_kesselwahl.json`

## Usage

These files are **read-only reference material**. Do not edit them by hand.

The integration implements only the endpoints documented here. If a path is not in these
files, it is not safe to assume it exists on the device.

To regenerate the human-readable reference documents from these sources:

```bash
make build-docs
# or directly:
docker compose run --rm test python scripts/build_docs.py
```

This produces:
- [`docs/integrator/rest-api.md`](../integrator/rest-api.md) — full endpoint reference
- [`docs/integrator/swagger-coverage.md`](../integrator/swagger-coverage.md) — coverage matrix

## Services covered

| Service | Version | Description |
|---|---|---|
| `RestApiRC7030` | 1.0 | Core LON datapoints, nodes, lookup, config, scan |
| `InfoWinHeartbeat` | 1.0 | Boiler selection (kesselwahl), heartbeat |
| `InfoWinFehlerlog` | 1.0 | Error log |
| `WsAdmin` | 1.0 | System time, LED, firmware update, user management |
| `DcmRC7030` | 1.0 | Device configuration module |
| `WsFUP7030` | 1.0 | Firmware update process |
| `DpRecorder` | 1.0 | Datapoint recorder |
