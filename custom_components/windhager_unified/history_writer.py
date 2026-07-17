"""Coordinator-driven archive writer for Windhager history.

Subscribes to successful coordinator updates and writes eligible datapoints to
the integration-owned SQLite archive. Uses YAML semantic metadata to decide when
to write and how to deduplicate.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    HISTORY_MODE_ALL_MARKED,
    HISTORY_MODE_CRITICAL,
    HISTORY_MODE_HOME_ASSISTANT,
)
from .entity_metadata import (
    HistoryImportance,
    TemporalSemantics,
    parse_datapoint_metadata,
)
from .history_repository import (
    HISTORY_RECORD_QUALITY_UNAVAILABLE,
    HISTORY_RECORD_QUALITY_VALID,
    HistoryRecord,
    LastWriteState,
    WindhagerHistoryRepository,
)

_LOGGER = logging.getLogger(__name__)

_VALUE_TYPE_BOOL = "bool"
_VALUE_TYPE_INT = "int"
_VALUE_TYPE_FLOAT = "float"
_VALUE_TYPE_TIMESTAMP = "timestamp"
_VALUE_TYPE_DATE = "date"
_VALUE_TYPE_TEXT = "text"


class HistoryArchiveWriter:
    """Writes coordinator values to the integration-owned archive.

    The writer is created during config entry setup when an archive mode is
    selected. It ensures datapoint metadata once, then listens to coordinator
    updates and writes records according to the temporal semantics policy.

    Archive failures are isolated: an exception during a write is logged but
    does not break the coordinator update that triggered it.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        repository: WindhagerHistoryRepository,
        config_entry_id: str,
        storage_mode: str,
        sample_interval: int,
    ) -> None:
        self._hass = hass
        self._repository = repository
        self._config_entry_id = config_entry_id
        self._storage_mode = storage_mode
        self._sample_interval = timedelta(seconds=sample_interval)
        self._last_write_states: dict[str, LastWriteState] = {}
        self._started = False
        self._eligible_oids: set[str] = set()

    @property
    def repository(self) -> WindhagerHistoryRepository:
        """Return the underlying repository (used by diagnostics)."""
        return self._repository

    @property
    def storage_mode(self) -> str:
        return self._storage_mode

    @property
    def sample_interval(self) -> int:
        return int(self._sample_interval.total_seconds())

    async def async_start(self, datapoints: list[dict[str, Any]]) -> None:
        """Initialize the writer and restore deduplication state.

        This is called after the coordinator has loaded its catalogue. The
        writer ensures all datapoint metadata rows exist, then reads the latest
        archived record for each eligible datapoint so it can resume correct
        deduplication after a restart.
        """
        if self._storage_mode == HISTORY_MODE_HOME_ASSISTANT:
            return

        self._eligible_oids = self._select_eligible_oids(datapoints)
        eligible_datapoints = [
            dp for dp in datapoints if str(dp.get("oid", "")) in self._eligible_oids
        ]
        if not eligible_datapoints:
            self._started = True
            return

        await self._repository.async_ensure_datapoints(eligible_datapoints)
        self._last_write_states = await self._repository.async_get_last_write_states(
            list(self._eligible_oids)
        )
        self._started = True
        _LOGGER.debug(
            "History archive writer started for %s: %d eligible datapoints, "
            "%d restored write states",
            self._config_entry_id,
            len(self._eligible_oids),
            len(self._last_write_states),
        )

    async def async_stop(self) -> None:
        """Stop the writer and clear transient state."""
        self._started = False
        self._last_write_states.clear()
        self._eligible_oids.clear()

    async def async_process_update(
        self,
        data: dict[str, Any],
        datapoints: list[dict[str, Any]],
    ) -> None:
        """Process a successful coordinator update and write eligible records.

        This is called from a coordinator listener. It must be fast and never
        raise: the coordinator update is committed to HA state regardless of
        archive success.
        """
        if not self._started or self._storage_mode == HISTORY_MODE_HOME_ASSISTANT:
            return

        if not data:
            return

        # Ensure any newly eligible datapoints (e.g. after options change) have
        # metadata rows. This is a no-op for existing rows.
        eligible_datapoints = [
            dp for dp in datapoints if str(dp.get("oid", "")) in self._eligible_oids
        ]
        if not eligible_datapoints:
            return
        await self._repository.async_ensure_datapoints(eligible_datapoints)

        records: list[HistoryRecord] = []
        now = datetime.now(UTC)

        for dp in eligible_datapoints:
            oid = str(dp.get("oid", ""))
            key = str(dp.get("key", ""))
            raw_value = data.get(key)
            meta = parse_datapoint_metadata(dp)
            record = self._build_record(oid, now, raw_value)
            last = self._last_write_states.get(oid)

            if self._should_write(record, last, meta.temporal_semantics):
                records.append(record)
                self._last_write_states[oid] = LastWriteState(
                    observed_at_utc=record.observed_at_utc,
                    numeric_value=record.numeric_value,
                    text_value=record.text_value,
                    quality=record.quality,
                    available=record.available,
                )

        if records:
            try:
                await self._repository.async_record_batch(records)
            except Exception as err:
                # Failure is isolated: the coordinator already updated HA state.
                _LOGGER.error("History archive write failed: %s", err)

    def _select_eligible_oids(self, datapoints: list[dict[str, Any]]) -> set[str]:
        """Return the OIDs that are eligible under the current storage mode."""
        if self._storage_mode == HISTORY_MODE_HOME_ASSISTANT:
            return set()

        eligible: set[str] = set()
        for dp in datapoints:
            meta = parse_datapoint_metadata(dp)
            if not meta.history_importance_explicit:
                # Explicit YAML marking required. A missing key is not eligible
                # even though the parser defaults to STANDARD.
                continue
            if (
                self._storage_mode == HISTORY_MODE_CRITICAL
                and meta.history_importance is HistoryImportance.CRITICAL
            ) or (
                self._storage_mode == HISTORY_MODE_ALL_MARKED
                and meta.history_importance
                in (
                    HistoryImportance.CRITICAL,
                    HistoryImportance.STANDARD,
                    HistoryImportance.LOW,
                )
            ):
                eligible.add(str(dp.get("oid", "")))
        return eligible

    def _build_record(self, oid: str, observed_at: datetime, raw_value: Any) -> HistoryRecord:
        """Convert a coordinator value into a typed HistoryRecord."""
        if raw_value is None:
            return HistoryRecord(
                oid=oid,
                observed_at_utc=observed_at,
                numeric_value=None,
                text_value=None,
                value_type=_VALUE_TYPE_TEXT,
                quality=HISTORY_RECORD_QUALITY_UNAVAILABLE,
                available=False,
            )

        if isinstance(raw_value, bool):
            return HistoryRecord(
                oid=oid,
                observed_at_utc=observed_at,
                numeric_value=float(raw_value),
                text_value="true" if raw_value else "false",
                value_type=_VALUE_TYPE_BOOL,
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )

        if isinstance(raw_value, int):
            return HistoryRecord(
                oid=oid,
                observed_at_utc=observed_at,
                numeric_value=float(raw_value),
                text_value=str(raw_value),
                value_type=_VALUE_TYPE_INT,
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )

        if isinstance(raw_value, float):
            return HistoryRecord(
                oid=oid,
                observed_at_utc=observed_at,
                numeric_value=raw_value,
                text_value=str(raw_value),
                value_type=_VALUE_TYPE_FLOAT,
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )

        if isinstance(raw_value, datetime):
            return HistoryRecord(
                oid=oid,
                observed_at_utc=observed_at,
                numeric_value=None,
                text_value=raw_value.isoformat(),
                value_type=_VALUE_TYPE_TIMESTAMP,
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )

        # date object is handled separately because datetime is a subclass of date
        if type(raw_value).__name__ == "date":
            return HistoryRecord(
                oid=oid,
                observed_at_utc=observed_at,
                numeric_value=None,
                text_value=raw_value.isoformat(),
                value_type=_VALUE_TYPE_DATE,
                quality=HISTORY_RECORD_QUALITY_VALID,
                available=True,
            )

        text = str(raw_value)
        return HistoryRecord(
            oid=oid,
            observed_at_utc=observed_at,
            numeric_value=None,
            text_value=text,
            value_type=_VALUE_TYPE_TEXT,
            quality=HISTORY_RECORD_QUALITY_VALID,
            available=True,
        )

    def _should_write(
        self,
        record: HistoryRecord,
        last: LastWriteState | None,
        temporal_semantics: TemporalSemantics,
    ) -> bool:
        """Apply the temporal-semantics write policy to a candidate record."""
        if temporal_semantics is TemporalSemantics.NONE:
            return False

        if last is None:
            # First observation for this datapoint.
            return True

        # Availability transitions are always recorded immediately.
        if record.available != last.available:
            return True
        if record.quality != last.quality:
            return True

        if temporal_semantics is TemporalSemantics.SAMPLED:
            # Record at the configured interval when available. Do not store
            # repeated unavailable samples on every poll.
            if not record.available:
                return False
            elapsed = record.observed_at_utc - last.observed_at_utc
            return elapsed >= self._sample_interval

        # step, event, counter, snapshot: write only when the effective value changes.
        return not self._values_equal(record, last)

    @staticmethod
    def _values_equal(record: HistoryRecord, last: LastWriteState) -> bool:
        """Return True if the record and last state represent the same value."""
        if record.numeric_value is not None and last.numeric_value is not None:
            return record.numeric_value == last.numeric_value
        if record.text_value is not None and last.text_value is not None:
            return record.text_value == last.text_value
        # Mixed types (e.g. one numeric and one text) are compared via text.
        return str(record.text_value) == str(last.text_value)
