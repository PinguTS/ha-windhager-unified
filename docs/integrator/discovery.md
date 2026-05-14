# Runtime Discovery

The `discovery` module (`custom_components/windhager_unified/discovery.py`) performs a
one-time runtime introspection of the connected Windhager device during the
config flow. Its output is used to populate the group selection step of the UI
and to build the **`discovered_datapoints`** option (serialized list of OID rows)
that the coordinator uses on **Essential / Comfort / Advanced** tiers.

Tier ↔ `levelId` mapping helpers live in
`custom_components/windhager_unified/tier_lookup.py` (see bundled
`EbenenTexte_*.xml` for boiler-style `fcttyp` 9/10 menu ids 155–158).

## What is discovered

1. **Boiler family** — detected via `GET /InfoWinHeartbeat/api/1.0/kesselwahl/selected`.
   The numeric `id` is mapped to a human-readable product family name using
   `KESSELWAHL_FAMILY` in `discovery.py`. See
   [boiler-detection.md](boiler-detection.md) for details.

2. **LON nodes (topology)** — depends on the selected **experience tier** passed to
   `discover(client, experience_tier=…)` from the config flow:

   - **Essential / Comfort / Advanced** — `GET /api/1.0/lookup/{subnetId}` (default
     subnet `1`). The JSON shape is not fully specified in Swagger (`type: void`);
     the implementation accepts a top-level array of node objects and optional
     inline `functions[]` per node. If that call returns no nodes, discovery
     falls back to `GET /api/1.0/nodes`.

   - **Expert / Service** (or `experience_tier=None`, backward compatible) —
     `GET /api/1.0/nodes` flat list.

3. **Functions per node** — either from the inline `functions` array on each node
   (lookup subnet response) or from `GET /api/1.0/lookup/{subnet}/{nodeId}` when
   not present.

4. **Levels per function** — `GET /api/1.0/lookup/{subnet}/{nodeId}/{fctId}`.
   For easy tiers, only **allowed** `levelId` values are walked (see
   `TIER_LEVEL_FILTER` in `tier_lookup.py`). Expert/Service walk all returned
   levels up to `MAX_LEVELS`.

5. **Datapoint positions** — `GET /api/1.0/lookup/{subnet}/{nodeId}/{fctId}/{levelId}`.
   Each position yields a `DiscoveredDatapoint` (OID, `writeProt`, `typeId`, etc.)
   and an inferred `experience_minimum` (see `experience_minimum_from_discovery`).

6. **Functional groups** — each `fctType` is classified into a named group
   (`boiler`, `heating_circuit`, …) using `MapToInstance.xml` and the
   hardcoded `FUNCTION_TYPE_GROUPS` table.

## Discovery result

`discover()` returns a `DiscoveryResult` dataclass:

```python
@dataclass
class DiscoveryResult:
    boiler_id: int | None
    boiler_name: str | None
    nodes: list[DiscoveredNode]
    groups: list[DiscoveredGroup]
    warnings: list[str]
```

Each `DiscoveredGroup` contains `datapoints: list[DiscoveredDatapoint]` (not only
OID strings). `serialize_discovered_datapoints_for_config()` flattens these into
JSON-serializable dicts for `config_entry.options["discovered_datapoints"]`.

## Walk algorithm (conceptual)

```
kesselwahl/selected
if tier in (essential, comfort, advanced):
    nodes ← GET /api/1.0/lookup/1   (fallback: GET /api/1.0/nodes if empty)
else:
    nodes ← GET /api/1.0/nodes

for each node:
    functions ← node["functions"] or GET /lookup/{subnet}/{nodeId}
    for each function:
        classify fctType → group
        levels ← GET /lookup/{subnet}/{nodeId}/{fctId}
        for each levelId (filtered on easy tiers):
            positions ← GET /lookup/{subnet}/{nodeId}/{fctId}/{levelId}
            for each position (capped):
                append DiscoveredDatapoint
```

Limits: `MAX_LEVELS = 200`, `MAX_POSITIONS = 20` per level.

## Error handling

- A 404 on `kesselwahl/selected` is treated as "no boiler selected" — the
  `boiler_id` and `boiler_name` fields are set to `None`. The rest of
  discovery continues.
- An `WindhagerAuthError` during discovery aborts the entire flow and returns
  an `invalid_auth` error to the user.
- Other API errors log a warning and skip the affected node, so partial
  discovery is possible on resilient devices.

## Using discovery results at runtime

The coordinator reads **`discovered_datapoints`** and **`adhoc_oids`** from
`config_entry.options` (see `WindhagerCoordinator` in `coordinator.py`). It does
**not** re-run discovery on every poll; the lists are fixed at setup (or when
you change options / call **`windhager_unified.add_datapoint`**, which reloads
the entry).
