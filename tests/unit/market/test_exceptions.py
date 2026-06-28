"""Unit tests for market domain exception types."""

from __future__ import annotations

import pytest

from athena.market.exceptions import (
    ExchangeNotFoundError,
    InvalidMarketIdError,
    InvalidMarketStateError,
    InvalidScheduleError,
    MarketError,
    MarketHaltedError,
    SegmentNotFoundError,
    UnsupportedCapabilityError,
)
from athena.platform.exceptions import AthenaError


class TestMarketError:
    def test_is_athena_error(self) -> None:
        assert issubclass(MarketError, AthenaError)

    def test_construction(self) -> None:
        exc = MarketError("market failed", component="exchange")
        assert "market failed" in str(exc)


class TestInvalidMarketIdError:
    def test_is_market_error(self) -> None:
        assert issubclass(InvalidMarketIdError, MarketError)

    def test_attributes(self) -> None:
        exc = InvalidMarketIdError("bad-id", reason="contains hyphen")
        assert exc.identifier == "bad-id"
        assert exc.reason == "contains hyphen"
        assert exc.error_code == "MKT_001"
        assert "bad-id" in str(exc)


class TestExchangeNotFoundError:
    def test_is_market_error(self) -> None:
        assert issubclass(ExchangeNotFoundError, MarketError)

    def test_attributes(self) -> None:
        exc = ExchangeNotFoundError("UNKNOWN")
        assert exc.exchange_id == "UNKNOWN"
        assert exc.error_code == "MKT_002"
        assert "UNKNOWN" in str(exc)


class TestSegmentNotFoundError:
    def test_is_market_error(self) -> None:
        assert issubclass(SegmentNotFoundError, MarketError)

    def test_without_exchange(self) -> None:
        exc = SegmentNotFoundError("SEG1")
        assert exc.segment_id == "SEG1"
        assert exc.exchange_id is None

    def test_with_exchange(self) -> None:
        exc = SegmentNotFoundError("SEG1", exchange_id="NSE")
        assert "NSE" in str(exc)
        assert exc.error_code == "MKT_003"


class TestInvalidMarketStateError:
    def test_is_market_error(self) -> None:
        assert issubclass(InvalidMarketStateError, MarketError)

    def test_attributes(self) -> None:
        exc = InvalidMarketStateError("bad transition", from_state="closed", to_state="open")
        assert exc.from_state == "closed"
        assert exc.to_state == "open"
        assert exc.error_code == "MKT_004"

    def test_without_states(self) -> None:
        exc = InvalidMarketStateError("something wrong")
        assert exc.from_state is None
        assert exc.to_state is None


class TestInvalidScheduleError:
    def test_is_market_error(self) -> None:
        assert issubclass(InvalidScheduleError, MarketError)

    def test_construction(self) -> None:
        exc = InvalidScheduleError("sessions overlap", session_type="continuous")
        assert "sessions overlap" in str(exc)
        assert exc.error_code == "MKT_005"


class TestMarketHaltedError:
    def test_is_market_error(self) -> None:
        assert issubclass(MarketHaltedError, MarketError)

    def test_with_segment(self) -> None:
        exc = MarketHaltedError("NSE", segment_id="NSE_FO", halt_reason="circuit breaker")
        assert exc.exchange_id == "NSE"
        assert exc.segment_id == "NSE_FO"
        assert exc.halt_reason == "circuit breaker"
        assert exc.error_code == "MKT_006"
        assert "NSE" in str(exc)

    def test_without_segment(self) -> None:
        exc = MarketHaltedError("NSE")
        assert exc.segment_id is None
        assert exc.halt_reason == "unspecified"

    def test_caught_as_market_error(self) -> None:
        with pytest.raises(MarketError):
            raise MarketHaltedError("NSE")


class TestUnsupportedCapabilityError:
    def test_is_market_error(self) -> None:
        assert issubclass(UnsupportedCapabilityError, MarketError)

    def test_attributes(self) -> None:
        exc = UnsupportedCapabilityError("short_selling", "NSE", "NSE_EQ")
        assert exc.capability == "short_selling"
        assert exc.exchange_id == "NSE"
        assert exc.segment_id == "NSE_EQ"
        assert exc.error_code == "MKT_007"

    def test_without_segment(self) -> None:
        exc = UnsupportedCapabilityError("futures_trading", "BSE")
        assert exc.segment_id is None
        assert "BSE" in str(exc)
