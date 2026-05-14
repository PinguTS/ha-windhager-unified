# Windhager Home Assistant Integration — Documentation

This documentation covers the **ha-windhager-unified** custom integration for Home Assistant.
It is structured using [Diátaxis](https://diataxis.fr/) principles: tutorials, how-to
guides, reference material, and explanatory background are separated so each audience
can navigate to what they need.

## Audiences

| Audience | Start here |
|---|---|
| **Homeowner / end user** — wants a dashboard and notifications | [Installation](user/installation.md) → [Setup](user/setup.md) → [Experience levels](user/experience-levels.md) |
| **Power user / automation author** — builds automations and wants all data | [Entities](user/entities.md) → [Services](user/services.md) → [Experience levels](user/experience-levels.md) |
| **Integrator / developer** — reads or extends the integration code | [Architecture](integrator/architecture.md) → [REST API](integrator/rest-api.md) → [LON model](integrator/lon-model.md) |
| **Installer / service technician** — configures, diagnoses, or replaces the system | [Boiler detection](integrator/boiler-detection.md) → [Discovery](integrator/discovery.md) → Experience level **Service** |

## Source-of-truth pointers

All REST API claims in this documentation trace back to the Swagger 1.2 source files in
[`docs/swagger/`](swagger/). The generated
reference pages ([rest-api.md](integrator/rest-api.md) and
[swagger-coverage.md](integrator/swagger-coverage.md)) are produced by running:

```
docker compose run --rm test python scripts/build_docs.py
```

LON datapoints and their metadata are curated in
[`custom_components/windhager_unified/oids.yaml`](../custom_components/windhager_unified/oids.yaml).

The label XML files shipped with the integration under
`custom_components/windhager_unified/labels/` originate from the Windhager device's
`/res/xml/` endpoint — see [XML resources](integrator/xml-resources.md) for details.

## User guides

- [Installation](user/installation.md)
- [Setup walkthrough](user/setup.md)
- [Experience levels](user/experience-levels.md)
- [Entities reference](user/entities.md)
- [Services](user/services.md)
- [Troubleshooting](user/troubleshooting.md)

## Integrator reference

- [Architecture](integrator/architecture.md)
- [REST API reference](integrator/rest-api.md) *(generated)*
- [LON / OID model](integrator/lon-model.md)
- [Discovery flow](integrator/discovery.md)
- [Boiler detection](integrator/boiler-detection.md)
- [XML label resources](integrator/xml-resources.md)
- [Swagger API coverage](integrator/swagger-coverage.md) *(generated)*

## Schema reference

- [OID catalogue schema](reference/oids-schema.md)
- [REST endpoint catalogue schema](reference/endpoints-schema.md)
