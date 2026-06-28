"""Unit tests for the Instrument value object and factory constructors."""

from __future__ import annotations

import dataclasses
from datetime import date
from decimal import Decimal

import pytest

from athena.assets.classification import (
    AssetClass,
    ExchangeSegment,
    InstrumentType,
    OptionType,
    SettlementType,
)
from athena.assets.contracts import (
    CommoditySpec,
    CurrencySpec,
    EquitySpec,
    ETFSpec,
    FuturesSpec,
    IndexSpec,
    OptionsSpec,
)
from athena.assets.exceptions import InvalidInstrumentError
from athena.assets.identifiers import ISIN, CurrencyCode, ExchangeId, InstrumentId, Symbol
from athena.assets.instruments import Instrument

INR = CurrencyCode("INR")
USD = CurrencyCode("USD")
NSE = ExchangeId("NSE")
MCX = ExchangeId("MCX")
NIFTY = Symbol("NSE", "NIFTY50-INDEX")
HDFC = Symbol("NSE", "HDFCBANK")
EXPIRY = date(2025, 1, 30)


class TestInstrumentConstruction:
    def test_direct_construction(self) -> None:
        spec = IndexSpec(Decimal("1"), Decimal("0.05"), INR)
        instr = Instrument(
            id=InstrumentId.generate(),
            symbol=NIFTY,
            name="Nifty 50",
            exchange=NSE,
            segment=ExchangeSegment.NSE_EQ,
            asset_class=AssetClass.INDEX,
            instrument_type=InstrumentType.BROAD_MARKET_INDEX,
            contract=spec,
        )
        assert instr.name == "Nifty 50"

    def test_empty_name_raises(self) -> None:
        spec = IndexSpec(Decimal("1"), Decimal("0.05"), INR)
        with pytest.raises(InvalidInstrumentError, match="name"):
            Instrument(
                id=InstrumentId.generate(),
                symbol=NIFTY,
                name="   ",
                exchange=NSE,
                segment=ExchangeSegment.NSE_EQ,
                asset_class=AssetClass.INDEX,
                instrument_type=InstrumentType.BROAD_MARKET_INDEX,
                contract=spec,
            )

    def test_is_frozen(self) -> None:
        spec = IndexSpec(Decimal("1"), Decimal("0.05"), INR)
        instr = Instrument(
            id=InstrumentId.generate(),
            symbol=NIFTY,
            name="Nifty 50",
            exchange=NSE,
            segment=ExchangeSegment.NSE_EQ,
            asset_class=AssetClass.INDEX,
            instrument_type=InstrumentType.BROAD_MARKET_INDEX,
            contract=spec,
        )
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            instr.name = "Changed"  # type: ignore[misc]


class TestInstrumentProperties:
    def test_currency_delegates_to_contract(self, nifty_instrument: Instrument) -> None:
        assert nifty_instrument.currency == INR

    def test_is_derivative_false_for_index(self, nifty_instrument: Instrument) -> None:
        assert nifty_instrument.is_derivative is False

    def test_is_derivative_true_for_option(self, nifty_call: Instrument) -> None:
        assert nifty_call.is_derivative is True

    def test_is_active_default(self, nifty_instrument: Instrument) -> None:
        assert nifty_instrument.is_active is True

    def test_is_expired_false_for_active(self, nifty_instrument: Instrument) -> None:
        assert nifty_instrument.is_expired is False

    def test_is_index(self, nifty_instrument: Instrument) -> None:
        assert nifty_instrument.is_index is True

    def test_is_index_false_for_option(self, nifty_call: Instrument) -> None:
        assert nifty_call.is_index is False

    def test_str_is_symbol(self, nifty_instrument: Instrument) -> None:
        assert str(nifty_instrument) == "NSE:NIFTY50-INDEX"

    def test_repr_contains_id_and_symbol(self, nifty_instrument: Instrument) -> None:
        r = repr(nifty_instrument)
        assert "NSE:NIFTY50-INDEX" in r
        assert "broad_market_index" in r


class TestEquityFactory:
    def test_creates_equity_instrument(self, hdfc_equity: Instrument) -> None:
        assert hdfc_equity.asset_class == AssetClass.EQUITY
        assert hdfc_equity.instrument_type == InstrumentType.COMMON_STOCK
        assert isinstance(hdfc_equity.contract, EquitySpec)

    def test_generates_id_when_not_provided(self, hdfc_equity: Instrument) -> None:
        assert hdfc_equity.id is not None

    def test_uses_provided_id(self) -> None:
        iid = InstrumentId.generate()
        instr = Instrument.equity(
            symbol=HDFC,
            name="HDFC Bank",
            exchange=NSE,
            segment=ExchangeSegment.NSE_EQ,
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
            instrument_id=iid,
        )
        assert instr.id == iid

    def test_isin_stored_on_instrument(self, hdfc_equity: Instrument) -> None:
        assert hdfc_equity.isin == ISIN("INE040A01034")

    def test_preferred_stock_type(self) -> None:
        instr = Instrument.equity(
            symbol=Symbol("NSE", "PREFSTOCK"),
            name="Pref Stock",
            exchange=NSE,
            segment=ExchangeSegment.NSE_EQ,
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
            instrument_type=InstrumentType.PREFERRED_STOCK,
        )
        assert instr.instrument_type == InstrumentType.PREFERRED_STOCK


