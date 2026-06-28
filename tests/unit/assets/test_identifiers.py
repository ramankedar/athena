"""Unit tests for typed identifier value objects."""

from __future__ import annotations

import dataclasses
from uuid import UUID

import pytest

from athena.assets.exceptions import InvalidIdentifierError
from athena.assets.identifiers import (
    ISIN,
    CurrencyCode,
    ExchangeId,
    InstrumentId,
    Symbol,
    _compute_isin_check_digit,
)


class TestInstrumentId:
    def test_construction_from_uuid(self) -> None:
        uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
        iid = InstrumentId(uuid)
        assert iid.value == uuid

    def test_generate_produces_unique_ids(self) -> None:
        ids = {InstrumentId.generate() for _ in range(100)}
        assert len(ids) == 100

    def test_str_is_uuid_string(self) -> None:
        iid = InstrumentId.generate()
        assert str(iid) == str(iid.value)

    def test_from_string_valid_uuid(self) -> None:
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        iid = InstrumentId.from_string(uuid_str)
        assert str(iid.value) == uuid_str

    def test_from_string_invalid_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="valid UUID"):
            InstrumentId.from_string("not-a-uuid")

    def test_is_frozen(self) -> None:
        iid = InstrumentId.generate()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            iid.value = UUID("00000000-0000-0000-0000-000000000000")  # type: ignore[misc]

    def test_equality(self) -> None:
        uuid = UUID("550e8400-e29b-41d4-a716-446655440000")
        assert InstrumentId(uuid) == InstrumentId(uuid)

    def test_repr(self) -> None:
        iid = InstrumentId.from_string("550e8400-e29b-41d4-a716-446655440000")
        assert "550e8400" in repr(iid)


class TestExchangeId:
    def test_valid_nse(self) -> None:
        eid = ExchangeId("NSE")
        assert eid.code == "NSE"

    def test_str(self) -> None:
        assert str(ExchangeId("BSE")) == "BSE"

    def test_repr(self) -> None:
        assert "'MCX'" in repr(ExchangeId("MCX"))

    def test_empty_code_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="empty"):
            ExchangeId("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError):
            ExchangeId("   ")

    def test_lowercase_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="uppercase"):
            ExchangeId("nse")

    def test_mixed_case_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError):
            ExchangeId("Nse")

    def test_special_chars_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError):
            ExchangeId("NS-E")

    def test_is_frozen(self) -> None:
        eid = ExchangeId("NSE")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            eid.code = "BSE"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ExchangeId("NSE") == ExchangeId("NSE")
        assert ExchangeId("NSE") != ExchangeId("BSE")

    def test_hashable(self) -> None:
        mapping = {ExchangeId("NSE"): "nse", ExchangeId("BSE"): "bse"}
        assert mapping[ExchangeId("NSE")] == "nse"


class TestSymbol:
    def test_valid_construction(self) -> None:
        s = Symbol("NSE", "NIFTY50-INDEX")
        assert s.exchange_code == "NSE"
        assert s.ticker == "NIFTY50-INDEX"

    def test_str(self) -> None:
        assert str(Symbol("NSE", "HDFCBANK")) == "NSE:HDFCBANK"

    def test_repr(self) -> None:
        s = Symbol("NSE", "HDFCBANK")
        assert "NSE" in repr(s)
        assert "HDFCBANK" in repr(s)

    def test_parse_valid(self) -> None:
        s = Symbol.parse("NSE:NIFTY25JAN24500CE")
        assert s.exchange_code == "NSE"
        assert s.ticker == "NIFTY25JAN24500CE"

    def test_parse_no_separator_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="separator"):
            Symbol.parse("NSENIFTY50")

    def test_empty_exchange_code_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="exchange_code"):
            Symbol("", "NIFTY50")

    def test_empty_ticker_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="ticker"):
            Symbol("NSE", "")

    def test_ticker_with_colon_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="must not contain"):
            Symbol("NSE", "TICK:ER")

    def test_equality(self) -> None:
        assert Symbol("NSE", "NIFTY50-INDEX") == Symbol("NSE", "NIFTY50-INDEX")
        assert Symbol("NSE", "NIFTY50-INDEX") != Symbol("BSE", "NIFTY50-INDEX")

    def test_hashable_as_dict_key(self) -> None:
        mapping = {Symbol("NSE", "NIFTY50-INDEX"): "nifty"}
        assert mapping[Symbol("NSE", "NIFTY50-INDEX")] == "nifty"

    def test_is_frozen(self) -> None:
        s = Symbol("NSE", "TICKER")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            s.ticker = "OTHER"  # type: ignore[misc]


