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
| `device_class` | string | no | HA sensor device class slug. Use `null` for none. |
| `state_class` | string \| null | no | HA sensor state class slug: `measurement`, `total`, `total_increasing`, `measurement_angle`, or `null`. |
| `unit` | string | no | Physical unit for sensor entities. |
| `suggested_display_precision` | int | no | Number of decimal places shown in the UI. |
| `icon` | string | no | Material Design Icon slug, e.g. `mdi:thermometer`. |
| `entity_category` | string | no | `diagnostic` or `config`. |
| `enabled_by_default` | bool | no | Explicitly enable or disable the entity at registration. Overrides the experience-tier fallback. |
| `data_role` | string | no | Domain semantic role: `measurement`, `setpoint`, `configuration`, `operating_state`, `actuator_state`, `command`, `counter`, `forecast`, `derived`, `diagnostic`, `unknown`. Default: `unknown`. |
| `temporal_semantics` | string | no | Temporal behaviour: `sampled`, `step`, `event`, `counter`, `snapshot`, `none`. Default: `none`. |
| `model_role` | string | no | Model relevance: `feature`, `target`, `context`, `event`, `control`, `ignore`, `unknown`. Default: `unknown`. |
| `history_importance` | string | no | History recommendation: `critical`, `standard`, `low`, `none`. Default: `standard`. |

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
      data_role: command
      temporal_semantics: event
      model_role: control
      history_importance: low
      icon: mdi:playlist-remove
```

## Semantic metadata example

```yaml
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
      data_role: diagnostic
      temporal_semantics: snapshot
      model_role: event
      history_importance: critical
      icon: mdi:alert-box
```

## Recorder history and long-term statistics

- `state_class` only enables Home Assistant long-term statistics (LTS) for eligible sensor entities. LTS stores aggregated minimum, maximum, and mean values.
- LTS is **not** a replacement for exact event history or configuration-change sequences. Operating phases, pump states, setpoints, and configuration values remain historically critical even when `state_class` is `null`.
- Ordinary state history is recorded by the Home Assistant Recorder when the entity is included in Recorder configuration. Detailed history is subject to the user's global `purge_keep_days` setting.
- `history_importance` is a recommendation for future export or archive tools, not a guarantee that Home Assistant retains the data permanently.
- Static metadata attributes (`windhager_data_role`, `windhager_temporal_semantics`, `windhager_model_role`, `windhager_history_importance`, `windhager_oid`, `windhager_write_protected`) are excluded from Recorder attribute storage. The primary entity state remains fully recorded.
- Metadata changes require an integration reload or Home Assistant restart. Long-term statistics are not created retroactively.
