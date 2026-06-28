"""Unit tests for market data exceptions."""

from __future__ import annotations

import pytest

from athena.market_data.exceptions import (
    DataGapError,
    InvalidAdjustmentError,
    InvalidBarError,
    InvalidOrderBookError,
    InvalidQuoteError,
    InvalidSeriesError,
    InvalidTickError,
    InvalidTradeError,
    MarketDataError,
    ProviderError,
)
from athena.platform.exceptions import AthenaError


class TestMarketDataError:
    def test_is_athena_error(self) -> None:
        assert issubclass(MarketDataError, AthenaError)


class TestInvalidBarError:
    def test_is_market_data_error(self) -> None:
        assert issubclass(InvalidBarError, MarketDataError)

    def test_message_contains_field(self) -> None:
        exc = InvalidBarError("high", 100, "must be >= open")
        assert "high" in str(exc)
        assert exc.field == "high"
        assert exc.error_code == "MDT_001"

    def test_no_value(self) -> None:
        exc = InvalidBarError("timestamp")
        assert "timestamp" in str(exc)


class TestInvalidTickError:
    def test_attributes(self) -> None:
        exc = InvalidTickError("price must be > 0")
        assert exc.reason == "price must be > 0"
        assert exc.error_code == "MDT_002"


class TestInvalidQuoteError:
    def test_attributes(self) -> None:
        exc = InvalidQuoteError("crossed market")
        assert exc.error_code == "MDT_003"


class TestInvalidTradeError:
    def test_attributes(self) -> None:
        exc = InvalidTradeError("volume is zero")
        assert exc.error_code == "MDT_004"


class TestInvalidOrderBookError:
    def test_attributes(self) -> None:
        exc = InvalidOrderBookError("bid > ask")
        assert exc.error_code == "MDT_005"


class TestInvalidSeriesError:
    def test_attributes(self) -> None:
        exc = InvalidSeriesError("bars not ordered")
        assert exc.reason == "bars not ordered"
        assert exc.error_code == "MDT_006"


class TestDataGapError:
    def test_attributes(self) -> None:
        exc = DataGapError("2025-01-15T09:15", "2025-01-15T10:00", expected_bars=45)
        assert exc.gap_start == "2025-01-15T09:15"
        assert exc.expected_bars == 45
        assert exc.error_code == "MDT_007"

    def test_str(self) -> None:
        exc = DataGapError("2025-01-15T09:15", "2025-01-15T10:00", 45)
        assert "45" in str(exc)


class TestInvalidAdjustmentError:
    def test_attributes(self) -> None:
        exc = InvalidAdjustmentError("price_factor", 0, "must be > 0")
        assert exc.field == "price_factor"
        assert exc.error_code == "MDT_008"


class TestProviderError:
    def test_attributes(self) -> None:
        exc = ProviderError("fyers", "rate limit exceeded", status_code=429)
        assert exc.vendor == "fyers"
        assert exc.reason == "rate limit exceeded"
        assert exc.error_code == "MDT_009"
        assert exc.context["status_code"] == 429

    def test_caught_as_market_data_error(self) -> None:
        with pytest.raises(MarketDataError):
            raise ProviderError("nse", "timeout")