class TestISINCheckDigit:
    def test_hdfc_bank_india(self) -> None:
        assert _compute_isin_check_digit("INE040A0103") == 4

    def test_apple_us(self) -> None:
        assert _compute_isin_check_digit("US023135106") == 7

    def test_all_zeros(self) -> None:
        # Known Luhn property: all zeros with check 0 is valid
        result = _compute_isin_check_digit("US00000000" + "0")
        assert 0 <= result <= 9


class TestISIN:
    def test_valid_hdfc_bank(self) -> None:
        isin = ISIN("INE040A01034")
        assert isin.value == "INE040A01034"
        assert isin.country_code == "IN"
        assert isin.nsin == "E040A0103"
        assert isin.check_digit == 4

    def test_valid_apple(self) -> None:
        isin = ISIN("US0231351067")
        assert isin.country_code == "US"
        assert isin.check_digit == 7

    def test_str(self) -> None:
        assert str(ISIN("INE040A01034")) == "INE040A01034"

    def test_repr(self) -> None:
        assert "INE040A01034" in repr(ISIN("INE040A01034"))

    def test_wrong_length_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="12 characters"):
            ISIN("INE040A0103")  # 11 chars

    def test_non_alpha_country_raises(self) -> None:
        # 12-char ISIN where country code is numeric digits, not letters
        with pytest.raises(InvalidIdentifierError, match="alphabetic"):
            ISIN("12E040A01034")  # "12" is not an alpha country code

    def test_invalid_check_digit_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="check digit"):
            ISIN("INE040A01035")  # correct would be 4, not 5

    def test_non_alphanumeric_nsin_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="alphanumeric"):
            ISIN("IN!040A010348")  # ! in NSIN

    def test_non_digit_check_char_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="digit"):
            ISIN("INE040A0103X")  # X is not a digit

    def test_is_frozen(self) -> None:
        isin = ISIN("INE040A01034")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            isin.value = "US0231351067"  # type: ignore[misc]

    def test_equality(self) -> None:
        assert ISIN("INE040A01034") == ISIN("INE040A01034")
        assert ISIN("INE040A01034") != ISIN("US0231351067")


class TestCurrencyCode:
    def test_valid_inr(self) -> None:
        cc = CurrencyCode("INR")
        assert cc.code == "INR"

    def test_str(self) -> None:
        assert str(CurrencyCode("USD")) == "USD"

    def test_repr(self) -> None:
        assert "'EUR'" in repr(CurrencyCode("EUR"))

    def test_lowercase_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError, match="uppercase"):
            CurrencyCode("inr")

    def test_too_short_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError):
            CurrencyCode("IN")

    def test_too_long_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError):
            CurrencyCode("INRR")

    def test_numeric_raises(self) -> None:
        with pytest.raises(InvalidIdentifierError):
            CurrencyCode("1NR")

    def test_equality(self) -> None:
        assert CurrencyCode("INR") == CurrencyCode("INR")
        assert CurrencyCode("INR") != CurrencyCode("USD")

    def test_is_frozen(self) -> None:
        cc = CurrencyCode("INR")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            cc.code = "USD"  # type: ignore[misc]
