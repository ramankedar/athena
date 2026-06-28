# Athena Current Status

**Last updated:** 2026-06-28  
**Branch:** `feat/bootstrap`  
**Commit:** `ac8b3d1` — Sprint 8: Experiment Domain  

---

## By the Numbers

| Metric | Value |
|---|---|
| Total Python source files | 126 |
| Total test files | 106 |
| Total lines of code | ~65,000 |
| Passing tests | **1,747** |
| Overall coverage | **95%** |
| Ruff violations | **0** |
| Open GitHub Issues | 0 |
| Sprint velocity | 8 sprints completed |

---

## What Is Production-Ready

All eight completed domains are production-quality:
- Strict mypy types (no `Any`)
- Google-style docstrings on every public surface
- 95%+ test coverage (unit tests only — no live services required)
- Ruff clean (lint + format)
- Import-linter contracts enforced (22 contracts, 0 violations)
- Conventional commit messages

---

## Current State by Package

### `athena.platform` ✅ Sprint 1
- `AthenaSettings` loads from env vars with `ATHENA_*` prefix, double-underscore nesting
- `configure_logging()` switches structlog between ConsoleRenderer (dev) and JSONRenderer (prod)
- `bootstrap_application()` → `ApplicationContext` (frozen, carries settings + started_at)
- `bind_context()` uses `ContextVar` for async-safe correlation ID tracking
- **Note:** `cache_logger_on_first_use=False` so test suites can reconfigure

### `athena.time` ✅ Sprint 2
- `SystemClock` is the ONLY place `datetime.now()` is called in the entire codebase
- `NSETradingCalendar` — weekdays minus holidays, 365-day safety limit on searches
- `NSESessionService` — 5 session phases (PRE_OPEN, PRE_OPEN_MATCHING, NORMAL, CLOSING, POST_CLOSE), left-inclusive bounds
- `NSEExpiryCalculator` — last Thursday of month (monthly), configurable weekday (weekly), holiday-adjusted
- `NIFTY_WEEKLY_EXPIRY_DAY = WeeklyExpiryDay.THURSDAY`, `SENSEX_WEEKLY_EXPIRY_DAY = WeeklyExpiryDay.TUESDAY`

### `athena.storage` ✅ Sprint 3
- Pure interfaces, no implementations
- `Page[T]` — every list operation returns paginated results, never raw lists
- `StorageKey = str` — canonical string form of any backend key
- `SchemaVersion(order=True)` — supports `max()` and `sorted()`
- `UnitOfWorkProtocol` — groups repositories into atomic transactions
- Optimistic locking via `OptimisticLockSpec(expected_version=n)`

### `athena.assets` ✅ Sprint 4
- Single `Instrument` + discriminated `ContractSpec` (not 7 subclasses)
- `Symbol` is a STRUCTURED value object (`exchange:ticker`), not a NewType
- `ISIN` validates ISO 6166 Luhn check digit (verified: HDFC Bank `INE040A01034`, Apple `US0231351067`)
- `InMemoryInstrumentRegistry` — indexed by id, symbol, ISIN; O(1) lookups
- `ExchangeSegment.exchange_code` property extracts "NSE" from "NSE_FO"

### `athena.market` ✅ Sprint 5
- `NSE`, `BSE`, `MCX`, `NYSE` as module-level `ExchangeMetadata` constants
- `SEBI_NSE_CIRCUIT_BREAKER` — 10%/15%/20% thresholds, 45min/105min/rest-of-day halts
- `NSE_STANDARD_SCHEDULE` — PRE_OPEN(9:00-9:15), CONTINUOUS(9:15-15:30), CLOSING_AUCTION(15:30-16:00) IST
- `VALID_TRANSITIONS` — explicit frozenset of valid `(from, to)` MarketState pairs
- `MarketCalendarPort` — integration boundary; `athena.time` satisfies it without cross-peer import

### `athena.market_data` ✅ Sprint 6
- `Timeframe` uses string codes matching Fyers/pandas convention (`"1T"`, `"1H"`, `"1D"`)
- `OHLCVBar` validates: H≥max(O,C), L≤min(O,C), VWAP∈[L,H], all prices > 0
- `OHLCVSeries.detect_gaps()` — 2× threshold heuristic (avoids overnight false positives)
- `DataQuality` — `frozenset[QualityFlag]` + `float` confidence; `GAP_FILLED`, `SYNTHETIC`, etc.
- `DataProvenance` — vendor, vendor_symbol, retrieved_at, is_delayed, delay_minutes
- `computation_hash` not included — content hash belongs on the storage layer, not market data domain

