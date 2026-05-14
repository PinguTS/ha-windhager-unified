"""Label catalogue for Windhager LON datapoints.

Loads bundled XML files from this package directory (shipped with the
integration) and provides a lookup interface for variable names, enum labels,
level names, and error texts.

Optionally, labels can be refreshed from the device's /res/xml/ endpoint.
This is an IMPLEMENTATION ASSUMPTION: the endpoint is not documented in Swagger
but was observed on one RC7030-class device as an Apache directory listing
(DOCTYPE HTML 3.2 Final).  The refresh is disabled by default and will fail
safely — bundled labels remain in use on any error.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from html.parser import HTMLParser
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from ..api_client import WindhagerApiClient

_LOGGER = logging.getLogger(__name__)

# Bundled XML files live next to this __init__.py
_BUNDLE_DIR = Path(__file__).parent

SUPPORTED_LANGS = ("de", "en", "fr", "it")
_FALLBACK_LANG = "en"


# ---------------------------------------------------------------------------
# HTML index parser
# ---------------------------------------------------------------------------


class _ApacheIndexParser(HTMLParser):
    """Parse basenames from an Apache-generated directory listing.

    Only extracts links whose href ends with '.xml' and does not start
    with '/' (to exclude the parent-directory link).  Implementation
    assumption: observed HTML uses <a href="File.xml">…</a> list items.
    """

    def __init__(self) -> None:
        super().__init__()
        self.basenames: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value and value.endswith(".xml") and not value.startswith("/"):
                self.basenames.append(value.rstrip("/"))


def parse_res_xml_index(html: str) -> list[str]:
    """Return sorted list of .xml basenames from a /res/xml/ Apache index page."""
    parser = _ApacheIndexParser()
    parser.feed(html)
    return sorted(parser.basenames)


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


class LabelCatalog:
    """Provides human-readable label lookups from bundled (or refreshed) XML files.

    Loaded synchronously from disk at construction time.  Use the class method
    ``load()`` to create an instance; it logs and skips any missing or
    malformed files so the integration can continue with partial data.
    """

    def __init__(self) -> None:
        # {lang: {(gn, mn): label}}
        self._var_ident: dict[str, dict[tuple[int, int], str]] = {}
        # {lang: {(gn, mn, eid): label}}
        self._aufzaehlung: dict[str, dict[tuple[int, int, int], str]] = {}
        # Fast membership test: (gn, mn) pairs that have at least one enum label
        self._enum_pairs: set[tuple[int, int]] = set()
        # {lang: {(fct_type, level_id): label}}
        self._ebenen: dict[str, dict[tuple[int, int], str]] = {}
        # {lang: {code: text}}
        self._errors: dict[str, dict[int, str]] = {}
        # {gnmn_key: {lang: label}} from StaticNav
        self._static_nav: dict[str, dict[str, str]] = {}

    @classmethod
    def load(cls, base_dir: Path | None = None) -> LabelCatalog:
        """Load bundled XML label files and return a populated catalogue."""
        cat = cls()
        root = base_dir or _BUNDLE_DIR
        cat._load_var_ident(root)
        cat._load_aufzaehlung(root)
        cat._load_ebenen(root)
        cat._load_errors(root)
        cat._load_static_nav(root)
        return cat

    # ------------------------------------------------------------------
    # Public lookup API
    # ------------------------------------------------------------------

    def var_ident(self, gn: int, mn: int, lang: str = "en") -> str | None:
        """Return the variable name for (gn, mn) in the given language.

        Fallback order: requested lang → StaticNav → _FALLBACK_LANG VarIdent.
        """
        key = (gn, mn)
        result = self._var_ident.get(lang, {}).get(key)
        if result:
            return result
        gnmn_key = f"{gn:02d}:{mn:02d}"
        static = self._static_nav.get(gnmn_key, {})
        result = static.get(lang) or static.get(_FALLBACK_LANG)
        if result:
            return result
        if lang != _FALLBACK_LANG:
            return self._var_ident.get(_FALLBACK_LANG, {}).get(key)
        return None

    def enum_label(self, gn: int, mn: int, eid: int, lang: str = "en") -> str | None:
        """Return the enum text for (gn, mn, eid) in the given language."""
        key = (gn, mn, eid)
        result = self._aufzaehlung.get(lang, {}).get(key)
        if result is not None:
            return result
        if lang != _FALLBACK_LANG:
            return self._aufzaehlung.get(_FALLBACK_LANG, {}).get(key)
        return None

    def has_enum_labels(self, gn: int, mn: int) -> bool:
        """Return True if any enum labels are defined for (gn, mn)."""
        return (gn, mn) in self._enum_pairs

    def enum_options(self, gn: int, mn: int, lang: str = "en") -> list[str]:
        """Return all enum labels for (gn, mn) sorted by enum id.

        Falls back to English when the requested language is unavailable.
        Duplicate label strings are deduplicated while preserving order.
        """
        mapping = self._aufzaehlung.get(lang) or self._aufzaehlung.get(_FALLBACK_LANG, {})
        pairs = sorted(
            ((k[2], v) for k, v in mapping.items() if k[0] == gn and k[1] == mn),
            key=lambda t: t[0],
        )
        seen: set[str] = set()
        result: list[str] = []
        for _, label in pairs:
            if label not in seen:
                seen.add(label)
                result.append(label)
        return result

    def level_name(self, fct_type: int, level_id: int, lang: str = "en") -> str | None:
        """Return the level/group name for (fct_type, level_id)."""
        key = (fct_type, level_id)
        result = self._ebenen.get(lang, {}).get(key)
        if result is not None:
            return result
        if lang != _FALLBACK_LANG:
            return self._ebenen.get(_FALLBACK_LANG, {}).get(key)
        return None

    def error_text(self, code: int, lang: str = "en") -> str | None:
        """Return the human-readable error description for a given error code."""
        result = self._errors.get(lang, {}).get(code)
        if result is not None:
            return result
        if lang != _FALLBACK_LANG:
            return self._errors.get(_FALLBACK_LANG, {}).get(code)
        return None

    def static_nav(self, gnmn: str, lang: str = "en") -> str | None:
        """Return the StaticNav label for a gnmn key like '03:61'."""
        labels = self._static_nav.get(gnmn, {})
        return labels.get(lang) or labels.get(_FALLBACK_LANG)

    # ------------------------------------------------------------------
    # Optional device refresh
    # ------------------------------------------------------------------

    async def async_refresh_from_device(
        self,
        client: WindhagerApiClient,
        storage_dir: Path,
    ) -> None:
        """Refresh label XML files from the device's /res/xml/ endpoint.

        IMPLEMENTATION ASSUMPTION: The device serves an Apache-style HTML
        directory index at GET /res/xml/ with links like <a href="File.xml">.
        This was observed on one RC7030-class device and is NOT in Swagger.

        On any error (network, parse, HTTP), the method logs at WARNING and
        returns without modifying the in-memory catalogue.  Caller should
        continue with the already-loaded bundled data.
        """
        try:
            index_resp = await client.async_request("GET", "/res/xml/")
        except Exception as err:
            _LOGGER.warning("labels: could not fetch /res/xml/ index: %s", err)
            return

        html = (index_resp or {}).get("text", "")
        if not html:
            _LOGGER.warning("labels: /res/xml/ returned empty body; skipping refresh")
            return

        basenames = parse_res_xml_index(html)
        if not basenames:
            _LOGGER.warning("labels: no .xml links found in /res/xml/ index; skipping refresh")
            return

        _LOGGER.debug("labels: found %d XML files on device; refreshing", len(basenames))
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, functools.partial(storage_dir.mkdir, parents=True, exist_ok=True)
        )

        fetch_tasks = [
            self._fetch_and_store(client, basename, storage_dir) for basename in basenames
        ]
        await asyncio.gather(*fetch_tasks, return_exceptions=True)

        await loop.run_in_executor(None, self._load_var_ident, storage_dir)
        await loop.run_in_executor(None, self._load_aufzaehlung, storage_dir)
        await loop.run_in_executor(None, self._load_ebenen, storage_dir)
        await loop.run_in_executor(None, self._load_errors, storage_dir)
        await loop.run_in_executor(None, self._load_static_nav, storage_dir)
        _LOGGER.info("labels: refreshed from device, %d files fetched", len(basenames))

    async def _fetch_and_store(
        self,
        client: WindhagerApiClient,
        basename: str,
        dest_dir: Path,
    ) -> None:
        try:
            resp = await client.async_request("GET", f"/res/xml/{basename}")
        except Exception as err:
            _LOGGER.warning("labels: failed to fetch /res/xml/%s: %s", basename, err)
            return

        text = (resp or {}).get("text", "")
        if not text:
            _LOGGER.warning("labels: /res/xml/%s returned empty body; skipping", basename)
            return

        try:
            await asyncio.get_running_loop().run_in_executor(None, ET.fromstring, text.encode())
        except ET.ParseError as err:
            _LOGGER.warning("labels: /res/xml/%s not valid XML (%s); skipping", basename, err)
            return

        dest = dest_dir / basename
        await asyncio.get_running_loop().run_in_executor(
            None, functools.partial(dest.write_text, text, encoding="utf-8")
        )
        _LOGGER.debug("labels: stored %s (%d bytes)", basename, len(text))

    # ------------------------------------------------------------------
    # Internal loaders
    # ------------------------------------------------------------------

    def _open_xml(self, base_dir: Path, filename: str) -> ET.Element | None:
        """Parse an XML file; return root element or None on any error."""
        path = base_dir / filename
        if not path.exists():
            bundled = _BUNDLE_DIR / filename
            if not bundled.exists():
                _LOGGER.debug("labels: %s not found in %s or bundled dir", filename, base_dir)
                return None
            path = bundled
        try:
            tree = ET.parse(path)
            return tree.getroot()
        except ET.ParseError as err:
            _LOGGER.warning("labels: could not parse %s: %s", path, err)
            return None

    def _load_var_ident(self, base_dir: Path) -> None:
        for lang in SUPPORTED_LANGS:
            root = self._open_xml(base_dir, f"VarIdentTexte_{lang}.xml")
            if root is None:
                continue
            mapping: dict[tuple[int, int], str] = {}
            for gn_el in root.findall("gn"):
                try:
                    gn = int(gn_el.get("id", "-1"))
                except ValueError:
                    continue
                for mn_el in gn_el.findall("mn"):
                    try:
                        mn = int(mn_el.get("id", "-1"))
                    except ValueError:
                        continue
                    text = (mn_el.text or "").strip()
                    if text:
                        mapping[(gn, mn)] = text
            self._var_ident[lang] = mapping
            _LOGGER.debug("labels: loaded VarIdentTexte_%s: %d entries", lang, len(mapping))

    def _load_aufzaehlung(self, base_dir: Path) -> None:
        for lang in SUPPORTED_LANGS:
            root = self._open_xml(base_dir, f"AufzaehlTexte_{lang}.xml")
            if root is None:
                continue
            mapping: dict[tuple[int, int, int], str] = {}
            for gn_el in root.findall("gn"):
                try:
                    gn = int(gn_el.get("id", "-1"))
                except ValueError:
                    continue
                for mn_el in gn_el.findall("mn"):
                    try:
                        mn = int(mn_el.get("id", "-1"))
                    except ValueError:
                        continue
                    for enum_el in mn_el.findall("enum"):
                        try:
                            eid = int(enum_el.get("id", "-1"))
                        except ValueError:
                            continue
                        text = (enum_el.text or "").strip()
                        if text:
                            mapping[(gn, mn, eid)] = text
                            self._enum_pairs.add((gn, mn))
            self._aufzaehlung[lang] = mapping
            _LOGGER.debug("labels: loaded AufzaehlTexte_%s: %d entries", lang, len(mapping))

    def _load_ebenen(self, base_dir: Path) -> None:
        for lang in SUPPORTED_LANGS:
            root = self._open_xml(base_dir, f"EbenenTexte_{lang}.xml")
            if root is None:
                continue
            mapping: dict[tuple[int, int], str] = {}
            for fct_el in root.findall("fcttyp"):
                try:
                    fct_type = int(fct_el.get("id", "-999"))
                except ValueError:
                    continue
                for ebene_el in fct_el.findall("ebene"):
                    try:
                        level_id = int(ebene_el.get("id", "-1"))
                    except ValueError:
                        continue
                    text = (ebene_el.text or "").strip()
                    if text:
                        mapping[(fct_type, level_id)] = text
            self._ebenen[lang] = mapping
            _LOGGER.debug("labels: loaded EbenenTexte_%s: %d entries", lang, len(mapping))

    def _load_errors(self, base_dir: Path) -> None:
        for lang in SUPPORTED_LANGS:
            root = self._open_xml(base_dir, f"ErrorTexte_{lang}.xml")
            if root is None:
                continue
            mapping: dict[int, str] = {}
            for err_el in root.findall("error"):
                try:
                    code = int(err_el.get("code", "-1"))
                except ValueError:
                    continue
                text = (err_el.get("text") or "").strip()
                if text:
                    mapping[code] = text
            self._errors[lang] = mapping
            _LOGGER.debug("labels: loaded ErrorTexte_%s: %d entries", lang, len(mapping))

    def _load_static_nav(self, base_dir: Path) -> None:
        root = self._open_xml(base_dir, "StaticNav.xml")
        if root is None:
            return
        for tp_el in root.findall("timeprogram"):
            gnmn = tp_el.get("gnmn", "")
            if not gnmn:
                continue
            text_el = tp_el.find("text")
            if text_el is None:
                continue
            labels: dict[str, str] = {}
            for child in text_el:
                lang_tag = child.tag
                text = (child.text or "").strip()
                if text:
                    labels[lang_tag] = text
            if labels:
                self._static_nav[gnmn] = labels
        _LOGGER.debug("labels: loaded StaticNav: %d entries", len(self._static_nav))
