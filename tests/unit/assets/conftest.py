"""Shared fixtures for asset domain tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from athena.assets.classification import (
    ExchangeSegment,
    OptionStyle,
    OptionType,
    SettlementType,
)
from athena.assets.identifiers import ISIN, CurrencyCode, ExchangeId, Symbol

INR = CurrencyCode("INR")
USD = CurrencyCode("USD")
NSE = ExchangeId("NSE")
BSE = ExchangeId("BSE")
MCX = ExchangeId("MCX")

NIFTY_SYMBOL = Symbol("NSE", "NIFTY50-INDEX")
HDFC_SYMBOL = Symbol("NSE", "HDFCBANK")
NIFTY_FUT_SYMBOL = Symbol("NSE", "NIFTY25JANFUT")
NIFTY_CALL_SYMBOL = Symbol("NSE", "NIFTY25JAN24500CE")

# Verified real ISINs
HDFC_ISIN = ISIN("INE040A01034")  # HDFC Bank
APPLE_ISIN = ISIN("US0231351067")  # Apple Inc.

EXPIRY_JAN_2025 = date(2025, 1, 30)


@pytest.fixture
def nifty_symbol() -> Symbol:
    return NIFTY_SYMBOL


@pytest.fixture
def hdfc_symbol() -> Symbol:
    return HDFC_SYMBOL


@pytest.fixture
def inr() -> CurrencyCode:
    return INR


@pytest.fixture
def nse() -> ExchangeId:
    return NSE


@pytest.fixture
def nifty_instrument() -> object:
    """Nifty 50 index instrument."""
    from athena.assets.instruments import Instrument

    return Instrument.index(
        symbol=NIFTY_SYMBOL,
        name="Nifty 50",
        exchange=NSE,
        segment=ExchangeSegment.NSE_EQ,
        lot_size=Decimal("1"),
        tick_size=Decimal("0.05"),
        currency=INR,
        num_components=50,
    )


@pytest.fixture
def hdfc_equity() -> object:
    """HDFC Bank equity instrument."""
    from athena.assets.instruments import Instrument

    return Instrument.equity(
        symbol=HDFC_SYMBOL,
        name="HDFC Bank Limited",
        exchange=NSE,
        segment=ExchangeSegment.NSE_EQ,
        lot_size=Decimal("1"),
        tick_size=Decimal("0.05"),
        currency=INR,
        isin=HDFC_ISIN,
        face_value=Decimal("1"),
    )


@pytest.fixture
def nifty_call() -> object:
    """NIFTY 24500 CE January 2025 options contract."""
    from athena.assets.instruments import Instrument

    return Instrument.option(
        symbol=NIFTY_CALL_SYMBOL,
        name="NIFTY 24500 CE JAN 2025",
        exchange=NSE,
        segment=ExchangeSegment.NSE_FO,
        lot_size=Decimal("50"),
        tick_size=Decimal("0.05"),
        currency=INR,
        underlying=NIFTY_SYMBOL,
        expiry=EXPIRY_JAN_2025,
        strike=Decimal("24500"),
        option_type=OptionType.CALL,
        style=OptionStyle.EUROPEAN,
        settlement=SettlementType.CASH,
    )
