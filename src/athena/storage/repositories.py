"""Domain-specific repository interfaces.

Each Protocol here extends the generic ``RepositoryProtocol`` with
domain-specific query methods for the entities managed by the Data Engine.

Scope of this module (Sprint 3):
    Only the Data Engine's storage interfaces are defined here. Trading Engine
    (order/position ledgers) and Governance Engine (audit log) repositories
    will be added in their respective sprints.

Import note:
    This module imports domain types from ``athena.core.domain`` because
    the Data Engine entities are the stored objects. The storage layer is
    permitted to import from ``athena.core``; the dependency runs one way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from athena.core.domain.instrument import Exchange, Instrument, Segment
    from athena.core.domain.ohlcv import OHLCV, BarInterval
    from athena.core.domain.primitives import Symbol
    from athena.core.domain.tick import Tick
    from athena.storage.models import Page, QuerySpec, StorageKey


@runtime_checkable
class InstrumentRepositoryProtocol(Protocol):
    """Storage interface for the instrument master.

    The instrument master is a reference dataset loaded at startup. It is
    read far more often than it is written. Implementations are expected
    to cache aggressively — a local in-memory cache backed by TimescaleDB
    is the standard pattern.

    Note:
        This protocol defines storage operations for instruments. The
        ``InstrumentRepositoryPort`` in ``athena.core.ports`` defines the
        runtime query interface used by engines. The two are complementary:
        this module defines HOW instruments are stored; the core port defines
        HOW engines access them.
    """

    async def get_instrument(self, symbol: Symbol) -> Instrument:
        """Return the ``Instrument`` for the given symbol.

        Args:
            symbol: Fully-qualified instrument symbol (e.g.
                ``Symbol("NSE:NIFTY50-INDEX")``).

        Returns:
            The matching ``Instrument``.

        Raises:
            RecordNotFoundError: If the symbol is not in the master.
        """
        ...

    async def get_instrument_or_none(self, symbol: Symbol) -> Instrument | None:
        """Return the ``Instrument`` for the given symbol, or ``None``.

        Args:
            symbol: Fully-qualified instrument symbol.

        Returns:
            The matching ``Instrument``, or ``None`` if not found.
        """
        ...

    async def find_instruments(
        self,
        exchange: Exchange | None = None,
        segment: Segment | None = None,
        spec: QuerySpec | None = None,
    ) -> Page[Instrument]:
        """Return instruments matching the given criteria.

        Args:
            exchange: Optional filter by exchange (``NSE``, ``BSE``, etc.).
            segment:  Optional filter by segment (``INDEX``, ``FUT``, etc.).
            spec:     Optional additional filters and pagination.

        Returns:
            A paginated list of matching ``Instrument`` objects.
        """
        ...

    async def upsert_instrument(self, instrument: Instrument) -> StorageKey:
        """Insert or update an instrument in the master.

        Upsert semantics: if an instrument with the same symbol already
        exists, its fields are replaced. This is the standard update path
        for daily instrument-master refreshes.

        Args:
            instrument: The instrument to persist.

        Returns:
            The ``StorageKey`` for the record.
        """
        ...

    async def upsert_many(self, instruments: list[Instrument]) -> int:
        """Bulk upsert instruments. Returns the number of records affected.

        Args:
            instruments: List of instruments to persist.

        Returns:
            Total number of records inserted or updated.
        """
        ...

    async def count_instruments(
        self,
        exchange: Exchange | None = None,
        segment: Segment | None = None,
    ) -> int:
        """Return the total count of instruments matching the given criteria.

        Args:
            exchange: Optional exchange filter.
            segment:  Optional segment filter.

        Returns:
            Total count of matching instruments.
        """
        ...


@runtime_checkable
class TickRepositoryProtocol(Protocol):
    """Storage interface for raw market tick data.

    Ticks are the highest-resolution market data in Athena. Implementations
    are expected to use a time-series-optimised backend (TimescaleDB hypertable
    or Parquet partitioned by date) to support efficient range queries and
    bulk inserts at market data rates.

    Key design decisions:
        - Ticks are immutable once stored. There is no ``update`` method.
        - Bulk insert (``add_ticks``) is the primary write path — individual
          tick inserts would be too slow at NSE tick rates.
        - Range queries always require a symbol. Unbounded cross-symbol queries
          are not supported to prevent accidental full-table scans.
    """

    async def get_tick(self, symbol: Symbol, timestamp_utc: datetime) -> Tick:
        """Return the tick for the given symbol and exact timestamp.

        Args:
            symbol:        Instrument symbol.
            timestamp_utc: Exact UTC timestamp (timezone-aware).

        Returns:
            The matching ``Tick``.

        Raises:
            RecordNotFoundError: If no tick exists at that exact timestamp.
        """
        ...

    async def get_latest_tick(self, symbol: Symbol) -> Tick | None:
        """Return the most recent tick for the given symbol.

        Args:
            symbol: Instrument symbol.

        Returns:
            The most recent ``Tick``, or ``None`` if no ticks exist.
        """
        ...

    async def find_ticks(
        self,
        symbol: Symbol,
        from_utc: datetime,
        to_utc: datetime,
        spec: QuerySpec | None = None,
    ) -> Page[Tick]:
        """Return ticks in the time range ``[from_utc, to_utc)``.

        Args:
            symbol:   Instrument symbol.
            from_utc: Inclusive lower bound (timezone-aware).
            to_utc:   Exclusive upper bound (timezone-aware).
            spec:     Optional pagination and sort specification.

        Returns:
            A paginated page of ``Tick`` objects in ascending timestamp order.

        Raises:
            QueryError: If the time range is invalid or datetimes are naive.
        """
        ...

    async def add_tick(self, tick: Tick) -> StorageKey:
        """Persist a single tick.

        For high-throughput ingestion, prefer ``add_ticks`` to amortise
        I/O overhead across many records.

        Args:
            tick: The ``Tick`` to persist.

        Returns:
            The assigned ``StorageKey``.
        """
        ...

    async def add_ticks(self, ticks: list[Tick]) -> int:
        """Bulk-persist a batch of ticks. Returns the number stored.

        Implementations should use the most efficient bulk-insert path
        available for the backend (COPY for PostgreSQL, Parquet batch write,
        Arrow RecordBatch insert, etc.).

        Args:
            ticks: Batch of ``Tick`` objects to persist.

        Returns:
            The number of ticks successfully stored.
        """
        ...

    async def delete_ticks_before(self, symbol: Symbol, cutoff_utc: datetime) -> int:
        """Delete all ticks for the given symbol before the cutoff timestamp.

        Used for time-to-live retention policies on high-volume symbols.

        Args:
            symbol:     Instrument symbol to purge ticks for.
            cutoff_utc: Exclusive upper bound for deletion (timezone-aware).

        Returns:
            The number of ticks deleted.
        """
        ...

    async def count_ticks(
        self,
        symbol: Symbol,
        from_utc: datetime | None = None,
        to_utc: datetime | None = None,
    ) -> int:
        """Count ticks for a symbol, optionally within a time range.

        Args:
            symbol:   Instrument symbol.
            from_utc: Optional inclusive lower bound.
            to_utc:   Optional exclusive upper bound.

        Returns:
            Total count of matching tick records.
        """
        ...


@runtime_checkable
class OHLCVRepositoryProtocol(Protocol):
    """Storage interface for OHLCV bar data.

    OHLCV bars are aggregated from ticks by the Data Engine's aggregator.
    They are stored at multiple resolutions (1-minute, 5-minute, 1-hour,
    daily) and queried heavily by the Research Engine for backtesting.

    Immutability constraint:
        Closed bars are immutable. Once a bar is stored, its OHLCV values
        never change. The ``add`` methods are idempotent — storing the same
        bar twice silently succeeds (deduplication on primary key).
    """

    async def get_bar(
        self,
        symbol: Symbol,
        interval: BarInterval,
        open_time_utc: datetime,
    ) -> OHLCV:
        """Return the bar for the given symbol, interval, and open timestamp.

        Args:
            symbol:        Instrument symbol.
            interval:      Bar duration (e.g. ``BarInterval.ONE_MINUTE``).
            open_time_utc: The bar's open timestamp (timezone-aware).

        Returns:
            The matching ``OHLCV`` bar.

        Raises:
            RecordNotFoundError: If no bar exists for the given key.
        """
        ...

    async def find_bars(
        self,
        symbol: Symbol,
        interval: BarInterval,
        from_utc: datetime,
        to_utc: datetime,
        spec: QuerySpec | None = None,
    ) -> Page[OHLCV]:
        """Return OHLCV bars in the time range ``[from_utc, to_utc)``.

        Args:
            symbol:   Instrument symbol.
            interval: Bar resolution.
            from_utc: Inclusive lower bound on ``open_time`` (timezone-aware).
            to_utc:   Exclusive upper bound on ``open_time`` (timezone-aware).
            spec:     Optional pagination specification.

        Returns:
            A paginated page of ``OHLCV`` bars in ascending ``open_time`` order.
        """
        ...

    async def get_latest_bar(self, symbol: Symbol, interval: BarInterval) -> OHLCV | None:
        """Return the most recent bar for the given symbol and interval.

        Args:
            symbol:   Instrument symbol.
            interval: Bar resolution.

        Returns:
            The ``OHLCV`` bar with the highest ``open_time``, or ``None``.
        """
        ...

    async def add_bar(self, bar: OHLCV) -> StorageKey:
        """Persist a single OHLCV bar (idempotent).

        Args:
            bar: The ``OHLCV`` bar to persist.

        Returns:
            The ``StorageKey`` for the record.
        """
        ...

    async def add_bars(self, bars: list[OHLCV]) -> int:
        """Bulk-persist a batch of OHLCV bars. Returns the number stored.

        Bars already present in storage (same symbol + interval + open_time)
        are skipped — this method is idempotent per primary key.

        Args:
            bars: Batch of ``OHLCV`` bars to persist.

        Returns:
            The number of bars successfully stored (excluding duplicates).
        """
        ...

    async def count_bars(
        self,
        symbol: Symbol,
        interval: BarInterval,
        from_utc: datetime | None = None,
        to_utc: datetime | None = None,
    ) -> int:
        """Count bars for a symbol and interval, optionally within a time range.

        Args:
            symbol:   Instrument symbol.
            interval: Bar resolution.
            from_utc: Optional inclusive lower bound.
            to_utc:   Optional exclusive upper bound.

        Returns:
            Total count of matching bar records.
        """
        ...

    async def delete_bars_before(
        self,
        symbol: Symbol,
        interval: BarInterval,
        cutoff_utc: datetime,
    ) -> int:
        """Delete bars for a symbol/interval combination before the cutoff.

        Args:
            symbol:     Instrument symbol.
            interval:   Bar resolution.
            cutoff_utc: Exclusive upper bound for deletion (timezone-aware).

        Returns:
            The number of bars deleted.
        """
        ...
