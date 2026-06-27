"""Instrument domain model.

An Instrument is the atomic unit of what can be traded on the platform.
It is immutable — market metadata (lot size, tick size) is fixed per
contract specification and only changes on exchange notice.

The platform currently supports NSE and BSE instruments. MCX (commodity
derivatives) and NSE CDS (currency derivatives) are defined but not
activated until the instrument universe is expanded.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.core.domain.primitives import Currency, Price, Quantity, Symbol


class Exchange(StrEnum):
    """Recognised exchanges. Values match Fyers API exchange identifiers."""

    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"  # Commodity - planned
    NSE_CDS = "NSE_CDS"  # Currency derivatives - planned


class Segment(StrEnum):
    """Market segment within an exchange."""

    INDEX = "INDEX"
    EQUITY = "EQ"
    FUTURES = "FUT"
    OPTIONS = "OPT"


class OptionType(StrEnum):
    CALL = "CE"
    PUT = "PE"


@dataclass(frozen=True)
class Instrument:
    """Immutable description of a tradable instrument.

    This is a value object: two Instruments with identical fields are equal.
    Frozen dataclasses are hashable and safe to use as dict keys or set members.
    """

    symbol: Symbol
    exchange: Exchange
    segment: Segment
    name: str
    lot_size: Quantity
    tick_size: Price
    currency: Currency

    def __str__(self) -> str:
        return f"{self.exchange}:{self.symbol}"

    @property
    def is_derivative(self) -> bool:
        return self.segment in (Segment.FUTURES, Segment.OPTIONS)

    @property
    def is_index(self) -> bool:
        return self.segment == Segment.INDEX
