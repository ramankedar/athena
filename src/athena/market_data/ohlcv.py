"""OHLCV bar and series value objects.

``OHLCVBar`` is the primary unit of historical price data in Athena.  It
extends the lightweight ``athena.core.domain.ohlcv.OHLCV`` transport type
with vendor provenance, data quality, auxiliary fields (VWAP, trade count),
and adjustment state.

``OHLCVSeries`` is an immutable, validated collection of ``OHLCVBar`` objects
for the same symbol and timeframe, sorted ascending by ``open_time``.  It
provides series-level analytics (gap detection, date range, bar count) that
are not meaningful on an individual bar.

``GapInfo`` records a detected gap in a series: the time window where bars
are missing and the number of bars that should have been present.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidBarError, InvalidSeriesError
from athena.market_data.models import BarState, Timeframe, timeframe_seconds

if TYPE_CHECKING:
    from datetime import datetime

    from athena.market_data.metadata import DataProvenance
    from athena.market_data.quality import DataQuality


@dataclass(frozen=True)
class OHLCVBar:
    """An immutable OHLCV bar with provenance and quality metadata.

    This is the richer sibling of ``athena.core.domain.ohlcv.OHLCV``.
    Where the core type is a minimal transport object used in engine events,
    ``OHLCVBar`` is the domain model used for storage, analysis, and research
    — carrying vendor provenance, data quality flags, and auxiliary fields
    such as VWAP and trade count.

    Attributes:
        symbol:        Instrument symbol (``"NSE:NIFTY50-INDEX"``).
        timeframe:     Bar aggregation period.
        open_time:     UTC timestamp of the bar's open (timezone-aware).
        close_time:    UTC timestamp of the bar's close (timezone-aware).
        open:          Opening price. Must be > 0.
        high:          Highest price in the bar. Must be >= open and close.
        low:           Lowest price in the bar. Must be <= open and close.
        close:         Closing price. Must be > 0.
        volume:        Traded volume. Must be >= 0.
        open_interest: Open interest at bar close (derivatives). ``None`` for
            cash equities and non-OI instruments.
        vwap:          Volume-weighted average price. ``None`` when not provided
            by the vendor.
        trade_count:   Number of individual trades in the bar. ``None`` when
            not provided.
        state:         Whether the bar has closed (COMPLETE) or is still
            forming (INCOMPLETE).
        is_adjusted:   ``True`` when prices have been adjusted for corporate
            actions.
        provenance:    Source metadata. ``None`` for in-process generated bars.
        quality:       Quality flags and confidence score. ``None`` implies
            unknown quality.

    Raises:
        InvalidBarError: If any of the OHLCV integrity constraints are violated,
            timestamps are naive, or ``open_time >= close_time``.
    """

    symbol: Symbol
    timeframe: Timeframe
    open_time: datetime
    close_time: datetime
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    open_interest: Quantity | None = None
    vwap: Price | None = None
    trade_count: int | None = None
    state: BarState = BarState.COMPLETE
    is_adjusted: bool = False
    provenance: DataProvenance | None = None
    quality: DataQuality | None = None

    def __post_init__(self) -> None:
        # Timezone-awareness
        if self.open_time.tzinfo is None:
            raise InvalidBarError("open_time", str(self.open_time), "must be timezone-aware")
        if self.close_time.tzinfo is None:
            raise InvalidBarError("close_time", str(self.close_time), "must be timezone-aware")

        # Temporal ordering
        if self.open_time >= self.close_time:
            raise InvalidBarError(
                "open_time",
                str(self.open_time),
                f"open_time must be before close_time ({self.close_time})",
            )

        # Price positivity
        for name, val in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            if val <= 0:
                raise InvalidBarError(name, val, "price must be > 0")

        # OHLCV structural integrity: high >= max(open, close) >= min(open, close) >= low
        if self.high < self.open or self.high < self.close:
            raise InvalidBarError(
                "high",
                self.high,
                f"high ({self.high}) must be >= open ({self.open}) and close ({self.close})",
            )
        if self.low > self.open or self.low > self.close:
            raise InvalidBarError(
                "low",
                self.low,
                f"low ({self.low}) must be <= open ({self.open}) and close ({self.close})",
            )

        # Volume non-negativity
        if self.volume < 0:
            raise InvalidBarError("volume", self.volume, "volume must be >= 0")

        # VWAP must be within [low, high] when provided
        if self.vwap is not None and not (self.low <= self.vwap <= self.high):
            raise InvalidBarError(
                "vwap",
                self.vwap,
                f"VWAP ({self.vwap}) must be within [low={self.low}, high={self.high}]",
            )

        # trade_count non-negativity
        if self.trade_count is not None and self.trade_count < 0:
            raise InvalidBarError("trade_count", self.trade_count, "must be >= 0")

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def bar_range(self) -> Price:
        """Price range from low to high.

        Returns:
            ``high - low`` as a ``Price``.
        """
        return Price(self.high - self.low)

    @property
    def body_size(self) -> Price:
        """Absolute difference between open and close.

        Returns:
            ``abs(close - open)`` as a ``Price``.
        """
        return Price(abs(self.close - self.open))

    @property
    def is_bullish(self) -> bool:
        """Return ``True`` when close >= open.

        Returns:
            ``True`` for bullish (or neutral) bars.
        """
        return self.close >= self.open

    @property
    def is_complete(self) -> bool:
        """Return ``True`` when the bar's period has fully closed.

        Returns:
            ``True`` when ``state == BarState.COMPLETE``.
        """
        return self.state == BarState.COMPLETE

    @property
    def duration(self) -> timedelta:
        """Elapsed time from open to close.

        Returns:
            A ``timedelta`` representing the bar's period.
        """
        return self.close_time - self.open_time

    def __str__(self) -> str:
        return (
            f"OHLCVBar({self.symbol} {self.timeframe.value} "
            f"{self.open_time.isoformat()} "
            f"O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume})"
        )


@dataclass(frozen=True)
class GapInfo:
    """A detected gap in an ``OHLCVSeries``.

    Attributes:
        gap_start:     UTC timestamp of the last bar before the gap.
        gap_end:       UTC timestamp of the first bar after the gap.
        missing_bars:  Estimated number of bars missing in this gap.
    """

    gap_start: datetime
    gap_end: datetime
    missing_bars: int

    @property
    def gap_duration(self) -> timedelta:
        """Duration of the gap from start to end.

        Returns:
            ``timedelta`` representing the gap's span.
        """
        return self.gap_end - self.gap_start

    def __str__(self) -> str:
        return (
            f"GapInfo({self.gap_start.isoformat()} to {self.gap_end.isoformat()}, "
            f"~{self.missing_bars} bars)"
        )


@dataclass(frozen=True)
class OHLCVSeries:
    """An immutable, validated sequence of OHLCV bars.

    All bars must share the same ``symbol`` and ``timeframe`` and must be
    sorted in strictly ascending order by ``open_time``. Duplicate timestamps
    are not permitted.

    Attributes:
        symbol:    Instrument symbol.
        timeframe: Bar aggregation period.
        bars:      Ordered tuple of bars. May be empty.

    Raises:
        InvalidSeriesError: If bars have mismatched symbol or timeframe,
            are not in ascending ``open_time`` order, or contain duplicates.
    """

    symbol: Symbol
    timeframe: Timeframe
    bars: tuple[OHLCVBar, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for i, bar in enumerate(self.bars):
            if bar.symbol != self.symbol:
                raise InvalidSeriesError(
                    f"bar[{i}].symbol {bar.symbol!r} != series.symbol {self.symbol!r}"
                )
            if bar.timeframe != self.timeframe:
                raise InvalidSeriesError(
                    f"bar[{i}].timeframe {bar.timeframe!r} != series.timeframe {self.timeframe!r}"
                )

        for i in range(len(self.bars) - 1):
            current = self.bars[i]
            following = self.bars[i + 1]
            if current.open_time >= following.open_time:
                raise InvalidSeriesError(
                    f"bars must be in ascending open_time order: "
                    f"bar[{i}]={current.open_time.isoformat()} >= "
                    f"bar[{i + 1}]={following.open_time.isoformat()}"
                )

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def bar_count(self) -> int:
        """Number of bars in the series.

        Returns:
            Length of ``self.bars``.
        """
        return len(self.bars)

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when the series contains no bars.

        Returns:
            ``True`` when ``bar_count == 0``.
        """
        return len(self.bars) == 0

    @property
    def start_time(self) -> datetime | None:
        """UTC timestamp of the first bar's open, or ``None`` when empty.

        Returns:
            ``self.bars[0].open_time`` or ``None``.
        """
        return self.bars[0].open_time if self.bars else None

    @property
    def end_time(self) -> datetime | None:
        """UTC timestamp of the last bar's close, or ``None`` when empty.

        Returns:
            ``self.bars[-1].close_time`` or ``None``.
        """
        return self.bars[-1].close_time if self.bars else None

    def detect_gaps(self) -> tuple[GapInfo, ...]:
        """Identify gaps in the series where bars are missing.

        A gap is detected when the interval between two consecutive bars'
        ``open_time`` values is more than 2x the expected timeframe duration.
        This heuristic accommodates overnight and weekend breaks for intraday
        data without false positives.

        For ``TICK``, ``MONTH_1``, ``QUARTER_1``, and ``YEAR_1`` timeframes
        (variable duration), no gap detection is performed and an empty tuple
        is returned.

        Returns:
            Ordered tuple of ``GapInfo`` objects, one per detected gap.
            Empty tuple when no gaps are found or the series is too short.
        """
        if len(self.bars) < 2:
            return ()
        duration_sec = timeframe_seconds(self.timeframe)
        if duration_sec is None:
            return ()

        expected = timedelta(seconds=duration_sec)
        threshold = expected * 2  # anything > 2x is a gap

        gaps: list[GapInfo] = []
        for i in range(len(self.bars) - 1):
            actual_gap = self.bars[i + 1].open_time - self.bars[i].open_time
            if actual_gap > threshold:
                missing = int(actual_gap / expected) - 1
                gaps.append(
                    GapInfo(
                        gap_start=self.bars[i].open_time,
                        gap_end=self.bars[i + 1].open_time,
                        missing_bars=max(0, missing),
                    )
                )
        return tuple(gaps)

    def has_gaps(self) -> bool:
        """Return ``True`` when the series has one or more detected gaps.

        Returns:
            ``True`` when ``detect_gaps()`` returns a non-empty tuple.
        """
        return len(self.detect_gaps()) > 0

    def __str__(self) -> str:
        if self.is_empty:
            return f"OHLCVSeries({self.symbol} {self.timeframe.value} empty)"
        return (
            f"OHLCVSeries({self.symbol} {self.timeframe.value} "
            f"{self.bar_count} bars "
            f"{self.start_time.isoformat()} to {self.end_time.isoformat()})"  # type: ignore[union-attr]
        )
