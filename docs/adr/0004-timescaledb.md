# ADR-0004: Use TimescaleDB for Time-Series Storage

**Status:** Accepted  
**Date:** 2026-06-27  
**Deciders:** Platform Engineering

---

## Context

Athena must store and query:
- Tick data: ~10,000–50,000 ticks/day per instrument at launch; scales to millions if instrument count grows
- OHLCV bars: ~375 one-minute bars/instrument/day for NSE market hours
- Options chain snapshots: periodic JSON blobs
- Audit log: append-only event records with hash chaining

Requirements:
- Time-range queries on (symbol, interval, from_utc, to_utc) must complete in < 500ms for 30-day windows
- Insert throughput must handle peak tick rate without back-pressure on the WebSocket consumer
- Must support continuous aggregates (auto-refresh 1-min bars → 5-min → hourly)
- Must allow append-only tables for the audit log (row-level security: no UPDATE/DELETE)
- SQL interface preferred (research notebooks use pandas + SQL natively)

Candidates: TimescaleDB, InfluxDB 3.0, QuestDB, ClickHouse, plain PostgreSQL.

## Decision

Use **TimescaleDB** (PostgreSQL extension) as the primary data store.

| Criterion | TimescaleDB | InfluxDB 3.0 | QuestDB | Plain PostgreSQL |
|-----------|-------------|-------------|---------|-----------------|
| SQL compatibility | Full PostgreSQL | Partial (Flight SQL) | PostgreSQL-like | Full |
| Time-series performance | Hypertables: 10–100x vs plain PG | Excellent | Excellent | Poor at scale |
| Continuous aggregates | Native, auto-refresh | No | No | Manual materialised views |
| Compression | Native columnar | Yes | Yes | No |
| Row-level security | Full PostgreSQL RLS | No | No | Full |
| Joins with reference data | SQL JOIN | Complex | Limited | SQL JOIN |
| Operational complexity | Single PostgreSQL process | Separate daemon | Separate daemon | Single process |

## Consequences

**Positive:**
- Single database process serves all storage needs (ticks, OHLCV, instruments, audit)
- Full PostgreSQL tooling: psql, pgAdmin, Alembic migrations, asyncpg driver, pandas `read_sql`
- Row-level security enables the append-only audit log at the database level — tampering requires superuser access and is logged
- Continuous aggregates automatically maintain 5-min and hourly bars from 1-min bars
- `timescale/timescaledb:latest-pg16` Docker image is available for local development

**Negative / Risks:**
- TimescaleDB is an extension — upgrading PostgreSQL requires care to keep extension compatibility
- At very high instrument counts (thousands), QuestDB or ClickHouse may offer better write throughput

**Mitigation:**
- `HistoricalStorePort` protocol abstracts the storage layer — migrating to QuestDB requires only reimplementing the adapter
- Alembic handles schema migrations with rollback scripts alongside every forward migration
- TimescaleDB compression is enabled by default for partitions older than 7 days, limiting storage growth
