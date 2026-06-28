"""Unit tests for market data validation utilities."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.adjustments import AdjustmentFactor
from athena.market_data.models import AdjustmentMethodology, Timeframe
from athena.market_data.ohlcv import OHLCVBar, OHLCVSeries
from athena.market_data.validation import (
    ValidationResult,
    validate_adjustment_factor,
    validate_ohlcv_bar,
    validate_ohlcv_series,
    validate_order_book,
    validate_quote,
    validate_tick,
    validate_trade,
)

NIFTY = Symbol("NSE:NIFTY50-INDEX")
NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
CLOSE = datetime(2025, 1, 15, 9, 16, tzinfo=UTC)


class TestValidationResult:
    def test_ok(self) -> None:
        r = ValidationResult.ok()
        assert r.is_valid
        assert r.failures == ()

    def test_failed(self) -> None:
        r = ValidationResult.failed("err1", "err2")
        assert not r.is_valid
        assert len(r.failures) == 2

    def test_merge_two_ok(self) -> None:
        assert ValidationResult.ok().merge(ValidationResult.ok()).is_valid

    def test_merge_ok_failed(self) -> None:
        merged = ValidationResult.ok().merge(ValidationResult.failed("bad"))
        assert not merged.is_valid
        assert "bad" in merged.failures


class TestValidateOHLCVBar:
    def test_valid_bar(self, sample_bar: OHLCVBar) -> None:
        assert validate_ohlcv_bar(sample_bar).is_valid

    def test_invalid_via_duck_type_naive_timestamp(self) -> None:
        class FakeBar:
            open_time = datetime(2025, 1, 15, 9, 15)  # naive
            close_time = CLOSE
            open = Price(Decimal("100"))
            high = Price(Decimal("110"))
            low = Price(Decimal("90"))
            close = Price(Decimal("105"))
            volume = Quantity(Decimal("1000"))
            vwap = None

        result = validate_ohlcv_bar(FakeBar())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_invalid_high_less_than_low_via_duck_type(self) -> None:
        class FakeBar:
            open_time = NOW
            close_time = CLOSE
            open = Price(Decimal("100"))
            high = Price(Decimal("80"))  # < low
            low = Price(Decimal("90"))
            close = Price(Decimal("85"))
            volume = Quantity(Decimal("1000"))
            vwap = None

        result = validate_ohlcv_bar(FakeBar())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateOHLCVSeries:
    def test_valid_series(self, sample_bar: OHLCVBar) -> None:
        series = OHLCVSeries(symbol=NIFTY, timeframe=Timeframe.MINUTE_1, bars=(sample_bar,))
        assert validate_ohlcv_series(series).is_valid

    def test_empty_series_valid(self) -> None:
        series = OHLCVSeries(symbol=NIFTY, timeframe=Timeframe.MINUTE_1)
        assert validate_ohlcv_series(series).is_valid


class TestValidateTick:
    def test_valid_tick_via_duck_type(self) -> None:
        class FakeTick:
            timestamp_utc = NOW
            price = Price(Decimal("100"))
            volume = Quantity(Decimal("1"))

        result = validate_tick(FakeTick())  # type: ignore[arg-type]
        assert result.is_valid

    def test_invalid_naive_timestamp(self) -> None:
        class FakeTick:
            timestamp_utc = datetime(2025, 1, 15)  # naive
            price = Price(Decimal("100"))
            volume = Quantity(Decimal("1"))

        result = validate_tick(FakeTick())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_invalid_zero_price(self) -> None:
        class FakeTick:
            timestamp_utc = NOW
            price = Price(Decimal("0"))
            volume = Quantity(Decimal("1"))

        result = validate_tick(FakeTick())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_invalid_negative_volume(self) -> None:
        class FakeTick:
            timestamp_utc = NOW
            price = Price(Decimal("100"))
            volume = Quantity(Decimal("-1"))

        result = validate_tick(FakeTick())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateQuote:
    def test_valid_quote_via_duck_type(self) -> None:
        class FakeQuote:
            timestamp_utc = NOW
            bid_price = Price(Decimal("100"))
            ask_price = Price(Decimal("110"))
            is_crossed = False

        result = validate_quote(FakeQuote())  # type: ignore[arg-type]
        assert result.is_valid

    def test_crossed_quote_fails(self) -> None:
        class FakeQuote:
            timestamp_utc = NOW
            bid_price = Price(Decimal("110"))
            ask_price = Price(Decimal("100"))
            is_crossed = True

        result = validate_quote(FakeQuote())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateTrade:
    def test_valid_trade_via_duck_type(self) -> None:
        class FakeTrade:
            timestamp_utc = NOW
            price = Price(Decimal("100"))
            volume = Quantity(Decimal("1"))

        result = validate_trade(FakeTrade())  # type: ignore[arg-type]
        assert result.is_valid

    def test_invalid_zero_volume(self) -> None:
        class FakeTrade:
            timestamp_utc = NOW
            price = Price(Decimal("100"))
            volume = Quantity(Decimal("0"))

        result = validate_trade(FakeTrade())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateOrderBook:
    def test_valid_book_via_duck_type(self) -> None:
        class FakeBook:
            timestamp_utc = NOW
            is_crossed = False

        result = validate_order_book(FakeBook())  # type: ignore[arg-type]
        assert result.is_valid

    def test_crossed_book_fails(self) -> None:
        class FakeBook:
            timestamp_utc = NOW
            bids = type("Side", (), {"best_price": Price(Decimal("200"))})()
            asks = type("Side", (), {"best_price": Price(Decimal("100"))})()
            is_crossed = True

        result = validate_order_book(FakeBook())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateOHLCVSeriesViaFakes:
    def test_symbol_mismatch_via_duck_type(self, sample_bar: OHLCVBar) -> None:
        class FakeSeries:
            symbol = NIFTY
            timeframe = Timeframe.MINUTE_1

            class FakeBar:
                symbol = Symbol("NSE:OTHER")
                timeframe = Timeframe.MINUTE_1
                open_time = NOW
                close_time = CLOSE
                open = Price(Decimal("100"))
                high = Price(Decimal("110"))
                low = Price(Decimal("90"))
                close = Price(Decimal("105"))
                volume = Quantity(Decimal("1000"))
                vwap = None

            bars = (FakeBar(),)

        result = validate_ohlcv_series(FakeSeries())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_out_of_order_via_duck_type(self) -> None:
        from datetime import timedelta

        class FakeSeries:
            symbol = NIFTY
            timeframe = Timeframe.MINUTE_1

            class Bar1:
                symbol = NIFTY
                timeframe = Timeframe.MINUTE_1
                open_time = CLOSE  # later
                close_time = CLOSE + timedelta(minutes=1)
                open = high = low = close = Price(Decimal("100"))
                volume = Quantity(Decimal("1"))
                vwap = None

            class Bar2:
                symbol = NIFTY
                timeframe = Timeframe.MINUTE_1
                open_time = NOW  # earlier (wrong order)
                close_time = CLOSE
                open = high = low = close = Price(Decimal("100"))
                volume = Quantity(Decimal("1"))
                vwap = None

            bars = (Bar1(), Bar2())

        result = validate_ohlcv_series(FakeSeries())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateQuoteFailurePaths:
    def test_zero_bid_price_via_duck_type(self) -> None:
        class FakeQuote:
            timestamp_utc = NOW
            bid_price = Price(Decimal("0"))
            ask_price = Price(Decimal("110"))
            is_crossed = False

        result = validate_quote(FakeQuote())  # type: ignore[arg-type]
        assert not result.is_valid

    def test_zero_ask_price_via_duck_type(self) -> None:
        class FakeQuote:
            timestamp_utc = NOW
            bid_price = Price(Decimal("100"))
            ask_price = Price(Decimal("0"))
            is_crossed = False

        result = validate_quote(FakeQuote())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateTradeFailurePaths:
    def test_zero_price_via_duck_type(self) -> None:
        class FakeTrade:
            timestamp_utc = NOW
            price = Price(Decimal("0"))
            volume = Quantity(Decimal("1"))

        result = validate_trade(FakeTrade())  # type: ignore[arg-type]
        assert not result.is_valid


class TestValidateAdjustmentFactor:
    def test_valid_factor(self) -> None:
        from datetime import date

        f = AdjustmentFactor(
            symbol=NIFTY,
            effective_date=date(2025, 1, 20),
            price_factor=Decimal("0.5"),
            volume_factor=Decimal("2.0"),
            methodology=AdjustmentMethodology.BACKWARD,
        )
        assert validate_adjustment_factor(f).is_valid

    def test_invalid_via_duck_type(self) -> None:
        class FakeFactor:
            price_factor = Decimal("0")
            volume_factor = Decimal("1")

        result = validate_adjustment_factor(FakeFactor())  # type: ignore[arg-type]
        assert not result.is_valid