class TestIndexFactory:
    def test_creates_index_instrument(self, nifty_instrument: Instrument) -> None:
        assert nifty_instrument.asset_class == AssetClass.INDEX
        assert nifty_instrument.instrument_type == InstrumentType.BROAD_MARKET_INDEX
        assert isinstance(nifty_instrument.contract, IndexSpec)

    def test_num_components_in_spec(self, nifty_instrument: Instrument) -> None:
        assert isinstance(nifty_instrument.contract, IndexSpec)
        assert nifty_instrument.contract.num_components == 50


class TestFuturesFactory:
    def test_creates_futures_instrument(self) -> None:
        instr = Instrument.futures(
            symbol=Symbol("NSE", "NIFTY25JANFUT"),
            name="NIFTY January 2025 Futures",
            exchange=NSE,
            segment=ExchangeSegment.NSE_FO,
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=EXPIRY,
        )
        assert instr.asset_class == AssetClass.DERIVATIVE
        assert instr.instrument_type == InstrumentType.FUTURES
        assert isinstance(instr.contract, FuturesSpec)

    def test_settlement_default_cash(self) -> None:
        instr = Instrument.futures(
            symbol=Symbol("NSE", "NIFTY25JANFUT"),
            name="NIFTY Futures",
            exchange=NSE,
            segment=ExchangeSegment.NSE_FO,
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=EXPIRY,
        )
        assert isinstance(instr.contract, FuturesSpec)
        assert instr.contract.settlement == SettlementType.CASH


class TestOptionFactory:
    def test_creates_call_option(self, nifty_call: Instrument) -> None:
        assert nifty_call.asset_class == AssetClass.DERIVATIVE
        assert nifty_call.instrument_type == InstrumentType.CALL_OPTION
        assert isinstance(nifty_call.contract, OptionsSpec)

    def test_creates_put_option(self) -> None:
        instr = Instrument.option(
            symbol=Symbol("NSE", "NIFTY25JAN24500PE"),
            name="NIFTY 24500 PE JAN 2025",
            exchange=NSE,
            segment=ExchangeSegment.NSE_FO,
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=EXPIRY,
            strike=Decimal("24500"),
            option_type=OptionType.PUT,
        )
        assert instr.instrument_type == InstrumentType.PUT_OPTION

    def test_call_spec_properties(self, nifty_call: Instrument) -> None:
        assert isinstance(nifty_call.contract, OptionsSpec)
        assert nifty_call.contract.is_call is True
        assert nifty_call.contract.strike == Decimal("24500")


class TestETFFactory:
    def test_creates_etf(self) -> None:
        instr = Instrument.etf(
            symbol=Symbol("NSE", "NIFTYBEES"),
            name="Nippon India ETF Nifty BeES",
            exchange=NSE,
            segment=ExchangeSegment.NSE_EQ,
            lot_size=Decimal("1"),
            tick_size=Decimal("0.01"),
            currency=INR,
            tracking_index=NIFTY,
            total_expense_ratio=Decimal("0.0005"),
        )
        assert instr.asset_class == AssetClass.ETF
        assert isinstance(instr.contract, ETFSpec)


class TestCurrencyPairFactory:
    def test_creates_fx_instrument(self) -> None:
        instr = Instrument.currency_pair(
            symbol=Symbol("NSE", "USDINR"),
            name="USD/INR",
            exchange=NSE,
            segment=ExchangeSegment.NSE_CDS,
            lot_size=Decimal("1000"),
            tick_size=Decimal("0.0025"),
            base_currency=USD,
            quote_currency=INR,
        )
        assert instr.asset_class == AssetClass.CURRENCY
        assert isinstance(instr.contract, CurrencySpec)

    def test_currency_field_is_quote_currency(self) -> None:
        instr = Instrument.currency_pair(
            symbol=Symbol("NSE", "USDINR"),
            name="USD/INR",
            exchange=NSE,
            segment=ExchangeSegment.NSE_CDS,
            lot_size=Decimal("1000"),
            tick_size=Decimal("0.0025"),
            base_currency=USD,
            quote_currency=INR,
        )
        assert instr.currency == INR


class TestCommodityFactory:
    def test_creates_commodity_instrument(self) -> None:
        instr = Instrument.commodity(
            symbol=Symbol("MCX", "GOLDPETAL"),
            name="Gold Petal",
            exchange=MCX,
            segment=ExchangeSegment.MCX_FO,
            lot_size=Decimal("100"),
            tick_size=Decimal("1"),
            currency=INR,
            unit_of_measure="gram",
            expiry=date(2025, 2, 5),
            quality_grade="999.9 fine gold",
        )
        assert instr.asset_class == AssetClass.COMMODITY
        assert isinstance(instr.contract, CommoditySpec)

    def test_unit_of_measure_in_spec(self) -> None:
        instr = Instrument.commodity(
            symbol=Symbol("MCX", "GOLDPETAL"),
            name="Gold",
            exchange=MCX,
            segment=ExchangeSegment.MCX_FO,
            lot_size=Decimal("100"),
            tick_size=Decimal("1"),
            currency=INR,
            unit_of_measure="gram",
        )
        assert isinstance(instr.contract, CommoditySpec)
        assert instr.contract.unit_of_measure == "gram"
