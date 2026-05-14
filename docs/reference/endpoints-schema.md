# REST endpoint catalogue schema (`restapi_endpoints.yaml`)

`custom_components/windhager_unified/restapi_endpoints.yaml` is the curated list of
REST API endpoints exposed as HA entities. It is loaded at startup by the
coordinator.

## Top-level structure

```yaml
restapi_endpoints:
  <group_name>:
    - <EndpointEntry>
    - ...
```

The group name (e.g. `heartbeat`, `fehlerlog`, `system`) is used to organise
entities under HA devices.

## `EndpointEntry` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `endpoint` | string | **yes** | Full path from `basePath + path` (no extra segment). E.g. `/InfoWinHeartbeat/api/1.0/heartbeat` |
| `key` | string | **yes** | Stable dot-separated identifier (used as coordinator data key and `translation_key`) |
| `entity_type` | string | **yes** | `sensor` \| `button` \| `select` \| `switch` |
| `name` | string | **yes** | English display name (fallback if translation missing) |
| `i18n` | map | **yes** | `{de: "...", en: "..."}` |
| `http_method` | string | no | HTTP method for actuators (`POST`, `PUT`, `DELETE`). Default: `POST` for button, `PUT` for select/switch |
| `device_class` | string | no | HA device class slug for sensors |
| `state_class` | string | no | HA state class slug for sensors |
| `on_value` | string | no | Value to send for switch turn-on (default: `on`) |
| `off_value` | string | no | Value to send for switch turn-off (default: `off`) |
| `options` | list | no | Allowed option values for `select` entities |
| `group` | string | no | Functional group id (same taxonomy as `oids.yaml`). Used for group-filtering. |
| `experience_minimum` | string | no | Minimum experience level: `essential` \| `comfort` \| `advanced` \| `expert` \| `service`. |

## `experience_minimum` ordering rule

Same ordering as for LON datapoints:

```
essential < comfort < advanced < expert < service
```

Absent field defaults to `advanced` for read-only sensors and `service` for
actuators (buttons, switches, selects with write operations).

## Example entry

```yaml
restapi_endpoints:
  fehlerlog:
    - endpoint: "/InfoWinFehlerlog/api/1.0/fehlerlog"
      key: "fehlerlog.list"
      entity_type: sensor
      name: "Error Log"
      i18n:
        de: "Fehlerprotokoll"
        en: "Error Log"
      device_class: null
      state_class: null
      group: "fehlerlog"
      experience_minimum: advanced

    - endpoint: "/InfoWinFehlerlog/api/1.0/fehlerlog/reset/0"
      key: "fehlerlog.reset"
      entity_type: button
      http_method: PUT
      name: "Reset Error Log"
      i18n:
        de: "Fehlerprotokoll zurücksetzen"
        en: "Reset Error Log"
      group: "fehlerlog"
      experience_minimum: service
```
