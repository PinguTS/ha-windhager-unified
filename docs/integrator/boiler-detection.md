# Boiler Detection

The integration detects the connected boiler family using the
`InfoWinHeartbeat` service, which is documented in
[`docs/swagger/InfoWinHeartbeat_1.0_kesselwahl.json`](../../docs/swagger/InfoWinHeartbeat_1.0_kesselwahl.json).

## Swagger-documented endpoint

```
GET  /InfoWinHeartbeat/api/1.0/kesselwahl/selected
PUT  /InfoWinHeartbeat/api/1.0/kesselwahl/selected
GET  /InfoWinHeartbeat/api/1.0/kesselwahl/list
```

The `selected` endpoint returns the currently active boiler entry as:

```json
{ "id": 2, "name": "Holz" }
```

The `list` endpoint returns all entries the firmware knows about:

```json
[{ "id": 1 }, { "id": 2 }, { "id": 3 }]
```

## ID to product family mapping

The Swagger schema documents the `id` field as an integer but does not specify
which id maps to which physical product. The integration uses a
best-effort mapping in `discovery.py`:

| `id` | Assumed family (ASSUMPTION)     |
| ---- | ------------------------------- |
| 1    | BioWIN / PuroWIN (Pellets)      |
| 2    | LogWIN (Holz)                   |
| 3    | DuoWIN (Kombikessel)            |
| 4    | HackWIN (Hackschnitzel)         |
| 5    | OelWIN (Öl)                     |
| 6    | GasWIN (Gas)                    |
| 7    | BWWP (Brauchwasser-Wärmepumpe)  |

Any unknown `id` is reported as `"Unknown boiler (id={id})"`. The label is
shown in the config flow and in diagnostics, but does not affect polling
behaviour.

**Risk:** If Windhager changes these id values in a firmware update, the
display label will be wrong but the integration will continue to function
because no logic depends on the label.

## API client helpers

`WindhagerApiClient` exposes:

```python
async def async_get_kesselwahl_selected() -> dict
async def async_get_kesselwahl_list() -> list[dict]
async def async_put_kesselwahl(boiler_id: int, option: int) -> None
```

These methods live in `api_client.py` and are tested in
`tests/test_api_client.py`.

## Adding a new boiler family

If you discover a new `id` value on a real device:

1. Update `KESSELWAHL_FAMILY` in `discovery.py`.
2. Add a test in `tests/test_discovery.py` covering the new id.
3. Document the `id → name` mapping in this file.
4. Open a PR with the device evidence (screenshot of the device UI or API
   response).
