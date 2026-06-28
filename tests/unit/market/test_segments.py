"""Unit tests for market segments and trading venues."""

from __future__ import annotations

import pytest

from athena.market.exceptions import InvalidMarketIdError, SegmentNotFoundError
from athena.market.models import MarketId
from athena.market.segments import (
    KNOWN_SEGMENTS,
    MCX_FO,
    NSE_CDS,
    NSE_EQ,
    NSE_FO,
    InMemorySegmentRepository,
    MarketSegment,
    MarketSegmentType,
    TradingVenue,
)


class TestMarketSegment:
    def test_nse_eq_constant(self) -> None:
        assert NSE_EQ.id == MarketId("NSE_EQ")
        assert NSE_EQ.exchange_id == MarketId("NSE")
        assert NSE_EQ.segment_type == MarketSegmentType.CASH_EQUITY
        assert NSE_EQ.settlement_cycle == "T+1"

    def test_nse_fo_constant(self) -> None:
        assert NSE_FO.segment_type == MarketSegmentType.FUTURES_AND_OPTIONS

    def test_nse_cds_constant(self) -> None:
        assert NSE_CDS.segment_type == MarketSegmentType.CURRENCY_DERIVATIVES

    def test_mcx_fo_constant(self) -> None:
        assert MCX_FO.exchange_id == MarketId("MCX")
        assert MCX_FO.segment_type == MarketSegmentType.COMMODITY

    def test_str(self) -> None:
        assert str(NSE_EQ) == "NSE/NSE_EQ"

    def test_repr(self) -> None:
        r = repr(NSE_EQ)
        assert "NSE_EQ" in r
        assert "cash_equity" in r

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="name"):
            MarketSegment(
                id=MarketId("TEST"),
                exchange_id=MarketId("NSE"),
                segment_type=MarketSegmentType.CASH_EQUITY,
                name="",
            )

    def test_known_segments_dict(self) -> None:
        assert MarketId("NSE_EQ") in KNOWN_SEGMENTS
        assert MarketId("MCX_FO") in KNOWN_SEGMENTS


class TestMarketSegmentType:
    def test_values(self) -> None:
        assert MarketSegmentType.CASH_EQUITY == "cash_equity"
        assert MarketSegmentType.FUTURES_AND_OPTIONS == "futures_and_options"
        assert MarketSegmentType.CURRENCY_DERIVATIVES == "currency_derivatives"
        assert MarketSegmentType.COMMODITY == "commodity"
        assert MarketSegmentType.SME == "sme"
        assert MarketSegmentType.DEBT == "debt"
        assert MarketSegmentType.INSTITUTIONAL == "institutional"


class TestTradingVenue:
    def test_construction(self) -> None:
        venue = TradingVenue(
            id=MarketId("NSE_MAIN"),
            exchange_id=MarketId("NSE"),
            name="NSE Main Board",
            segment_ids=frozenset({MarketId("NSE_EQ"), MarketId("NSE_FO")}),
            is_primary_venue=True,
        )
        assert venue.is_primary_venue is True
        assert venue.is_dark_pool is False

    def test_serves_segment_true(self) -> None:
        venue = TradingVenue(
            id=MarketId("V1"),
            exchange_id=MarketId("NSE"),
            name="Venue 1",
            segment_ids=frozenset({MarketId("NSE_EQ")}),
        )
        assert venue.serves_segment(MarketId("NSE_EQ")) is True

    def test_serves_segment_false(self) -> None:
        venue = TradingVenue(
            id=MarketId("V1"),
            exchange_id=MarketId("NSE"),
            name="Venue 1",
            segment_ids=frozenset({MarketId("NSE_EQ")}),
        )
        assert venue.serves_segment(MarketId("NSE_FO")) is False

    def test_dark_pool_flag(self) -> None:
        dp = TradingVenue(
            id=MarketId("DARK"),
            exchange_id=MarketId("NSE"),
            name="Dark Pool",
            is_dark_pool=True,
            is_primary_venue=False,
        )
        assert dp.is_dark_pool is True

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="name"):
            TradingVenue(
                id=MarketId("V1"),
                exchange_id=MarketId("NSE"),
                name="",
            )

    def test_str(self) -> None:
        venue = TradingVenue(id=MarketId("V1"), exchange_id=MarketId("NSE"), name="V1")
        assert str(venue) == "NSE/V1"


class TestInMemorySegmentRepository:
    def test_preloaded_with_known_segments(self) -> None:
        repo = InMemorySegmentRepository()
        assert len(repo) == len(KNOWN_SEGMENTS)

    def test_get_nse_eq(self) -> None:
        repo = InMemorySegmentRepository()
        assert repo.get(MarketId("NSE_EQ")) is NSE_EQ

    def test_get_not_found_raises(self) -> None:
        repo = InMemorySegmentRepository()
        with pytest.raises(SegmentNotFoundError):
            repo.get(MarketId("UNKNOWN"))

    def test_get_or_none_found(self) -> None:
        repo = InMemorySegmentRepository()
        assert repo.get_or_none(MarketId("NSE_FO")) is NSE_FO

    def test_get_or_none_not_found(self) -> None:
        repo = InMemorySegmentRepository()
        assert repo.get_or_none(MarketId("UNKNOWN")) is None

    def test_find_by_exchange_nse(self) -> None:
        repo = InMemorySegmentRepository()
        nse_segs = repo.find_by_exchange(MarketId("NSE"))
        ids = {s.id for s in nse_segs}
        assert MarketId("NSE_EQ") in ids
        assert MarketId("NSE_FO") in ids

    def test_find_by_type_fo(self) -> None:
        repo = InMemorySegmentRepository()
        fo_segs = repo.find_by_type(MarketSegmentType.FUTURES_AND_OPTIONS)
        assert any(s.id == MarketId("NSE_FO") for s in fo_segs)
        assert any(s.id == MarketId("BSE_FO") for s in fo_segs)

    def test_all_segments(self) -> None:
        repo = InMemorySegmentRepository()
        assert len(repo.all_segments()) == len(KNOWN_SEGMENTS)

    def test_empty_when_preload_false(self) -> None:
        repo = InMemorySegmentRepository(preload_known=False)
        assert len(repo) == 0

    def test_register_new_segment(self) -> None:
        repo = InMemorySegmentRepository(preload_known=False)
        repo.register(NSE_EQ)
        assert len(repo) == 1
