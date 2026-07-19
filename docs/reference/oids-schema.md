# OID catalogue schema (`oids.yaml`)

`custom_components/windhager_unified/oids.yaml` is the curated list of LON datapoints
the integration knows about. It is loaded at startup by the coordinator.

## Top-level structure

```yaml
meta:
  version: <int>        # catalogue format version
  description: <str>    # human-readable description of the catalogue
  datapoint_count: <int>

datapoints:
  - <DatapointEntry>
  - ...
```

## `DatapointEntry` fields

| Field | Type | Required | Description |
|---|---|---|---|
| `oid` | string | **yes** | OID in `subnetId/nodeId/fctId/groupId/memberId/varInst` format (6 slash-separated integers) |
| `key` | string | **yes** | Stable dot-separated identifier used as the coordinator data key and HA `translation_key` |
| `i18n` | map | **yes** | Human-readable names per language: `de`, `en`, `fr`, `it` |
| `api_name` | string | no | Raw name from the Windhager API (`GG-MMM` format) |
| `hint_node` | string | no | Short device hint (e.g. `LogWIN`, `UMUMLZ`) for HA model field |
| `type_id` | int | no | LON type code from the API |
| `subtype_id` | int | no | LON subtype code |
| `unit_id` | int | no | Numeric unit code from the API |
| `write_protected` | bool | no | `true` if the device rejects writes to this OID |
| `unit` | string | no | Physical unit (e.g. `°C`, `%`, `kW`) |
| `min_value` | string | no | Minimum value from API metadata (stringified float) |
| `max_value` | string | no | Maximum value from API metadata |
| `step` | string | no | Resolution / step size |
| `device_class` | string | no | HA sensor device class slug (e.g. `temperature`, `power`, `enum`, `timestamp`). |
| `state_class` | string \| null | no | HA sensor state class slug: `measurement`, `total`, `total_increasing`, `measurement_angle`, or `null`. |
| `unit` | string | no | Physical unit (e.g. `°C`, `%`, `kW`, `h`). |
| `suggested_display_precision` | int | no | Number of decimal places shown in the UI. |
| `icon` | string | no | Material Design Icon slug, e.g. `mdi:thermometer`. |
| `entity_category` | string | no | `diagnostic` or `config`. Overrides the scope-derived category when present. |
| `parameter_scope` | string | no | Explicit parameter classification: `user` (day-to-day controls), `config` (true configuration parameters), or `installer` (system-type/installer settings). Overrides the derivation from `data_role`. |
| `enabled_by_default` | bool | no | Explicitly enable or disable the entity at registration. Overrides the experience-tier fallback. |
| `enum_values` | map | no | Parsed enum labels per language `{de: {0: "off", 1: "on"}, en: {...}}` (currently unused by code; enum labels come from XML). |
| `group` | string | no | Functional group id (e.g. `boiler`, `heating_circuit`, `dhw`) assigned during enrichment |
| `fct_type` | int | no | LON function type that owns this datapoint |
| `experience_minimum` | string | no | Minimum experience level to include this entity: `essential` \| `comfort` \| `advanced` \| `expert` \| `service`. Defaults to `expert` when absent. |
| `unverified` | bool | no | `true` if the OID was imported from an external reference and has not been confirmed against a live device. Unverified entries are not classified automatically; they default to `unknown`. |
| `data_role` | string | no | Domain semantic role: `measurement`, `setpoint`, `configuration`, `operating_state`, `actuator_state`, `command`, `counter`, `forecast`, `derived`, `diagnostic`, `unknown`. Default: `unknown`. For writable datapoints this drives the default `parameter_scope` when `parameter_scope` is not set: `setpoint`/`operating_state`/`command` → `user`, `configuration` → `config`. |
| `temporal_semantics` | string | no | Temporal behaviour: `sampled`, `step`, `event`, `counter`, `snapshot`, `none`. Default: `none`. |
| `model_role` | string | no | Model relevance: `feature`, `target`, `context`, `event`, `control`, `ignore`, `unknown`. Default: `unknown`. |
| `history_importance` | string | no | History recommendation: `critical`, `standard`, `low`, `none`. Default: `standard`. |

## `experience_minimum` ordering rule

```
essential < comfort < advanced < expert < service
```

An entity is included when `effective_experience_minimum <= user_tier` (ordinal
comparison). The effective minimum is the more restrictive of the declared
`experience_minimum` (or `expert` when absent) and the `parameter_scope` tier
floor:

