# Entities

The integration creates entities across four HA platforms:

| Platform | Used for |
|---|---|
| `sensor` | Read-only values: temperatures, operating state, error log, heartbeat, VPN status, … |
| `switch` | On/off values backed by REST PUT endpoints (experience level `service`) |
| `button` | One-shot actions: error log reset, heartbeat start/stop, LED toggle (experience level `advanced`+) |
| `select` | Enumerated choices: timezone, NTP server (experience level `advanced`+) |

## Device grouping

Entities are grouped under HA devices. Each LON node discovered on the network
becomes a device (e.g. "LogWIN", "UMUMLZ", "WFBPK"). REST API service entities
are grouped under their service (e.g. "Windhager Heartbeat", "Windhager Fehlerlog").

## Entity states

- **LON sensors:** report `native_value` from the `value` field in the
  `/api/1.0/datapoint/{OID}` response, with unit and device class from
  `oids.yaml`.
- **REST sensors:** report a scalar extracted from the GET response (field
  `value`, `status`, `time`, or `text`, in that priority order).
- **Switches:** derive `is_on` from the coordinator data value; turn-on/off
  sends `PUT` with `on_value` / `off_value` from `restapi_endpoints.yaml`.
- **Buttons:** send the configured HTTP method (POST, PUT, DELETE) when pressed.
- **Selects:** report `current_option` from coordinator data; change sends `PUT`
  with the chosen option as query parameter `value`.

## Enabled by default

Entity visibility defaults are set from the **experience level** chosen during
setup:

| Experience level | Default-enabled entities |
|---|---|
| Essential | Essential-tagged sensors only |
| Comfort | Essential + Comfort sensors |
| Advanced | Essential + Comfort + Advanced sensors, plus read-only REST |
| Expert | All of the above + broad LON catalogue |
| Service | Everything, including write actions |

Entities that exist but are above your chosen tier are **registered as
disabled**. You can enable any entity manually from the HA Entities page.

## Unique IDs

Unique IDs are stable MD5 hashes of `host + OID/endpoint + key`. They survive
restarts and upgrades without losing history.

## Why is an entity missing?

See [Experience levels — why don't I see entity X?](experience-levels.md#why-dont-i-see-entity-x)
