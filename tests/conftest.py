"""pytest configuration for ha-windhager-unified tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

_orig_set_time_zone: Any = None


@pytest.fixture
def mock_hass():
    """Minimal mock Home Assistant for coordinator tests."""
    hass = MagicMock()
    hass.loop = MagicMock()
    return hass


def pytest_configure(config: pytest.Config) -> None:
    """Map legacy pytest-ha timezone to a valid IANA zone (Home Assistant 2024+)."""
    global _orig_set_time_zone
    from homeassistant.core import Config

    _orig_set_time_zone = Config.set_time_zone

    def set_time_zone(self: Config, time_zone_str: str) -> None:
        if time_zone_str == "US/Pacific":
            time_zone_str = "America/Los_Angeles"
        return _orig_set_time_zone(self, time_zone_str)

    Config.set_time_zone = set_time_zone  # type: ignore[method-assign]


def pytest_unconfigure(config: pytest.Config) -> None:
    global _orig_set_time_zone
    if _orig_set_time_zone is not None:
        from homeassistant.core import Config

        Config.set_time_zone = _orig_set_time_zone  # type: ignore[method-assign]
        _orig_set_time_zone = None
