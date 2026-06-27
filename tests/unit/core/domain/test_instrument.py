"""Unit tests for the Instrument domain model."""

from __future__ import annotations

from decimal import Decimal

import pytest

from athena.core.domain.instrument import Exchange, Instrument, Segment
from athena.core.domain.primitives import Currency, Price, Quantity, Symbol


def _make_nifty() -> Instrument:
    return Instrument(
        symbol=Symbol("NSE:NIFTY50-INDEX"),
        exchange=Exchange.NSE,
        segment=Segment.INDEX,
        name="Nifty 50",
        lot_size=Quantity(Decimal("50")),
        tick_size=Price(Decimal("0.05")),
        currency=Currency("INR"),
    )


def _make_nifty_call() -> Instrument:
    return Instrument(
        symbol=Symbol("NSE:NIFTY25JAN24500CE"),
        exchange=Exchange.NSE,
        segment=Segment.OPTIONS,
        name="NIFTY 24500 CE JAN 2025",
        lot_size=Quantity(Decimal("50")),
        tick_size=Price(Decimal("0.05")),
        currency=Currency("INR"),
    )


class TestInstrumentImmutability:
    def test_is_frozen(self) -> None:
        instrument = _make_nifty()
        with pytest.raises(AttributeError):
            instrument.name = "Hacked"  # type: ignore[misc]

    def test_is_hashable(self) -> None:
        instrument = _make_nifty()
        assert hash(instrument) is not None

    def test_equal_instruments_have_equal_hash(self) -> None:
        assert hash(_make_nifty()) == hash(_make_nifty())

    def test_can_be_used_as_dict_key(self) -> None:
        mapping = {_make_nifty(): "value"}
        assert mapping[_make_nifty()] == "value"

    def test_duplicate_instruments_collapse_in_set(self) -> None:
        instrument_set = {_make_nifty(), _make_nifty(), _make_nifty()}
        assert len(instrument_set) == 1


class TestInstrumentProperties:
    def test_index_is_not_derivative(self) -> None:
        assert not _make_nifty().is_derivative

    def test_index_is_index(self) -> None:
        assert _make_nifty().is_index

    def test_option_is_derivative(self) -> None:
        assert _make_nifty_call().is_derivative

    def test_option_is_not_index(self) -> None:
        assert not _make_nifty_call().is_index


class TestExchangeEnum:
    def test_nse_value(self) -> None:
        assert Exchange.NSE == "NSE"

    def test_bse_value(self) -> None:
        assert Exchange.BSE == "BSE"

    def test_is_str(self) -> None:
        assert isinstance(Exchange.NSE, str)


class TestSegmentEnum:
    def test_index_value(self) -> None:
        assert Segment.INDEX == "INDEX"

    def test_futures_value(self) -> None:
        assert Segment.FUTURES == "FUT"

    def test_options_value(self) -> None:
        assert Segment.OPTIONS == "OPT"
