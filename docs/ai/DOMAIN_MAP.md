# Athena Domain Map

A precise reference for every Python package in `src/athena/`. Use this to navigate the codebase, understand what each module owns, and find the right place to implement new functionality.

---

## Package Overview

```
src/athena/
├── core/                    ← Shared kernel (zero deps)
├── platform/                ← Cross-cutting runtime concerns
├── time/                    ← Temporal logic (clock, calendar, sessions, expiry)
├── storage/                 ← Persistence interfaces (no implementations)
├── assets/                  ← Financial instrument domain
├── market/                  ← Exchange and market operations domain
├── market_data/             ← Historical and live market data domain
├── features/                ← Engineered feature domain
├── experiments/             ← Reproducible research experiment domain
└── engines/                 ← Five computation engines (mostly stubs)
    ├── data/
    ├── research/
    ├── intelligence/
    ├── trading/
    └── governance/
```

---

## `athena.core` — Shared Kernel

**Rule:** Zero imports from any other `athena.*` package.

| Module | Contents |
|---|---|
| `core/domain/primitives.py` | `Price`, `Quantity`, `Currency`, `Symbol` (NewType wrappers over Decimal/str) |
| `core/domain/instrument.py` | `Instrument`, `Exchange`, `Segment`, `OptionType` (lightweight transport types) |
| `core/domain/market.py` | `SessionType`, `MarketSession` (transport types for session events) |
| `core/domain/tick.py` | `Tick` (minimal transport for tick events) |
| `core/domain/ohlcv.py` | `OHLCV`, `BarInterval` (minimal transport for bar events) |
| `core/events/base.py` | `DomainEvent` (frozen dataclass: event_id UUID, occurred_at UTC, correlation_id) |
| `core/ports/broker.py` | `BrokerPort`, `OrderRequest`, `OrderAcknowledgement`, `Position`, `OrderSide/Type/Status`, `ProductType` |
| `core/ports/market_data_feed.py` | `MarketDataFeedPort` Protocol |
| `core/ports/historical_store.py` | `HistoricalStorePort` Protocol |
| `core/ports/instrument_repository.py` | `InstrumentRepositoryPort` Protocol |

---

## `athena.platform` — Platform Foundation

**Rule:** Imports from `athena.core` only.

| Module | Contents |
|---|---|
| `platform/exceptions/errors.py` | `AthenaError` (root) + `ConfigurationError`, `ValidationError`, `InfrastructureError`, `ExternalServiceError`, `DataIntegrityError`, `NotImplementedFeatureError` |
| `platform/types/enums.py` | `Environment`, `LogLevel`, `LogFormat`, `ApplicationMode`, `MarketType` |
| `platform/config/settings.py` | `AthenaSettings`, `AppConfig`, `LoggingConfig` (pydantic-settings, `ATHENA_*` env vars) |
| `platform/logging/setup.py` | `configure_logging()`, `get_logger()` (structlog, JSON in prod, console in dev) |
| `platform/logging/context.py` | `bind_context()`, `get_correlation_id()`, `set_request_id()` (ContextVar-based, async-safe) |
| `platform/bootstrap/bootstrapper.py` | `bootstrap_application()` → `ApplicationContext` |
| `platform/bootstrap/context.py` | `ApplicationContext` (frozen: settings + started_at) |

**Key pattern:** `AthenaError` is the root of ALL platform exceptions. Every domain exception inherits from it.

---

## `athena.time` — Time Domain

**Rule:** Peer layer. Imports from `athena.core` + `athena.platform` only.

| Module | Contents |
|---|---|
| `time/timezone.py` | `UTC`, `IST` constants; `require_aware()`, `to_utc()`, `to_ist()` |
| `time/clock.py` | `SystemClock`, `FrozenClock`, `ManualClock`, `OffsetClock` |
| `time/holiday.py` | `NullHolidayProvider`, `SetHolidayProvider` |
| `time/calendar.py` | `NSETradingCalendar` (Mon-Fri minus holidays, 365-day safety limit) |
| `time/session.py` | `NSESessionService` (5 session types, IST→UTC, MarketSession objects) |
| `time/business_day.py` | `add_trading_days()`, `subtract_trading_days()`, `count_trading_days()`, `trading_days_in_month()` |
| `time/expiry.py` | `NSEExpiryCalculator` (monthly last-Thursday, weekly configurable day, holiday-adjusted) |
| `time/models.py` | `ExpiryType`, `WeeklyExpiryDay`, `ExpiryInfo`, `TimeRange` |
| `time/interfaces.py` | `ClockProtocol`, `HolidayProviderProtocol`, `TradingCalendarProtocol`, `SessionServiceProtocol`, `ExpiryCalculatorProtocol` |

**Key constants:** `NIFTY_WEEKLY_EXPIRY_DAY = WeeklyExpiryDay.THURSDAY`, `SENSEX_WEEKLY_EXPIRY_DAY = WeeklyExpiryDay.TUESDAY`

---

## `athena.storage` — Storage Foundation

**Rule:** Peer layer. No implementations, only interfaces and models.

