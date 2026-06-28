"""Athena Market Domain — Sprint 5.

Represents how financial markets operate, independently of any broker or
data vendor. This package models exchanges, trading segments, session
schedules, market states, trading rules, and market capabilities.

No broker APIs, no market data ingestion, no databases.

Market domain responsibilities:
    Exchange modelling  — what exchanges exist, where, regulated by whom
    Segment modelling   — what segments each exchange offers
    Session schedules   — when each exchange operates (schedule pattern)
    Market state        — operational status (open, halted, closed, etc.)
    Rule configuration  — price bands, circuit breaker thresholds
    Capabilities        — what order types and asset classes each market supports

Integration with Time Domain (``athena.time``):
    The Market Domain does NOT import from ``athena.time``. Integration is
    mediated by ``MarketCalendarPort`` — a Protocol defined here that
    ``athena.time`` implementations satisfy. Engines wire the two together.

Public API::

    from athena.market import (
        # Models
        MarketId, CountryCode, MarketCurrency, MarketTimezone, WeeklySchedule,
        INDIA_TIMEZONE, INR,

        # Exchange
        ExchangeMetadata, NSE, BSE, MCX, NYSE,
        InMemoryExchangeRepository,

        # Segments
        MarketSegment, MarketSegmentType, TradingVenue,
        NSE_EQ, NSE_FO, NSE_CDS, BSE_EQ, BSE_FO, MCX_FO,
        InMemorySegmentRepository,

        # Sessions
        MarketSessionType, SessionWindow, DailySchedule, ExchangeSchedule,
        NSE_STANDARD_SCHEDULE,

        # Market state
        MarketState, HaltReason, MarketStateSnapshot, StateTransition,
        is_valid_transition, validate_transition,

        # Rules
        PriceBandType, PriceBandConfig, CircuitBreakerLevel,
        CircuitBreakerThreshold, IndexCircuitBreakerConfig,
        RestrictionType, TradingRestriction,
        PriceBandRuleProtocol, CircuitBreakerRuleProtocol,
        SEBI_NSE_CIRCUIT_BREAKER,

        # Capabilities
        OrderType, OrderValidity, OrderCapabilities, MarketCapabilities,
        NSE_EQ_CAPABILITIES,

        # Interfaces
        ExchangeRepositoryProtocol, SegmentRepositoryProtocol,
        MarketCalendarPort, MarketStateServiceProtocol,
        ScheduleRepositoryProtocol, MarketRulesRepositoryProtocol,

        # Validation
        ValidationResult, validate_exchange_metadata, validate_daily_schedule,
        validate_price_band_config, validate_circuit_breaker_config,
        validate_market_capabilities,

        # Exceptions
        MarketError, InvalidMarketIdError, ExchangeNotFoundError,
        SegmentNotFoundError, InvalidMarketStateError, InvalidScheduleError,
        MarketHaltedError, UnsupportedCapabilityError,
    )
"""

