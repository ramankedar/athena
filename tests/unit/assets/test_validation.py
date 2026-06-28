"""Unit tests for validation utilities."""

from __future__ import annotations

from decimal import Decimal

from athena.assets.classification import (
    AssetClass,
    ExchangeSegment,
    InstrumentType,
    OptionStyle,
    OptionType,
    SettlementType,
)
from athena.assets.contracts import EquitySpec, FuturesSpec
from athena.assets.identifiers import CurrencyCode, ExchangeId, InstrumentId, Symbol
from athena.assets.instruments import Instrument
from athena.assets.validation import (
    ValidationResult,
    is_valid_isin,
    is_valid_symbol_string,
    validate_contract,
    validate_instrument,
)

INR = CurrencyCode("INR")
USD = CurrencyCode("USD")
NSE = ExchangeId("NSE")
NIFTY = Symbol("NSE", "NIFTY50-INDEX")


class TestValidationResult:
    def test_ok_is_valid(self) -> None:
        r = ValidationResult.ok()
        assert r.is_valid is True
        assert r.failures == ()

    def test_failed_is_invalid(self) -> None:
        r = ValidationResult.failed("field x is wrong")
        assert r.is_valid is False
        assert "field x is wrong" in r.failures

    def test_failed_multiple_messages(self) -> None:
        r = ValidationResult.failed("err1", "err2")
        assert len(r.failures) == 2

    def test_merge_two_ok(self) -> None:
        result = ValidationResult.ok().merge(ValidationResult.ok())
        assert result.is_valid is True

    def test_merge_ok_and_failed(self) -> None:
        result = ValidationResult.ok().merge(ValidationResult.failed("bad"))
        assert result.is_valid is False
        assert "bad" in result.failures

    def test_merge_two_failed(self) -> None:
        r1 = ValidationResult.failed("err1")
        r2 = ValidationResult.failed("err2")
        merged = r1.merge(r2)
        assert not merged.is_valid
        assert len(merged.failures) == 2


class TestIsValidIsin:
    def test_valid_hdfc(self) -> None:
        assert is_valid_isin("INE040A01034") is True

    def test_valid_apple(self) -> None:
        assert is_valid_isin("US0231351067") is True

    def test_wrong_length(self) -> None:
        assert is_valid_isin("INE040A0103") is False

    def test_wrong_check_digit(self) -> None:
        assert is_valid_isin("INE040A01035") is False

    def test_numeric_country_code(self) -> None:
        assert is_valid_isin("12E040A010348") is False

    def test_empty_string(self) -> None:
        assert is_valid_isin("") is False

    def test_non_digit_check(self) -> None:
        assert is_valid_isin("INE040A0103X") is False


class TestIsValidSymbolString:
    def test_valid_nse_nifty(self) -> None:
        assert is_valid_symbol_string("NSE:NIFTY50-INDEX") is True

    def test_valid_mcx_gold(self) -> None:
        assert is_valid_symbol_string("MCX:GOLDPETAL") is True

    def test_no_colon(self) -> None:
        assert is_valid_symbol_string("NSENIFTY50INDEX") is False

    def test_empty_exchange(self) -> None:
        assert is_valid_symbol_string(":NIFTY50") is False

    def test_empty_ticker(self) -> None:
        assert is_valid_symbol_string("NSE:") is False

    def test_multiple_colons_in_ticker(self) -> None:
        assert is_valid_symbol_string("NSE:TICK:ER") is False


class TestValidateContract:
    def test_valid_equity_spec(self) -> None:
        spec = EquitySpec(Decimal("1"), Decimal("0.05"), INR)
        result = validate_contract(spec)
        assert result.is_valid

    def test_valid_futures_spec(self) -> None:
        from datetime import date

        from athena.assets.contracts import FuturesSpec

        spec = FuturesSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=date(2025, 1, 30),
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
        result = validate_contract(spec)
        assert result.is_valid

    def test_valid_currency_spec(self) -> None:
        from athena.assets.contracts import CurrencySpec

        spec = CurrencySpec(
            lot_size=Decimal("1000"),
            tick_size=Decimal("0.0025"),
            currency=INR,
            base_currency=USD,
            quote_currency=INR,
        )
        result = validate_contract(spec)
        assert result.is_valid

    def test_valid_etf_spec(self) -> None:
        from athena.assets.contracts import ETFSpec

        spec = ETFSpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.01"),
            currency=INR,
            total_expense_ratio=Decimal("0.0005"),
        )
        result = validate_contract(spec)
        assert result.is_valid

    def test_valid_index_spec(self) -> None:
        from athena.assets.contracts import IndexSpec

        spec = IndexSpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=INR,
            num_components=50,
        )
        result = validate_contract(spec)
        assert result.is_valid

    def test_valid_commodity_spec(self) -> None:
        from athena.assets.contracts import CommoditySpec

        spec = CommoditySpec(
            lot_size=Decimal("100"),
            tick_size=Decimal("1"),
            currency=INR,
            unit_of_measure="gram",
        )
        result = validate_contract(spec)
        assert result.is_valid

    def test_valid_options_spec(self) -> None:
        from datetime import date

        from athena.assets.contracts import OptionsSpec

        spec = OptionsSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=date(2025, 1, 30),
            strike=Decimal("24500"),
            option_type=OptionType.CALL,
            style=OptionStyle.EUROPEAN,
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
        result = validate_contract(spec)
        assert result.is_valid


class TestValidateInstrument:
    def test_valid_index_instrument(self, nifty_instrument: Instrument) -> None:
        result = validate_instrument(nifty_instrument)
        assert result.is_valid

    def test_valid_equity_instrument(self, hdfc_equity: Instrument) -> None:
        result = validate_instrument(hdfc_equity)
        assert result.is_valid

    def test_valid_option_instrument(self, nifty_call: Instrument) -> None:
        result = validate_instrument(nifty_call)
        assert result.is_valid

    def test_mismatched_asset_class_and_spec(self) -> None:
        # Equity asset class with FuturesSpec — should fail validation
        from datetime import date

        spec = FuturesSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=INR,
            underlying=NIFTY,
            expiry=date(2025, 1, 30),
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
        instr = Instrument(
            id=InstrumentId.generate(),
            symbol=Symbol("NSE", "HDFCBANK"),
            name="HDFC Bank",
            exchange=NSE,
            segment=ExchangeSegment.NSE_EQ,
            asset_class=AssetClass.EQUITY,  # wrong for FuturesSpec
            instrument_type=InstrumentType.COMMON_STOCK,
            contract=spec,
        )
        result = validate_instrument(instr)
        assert not result.is_valid
        assert any("EquitySpec" in msg for msg in result.failures)

    def test_mismatched_instrument_type(self) -> None:
        # INDEX asset class with COMMON_STOCK type — should fail
        from athena.assets.contracts import IndexSpec

        spec = IndexSpec(Decimal("1"), Decimal("0.05"), INR)
        instr = Instrument(
            id=InstrumentId.generate(),
            symbol=NIFTY,
            name="Nifty 50",
            exchange=NSE,
            segment=ExchangeSegment.NSE_EQ,
            asset_class=AssetClass.INDEX,
            instrument_type=InstrumentType.COMMON_STOCK,  # wrong for INDEX
            contract=spec,
        )
        result = validate_instrument(instr)
        assert not result.is_valid
