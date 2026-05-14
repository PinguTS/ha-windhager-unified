# Experience levels

The integration exposes a large number of LON datapoints and REST API values —
sometimes more than 300 on a fully equipped system. Showing all of them to every
user would be overwhelming. **Experience levels** let you choose how much detail
you want on first setup, and change the selection later without removing and
re-adding the integration.

## How to choose

During initial setup the wizard asks you to pick a level. The default is
**Essential**.

You can change the level at any time via **Settings → Devices & Services →
Windhager Unified → Configure (gear icon)**.

## Levels explained

| Level | Slug | Best for | What you get |
|---|---|---|---|
| **Essential** | `essential` | Homeowners who just want a dashboard | Boiler temperature, buffer / DHW summary temps, outdoor temperature, coarse operating state |
| **Comfort** | `comfort` | Engaged homeowners | Everything in Essential, plus heating circuit setpoints and room temperatures, DHW detail, buffer zone breakdown, a human-readable error summary |
| **Advanced** | `advanced` | Power users and automation authors | Everything in Comfort, plus the full error log sensor, heartbeat status, kesselwahl (boiler selection) read-only, VPN / DynIP / system time read-only |
| **Expert** | `expert` | Integrators and automation builders | Everything in Advanced, plus all discovered LON datapoints in selected groups, NV exposure where applicable, `windhager_unified.set_datapoint` for write access |
| **Service** | `service` | Installers with Service-level credentials | Everything in Expert, plus write and reset actions: error log reset, heartbeat start/stop, LED control, factory reset / firmware update paths, kesselwahl selection, notification register/unregister |

## Discovery, lookup levels, and what you see in Home Assistant

During setup, **discovery** walks the device’s documented REST lookup tree. How
deep that walk goes depends on the experience tier you chose:

- **Essential / Comfort / Advanced** — Topology is loaded from
  `GET /api/1.0/lookup/{subnet}` (subnet `1` on RC7030-class devices). Only
  certain **menu level ids** (`levelId` in the API path) are requested, aligned
  with the Windhager UI layers described in the bundled `EbenenTexte_*.xml`
  (e.g. Infoebene `156`, Betreiberebene `157`). The list of OIDs found at those
  levels is stored in the config entry as **`discovered_datapoints`**. For
  curated entries in `oids.yaml`, the coordinator only creates entities whose
  OID appears in that list **and** passes the usual group + tier filters — so
  you are not flooded with expert-only datapoints on an “Essential” install.

- **Expert / Service** — Topology uses `GET /api/1.0/nodes` and a **full**
  lookup walk (still subject to `MAX_LEVELS` / `MAX_POSITIONS` caps). OIDs that
  appear in discovery but **not** in `oids.yaml` get minimal synthetic sensor
  definitions so they can still be polled.

**ASSUMPTION (documented in code):** For function types where the numeric
`levelId` does not map to Info/Operator/Service menus in `EbenenTexte_*.xml`,
the integration falls back to the datapoint’s `writeProt` flag from the lookup
response to guess a minimum tier (`writeProt: true` → read-only / essential
floor, `false` → comfort). Curated `oids.yaml` values always win when both exist.

### Adding a single OID later

Use the **`windhager_unified.add_datapoint`** service: it performs
`GET /api/1.0/datapoint/{…}` to verify the OID, appends it to **`adhoc_oids`**
in the config entry options (with optional **group** slug for your group filter),
and reloads the integration. If you have more than one Windhager config entry,
pass **`config_entry_id`** in the service data.

> **Note:** The **Service** tier assumes your Windhager credentials have
> Service-level privileges. Actions that exceed the credential level will return
> HTTP 403 from the device.

## Relationship to functional groups

Experience level and **groups** are independent filters. During setup:

1. You pick an experience level.
2. The wizard discovers which LON nodes and groups exist on your system.
3. It presents checkboxes for functional groups (boiler, heating circuit 1,
   DHW, buffer, cascade, solar, …). The default checked state depends on your
   chosen tier — Essential checks only the boiler summary and one heating
   circuit; Service tiers check maintenance-related groups too.

The final set of entities created is: **group selected ∩ discovered (tier-scoped for easy tiers) ∩ experience
level applies** (see [Experience levels](experience-levels.md) for how discovery narrows OIDs).

## Why don't I see entity X?

1. Check that the functional group containing X is enabled
   (**Configure → groups**).
2. Check that your experience level includes X — see the table above.
3. Check whether X was discovered on your specific device. Not all models
   expose all datapoints.
4. If an entity was created but is disabled, enable it from the HA **Entities**
   page.

## Changing the level later

Open **Settings → Devices & Services → Windhager Unified → Configure**.

Changing the level reloads the integration. Entities for newly visible
datapoints are added; entities for datapoints above the new level are removed.
Automations referencing removed entities will show "entity not found" — update
them manually.
