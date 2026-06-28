"""Unit tests for OHLCVBar, OHLCVSeries, and GapInfo."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidBarError, InvalidSeriesError
from athena.market_data.models import BarState, Timeframe
from athena.market_data.ohlcv import GapInfo, OHLCVBar, OHLCVSeries

NIFTY = Symbol("NSE:NIFTY50-INDEX")
T0 = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
T1 = datetime(2025, 1, 15, 9, 16, tzinfo=UTC)


def _bar(open_time: datetime = T0, close_time: datetime = T1) -> OHLCVBar:
    return OHLCVBar(
        symbol=NIFTY,
        timeframe=Timeframe.MINUTE_1,
        open_time=open_time,
        close_time=close_time,
        open=Price(Decimal("24490")),
        high=Price(Decimal("24510")),
        low=Price(Decimal("24480")),
        close=Price(Decimal("24500")),
        volume=Quantity(Decimal("5000")),
    )


class TestOHLCVBar:
    def test_valid_construction(self, sample_bar: OHLCVBar) -> None:
        assert sample_bar.symbol == NIFTY
        assert sample_bar.open == Price(Decimal("24490"))

    def test_naive_open_time_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="open_time"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=datetime(2025, 1, 15, 9, 15),
                close_time=T1,
                open=Price(Decimal("100")),
                high=Price(Decimal("110")),
                low=Price(Decimal("90")),
                close=Price(Decimal("105")),
                volume=Quantity(Decimal("1000")),
            )

    def test_naive_close_time_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="close_time"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=datetime(2025, 1, 15, 9, 16),
                open=Price(Decimal("100")),
                high=Price(Decimal("110")),
                low=Price(Decimal("90")),
                close=Price(Decimal("105")),
                volume=Quantity(Decimal("1000")),
            )

    def test_open_time_equals_close_time_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="open_time"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=T0,
                open=Price(Decimal("100")),
                high=Price(Decimal("110")),
                low=Price(Decimal("90")),
                close=Price(Decimal("105")),
                volume=Quantity(Decimal("1000")),
            )

    def test_zero_open_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="open"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=T1,
                open=Price(Decimal("0")),
                high=Price(Decimal("110")),
                low=Price(Decimal("0")),
                close=Price(Decimal("0")),
                volume=Quantity(Decimal("1000")),
            )

    def test_high_below_open_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="high"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=T1,
                open=Price(Decimal("200")),
                high=Price(Decimal("150")),  # high < open
                low=Price(Decimal("100")),
                close=Price(Decimal("120")),
                volume=Quantity(Decimal("1000")),
            )

    def test_low_above_close_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="low"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=T1,
                open=Price(Decimal("200")),
                high=Price(Decimal("250")),
                low=Price(Decimal("220")),  # low > close
                close=Price(Decimal("210")),
                volume=Quantity(Decimal("1000")),
            )

    def test_negative_volume_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="volume"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=T1,
                open=Price(Decimal("100")),
                high=Price(Decimal("110")),
                low=Price(Decimal("90")),
                close=Price(Decimal("105")),
                volume=Quantity(Decimal("-1")),
            )

    def test_vwap_outside_range_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="VWAP"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=T1,
                open=Price(Decimal("100")),
                high=Price(Decimal("110")),
                low=Price(Decimal("90")),
                close=Price(Decimal("105")),
                volume=Quantity(Decimal("1000")),
                vwap=Price(Decimal("120")),  # above high
            )

    def test_negative_trade_count_raises(self) -> None:
        with pytest.raises(InvalidBarError, match="trade_count"):
            OHLCVBar(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                open_time=T0,
                close_time=T1,
                open=Price(Decimal("100")),
                high=Price(Decimal("110")),
                low=Price(Decimal("90")),
                close=Price(Decimal("105")),
                volume=Quantity(Decimal("1000")),
                trade_count=-1,
            )

    def test_properties(self, sample_bar: OHLCVBar) -> None:
        assert sample_bar.bar_range == Price(Decimal("30"))  # 24510 - 24480
        assert sample_bar.body_size == Price(Decimal("10"))  # |24500 - 24490|
        assert sample_bar.is_bullish is True  # close > open
        assert sample_bar.is_complete is True
        assert sample_bar.duration == timedelta(minutes=1)

    def test_bearish_bar(self) -> None:
        bar = OHLCVBar(
            symbol=NIFTY,
            timeframe=Timeframe.MINUTE_1,
            open_time=T0,
            close_time=T1,
            open=Price(Decimal("200")),
            high=Price(Decimal("210")),
            low=Price(Decimal("180")),
            close=Price(Decimal("190")),
            volume=Quantity(Decimal("1000")),
        )
        assert bar.is_bullish is False

    def test_incomplete_bar(self) -> None:
        bar = OHLCVBar(
            symbol=NIFTY,
            timeframe=Timeframe.MINUTE_1,
            open_time=T0,
            close_time=T1,
            open=Price(Decimal("100")),
            high=Price(Decimal("110")),
            low=Price(Decimal("90")),
            close=Price(Decimal("105")),
            volume=Quantity(Decimal("1000")),
            state=BarState.INCOMPLETE,
        )
        assert bar.is_complete is False

    def test_str(self, sample_bar: OHLCVBar) -> None:
        s = str(sample_bar)
        assert "NSE:NIFTY50-INDEX" in s
        assert "1T" in s

    def test_is_frozen(self, sample_bar: OHLCVBar) -> None:
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            sample_bar.close = Price(Decimal("99"))  # type: ignore[misc]


class TestGapInfo:
    def test_construction(self) -> None:
        gap = GapInfo(gap_start=T0, gap_end=T1, missing_bars=3)
        assert gap.missing_bars == 3

    def test_duration(self) -> None:
        gap = GapInfo(gap_start=T0, gap_end=T1, missing_bars=1)
        assert gap.gap_duration == timedelta(minutes=1)

    def test_str(self) -> None:
        gap = GapInfo(gap_start=T0, gap_end=T1, missing_bars=2)
        assert "2 bars" in str(gap)


class TestOHLCVSeries:
    def test_empty_series(self) -> None:
        series = OHLCVSeries(symbol=NIFTY, timeframe=Timeframe.MINUTE_1)
        assert series.is_empty is True
        assert series.bar_count == 0
        assert series.start_time is None
        assert series.end_time is None

    def test_series_with_bars(self, sample_bar: OHLCVBar) -> None:
        series = OHLCVSeries(
            symbol=NIFTY,
            timeframe=Timeframe.MINUTE_1,
            bars=(sample_bar,),
        )
        assert series.bar_count == 1
        assert series.start_time == T0
        assert series.end_time == T1

    def test_mismatched_symbol_raises(self, sample_bar: OHLCVBar) -> None:
        other_bar = OHLCVBar(
            symbol=Symbol("NSE:HDFCBANK"),
            timeframe=Timeframe.MINUTE_1,
            open_time=T1,
            close_time=T1 + timedelta(minutes=1),
            open=Price(Decimal("100")),
            high=Price(Decimal("110")),
            low=Price(Decimal("90")),
            close=Price(Decimal("105")),
            volume=Quantity(Decimal("1000")),
        )
        with pytest.raises(InvalidSeriesError, match="symbol"):
            OHLCVSeries(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                bars=(sample_bar, other_bar),
            )

    def test_mismatched_timeframe_raises(self, sample_bar: OHLCVBar) -> None:
        other_bar = OHLCVBar(
            symbol=NIFTY,
            timeframe=Timeframe.MINUTE_5,  # different timeframe
            open_time=T1,
            close_time=T1 + timedelta(minutes=5),
            open=Price(Decimal("100")),
            high=Price(Decimal("110")),
            low=Price(Decimal("90")),
            close=Price(Decimal("105")),
            volume=Quantity(Decimal("1000")),
        )
        with pytest.raises(InvalidSeriesError, match="timeframe"):
            OHLCVSeries(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                bars=(sample_bar, other_bar),
            )

    def test_out_of_order_raises(self, sample_bar: OHLCVBar) -> None:
        earlier_bar = _bar(
            open_time=T1,
            close_time=T1 + timedelta(minutes=1),
        )
        with pytest.raises(InvalidSeriesError, match="open_time"):
            OHLCVSeries(
                symbol=NIFTY,
                timeframe=Timeframe.MINUTE_1,
                bars=(earlier_bar, sample_bar),  # wrong order
            )

    def test_gap_detection(self, sample_bar: OHLCVBar) -> None:
        # Create two bars with a 10-minute gap (should detect gap for 1T bars)
        bar2 = _bar(
            open_time=T0 + timedelta(minutes=11),
            close_time=T0 + timedelta(minutes=12),
        )
        series = OHLCVSeries(
            symbol=NIFTY,
            timeframe=Timeframe.MINUTE_1,
            bars=(sample_bar, bar2),
        )
        assert series.has_gaps() is True
        gaps = series.detect_gaps()
        assert len(gaps) == 1

    def test_no_gap_consecutive_bars(self) -> None:
        bars = tuple(
            _bar(
                open_time=T0 + timedelta(minutes=i),
                close_time=T0 + timedelta(minutes=i + 1),
            )
            for i in range(5)
        )
        series = OHLCVSeries(symbol=NIFTY, timeframe=Timeframe.MINUTE_1, bars=bars)
        assert series.has_gaps() is False

    def test_no_gap_detection_for_monthly(self, sample_bar: OHLCVBar) -> None:
        monthly_bar = OHLCVBar(
            symbol=NIFTY,
            timeframe=Timeframe.MONTH_1,
            open_time=T0,
            close_time=T0 + timedelta(days=31),
            open=Price(Decimal("100")),
            high=Price(Decimal("110")),
            low=Price(Decimal("90")),
            close=Price(Decimal("105")),
            volume=Quantity(Decimal("1000")),
        )
        bar2 = OHLCVBar(
            symbol=NIFTY,
            timeframe=Timeframe.MONTH_1,
            open_time=T0 + timedelta(days=35),
            close_time=T0 + timedelta(days=65),
            open=Price(Decimal("100")),
            high=Price(Decimal("110")),
            low=Price(Decimal("90")),
            close=Price(Decimal("105")),
            volume=Quantity(Decimal("1000")),
        )
        series = OHLCVSeries(
            symbol=NIFTY,
            timeframe=Timeframe.MONTH_1,
            bars=(monthly_bar, bar2),
        )
        # Monthly timeframe has no fixed duration, so no gap detection
        assert series.detect_gaps() == ()

    def test_str(self) -> None:
        series = OHLCVSeries(symbol=NIFTY, timeframe=Timeframe.MINUTE_1)
        assert "empty" in str(series)

    def test_str_with_bars(self, sample_bar: OHLCVBar) -> None:
        series = OHLCVSeries(symbol=NIFTY, timeframe=Timeframe.MINUTE_1, bars=(sample_bar,))
        assert "1 bars" in str(series)
