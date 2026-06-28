# Athena Architecture Constitution

This document defines the non-negotiable architectural rules of the Athena platform. Every design decision must be traceable to at least one of these principles. Violations require an Architecture Decision Record (ADR) in `docs/adr/`.

---

## 1. Five-Engine Model

Athena's business logic is organised into five independent engines. Each engine owns a distinct slice of responsibility. No engine reaches into another engine's internals.

| Engine | Responsibility |
|---|---|
| **Data** | Market data ingestion, normalisation, tick storage, OHLCV storage, instrument master |
| **Research** | Event-driven backtesting, signal development, performance analytics |
| **Intelligence** | ML pipeline — feature store, model training, serving (planned, not built) |
| **Trading** | Order lifecycle (OMS/EMS), pre-trade risk, position ledger, reconciliation |
| **Governance** | Immutable audit trail, SEBI compliance, regulatory reporting |

Engines live in `src/athena/engines/{name}/` and internally follow hexagonal architecture (core → application → infrastructure).

---

## 2. Hexagonal Architecture Within Each Engine

Every engine has three internal layers with a strict one-way dependency rule:

```
infrastructure/ → application/ → core/
```

- **`core/`** — Pure domain models, domain events, port Protocols. Zero external dependencies.
- **`application/`** — Use cases that orchestrate core logic. Imports core only.
- **`infrastructure/`** — Concrete adapters (DB, APIs, message bus). Imports core + application + third-party libs.

---

## 3. Import Hierarchy (the absolute law)

```
athena.interfaces
    ↑
athena.engines
    ↑
athena.platform  athena.time  athena.storage  athena.assets
athena.market    athena.market_data  athena.features  athena.experiments
    ↑
athena.core
```

**Rules enforced by `import-linter` in CI (19 contracts):**
- Arrows point upward only. Lower layers never import from higher layers.
- Peer layers (`athena.time`, `athena.market`, `athena.assets`, etc.) never import from each other.
- `athena.core` imports from nothing inside `athena.*`.
- `athena.platform` imports from `athena.core` only (for exceptions base).
- All peer domains (`athena.market_data`, `athena.features`, `athena.experiments`) import from `athena.platform` only.

**Cross-peer integration pattern:** Define a `Protocol` (port) in the domain that needs the capability. The engine layer wires the concrete implementation. Example: `athena.market.interfaces.MarketCalendarPort` is satisfied by `athena.time` implementations — neither domain imports the other.

---

## 4. Immutability by Default

Every domain model is a `@dataclass(frozen=True)`. This means:
- Constructed once, never mutated.
- Thread-safe and async-safe without locks.
- Hashable → usable as dict keys and set members.
- State changes produce new instances (`dataclasses.replace()`), not mutations.

**Exception:** Registry classes (e.g., `InMemoryInstrumentRegistry`, `InMemoryExperimentRegistry`) are mutable because they ARE the state store. Their stored value objects are still frozen.

---

## 5. No `Any` — Ever

`from typing import Any` is forbidden in source code. Use:
- `object` for truly polymorphic values (e.g., exception context kwargs).
- `# type: ignore[arg-type]` with a comment when third-party stubs force it (structlog, etc.).
- Generic TypeVar with bounds when the type is constrained.

Mypy runs in `--strict` mode. Every public function signature is fully typed.

---

## 6. Typed Identifiers, Not Raw Strings

Domain identifiers are typed value objects, never bare strings:
- `athena.assets`: `InstrumentId`, `ExchangeId`, `Symbol`, `ISIN`, `CurrencyCode`
- `athena.market`: `MarketId`
- `athena.features`: `FeatureId`
- `athena.experiments`: `ExperimentId`, `RunId`, `RunGroupId`
- `athena.storage`: `StorageKey` (type alias for `str`, but conceptually typed)

---

## 7. Clock Abstraction

`datetime.now()` is called in exactly one place in the entire codebase: `athena.time.clock.SystemClock.now()`. All other time-dependent code receives a `ClockProtocol` via dependency injection.

Test doubles: `FrozenClock` (fixed instant), `ManualClock` (manually advanceable).

---

## 8. Fail Fast, Fail Loud

- Configuration validation fails at startup, not during trading hours.
- Invalid domain objects raise typed exceptions in `__post_init__`, not silently.
- `NaiveDatetimeError` is raised immediately at any domain boundary that receives a naive datetime.
- Pre-trade risk checks are synchronous and blocking. An order is never submitted when risk state is uncertain.

---

## 9. Every External Call is Audited

Any call that leaves the process boundary — broker API, database, external data provider — is wrapped in infrastructure adapters that log the request, response, latency, and outcome. Silent failures are impossible by design.

---

## 10. Protocol-Based Ports (Structural Typing)

Service interfaces use `typing.Protocol` with `@runtime_checkable`. This enables:
- Structural subtyping — no forced inheritance.
- `isinstance()` checks at runtime for guard clauses.
- Third-party types satisfying Athena ports without modification.

Every peer domain defines its own integration ports. Engines are the only layer that wires ports to concrete implementations.

---

## 11. Reproducibility as a First-Class Concern

The `athena.experiments.ReproducibilitySnapshot` captures:
- Git commit hash + dirty flag
- Random seed
- Python version
- Environment hash (installed packages)
- Dataset versions used
- Feature set versions used

A `snapshot_hash` (SHA-256) allows comparing two runs: equal hashes = bitwise-identical configuration.

---

## 12. Audit Trail Cannot Be Bypassed

The Governance Engine's audit log:
- Is append-only at the database level (PostgreSQL row-level security: no UPDATE/DELETE).
- Uses a SHA-256 hash chain: each entry contains the hash of the previous entry.
- Retroactive modification is detectable.
- Retained for 7 years (SEBI minimum is 5).

---

## ADR Template

Any deviation from this constitution requires an ADR in `docs/adr/`:

```markdown
# ADR-XXXX: <Title>

**Status:** Proposed / Accepted / Superseded
**Date:** YYYY-MM-DD
**Context:** Why is this decision needed?
**Decision:** What was decided?
**Consequences:** What are the trade-offs?
```
