# 🔥 Windhager Unified

> Home Assistant integration for Windhager biomass heating systems

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![GitHub release](https://img.shields.io/github/v/release/pinguts/ha-windhager-unified)](https://github.com/pinguts/ha-windhager-unified/releases)
[![CI](https://github.com/pinguts/ha-windhager-unified/actions/workflows/ci.yml/badge.svg)](https://github.com/pinguts/ha-windhager-unified/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![HA min version](https://img.shields.io/badge/Home%20Assistant-%3E%3D%202024.1-brightgreen)](https://www.home-assistant.io/)

Windhager Unified is a comprehensive Home Assistant integration designed for the entire range of Windhager biomass heating systems using the RC7030 controller generation. 

By utilizing a generic, discovery-based approach, it automatically maps your specific network topology to Home Assistant entities. This ensures compatibility across different models and configurations without manual OID mapping.

---

## Features

*   **Automatic LON discovery** — Reads the live network topology from the device; no manual configuration of data points needed.
*   **Experience levels** — Tailor the entity count from *Essential* (basic temperatures and state) to *Service* (full data points and write actions).
*   **Multi-language labels** — Entity names automatically follow the labels defined in the device (supports German, English, French, and Italian).
*   **Functional group filtering** — Enable only the groups relevant to your installation (boiler, heating circuits, DHW, solar, etc.).
*   **Diagnostics** — Built-in support for HA diagnostics with automatic redaction of sensitive information like credentials and hostnames.
*   **Local polling** — Communicates directly with the device via the built-in REST API; no cloud dependency.

---

## Supported devices

This integration is designed for the **RC7030 web server** platform. While other integrations might focus specifically on the BioWIN series, **Windhager Unified** provides a universal approach for all devices on this platform.

**Confirmed working:**
*   **Windhager LogWIN** (with RC7030 controller)

**Expected to work:**
*   **BioWIN2** / **BioWIN2 Touch**
*   **PuroWIN**
*   **DuoWIN**
*   **VarioWIN**
*   **FireWIN**

Feedback from users with these devices is highly welcome to expand the confirmed compatibility list.

---

## Installation

### HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Click **Integrations** → three-dot menu → **Custom repositories**.
3. Add `[https://github.com/pinguts/ha-windhager-unified](https://github.com/pinguts/ha-windhager-unified)` with category **Integration**.
4. Search for **Windhager Unified** in the HACS store and click **Download**.
5. Restart Home Assistant.

### Manual

1. Copy the `custom_components/windhager_unified/` folder into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Windhager Unified**.
3. Enter the device host (IP or hostname), credentials, and select your preferred experience level and functional groups.

For a detailed walkthrough, see [docs/user/setup.md](docs/user/setup.md).

### Experience levels and discovery API

The experience level controls both how much data is visible and which API path is used during initial setup:

| Level | API used at setup | Level filter | Typical use |
|---|---|---|---|
| **Essential** | `GET /api/1.0/lookup/{subnet}` | Temperature-reading levels only | Key sensors, boiler status |
| **Comfort** | `GET /api/1.0/lookup/{subnet}` | Readings + user time-program levels | User-adjustable settings |
| **Advanced** | `GET /api/1.0/lookup/{subnet}` | Readings + user + module levels | All non-service parameters |
| **Expert** | LON scan* + `GET /api/1.0/nodes` | All levels | Full node topology + all datapoints |
| **Service** | LON scan* + `GET /api/1.0/nodes` | All levels | All datapoints including service parameters |

\* The LON scan (`PUT /api/1.0/scan/nodes/*` state machine) is triggered once at setup for Expert/Service tiers to ensure the node list reflects the current live LON network. It adds approximately 10–60 seconds to the initial setup step. On timeout or error it falls back to the cached node list and logs a warning.

---

## Documentation

Full documentation is available in the `docs/` folder:

| Document | Contents |
|---|---|
| [Setup Guide](docs/user/setup.md) | Detailed installation and configuration |
| [Troubleshooting](docs/user/troubleshooting.md) | Common problems and debug logging |
| [Architecture](docs/integrator/architecture.md) | Code architecture and design decisions |
| [REST API Reference](docs/integrator/rest-api.md) | Technical reference for the RC7030 API |

---

## Development & Contributing

All checks and tests run inside Docker to ensure consistency.

```bash
make build          # Build the test image
make check          # Run linting, type checking, and tests
make format         # Auto-format the codebase
make build-docs     # Regenerate API reference documentation
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on PR expectations and testing conventions.

---

## Security

**Do not open public issues for security vulnerabilities.** Please use [GitHub private vulnerability reporting](https://github.com/pinguts/ha-windhager-unified/security/advisories/new) instead.

---

## Disclaimer

This project is a community-maintained integration and is **not** affiliated with, endorsed by, or supported by any of the following entities:
*   **Windhager Zentralheizung GmbH**
*   **BWT Holding GmbH** (BWT Windhager)
*   **Best Heating Technology GmbH**

All product names, trademarks, and registered trademarks are property of their respective owners. Use this integration at your own risk. The developers are not responsible for any damage or unintended behavior of your heating system.

---
Copyright (c) 2026 Thilo Schumann. Released under the [MIT License](LICENSE).