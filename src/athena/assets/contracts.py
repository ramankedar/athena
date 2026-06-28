"""Contract specification value objects.

A ``ContractSpec`` defines the quantitative and structural parameters of a
financial instrument's contract. It is composed into an ``Instrument`` and
carries the information needed to compute P&L, margin, and settlement values.

Hierarchy::

    ContractSpec          — shared fields: lot_size, tick_size, currency
    ├── EquitySpec        — equity-specific: isin, face_value
    ├── IndexSpec         — index-specific: base_value, base_date
    ├── FuturesSpec       — futures: underlying, expiry, multiplier, settlement
    ├── OptionsSpec       — options: + strike, option_type, style
    ├── ETFSpec           — ETF: tracking_index, expense_ratio
    ├── CurrencySpec      — FX: base_currency, quote_currency, pip_size
    └── CommoditySpec     — commodities: underlying, expiry, unit_of_measure

Design decisions:
    - ``ContractSpec`` is the common base; all required fields have no defaults.
      Subclass fields with sensible defaults come after.
    - ``lot_size`` uses ``Decimal`` (not ``int``) for future-proofing: some
      markets allow fractional lots (ETF fractions, FX micro-lots).
    - Validation happens in each class's ``__post_init__``, raising
      ``InvalidContractSpecError`` rather than generic ``ValueError``.
    - ``FuturesSpec.underlying`` and ``OptionsSpec.underlying`` hold a ``Symbol``
      (not a full ``Instrument``) to prevent circular references. The registry
      resolves the full instrument on demand.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from athena.assets.classification import SettlementType
from athena.assets.exceptions import InvalidContractSpecError

if TYPE_CHECKING:
    from datetime import date

    from athena.assets.classification import OptionStyle, OptionType
    from athena.assets.identifiers import ISIN, CurrencyCode, Symbol


def _require_positive(field: str, value: Decimal) -> None:
    """Raise ``InvalidContractSpecError`` if ``value`` is not strictly positive."""
    if value <= Decimal(0):
        raise InvalidContractSpecError(
            field=field,
            value=value,
            reason="must be strictly positive (> 0)",
        )


# ── Base spec ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContractSpec:
    """Shared contract parameters common to all asset classes.

    This is the base class for all concrete spec types. It should not be
    instantiated directly — use one of the typed subclasses.

    Attributes:
        lot_size: Minimum tradable quantity (number of units per contract).
            Must be positive. Typical values: 1 (equity), 50 (NIFTY options).
        tick_size: Smallest allowable price movement. Must be positive.
            Typical values: ``Decimal("0.05")`` (index), ``Decimal("0.01")``
            (equity), ``Decimal("1")`` (certain commodity contracts).
        currency: Settlement currency for this contract (ISO 4217).
    """

    lot_size: Decimal
    tick_size: Decimal
    currency: CurrencyCode

    def __post_init__(self) -> None:
        _require_positive("lot_size", self.lot_size)
        _require_positive("tick_size", self.tick_size)

    @property
    def tick_value(self) -> Decimal:
        """Value of one tick move per lot.

        Returns:
            ``tick_size * lot_size``.
        """
        return self.tick_size * self.lot_size


# ── Equity ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EquitySpec(ContractSpec):
    """Contract specification for common and preferred stock.

    Attributes:
        lot_size:   Number of shares per exchange lot. Almost always 1 for
            cash equities; may differ in SME segment.
        tick_size:  Minimum price movement. Typically ``Decimal("0.05")`` on NSE.
        currency:   Settlement currency.
        isin:       Optional ISO 6166 ISIN. Present for most listed equities.
        face_value: Par/face value per share (e.g. ``Decimal("10")`` for most
            Indian companies). Used for dividend and rights calculations.

    Example::

        spec = EquitySpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=CurrencyCode("INR"),
            isin=ISIN("INE040A01034"),
            face_value=Decimal("1"),
        )
    """

    isin: ISIN | None = None
    face_value: Decimal | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.face_value is not None and self.face_value <= Decimal(0):
            raise InvalidContractSpecError(
                field="face_value",
                value=self.face_value,
                reason="face value must be positive when provided",
            )


# ── Index ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class IndexSpec(ContractSpec):
    """Contract specification for a market index.

    Indices are non-tradable instruments but appear in the instrument master
    as the underlying reference for derivatives. The ``lot_size`` and
    ``tick_size`` represent the index's effective parameters for computing
    contract values when the index is an underlying.

    Attributes:
        lot_size:       Effective lot size. Typically ``Decimal("1")``.
        tick_size:      Minimum index move (e.g. ``Decimal("0.05")`` for NIFTY 50).
        currency:       Index currency.
        base_value:     Initial index value at inception (e.g. ``Decimal("1000")``).
        base_date:      Date the index was established at ``base_value``.
        num_components: Number of constituent securities in the index.

    Example::

        spec = IndexSpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=CurrencyCode("INR"),
            base_value=Decimal("1000"),
            num_components=50,
        )
    """

    base_value: Decimal | None = None
    base_date: date | None = None
    num_components: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.base_value is not None and self.base_value <= Decimal(0):
            raise InvalidContractSpecError(
                field="base_value",
                value=self.base_value,
                reason="index base value must be positive when provided",
            )
        if self.num_components is not None and self.num_components < 1:
            raise InvalidContractSpecError(
                field="num_components",
                value=self.num_components,
                reason="index must have at least 1 component when specified",
            )


# ── Futures ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FuturesSpec(ContractSpec):
    """Contract specification for a futures contract.

    Attributes:
        lot_size:    Number of units of underlying per contract (e.g. 50 for NIFTY).
        tick_size:   Minimum price move.
        currency:    Settlement currency.
        underlying:  ``Symbol`` of the underlying instrument.
        expiry:      Contract expiry / last trading date.
        multiplier:  Contract value multiplier. For Indian index futures,
            ``contract value = index_price * multiplier``. Typically
            ``Decimal("1")`` when lot_size already encodes contract size.
        settlement:  Cash or physical settlement at expiry.

    Example::

        spec = FuturesSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=CurrencyCode("INR"),
            underlying=Symbol.parse("NSE:NIFTY50-INDEX"),
            expiry=date(2025, 1, 30),
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
    """

    underlying: Symbol
    expiry: date
    multiplier: Decimal
    settlement: SettlementType

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_positive("multiplier", self.multiplier)


# ── Options ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OptionsSpec(ContractSpec):
    """Contract specification for an options contract (call or put).

    Attributes:
        lot_size:     Number of units of underlying per contract.
        tick_size:    Minimum premium move.
        currency:     Premium and settlement currency.
        underlying:   ``Symbol`` of the underlying instrument.
        expiry:       Option expiry date (last day to exercise).
        strike:       Exercise price of the option. Must be positive.
        option_type:  ``CALL`` (right to buy) or ``PUT`` (right to sell).
        style:        ``EUROPEAN`` (at expiry only) or ``AMERICAN`` (any time).
        multiplier:   Contract value multiplier (typically ``Decimal("1")``).
        settlement:   Cash or physical settlement.

    Example::

        spec = OptionsSpec(
            lot_size=Decimal("50"),
            tick_size=Decimal("0.05"),
            currency=CurrencyCode("INR"),
            underlying=Symbol.parse("NSE:NIFTY50-INDEX"),
            expiry=date(2025, 1, 30),
            strike=Decimal("24500"),
            option_type=OptionType.CALL,
            style=OptionStyle.EUROPEAN,
            multiplier=Decimal("1"),
            settlement=SettlementType.CASH,
        )
    """

    underlying: Symbol
    expiry: date
    strike: Decimal
    option_type: OptionType
    style: OptionStyle
    multiplier: Decimal
    settlement: SettlementType

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_positive("strike", self.strike)
        _require_positive("multiplier", self.multiplier)

    @property
    def is_call(self) -> bool:
        """Return ``True`` if this is a call option.

        Returns:
            ``True`` when ``option_type == OptionType.CALL``.
        """
        from athena.assets.classification import OptionType

        return self.option_type == OptionType.CALL

    @property
    def is_put(self) -> bool:
        """Return ``True`` if this is a put option.

        Returns:
            ``True`` when ``option_type == OptionType.PUT``.
        """
        from athena.assets.classification import OptionType

        return self.option_type == OptionType.PUT


# ── ETF ────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ETFSpec(ContractSpec):
    """Contract specification for an exchange-traded fund.

    ETFs trade like equities but track an underlying index, commodity, or
    basket of assets. They have ISINs and are listed on the equity segment.

    Attributes:
        lot_size:            Typically ``Decimal("1")`` (unit-based trading).
        tick_size:           Minimum NAV-based price move.
        currency:            Fund currency.
        tracking_index:      ``Symbol`` of the index or asset being tracked.
            ``None`` for actively-managed ETFs.
        total_expense_ratio: Annual management cost as a fraction
            (e.g. ``Decimal("0.0007")`` = 0.07% TER). Must be in [0, 1).
        isin:                ISIN for cross-exchange identification.

    Example::

        spec = ETFSpec(
            lot_size=Decimal("1"),
            tick_size=Decimal("0.01"),
            currency=CurrencyCode("INR"),
            tracking_index=Symbol.parse("NSE:NIFTY50-INDEX"),
            total_expense_ratio=Decimal("0.0017"),
        )
    """

    tracking_index: Symbol | None = None
    total_expense_ratio: Decimal | None = None
    isin: ISIN | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.total_expense_ratio is not None and not (
            Decimal(0) <= self.total_expense_ratio < Decimal(1)
        ):
            raise InvalidContractSpecError(
                field="total_expense_ratio",
                value=self.total_expense_ratio,
                reason="total expense ratio must be in [0, 1) (a fraction, not a percentage)",
            )


# ── Currency / FX ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CurrencySpec(ContractSpec):
    """Contract specification for a currency pair (FX spot or derivatives).

    The ``currency`` base-class field is the settlement currency (usually the
    quote currency). ``base_currency`` and ``quote_currency`` define the pair.

    Attributes:
        lot_size:       Contract size in units of ``base_currency``.
        tick_size:      Minimum exchange rate move (pip size).
        currency:       Settlement currency (typically ``quote_currency``).
        base_currency:  The "1" in the exchange rate (e.g. ``"USD"`` in USD/INR).
        quote_currency: The price currency (e.g. ``"INR"`` in USD/INR).
        pip_size:       Smallest standard price increment displayed to traders.
            May differ from ``tick_size`` in some market conventions.

    Example::

        spec = CurrencySpec(
            lot_size=Decimal("1000"),
            tick_size=Decimal("0.0025"),
            currency=CurrencyCode("INR"),
            base_currency=CurrencyCode("USD"),
            quote_currency=CurrencyCode("INR"),
        )
    """

    base_currency: CurrencyCode
    quote_currency: CurrencyCode
    pip_size: Decimal | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.base_currency == self.quote_currency:
            raise InvalidContractSpecError(
                field="quote_currency",
                value=self.quote_currency,
                reason="base_currency and quote_currency must be different",
            )
        if self.pip_size is not None:
            _require_positive("pip_size", self.pip_size)

    @property
    def pair_name(self) -> str:
        """Human-readable currency pair name.

        Returns:
            A string in the form ``"USD/INR"``.
        """
        return f"{self.base_currency}/{self.quote_currency}"


# ── Commodity ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CommoditySpec(ContractSpec):
    """Contract specification for a commodity (spot or futures on MCX/NCDEX).

    Attributes:
        lot_size:          Quantity of commodity per contract in the unit of
            measure (e.g. 100 for gold in grams, 1 for crude oil in barrels).
        tick_size:         Minimum price move per unit.
        currency:          Contract settlement currency.
        unit_of_measure:   Unit for ``lot_size`` (e.g. ``"gram"``, ``"barrel"``,
            ``"MT"`` for metric tonne).
        underlying:        Optional ``Symbol`` if this is a derivative on a spot
            commodity. ``None`` for spot commodity instruments.
        expiry:            Contract expiry date. ``None`` for spot.
        multiplier:        Contract value multiplier (typically ``Decimal("1")``).
        settlement:        Cash or physical delivery at expiry.
        quality_grade:     Commodity quality specification (e.g. ``"999.9 fine"``
            for gold, ``"Brent`` crude``"``).
        delivery_location: Designated delivery point for physical settlement.

    Example::

        spec = CommoditySpec(
            lot_size=Decimal("100"),
            tick_size=Decimal("1"),
            currency=CurrencyCode("INR"),
            unit_of_measure="gram",
            expiry=date(2025, 2, 5),
            settlement=SettlementType.PHYSICAL,
            quality_grade="999.9 fine gold",
        )
    """

    unit_of_measure: str
    underlying: Symbol | None = None
    expiry: date | None = None
    multiplier: Decimal = Decimal("1")
    settlement: SettlementType = SettlementType.PHYSICAL
    quality_grade: str | None = None
    delivery_location: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        _require_positive("multiplier", self.multiplier)
        if not self.unit_of_measure.strip():
            raise InvalidContractSpecError(
                field="unit_of_measure",
                value=self.unit_of_measure,
                reason="unit of measure must not be empty",
            )
