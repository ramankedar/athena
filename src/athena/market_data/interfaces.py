"""Service Protocol interfaces for the Market Data Domain.

These Protocols define the structural contracts for market data providers and
repositories. No implementations are provided in this module — concrete
adapters (Fyers WebSocket, NSE historical API, TimescaleDB repository) will
satisfy these protocols via structural subtyping in future sprints.

Three categories of interfaces:

1. **Provider protocols** — fetch data from external vendors:
   - ``HistoricalDataProviderProtocol`` — past OHLCV, ticks, trades, quotes,
     corporate actions.
   - ``LiveDataProviderProtocol`` — real-time tick and quote subscriptions.
   - ``CorporateActionProviderProtocol`` — corporate action events.

2. **Repository protocol** — persist and retrieve market data:
   - ``MarketDataRepositoryProtocol`` — storage-backed data access.

All provider methods are ``async`` because every concrete implementation will
make I/O calls (HTTP, WebSocket, database). Making them sync would force
blocking in async engine contexts.

Integration with Time, Market, Assets, and Storage domains:
    These protocols use ``Symbol``, ``Timeframe``, and market data types
    defined within ``athena.market_data``. They do NOT import from peer layers
    (``athena.time``, ``athena.market``, ``athena.assets``, ``athena.storage``).
    Integration is achieved by engines that wire these protocols to concrete
    implementations from those domains.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import date, datetime

    from athena.core.domain.primitives import Symbol
    from athena.market_data.adjustments import AdjustmentFactor
    from athena.market_data.corporate_actions import CorporateAction
    from athena.market_data.models import Timeframe
    from athena.market_data.ohlcv import OHLCVBar
    from athena.market_data.quotes import Quote
    from athena.market_data.ticks import MarketTick
    from athena.market_data.trades import Trade


@runtime_checkable
class HistoricalDataProviderProtocol(Protocol):
    """Provider of historical market data from an external vendor.

    Implementations connect to a specific data source (Fyers historical API,
    NSE data files, Yahoo Finance, etc.) and translate vendor responses into
    Athena's domain types.

    All methods are ``async`` to support non-blocking I/O in engine contexts.
    """

    @property
    def vendor_name(self) -> str:
        """Name identifier for this data vendor (e.g. ``"fyers"``).

        Returns:
            Lowercase hyphenated vendor name string.
        """
        ...

    @property
    def supported_timeframes(self) -> frozenset[Timeframe]:
        """Set of timeframes this provider can supply.

        Returns:
            Frozenset of supported ``Timeframe`` values.
        """
        ...

    async def fetch_ohlcv(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        from_utc: datetime,
        to_utc: datetime,
    ) -> tuple[OHLCVBar, ...]:
        """Fetch OHLCV bars for a symbol and time range.

        Args:
            symbol:    Instrument symbol.
            timeframe: Bar aggregation period.
            from_utc:  Inclusive range start (timezone-aware UTC).
            to_utc:    Inclusive range end (timezone-aware UTC).

        Returns:
            Ordered tuple of ``OHLCVBar`` objects in ascending ``open_time``.

        Raises:
            ProviderError: If the vendor returns an error response.
        """
        ...

    async def fetch_ticks(
        self,
        symbol: Symbol,
        from_utc: datetime,
        to_utc: datetime,
    ) -> tuple[MarketTick, ...]:
        """Fetch raw ticks for a symbol and time range.

        Args:
            symbol:   Instrument symbol.
            from_utc: Inclusive range start.
            to_utc:   Inclusive range end.

        Returns:
            Ordered tuple of ``MarketTick`` objects in ascending timestamp.
        """
        ...

    async def fetch_trades(
        self,
        symbol: Symbol,
        from_utc: datetime,
        to_utc: datetime,
    ) -> tuple[Trade, ...]:
        """Fetch executed trades for a symbol and time range.

        Args:
            symbol:   Instrument symbol.
            from_utc: Inclusive range start.
            to_utc:   Inclusive range end.

        Returns:
            Ordered tuple of ``Trade`` objects.
        """
        ...

    async def fetch_quotes(
        self,
        symbol: Symbol,
        from_utc: datetime,
        to_utc: datetime,
    ) -> tuple[Quote, ...]:
        """Fetch historical quote snapshots for a symbol and time range.

        Args:
            symbol:   Instrument symbol.
            from_utc: Inclusive range start.
            to_utc:   Inclusive range end.

        Returns:
            Ordered tuple of ``Quote`` objects.
        """
        ...

    async def fetch_corporate_actions(
        self,
        symbol: Symbol,
        from_date: date,
        to_date: date,
    ) -> tuple[CorporateAction, ...]:
        """Fetch corporate actions for a symbol within a date range.

        Args:
            symbol:    Instrument symbol.
            from_date: Inclusive start date.
            to_date:   Inclusive end date.

        Returns:
            Tuple of ``CorporateAction`` objects ordered by ``ex_date``.
        """
        ...


@runtime_checkable
class LiveDataProviderProtocol(Protocol):
    """Provider of real-time (streaming) market data.

    Concrete implementations manage WebSocket connections or exchange-native
    streaming APIs. The protocol defines subscription lifecycle (subscribe,
    unsubscribe) and last-known-state queries.
    """

    @property
    def vendor_name(self) -> str:
        """Name identifier for this data vendor.

        Returns:
            Lowercase hyphenated vendor name string.
        """
        ...

    @property
    def is_connected(self) -> bool:
        """Return ``True`` when the streaming connection is active.

        Returns:
            ``True`` when the provider has an open, authenticated connection.
        """
        ...

    async def subscribe_ticks(self, symbols: frozenset[Symbol]) -> None:
        """Subscribe to real-time tick updates for the given symbols.

        Args:
            symbols: Frozenset of instrument symbols to subscribe.
        """
        ...

    async def subscribe_quotes(self, symbols: frozenset[Symbol]) -> None:
        """Subscribe to real-time quote (bid/ask) updates for the given symbols.

        Args:
            symbols: Frozenset of instrument symbols to subscribe.
        """
        ...

    async def unsubscribe(self, symbols: frozenset[Symbol]) -> None:
        """Unsubscribe from real-time updates for the given symbols.

        Args:
            symbols: Frozenset of instrument symbols to unsubscribe.
        """
        ...

    async def get_subscribed_symbols(self) -> frozenset[Symbol]:
        """Return the set of currently subscribed symbols.

        Returns:
            Frozenset of symbols for which updates are actively received.
        """
        ...

    async def get_latest_quote(self, symbol: Symbol) -> Quote | None:
        """Return the most recently received quote for the symbol.

        Args:
            symbol: Instrument symbol.

        Returns:
            The latest ``Quote``, or ``None`` if no data has arrived yet.
        """
        ...

    async def get_latest_trade(self, symbol: Symbol) -> Trade | None:
        """Return the most recently received trade for the symbol.

        Args:
            symbol: Instrument symbol.

        Returns:
            The latest ``Trade``, or ``None`` if no data has arrived yet.
        """
        ...


@runtime_checkable
class CorporateActionProviderProtocol(Protocol):
    """Provider of corporate action data and computed adjustment factors."""

    @property
    def vendor_name(self) -> str:
        """Name identifier for this provider.

        Returns:
            Lowercase hyphenated vendor name string.
        """
        ...

    async def fetch_corporate_actions(
        self,
        symbol: Symbol,
        from_date: date,
        to_date: date,
    ) -> tuple[CorporateAction, ...]:
        """Fetch corporate actions for a symbol within a date range.

        Args:
            symbol:    Instrument symbol.
            from_date: Inclusive start date.
            to_date:   Inclusive end date.

        Returns:
            Tuple of ``CorporateAction`` objects ordered by ``ex_date``.
        """
        ...

    async def compute_adjustment_factors(
        self,
        symbol: Symbol,
        from_date: date,
        to_date: date,
    ) -> tuple[AdjustmentFactor, ...]:
        """Compute cumulative price adjustment factors for a date range.

        Args:
            symbol:    Instrument symbol.
            from_date: Start date of the adjustment period.
            to_date:   End date of the adjustment period.

        Returns:
            Ordered tuple of ``AdjustmentFactor`` objects by ``effective_date``.
        """
        ...


@runtime_checkable
class MarketDataRepositoryProtocol(Protocol):
    """Storage-backed market data persistence and retrieval.

    Implementations connect to the storage layer (TimescaleDB, Parquet, S3)
    and provide typed access to stored market data. This protocol is
    structurally compatible with ``athena.storage.RepositoryProtocol`` but
    is defined independently to preserve peer-layer isolation.
    """

    async def store_ohlcv_bars(self, bars: tuple[OHLCVBar, ...]) -> int:
        """Persist OHLCV bars. Returns the count of bars stored.

        Args:
            bars: Bars to persist.

        Returns:
            Number of bars actually written (may differ from ``len(bars)``
            when duplicates are skipped).
        """
        ...

    async def fetch_ohlcv_bars(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        from_utc: datetime,
        to_utc: datetime,
    ) -> tuple[OHLCVBar, ...]:
        """Retrieve stored OHLCV bars for a symbol and time range.

        Args:
            symbol:    Instrument symbol.
            timeframe: Bar aggregation period.
            from_utc:  Inclusive start.
            to_utc:    Inclusive end.

        Returns:
            Ordered tuple of ``OHLCVBar`` objects.
        """
        ...

    async def store_ticks(self, ticks: tuple[MarketTick, ...]) -> int:
        """Persist market ticks. Returns the count stored.

        Args:
            ticks: Ticks to persist.

        Returns:
            Count of ticks written.
        """
        ...

    async def fetch_ticks(
        self,
        symbol: Symbol,
        from_utc: datetime,
        to_utc: datetime,
    ) -> tuple[MarketTick, ...]:
        """Retrieve stored ticks for a symbol and time range.

        Args:
            symbol:   Instrument symbol.
            from_utc: Inclusive start.
            to_utc:   Inclusive end.

        Returns:
            Ordered tuple of ``MarketTick`` objects.
        """
        ...

    async def store_corporate_actions(self, actions: tuple[CorporateAction, ...]) -> int:
        """Persist corporate actions. Returns the count stored.

        Args:
            actions: Actions to persist.

        Returns:
            Count of actions written.
        """
        ...

    async def fetch_corporate_actions(
        self,
        symbol: Symbol,
        from_date: date,
        to_date: date,
    ) -> tuple[CorporateAction, ...]:
        """Retrieve stored corporate actions for a symbol.

        Args:
            symbol:    Instrument symbol.
            from_date: Inclusive start date.
            to_date:   Inclusive end date.

        Returns:
            Tuple of ``CorporateAction`` objects ordered by ``ex_date``.
        """
        ...
