"""Athena Asset Domain — Sprint 4.

Defines every tradable financial instrument used throughout the Athena platform.
This package contains only domain models, typed identifiers, classification
enumerations, and protocol interfaces — no broker connections, no databases,
no market data.

Supported asset classes:
    EQUITY     — common and preferred stocks
    INDEX      — market indices (NIFTY 50, SENSEX, BANKEX, etc.)
    DERIVATIVE — futures and options contracts
    ETF        — exchange-traded funds
    CURRENCY   — FX spot and derivatives
    COMMODITY  — physical commodities (MCX gold, crude oil, etc.)
    FIXED_INCOME — planned

Exchange coverage:
    NSE  — National Stock Exchange (EQ, F&O, CDS segments)
    BSE  — Bombay Stock Exchange (EQ, F&O, SME segments)
    MCX  — Multi Commodity Exchange (F&O segment)
    International — planned (NYSE, NASDAQ, LSE, etc.)

Public API::

    from athena.assets import (
        # Core model
        Instrument,

        # Identifiers
        InstrumentId, ExchangeId, Symbol, ISIN, CurrencyCode,

        # Classification
        AssetClass, InstrumentType, ExchangeSegment, InstrumentStatus,
        OptionType, OptionStyle, SettlementType, MarketTier,

        # Contract specs
        ContractSpec, EquitySpec, IndexSpec, FuturesSpec, OptionsSpec,
        ETFSpec, CurrencySpec, CommoditySpec,

        # Registry
        InstrumentQuery, InMemoryInstrumentRegistry,

        # Interfaces
        InstrumentRegistryProtocol, InstrumentLookupProtocol,

        # Validation
        ValidationResult, validate_instrument, validate_contract,
        is_valid_isin, is_valid_symbol_string,

        # Exceptions
        AssetError, InvalidIdentifierError, InvalidInstrumentError,
        InvalidContractSpecError, InstrumentNotFoundError,
        DuplicateInstrumentError, InstrumentExpiredError,
        UnsupportedAssetClassError,
    )
"""

from athena.assets.classification import (
    AssetClass,
    ExchangeSegment,
    InstrumentStatus,
    InstrumentType,
    MarketTier,
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
from athena.assets.exceptions import (
    AssetError,
    DuplicateInstrumentError,
    InstrumentExpiredError,
    InstrumentNotFoundError,
    InvalidContractSpecError,
    InvalidIdentifierError,
    InvalidInstrumentError,
    UnsupportedAssetClassError,
)
from athena.assets.identifiers import ISIN, CurrencyCode, ExchangeId, InstrumentId, Symbol
from athena.assets.instruments import Instrument
from athena.assets.interfaces import InstrumentLookupProtocol, InstrumentRegistryProtocol
from athena.assets.registry import InMemoryInstrumentRegistry, InstrumentQuery
from athena.assets.validation import (
    ValidationResult,
    is_valid_isin,
    is_valid_symbol_string,
    validate_contract,
    validate_instrument,
)

__all__ = [
    "ISIN",
    "AssetClass",
    "AssetError",
    "CommoditySpec",
    "ContractSpec",
    "CurrencyCode",
    "CurrencySpec",
    "DuplicateInstrumentError",
    "ETFSpec",
    "EquitySpec",
    "ExchangeId",
    "ExchangeSegment",
    "FuturesSpec",
    "InMemoryInstrumentRegistry",
    "IndexSpec",
    "Instrument",
    "InstrumentExpiredError",
    "InstrumentId",
    "InstrumentLookupProtocol",
    "InstrumentNotFoundError",
    "InstrumentQuery",
    "InstrumentRegistryProtocol",
    "InstrumentStatus",
    "InstrumentType",
    "InvalidContractSpecError",
    "InvalidIdentifierError",
    "InvalidInstrumentError",
    "MarketTier",
    "OptionStyle",
    "OptionType",
    "OptionsSpec",
    "SettlementType",
    "Symbol",
    "UnsupportedAssetClassError",
    "ValidationResult",
    "is_valid_isin",
    "is_valid_symbol_string",
    "validate_contract",
    "validate_instrument",
]
