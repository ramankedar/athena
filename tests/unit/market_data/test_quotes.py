"""Unit tests for Quote."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from athena.core.domain.primitives import Price, Quantity, Symbol
from athena.market_data.exceptions import InvalidQuoteError
from athena.market_data.quality import DataQuality, QualityFlag
from athena.market_data.quotes import Quote

NIFTY = Symbol("NSE:NIFTY50-INDEX")
NOW = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)


class TestQuote:
    def test_valid_quote(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("24490")),
            ask_price=Price(Decimal("24510")),
            bid_size=Quantity(Decimal("50")),
            ask_size=Quantity(Decimal("100")),
        )
        assert q.spread == Price(Decimal("20"))
        assert q.mid_price == Price(Decimal("24500"))

    def test_naive_timestamp_raises(self) -> None:
        with pytest.raises(InvalidQuoteError, match="timezone-aware"):
            Quote(symbol=NIFTY, timestamp_utc=datetime(2025, 1, 15, 9, 15))

    def test_zero_bid_price_raises(self) -> None:
        with pytest.raises(InvalidQuoteError, match="bid_price"):
            Quote(
                symbol=NIFTY,
                timestamp_utc=NOW,
                bid_price=Price(Decimal("0")),
                ask_price=Price(Decimal("100")),
            )

    def test_zero_ask_price_raises(self) -> None:
        with pytest.raises(InvalidQuoteError, match="ask_price"):
            Quote(
                symbol=NIFTY,
                timestamp_utc=NOW,
                bid_price=Price(Decimal("100")),
                ask_price=Price(Decimal("0")),
            )

    def test_negative_bid_size_raises(self) -> None:
        with pytest.raises(InvalidQuoteError, match="bid_size"):
            Quote(
                symbol=NIFTY,
                timestamp_utc=NOW,
                bid_size=Quantity(Decimal("-1")),
            )

    def test_spread_none_when_one_side_missing(self) -> None:
        q = Quote(symbol=NIFTY, timestamp_utc=NOW, bid_price=Price(Decimal("100")))
        assert q.spread is None

    def test_mid_price_none_when_one_side_missing(self) -> None:
        q = Quote(symbol=NIFTY, timestamp_utc=NOW, ask_price=Price(Decimal("100")))
        assert q.mid_price is None

    def test_is_crossed(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("24510")),
            ask_price=Price(Decimal("24490")),  # bid > ask
        )
        assert q.is_crossed is True

    def test_not_crossed(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("24490")),
            ask_price=Price(Decimal("24510")),
        )
        assert q.is_crossed is False

    def test_is_crossed_false_when_one_side_missing(self) -> None:
        q = Quote(symbol=NIFTY, timestamp_utc=NOW, bid_price=Price(Decimal("100")))
        assert q.is_crossed is False

    def test_effective_quality_crossed_market(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("200")),
            ask_price=Price(Decimal("100")),
        )
        eq = q.effective_quality
        assert QualityFlag.CROSSED_MARKET in eq.flags
        assert eq.confidence <= 0.1

    def test_effective_quality_good(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("100")),
            ask_price=Price(Decimal("110")),
            quality=DataQuality.good(),
        )
        eq = q.effective_quality
        assert QualityFlag.COMPLETE in eq.flags

    def test_effective_quality_no_quality_field(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("100")),
            ask_price=Price(Decimal("110")),
        )
        eq = q.effective_quality
        assert eq.is_reliable

    def test_effective_quality_crossed_with_existing_quality(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("200")),
            ask_price=Price(Decimal("100")),
            quality=DataQuality.with_flags(QualityFlag.STALE_TIMESTAMP, confidence=0.3),
        )
        eq = q.effective_quality
        assert QualityFlag.CROSSED_MARKET in eq.flags
        assert QualityFlag.STALE_TIMESTAMP in eq.flags

    def test_str(self) -> None:
        q = Quote(
            symbol=NIFTY,
            timestamp_utc=NOW,
            bid_price=Price(Decimal("100")),
            ask_price=Price(Decimal("110")),
        )
        assert "NSE:NIFTY50-INDEX" in str(q)
