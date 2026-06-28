"""Unit tests for InstrumentQuery and InMemoryInstrumentRegistry."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from athena.assets.classification import (
    AssetClass,
    ExchangeSegment,
    InstrumentStatus,
    InstrumentType,
    SettlementType,
)
from athena.assets.exceptions import DuplicateInstrumentError, InstrumentNotFoundError
from athena.assets.identifiers import ISIN, CurrencyCode, ExchangeId, InstrumentId, Symbol
from athena.assets.instruments import Instrument
from athena.assets.registry import InMemoryInstrumentRegistry, InstrumentQuery

INR = CurrencyCode("INR")
NSE = ExchangeId("NSE")
MCX = ExchangeId("MCX")
NIFTY = Symbol("NSE", "NIFTY50-INDEX")
HDFC = Symbol("NSE", "HDFCBANK")
HDFC_ISIN = ISIN("INE040A01034")
EXPIRY = date(2025, 1, 30)


def _nifty() -> Instrument:
    return Instrument.index(
        symbol=NIFTY,
        name="Nifty 50",
        exchange=NSE,
        segment=ExchangeSegment.NSE_EQ,
        lot_size=Decimal("1"),
        tick_size=Decimal("0.05"),
        currency=INR,
        num_components=50,
    )


def _hdfc() -> Instrument:
    return Instrument.equity(
        symbol=HDFC,
        name="HDFC Bank",
        exchange=NSE,
        segment=ExchangeSegment.NSE_EQ,
        lot_size=Decimal("1"),
        tick_size=Decimal("0.05"),
        currency=INR,
        isin=HDFC_ISIN,
    )


def _nifty_futures() -> Instrument:
    return Instrument.futures(
        symbol=Symbol("NSE", "NIFTY25JANFUT"),
        name="NIFTY January Futures",
        exchange=NSE,
        segment=ExchangeSegment.NSE_FO,
        lot_size=Decimal("50"),
        tick_size=Decimal("0.05"),
        currency=INR,
        underlying=NIFTY,
        expiry=EXPIRY,
        settlement=SettlementType.CASH,
    )


class TestInstrumentQuery:
    def test_empty_query(self) -> None:
        q = InstrumentQuery()
        assert q.is_empty is True

    def test_non_empty_query(self) -> None:
        q = InstrumentQuery(asset_class=AssetClass.EQUITY)
        assert q.is_empty is False

    def test_is_frozen(self) -> None:
        import dataclasses

        q = InstrumentQuery()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            q.asset_class = AssetClass.EQUITY  # type: ignore[misc]

    def test_all_fields_none_by_default(self) -> None:
        q = InstrumentQuery()
        assert q.asset_class is None
        assert q.instrument_type is None
        assert q.exchange is None
        assert q.segment is None
        assert q.status is None
        assert q.name_contains is None
        assert q.isin is None


class TestInMemoryRegistryBasicOps:
    def test_empty_registry(self) -> None:
        registry = InMemoryInstrumentRegistry()
        assert len(registry) == 0
        assert repr(registry) == "InMemoryInstrumentRegistry(count=0)"

    def test_register_and_len(self) -> None:
        registry = InMemoryInstrumentRegistry()
        registry.register(_nifty())
        assert len(registry) == 1

    def test_register_duplicate_raises(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        with pytest.raises(DuplicateInstrumentError):
            registry.register(nifty)

    def test_remove_existing(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        removed = registry.remove(nifty.id)
        assert removed is True
        assert len(registry) == 0

    def test_remove_non_existent(self) -> None:
        registry = InMemoryInstrumentRegistry()
        removed = registry.remove(InstrumentId.generate())
        assert removed is False

    def test_exists_true(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        assert registry.exists(nifty.id) is True

    def test_exists_false(self) -> None:
        registry = InMemoryInstrumentRegistry()
        assert registry.exists(InstrumentId.generate()) is False


class TestInMemoryRegistryLookup:
    def test_get_by_id(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        found = registry.get(nifty.id)
        assert found == nifty

    def test_get_by_id_not_found(self) -> None:
        registry = InMemoryInstrumentRegistry()
        with pytest.raises(InstrumentNotFoundError, match="id"):
            registry.get(InstrumentId.generate())

    def test_get_or_none_found(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        assert registry.get_or_none(nifty.id) == nifty

    def test_get_or_none_not_found(self) -> None:
        registry = InMemoryInstrumentRegistry()
        assert registry.get_or_none(InstrumentId.generate()) is None

    def test_get_by_symbol(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        found = registry.get_by_symbol(NIFTY)
        assert found == nifty

    def test_get_by_symbol_not_found(self) -> None:
        registry = InMemoryInstrumentRegistry()
        with pytest.raises(InstrumentNotFoundError, match="symbol"):
            registry.get_by_symbol(Symbol("NSE", "UNKNOWN"))

    def test_get_by_isin_found(self) -> None:
        registry = InMemoryInstrumentRegistry()
        hdfc = _hdfc()
        registry.register(hdfc)
        found = registry.get_by_isin(HDFC_ISIN)
        assert found == hdfc

    def test_get_by_isin_not_found(self) -> None:
        registry = InMemoryInstrumentRegistry()
        assert registry.get_by_isin(ISIN("US0231351067")) is None

    def test_remove_clears_symbol_index(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        registry.remove(nifty.id)
        with pytest.raises(InstrumentNotFoundError):
            registry.get_by_symbol(NIFTY)

    def test_remove_clears_isin_index(self) -> None:
        registry = InMemoryInstrumentRegistry()
        hdfc = _hdfc()
        registry.register(hdfc)
        registry.remove(hdfc.id)
        assert registry.get_by_isin(HDFC_ISIN) is None


class TestInMemoryRegistrySearch:
    def _populated(self) -> InMemoryInstrumentRegistry:
        registry = InMemoryInstrumentRegistry()
        registry.register(_nifty())
        registry.register(_hdfc())
        registry.register(_nifty_futures())
        return registry

    def test_find_all_with_empty_query(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery())
        assert len(results) == 3

    def test_find_by_asset_class_index(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(asset_class=AssetClass.INDEX))
        assert len(results) == 1
        assert results[0].symbol == NIFTY

    def test_find_by_asset_class_derivative(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(asset_class=AssetClass.DERIVATIVE))
        assert len(results) == 1

    def test_find_by_segment(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(segment=ExchangeSegment.NSE_FO))
        assert len(results) == 1

    def test_find_by_name_contains(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(name_contains="nifty"))
        assert all("Nifty" in r.name or "NIFTY" in r.name for r in results)

    def test_find_by_status_active(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(status=InstrumentStatus.ACTIVE))
        assert len(results) == 3

    def test_find_by_status_expired_empty(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(status=InstrumentStatus.EXPIRED))
        assert len(results) == 0

    def test_find_by_isin(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(isin=HDFC_ISIN))
        assert len(results) == 1
        assert results[0].symbol == HDFC

    def test_find_by_instrument_type(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(instrument_type=InstrumentType.FUTURES))
        assert len(results) == 1

    def test_find_by_exchange(self) -> None:
        registry = self._populated()
        results = registry.find(InstrumentQuery(exchange=NSE))
        assert len(results) == 3  # all are on NSE

    def test_find_combined_filters(self) -> None:
        registry = self._populated()
        results = registry.find(
            InstrumentQuery(
                exchange=NSE,
                segment=ExchangeSegment.NSE_EQ,
            )
        )
        # Both NIFTY index (NSE_EQ) and HDFC equity (NSE_EQ)
        assert len(results) == 2

    def test_count_all(self) -> None:
        registry = self._populated()
        assert registry.count() == 3

    def test_count_by_asset_class(self) -> None:
        registry = self._populated()
        assert registry.count(AssetClass.EQUITY) == 1
        assert registry.count(AssetClass.INDEX) == 1
        assert registry.count(AssetClass.DERIVATIVE) == 1

    def test_all_symbols(self) -> None:
        registry = self._populated()
        symbols = registry.all_symbols()
        assert NIFTY in symbols
        assert HDFC in symbols

    def test_register_many_skips_duplicates(self) -> None:
        registry = InMemoryInstrumentRegistry()
        nifty = _nifty()
        registry.register(nifty)
        # Register the same instrument again via register_many — should skip
        added = registry.register_many((nifty, _hdfc()))
        assert added == 1
        assert registry.count() == 2
