"""Tests for entity registry migration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.windhager_unified.const import DOMAIN
from custom_components.windhager_unified.migrate import async_migrate_entry


@pytest.mark.asyncio
async def test_migrate_removes_stale_control_sensors(hass):
    entry = MagicMock()
    entry.version = 1
    entry.entry_id = "test_entry"
    entry.data = {"host": "http://test-host"}

    registry = er.async_get(hass)
    stale = registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="deadbeef",
        config_entry=entry,
    )

    with (
        patch(
            "custom_components.windhager_unified.migrate._control_unique_ids",
            return_value={"deadbeef"},
        ),
        patch.object(
            hass.config_entries,
            "async_update_entry",
        ) as mock_update,
    ):
        assert await async_migrate_entry(hass, entry) is True

    assert registry.async_get(stale.entity_id) is None
    mock_update.assert_called_once()
    assert mock_update.call_args.kwargs.get("version") == 2