| Module | Contents |
|---|---|
| `storage/models.py` | `StorageKey`, `Page[T]`, `Pagination`, `QuerySpec`, `FilterExpression`, `TimeRangeFilter`, `OptimisticLockSpec`, `StorageMetadata`, `StorageRecord[T]`, `HealthCheckResult`, `SchemaVersion` |
| `storage/exceptions.py` | `StorageError` + 8 subtypes (`RecordNotFoundError`, `DuplicateKeyError`, `VersionConflictError`, etc.) |
| `storage/interfaces.py` | `ReadRepositoryProtocol[T]`, `WriteRepositoryProtocol[T]`, `RepositoryProtocol[T]`, `TimeSeriesRepositoryProtocol[T]` |
| `storage/repositories.py` | `InstrumentRepositoryProtocol`, `TickRepositoryProtocol`, `OHLCVRepositoryProtocol` (domain-specific) |
| `storage/transactions.py` | `TransactionIsolationLevel`, `TransactionProtocol`, `UnitOfWorkProtocol`, `TransactionManagerProtocol` |
| `storage/health.py` | `StorageHealthProtocol`, `StorageHealthRegistryProtocol` |
| `storage/serialization.py` | `SerializerProtocol[T]`, `DeserializerProtocol[T]`, `CodecProtocol[T]`, `SchemaProtocol` |
| `storage/versioning.py` | `MigrationProtocol`, `VersionRegistryProtocol`, `SchemaRegistryProtocol` |

---

## `athena.assets` — Asset Domain

**Rule:** Peer layer. Contains rich financial instrument models.

| Module | Contents |
|---|---|
| `assets/identifiers.py` | `InstrumentId` (UUID), `ExchangeId`, `Symbol` (exchange:ticker structured), `ISIN` (ISO 6166 Luhn), `CurrencyCode` |
| `assets/classification.py` | `AssetClass`, `InstrumentType`, `ExchangeSegment` (NSE/BSE/MCX), `InstrumentStatus`, `OptionType`, `OptionStyle`, `SettlementType`, `MarketTier` |
| `assets/contracts.py` | `ContractSpec` base + `EquitySpec`, `IndexSpec`, `FuturesSpec`, `OptionsSpec`, `ETFSpec`, `CurrencySpec`, `CommoditySpec` |
| `assets/instruments.py` | `Instrument` (single frozen dataclass + 7 factory classmethods: `.equity()`, `.index()`, `.futures()`, `.option()`, `.etf()`, `.currency_pair()`, `.commodity()`) |
| `assets/validation.py` | `ValidationResult`, `validate_instrument()`, `validate_contract()`, `is_valid_isin()`, `is_valid_symbol_string()` |
| `assets/interfaces.py` | `InstrumentLookupProtocol`, `InstrumentRegistryProtocol` |
| `assets/registry.py` | `InstrumentQuery`, `InMemoryInstrumentRegistry` |

**Key design:** Single `Instrument` + discriminated `ContractSpec`, NOT 7 instrument subclasses.

---

## `athena.market` — Market Domain

**Rule:** Peer layer. Represents how markets operate (rules, states, capabilities, sessions).

| Module | Contents |
|---|---|
| `market/models.py` | `MarketId`, `CountryCode`, `MarketCurrency`, `MarketTimezone` (IANA-validated), `WeeklySchedule` |
| `market/exchange.py` | `ExchangeMetadata`, constants: `NSE`, `BSE`, `MCX`, `NYSE`; `InMemoryExchangeRepository` |
| `market/segments.py` | `MarketSegmentType`, `MarketSegment`, `TradingVenue`; constants: `NSE_EQ`, `NSE_FO`, `NSE_CDS`, `BSE_EQ`, `BSE_FO`, `MCX_FO`; `InMemorySegmentRepository` |
| `market/sessions.py` | `MarketSessionType`, `SessionWindow`, `DailySchedule`, `ExchangeSchedule`; `NSE_STANDARD_SCHEDULE` |
| `market/market_state.py` | `MarketState` (9 states), `HaltReason`, `MarketStateSnapshot`, `StateTransition`, `VALID_TRANSITIONS`, `is_valid_transition()`, `validate_transition()` |
| `market/rules.py` | `PriceBandConfig`, `CircuitBreakerThreshold`, `IndexCircuitBreakerConfig`; `SEBI_NSE_CIRCUIT_BREAKER`; `PriceBandRuleProtocol`, `CircuitBreakerRuleProtocol` |
| `market/capabilities.py` | `OrderType`, `OrderValidity`, `OrderCapabilities`, `MarketCapabilities`; `NSE_EQ_CAPABILITIES` |
| `market/interfaces.py` | `ExchangeRepositoryProtocol`, `SegmentRepositoryProtocol`, `MarketCalendarPort`, `MarketStateServiceProtocol`, `ScheduleRepositoryProtocol`, `MarketRulesRepositoryProtocol` |

**Key integration pattern:** `MarketCalendarPort` is defined here and satisfied by `athena.time` — no cross-peer import.

---

## `athena.market_data` — Market Data Domain