### `athena.features` ✅ Sprint 7
- `FeatureId(namespace, name)` → `"technical:rsi_14"` — structured, not bare string
- `FeatureVersion.satisfies(">=1.0.0")` — constraint checking for dependency pinning
- `DependencyGraph` — DFS cycle detection with rollback on `add_dependency()`
- `computation_hash` in `FeatureDefinition` — SHA-256 of id+version+params+deps+schema (NOT metadata)
- `ParameterSnapshot` — always sorted by name; `snapshot_hash` enables deduplication
- `InputDataType`/`InputTimeframe` — independent of `athena.market_data` (peer isolation)

### `athena.experiments` ✅ Sprint 8
- `ReproducibilitySnapshot.snapshot_hash` — SHA-256 of git commit, seed, env, datasets, features
- `ReproducibilitySnapshot.is_clean` — True only when commit is set AND not dirty
- `ExperimentRun` — fully frozen; status transitions use `dataclasses.replace()` in registry
- `ExperimentLineageGraph` — DFS cycle detection, ancestors/descendants/roots/leaves traversal
- `ExperimentRunGroup` — recommended addition for hyperparameter sweeps, walk-forward, Monte Carlo
- `MetricDirection.LOWER_IS_BETTER` uses positive values (10% drawdown, not -10%)

---

## What Needs Wiring (Cross-Domain Integration Points)

These are Protocol ports that exist but have no concrete implementations yet:

| Port | Defined In | Needs Implementation |
|---|---|---|
| `MarketCalendarPort` | `athena.market` | `athena.time.NSETradingCalendar` |
| `MarketDataFeedPort` | `athena.core.ports` | Fyers WebSocket adapter |
| `HistoricalStorePort` | `athena.core.ports` | TimescaleDB adapter |
| `InstrumentRepositoryPort` | `athena.core.ports` | Redis + TimescaleDB adapter |
| `BrokerPort` | `athena.core.ports` | Fyers REST adapter |
| `HistoricalDataProviderProtocol` | `athena.market_data` | Fyers Historical adapter |
| `LiveDataProviderProtocol` | `athena.market_data` | Fyers WebSocket adapter |
| `MarketDataRepositoryProtocol` | `athena.market_data` | TimescaleDB adapter |
| `FeatureRegistryProtocol` | `athena.features` | Database-backed impl |
| `ExperimentRegistryProtocol` | `athena.experiments` | Database-backed impl |
| `FeatureProviderProtocol` | `athena.features` | Pandas/polars compute engine |

---

## Known Technical Debt

1. **`athena.shared/`** — Bootstrap-era scaffold with basic `config.py`, `logging.py`, `exceptions.py`. Superseded by `athena.platform`. Should be removed in a cleanup sprint.

2. **`athena.core.domain.instrument.Exchange`** — A simple StrEnum for lightweight identification. Coexists with the richer `athena.market.ExchangeMetadata`. Both serve valid but different purposes (events vs. operations).

3. **`athena.core.domain.market.SessionType`** — Predates the richer `athena.time.session.MarketSessionType`. Both coexist; engines can use either depending on context.

4. **`athena.core.ports`** — Ports defined in core domain for the five engine architecture. Some overlap conceptually with Protocol ports in peer domains. Will be reconciled when engines are implemented.

5. **`UP046` suppressed** — PEP 695 generic class syntax (`class Page[T]:`) is available in Python 3.12+ but some tooling support is incomplete. Global suppress in pyproject.toml.

---

## Import-Linter Contract Count

22 contracts enforced. Zero violations on `feat/bootstrap`. Run `make import-check` to verify.

---

## CI Status

All GitHub Actions workflows are defined in `.github/workflows/`:
- `ci.yml` — quality (ruff, mypy, import-linter) + unit tests (3.12 + 3.13 matrix) + integration + security audit
- `release.yml` — on tag push: build + changelog extraction + GitHub Release
- `codeql.yml` — weekly Monday 02:00 UTC security scan

CI has not yet been run against GitHub (no PRs have been opened). All checks pass locally.
