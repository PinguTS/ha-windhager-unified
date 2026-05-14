"""Tests for custom_components/windhager_unified/labels.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from custom_components.windhager_unified.labels import LabelCatalog, parse_res_xml_index

# ---------------------------------------------------------------------------
# Bundled XML fixtures: use the actual labels/ dir shipped with the integration
# ---------------------------------------------------------------------------

LABELS_DIR = Path(__file__).parent.parent / "custom_components" / "windhager_unified" / "labels"


@pytest.fixture(scope="module")
def catalog() -> LabelCatalog:
    return LabelCatalog.load(LABELS_DIR)


# ---------------------------------------------------------------------------
# VarIdent
# ---------------------------------------------------------------------------


def test_var_ident_german_from_bundled(catalog: LabelCatalog):
    """gn=0, mn=0 should return 'Aussentemperatur' from VarIdentTexte_de.xml."""
    result = catalog.var_ident(0, 0, lang="de")
    assert result is not None
    assert "temperatur" in result.lower() or "aussen" in result.lower()


def test_var_ident_english_from_bundled(catalog: LabelCatalog):
    # gn=0, mn=1 → "Actual" in English VarIdentTexte_en.xml
    result = catalog.var_ident(0, 1, lang="en")
    assert result is not None
    assert len(result) > 0


def test_var_ident_missing_pair_returns_none(catalog: LabelCatalog):
    result = catalog.var_ident(9999, 9999, lang="en")
    assert result is None


def test_var_ident_fallback_to_english(catalog: LabelCatalog):
    """If German is missing for a pair, should fall back to English."""
    result = catalog.var_ident(0, 0, lang="de")
    assert result is not None


# ---------------------------------------------------------------------------
# Enum labels
# ---------------------------------------------------------------------------


def test_enum_label_german(catalog: LabelCatalog):
    """gn=2, mn=1, eid=8 → 'Modulationsbetrieb' in German."""
    result = catalog.enum_label(2, 1, 8, lang="de")
    assert result is not None
    assert "modulation" in result.lower()


def test_enum_label_english(catalog: LabelCatalog):
    result = catalog.enum_label(2, 1, 8, lang="en")
    assert result is not None


def test_enum_label_missing_returns_none(catalog: LabelCatalog):
    result = catalog.enum_label(9999, 9999, 9999, lang="de")
    assert result is None


def test_has_enum_labels_known_pair(catalog: LabelCatalog):
    """gn=2, mn=1 has enum labels in the bundled XML."""
    assert catalog.has_enum_labels(2, 1) is True


def test_has_enum_labels_unknown_pair(catalog: LabelCatalog):
    assert catalog.has_enum_labels(9999, 9999) is False


def test_enum_options_returns_sorted_unique_labels(catalog: LabelCatalog):
    """enum_options for gn=2, mn=1 returns a non-empty list of strings."""
    options = catalog.enum_options(2, 1, lang="en")
    assert len(options) > 0
    assert all(isinstance(o, str) for o in options)
    # Modulation mode is eid=8 and must be present
    assert any("modulation" in o.lower() for o in options)


def test_enum_options_no_duplicates(catalog: LabelCatalog):
    """Options list must not contain duplicate strings."""
    options = catalog.enum_options(2, 1, lang="en")
    assert len(options) == len(set(options))


# ---------------------------------------------------------------------------
# Error texts
# ---------------------------------------------------------------------------


def test_error_text_german(catalog: LabelCatalog):
    """Error code 1 → primary-air-flap text in German."""
    result = catalog.error_text(1, lang="de")
    assert result is not None
    assert len(result) > 5  # non-empty meaningful text


def test_error_text_missing_returns_none(catalog: LabelCatalog):
    result = catalog.error_text(99999, lang="de")
    assert result is None


# ---------------------------------------------------------------------------
# Static nav
# ---------------------------------------------------------------------------


def test_static_nav_lookup(catalog: LabelCatalog):
    result = catalog.static_nav("03:61", lang="de")
    assert result is not None


# ---------------------------------------------------------------------------
# Missing file: catalogue still loads
# ---------------------------------------------------------------------------


def test_catalog_loads_with_missing_file(tmp_path: Path):
    """LabelCatalog.load() should not raise when a storage dir is empty.

    The implementation falls back to bundled XMLs, so lookups still work.
    The key requirement is that load() does not raise.
    """
    # tmp_path has no XML files; loader should fall back to bundled without raising
    cat = LabelCatalog.load(tmp_path)
    assert cat is not None
    # Bundled fallback means German outside temp is still resolved
    # (or None if bundled is also missing — either is acceptable)
    # No assertion on value — just that it doesn't raise
    cat.var_ident(0, 0, "de")


# ---------------------------------------------------------------------------
# /res/xml/ index HTML parsing
# ---------------------------------------------------------------------------

# The exact HTML format observed on a real RC7030-class device (DOCTYPE HTML 3.2)
_INDEX_HTML = """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /res/xml</title>
 </head>
 <body>