**Rule:** Peer layer. Vendor-agnostic representation of historical and live market data.

| Module | Contents |
|---|---|
| `market_data/models.py` | `Timeframe` (18 values, pandas-compatible codes), `TradeSide`, `TickType`, `BarState`, `AdjustmentMethodology`, `timeframe_seconds()`, `is_intraday()` |
| `market_data/metadata.py` | `DataProvenance` (vendor, symbol, retrieval time), `SymbolMapping` |
| `market_data/quality.py` | `QualityFlag` (10 flags), `DataQuality` (frozenset + confidence score, factory methods) |
| `market_data/ohlcv.py` | `OHLCVBar` (richer than core OHLCV), `OHLCVSeries` (validated ordering), `GapInfo` |
| `market_data/ticks.py` | `MarketTick` (richer than core Tick, with conditions, sequence number) |
| `market_data/quotes.py` | `Quote` (bid/ask with spread, mid, is_crossed, effective_quality) |
| `market_data/trades.py` | `Trade` (executed print with notional_value, is_buyer_initiated) |
| `market_data/orderbook.py` | `OrderBookLevel`, `OrderBookSide` (validated ordering), `OrderBookSnapshot` |
| `market_data/corporate_actions.py` | `CorporateActionType` (13 types), `CorporateAction` (split_factor, affects_price) |
| `market_data/adjustments.py` | `AdjustmentFactor`, `AdjustedPrice`, `apply_adjustment()`, `cumulative_price_factor()` |
| `market_data/interfaces.py` | `HistoricalDataProviderProtocol`, `LiveDataProviderProtocol`, `CorporateActionProviderProtocol`, `MarketDataRepositoryProtocol` |
| `market_data/validation.py` | `ValidationResult` + 7 validators |

---

## `athena.features` — Feature Domain

**Rule:** Peer layer. Represents engineered features (NOT calculations).

| Module | Contents |
|---|---|
| `features/models.py` | `FeatureId` (namespace:name structured), `FeatureVersion` (with `satisfies()` constraint), `FeatureNamespace`, `FeatureOutputType`, `InputDataType`, `InputTimeframe` |
| `features/metadata.py` | `ReproducibilityInfo`, `PaperReference`, `FeatureMetadata` |
| `features/schemas.py` | `InputRequirement` (validated min≤lookback), `FeatureOutputField`, `FeatureOutputSchema` |
| `features/dependencies.py` | `FeatureDependency`, `DependencyGraph` (DAG, DFS cycle detection), `ImmutableDependencyGraph` |
| `features/registry.py` | `FeatureDefinition` (with SHA-256 `computation_hash`), `FeatureSet`, `InMemoryFeatureRegistry` |
| `features/interfaces.py` | `FeatureRegistryProtocol`, `FeatureProviderProtocol` |
| `features/validation.py` | `ValidationResult` + 3 validators |

**Key design:** `computation_hash` excludes metadata (description, author) — structural changes invalidate it, documentation changes do not.

---

## `athena.experiments` — Experiment Domain

**Rule:** Peer layer. Reproducible research experiments, no ML.

| Module | Contents |
|---|---|
| `experiments/models.py` | `ExperimentId`, `RunId`, `RunGroupId` (UUID-backed), `ExperimentStatus`, `RunStatus`, `RunGroupPurpose`, transition tables |
| `experiments/parameters.py` | `ParameterValueType`, `ParameterValue` (with `as_int/float/bool`), `ParameterDefinition`, `ParameterSnapshot` (sorted, SHA-256 hash) |
| `experiments/metrics.py` | `MetricDirection`, `ExperimentMetric` (`comparison_value`, `is_better_than()`), `MetricSnapshot` |
| `experiments/artifacts.py` | `ArtifactType` (9 types), `ArtifactLocation`, `ExperimentArtifact` |
| `experiments/metadata.py` | `DatasetVersion`, `FeatureSetVersion`, `ReproducibilitySnapshot` (snapshot_hash, is_clean), `ExperimentMetadata` |
| `experiments/lineage.py` | `ExperimentLineageNode`, `ExperimentLineageGraph` (DAG, cycle detection with rollback) |
| `experiments/registry.py` | `Experiment`, `ExperimentRun` (fully frozen), `ExperimentRunGroup`, `InMemoryExperimentRegistry` |
| `experiments/interfaces.py` | `ExperimentRegistryProtocol` |
| `experiments/validation.py` | `ValidationResult` + 5 validators |

**Key design:** `ExperimentRun` is fully immutable. Status changes use `dataclasses.replace()` and registry replaces the stored instance.

---

## Engine Stubs (not yet implemented)

All five engines have their directory structure in place with docstring-only `__init__.py` files:

```
engines/data/{core,application,infrastructure}/__init__.py
engines/research/{core,application,infrastructure}/__init__.py
engines/intelligence/__init__.py  ← planned, not Sprint 1-8
engines/trading/{core,application,infrastructure}/__init__.py
engines/governance/{core,application,infrastructure}/__init__.py
```

The engine layer is where peer domains are wired together via their Protocol ports.
