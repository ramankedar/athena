# ADR-0003: Adopt Hexagonal Architecture (Ports and Adapters)

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Platform Engineering

---

## Context

A quantitative trading platform faces several structural pressures that naive layering handles poorly:

1. **Multiple brokers over time.** Starting with Fyers, expanding to Zerodha or IBKR later. If broker-specific code is interleaved with business logic, every broker change requires auditing the entire codebase.

2. **Live and backtest must be identical.** The most dangerous class of quant bugs is live/backtest divergence — where a strategy that backtests profitably behaves differently live because it depends on different code paths. If production execution and backtesting share the same signal handlers running over the same event types, this class of bug is eliminated structurally.

3. **Testing without a live broker.** Order management logic must be unit-testable without network access or a brokerage account. If the business logic is directly coupled to the Fyers SDK, it cannot be tested in isolation.

4. **Replacing infrastructure.** TimescaleDB may be replaced by QuestDB or ClickHouse as data volumes grow. If query logic is embedded in application services, this replacement requires changes throughout the codebase.

## Decision

Adopt **Hexagonal Architecture** (Ports and Adapters, also called Clean Architecture) across all five engines.

**The dependency rule:** all dependencies point inward. Infrastructure depends on domain; domain never depends on infrastructure.

```
athena.interfaces → athena.engines → athena.shared → athena.core
                         ↑
               (adapters implement ports defined in core)
```

**Ports** are `typing.Protocol` interfaces in `athena.core.ports`. They define *what* is needed without specifying *how*.  
**Adapters** are concrete implementations in each engine's `infrastructure/` layer.

## Consequences

**Positive:**
- The domain core has zero external dependencies — it is testable with `pytest` in milliseconds
- Swapping Fyers for Zerodha requires only implementing `BrokerPort` and `MarketDataFeedPort` — no domain changes
- The backtesting framework is wire-compatible with live trading by design
- `import-linter` contracts enforce the dependency rule in CI — violations are caught before merge

**Negative / Risks:**
- More files and indirection than a simple layered architecture
- Engineers unfamiliar with hexagonal architecture face a learning curve

**Mitigation:**
- This ADR and `ARCHITECTURE.md` document the pattern thoroughly
- The five-engine namespace (`athena.engines.{name}`) groups related files and makes the structure navigable
- The `make import-check` target provides immediate feedback when a boundary is crossed
