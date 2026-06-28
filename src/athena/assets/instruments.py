"""Core Instrument value object and factory constructors.

An ``Instrument`` is the atomic tradable entity in Athena — the equivalent
of a row in an exchange's instrument master. It is an immutable value object
composed from typed identifiers, a classification, and a ``ContractSpec``.

Design decisions:
    Single ``Instrument`` + discriminated ``ContractSpec`` (not subclasses):
        Registries, repositories, and engines all operate on ``Instrument``.
        Replacing one Instrument type with seven subclasses forces isinstance
        checks everywhere. A single type with a typed spec field is cleaner.

    Named factory constructors (``Instrument.equity(...)``, etc.):
        Constructing an Instrument directly requires populating every field
        and choosing the right ``AssetClass`` / ``InstrumentType`` manually.
        Factory methods encode these mappings and set sensible defaults,
        making it hard to create a structurally invalid instrument.

    ``instrument_id`` is optional in factories:
        Callers can supply a known ID (when loading from storage) or omit it
        to auto-generate a new UUID. This keeps factories useful in both the
        creation and the reconstitution paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from athena.assets.classification import (
    AssetClass,
    ExchangeSegment,
    InstrumentStatus,
    InstrumentType,
    OptionStyle,
    OptionType,
    SettlementType,
)
from athena.assets.contracts import (
    CommoditySpec,
    ContractSpec,
    CurrencySpec,
    EquitySpec,
    ETFSpec,
    FuturesSpec,
    IndexSpec,
    OptionsSpec,
)
from athena.assets.exceptions import InvalidInstrumentError
from athena.assets.identifiers import CurrencyCode, ExchangeId, InstrumentId, Symbol

if TYPE_CHECKING:
    from datetime import date

    from athena.assets.identifiers import ISIN


@dataclass(frozen=True)
class Instrument:
    """An immutable representation of a listed financial instrument.

    This is the single domain entity for the Asset Domain. It composes typed
    identifiers, exchange and segment information, a classification pair
    (``asset_class`` + ``instrument_type``), and a ``ContractSpec`` subclass
    that carries the asset-class-specific parameters.

    Attributes:
        id:              Platform-internal UUID identifier.
        symbol:          Structured ``EXCHANGE:TICKER`` market symbol.
        name:            Human-readable instrument name
            (e.g. ``"Nifty 50 Index"``).
        exchange:        The exchange where this instrument is listed.
        segment:         The trading segment within the exchange.
        asset_class:     Broad asset classification.
        instrument_type: Specific instrument type within the asset class.
        contract:        Asset-class-specific contract parameters.
        status:          Current lifecycle state.
        isin:            Optional ISO 6166 identifier (present for equities/ETFs).
        description:     Optional free-text description.

    Example::

        nifty = Instrument.index(
            symbol=Symbol.parse("NSE:NIFTY50-INDEX"),
            name="Nifty 50",
            exchange=ExchangeId("NSE"),
            segment=ExchangeSegment.NSE_EQ,
            lot_size=Decimal("1"),
            tick_size=Decimal("0.05"),
            currency=CurrencyCode("INR"),
            num_components=50,
        )
    """

    id: InstrumentId
    symbol: Symbol
    name: str
    exchange: ExchangeId
    segment: ExchangeSegment
    asset_class: AssetClass
    instrument_type: InstrumentType
    contract: ContractSpec
    status: InstrumentStatus = InstrumentStatus.ACTIVE
    isin: ISIN | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidInstrumentError(
                "Instrument.name must not be empty",
                symbol=str(self.symbol),
            )

    # ── Derived properties ────────────────────────────────────────────────────

    @property
    def currency(self) -> CurrencyCode:
        """Settlement currency, delegated from the contract spec.

        Returns:
            The ``CurrencyCode`` from ``self.contract``.
        """
        return self.contract.currency

    @property
    def is_derivative(self) -> bool:
        """Return ``True`` if this instrument is a derivative contract.

        Returns:
            ``True`` when ``asset_class == AssetClass.DERIVATIVE``.
        """
        return self.asset_class == AssetClass.DERIVATIVE

    @property
    def is_active(self) -> bool:
        """Return ``True`` when the instrument is actively trading.

        Returns:
            ``True`` when ``status == InstrumentStatus.ACTIVE``.
        """
        return self.status == InstrumentStatus.ACTIVE

    @property
    def is_expired(self) -> bool:
        """Return ``True`` when the derivative contract has passed its expiry.

        Returns:
            ``True`` when ``status == InstrumentStatus.EXPIRED``.
        """
        return self.status == InstrumentStatus.EXPIRED

    @property
    def is_index(self) -> bool:
        """Return ``True`` when this instrument represents a market index.

        Returns:
            ``True`` when ``asset_class == AssetClass.INDEX``.
        """
        return self.asset_class == AssetClass.INDEX

    def __str__(self) -> str:
        return str(self.symbol)

    def __repr__(self) -> str:
        return (
            f"Instrument(id={self.id!s}, symbol={self.symbol!s}, type={self.instrument_type.value})"
        )

    # ── Named factory constructors ────────────────────────────────────────────

    @classmethod
    def equity(
        cls,
        *,
        symbol: Symbol,
        name: str,
        exchange: ExchangeId,
        segment: ExchangeSegment,
        lot_size: Decimal,
        tick_size: Decimal,
        currency: CurrencyCode,
        isin: ISIN | None = None,
        face_value: Decimal | None = None,
        instrument_type: InstrumentType = InstrumentType.COMMON_STOCK,
        status: InstrumentStatus = InstrumentStatus.ACTIVE,
        description: str | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> Instrument:
        """Create an equity instrument (common or preferred stock).

        Args:
            symbol:          Market symbol (e.g. ``Symbol.parse("NSE:HDFCBANK")``).
            name:            Human-readable name.
            exchange:        Listing exchange.
            segment:         Trading segment (typically ``NSE_EQ`` or ``BSE_EQ``).
            lot_size:        Exchange lot size (1 for most equities).
            tick_size:       Minimum price move.
            currency:        Settlement currency.
            isin:            Optional ISO 6166 identifier.
            face_value:      Optional par value per share.
            instrument_type: ``COMMON_STOCK`` (default) or ``PREFERRED_STOCK``.
            status:          Lifecycle status.
            description:     Optional free-text description.
            instrument_id:   Supply a known ID when reconstituting from storage;
                omit to auto-generate a UUID.

        Returns:
            An ``Instrument`` with ``AssetClass.EQUITY`` and ``EquitySpec``.
        """
        spec = EquitySpec(
            lot_size=lot_size,
            tick_size=tick_size,
            currency=currency,
            isin=isin,
            face_value=face_value,
        )
        return cls(
            id=instrument_id or InstrumentId.generate(),
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            asset_class=AssetClass.EQUITY,
            instrument_type=instrument_type,
            contract=spec,
            status=status,
            isin=isin,
            description=description,
        )

    @classmethod
    def index(
        cls,
        *,
        symbol: Symbol,
        name: str,
        exchange: ExchangeId,
        segment: ExchangeSegment,
        lot_size: Decimal,
        tick_size: Decimal,
        currency: CurrencyCode,
        base_value: Decimal | None = None,
        base_date: date | None = None,
        num_components: int | None = None,
        instrument_type: InstrumentType = InstrumentType.BROAD_MARKET_INDEX,
        status: InstrumentStatus = InstrumentStatus.ACTIVE,
        description: str | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> Instrument:
        """Create a market index instrument.

        Args:
            symbol:          Market symbol (e.g. ``Symbol.parse("NSE:NIFTY50-INDEX")``).
            name:            Human-readable index name.
            exchange:        Exchange that calculates/publishes this index.
            segment:         Segment (typically the equity segment of the exchange).
            lot_size:        Reference lot size (``Decimal("1")`` for most indices).
            tick_size:       Minimum index move.
            currency:        Index currency.
            base_value:      Optional initial index value at inception.
            base_date:       Optional index inception date.
            num_components:  Optional number of constituent securities.
            instrument_type: Index sub-type.
            status:          Lifecycle status.
            description:     Optional description.
            instrument_id:   Optional pre-assigned UUID.

        Returns:
            An ``Instrument`` with ``AssetClass.INDEX`` and ``IndexSpec``.
        """
        spec = IndexSpec(
            lot_size=lot_size,
            tick_size=tick_size,
            currency=currency,
            base_value=base_value,
            base_date=base_date,
            num_components=num_components,
        )
        return cls(
            id=instrument_id or InstrumentId.generate(),
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            asset_class=AssetClass.INDEX,
            instrument_type=instrument_type,
            contract=spec,
            status=status,
            description=description,
        )

    @classmethod
    def futures(
        cls,
        *,
        symbol: Symbol,
        name: str,
        exchange: ExchangeId,
        segment: ExchangeSegment,
        lot_size: Decimal,
        tick_size: Decimal,
        currency: CurrencyCode,
        underlying: Symbol,
        expiry: date,
        multiplier: Decimal = Decimal("1"),
        settlement: SettlementType = SettlementType.CASH,
        status: InstrumentStatus = InstrumentStatus.ACTIVE,
        description: str | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> Instrument:
        """Create a futures contract instrument.

        Args:
            symbol:      Market symbol (e.g. ``Symbol.parse("NSE:NIFTY25JANFUT")``).
            name:        Human-readable contract name.
            exchange:    Listing exchange.
            segment:     Segment (e.g. ``NSE_FO``).
            lot_size:    Contract lot size.
            tick_size:   Minimum price move.
            currency:    Settlement currency.
            underlying:  Symbol of the underlying instrument.
            expiry:      Contract expiry date.
            multiplier:  Contract value multiplier.
            settlement:  Cash or physical settlement.
            status:      Lifecycle status.
            description: Optional description.
            instrument_id: Optional pre-assigned UUID.

        Returns:
            An ``Instrument`` with ``AssetClass.DERIVATIVE``,
            ``InstrumentType.FUTURES``, and ``FuturesSpec``.
        """
        spec = FuturesSpec(
            lot_size=lot_size,
            tick_size=tick_size,
            currency=currency,
            underlying=underlying,
            expiry=expiry,
            multiplier=multiplier,
            settlement=settlement,
        )
        return cls(
            id=instrument_id or InstrumentId.generate(),
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            asset_class=AssetClass.DERIVATIVE,
            instrument_type=InstrumentType.FUTURES,
            contract=spec,
            status=status,
            description=description,
        )

    @classmethod
    def option(
        cls,
        *,
        symbol: Symbol,
        name: str,
        exchange: ExchangeId,
        segment: ExchangeSegment,
        lot_size: Decimal,
        tick_size: Decimal,
        currency: CurrencyCode,
        underlying: Symbol,
        expiry: date,
        strike: Decimal,
        option_type: OptionType,
        style: OptionStyle = OptionStyle.EUROPEAN,
        multiplier: Decimal = Decimal("1"),
        settlement: SettlementType = SettlementType.CASH,
        status: InstrumentStatus = InstrumentStatus.ACTIVE,
        description: str | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> Instrument:
        """Create an options contract instrument.

        Args:
            symbol:      Market symbol (e.g. ``Symbol.parse("NSE:NIFTY25JAN24500CE")``).
            name:        Human-readable contract name.
            exchange:    Listing exchange.
            segment:     Segment (e.g. ``NSE_FO``).
            lot_size:    Contract lot size.
            tick_size:   Minimum premium move.
            currency:    Premium and settlement currency.
            underlying:  Symbol of the underlying instrument.
            expiry:      Option expiry date.
            strike:      Strike price. Must be positive.
            option_type: ``CALL`` or ``PUT``.
            style:       ``EUROPEAN`` (default) or ``AMERICAN``.
            multiplier:  Contract value multiplier.
            settlement:  Cash or physical settlement.
            status:      Lifecycle status.
            description: Optional description.
            instrument_id: Optional pre-assigned UUID.

        Returns:
            An ``Instrument`` with ``AssetClass.DERIVATIVE``,
            ``InstrumentType.CALL_OPTION`` or ``PUT_OPTION``, and ``OptionsSpec``.
        """
        spec = OptionsSpec(
            lot_size=lot_size,
            tick_size=tick_size,
            currency=currency,
            underlying=underlying,
            expiry=expiry,
            strike=strike,
            option_type=option_type,
            style=style,
            multiplier=multiplier,
            settlement=settlement,
        )
        instrument_type = (
            InstrumentType.CALL_OPTION
            if option_type == OptionType.CALL
            else InstrumentType.PUT_OPTION
        )
        return cls(
            id=instrument_id or InstrumentId.generate(),
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            asset_class=AssetClass.DERIVATIVE,
            instrument_type=instrument_type,
            contract=spec,
            status=status,
            description=description,
        )

    @classmethod
    def etf(
        cls,
        *,
        symbol: Symbol,
        name: str,
        exchange: ExchangeId,
        segment: ExchangeSegment,
        lot_size: Decimal,
        tick_size: Decimal,
        currency: CurrencyCode,
        tracking_index: Symbol | None = None,
        total_expense_ratio: Decimal | None = None,
        isin: ISIN | None = None,
        instrument_type: InstrumentType = InstrumentType.EQUITY_ETF,
        status: InstrumentStatus = InstrumentStatus.ACTIVE,
        description: str | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> Instrument:
        """Create an exchange-traded fund instrument.

        Args:
            symbol:              Market symbol.
            name:                Fund name.
            exchange:            Listing exchange.
            segment:             Trading segment.
            lot_size:            Minimum trading unit.
            tick_size:           Minimum price move.
            currency:            Fund currency.
            tracking_index:      Optional symbol of the tracked index.
            total_expense_ratio: Annual cost as a fraction (e.g. 0.0007 = 0.07%).
            isin:                Optional ISIN.
            instrument_type:     ETF sub-type.
            status:              Lifecycle status.
            description:         Optional description.
            instrument_id:       Optional pre-assigned UUID.

        Returns:
            An ``Instrument`` with ``AssetClass.ETF`` and ``ETFSpec``.
        """
        spec = ETFSpec(
            lot_size=lot_size,
            tick_size=tick_size,
            currency=currency,
            tracking_index=tracking_index,
            total_expense_ratio=total_expense_ratio,
            isin=isin,
        )
        return cls(
            id=instrument_id or InstrumentId.generate(),
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            asset_class=AssetClass.ETF,
            instrument_type=instrument_type,
            contract=spec,
            status=status,
            isin=isin,
            description=description,
        )

    @classmethod
    def currency_pair(
        cls,
        *,
        symbol: Symbol,
        name: str,
        exchange: ExchangeId,
        segment: ExchangeSegment,
        lot_size: Decimal,
        tick_size: Decimal,
        base_currency: CurrencyCode,
        quote_currency: CurrencyCode,
        pip_size: Decimal | None = None,
        instrument_type: InstrumentType = InstrumentType.FX_SPOT,
        status: InstrumentStatus = InstrumentStatus.ACTIVE,
        description: str | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> Instrument:
        """Create a currency pair (FX spot or derivatives) instrument.

        Args:
            symbol:          Market symbol (e.g. ``Symbol.parse("NSE:USDINR")``).
            name:            Pair name (e.g. ``"USD/INR"``).
            exchange:        Listing exchange.
            segment:         Trading segment (e.g. ``NSE_CDS``).
            lot_size:        Contract size in units of base currency.
            tick_size:       Minimum price move.
            base_currency:   First currency in the pair (e.g. ``CurrencyCode("USD")``).
            quote_currency:  Price currency (e.g. ``CurrencyCode("INR")``).
            pip_size:        Optional standard display pip size.
            instrument_type: FX instrument sub-type.
            status:          Lifecycle status.
            description:     Optional description.
            instrument_id:   Optional pre-assigned UUID.

        Returns:
            An ``Instrument`` with ``AssetClass.CURRENCY`` and ``CurrencySpec``.
        """
        spec = CurrencySpec(
            lot_size=lot_size,
            tick_size=tick_size,
            currency=quote_currency,  # settlement in quote currency
            base_currency=base_currency,
            quote_currency=quote_currency,
            pip_size=pip_size,
        )
        return cls(
            id=instrument_id or InstrumentId.generate(),
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            asset_class=AssetClass.CURRENCY,
            instrument_type=instrument_type,
            contract=spec,
            status=status,
            description=description,
        )

    @classmethod
    def commodity(
        cls,
        *,
        symbol: Symbol,
        name: str,
        exchange: ExchangeId,
        segment: ExchangeSegment,
        lot_size: Decimal,
        tick_size: Decimal,
        currency: CurrencyCode,
        unit_of_measure: str,
        underlying: Symbol | None = None,
        expiry: date | None = None,
        multiplier: Decimal = Decimal("1"),
        settlement: SettlementType = SettlementType.PHYSICAL,
        quality_grade: str | None = None,
        delivery_location: str | None = None,
        instrument_type: InstrumentType = InstrumentType.COMMODITY_FUTURES,
        status: InstrumentStatus = InstrumentStatus.ACTIVE,
        description: str | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> Instrument:
        """Create a commodity instrument (spot or futures).

        Args:
            symbol:            Market symbol (e.g. ``Symbol.parse("MCX:GOLDPETAL")``).
            name:              Instrument name.
            exchange:          Listing exchange (typically ``ExchangeId("MCX")``).
            segment:           Trading segment (typically ``MCX_FO``).
            lot_size:          Quantity per contract in ``unit_of_measure``.
            tick_size:         Minimum price move per unit.
            currency:          Settlement currency.
            unit_of_measure:   Physical unit (e.g. ``"gram"``, ``"barrel"``).
            underlying:        Optional underlying symbol for derivatives.
            expiry:            Optional contract expiry.
            multiplier:        Optional contract value multiplier.
            settlement:        Cash or physical.
            quality_grade:     Optional quality specification.
            delivery_location: Optional delivery point.
            instrument_type:   Commodity sub-type.
            status:            Lifecycle status.
            description:       Optional description.
            instrument_id:     Optional pre-assigned UUID.

        Returns:
            An ``Instrument`` with ``AssetClass.COMMODITY`` and ``CommoditySpec``.
        """
        spec = CommoditySpec(
            lot_size=lot_size,
            tick_size=tick_size,
            currency=currency,
            unit_of_measure=unit_of_measure,
            underlying=underlying,
            expiry=expiry,
            multiplier=multiplier,
            settlement=settlement,
            quality_grade=quality_grade,
            delivery_location=delivery_location,
        )
        return cls(
            id=instrument_id or InstrumentId.generate(),
            symbol=symbol,
            name=name,
            exchange=exchange,
            segment=segment,
            asset_class=AssetClass.COMMODITY,
            instrument_type=instrument_type,
            contract=spec,
            status=status,
            description=description,
        )
