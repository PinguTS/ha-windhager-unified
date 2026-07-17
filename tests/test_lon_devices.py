"""Tests for LON function-block device grouping."""

from __future__ import annotations

from custom_components.windhager_unified.const import DOMAIN
from custom_components.windhager_unified.lon_devices import (
    build_function_block_device_info,
    function_block_fallback_name,
    function_block_identifier,
)


def test_function_block_identifier_from_oid():
    assert function_block_identifier("entry1", "1/15/0/2/10/0") == "entry1_fb_1_15_0"


def test_function_block_fallback_name_uses_group():
    dp = {"oid": "1/15/0/2/10/0", "group": "central", "fct_type": 15}
    name = function_block_fallback_name(dp)
    assert "Central" in name or "Buffer" in name or name


def test_function_block_device_info_links_hub():
    dp = {
        "oid": "1/65/0/0/0/0",
        "hint_node": "LogWIN",
        "group": "boiler",
        "fct_type": 10,
    }
    info = build_function_block_device_info(
        "entry1",
        dp,
        sw_version="1.2.3",
        model="BioWIN",
    )
    assert info["identifiers"] == {(DOMAIN, "entry1_fb_1_65_0")}
    assert info["via_device"] == (DOMAIN, "entry1")
    assert info["sw_version"] == "1.2.3"
    assert info["model"] == "BioWIN"


def test_function_block_fallback_name_uses_configured_node_name():
    dp = {
        "oid": "1/65/0/0/0/0",
        "hint_node": "LogWIN",
        "group": "boiler",
        "fct_type": 10,
        "function_name": "Kessel",
    }
    name = function_block_fallback_name(dp, node_names={"1/65": "Hauptkessel"})
    assert name == "Hauptkessel Kessel"


def test_function_block_device_info_uses_configured_node_name_for_display():
    dp = {
        "oid": "1/65/0/0/0/0",
        "hint_node": "LogWIN",
        "group": "boiler",
        "fct_type": 10,
        "function_name": "Kessel",
    }
    info = build_function_block_device_info(
        "entry1",
        dp,
        node_names={"1/65": "Hauptkessel"},
    )
    assert info["name"] == "Hauptkessel Kessel"
    # Identifier must remain OID-based, never include the configured name
    assert info["identifiers"] == {(DOMAIN, "entry1_fb_1_65_0")}


def test_function_block_fallback_name_skips_placeholder_node_name():
    dp = {
        "oid": "1/65/0/0/0/0",
        "hint_node": "LogWIN",
        "group": "boiler",
        "fct_type": 10,
    }
    name = function_block_fallback_name(dp, node_names={"1/65": "node_65"})
    assert "node_65" not in name
    assert "Boiler" in name
