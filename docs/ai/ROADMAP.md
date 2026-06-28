# Athena Development Roadmap

## Completed Sprints (1–8)

All infrastructure and domain modelling is complete. The platform has 1,747 passing tests at 95% overall coverage.

| Sprint | Title | Package | Tests | Coverage |
|---|---|---|---|---|
| 1 | Platform Foundation | `athena.platform` | ~60 | 99% |
| 2 | Time Domain | `athena.time` | ~90 | 96% |
| 3 | Storage Foundation | `athena.storage` | ~100 | 100% |
| 4 | Asset Domain | `athena.assets` | ~230 | 97% |
| 5 | Market Domain | `athena.market` | ~130 | 96% |
| 6 | Market Data Domain | `athena.market_data` | ~220 | 96% |
| 7 | Feature Domain | `athena.features` | ~175 | 98% |
| 8 | Experiment Domain | `athena.experiments` | ~210 | 98% |

---

## Planned Sprints

### Sprint 9 — Data Engine (Infrastructure)

**Purpose:** Implement concrete adapters for the Data Engine.

**Scope:**
- Fyers WebSocket adapter → `MarketDataFeedPort`
- Fyers Historical API adapter → `HistoricalStorePort`
- TimescaleDB adapter for OHLCV + tick storage
- Redis-backed instrument master cache → `InstrumentRepositoryPort`
- Data quality pipeline (gap detection, outlier flagging, backfill on reconnect)
- Alembic schema migrations

**Key interfaces to satisfy:**
- `athena.storage.repositories.TickRepositoryProtocol`
- `athena.storage.repositories.OHLCVRepositoryProtocol`
- `athena.core.ports.market_data_feed.MarketDataFeedPort`
- `athena.core.ports.historical_store.HistoricalStorePort`
- `athena.core.ports.instrument_repository.InstrumentRepositoryPort`

**Out of scope:** No order management, no signal computation.

---

### Sprint 10 — Research Engine (Backtesting)

**Purpose:** Event-driven backtesting framework.

**Scope:**
- `HistoricalReplayEngine` — replays stored ticks/OHLCV as `TickReceived`/`OHLCVBarClosed` domain events
- `SignalHandlerPort` — interface a signal handler must implement
- `SimulatedBroker` — fills at next-bar open price + configurable slippage model
- `PositionTracker` — tracks open positions, unrealised P&L during backtest
- `PerformanceAnalytics` — Sharpe, Sortino, max drawdown, Calmar ratio, hit rate, turnover
- `TearSheet` — renders performance summary to notebook or file

**Key principle:** Signal handlers for backtesting are wire-compatible with the live Trading Engine. Only the event source changes (historical replay vs. live feed).

---

### Sprint 11 — Trading Engine (Core)

**Purpose:** Order management and pre-trade risk.

**Scope:**
- `OMS` — Order lifecycle state machine (PENDING → ACKNOWLEDGED → FILLED)
- `EMS` — Routing, retry with exponential backoff, idempotency key cache
- Pre-trade risk gate (7 synchronous checks: InstrumentHalt, SessionCheck, PositionLimit, NotionalLimit, DrawdownLimit, DuplicateOrder, InstrumentAuthorised)
- Broker circuit breaker (3 retries + backoff → open)
- Real-time position ledger
- Fyers order adapter → `BrokerPort`
- Fyers fill event listener (WebSocket `OnOrderUpdate`)

---

### Sprint 12 — Governance Engine

**Purpose:** Audit trail and SEBI compliance.

**Scope:**
- Hash-chained audit log (SHA-256 previous-entry chain)
- PostgreSQL append-only table (RLS: no UPDATE/DELETE at DB level)
- SEBI trade log format (regulatory reporting)
- EOD position reconciliation against broker
- Margin utilisation reporting
- Alert dispatcher (Slack/email/PagerDuty)

---

### Sprint 13 — Intelligence Engine (ML Pipeline)

**Purpose:** Feature computation and ML model serving.

**Scope:**
- Feature store (point-in-time correct extraction from TimescaleDB)
- ONNX model serving (latency target: < 10ms p99 inference)
- Model registry (versioned artefacts + performance metadata)
- Concept drift detection (distribution shift monitoring)
- Integration with `athena.features.FeatureRegistryProtocol`

**Note:** Intelligence Engine outputs `SignalGenerated` events identical to Research Engine. Trading Engine consumes both without distinguishing source.

---

### Sprint 14 — REST/WebSocket API

**Purpose:** Operational control surface for human operators.

**Scope:**
- FastAPI application (`athena.interfaces.api`)
- Positions and P&L endpoints
- Order status endpoint
- Market state endpoint
- Live P&L WebSocket feed
- Strategy start/stop controls
- API key + HMAC request signature authentication

---

### Sprint 15 — Production Hardening

**Purpose:** Prepare for live trading.

**Scope:**
- Walk-forward validation against Fyers paper account
- Full end-to-end integration tests (requires live services)
- Prometheus metrics (all `athena_*` metrics from ARCHITECTURE.md)
- Grafana dashboards (P&L, latency, circuit breaker state)
- Runbook documentation
- Deployment guide (Docker → VPS → NSE co-location)

---

## Non-Goals (permanent)

These will never be part of Athena:

- **Retail brokerage features** — no order placement UI, no portfolio tracking for non-professionals.
- **High-frequency trading** — Athena targets strategies with holding periods in minutes to days, not microseconds. No FPGA, no kernel bypass networking.
- **Social/copy trading** — no strategy sharing, no follower mechanics.
- **Multi-tenant SaaS** — single-tenant, single-fund deployment model.
- **Cryptocurrency** — Indian equity and derivative markets only (NSE/BSE/MCX).
- **Equities outside India** — initial scope is F&O on indices and stocks listed on NSE/BSE.

---

## Performance Targets

| Metric | Target | Rationale |
|---|---|---|
| Market data latency (WS feed → in-memory tick) | < 10ms p99 | NSE tick-to-signal SLA |
| Order submission latency (signal → API dispatched) | < 100ms p99 | Within reasonable human reaction time |
| Historical data query (30-day OHLCV window) | < 500ms | Interactive research workflows |
| Platform cold start | < 60s | Acceptable for non-HFT re-deployment |
| Unit test suite | < 30s | Fast feedback loops during development |
| NSE trading hours availability | 99.9% | ~8.7 hours downtime per year |
| Audit log retention | 7 years | SEBI requires 5 years minimum |

---

## Broker Expansion Roadmap

The `BrokerPort` in `athena.core.ports.broker` is already defined. Adding a new broker requires only implementing the port — zero domain changes:

1. **Zerodha (Kite Connect)** — secondary broker for redundancy
2. **IBKR (Interactive Brokers)** — international exchange access
3. **BSE StAR MF** — mutual fund platform integration