from athena.market.capabilities import (
    NSE_EQ_CAPABILITIES,
    NSE_EQ_ORDER_CAPS,
    MarketCapabilities,
    OrderCapabilities,
    OrderType,
    OrderValidity,
)
from athena.market.exceptions import (
    ExchangeNotFoundError,
    InvalidMarketIdError,
    InvalidMarketStateError,
    InvalidScheduleError,
    MarketError,
    MarketHaltedError,
    SegmentNotFoundError,
    UnsupportedCapabilityError,
)
from athena.market.exchange import (
    BSE,
    KNOWN_EXCHANGES,
    MCX,
    NSE,
    NYSE,
    ExchangeMetadata,
    InMemoryExchangeRepository,
)
from athena.market.interfaces import (
    ExchangeRepositoryProtocol,
    MarketCalendarPort,
    MarketRulesRepositoryProtocol,
    MarketStateServiceProtocol,
    ScheduleRepositoryProtocol,
    SegmentRepositoryProtocol,
)
from athena.market.market_state import (
    VALID_TRANSITIONS,
    HaltReason,
    MarketState,
    MarketStateSnapshot,
    StateTransition,
    is_valid_transition,
    validate_transition,
)
from athena.market.models import (
    INDIA,
    INDIA_TIMEZONE,
    INR,
    UNITED_STATES,
    US_EASTERN_TIMEZONE,
    USD,
    CountryCode,
    MarketCurrency,
    MarketId,
    MarketTimezone,
    WeeklySchedule,
)
from athena.market.rules import (
    SEBI_NSE_CIRCUIT_BREAKER,
    CircuitBreakerLevel,
    CircuitBreakerRuleProtocol,
    CircuitBreakerThreshold,
    IndexCircuitBreakerConfig,
    PriceBandConfig,
    PriceBandRuleProtocol,
    PriceBandType,
    RestrictionType,
    TradingRestriction,
)
from athena.market.segments import (
    BSE_EQ,
    BSE_FO,
    KNOWN_SEGMENTS,
    MCX_FO,
    NSE_CDS,
    NSE_EQ,
    NSE_FO,
    NSE_SME,
    InMemorySegmentRepository,
    MarketSegment,
    MarketSegmentType,
    TradingVenue,
)
from athena.market.sessions import (
    NSE_STANDARD_SCHEDULE,
    DailySchedule,
    ExchangeSchedule,
    MarketSessionType,
    SessionWindow,
)
from athena.market.validation import (
    ValidationResult,
    validate_circuit_breaker_config,
    validate_daily_schedule,
    validate_exchange_metadata,
    validate_market_capabilities,
    validate_price_band_config,
)

__all__ = [
    "BSE",
    "BSE_EQ",
    "BSE_FO",
    "INDIA",
    "INDIA_TIMEZONE",
    "INR",
    "KNOWN_EXCHANGES",
    "KNOWN_SEGMENTS",
    "MCX",
    "MCX_FO",
    "NSE",
    "NSE_CDS",
    "NSE_EQ",
    "NSE_EQ_CAPABILITIES",
    "NSE_EQ_ORDER_CAPS",
    "NSE_FO",
    "NSE_SME",
    "NSE_STANDARD_SCHEDULE",
    "NYSE",
    "SEBI_NSE_CIRCUIT_BREAKER",
    "UNITED_STATES",
    "USD",
    "US_EASTERN_TIMEZONE",
    "VALID_TRANSITIONS",
    "CircuitBreakerLevel",
    "CircuitBreakerRuleProtocol",
    "CircuitBreakerThreshold",
    "CountryCode",
    "DailySchedule",
    "ExchangeMetadata",
    "ExchangeNotFoundError",
    "ExchangeRepositoryProtocol",
    "ExchangeSchedule",
    "HaltReason",
    "InMemoryExchangeRepository",
    "InMemorySegmentRepository",
    "IndexCircuitBreakerConfig",
    "InvalidMarketIdError",
    "InvalidMarketStateError",
    "InvalidScheduleError",
    "MarketCalendarPort",
    "MarketCapabilities",
    "MarketCurrency",
    "MarketError",
    "MarketHaltedError",
    "MarketId",
    "MarketRulesRepositoryProtocol",
    "MarketSegment",
    "MarketSegmentType",
    "MarketSessionType",
    "MarketState",
    "MarketStateServiceProtocol",
    "MarketStateSnapshot",
    "MarketTimezone",
    "OrderCapabilities",
    "OrderType",
    "OrderValidity",
    "PriceBandConfig",
    "PriceBandRuleProtocol",
    "PriceBandType",
    "RestrictionType",
    "ScheduleRepositoryProtocol",
    "SegmentNotFoundError",
    "SegmentRepositoryProtocol",
    "SessionWindow",
    "StateTransition",
    "TradingRestriction",
    "TradingVenue",
    "UnsupportedCapabilityError",
    "ValidationResult",
    "WeeklySchedule",
    "is_valid_transition",
    "validate_circuit_breaker_config",
    "validate_daily_schedule",
    "validate_exchange_metadata",
    "validate_market_capabilities",
    "validate_price_band_config",
    "validate_transition",
]
