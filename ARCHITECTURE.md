# Athena Platform Architecture

> **Audience:** Senior engineers joining the Athena team.  
> **Purpose:** Provide a complete mental model of the system — from first principles to deployment — without reading a single line of code.  
> **Status:** Living document. All significant deviations from this design must be recorded as an Architecture Decision Record (ADR) in `docs/adr/`.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Goals](#2-system-goals)
3. [Guiding Principles](#3-guiding-principles)
4. [The Five-Engine Model](#4-the-five-engine-model)
5. [Hexagonal Architecture](#5-hexagonal-architecture)
6. [Engine Deep-Dives](#6-engine-deep-dives)
   - 6.1 [Data Engine](#61-data-engine)
   - 6.2 [Research Engine](#62-research-engine)
   - 6.3 [Intelligence Engine](#63-intelligence-engine)
   - 6.4 [Trading Engine](#64-trading-engine)
   - 6.5 [Governance Engine](#65-governance-engine)
7. [Module Boundaries and Dependency Rules](#7-module-boundaries-and-dependency-rules)
8. [Data Flow](#8-data-flow)
9. [Lifecycle Diagrams](#9-lifecycle-diagrams)
10. [Technology Stack Rationale](#10-technology-stack-rationale)
11. [Extensibility Model](#11-extensibility-model)
12. [Failure Isolation](#12-failure-isolation)
13. [Scalability Strategy](#13-scalability-strategy)
14. [Security Architecture](#14-security-architecture)
15. [Observability](#15-observability)
16. [Deployment Philosophy](#16-deployment-philosophy)
17. [Future Evolution](#17-future-evolution)
18. [Glossary](#18-glossary)

---

## 1. Executive Summary

Athena is a production-grade, AI-augmented quantitative research and automated trading platform built for Indian derivative markets. It provides a unified, auditable, and extensible surface for the complete research-to-execution lifecycle: from ingesting real-time tick data from the NSE/BSE through the Fyers API, to producing and evaluating trading signals in research notebooks, to placing and managing orders with millisecond-level audit trails, to satisfying SEBI reporting obligations.

The platform is organised around **five independent engines** — Data, Research, Intelligence, Trading, and Governance — each with a clearly bounded responsibility, explicit public interfaces, and the ability to fail or scale independently. Engines communicate through domain events and well-typed service ports rather than direct coupling. This keeps the system testable in isolation, swappable at the infrastructure boundary, and comprehensible as it grows.

Athena is not a monolith that happens to live in one repository. It is a modular platform with deliberate seams — seams that will become service boundaries if and when the operational need arises.

---

## 2. System Goals

### Functional Goals

| ID  | Goal |
|-----|------|
| G-01 | Ingest real-time tick data and order book snapshots for NIFTY, BANKNIFTY, SENSEX, and BANKEX derivatives via Fyers WebSocket feeds with zero data loss under normal market conditions |
| G-02 | Store normalised historical OHLCV, tick, and options chain data in a queryable, time-series-optimised store |
| G-03 | Provide a research environment where quantitative analysts can backtest signal hypotheses against clean, adjusted historical data |
| G-04 | Execute orders through the Fyers REST API with pre-trade risk validation, idempotent retry semantics, and position-level reconciliation |
| G-05 | Maintain an immutable, cryptographically ordered audit trail of every decision, order, fill, and risk event |
| G-06 | Expose configuration-driven risk limits (notional, drawdown, position concentration) that are enforced synchronously on the critical path |
| G-07 | Generate regulatory-compliant trade reports aligned with SEBI requirements |

### Non-Functional Goals

| ID  | Goal | Target |
|-----|------|--------|
| N-01 | Market data latency (WebSocket feed → normalised in-memory tick) | < 10 ms p99 |
| N-02 | Order submission latency (signal → API call dispatched) | < 100 ms p99 |
| N-03 | System availability during NSE trading hours (09:00–16:00 IST) | 99.9% |
| N-04 | Historical data query for any 30-day OHLCV window | < 500 ms |
| N-05 | Full unit test suite execution | < 30 s |
| N-06 | Cold-start time for the trading stack | < 60 s |
| N-07 | Audit log retention | 7 years (SEBI requirement) |

### Anti-Goals

The following are explicitly out of scope at this stage, to prevent premature complexity:

- **No high-frequency trading (HFT) infrastructure.** Athena targets algorithmic strategies with holding periods measured in minutes to days, not microseconds.
- **No multi-broker abstraction at launch.** The platform is Fyers-native. Broker abstraction ports exist but will only be wired to a second broker when there is an operational need.
- **No real-time user-facing web UI.** Operational control is through CLI, notebooks, and structured logs. A web dashboard is a future concern.
- **No cross-market trading (equities outside India).** Focus on NSE/BSE derivative instruments only.

---

## 3. Guiding Principles

These principles are not suggestions. Every design decision in Athena should be traceable back to at least one of them. When a principle is violated, an ADR must explain why.

### P-1: Domain First, Infrastructure Second

The core domain — instruments, orders, positions, signals, risk limits — is pure Python with no external dependencies. Infrastructure (databases, API clients, message queues) depends on the domain; the domain never depends on infrastructure. This makes the business logic testable without network access, a database, or a live broker.

### P-2: Explicit Contracts at Every Boundary

Every interaction between engines happens through an explicitly typed interface (a Python `Protocol` or `ABC`). There are no shared mutable data structures between engines. Violations are caught by mypy in CI, not at runtime in production.

### P-3: Immutability by Default

Market data, audit records, and filled orders are append-only and treated as immutable facts once written. Nothing is updated in place. Corrections are new events that reference the original, not overwrites. This is the foundation for a trustworthy audit trail.

### P-4: Observable at Every Layer

Every engine, every component, and every significant operation emits structured log events with a consistent schema. Latency, error rates, and business metrics are captured as counters and histograms. You should be able to reconstruct the full causal chain of any order from structured logs alone.

### P-5: Fail Safe, Not Fail Open

When a component encounters an unexpected state — network timeout, malformed API response, breached risk limit — the default behaviour is to halt and raise, not to continue with degraded assumptions. The Trading Engine never submits an order it cannot fully validate. A known bad state is always preferable to an unknown good state.

### P-6: Configuration Over Code for Operational Parameters

Risk limits, instrument universes, market session schedules, and exchange-specific parameters are configuration values, not code constants. Changing the BANKNIFTY lot size does not require a code change and a deployment.

### P-7: Research and Production Share a Single Data Contract

The same `Instrument`, `OHLCV`, `OptionChain`, and `Tick` types that flow through the live trading stack are the exact types used in backtesting. There is no separate "research model." This eliminates an entire class of live/backtest divergence bugs.

### P-8: Every External Call is Audited

Any call that leaves the process boundary — Fyers API, database, external data provider — is wrapped in infrastructure adapters that log the request, response, latency, and outcome. Silent failures are impossible by design.

---

## 4. The Five-Engine Model

Athena's functionality is partitioned into five engines. Each engine owns a distinct slice of the system's responsibility. No engine reaches into another engine's internals.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ATHENA PLATFORM                                │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────────────┐   │
│  │              │   │              │   │                              │   │
│  │   DATA       │   │  RESEARCH    │   │      INTELLIGENCE            │   │
│  │   ENGINE     │──▶│  ENGINE      │──▶│      ENGINE                  │   │
│  │              │   │              │   │      (future)                │   │
│  │  Ingestion   │   │  Backtesting │   │                              │   │
│  │  Storage     │   │  Signals     │   │  ML Training                 │   │
│  │  Normalis.   │   │  Analytics   │   │  Model Serving               │   │
│  │              │   │              │   │  Feature Store               │   │
│  └──────┬───────┘   └──────┬───────┘   └─────────────┬────────────────┘   │
│         │                  │                          │                    │
│         │           ┌──────▼───────┐                  │                    │
│         └──────────▶│              │◀─────────────────┘                    │
│                     │   TRADING    │                                        │
│                     │   ENGINE     │                                        │
│                     │              │                                        │
│                     │  OMS / EMS   │                                        │
│                     │  Risk Checks │                                        │
│                     │  Positions   │                                        │
│                     │              │                                        │
│                     └──────┬───────┘                                        │
│                            │                                                │
│                     ┌──────▼───────┐                                        │
│                     │              │                                        │
│                     │  GOVERNANCE  │                                        │
│                     │  ENGINE      │                                        │
│                     │              │                                        │
│                     │  Audit Trail │                                        │
│                     │  Compliance  │                                        │
│                     │  Reporting   │                                        │
│                     │              │                                        │
│                     └──────────────┘                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data Flow Summary:**
- The Data Engine is the single source of truth for market state. All other engines consume data from it; none write to it directly.
- The Research Engine consumes historical data from the Data Engine to produce signal specifications and validated parameter sets.
- The Intelligence Engine (when active) produces model-scored signals that feed into the Trading Engine alongside rule-based signals from Research.
- The Trading Engine is the only engine authorised to submit orders. It consumes signals, applies risk checks, manages positions, and interacts with the broker API.
- The Governance Engine passively consumes events from all other engines. It never blocks execution but it records everything and enforces post-trade compliance checks.

---

## 5. Hexagonal Architecture

Each engine internally follows the hexagonal architecture (also called Ports and Adapters). This is the structural pattern that makes the domain portable across different infrastructure choices.

```
                    ┌─────────────────────────────────────┐
                    │           ENGINE BOUNDARY           │
                    │                                     │
     External       │  ┌─────────┐      ┌─────────────┐  │    External
     Drivers        │  │         │      │             │  │    Systems
   (CLI, API,  ────▶│  │  INPUT  │      │  OUTPUT     │──┼──▶ (DB, Broker
    Scheduler) │    │  │  PORTS  │      │  PORTS      │  │     API, Queue)
                    │  │         │      │             │  │
                    │  └────┬────┘      └──────▲──────┘  │
                    │       │                  │         │
                    │       ▼                  │         │
                    │  ┌────────────────────────────┐    │
                    │  │                            │    │
                    │  │       DOMAIN CORE          │    │
                    │  │                            │    │
                    │  │  Models, Aggregates,       │    │
                    │  │  Domain Services,          │    │
                    │  │  Domain Events             │    │
                    │  │                            │    │
                    │  │  (Zero external imports)   │    │
                    │  │                            │    │
                    │  └────────────────────────────┘    │
                    │                                     │
                    │  Input Adapters  │ Output Adapters  │
                    │  (FastAPI, CLI)  │ (FyersClient,    │
                    │                  │  TimescaleDB)    │
                    └─────────────────────────────────────┘
```

**The three layers inside every engine:**

| Layer | What it contains | What it imports |
|-------|-----------------|-----------------|
| **Core / Domain** | Models, value objects, domain events, pure business rules, port interfaces (Protocols) | Nothing outside the standard library |
| **Application** | Use-case orchestrators, command/query handlers, event handlers | Core only |
| **Infrastructure** | Concrete adapters: Fyers API client, DB repositories, message bus | Core + Application + third-party libraries |

**The dependency rule:** arrows always point inward. Infrastructure adapters know about the domain. The domain knows nothing about infrastructure. This rule is enforced by mypy and by import-linter in CI.

---

## 6. Engine Deep-Dives

### 6.1 Data Engine

**Responsibility:** Be the authoritative, always-current, queryable representation of the Indian derivative market.

**What it owns:**
- Instrument master (all NSE/BSE tradable instruments, lot sizes, tick sizes, expiry calendars)
- Real-time tick and order book ingestion via Fyers WebSocket
- Historical OHLCV data (1-minute and above) from Fyers Historical API
- Options chain snapshots (Greeks, OI, volume)
- Corporate action adjustment logic (splits, dividends, bonuses) for underlying indices
- Data quality validation pipeline (gap detection, outlier flagging, stale price detection)

**Internal structure:**

```
data_engine/
├── core/
│   ├── models/
│   │   ├── instrument.py        # Instrument, Exchange, Segment, LotSize
│   │   ├── tick.py              # Tick (timestamp, ltp, bid, ask, volume)
│   │   ├── ohlcv.py             # OHLCV bar (immutable dataclass)
│   │   ├── option_chain.py      # OptionChain, OptionContract, Greeks
│   │   └── market_session.py    # MarketSession, TradingCalendar
│   ├── ports/
│   │   ├── market_data_feed.py  # Protocol: subscribe(), unsubscribe()
│   │   ├── historical_store.py  # Protocol: fetch_ohlcv(), fetch_ticks()
│   │   └── instrument_repo.py   # Protocol: get_by_symbol(), search()
│   └── services/
│       ├── normaliser.py        # Converts raw Fyers payloads to domain models
│       ├── aggregator.py        # Tick → OHLCV bar aggregation
│       └── quality_checker.py   # Validates incoming data against expectations
├── application/
│   ├── subscribe_to_feed.py     # Use case: start streaming a symbol
│   ├── fetch_history.py         # Use case: populate historical store
│   └── snapshot_chain.py        # Use case: fetch and cache options chain
└── infrastructure/
    ├── fyers_websocket.py       # Adapter: Fyers WebSocket → Tick domain events
    ├── fyers_historical.py      # Adapter: Fyers REST history API
    ├── timescale_store.py       # Adapter: TimescaleDB for OHLCV + ticks
    └── instrument_cache.py      # Adapter: in-memory instrument master (Redis-backed)
```

**Key design decisions:**

- The `Tick` and `OHLCV` types are frozen dataclasses. Once created from a raw exchange payload, they are never mutated.
- The WebSocket adapter reconnects automatically with exponential backoff. All gaps caused by reconnection are recorded as data quality events and filled via the historical API on reconnect.
- Instrument reference data is loaded at startup and held in memory. It is refreshed at market open each day.

**Events emitted:**
- `TickReceived(instrument, tick)`
- `OHLCVBarClosed(instrument, bar)`
- `OptionChainUpdated(underlying, chain)`
- `DataQualityAlert(instrument, severity, description)`
- `MarketSessionEvent(session_type, timestamp)` — pre-open, open, close

---

### 6.2 Research Engine

**Responsibility:** Provide a reproducible, auditable environment for hypothesis testing and signal development against clean historical data.

**What it owns:**
- Backtesting framework (event-driven, not vectorised, to match live execution semantics exactly)
- Signal computation pipeline
- Factor library (primitives: returns, volatility, momentum, mean-reversion, options-specific: IV rank, put/call ratio, skew)
- Performance analytics and tear-sheet generation
- Notebook integration layer (exposes clean Python APIs usable from Jupyter without modification)

**What it does NOT own:**
- Historical data storage (owned by Data Engine)
- Any live market state (it operates on snapshots provided by the Data Engine)
- Order submission (signals are data structures; only the Trading Engine acts on them)

**The backtester design principle:**

The backtester is event-driven and uses the same event types (`TickReceived`, `OHLCVBarClosed`) as the live system. A signal handler written for the backtester is wire-compatible with the live Trading Engine. The only difference is the source of events: in backtest mode, events come from a historical replay engine; in live mode, they come from the Data Engine's WebSocket adapter.

```
Research Backtesting Loop:

  HistoricalStore
       │
       │ yields TickReceived / OHLCVBarClosed events
       ▼
  EventReplayEngine
       │
       │ dispatches to
       ▼
  SignalHandler (user code)
       │
       │ yields SignalEvent
       ▼
  SimulatedBroker  ←── fills at next-bar open, respects slippage model
       │
       │ yields FillEvent
       ▼
  PositionTracker
       │
       ▼
  PerformanceAnalytics
       │
       ▼
  TearSheet (Sharpe, Sortino, Max DD, Calmar, turnover, hit rate)
```

**Key backtesting constraints (no-look-ahead guarantee):**

- All signals are computed using data available at the bar's close timestamp only
- Corporate action adjustments are applied as-of their announcement date, not retroactively
- Slippage is modelled as a configurable fraction of the bid-ask spread at the time of signal
- Commission is applied per-leg at NSE/BSE standard rates by default

**Events consumed:** `TickReceived`, `OHLCVBarClosed`, `OptionChainUpdated`  
**Events emitted:** `SignalGenerated(instrument, direction, confidence, metadata)`

---

### 6.3 Intelligence Engine

**Responsibility:** Train, serve, and monitor ML models that augment or replace rule-based signal generation.

**Status: Planned. Not implemented in v1. This section documents the intended design so that the infrastructure built now does not need to change when ML is introduced.**

**What it will own:**
- Feature store (point-in-time correct feature extraction from tick and OHLCV history)
- Model training pipeline (offline, batch, triggered manually or on schedule)
- Model registry (versioned model artefacts with performance metadata)
- Online model serving (low-latency inference during market hours)
- Model performance monitoring (concept drift detection, prediction calibration)

**Integration contract:**

The Intelligence Engine will consume from the Data Engine exactly as the Research Engine does. It will produce `SignalGenerated` events with an additional `model_version` and `confidence_interval` field. The Trading Engine will accept signals from both Research and Intelligence engines identically — it does not distinguish between a rule-based and an ML-based signal at the execution boundary.

**Why defer ML:**

Deploying ML models in production trading requires a mature data pipeline, a validated backtesting framework, and a robust execution system. Building those first — and getting the plumbing right — produces better ML outcomes than building everything simultaneously.

---

### 6.4 Trading Engine

**Responsibility:** Be the exclusive authority for order submission, position management, and real-time risk control.

**This is the most critical engine in the platform. Any bug here has direct financial consequence.**

**What it owns:**
- Order Management System (OMS): full order lifecycle from creation to terminal state
- Execution Management System (EMS): order routing, smart order splitting, retry logic
- Position ledger: real-time tracking of open positions, unrealised P&L, and notional exposure
- Pre-trade risk checks: synchronous validation that must pass before any order is submitted
- Post-trade reconciliation: comparing the internal position ledger against the broker's position report

**Order lifecycle:**

```
SignalGenerated
     │
     ▼
OrderIntent created (not yet validated)
     │
     ├─▶ Pre-Trade Risk Checks ──── FAIL ──▶ OrderRejected event + audit log
     │        │
     │      PASS
     │        │
     ▼        ▼
OrderValidated
     │
     ▼
FyersOrderAdapter.submit()  ──── Network Error ──▶ Retry (exponential, max 3)
     │                                               │
     │                                             FAIL ──▶ OrderFailed + circuit open
     │
   SUCCESS
     │
     ▼
OrderAcknowledged (broker order_id recorded)
     │
     ▼
FyersWebSocket fill event received
     │
     ▼
OrderFilled (or OrderPartiallyFilled)
     │
     ▼
PositionLedger.apply(fill)
     │
     ▼
Post-Trade Risk Checks (position limits, concentration)
```

**Pre-trade risk check taxonomy:**

| Check | Description | Action on failure |
|-------|-------------|-------------------|
| `InstrumentHaltCheck` | Is the instrument in a circuit breaker or trading halt? | Reject order |
| `MarketSessionCheck` | Is the market currently in a tradable session? | Reject order |
| `PositionLimitCheck` | Would this order breach the per-instrument position limit? | Reject order |
| `NotionalLimitCheck` | Would this order breach the per-strategy notional limit? | Reject order |
| `DrawdownCheck` | Has the portfolio breached the intraday drawdown limit? | Reject order + halt strategy |
| `DuplicateOrderCheck` | Is there an identical open order already in-flight? | Reject order (idempotency) |
| `InstrumentAuthorisedCheck` | Is this instrument in the authorised trading universe? | Reject order |

**Idempotency:**

Every order intent is assigned a client-generated `idempotency_key` (UUID v4). The EMS stores all in-flight idempotency keys in a short-lived cache. Before submitting to the broker, it checks this cache. This prevents duplicate orders from retry storms during network instability.

**Reconciliation:**

At market close and at configurable intraday intervals, the position ledger is compared against the broker's position report from the Fyers API. Any discrepancy generates a `ReconciliationAlert` event and halts automated trading for the affected strategy until a human operator resolves it.

**Events consumed:** `SignalGenerated`, `TickReceived` (for P&L marking)  
**Events emitted:** `OrderIntent`, `OrderValidated`, `OrderRejected`, `OrderAcknowledged`, `OrderFilled`, `OrderPartiallyFilled`, `OrderCancelled`, `OrderFailed`, `PositionUpdated`, `ReconciliationAlert`

---

### 6.5 Governance Engine

**Responsibility:** Maintain an immutable, auditable record of all platform activity and enforce regulatory obligations.

**Critical property: The Governance Engine never blocks execution.** It consumes events asynchronously. If the audit log is slow, orders still flow. If the reporting pipeline fails, trading continues. Governance is a shadow of the system, not a gatekeeper of it (except for risk limits, which are enforced synchronously by the Trading Engine itself).

**What it owns:**
- Immutable audit log: every domain event from every engine, sequenced and hash-chained
- Regulatory reports: SEBI-required trade logs, margin utilisation reports
- Trade surveillance: pattern detection for wash trades, layering, or unusual activity
- Risk limit ledger: current state of all configured risk limits and their utilisation

**Audit log design:**

```
AuditEntry {
    sequence_number: uint64          # Monotonically increasing, gapless
    timestamp_utc: datetime          # Microsecond precision
    engine: str                      # "data" | "research" | "trading" | "governance"
    event_type: str                  # e.g. "OrderFilled"
    payload: dict                    # Full serialised event
    previous_hash: str               # SHA-256 of the previous AuditEntry
    entry_hash: str                  # SHA-256 of this entry
}
```

The hash chain ensures that any retroactive modification of the audit log is detectable. This is a fundamental requirement for regulatory defensibility.

**Retention policy:**

SEBI requires trade records to be retained for 5 years from the date of the transaction. Athena retains all audit log entries for 7 years. Entries older than 30 days are compressed and archived to object storage. The hash chain is preserved across archival.

**Events consumed:** All events from all engines  
**Events emitted:** `AuditEntryWritten`, `ComplianceAlert`, `RegulatoryReportGenerated`

---

## 7. Module Boundaries and Dependency Rules

### Import Hierarchy (strictly enforced by import-linter in CI)

```
athena.core          ← no imports from athena.*
      ▲
athena.data          ← imports athena.core only
      ▲
athena.application   ← imports athena.core, athena.data
      ▲
athena.infrastructure ← imports all of the above + third-party
      ▲
athena.interfaces    ← imports all of the above (thin delivery layer)
```

### Engine-to-Engine Communication Rules

| Allowed | Forbidden |
|---------|-----------|
| Engine A consumes events published by Engine B | Engine A calls Engine B's internal services directly |
| Engine A implements Engine B's declared port (Protocol) | Engine A imports Engine B's infrastructure adapters |
| Engine A reads from shared data stores (DB, cache) via its own adapter | Engines share mutable in-process state |

### The Shared Kernel

A small set of types is shared across all engines: `Instrument`, `Timestamp`, `Currency`, `Quantity`, `Price`. These live in `athena.core.types` and are frozen dataclasses. They are the only cross-engine shared types.

---

## 8. Data Flow

### 8.1 Live Market Data Flow

```
NSE/BSE Exchange
     │
     │  (UDP multicast → Fyers normalisation)
     ▼
Fyers WebSocket API
     │
     │  JSON tick payload
     ▼
FyersWebSocketAdapter                   [infrastructure layer]
     │
     │  Parses, validates, maps to domain model
     ▼
Tick (domain model)
     │
     ├──▶ InMemoryTickBus.publish(TickReceived)
     │          │
     │          ├──▶ DataQualityChecker
     │          ├──▶ OHLCVAggregator (produces OHLCVBarClosed on bar close)
     │          └──▶ TickStore.append()   → TimescaleDB
     │
     └──▶ Subscribers:
               ├── Trading Engine (for real-time P&L marking)
               └── Research Engine (for live signal computation if running)
```

### 8.2 Order Submission Flow

```
[Signal from Research/Intelligence Engine]
     │
     ▼
Trading Engine receives SignalGenerated event
     │
     ▼
OrderIntentBuilder.build(signal, current_position, risk_config)
     │
     ▼
PreTradeRiskGate.validate(order_intent)    ← synchronous, blocks execution
     │
     ├── REJECTED → OrderRejected event → Governance Engine
     │
     └── APPROVED
              │
              ▼
         FyersOrderAdapter.submit(order_intent)
              │
              ├── SUCCESS → OrderAcknowledged event
              │
              └── FAILURE → Retry with exponential backoff
                                │
                                ├── Max retries exceeded → OrderFailed event
                                │                          + circuit breaker opens
                                └── Success → OrderAcknowledged event
```

### 8.3 Research / Backtest Data Flow

```
Analyst writes signal logic using ResearchEngine API
     │
     ▼
BacktestRunner.run(signal_spec, universe, date_range, params)
     │
     ▼
HistoricalReplayEngine reads from TimescaleDB
     │  (ordered by timestamp, respects corporate action adjustments)
     ▼
Emits: TickReceived / OHLCVBarClosed events (same types as live)
     │
     ▼
Signal logic handles events → yields SignalGenerated
     │
     ▼
SimulatedBroker fills at next available price + slippage model
     │
     ▼
PerformanceAnalytics.compute(fills, positions)
     │
     ▼
TearSheet rendered to notebook or saved to research/ directory
```

---

## 9. Lifecycle Diagrams

### 9.1 Platform Startup Sequence

```
Process start
     │
     ├─1─▶ Load and validate configuration (pydantic-settings)
     │      Fail fast on missing required secrets
     │
     ├─2─▶ Establish database connections (TimescaleDB, Redis)
     │      Health-check each connection before proceeding
     │
     ├─3─▶ Load instrument master from DB + warm in-memory cache
     │      Verify against Fyers API instrument list
     │
     ├─4─▶ Start Governance Engine (audit log ready before anything else)
     │
     ├─5─▶ Start Data Engine
     │      ├─ Connect Fyers WebSocket
     │      ├─ Subscribe to configured instrument universe
     │      └─ Backfill any gaps since last shutdown
     │
     ├─6─▶ Start Trading Engine
     │      ├─ Load persisted position state from DB
     │      ├─ Reconcile against Fyers live positions
     │      └─ Open pre-trade risk gate
     │
     └─7─▶ System READY — emit SystemReadyEvent
```

### 9.2 Market Session Lifecycle

```
04:00 IST  System health check, config reload
     │
09:00 IST  Pre-market session opens
     │      ├─ Refresh instrument master
     │      ├─ Fetch overnight corporate actions
     │      └─ Run data quality checks on previous day close
     │
09:15 IST  Market open
     │      ├─ Trading Engine accepts new orders
     │      ├─ Signal generators activate
     │      └─ Real-time P&L tracking begins
     │
     │  [Normal trading]
     │
14:30 IST  Intraday reconciliation checkpoint
     │      ├─ Compare internal positions vs. Fyers positions
     │      └─ Generate intraday exposure report
     │
15:30 IST  Market close
     │      ├─ Trading Engine halts new order submissions
     │      ├─ Manage open positions per configured EOD rules
     │      └─ Close signal generators
     │
15:30–16:00  Post-market close auction (BSE SENSEX/BANKEX components)
     │
16:00 IST  End-of-day reconciliation
     │      ├─ Final Fyers position reconciliation
     │      ├─ P&L attribution report
     │      ├─ Regulatory trade log generation
     │      └─ Archive tick data
     │
18:00 IST  F&O expiry checks (weekly/monthly as applicable)
     │
20:00 IST  System diagnostic report
```

### 9.3 Order State Machine

```
                      ┌─────────────────────────┐
                      │      OrderIntent         │
                      └────────────┬────────────┘
                                   │
                         Pre-trade risk check
                                   │
               ┌───────────────────┴───────────────────┐
               │                                       │
               ▼ PASS                                  ▼ FAIL
    ┌──────────────────────┐               ┌──────────────────────┐
    │   OrderValidated     │               │   OrderRejected      │ (terminal)
    └────────────┬─────────┘               └──────────────────────┘
                 │
                 │ submit to broker
                 │
    ┌────────────▼─────────┐
    │  OrderAcknowledged   │
    │  (broker order_id)   │
    └────────────┬─────────┘
                 │
     ┌───────────┴──────────┐
     │                      │
     ▼                      ▼
┌─────────┐          ┌─────────────────┐
│ OrderFilled│        │OrderPartialFilled│
│ (terminal) │        │                 │
└─────────┘          └────────┬────────┘
                               │
                    ┌──────────▼──────────┐
                    │     (waiting)        │
                    └──────────┬──────────┘
                               │
                  ┌────────────┴───────────┐
                  │                        │
                  ▼                        ▼
          ┌─────────────┐         ┌─────────────────┐
          │ OrderFilled │         │ OrderCancelled  │
          │ (terminal)  │         │ (terminal)      │
          └─────────────┘         └─────────────────┘
```

---

## 10. Technology Stack Rationale

### Core Language: Python 3.12+

**Why Python:** The scientific and quantitative finance ecosystem is unmatched — NumPy, Pandas, SciPy, and every broker API SDK is Python-first. The latency requirements of Athena (order submission < 100ms) are achievable in Python. If microsecond execution were needed, this choice would be revisited.

**Why 3.12+:** PEP 695 (type parameter syntax), improved performance (10-60% faster than 3.10 in CPU-bound tasks), and `tomllib` in stdlib.

### Package Manager: `uv`

Chosen over Poetry and pip for its Rust-based speed (cold installs 10-100x faster than pip, critical in CI), full PEP compliance (517/518/621), and lock file reliability. See `docs/adr/0002-use-uv.md`.

### Time Series Database: TimescaleDB (PostgreSQL extension)

**Why TimescaleDB over InfluxDB, QuestDB, or pure PostgreSQL:**

| Consideration | TimescaleDB |
|---------------|-------------|
| SQL compatibility | Full PostgreSQL — existing tooling works unchanged |
| Time-series performance | Automatic hypertable partitioning; 10-100x better insert/query performance for time-series vs. vanilla PG |
| Continuous aggregates | Pre-computed OHLCV rollups with automatic refresh |
| Compression | Native columnar compression; 90%+ size reduction for tick data |
| Operational simplicity | Single PostgreSQL process; no separate TSDB daemon |
| Joins with reference data | Native SQL joins between tick data and instrument master |

### In-Memory Cache / Pub-Sub: Redis

Used for:
- Real-time instrument master cache (read on every order validation)
- Intra-process event bus (list-based lightweight pub/sub)
- Short-lived idempotency key cache for order deduplication (TTL: 60s)
- Session state for reconnecting WebSocket clients

Not used for durable storage. If Redis is unavailable, the platform degrades gracefully (slower instrument lookups from DB, no in-flight idempotency cache).

### Async Runtime: asyncio

The WebSocket feed, order acknowledgement callbacks, and all I/O-bound infrastructure adapters are async. CPU-bound work (signal computation, backtesting) runs in a process pool to avoid blocking the event loop.

### Structured Logging: `structlog`

Every log entry is a JSON object with consistent fields: `timestamp`, `engine`, `component`, `event`, `correlation_id`, and event-specific payload. In development, structlog renders these as colourised key=value pairs. In production, raw JSON is written to stdout for collection by the logging infrastructure.

### Configuration: `pydantic-settings`

All configuration is validated at startup using Pydantic v2 models. `SecretStr` fields prevent secrets from appearing in logs or stack traces. Configuration hierarchy: environment variables > `.env` file > `configs/{environment}.toml`.

### HTTP Client: `httpx`

Used by all infrastructure adapters that call REST APIs (Fyers order submission, historical data fetching). Chosen over `requests` for native async support and better connection pool management.

### Linting and Formatting: Ruff

Single tool that replaces flake8, isort, pyupgrade, and Black. Runs in < 1 second on the full codebase. See `.ruff.toml` for full configuration.

### Type Checking: mypy (strict mode)

All public APIs are fully typed. `--strict` mode is enabled. mypy runs in CI on every PR. Type stubs (`types-*`) are installed for all third-party dependencies that lack inline types.

### Testing: pytest + hypothesis

Unit tests use `pytest` with `pytest-asyncio` for async code and `hypothesis` for property-based testing of financial calculations (e.g., verify that P&L calculation is associative across any sequence of fills). Integration tests run against a real TimescaleDB instance in Docker.

---

## 11. Extensibility Model

### Adding a New Broker

1. Implement the `BrokerPort` Protocol from `athena.core.ports.broker`
2. Implement the `MarketDataFeedPort` Protocol from `athena.core.ports.market_data`
3. Register the new adapters in the dependency injection container in `athena.infrastructure.container`
4. Add broker-specific configuration schema in `athena.core.config`

The Trading Engine, Research Engine, and all domain logic require zero changes.

### Adding a New Instrument Universe

1. Add instruments to the instrument master (configuration, not code)
2. Subscribe the Data Engine to the new symbols
3. The rest of the platform observes the subscription and begins processing

No code changes required if the instruments are on supported exchanges.

### Adding a New Signal Type

1. Write a handler class that implements the `SignalHandlerPort` Protocol
2. Register it with the Research Engine's signal registry
3. It immediately becomes available in both backtesting and live modes

### Adding a New Data Source

1. Implement the `HistoricalStorePort` or `MarketDataFeedPort` Protocol
2. Connect it via the infrastructure container

The domain core and application layers are unaware of which data source backs them.

---

## 12. Failure Isolation

### Engine Isolation

Each engine runs with its own error boundary. A crash in the Research Engine (e.g., a signal computation error in a notebook) does not affect the Trading Engine's ability to manage existing positions. The Governance Engine is the most defensive: it processes events from a persistent queue so it can never lose an audit entry even if it temporarily lags.

### Failure Mode Taxonomy

| Component | Failure Mode | System Response |
|-----------|-------------|-----------------|
| Fyers WebSocket | Disconnect | Reconnect with exponential backoff (max 5 retries in 60s). Gap recorded. History backfill on reconnect. |
| Fyers REST API (orders) | Network timeout | Retry up to 3x with jitter. After 3 failures, open circuit breaker for that order type. Alert sent. |
| TimescaleDB | Connection lost | Application retries with backoff. In-memory buffer holds tick data for up to 60 seconds. Alert after 10 seconds. |
| Redis | Unavailable | Degrade gracefully: use direct DB lookups for instrument master. Idempotency cache disabled (duplicate order risk increases — alert sent). |
| Pre-trade risk check | Internal error | Fail closed: order is rejected. Never submit an order when risk check state is uncertain. |
| Position reconciliation | Divergence detected | Halt automated trading for affected strategy. Raise alert. Require manual operator acknowledgement before resuming. |

### Circuit Breakers

Three circuit breakers protect external call surfaces:

1. **Broker Order Circuit Breaker** — opens after 3 consecutive order submission failures within 60 seconds. Closes after a configurable cooldown (default: 120 seconds) and one successful test call.
2. **Market Data Circuit Breaker** — opens after the WebSocket reconnect budget is exhausted. Closes when a stable connection is re-established.
3. **Database Circuit Breaker** — opens after 5 consecutive DB connection failures. Switches to in-memory degraded mode.

---

## 13. Scalability Strategy

### Current Phase (Single-Process)

Athena v1 runs as a single Python process with asyncio for I/O concurrency and a process pool for CPU-bound computation. This is sufficient for trading a handful of strategies across 4 index derivatives. The single-process model simplifies operational reasoning and eliminates distributed systems failure modes at this stage.

### Near-Term Horizontal Scaling (Without Architecture Change)

The engines are designed to support horizontal scaling through shared state (TimescaleDB + Redis) without requiring the architecture to change:

- **Multiple Data Engine instances** can share a Redis pub/sub bus — one feeds data, others subscribe
- **Multiple Trading Engine instances** can each manage a disjoint strategy universe while sharing the position ledger in TimescaleDB
- **Research Engine** is stateless; any number of instances can run backtests in parallel against the same DB

### Long-Term Service Decomposition

The engine boundaries are the natural future service boundaries. When operational scale demands it:

```
v1: Single process
    athena/
      data_engine/
      trading_engine/
      governance_engine/

v2: Independent services (same codebase, different entry points)
    athena-data-service     → deployed separately, scales independently
    athena-trading-service  → stateful, single instance per strategy cluster
    athena-governance-service → replicated for HA audit

v3: Polyglot where warranted
    Data ingest → possibly Rust for tick normalisation at higher instrument count
    ML serving → Python (FastAPI) or ONNX runtime
```

No architectural changes are required to make this transition — only infrastructure wiring.

---

## 14. Security Architecture

### Threat Model Summary

Athena's primary threats are:
1. **Secret exposure** — Fyers API credentials, database passwords leaked via logs, error messages, or accident commits
2. **Unauthorised order submission** — an attacker injecting synthetic signal events to trigger orders
3. **Data poisoning** — tampered market data producing incorrect signals
4. **Audit trail manipulation** — retroactive modification of trade records
5. **Supply chain attacks** — malicious packages in the dependency tree

### Mitigations

**Secret Management:**
- No secrets in code or configuration files checked into git. `.env` is in `.gitignore`.
- All secrets are `SecretStr` in Pydantic configuration models. They are never serialised into logs.
- In production, secrets are injected via environment variables from a secrets manager (AWS Secrets Manager, HashiCorp Vault, or Docker secrets).
- `git-secrets` and `detect-secrets` are enforced in pre-commit hooks.

**Order Injection Prevention:**
- The Trading Engine is the only component authorised to submit orders. It accepts `SignalGenerated` events only from registered, in-process signal handlers — not from the network.
- The Fyers API client is constructed with credentials at startup and is not exposed outside the infrastructure layer.

**Data Integrity:**
- Every tick received from the Fyers WebSocket is validated against expected schema and plausibility checks before entering the domain.
- Anomalous ticks (price moves > configurable threshold from last known price) are quarantined and flagged before influencing any signal.

**Audit Trail Integrity:**
- The hash chain described in the Governance Engine section makes retroactive log tampering detectable.
- Audit log storage is append-only at the database level (PostgreSQL row-level security prohibits UPDATE/DELETE on the audit table).

**Dependency Security:**
- `pip-audit` runs on every PR to detect CVEs in dependencies.
- `dependabot` is configured to raise PRs for security updates automatically.
- The dependency lock file (`uv.lock`) ensures reproducible builds — no floating dependencies.

**Network Segmentation:**
- The trading host has outbound access only to Fyers API endpoints and configured data sources.
- No inbound internet access.
- All internal services (DB, Redis) communicate on a private network.

---

## 15. Observability

### Three Pillars

**1. Structured Logs**

Every log line is a JSON object. The following fields are mandatory on every entry:

```json
{
  "timestamp": "2025-01-15T09:15:00.123456Z",
  "level": "info",
  "engine": "trading",
  "component": "pre_trade_risk_gate",
  "event": "OrderValidated",
  "correlation_id": "a3f1c2d4-...",
  "order_id": "...",
  "instrument": "NSE:NIFTY25JAN24500CE",
  "latency_ms": 1.2
}
```

**2. Metrics**

All metrics are exposed in Prometheus format via a `/metrics` endpoint. Key metrics by engine:

| Engine | Metric | Type |
|--------|--------|------|
| Data | `athena_ticks_received_total` | Counter |
| Data | `athena_tick_latency_ms` | Histogram |
| Data | `athena_data_quality_alerts_total` | Counter |
| Trading | `athena_orders_submitted_total` | Counter |
| Trading | `athena_order_submission_latency_ms` | Histogram |
| Trading | `athena_orders_rejected_total{reason}` | Counter |
| Trading | `athena_position_pnl_inr` | Gauge |
| Trading | `athena_risk_limit_utilisation{limit_type}` | Gauge |
| Governance | `athena_audit_entries_total` | Counter |
| Governance | `athena_reconciliation_discrepancies_total` | Counter |
| System | `athena_engine_status{engine}` | Gauge (1=healthy, 0=degraded) |

**3. Distributed Traces**

Every order's journey — from signal to fill — is tracked as a single trace with spans for each stage: risk check, API submission, acknowledgement, fill. Correlation IDs are propagated across all log entries in the trace.

### Alerting Philosophy

Alerts fall into three tiers:

| Tier | Examples | Response |
|------|---------|----------|
| **Critical (page immediately)** | Broker circuit breaker open, reconciliation divergence, risk limit breach | Human response within 5 minutes |
| **Warning (alert within market hours)** | WebSocket reconnect, data quality alerts, order rejection rate elevated | Human response within 30 minutes |
| **Info (daily digest)** | Missing end-of-day data, slow historical queries | Review next business day |

---

## 16. Deployment Philosophy

### Environments

| Environment | Purpose | Data Source | Order Submission |
|-------------|---------|-------------|-----------------|
| `development` | Local engineer machines | Replay historical data or Fyers paper trade account | Paper/simulated only |
| `staging` | Pre-production validation | Live Fyers feed (read-only) | Paper/simulated only |
| `production` | Live trading | Live Fyers feed | Live orders |

No code changes are required between environments. Only configuration changes.

### Container Strategy

The full Athena stack is containerised with Docker. A single `docker-compose.yml` brings up the complete local environment:

- `athena-app` — the main Python process
- `timescaledb` — time series database
- `redis` — cache and pub/sub
- `prometheus` — metrics collection
- `grafana` — dashboards

Production deployment uses the same images, with environment-specific configuration injected at runtime.

### Deployment Checklist (pre-production)

Every production deployment must pass:

1. All unit and integration tests green
2. mypy type check passes
3. No known CVEs in pip-audit
4. Pre-trade risk configuration reviewed and approved
5. Fyers API connectivity verified against production endpoint
6. Position reconciliation confirmed clean (zero open unreconciled positions)
7. Runbook updated if deployment changes operational procedures

### Rollback Strategy

Every deployment is tagged with the git SHA and the image is retained in the container registry. Rollback is achieved by redeploying the previous image tag. The database schema is versioned with Alembic; rollback migrations are written alongside every forward migration.

---

## 17. Future Evolution

The following capabilities are on the long-term roadmap. They are documented here so that current design decisions can account for them without implementing them prematurely.

### Intelligence Engine (ML)

- Feature store backed by TimescaleDB continuous aggregates
- Offline model training pipeline (could be local or cloud-based batch compute)
- ONNX model serving for framework-agnostic inference
- A/B testing framework for model comparison in live trading

### Multi-Broker Support

The `BrokerPort` Protocol is already defined. Adding Zerodha, Interactive Brokers, or another NSE-authorised broker requires implementing this Protocol and registering it in the container. The smart order router can then split orders across brokers based on liquidity, fees, or reliability.

### Real-Time Risk Dashboard

A lightweight FastAPI application exposing the Trading Engine's position ledger and risk metrics via REST and WebSocket. Designed to be read-only and stateless — it subscribes to the event bus and renders live data.

### Strategy Isolation

When the strategy count grows, strategies should run in isolated subprocesses with per-strategy resource limits, position limits, and kill switches. The current single-process model will be a bottleneck.

### Expanded Instrument Coverage

The data and trading infrastructure is designed to be exchange-agnostic at the domain level. Expanding to equity futures, commodity derivatives (MCX), or currency derivatives (NSE CDS) requires:
- Adding instruments to the instrument master
- Configuring exchange-specific session schedules
- Implementing exchange-specific lot size and tick size rules

No architectural changes are needed.

---

## 18. Glossary

| Term | Definition |
|------|-----------|
| **ADR** | Architecture Decision Record. A short document recording a significant technical decision, its context, and the rationale for the choice made. Stored in `docs/adr/`. |
| **EMS** | Execution Management System. The component responsible for routing, splitting, and retrying orders to the broker API. |
| **EOD** | End of Day. Refers to the market close process and associated reconciliation. |
| **F&O** | Futures and Options. Derivative instruments traded on NSE/BSE. The primary instrument class for Athena. |
| **Hypertable** | TimescaleDB's partitioned table type. Automatic time-based partitioning for high-performance time-series storage. |
| **Idempotency Key** | A unique key assigned to each order attempt, used to prevent duplicate order submission during retries. |
| **IST** | Indian Standard Time (UTC+5:30). All market session times in this document are IST. |
| **OMS** | Order Management System. The component responsible for tracking the full lifecycle of every order from creation to terminal state. |
| **Port (Hexagonal)** | A typed interface (Python Protocol or ABC) defining how the domain interacts with external systems, without specifying the implementation. |
| **Adapter (Hexagonal)** | A concrete implementation of a Port that connects the domain to a specific external technology (e.g., Fyers API, TimescaleDB). |
| **SEBI** | Securities and Exchange Board of India. The regulatory body governing Indian financial markets. |
| **Signal** | A structured directive produced by the Research or Intelligence Engine, representing a view on a specific instrument (direction, size, confidence). The Trading Engine converts signals into orders. |
| **Tear Sheet** | A standardised performance summary for a trading strategy, including Sharpe ratio, maximum drawdown, Sortino ratio, hit rate, and turnover. |
| **Tick** | A single market data update representing a trade or quote at a specific timestamp. The atomic unit of market data. |
| **TimescaleDB** | A PostgreSQL extension optimised for time-series data, used as Athena's primary data store. |

---

*This document was authored at project inception and reflects the intended architecture of Athena v1. It is a living document. All deviations should be captured as ADRs, and this document should be updated to reflect the agreed design.*

*Last reviewed: 2026-06-27*  
*Owner: Platform Engineering*