- `user` scope: no floor (keeps declared `experience_minimum`).
- `config` scope: floor at `expert`.
- `installer` scope: floor at `service`.

If neither `parameter_scope` nor `data_role` is set on a writable datapoint, the
scope is unset and the declared `experience_minimum` is used unchanged.

## Example entry

```yaml
- oid: 1/65/0/0/7/0
  key: lon_1_65_0_0_7_0
  i18n:
    de: Kesseltemperatur Istwert
    en: Boiler temp. actual value
    fr: Temp. effective chaudière
    it: Temp. di caldaia Valore effettivo
  api_name: 00-007
  hint_node: LogWIN
  type_id: 13
  write_protected: true
  unit: °C
  device_class: temperature
  state_class: measurement
  group: boiler
  fct_type: 10
  experience_minimum: essential
  suggested_display_precision: 1
  data_role: measurement
  temporal_semantics: sampled
  model_role: feature
  history_importance: critical
  icon: mdi:fire
```

## Semantic metadata examples

### Physical temperature measurement

```yaml
- oid: 1/16/0/0/15/0
  key: lon_1_16_0_0_15_0
  i18n:
    de: Puffertemperatur Oben
    en: Buffer temperature top
  unit: "°C"
  device_class: temperature
  state_class: measurement
  suggested_display_precision: 1
  icon: mdi:storage-tank
  data_role: measurement
  temporal_semantics: sampled
  model_role: feature
  history_importance: critical
  group: buffer
  experience_minimum: essential
```

### Numeric setpoint (no state class)

```yaml
- oid: 1/15/0/1/1/0
  key: lon_1_15_0_1_1_0
  i18n:
    de: Sollwert
    en: Temperature setpoint
  unit: "°C"
  device_class: temperature
  state_class: null
  suggested_display_precision: 1
  icon: mdi:thermostat
  data_role: setpoint
  temporal_semantics: step
  model_role: control
  history_importance: critical
  group: heating_circuit
  experience_minimum: essential
```

### Heating curve configuration (no state class)

```yaml
- oid: 1/15/0/3/1/0
  key: lon_1_15_0_3_1_0
  i18n:
    de: Fußpunkt
    en: Heating curve foot point
  unit: "°C"
  device_class: temperature
  state_class: null
  suggested_display_precision: 1
  icon: mdi:chart-bell-curve
  data_role: configuration
  temporal_semantics: step
  model_role: context
  history_importance: critical
  group: heating_circuit
```

### Operating phase (enum, no state class)

```yaml
- oid: 1/65/0/2/1/0
  key: lon_1_65_0_2_1_0
  i18n:
    de: Betriebsphasen
    en: Boiler operating phase
  state_class: null
  icon: mdi:state-machine
  data_role: operating_state
  temporal_semantics: event
  model_role: event
  history_importance: critical
  group: boiler
  experience_minimum: essential
```

### Actuator state (pump)

```yaml
- oid: 1/16/0/22/50/0
  key: lon_1_16_0_22_50_0
  i18n:
    de: Pufferladepumpe
    en: Buffer loading pump
  state_class: null
  icon: mdi:pump
  data_role: actuator_state
  temporal_semantics: event
  model_role: event
  history_importance: critical
  group: boiler_loading_pump
  experience_minimum: expert
```

## Recorder history and long-term statistics

- `state_class` is **not** required for ordinary Recorder history. It only enables Home Assistant long-term statistics (LTS) for eligible sensor entities.
- LTS stores aggregated values (minimum, maximum, mean) over time. It does **not** preserve the exact sequence of operating phase transitions, setpoint changes, or configuration edits.
- Values such as operating phases, pump states, setpoints, heating curve parameters, and configuration values are historically critical even when they carry no `state_class`.
- Recorder retention is controlled by the user's global Recorder configuration and `purge_keep_days`. This integration does not modify those settings.
- `history_importance` is a recommendation for future export or model-training tools, not a guarantee that Home Assistant retains data permanently.
- Static metadata attributes (`windhager_data_role`, `windhager_temporal_semantics`, `windhager_model_role`, `windhager_history_importance`, `windhager_oid`, `windhager_write_protected`) are excluded from Recorder attribute storage. The primary entity state remains fully recorded.
- Metadata changes require an integration reload or Home Assistant restart. Long-term statistics are not created retroactively.
