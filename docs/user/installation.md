# Installation

## Requirements

- Home Assistant **2024.1.0** or newer (see `hacs.json`).
- Network access from your HA host to the Windhager RC7030 controller
  (LAN or WLAN, HTTP or HTTPS with self-signed certificate support).
- Windhager **Service** credentials or equivalent account with read access.

## Method 1 — HACS (recommended)

1. Open **HACS** in Home Assistant.
2. Go to **Integrations** → three-dot menu → **Custom repositories**.
3. Add `https://github.com/pinguts/ha-windhager-unified` as an **Integration** repository.
4. Search for **Windhager Unified** and click **Download**.
5. Restart Home Assistant.
6. Continue with [Setup](setup.md).

## Method 2 — Manual install

1. Download or clone the repository.
2. Copy the `custom_components/windhager_unified/` folder into your HA
   `config/custom_components/` directory.
3. Restart Home Assistant.
4. Continue with [Setup](setup.md).

## What gets installed

The integration installs the following files into Home Assistant:

```
custom_components/windhager_unified/
├── __init__.py           — entry setup / teardown
├── api_client.py         — HTTP client (Digest auth)
├── config_flow.py        — UI setup wizard
├── const.py              — shared constants
├── coordinator.py        — DataUpdateCoordinator (polling)
├── diagnostics.py        — HA diagnostics support
├── discovery.py          — LON network discovery
├── exceptions.py         — typed exceptions
├── labels.py             — label catalogue from bundled XML
├── manifest.json
├── oids.yaml             — curated LON datapoint catalogue
├── restapi_endpoints.yaml — REST endpoint catalogue
├── sensor.py / switch.py / button.py / select.py
├── services.yaml
├── translations/en.json
├── translations/de.json
└── labels/               — bundled XML label files from device
```
