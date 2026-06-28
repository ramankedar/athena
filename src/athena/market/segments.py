"""Market segment and trading venue value objects.

A financial exchange is subdivided into distinct ``MarketSegment`` objects
that differ in their trading mechanism, settlement cycle, asset class focus,
and regulatory treatment. Within a segment, a ``TradingVenue`` represents the
specific execution platform (main board, dark pool, special call market, etc.).

The three-tier model:
    Exchange   → NSE (the institution)
    Segment    → NSE_FO (Futures & Options segment)
    Venue      → NSE Main (primary continuous-trading venue within NSE_FO)

Segment type design:
    ``MarketSegmentType`` categorises by trading mechanism and settlement,
    not by asset class. NSE_FO trades both equity derivatives AND index
    derivatives — a single asset-class label would be inaccurate.

Settlement cycles:
    Settlement cycle strings follow the standard notation: ``"T+1"`` (next
    business day), ``"T+2"``, ``"Daily"`` (futures daily MTM), or ``"Immediate"``
    (spot FX). These are descriptive labels, not computational objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from athena.market.exceptions import InvalidMarketIdError, SegmentNotFoundError
from athena.market.models import MarketId


class MarketSegmentType(StrEnum):
    """Classification of a market segment by trading mechanism.

    Attributes:
        CASH_EQUITY:           Equity securities with rolling settlement
            (e.g. NSE EQ, BSE A/B groups).
        FUTURES_AND_OPTIONS:   Equity and index derivatives (e.g. NSE F&O, BSE F&O).
        CURRENCY_DERIVATIVES:  FX spot and derivatives (e.g. NSE CDS).
        COMMODITY:             Physical commodity and commodity derivatives
            (e.g. MCX).
        DEBT:                  Fixed income, bonds, and government securities.
        SME:                   Small and Medium Enterprise listing platform
            (e.g. NSE Emerge, BSE SME).
        INSTITUTIONAL:         Institutional-only trading platform.
    """

    CASH_EQUITY = "cash_equity"
    FUTURES_AND_OPTIONS = "futures_and_options"
    CURRENCY_DERIVATIVES = "currency_derivatives"
    COMMODITY = "commodity"
    DEBT = "debt"
    SME = "sme"
    INSTITUTIONAL = "institutional"


@dataclass(frozen=True)
class MarketSegment:
    """An immutable description of a trading segment within an exchange.

    Attributes:
        id:              Segment identifier (e.g. ``MarketId("NSE_FO")``).
        exchange_id:     The exchange this segment belongs to.
        segment_type:    Classification of the segment's trading mechanism.
        name:            Human-readable segment name (e.g. ``"Futures & Options"``).
        settlement_cycle: Settlement notation (e.g. ``"T+1"``, ``"Daily"``).
            ``None`` if not applicable or complex (e.g. derivatives with
            multiple settlement modes).
        description:     Optional extended description of the segment.

    Example::

        nse_fo = MarketSegment(
            id=MarketId("NSE_FO"),
            exchange_id=MarketId("NSE"),
            segment_type=MarketSegmentType.FUTURES_AND_OPTIONS,
            name="Futures and Options",
            settlement_cycle="Daily",
        )
    """

    id: MarketId
    exchange_id: MarketId
    segment_type: MarketSegmentType
    name: str
    settlement_cycle: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidMarketIdError(
                str(self.id),
                reason="MarketSegment.name must not be empty",
            )

    def __str__(self) -> str:
        return f"{self.exchange_id}/{self.id}"

    def __repr__(self) -> str:
        return (
            f"MarketSegment(id={self.id!s}, exchange={self.exchange_id!s}, "
            f"type={self.segment_type.value})"
        )


@dataclass(frozen=True)
class TradingVenue:
    """A specific execution platform or board within an exchange or segment.

    Venues represent the lowest tier in the exchange hierarchy. Most markets
    have a single primary venue per segment, but some have multiple (e.g.
    a dark pool alongside the main lit market).

    Attributes:
        id:               Venue identifier.
        exchange_id:      Parent exchange.
        segment_ids:      Segments this venue services. A venue may span
            multiple segments (e.g. a block deal platform on both equity
            and derivatives segments).
        name:             Human-readable venue name.
        is_primary_venue: ``True`` for the main, lit, continuous market.
            ``False`` for dark pools, special call markets, etc.
        is_dark_pool:     ``True`` when the venue does not display live
            order books (pre-trade opacity).

    Example::

        nse_main = TradingVenue(
            id=MarketId("NSE_MAIN"),
            exchange_id=MarketId("NSE"),
            segment_ids=frozenset({MarketId("NSE_EQ"), MarketId("NSE_FO")}),
            name="NSE Main Board",
            is_primary_venue=True,
        )
    """

    id: MarketId
    exchange_id: MarketId
    name: str
    segment_ids: frozenset[MarketId] = field(default_factory=frozenset)
    is_primary_venue: bool = True
    is_dark_pool: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidMarketIdError(
                str(self.id),
                reason="TradingVenue.name must not be empty",
            )

    def serves_segment(self, segment_id: MarketId) -> bool:
        """Return ``True`` if this venue services the given segment.

        Args:
            segment_id: The segment to check.

        Returns:
            ``True`` when ``segment_id`` is in ``self.segment_ids``.
        """
        return segment_id in self.segment_ids

    def __str__(self) -> str:
        return f"{self.exchange_id}/{self.id}"


# ── Well-known Indian market segments ─────────────────────────────────────────

#: NSE Cash Equity segment (T+1 settlement, NSE EQ).
NSE_EQ: MarketSegment = MarketSegment(
    id=MarketId("NSE_EQ"),
    exchange_id=MarketId("NSE"),
    segment_type=MarketSegmentType.CASH_EQUITY,
    name="NSE Cash Equity",
    settlement_cycle="T+1",
    description="National Stock Exchange equity segment with T+1 rolling settlement.",
)

#: NSE Futures and Options segment (daily MTM, weekly/monthly expiry).
NSE_FO: MarketSegment = MarketSegment(
    id=MarketId("NSE_FO"),
    exchange_id=MarketId("NSE"),
    segment_type=MarketSegmentType.FUTURES_AND_OPTIONS,
    name="NSE Futures and Options",
    settlement_cycle="Daily",
    description="NSE equity and index derivatives with daily mark-to-market settlement.",
)

#: NSE Currency Derivatives segment (USD/INR, EUR/INR, etc.).
NSE_CDS: MarketSegment = MarketSegment(
    id=MarketId("NSE_CDS"),
    exchange_id=MarketId("NSE"),
    segment_type=MarketSegmentType.CURRENCY_DERIVATIVES,
    name="NSE Currency Derivatives",
    settlement_cycle="T+2",
    description="NSE currency futures and options (USD/INR, EUR/INR, GBP/INR, JPY/INR).",
)

#: NSE Emerge SME platform.
NSE_SME: MarketSegment = MarketSegment(
    id=MarketId("NSE_SME"),
    exchange_id=MarketId("NSE"),
    segment_type=MarketSegmentType.SME,
    name="NSE Emerge",
    settlement_cycle="T+1",
    description="NSE Small and Medium Enterprise listing platform.",
)

#: BSE Cash Equity segment.
BSE_EQ: MarketSegment = MarketSegment(
    id=MarketId("BSE_EQ"),
    exchange_id=MarketId("BSE"),
    segment_type=MarketSegmentType.CASH_EQUITY,
    name="BSE Cash Equity",
    settlement_cycle="T+1",
    description="Bombay Stock Exchange equity segment with T+1 rolling settlement.",
)

#: BSE Futures and Options segment (SENSEX, BANKEX derivatives).
BSE_FO: MarketSegment = MarketSegment(
    id=MarketId("BSE_FO"),
    exchange_id=MarketId("BSE"),
    segment_type=MarketSegmentType.FUTURES_AND_OPTIONS,
    name="BSE Futures and Options",
    settlement_cycle="Daily",
    description="BSE equity index derivatives (SENSEX, BANKEX, MIDCAP SELECT).",
)

#: MCX commodity derivatives segment.
MCX_FO: MarketSegment = MarketSegment(
    id=MarketId("MCX_FO"),
    exchange_id=MarketId("MCX"),
    segment_type=MarketSegmentType.COMMODITY,
    name="MCX Commodity Derivatives",
    settlement_cycle="Daily",
    description="Multi Commodity Exchange futures: gold, silver, crude oil, natural gas.",
)

#: All well-known segments keyed by ``MarketId``.
KNOWN_SEGMENTS: dict[MarketId, MarketSegment] = {
    NSE_EQ.id: NSE_EQ,
    NSE_FO.id: NSE_FO,
    NSE_CDS.id: NSE_CDS,
    NSE_SME.id: NSE_SME,
    BSE_EQ.id: BSE_EQ,
    BSE_FO.id: BSE_FO,
    MCX_FO.id: MCX_FO,
}


# ── In-memory segment repository ──────────────────────────────────────────────


class InMemorySegmentRepository:
    """Pure in-memory repository for ``MarketSegment`` objects.

    Pre-populated with Indian exchange segments when ``preload_known=True``.
    """

    def __init__(self, preload_known: bool = True) -> None:
        self._segments: dict[MarketId, MarketSegment] = {}
        if preload_known:
            for segment in KNOWN_SEGMENTS.values():
                self._segments[segment.id] = segment

    def register(self, segment: MarketSegment) -> None:
        """Register a segment.

        Args:
            segment: The segment to register (overwrites any existing entry).
        """
        self._segments[segment.id] = segment

    def get(self, segment_id: MarketId) -> MarketSegment:
        """Return the segment for the given id.

        Args:
            segment_id: The ``MarketId`` to look up.

        Returns:
            The matching ``MarketSegment``.

        Raises:
            SegmentNotFoundError: If not found.
        """
        result = self._segments.get(segment_id)
        if result is None:
            raise SegmentNotFoundError(str(segment_id))
        return result

    def get_or_none(self, segment_id: MarketId) -> MarketSegment | None:
        """Return the segment for the given id, or ``None``.

        Args:
            segment_id: The ``MarketId`` to look up.

        Returns:
            The matching ``MarketSegment``, or ``None``.
        """
        return self._segments.get(segment_id)

    def find_by_exchange(self, exchange_id: MarketId) -> tuple[MarketSegment, ...]:
        """Return all segments belonging to the given exchange.

        Args:
            exchange_id: The exchange to filter by.

        Returns:
            Tuple of matching segments (may be empty).
        """
        return tuple(s for s in self._segments.values() if s.exchange_id == exchange_id)

    def find_by_type(self, segment_type: MarketSegmentType) -> tuple[MarketSegment, ...]:
        """Return all segments of the given type.

        Args:
            segment_type: The ``MarketSegmentType`` to filter by.

        Returns:
            Tuple of matching segments.
        """
        return tuple(s for s in self._segments.values() if s.segment_type == segment_type)

    def all_segments(self) -> tuple[MarketSegment, ...]:
        """Return all registered segments.

        Returns:
            Tuple of all registered ``MarketSegment`` objects.
        """
        return tuple(self._segments.values())

    def __len__(self) -> int:
        return len(self._segments)
