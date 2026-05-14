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
| `device_class` | string | no | HA sensor device class slug (e.g. `temperature`, `power`) |
| `state_class` | string | no | HA sensor state class slug (`measurement`, `total`, `total_increasing`) |
| `enum_values` | map | no | Parsed enum labels per language `{de: {0: "off", 1: "on"}, en: {...}}` |
| `group` | string | no | Functional group id (e.g. `boiler`, `heating_circuit`, `dhw`) assigned during enrichment |
| `fct_type` | int | no | LON function type that owns this datapoint |
| `experience_minimum` | string | no | Minimum experience level to include this entity: `essential` \| `comfort` \| `advanced` \| `expert` \| `service`. Defaults to `expert` when absent. |
| `unverified` | bool | no | `true` if the OID was imported from an external reference and has not been confirmed against a live device. |

## `experience_minimum` ordering rule

```
essential < comfort < advanced < expert < service
```

An entity is included when `experience_minimum <= user_tier` (ordinal
comparison). If the field is absent the datapoint is treated as `expert`
(visible only at Expert or Service level).

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
```
