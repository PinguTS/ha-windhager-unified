"""Tests for the history archive writer's temporal semantics and deduplication."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from custom_components.windhager_unified.const import (
    HISTORY_MODE_ALL_MARKED,
    HISTORY_MODE_CRITICAL,
    HISTORY_MODE_HOME_ASSISTANT,
)
from custom_components.windhager_unified.history_repository import WindhagerHistoryRepository
from custom_components.windhager_unified.history_writer import HistoryArchiveWriter


class _FakeHass:
    async def async_add_executor_job(self, target, *args):
        return target(*args)


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "writer.sqlite"


@pytest.fixture
def hass():
    return _FakeHass()


@pytest.fixture
def repo(hass, tmp_db):
    return WindhagerHistoryRepository(
        hass=hass,
        database_path=tmp_db,
        config_entry_id="entry-1",
    )


async def test_home_assistant_mode_does_not_write(hass, repo, tmp_db):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_HOME_ASSISTANT,
        sample_interval=300,
    )
    await writer.async_start([_sampled_dp("1/1/1/1/1/1", "critical")])
    await writer.async_process_update(
        {"key": 42.0},
        [_sampled_dp("1/1/1/1/1/1", "critical")],
    )
    info = await repo.async_get_archive_info()
    assert info.row_count == 0
    await repo.async_close()


async def test_critical_mode_only_archives_explicit_critical(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    dps = [
        _sampled_dp("1/1/0/0/0/0", "critical"),
        _sampled_dp("1/1/0/0/1/0", "standard"),
        _sampled_dp("1/1/0/0/2/0", None),  # omitted -> not explicit
    ]
    await writer.async_start(dps)
    await writer.async_process_update(
        {"key1": 1.0, "key2": 2.0, "key3": 3.0},
        dps,
    )
    rows1 = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    rows2 = await repo.async_query("1/1/0/0/1/0", _past(), _future())
    rows3 = await repo.async_query("1/1/0/0/2/0", _past(), _future())
    assert len(rows1) == 1
    assert len(rows2) == 0
    assert len(rows3) == 0
    await repo.async_close()


async def test_all_marked_mode_excludes_none_and_omitted(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_ALL_MARKED,
        sample_interval=300,
    )
    dps = [
        _sampled_dp("1/1/0/0/0/0", "critical"),
        _sampled_dp("1/1/0/0/1/0", "standard"),
        _sampled_dp("1/1/0/0/2/0", "low"),
        _sampled_dp("1/1/0/0/3/0", "none"),
        _sampled_dp("1/1/0/0/4/0", None),  # omitted
    ]
    await writer.async_start(dps)
    await writer.async_process_update(
        {f"key{i}": float(i) for i in range(5)},
        dps,
    )
    assert len(await repo.async_query("1/1/0/0/0/0", _past(), _future())) == 1
    assert len(await repo.async_query("1/1/0/0/1/0", _past(), _future())) == 1
    assert len(await repo.async_query("1/1/0/0/2/0", _past(), _future())) == 1
    assert len(await repo.async_query("1/1/0/0/3/0", _past(), _future())) == 0
    assert len(await repo.async_query("1/1/0/0/4/0", _past(), _future())) == 0
    await repo.async_close()


async def test_sampled_respects_interval(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    dp = _sampled_dp("1/1/0/0/0/0", "critical")
    await writer.async_start([dp])

    await writer.async_process_update({"key": 1.0}, [dp])
    await writer.async_process_update({"key": 2.0}, [dp])  # inside interval
    await writer.async_process_update({"key": 3.0}, [dp])  # inside interval

    rows = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    assert len(rows) == 1
    assert rows[0].numeric_value == 1.0
    await repo.async_close()


async def test_sampled_writes_after_interval(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=1,
    )
    dp = _sampled_dp("1/1/0/0/0/0", "critical")
    await writer.async_start([dp])
    await writer.async_process_update({"key": 1.0}, [dp])
    await asyncio.sleep(1.1)
    await writer.async_process_update({"key": 2.0}, [dp])
    rows = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    assert len(rows) == 2
    await repo.async_close()


async def test_step_only_writes_on_change(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    dp = _step_dp("1/1/0/0/0/0", "critical")
    await writer.async_start([dp])
    await writer.async_process_update({"key": 20.0}, [dp])
    await writer.async_process_update({"key": 20.0}, [dp])  # unchanged
    await writer.async_process_update({"key": 21.0}, [dp])  # changed
    rows = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    assert len(rows) == 2
    assert rows[0].numeric_value == 20.0
    assert rows[1].numeric_value == 21.0
    await repo.async_close()


async def test_event_records_transitions(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    dp = _event_dp("1/1/0/0/0/0", "critical")
    await writer.async_start([dp])
    await writer.async_process_update({"key": "idle"}, [dp])
    await writer.async_process_update({"key": "idle"}, [dp])
    await writer.async_process_update({"key": "heating"}, [dp])
    await writer.async_process_update({"key": "heating"}, [dp])
    rows = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    assert len(rows) == 2
    assert rows[0].text_value == "idle"
    assert rows[1].text_value == "heating"
    await repo.async_close()


async def test_unavailable_transition_recorded_once(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    dp = _step_dp("1/1/0/0/0/0", "critical")
    await writer.async_start([dp])
    await writer.async_process_update({"key": 20.0}, [dp])
    await writer.async_process_update({"key": None}, [dp])
    await writer.async_process_update({"key": None}, [dp])
    await writer.async_process_update({"key": 22.0}, [dp])
    rows = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    assert len(rows) == 3
    assert rows[0].available is True
    assert rows[1].available is False
    assert rows[2].available is True
    assert rows[2].numeric_value == 22.0
    await repo.async_close()


async def test_restart_restores_deduplication_state(hass, repo):
    await repo.async_initialize()
    writer1 = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    dp = _step_dp("1/1/0/0/0/0", "critical")
    await writer1.async_start([dp])
    await writer1.async_process_update({"key": 20.0}, [dp])
    await writer1.async_stop()

    # Simulate restart by creating a new writer over the same repository.
    writer2 = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    await writer2.async_start([dp])
    await writer2.async_process_update({"key": 20.0}, [dp])  # same as last -> no write
    await writer2.async_process_update({"key": 21.0}, [dp])  # changed -> write
    rows = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    assert len(rows) == 2
    await repo.async_close()


async def test_failure_isolated(hass, repo):
    await repo.async_initialize()
    writer = HistoryArchiveWriter(
        hass=hass,
        repository=repo,
        config_entry_id="entry-1",
        storage_mode=HISTORY_MODE_CRITICAL,
        sample_interval=300,
    )
    dp = _sampled_dp("1/1/0/0/0/0", "critical")
    await writer.async_start([dp])
    # Simulate a coordinator update where the datapoint's key is missing from the
    # data. The writer should not raise; it stores an unavailable record because
    # this is the first observation for that datapoint.
    await writer.async_process_update({"other_key": 1.0}, [dp])
    info = await repo.async_get_archive_info()
    rows = await repo.async_query("1/1/0/0/0/0", _past(), _future())
    assert info.row_count == 1
    assert len(rows) == 1
    assert rows[0].available is False
    assert rows[0].quality == "unavailable"
    await repo.async_close()


def _sampled_dp(oid: str, importance: str | None) -> dict[str, Any]:
    dp = {
        "oid": oid,
        "key": "key",
        "data_role": "measurement",
        "temporal_semantics": "sampled",
        "model_role": "feature",
    }
    if importance is not None:
        dp["history_importance"] = importance
    return dp


def _step_dp(oid: str, importance: str | None) -> dict[str, Any]:
    dp = {
        "oid": oid,
        "key": "key",
        "data_role": "setpoint",
        "temporal_semantics": "step",
        "model_role": "control",
    }
    if importance is not None:
        dp["history_importance"] = importance
    return dp


def _event_dp(oid: str, importance: str | None) -> dict[str, Any]:
    dp = {
        "oid": oid,
        "key": "key",
        "data_role": "operating_state",
        "temporal_semantics": "event",
        "model_role": "event",
    }
    if importance is not None:
        dp["history_importance"] = importance
    return dp


def _past():
    return datetime.now(UTC) - timedelta(hours=1)


def _future():
    return datetime.now(UTC) + timedelta(hours=1)
