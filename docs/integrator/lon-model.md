# LonWorks / LON Data Model

This document describes how the integration models the Windhager LON bus
hierarchy and maps it to Home Assistant entities.

## LON concepts relevant to this integration

The Windhager RC7030 controller exposes its LON network through a REST API.
You do not interact with LON directly — the REST server acts as the sole
abstraction boundary.

**Node** (`/api/1.0/nodes`)  
A physical or logical device on the LON segment. Each node has a `nodeId` and
`subnet`. The integration fetches the full node list at discovery time.

**Function** (returned by `/api/1.0/lookup/{subnet}/{nodeId}`)  
A function block inside a node. Functions are identified by a `fctType`
integer. The `fctType` determines the device class (boiler, circuit, buffer
tank, etc.) via the `MapToInstance.xml` label file.

**Datapoint** (OID)  
A single measured or controllable value within a function. OIDs are
hierarchical addresses encoded as `subnet/nodeId/fctId/groupNr/memberNr/index`.
The REST API exposes them at:

```
GET  /api/1.0/datapoint/{subnet}/{nodeId}/{fctId}/{gn}/{mn}/{index}
PUT  /api/1.0/datapoint/{subnet}/{nodeId}/{fctId}/{gn}/{mn}/{index}
```

## OID address structure

| Segment    | Meaning                                          |
| ---------- | ------------------------------------------------ |
| `subnet`   | LON subnet number (usually 1)                    |
| `nodeId`   | Node within the subnet                           |
| `fctId`    | Function instance within the node                |
| `gn`       | Group number — selects the VarIdent label group  |
| `mn`       | Member number — selects the label within the gn  |
| `index`    | Index within repeating structures (usually 0)    |

The static mapping `custom_components/windhager_unified/oids.yaml` stores known OIDs
with their human-readable labels (via `gn`/`mn`) and metadata such as
`group`, `fct_type`, and `experience_minimum`.

## Label resolution

The REST API returns raw numeric values. Human-readable labels and
enumeration text come from the XML files bundled in
`custom_components/windhager_unified/labels/`:

| File                     | Content                                    |
| ------------------------ | ------------------------------------------ |
| `VarIdentTexte_de.xml`   | German variable names, keyed by gn + mn    |
| `VarIdentTexte_en.xml`   | English variable names                     |
| `AufzaehlTexte_de.xml`   | German enumeration value labels            |
| `AufzaehlTexte_en.xml`   | English enumeration value labels           |
| `EbenenTexte_de.xml`     | Level / layer labels (navigation)          |
| `ErrorTexte_de.xml`      | Fault/error code descriptions              |
| `MapToInstance.xml`      | `fctType` → function class name            |
| `StaticNav.xml`          | Navigation hierarchy (human tree labels)   |
| `StaticNavAssignment.xml`| Maps fctId positions to nav nodes          |

`LabelCatalog` (in `labels/__init__.py`) loads these files at startup and
provides `var_ident(gn, mn, lang)`, `enum_label(gn, mn, val, lang)`, and
`error_text(code, lang)` lookups.

The user can optionally refresh these files from the live device at
`GET /res/xml/<filename>` via the `refresh_labels_from_device` option in the
OptionsFlow. This is useful when the device firmware is newer than the bundled
files.

## Writable vs read-only datapoints

The Swagger definition for the `datapoint` resource documents both GET and
PUT operations. The integration classifies datapoints from `oids.yaml` using
the `fct_type` field:

| `fct_type`  | Platform   | Behaviour                                    |
| ----------- | ---------- | -------------------------------------------- |
| `sensor`    | `sensor`   | Read-only, numeric or text state             |
| `switch`    | `switch`   | Read + write, boolean (0/1)                  |
| `select`    | `select`   | Read + write, enumerated set of values       |
| `button`    | `button`   | Write-only trigger (sends a fixed value)     |

The `fct_type` values in `oids.yaml` are inferred from German label semantics
and device context (see `scripts/enrich_oids_experience_tier.py`). They are
not directly documented in the Swagger files. When in doubt, treat a
datapoint as read-only.

## Groups

Each OID carries a `group` field that names the functional domain it belongs
to. Groups are the same vocabulary used in the `discovery.py` classification:

| Group         | Description                              |
| ------------- | ---------------------------------------- |
| `boiler`      | Combustion, fuel, and burner parameters  |
| `circuit`     | Heating circuit temperature and curves   |
| `hot_water`   | Domestic hot water preparation           |
| `buffer`      | Buffer / accumulator tank                |
| `solar`       | Solar thermal collectors                 |
| `heat_pump`   | Heat pump compressor and circuit         |
| `system`      | System-wide settings and diagnostics     |
| `network`     | LON bus and communication                |
| `unknown`     | Unclassified or service-only datapoints  |

## Limits not documented in Swagger

The following behaviours are observed from a real device but are not
documented in the Swagger files. They are labelled as assumptions:

- **ASSUMPTION** — The lookup walk terminates when a level returns an empty
  function list. The integration caps the walk at `MAX_LEVELS=200` and
  `MAX_POSITIONS=20` per level as a safety limit.
- **ASSUMPTION** — Boiler family names (`kesselwahl` id → product label) are
  best-effort mappings derived from device observation. Only the numeric id is
  formally documented.
- **ASSUMPTION** — A 404 from a datapoint GET means the datapoint is not
  present in the current firmware or not applicable to the installed boiler
  type. The integration tracks such OIDs in `coordinator.unknown_oids`.
