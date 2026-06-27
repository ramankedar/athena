"""Primitive value types for the Athena domain.

These are NewType wrappers over Decimal and str. NewType creates a distinct
type at the mypy level while remaining the underlying type at runtime — so
arithmetic, comparison, and Decimal methods all work without casting.

Why Decimal and not float:
    Financial calculations require exact decimal representation.
    float(0.1) + float(0.2) != float(0.3) — unacceptable for P&L accounting.
    Decimal arithmetic is exact within its precision.
"""

from decimal import Decimal
from typing import NewType

# Monetary price of a single unit of an instrument (e.g. 24500.50 INR).
Price = NewType("Price", Decimal)

# Number of units (contracts, shares, lots). Always positive or zero.
Quantity = NewType("Quantity", Decimal)

# ISO 4217 currency code. Athena operates exclusively in INR at launch.
Currency = NewType("Currency", str)

# Fully-qualified instrument symbol: "{EXCHANGE}:{TICKER}".
# Examples: "NSE:NIFTY50-INDEX", "NSE:NIFTY25JAN24500CE"
Symbol = NewType("Symbol", str)


def price(value: str | int | float | Decimal) -> Price:
    """Construct a Price from any numeric representation."""
    return Price(Decimal(str(value)))


def quantity(value: str | int | float | Decimal) -> Quantity:
    """Construct a Quantity from any numeric representation."""
    return Quantity(Decimal(str(value)))
