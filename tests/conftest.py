"""Global pytest fixtures shared across all test tiers.

Fixtures defined here are available to every test file without import.
Engine-specific fixtures belong in the relevant tier's conftest.py.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from athena.core.domain.instrument import Exchange, Instrument, Segment
from athena.core.domain.primitives import Currency, Price, Quantity, Symbol


@pytest.fixture(scope="session")
def nifty() -> Instrument:
    """Canonical NIFTY 50 index instrument for use in tests."""
    return Instrument(
        symbol=Symbol("NSE:NIFTY50-INDEX"),
        exchange=Exchange.NSE,
        segment=Segment.INDEX,
        name="Nifty 50",
        lot_size=Quantity(Decimal("50")),
        tick_size=Price(Decimal("0.05")),
        currency=Currency("INR"),
    )


@pytest.fixture(scope="session")
def banknifty() -> Instrument:
    """Canonical BANKNIFTY index instrument for use in tests."""
    return Instrument(
        symbol=Symbol("NSE:NIFTYBANK-INDEX"),
        exchange=Exchange.NSE,
        segment=Segment.INDEX,
        name="Nifty Bank",
        lot_size=Quantity(Decimal("15")),
        tick_size=Price(Decimal("0.05")),
        currency=Currency("INR"),
    )


@pytest.fixture(scope="session")
def nifty_call() -> Instrument:
    """A representative NIFTY call option for derivative tests."""
    return Instrument(
        symbol=Symbol("NSE:NIFTY25JAN24500CE"),
        exchange=Exchange.NSE,
        segment=Segment.OPTIONS,
        name="NIFTY 24500 CE JAN 2025",
        lot_size=Quantity(Decimal("50")),
        tick_size=Price(Decimal("0.05")),
        currency=Currency("INR"),
    )
