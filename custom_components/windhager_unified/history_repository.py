"""Integration-owned SQLite archive for Windhager model history.

This module intentionally does not touch Home Assistant Recorder tables or
configuration. All blocking database work is dispatched to a Home Assistant
executor so the event loop is never blocked by SQLite I/O.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

_SCHEMA_VERSION: Final[int] = 1
_ISO_FMT: Final[str] = "%Y-%m-%dT%H:%M:%S.%fZ"

HISTORY_RECORD_QUALITY_VALID = "valid"
HISTORY_RECORD_QUALITY_UNAVAILABLE = "unavailable"
HISTORY_RECORD_QUALITY_UNKNOWN = "unknown"
HISTORY_RECORD_QUALITY_INVALID = "invalid"
HISTORY_RECORD_QUALITY_STALE = "stale"


@dataclass(frozen=True)
class HistoryRecord:
    """One observation to be stored in the archive."""

    oid: str
    observed_at_utc: datetime
    numeric_value: float | None
    text_value: str | None
    value_type: str
    quality: str = HISTORY_RECORD_QUALITY_VALID
    available: bool = True


@dataclass(frozen=True)
class ArchiveInfo:
    """Snapshot of archive health and contents."""

    database_path: str
    schema_version: int
    size_bytes: int
    row_count: int
    oldest_timestamp: datetime | None
    newest_timestamp: datetime | None
    last_successful_write: datetime | None
    last_error: str | None
    eligible_datapoint_count: int
    archived_datapoint_count: int


@dataclass(frozen=True)
class LastWriteState:
    """Deduplication state for a single datapoint."""

    observed_at_utc: datetime
    numeric_value: float | None
    text_value: str | None
    quality: str
    available: bool


@dataclass
class _BatchInsert:
    """Internal container for a batch write."""

    records: list[HistoryRecord]
    datapoint_ids: dict[str, int]


class WindhagerHistoryRepository:
    """SQLite-backed archive for Windhager datapoint history.

    The repository runs all blocking I/O on the Home Assistant executor. It is
    safe to call from async code but must be closed via ``async_close`` before
    the config entry is unloaded.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        database_path: Path,
        config_entry_id: str,
    ) -> None:
        self._hass = hass
        self._database_path = Path(database_path)
        self._config_entry_id = config_entry_id
        self._connection: sqlite3.Connection | None = None
        self._last_error: str | None = None
        self._last_successful_write: datetime | None = None
        self._closed = False

    @property
    def database_path(self) -> Path:
        """Return the resolved SQLite file path."""
        return self._database_path

    async def async_initialize(self) -> None:
        """Open the database and ensure the schema is current."""
        if self._closed:
            raise RuntimeError("Repository is closed")
        self._connection = await self._hass.async_add_executor_job(self._init_database_sync)

    def _init_database_sync(self) -> sqlite3.Connection:
        """Blocking schema initialization."""
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._database_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")

        # Schema version table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
            """)
        current_version = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        version = current_version[0] if current_version else None

        if version is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (_SCHEMA_VERSION,))
        elif version != _SCHEMA_VERSION:
            # Future migrations go here. For now, bumping the version without a
            # migration script is an error; we refuse to write to an unknown
            # schema so the user can fix or purge the archive.
            conn.close()
            raise RuntimeError(
                f"Unsupported archive schema version {version} "
                f"(expected {_SCHEMA_VERSION}). Remove or migrate the archive."
            )

        conn.execute("""
            CREATE TABLE IF NOT EXISTS datapoints (
                id INTEGER PRIMARY KEY,
                config_entry_id TEXT NOT NULL,
                oid TEXT NOT NULL,
                catalogue_key TEXT,
                function_name TEXT,
                group_name TEXT,
                unit TEXT,
                device_class TEXT,
                data_role TEXT,
                temporal_semantics TEXT,
                model_role TEXT,
                history_importance TEXT,
                UNIQUE(config_entry_id, oid)
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY,
                datapoint_id INTEGER NOT NULL,
                observed_at_utc TEXT NOT NULL,
                numeric_value REAL,
                text_value TEXT,
                value_type TEXT NOT NULL,
                quality TEXT,
                available INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(datapoint_id) REFERENCES datapoints(id)
            )
            """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_datapoint_time
            ON history(datapoint_id, observed_at_utc)
            """)
        conn.commit()
        return conn

    async def async_close(self) -> None:
        """Close the database connection."""
        self._closed = True
        if self._connection is not None:
            await self._hass.async_add_executor_job(self._connection.close)
            self._connection = None

    async def async_ensure_datapoints(
        self,
        datapoints: list[dict[str, Any]],
    ) -> dict[str, int]:
        """Insert or update metadata rows and return a map oid -> datapoint_id."""
        if self._closed or self._connection is None:
            raise RuntimeError("Repository not initialized")
        return await self._hass.async_add_executor_job(self._ensure_datapoints_sync, datapoints)

    def _ensure_datapoints_sync(self, datapoints: list[dict[str, Any]]) -> dict[str, int]:
        """Blocking datapoint metadata upsert."""
        result: dict[str, int] = {}
        for dp in datapoints:
            oid = str(dp.get("oid", ""))
            if not oid:
                continue
            row = self._connection.execute(
                "SELECT id FROM datapoints WHERE config_entry_id = ? AND oid = ?",
                (self._config_entry_id, oid),
            ).fetchone()
            if row is None:
                cursor = self._connection.execute(
                    """
                    INSERT INTO datapoints (
                        config_entry_id, oid, catalogue_key, function_name,
                        group_name, unit, device_class, data_role,
                        temporal_semantics, model_role, history_importance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self._config_entry_id,
                        oid,
                        dp.get("key"),
                        dp.get("function_name"),
                        dp.get("group"),
                        dp.get("unit"),
                        dp.get("device_class"),
                        dp.get("data_role"),
                        dp.get("temporal_semantics"),
                        dp.get("model_role"),
                        dp.get("history_importance"),
                    ),
                )
                result[oid] = cursor.lastrowid
            else:
                result[oid] = row[0]
                self._connection.execute(
                    """
                    UPDATE datapoints SET
                        catalogue_key = ?,
                        function_name = ?,
                        group_name = ?,
                        unit = ?,
                        device_class = ?,
                        data_role = ?,
                        temporal_semantics = ?,
                        model_role = ?,
                        history_importance = ?
                    WHERE id = ?
                    """,
                    (
                        dp.get("key"),
                        dp.get("function_name"),
                        dp.get("group"),
                        dp.get("unit"),
                        dp.get("device_class"),
                        dp.get("data_role"),
                        dp.get("temporal_semantics"),
                        dp.get("model_role"),
                        dp.get("history_importance"),
                        row[0],
                    ),
                )
        self._connection.commit()
        return result

    async def async_record_batch(self, records: list[HistoryRecord]) -> None:
        """Write a batch of records to the archive."""
        if not records or self._closed or self._connection is None:
            return
        try:
            await self._hass.async_add_executor_job(self._record_batch_sync, records)
            self._last_successful_write = datetime.now(UTC)
            self._last_error = None
        except Exception as err:
            self._last_error = str(err)
            _LOGGER.error("Failed to write history batch: %s", err)
            raise

    def _record_batch_sync(self, records: list[HistoryRecord]) -> None:
        """Blocking batch insert with metadata lookup."""
        # Build a set of OIDs we need datapoint_id for.
        oids = {r.oid for r in records}
        placeholders = ",".join("?" * len(oids))
        rows = self._connection.execute(
            f"""
            SELECT id, oid FROM datapoints
            WHERE config_entry_id = ? AND oid IN ({placeholders})
            """,
            (self._config_entry_id, *oids),
        ).fetchall()
        datapoint_ids = {row["oid"]: row["id"] for row in rows}

        missing = oids - set(datapoint_ids)
        if missing:
            # This should not happen if ensure_datapoints was called first.
            _LOGGER.warning("Skipping records for unknown datapoints: %s", missing)

        params: list[tuple[int, str, float | None, str | None, str, str, int]] = []
        for r in records:
            dp_id = datapoint_ids.get(r.oid)
            if dp_id is None:
                continue
            params.append(
                (
                    dp_id,
                    r.observed_at_utc.strftime(_ISO_FMT),
                    r.numeric_value,
                    r.text_value,
                    r.value_type,
                    r.quality,
                    1 if r.available else 0,
                )
            )

        if not params:
            return

        self._connection.executemany(
            """
            INSERT INTO history
                (datapoint_id, observed_at_utc, numeric_value, text_value,
                 value_type, quality, available)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            params,
        )
        self._connection.commit()

    async def async_query(
        self,
        oid: str,
        start: datetime,
        end: datetime,
    ) -> list[HistoryRecord]:
        """Return archived records for a single OID in a time range."""
        if self._closed or self._connection is None:
            return []
        return await self._hass.async_add_executor_job(self._query_sync, oid, start, end)

    def _query_sync(self, oid: str, start: datetime, end: datetime) -> list[HistoryRecord]:
        """Blocking query by OID and time range."""
        row = self._connection.execute(
            "SELECT id FROM datapoints WHERE config_entry_id = ? AND oid = ?",
            (self._config_entry_id, oid),
        ).fetchone()
        if row is None:
            return []
        dp_id = row[0]
        rows = self._connection.execute(
            """
            SELECT observed_at_utc, numeric_value, text_value, value_type,
                   quality, available
            FROM history
            WHERE datapoint_id = ? AND observed_at_utc >= ? AND observed_at_utc <= ?
            ORDER BY observed_at_utc
            """,
            (dp_id, start.strftime(_ISO_FMT), end.strftime(_ISO_FMT)),
        ).fetchall()
        return [self._row_to_record(oid, r) for r in rows]

    @staticmethod
    def _row_to_record(oid: str, row: sqlite3.Row) -> HistoryRecord:
        """Convert a SQLite row to a HistoryRecord."""
        return HistoryRecord(
            oid=oid,
            observed_at_utc=datetime.strptime(row["observed_at_utc"], _ISO_FMT).replace(tzinfo=UTC),
            numeric_value=row["numeric_value"],
            text_value=row["text_value"],
            value_type=row["value_type"],
            quality=row["quality"],
            available=bool(row["available"]),
        )

    async def async_get_last_write_states(
        self,
        oids: list[str],
    ) -> dict[str, LastWriteState]:
        """Restore the latest archived record for each OID for deduplication."""
        if not oids or self._closed or self._connection is None:
            return {}
        return await self._hass.async_add_executor_job(self._get_last_write_states_sync, oids)

    def _get_last_write_states_sync(self, oids: list[str]) -> dict[str, LastWriteState]:
        """Blocking query of the latest record per OID."""
        placeholders = ",".join("?" * len(oids))
        rows = self._connection.execute(
            f"""
            SELECT h.datapoint_id, d.oid, h.observed_at_utc, h.numeric_value,
                   h.text_value, h.value_type, h.quality, h.available
            FROM history h
            JOIN datapoints d ON d.id = h.datapoint_id
            WHERE d.config_entry_id = ? AND d.oid IN ({placeholders})
              AND h.id = (
                  SELECT MAX(id) FROM history h2
                  WHERE h2.datapoint_id = h.datapoint_id
              )
            """,
            (self._config_entry_id, *oids),
        ).fetchall()
        return {
            row["oid"]: LastWriteState(
                observed_at_utc=datetime.strptime(row["observed_at_utc"], _ISO_FMT).replace(
                    tzinfo=UTC
                ),
                numeric_value=row["numeric_value"],
                text_value=row["text_value"],
                quality=row["quality"],
                available=bool(row["available"]),
            )
            for row in rows
        }

    async def async_get_archive_info(
        self,
        eligible_datapoints: int | None = None,
    ) -> ArchiveInfo:
        """Return current archive statistics and health."""
        if self._closed or self._connection is None:
            return ArchiveInfo(
                database_path=str(self._database_path),
                schema_version=0,
                size_bytes=0,
                row_count=0,
                oldest_timestamp=None,
                newest_timestamp=None,
                last_successful_write=self._last_successful_write,
                last_error=self._last_error,
                eligible_datapoint_count=eligible_datapoints or 0,
                archived_datapoint_count=0,
            )
        return await self._hass.async_add_executor_job(
            self._get_archive_info_sync, eligible_datapoints
        )

    def _get_archive_info_sync(self, eligible_datapoints: int | None) -> ArchiveInfo:
        """Blocking statistics collection."""
        size_bytes = 0
        with contextlib.suppress(OSError):
            size_bytes = os.path.getsize(self._database_path)

        row_count = self._connection.execute(
            """
            SELECT COUNT(*) FROM history h
            JOIN datapoints d ON d.id = h.datapoint_id
            WHERE d.config_entry_id = ?
            """,
            (self._config_entry_id,),
        ).fetchone()[0]

        ts_row = self._connection.execute(
            """
            SELECT MIN(h.observed_at_utc), MAX(h.observed_at_utc)
            FROM history h
            JOIN datapoints d ON d.id = h.datapoint_id
            WHERE d.config_entry_id = ?
            """,
            (self._config_entry_id,),
        ).fetchone()
        oldest = self._parse_optional_timestamp(ts_row[0])
        newest = self._parse_optional_timestamp(ts_row[1])

        archived_count = self._connection.execute(
            """
            SELECT COUNT(DISTINCT datapoint_id) FROM history h
            JOIN datapoints d ON d.id = h.datapoint_id
            WHERE d.config_entry_id = ?
            """,
            (self._config_entry_id,),
        ).fetchone()[0]

        return ArchiveInfo(
            database_path=str(self._database_path),
            schema_version=_SCHEMA_VERSION,
            size_bytes=size_bytes,
            row_count=row_count,
            oldest_timestamp=oldest,
            newest_timestamp=newest,
            last_successful_write=self._last_successful_write,
            last_error=self._last_error,
            eligible_datapoint_count=eligible_datapoints or 0,
            archived_datapoint_count=archived_count,
        )

    @staticmethod
    def _parse_optional_timestamp(value: str | None) -> datetime | None:
        """Parse an ISO timestamp or return None."""
        if value is None:
            return None
        try:
            return datetime.strptime(value, _ISO_FMT).replace(tzinfo=UTC)
        except ValueError:
            return None

    async def async_cleanup(self, retention_days: int) -> None:
        """Delete records older than the configured retention period."""
        if retention_days <= 0 or self._closed or self._connection is None:
            return
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)
        await self._hass.async_add_executor_job(self._cleanup_sync, cutoff)

    def _cleanup_sync(self, cutoff: datetime) -> None:
        """Blocking deletion of expired records."""
        cursor = self._connection.execute(
            """
            DELETE FROM history
            WHERE observed_at_utc < ?
            AND datapoint_id IN (
                SELECT id FROM datapoints WHERE config_entry_id = ?
            )
            """,
            (cutoff.strftime(_ISO_FMT), self._config_entry_id),
        )
        self._connection.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            _LOGGER.debug("Deleted %d expired history records", deleted)

    async def async_vacuum(self) -> None:
        """Run VACUUM to reclaim disk space. This is expensive and should not be
        called on every cleanup cycle.
        """
        if self._closed or self._connection is None:
            return
        await self._hass.async_add_executor_job(self._vacuum_sync)

    def _vacuum_sync(self) -> None:
        """Blocking vacuum."""
        self._connection.execute("VACUUM")
