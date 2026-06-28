"""Service Protocol interfaces for the Market Domain.

These Protocols define the structural contracts for market-domain services.
No implementations are provided here — concrete implementations satisfy the
protocols via structural subtyping (no inheritance required).

Key design — ``MarketCalendarPort`` decouples Market from Time:
    The Market Domain needs to know whether a given date is a trading day,
    but it cannot import from ``athena.time`` (peer-layer rule). Instead,
    ``MarketCalendarPort`` is defined here, and implementations in
    ``athena.time`` (or future adapters) satisfy it without any import
    crossing from the market side.

Protocol-based integration avoids circular dependencies:
    ``athena.market`` ← defines ``MarketCalendarPort``
    ``athena.time``   ← satisfies ``MarketCalendarPort`` (implements the interface)
    ``athena.engines`` ← wires them together
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import date

    from athena.market.capabilities import MarketCapabilities
    from athena.market.exchange import ExchangeMetadata
    from athena.market.market_state import MarketStateSnapshot
    from athena.market.models import CountryCode, MarketId
    from athena.market.rules import IndexCircuitBreakerConfig, PriceBandConfig, TradingRestriction
    from athena.market.segments import MarketSegment, MarketSegmentType
    from athena.market.sessions import ExchangeSchedule


@runtime_checkable
class ExchangeRepositoryProtocol(Protocol):
    """Read/write repository for ``ExchangeMetadata`` objects.

    The standard implementation is ``InMemoryExchangeRepository`` in
    ``athena.market.exchange``. Database-backed implementations satisfy
    this Protocol via structural subtyping.
    """

    def get(self, exchange_id: MarketId) -> ExchangeMetadata:
        """Return exchange metadata for the given id.

        Args:
            exchange_id: The exchange to retrieve.

        Returns:
            The matching ``ExchangeMetadata``.

        Raises:
            ExchangeNotFoundError: If not registered.
        """
        ...

    def get_or_none(self, exchange_id: MarketId) -> ExchangeMetadata | None:
        """Return exchange metadata or ``None`` if not registered.

        Args:
            exchange_id: The exchange to retrieve.

        Returns:
            The matching ``ExchangeMetadata``, or ``None``.
        """
        ...

    def exists(self, exchange_id: MarketId) -> bool:
        """Return ``True`` if the exchange is registered.

        Args:
            exchange_id: The exchange to check.

        Returns:
            ``True`` when a matching exchange exists.
        """
        ...

    def find_by_country(self, country: CountryCode) -> tuple[ExchangeMetadata, ...]:
        """Return all exchanges in the given country.

        Args:
            country: ISO 3166-1 alpha-2 country code.

        Returns:
            Tuple of matching exchanges (may be empty).
        """
        ...

    def all_exchanges(self) -> tuple[ExchangeMetadata, ...]:
        """Return all registered exchanges.

        Returns:
            Tuple of all registered ``ExchangeMetadata`` objects.
        """
        ...


@runtime_checkable
class SegmentRepositoryProtocol(Protocol):
    """Read/write repository for ``MarketSegment`` objects."""

    def get(self, segment_id: MarketId) -> MarketSegment:
        """Return the segment for the given id.

        Args:
            segment_id: The segment to retrieve.

        Returns:
            The matching ``MarketSegment``.

        Raises:
            SegmentNotFoundError: If not found.
        """
        ...

    def get_or_none(self, segment_id: MarketId) -> MarketSegment | None:
        """Return the segment or ``None`` if not found.

        Args:
            segment_id: The segment to retrieve.

        Returns:
            The matching ``MarketSegment``, or ``None``.
        """
        ...

    def find_by_exchange(self, exchange_id: MarketId) -> tuple[MarketSegment, ...]:
        """Return all segments belonging to the given exchange.

        Args:
            exchange_id: The exchange to filter by.

        Returns:
            Tuple of matching segments.
        """
        ...

    def find_by_type(self, segment_type: MarketSegmentType) -> tuple[MarketSegment, ...]:
        """Return all segments of the given type across all exchanges.

        Args:
            segment_type: The segment type to filter by.

        Returns:
            Tuple of matching segments.
        """
        ...

    def all_segments(self) -> tuple[MarketSegment, ...]:
        """Return all registered segments.

        Returns:
            Tuple of all registered ``MarketSegment`` objects.
        """
        ...


@runtime_checkable
class MarketCalendarPort(Protocol):
    """Port for trading calendar queries — satisfiable by ``athena.time``.

    This is the integration boundary between ``athena.market`` (peer layer)
    and ``athena.time`` (peer layer). The Market Domain defines this Port;
    the Time Domain provides implementations that satisfy it.

    Engines wire the two layers together without either importing from the
    other.
    """

    def is_trading_day(self, exchange_id: MarketId, d: date) -> bool:
        """Return ``True`` if ``d`` is a trading day for the given exchange.

        Args:
            exchange_id: The exchange to query.
            d:           The date to check.

        Returns:
            ``False`` for weekends, exchange holidays, and any date outside
            the exchange's operating calendar.
        """
        ...

    def next_trading_day(self, exchange_id: MarketId, d: date) -> date:
        """Return the first trading day strictly after ``d``.

        Args:
            exchange_id: The exchange to query.
            d:           Reference date.

        Returns:
            The next trading day after ``d``.
        """
        ...

    def previous_trading_day(self, exchange_id: MarketId, d: date) -> date:
        """Return the most recent trading day strictly before ``d``.

        Args:
            exchange_id: The exchange to query.
            d:           Reference date.

        Returns:
            The previous trading day before ``d``.
        """
        ...

    def trading_days_in_range(
        self, exchange_id: MarketId, start: date, end: date
    ) -> tuple[date, ...]:
        """Return all trading days in ``[start, end]`` (both inclusive).

        Args:
            exchange_id: The exchange to query.
            start:       Range start (inclusive).
            end:         Range end (inclusive).

        Returns:
            Ordered tuple of trading dates within the range.
        """
        ...


@runtime_checkable
class MarketStateServiceProtocol(Protocol):
    """Service for querying and transitioning the operational state of a market.

    Future sprint implementations will subscribe to real-time exchange feeds
    and apply circuit breaker rules to maintain accurate state. For now this
    Protocol defines the shape that such services will take.
    """

    def get_state(
        self,
        exchange_id: MarketId,
        segment_id: MarketId | None = None,
    ) -> MarketStateSnapshot:
        """Return the current state snapshot for the exchange or segment.

        Args:
            exchange_id: The exchange to query.
            segment_id:  Optional segment (``None`` = exchange-wide state).

        Returns:
            The most recent ``MarketStateSnapshot``.

        Raises:
            ExchangeNotFoundError: If the exchange is not registered.
        """
        ...

    def is_open(
        self,
        exchange_id: MarketId,
        segment_id: MarketId | None = None,
    ) -> bool:
        """Return ``True`` when the market is in an open, tradable state.

        Args:
            exchange_id: The exchange to query.
            segment_id:  Optional segment.

        Returns:
            ``True`` when ``get_state().state.is_tradable`` is ``True``.
        """
        ...

    def is_halted(
        self,
        exchange_id: MarketId,
        segment_id: MarketId | None = None,
    ) -> bool:
        """Return ``True`` when the market is halted or suspended.

        Args:
            exchange_id: The exchange to query.
            segment_id:  Optional segment.

        Returns:
            ``True`` when state is ``HALTED`` or ``SUSPENDED``.
        """
        ...


@runtime_checkable
class ScheduleRepositoryProtocol(Protocol):
    """Repository for exchange session schedules and market capabilities."""

    def get_schedule(
        self,
        exchange_id: MarketId,
        segment_id: MarketId | None = None,
    ) -> ExchangeSchedule:
        """Return the schedule for the given exchange or segment.

        Args:
            exchange_id: The exchange to query.
            segment_id:  Optional segment (``None`` = exchange-wide default).

        Returns:
            The ``ExchangeSchedule`` for the exchange or segment.

        Raises:
            ExchangeNotFoundError: If no schedule is registered.
        """
        ...

    def get_capabilities(
        self,
        exchange_id: MarketId,
        segment_id: MarketId | None = None,
    ) -> MarketCapabilities:
        """Return the capabilities for the given exchange or segment.

        Args:
            exchange_id: The exchange to query.
            segment_id:  Optional segment.

        Returns:
            The ``MarketCapabilities`` for the exchange or segment.
        """
        ...


@runtime_checkable
class MarketRulesRepositoryProtocol(Protocol):
    """Repository for market rules: price bands and circuit breakers."""

    def get_price_band_config(
        self,
        exchange_id: MarketId,
        instrument_symbol: str | None = None,
    ) -> PriceBandConfig | None:
        """Return the price band config for an exchange or specific instrument.

        Args:
            exchange_id:        The exchange to query.
            instrument_symbol:  Optional specific instrument symbol. ``None``
                returns the default exchange-wide band config.

        Returns:
            The ``PriceBandConfig``, or ``None`` if none is configured.
        """
        ...

    def get_circuit_breaker_config(self, exchange_id: MarketId) -> IndexCircuitBreakerConfig | None:
        """Return the index circuit breaker configuration for the exchange.

        Args:
            exchange_id: The exchange to query.

        Returns:
            The ``IndexCircuitBreakerConfig``, or ``None`` if not configured.
        """
        ...

    def get_restrictions(
        self,
        exchange_id: MarketId,
        d: date,
    ) -> tuple[TradingRestriction, ...]:
        """Return all active trading restrictions on the given date.

        Args:
            exchange_id: The exchange to query.
            d:           The date to check for active restrictions.

        Returns:
            Tuple of active ``TradingRestriction`` objects (may be empty).
        """
        ...
