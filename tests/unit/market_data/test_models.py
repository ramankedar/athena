"""Unit tests for core market data enumerations and utilities."""

from __future__ import annotations

from athena.market_data.models import (
    AdjustmentMethodology,
    BarState,
    TickType,
    Timeframe,
    TradeSide,
    is_intraday,
    timeframe_seconds,
)


class TestTimeframe:
    def test_tick_value(self) -> None:
        assert Timeframe.TICK == "tick"

    def test_minute_values(self) -> None:
        assert Timeframe.MINUTE_1 == "1T"
        assert Timeframe.MINUTE_5 == "5T"
        assert Timeframe.MINUTE_15 == "15T"
        assert Timeframe.MINUTE_30 == "30T"

    def test_hour_values(self) -> None:
        assert Timeframe.HOUR_1 == "1H"
        assert Timeframe.HOUR_4 == "4H"

    def test_daily_value(self) -> None:
        assert Timeframe.DAY_1 == "1D"

    def test_weekly_value(self) -> None:
        assert Timeframe.WEEK_1 == "1W"

    def test_monthly_value(self) -> None:
        assert Timeframe.MONTH_1 == "1M"

    def test_all_values_are_strings(self) -> None:
        for tf in Timeframe:
            assert isinstance(tf, str)


class TestTimeframeSeconds:
    def test_second_1(self) -> None:
        assert timeframe_seconds(Timeframe.SECOND_1) == 1

    def test_minute_1(self) -> None:
        assert timeframe_seconds(Timeframe.MINUTE_1) == 60

    def test_minute_5(self) -> None:
        assert timeframe_seconds(Timeframe.MINUTE_5) == 300

    def test_hour_1(self) -> None:
        assert timeframe_seconds(Timeframe.HOUR_1) == 3600

    def test_day_1(self) -> None:
        assert timeframe_seconds(Timeframe.DAY_1) == 86400

    def test_week_1(self) -> None:
        assert timeframe_seconds(Timeframe.WEEK_1) == 604800

    def test_month_is_none(self) -> None:
        assert timeframe_seconds(Timeframe.MONTH_1) is None

    def test_quarter_is_none(self) -> None:
        assert timeframe_seconds(Timeframe.QUARTER_1) is None

    def test_year_is_none(self) -> None:
        assert timeframe_seconds(Timeframe.YEAR_1) is None

    def test_tick_is_none(self) -> None:
        assert timeframe_seconds(Timeframe.TICK) is None


class TestIsIntraday:
    def test_minute_is_intraday(self) -> None:
        assert is_intraday(Timeframe.MINUTE_1) is True

    def test_hour_is_intraday(self) -> None:
        assert is_intraday(Timeframe.HOUR_4) is True

    def test_tick_is_intraday(self) -> None:
        assert is_intraday(Timeframe.TICK) is True

    def test_day_is_not_intraday(self) -> None:
        assert is_intraday(Timeframe.DAY_1) is False

    def test_week_is_not_intraday(self) -> None:
        assert is_intraday(Timeframe.WEEK_1) is False

    def test_month_is_not_intraday(self) -> None:
        assert is_intraday(Timeframe.MONTH_1) is False


class TestTradeSide:
    def test_values(self) -> None:
        assert TradeSide.BUY == "buy"
        assert TradeSide.SELL == "sell"
        assert TradeSide.UNKNOWN == "unknown"


class TestTickType:
    def test_values(self) -> None:
        assert TickType.TRADE == "trade"
        assert TickType.BID == "bid"
        assert TickType.ASK == "ask"
        assert TickType.UNKNOWN == "unknown"


class TestBarState:
    def test_values(self) -> None:
        assert BarState.COMPLETE == "complete"
        assert BarState.INCOMPLETE == "incomplete"


class TestAdjustmentMethodology:
    def test_values(self) -> None:
        assert AdjustmentMethodology.BACKWARD == "backward"
        assert AdjustmentMethodology.FORWARD == "forward"
        assert AdjustmentMethodology.NONE == "none"
