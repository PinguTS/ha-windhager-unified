# Services

## `windhager_unified.set_datapoint`

Writes a value directly to any LON OID.

**Available at experience level:** Expert or Service (the caller must also have
the appropriate Windhager credentials for the target datapoint).

### Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `oid` | string | yes | OID in `a/b/c/d/e/f` or `a.b.c.d.e.f` format (6 parts) |
| `value` | string | yes | Value to write; the device parses the string |

### Example

```yaml
service: windhager_unified.set_datapoint
data:
  oid: "1/15/0/3/51/0"
  value: "21.0"
```

This writes `21.0` to OID `1/15/0/3/51/0` (heating setpoint, from the OID
catalogue). The integration validates that the OID has exactly 6 parts, then
calls `PUT /api/1.0/datapoint/{oid}?value={value}` using the configured
credentials.

> **Important:** There is no soft interlock preventing you from writing to a
> read-protected or write-protected datapoint. The Windhager device will return
> HTTP 4xx if the operation is not permitted. Always confirm write capability
> from `oids.yaml` (`write_protected: false`) before building automations.
