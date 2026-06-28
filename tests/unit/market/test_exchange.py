"""Unit tests for exchange metadata and repository."""

from __future__ import annotations

import dataclasses

import pytest

from athena.market.exceptions import ExchangeNotFoundError, InvalidMarketIdError
from athena.market.exchange import (
    BSE,
    KNOWN_EXCHANGES,
    MCX,
    NSE,
    NYSE,
    ExchangeMetadata,
    InMemoryExchangeRepository,
)
from athena.market.models import CountryCode, MarketCurrency, MarketId, MarketTimezone


class TestExchangeMetadata:
    def test_nse_constant(self) -> None:
        assert NSE.id == MarketId("NSE")
        assert NSE.short_name == "NSE"
        assert NSE.country == CountryCode("IN")
        assert NSE.primary_currency == MarketCurrency("INR")
        assert NSE.regulator == "SEBI"
        assert NSE.established_year == 1992
        assert NSE.mic_code == "XNSE"

    def test_bse_constant(self) -> None:
        assert BSE.id == MarketId("BSE")
        assert BSE.established_year == 1875

    def test_mcx_constant(self) -> None:
        assert MCX.id == MarketId("MCX")

    def test_nyse_constant(self) -> None:
        assert NYSE.id == MarketId("NYSE")
        assert NYSE.country == CountryCode("US")

    def test_is_frozen(self) -> None:
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            NSE.name = "Changed"  # type: ignore[misc]

    def test_str(self) -> None:
        assert "NSE" in str(NSE)

    def test_repr(self) -> None:
        r = repr(NSE)
        assert "NSE" in r
        assert "Asia/Kolkata" in r

    def test_empty_name_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="name"):
            ExchangeMetadata(
                id=MarketId("TEST"),
                name="",
                short_name="T",
                country=CountryCode("IN"),
                primary_currency=MarketCurrency("INR"),
                timezone=MarketTimezone("Asia/Kolkata"),
                regulator="SEBI",
            )

    def test_empty_short_name_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="short_name"):
            ExchangeMetadata(
                id=MarketId("TEST"),
                name="Test Exchange",
                short_name="",
                country=CountryCode("IN"),
                primary_currency=MarketCurrency("INR"),
                timezone=MarketTimezone("Asia/Kolkata"),
                regulator="SEBI",
            )

    def test_empty_regulator_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="regulator"):
            ExchangeMetadata(
                id=MarketId("TEST"),
                name="Test",
                short_name="T",
                country=CountryCode("IN"),
                primary_currency=MarketCurrency("INR"),
                timezone=MarketTimezone("Asia/Kolkata"),
                regulator="",
            )

    def test_implausible_year_raises(self) -> None:
        with pytest.raises(InvalidMarketIdError, match="predates"):
            ExchangeMetadata(
                id=MarketId("OLD"),
                name="Ancient Exchange",
                short_name="AE",
                country=CountryCode("IN"),
                primary_currency=MarketCurrency("INR"),
                timezone=MarketTimezone("Asia/Kolkata"),
                regulator="SEBI",
                established_year=1000,
            )

    def test_known_exchanges_dict(self) -> None:
        assert MarketId("NSE") in KNOWN_EXCHANGES
        assert MarketId("BSE") in KNOWN_EXCHANGES
        assert MarketId("MCX") in KNOWN_EXCHANGES
        assert KNOWN_EXCHANGES[MarketId("NSE")] is NSE


class TestInMemoryExchangeRepository:
    def test_preloaded_with_known_exchanges(self) -> None:
        repo = InMemoryExchangeRepository()
        assert len(repo) == len(KNOWN_EXCHANGES)

    def test_get_nse(self) -> None:
        repo = InMemoryExchangeRepository()
        result = repo.get(MarketId("NSE"))
        assert result is NSE

    def test_get_not_found_raises(self) -> None:
        repo = InMemoryExchangeRepository()
        with pytest.raises(ExchangeNotFoundError):
            repo.get(MarketId("UNKNOWN"))

    def test_get_or_none_found(self) -> None:
        repo = InMemoryExchangeRepository()
        assert repo.get_or_none(MarketId("NSE")) is NSE

    def test_get_or_none_not_found(self) -> None:
        repo = InMemoryExchangeRepository()
        assert repo.get_or_none(MarketId("UNKNOWN")) is None

    def test_exists_true(self) -> None:
        assert InMemoryExchangeRepository().exists(MarketId("NSE"))

    def test_exists_false(self) -> None:
        assert not InMemoryExchangeRepository().exists(MarketId("UNKNOWN"))

    def test_find_by_country_india(self) -> None:
        repo = InMemoryExchangeRepository()
        result = repo.find_by_country(CountryCode("IN"))
        ids = {e.id for e in result}
        assert MarketId("NSE") in ids
        assert MarketId("BSE") in ids
        assert MarketId("MCX") in ids

    def test_find_by_country_empty(self) -> None:
        repo = InMemoryExchangeRepository()
        result = repo.find_by_country(CountryCode("GB"))
        assert len(result) == 0

    def test_all_exchanges(self) -> None:
        repo = InMemoryExchangeRepository()
        assert len(repo.all_exchanges()) == len(KNOWN_EXCHANGES)

    def test_register_new(self) -> None:
        repo = InMemoryExchangeRepository(preload_known=False)
        assert len(repo) == 0
        repo.register(NSE)
        assert len(repo) == 1

    def test_register_overrides_existing(self) -> None:
        repo = InMemoryExchangeRepository()
        updated = ExchangeMetadata(
            id=MarketId("NSE"),
            name="NSE Updated",
            short_name="NSE",
            country=CountryCode("IN"),
            primary_currency=MarketCurrency("INR"),
            timezone=MarketTimezone("Asia/Kolkata"),
            regulator="SEBI",
        )
        repo.register(updated)
        assert repo.get(MarketId("NSE")).name == "NSE Updated"

    def test_empty_repository_when_preload_false(self) -> None:
        repo = InMemoryExchangeRepository(preload_known=False)
        assert len(repo) == 0

    def test_repr(self) -> None:
        repo = InMemoryExchangeRepository()
        assert "count=" in repr(repo)
