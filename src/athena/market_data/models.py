"""Core primitive value types for the Market Data Domain.

Defines the enumerations and utility functions shared across all market data
modules. These types encode domain vocabulary that is independent of any
specific instrument or vendor.

Types defined here:
    ``Timeframe``              — bar aggregation period (e.g. "1T", "1H", "1D").
    ``TradeSide``              — buyer-initiated vs. seller-initiated trade.
    ``TickType``               — whether a tick is a trade, bid update, or ask update.
    ``BarState``               — whether a bar is fully formed or still in progress.
    ``AdjustmentMethodology``  — backward vs. forward price adjustment.
    ``timeframe_seconds``      — convert a Timeframe to seconds (None for variable).

Timeframe string codes follow the conventions of:
    - Fyers API (``"1T"`` = 1 minute)
    - pandas (``"1T"`` = 1 minute, ``"1H"`` = 1 hour, ``"1D"`` = 1 day)
    - Bloomberg, Reuters (similar conventions)

Using string codes rather than duration integers means the timeframe value
can be passed directly to vendor APIs without translation.
"""

from __future__ import annotations

from enum import StrEnum


class Timeframe(StrEnum):
    """Bar aggregation period.

    String codes match common vendor API conventions. Use
    ``timeframe_seconds()`` to convert to a duration for gap analysis.

    Attributes:
        TICK:       Raw tick data — no aggregation.
        SECOND_1:   1-second bars.
        SECOND_5:   5-second bars.
        SECOND_15:  15-second bars.
        SECOND_30:  30-second bars.
        MINUTE_1:   1-minute bars (``"1T"`` in pandas/Fyers convention).
        MINUTE_3:   3-minute bars.
        MINUTE_5:   5-minute bars.
        MINUTE_10:  10-minute bars.
        MINUTE_15:  15-minute bars.
        MINUTE_30:  30-minute bars.
        HOUR_1:     1-hour bars.
        HOUR_2:     2-hour bars.
        HOUR_4:     4-hour bars.
        DAY_1:      Daily bars.
        WEEK_1:     Weekly bars.
        MONTH_1:    Monthly bars.
        QUARTER_1:  Quarterly bars.
        YEAR_1:     Annual bars.
    """

    TICK = "tick"
    SECOND_1 = "1S"
    SECOND_5 = "5S"
    SECOND_15 = "15S"
    SECOND_30 = "30S"
    MINUTE_1 = "1T"
    MINUTE_3 = "3T"
    MINUTE_5 = "5T"
    MINUTE_10 = "10T"
    MINUTE_15 = "15T"
    MINUTE_30 = "30T"
    HOUR_1 = "1H"
    HOUR_2 = "2H"
    HOUR_4 = "4H"
    DAY_1 = "1D"
    WEEK_1 = "1W"
    MONTH_1 = "1M"
    QUARTER_1 = "1Q"
    YEAR_1 = "1Y"


class TradeSide(StrEnum):
    """Whether a trade was buyer- or seller-initiated.

    Determination is exchange-specific. Many exchanges provide this
    as a ``BuyOrSell`` flag in the trade record; others require
    inference from the prevailing quote at execution time.

    Attributes:
        BUY:     The aggressor was the buyer (lifted the ask).
        SELL:    The aggressor was the seller (hit the bid).
        UNKNOWN: Side cannot be determined from available data.
    """

    BUY = "buy"
    SELL = "sell"
    UNKNOWN = "unknown"


class TickType(StrEnum):
    """Classification of what a raw tick update represents.

    Attributes:
        TRADE:   A completed transaction (prints in the trade tape).
        BID:     An update to the best bid price or size.
        ASK:     An update to the best ask price or size.
        UNKNOWN: Type not determinable from the raw data.
    """

    TRADE = "trade"
    BID = "bid"
    ASK = "ask"
    UNKNOWN = "unknown"


class BarState(StrEnum):
    """Whether an OHLCV bar has closed (complete) or is still forming.

    Attributes:
        COMPLETE:   The bar's period has ended; all OHLCV values are final.
        INCOMPLETE: The bar's period is still open; values will change.
    """

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class AdjustmentMethodology(StrEnum):
    """How historical prices are adjusted for corporate actions.

    Attributes:
        BACKWARD: Adjust all historical data backward from the current price.
            The current price is always ``unadjusted``; older prices are
            scaled by the cumulative adjustment factor. Most common in
            quantitative research (Yahoo Finance, NSE adjusted series).
        FORWARD:  Adjust from the corporate action date forward. Historical
            data remains unchanged; new data reflects the adjustment.
            Used when preserving absolute historical prices is important.
        NONE:     No adjustment applied; raw unadjusted prices.
    """

    BACKWARD = "backward"
    FORWARD = "forward"
    NONE = "none"


# ── Utility ────────────────────────────────────────────────────────────────────

_TIMEFRAME_SECONDS: dict[Timeframe, int] = {
    Timeframe.SECOND_1: 1,
    Timeframe.SECOND_5: 5,
    Timeframe.SECOND_15: 15,
    Timeframe.SECOND_30: 30,
    Timeframe.MINUTE_1: 60,
    Timeframe.MINUTE_3: 180,
    Timeframe.MINUTE_5: 300,
    Timeframe.MINUTE_10: 600,
    Timeframe.MINUTE_15: 900,
    Timeframe.MINUTE_30: 1_800,
    Timeframe.HOUR_1: 3_600,
    Timeframe.HOUR_2: 7_200,
    Timeframe.HOUR_4: 14_400,
    Timeframe.DAY_1: 86_400,
    Timeframe.WEEK_1: 604_800,
}


def timeframe_seconds(timeframe: Timeframe) -> int | None:
    """Return the exact duration in seconds for the given timeframe.

    Monthly, quarterly, and annual timeframes have variable durations (months
    have different numbers of days) and return ``None``. Callers that need to
    perform gap analysis on such timeframes must use a calendar-aware approach.

    Args:
        timeframe: The bar aggregation period to convert.

    Returns:
        Integer number of seconds, or ``None`` for TICK, MONTH_1,
        QUARTER_1, and YEAR_1 (variable-duration timeframes).

    Example::

        assert timeframe_seconds(Timeframe.MINUTE_1) == 60
        assert timeframe_seconds(Timeframe.MONTH_1) is None
    """
    return _TIMEFRAME_SECONDS.get(timeframe)


def is_intraday(timeframe: Timeframe) -> bool:
    """Return ``True`` when the timeframe is shorter than one trading day.

    Args:
        timeframe: The timeframe to classify.

    Returns:
        ``True`` for TICK, SECOND_*, MINUTE_*, HOUR_* timeframes.
    """
    return timeframe not in (
        Timeframe.DAY_1,
        Timeframe.WEEK_1,
        Timeframe.MONTH_1,
        Timeframe.QUARTER_1,
        Timeframe.YEAR_1,
    )
