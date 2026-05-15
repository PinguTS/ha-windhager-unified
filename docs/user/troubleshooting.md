# Troubleshooting

## Enable debug logging

Add this to your `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: warning
  logs:
    custom_components.windhager_unified: debug
```

Debug logs include every HTTP request and response, authentication challenges,
OID parse warnings, and coordinator cycle timing.

## Common errors

### `cannot_connect`

The integration cannot reach the device.

- Confirm the host or IP is reachable from the HA server (try `ping` or open
  the URL in a browser).
- Check that port 80/443 is not blocked by a firewall.
- If using HTTPS with a self-signed certificate, uncheck **Verify SSL** in the
  options.

### `invalid_auth`

Username or password rejected.

- The default Windhager username is `Service`.
- Passwords are case-sensitive.
- Some installations change the default credentials. Contact your installer.

### Entities missing after setup

See [Experience levels — why don't I see entity X?](experience-levels.md#why-dont-i-see-entity-x).

### `UpdateFailed: Authentication failed`

The session expired or credentials changed while the integration was running.
Reload the integration from **Settings → Devices & Services → Windhager Unified →
three-dot menu → Reload**.

### Values stuck / not updating

Check the coordinator's `last_update_success` in **Developer Tools → Template**

(substitute a sensor entity from this integration, e.g. from **Developer Tools → States**):

```
{{ state_attr('sensor.YOUR_ENTITY_ID', 'last_updated') }}
```

Download a **Diagnostics** file (**Settings → Devices & Services → Windhager Unified →
three-dot menu → Download diagnostics**) and check `coordinator.last_update_success`.

### Diagnostics file

The diagnostics download (available to all users) contains:

- Redacted config entry (host, username, and password are stripped).
- Selected experience level and groups.
- Coordinator state: last update success flag, counts of datapoints and REST
  groups, and the current data snapshot.
- The list of `unknown_oids`: datapoints found on the device but not in
  `oids.yaml` — useful for reporting gaps.

### Reporting a bug

Include the diagnostics file and the relevant debug log section (with any
hostnames/IPs replaced by `<redacted>`). Open an issue at
<https://github.com/PinguTS/ha-windhager-unified/issues>.