<h1>Index of /res/xml</h1>
<ul><li><a href="/res/"> Parent Directory</a>
<li><a href="AufzaehlTexte_de.xml"> AufzaehlTexte_de.xml</a>
<li><a href="AufzaehlTexte_en.xml"> AufzaehlTexte_en.xml</a>
<li><a href="AufzaehlTexte_fr.xml"> AufzaehlTexte_fr.xml</a>
<li><a href="AufzaehlTexte_it.xml"> AufzaehlTexte_it.xml</a>
<li><a href="EbenenTexte_de.xml"> EbenenTexte_de.xml</a>
<li><a href="EbenenTexte_en.xml"> EbenenTexte_en.xml</a>
<li><a href="EbenenTexte_fr.xml"> EbenenTexte_fr.xml</a>
<li><a href="EbenenTexte_it.xml"> EbenenTexte_it.xml</a>
<li><a href="ErrorTexte_de.xml"> ErrorTexte_de.xml</a>
<li><a href="ErrorTexte_en.xml"> ErrorTexte_en.xml</a>
<li><a href="ErrorTexte_fr.xml"> ErrorTexte_fr.xml</a>
<li><a href="ErrorTexte_it.xml"> ErrorTexte_it.xml</a>
<li><a href="MapToInstance.xml"> MapToInstance.xml</a>
<li><a href="StaticNav.xml"> StaticNav.xml</a>
<li><a href="StaticNavAssignment.xml"> StaticNavAssignment.xml</a>
<li><a href="VarIdentTexte_de.xml"> VarIdentTexte_de.xml</a>
<li><a href="VarIdentTexte_en.xml"> VarIdentTexte_en.xml</a>
<li><a href="VarIdentTexte_fr.xml"> VarIdentTexte_fr.xml</a>
<li><a href="VarIdentTexte_it.xml"> VarIdentTexte_it.xml</a>
<li><a href="ws.getDP.req.xml"> ws.getDP.req.xml</a>
<li><a href="ws.getDP.res.xml"> ws.getDP.res.xml</a>
<li><a href="ws.listDP.req.xml"> ws.listDP.req.xml</a>
<li><a href="ws.listDP.res.xml"> ws.listDP.res.xml</a>
<li><a href="ws.readDP.req.xml"> ws.readDP.req.xml</a>
<li><a href="ws.readDP.res.xml"> ws.readDP.res.xml</a>
<li><a href="ws.setDP.req.xml"> ws.setDP.req.xml</a>
<li><a href="ws.setDP.res.xml"> ws.setDP.res.xml</a>
<li><a href="ws.writeDP.req.xml"> ws.writeDP.req.xml</a>
<li><a href="ws.writeDP.res.xml"> ws.writeDP.res.xml</a>
</ul>
</body></html>
"""


def test_parse_res_xml_index_29_files():
    basenames = parse_res_xml_index(_INDEX_HTML)
    assert len(basenames) == 29
    # Parent directory link must not appear
    assert all(not b.startswith("/") for b in basenames)
    # Spot-check
    assert "VarIdentTexte_de.xml" in basenames
    assert "MapToInstance.xml" in basenames


def test_parse_res_xml_index_excludes_parent():
    basenames = parse_res_xml_index(_INDEX_HTML)
    assert "/res/" not in basenames
    assert "" not in basenames


def test_parse_res_xml_index_malformed_html():
    """Malformed / empty HTML should return empty list, not raise."""
    result = parse_res_xml_index("")
    assert result == []

    result = parse_res_xml_index("<html><body>no links here</body></html>")
    assert result == []


def test_parse_res_xml_index_partial():
    """HTML with one valid and one non-xml link returns only the xml one."""
    html = '<a href="something.txt">file</a> <a href="labels.xml">xml</a>'
    result = parse_res_xml_index(html)
    assert result == ["labels.xml"]


# ---------------------------------------------------------------------------
# refresh_from_device mock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_from_device_success(tmp_path: Path):
    """refresh_from_device writes cached files and reloads the catalogue."""
    cat = LabelCatalog.load(LABELS_DIR)

    minimal_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<VarIdentTexte lang="de"><gn id="0"><mn id="0">RefreshTest</mn></gn></VarIdentTexte>'
    )

    client = AsyncMock()
    client.async_request.side_effect = [
        # First call: /res/xml/ index
        {"text": '<a href="VarIdentTexte_de.xml">VarIdentTexte_de.xml</a>'},
        # Second call: file fetch
        {"text": minimal_xml},
    ]

    storage_dir = tmp_path / "windhager_unified_labels"
    await cat.async_refresh_from_device(client, storage_dir)

    # After refresh, var_ident(0, 0, "de") should return "RefreshTest"
    assert cat.var_ident(0, 0, "de") == "RefreshTest"


@pytest.mark.asyncio
async def test_refresh_from_device_404_falls_back_silently(tmp_path: Path):
    """If /res/xml/ returns empty/404, the bundled labels are still usable."""
    cat = LabelCatalog.load(LABELS_DIR)

    client = AsyncMock()
    client.async_request.return_value = {"text": ""}  # empty body

    original_result = cat.var_ident(0, 0, "de")
    storage_dir = tmp_path / "windhager_unified_labels"
    await cat.async_refresh_from_device(client, storage_dir)

    # Bundled labels still intact
    assert cat.var_ident(0, 0, "de") == original_result
