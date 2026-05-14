# XML Label Resources

The Windhager device serves a set of XML files at `/res/xml/` that provide
human-readable strings for LON datapoints. The integration bundles a copy of
these files in `custom_components/windhager_unified/labels/` so it works offline.

## File inventory

| File                          | Format       | Content                              |
| ----------------------------- | ------------ | ------------------------------------ |
| `VarIdentTexte_de.xml`        | VarIdent     | German variable names (gn + mn)      |
| `VarIdentTexte_en.xml`        | VarIdent     | English variable names               |
| `AufzaehlTexte_de.xml`        | AufzaehlText | German enumeration value labels      |
| `AufzaehlTexte_en.xml`        | AufzaehlText | English enumeration value labels     |
| `EbenenTexte_de.xml`          | EbenenText   | Navigation level labels              |
| `ErrorTexte_de.xml`           | ErrorText    | Fault code descriptions              |
| `MapToInstance.xml`           | MapToInstance| `fctType` → instance/class name      |
| `StaticNav.xml`               | StaticNav    | Full navigation hierarchy            |
| `StaticNavAssignment.xml`     | Assignment   | Maps `fctId` positions to nav nodes  |

## XML schemas

### VarIdentTexte

```xml
<VarIdentTexte>
  <gn id="0">                        <!-- group number -->
    <mn id="0">Aussentemperatur</mn> <!-- member number → label text -->
    <mn id="1">Aktual</mn>
    ...
  </gn>
</VarIdentTexte>
```

The `gn`/`mn` pair corresponds directly to the LON OID segments `gn` and `mn`.

### AufzaehlTexte

```xml
<AufzaehlTexte>
  <gn id="2">
    <mn id="1">
      <val id="0">Aus</val>
      <val id="1">Ein</val>
      <val id="8">Automatik</val>
    </mn>
  </gn>
</AufzaehlTexte>
```

The `val id` matches the raw numeric value returned by the REST API.

### ErrorTexte

```xml
<ErrorTexte>
  <err id="1">Temperaturgrenze Kesselthermometer überschritten</err>
</ErrorTexte>
```

Error code `id` is matched by looking up the fault code from a LON datapoint.

### MapToInstance

```xml
<MapToInstance>
  <entry fctType="10" instance="WP_Kessel"/>
  <entry fctType="11" instance="WP_Brenner"/>
</MapToInstance>
```

The `fctType` integer is used to classify functions during discovery.

## LabelCatalog API

`LabelCatalog` (in `labels/__init__.py`) wraps all the XML files:

```python
catalog = LabelCatalog.load()          # load bundled files
catalog.var_ident(gn, mn, lang="de")   # → "Aussentemperatur" or None
catalog.enum_label(gn, mn, val, lang)  # → "Automatik" or None
catalog.error_text(code, lang)         # → "Temperaturgrenze..." or None
```

`load()` also accepts a `base_dir` argument pointing to a directory of
downloaded files. If a file is missing from `base_dir`, the loader falls back
to the bundled copy automatically.

## Optional device refresh

The OptionsFlow exposes a `refresh_labels_from_device` toggle. When enabled
during a reconfigure, `LabelCatalog.async_refresh_from_device` is called:

1. Fetches the Apache directory index at `GET /res/xml/`.
2. Parses all `<a href="*.xml">` links.
3. Downloads each file to a writable storage directory.
4. Re-loads the catalog from the new files.

This is useful when the device firmware ships newer labels than the bundled
copies. The refresh is idempotent and falls back to bundled files on any
individual download failure.

## Keeping bundled files up to date

1. Download the XML files from the device: `GET http://<host>/res/xml/<filename>`.
2. Copy them into `custom_components/windhager_unified/labels/`.
3. Commit the updated files.

The script `scripts/enrich_oids_i18n_from_resources_xml.py` re-reads
`VarIdentTexte_de.xml` and updates `oids.yaml` with the latest German labels.
Run it after updating the bundled files.
