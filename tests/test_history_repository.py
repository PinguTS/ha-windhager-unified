"""Tests for the integration-owned SQLite history archive repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.windhager_unified.history_repository import (
    HISTORY_RECORD_QUALITY_UNAVAILABLE,
    HISTORY_RECORD_QUALITY_VALID,
    HistoryRecord,
    WindhagerHistoryRepository,
)


class _FakeHass:
    """Minimal Home Assistant stand-in that runs executor jobs in the test thread."""

    async def async_add_executor_job(self, target, *args):
        return target(*args)


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test.sqlite"


@pytest.fixture
def repo(tmp_db):
    hass = _FakeHass()
    return WindhagerHistoryRepository(
        hass=hass,
        database_path=tmp_db,
        config_entry_id="test-entry",
    )


async def test_repository_initializes_schema(repo, tmp_db):
    assert not tmp_db.exists()
    await repo.async_initialize()
    assert tmp_db.exists()
    await repo.async_close()


async def test_ensure_and_query_records(repo, tmp_db):
    await repo.async_initialize()
    datapoints = [
        {
            "oid": "1/15/0/0/0/0",
            "key": "outdoor_temp",
            "function_name": "UMUMLZ",
            "group": "central",
            "unit": "°C",
            "device_class": "temperature",
            "data_role": "measurement",
            "temporal_semantics": "sampled",
            "model_role": "feature",
            "history_importance": "critical",
        }
    ]
    await repo.async_ensure_datapoints(datapoints)

    now = datetime.now(UTC)
    records = [
        HistoryRecord(
            oid="1/15/0/0/0/0",
            observed_at_utc=now,
            numeric_value=21.5,
            text_value="21.5",
            value_type="float",
            quality=HISTORY_RECORD_QUALITY_VALID,
            available=True,
        )
    ]
    await repo.async_record_batch(records)

    rows = await repo.async_query(
        "1/15/0/0/0/0",
        now - timedelta(seconds=1),
        now + timedelta(seconds=1),
    )
    assert len(rows) == 1
    assert rows[0].numeric_value == 21.5
    await repo.async_close()


async def test_query_returns_empty_for_unknown_oid(repo):
    await repo.async_initialize()
    rows = await repo.async_query(
        "1/1/1/1/1/1",
        datetime.now(UTC) - timedelta(hours=1),
        datetime.now(UTC),
    )
    assert rows == []
    await repo.async_close()


async def test_last_write_state_restored(repo):
    await repo.async_initialize()
    datapoints = [
        {
            "oid": "1/15/0/0/0/0",
            "key": "outdoor_temp",
            "data_role": "measurement",
            "temporal_semantics": "sampled",
        }
    ]
    await repo.async_ensure_datapoints(datapoints)

    now = datetime.now(UTC)
    await repo.async_record_batch(
        [
            HistoryRecord(
                oid="1/15/0/0/0/0",
                observed_at_utc=now,
                numeric_value=10.0,
                text_value="10.0",
                value_type="float",
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )
        ]
    )

    states = await repo.async_get_last_write_states(["1/15/0/0/0/0"])
    assert "1/15/0/0/0/0" in states
    assert states["1/15/0/0/0/0"].numeric_value == 10.0
    await repo.async_close()


async def test_cleanup_deletes_old_records(repo):
    await repo.async_initialize()
    datapoints = [
        {
            "oid": "1/15/0/0/0/0",
            "key": "outdoor_temp",
            "data_role": "measurement",
            "temporal_semantics": "sampled",
        }
    ]
    await repo.async_ensure_datapoints(datapoints)

    old = datetime.now(UTC) - timedelta(days=40)
    recent = datetime.now(UTC) - timedelta(days=1)
    await repo.async_record_batch(
        [
            HistoryRecord(
                oid="1/15/0/0/0/0",
                observed_at_utc=old,
                numeric_value=1.0,
                text_value="1.0",
                value_type="float",
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            ),
            HistoryRecord(
                oid="1/15/0/0/0/0",
                observed_at_utc=recent,
                numeric_value=2.0,
                text_value="2.0",
                value_type="float",
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            ),
        ]
    )

    await repo.async_cleanup(30)
    rows = await repo.async_query(
        "1/15/0/0/0/0",
        datetime.now(UTC) - timedelta(days=50),
        datetime.now(UTC),
    )
    assert len(rows) == 1
    assert rows[0].numeric_value == 2.0
    await repo.async_close()


async def test_cleanup_no_retention_days_keeps_everything(repo):
    await repo.async_initialize()
    datapoints = [
        {
            "oid": "1/15/0/0/0/0",
            "key": "outdoor_temp",
            "data_role": "measurement",
            "temporal_semantics": "sampled",
        }
    ]
    await repo.async_ensure_datapoints(datapoints)

    old = datetime.now(UTC) - timedelta(days=100)
    await repo.async_record_batch(
        [
            HistoryRecord(
                oid="1/15/0/0/0/0",
                observed_at_utc=old,
                numeric_value=1.0,
                text_value="1.0",
                value_type="float",
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )
        ]
    )

    await repo.async_cleanup(0)
    rows = await repo.async_query(
        "1/15/0/0/0/0",
        datetime.now(UTC) - timedelta(days=200),
        datetime.now(UTC),
    )
    assert len(rows) == 1
    await repo.async_close()


async def test_archive_info(repo, tmp_db):
    await repo.async_initialize()
    datapoints = [
        {
            "oid": "1/15/0/0/0/0",
            "key": "outdoor_temp",
            "data_role": "measurement",
            "temporal_semantics": "sampled",
        }
    ]
    await repo.async_ensure_datapoints(datapoints)
    now = datetime.now(UTC)
    await repo.async_record_batch(
        [
            HistoryRecord(
                oid="1/15/0/0/0/0",
                observed_at_utc=now,
                numeric_value=1.0,
                text_value="1.0",
                value_type="float",
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )
        ]
    )

    info = await repo.async_get_archive_info(eligible_datapoints=1)
    assert info.schema_version == 1
    assert info.row_count == 1
    assert info.archived_datapoint_count == 1
    assert info.eligible_datapoint_count == 1
    assert info.database_path == str(tmp_db)
    assert info.last_error is None
    await repo.async_close()


async def test_unavailable_records_stored(repo):
    await repo.async_initialize()
    datapoints = [
        {
            "oid": "1/15/0/0/0/0",
            "key": "outdoor_temp",
            "data_role": "measurement",
            "temporal_semantics": "sampled",
        }
    ]
    await repo.async_ensure_datapoints(datapoints)
    now = datetime.now(UTC)
    await repo.async_record_batch(
        [
            HistoryRecord(
                oid="1/15/0/0/0/0",
                observed_at_utc=now,
                numeric_value=None,
                text_value=None,
                value_type="text",
                quality=HISTORY_RECORD_QUALITY_UNAVAILABLE,
                available=False,
            )
        ]
    )

    rows = await repo.async_query(
        "1/15/0/0/0/0",
        now - timedelta(seconds=1),
        now + timedelta(seconds=1),
    )
    assert len(rows) == 1
    assert rows[0].available is False
    assert rows[0].numeric_value is None
    await repo.async_close()


async def test_closed_repository_returns_empty_info(repo):
    await repo.async_initialize()
    await repo.async_close()
    info = await repo.async_get_archive_info()
    assert info.schema_version == 0
    assert info.row_count == 0
