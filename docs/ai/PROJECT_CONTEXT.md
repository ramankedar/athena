# Athena — Project Context

## What is Athena?

Athena is a **production-grade, AI-powered quantitative research and automated trading platform** built for Indian derivative markets. It is being developed as if by the founding engineering team of a quantitative hedge fund — with the rigour, architecture, and tooling of an enterprise financial system.

**Target markets:** NIFTY 50, BANKNIFTY, SENSEX, BANKEX — NSE and BSE derivatives, MCX commodities.  
**Primary broker:** Fyers API (WebSocket feeds + REST order management).

## Repository

- **GitHub:** https://github.com/ramankedar/athena  
- **Branch:** `feat/bootstrap` (all work so far; no merge to main yet)  
- **Local path:** `/Users/ramankedar/Desktop/athena`

## Technology Stack

| Concern | Choice |
|---|---|
| Language | Python 3.12+ |
| Package manager | `uv` (Rust-based, PEP 721 compliant) |
| Build backend | `hatchling` |
| Formatting | `ruff format` |
| Linting | `ruff check` (replaces flake8, isort, pyupgrade) |
| Type checking | `mypy` (strict mode, no `Any`) |
| Testing | `pytest` + `hypothesis` + `pytest-asyncio` |
| Structured logging | `structlog` |
| Configuration | `pydantic-settings` |
| CI/CD | GitHub Actions |
| Containerisation | Docker (multi-stage, non-root) |
| Local services | Docker Compose (TimescaleDB + Redis) |

## Runtime Dependencies

```
pydantic>=2.7
pydantic-settings>=2.3
structlog>=24.2
httpx>=0.27
anyio>=4.4
typer>=0.12
tzdata>=2024
```

## Key Invariants (never violate these)

1. **No trading logic, ML models, or broker integrations** until explicitly sprint-planned.
2. **No `Any` type** anywhere in source code. Use `object` for truly polymorphic values.
3. **No `print()` statements.** All output goes through `structlog`.
4. **No `datetime.now()` calls** outside `SystemClock.now()` in `athena.time.clock`.
5. **All datetimes are UTC-aware.** Naive datetimes raise `NaiveDatetimeError` at domain boundaries.
6. **All domain models are frozen dataclasses.** No mutable shared state.
7. **Imports never cross peer-layer boundaries** (enforced by `import-linter` in CI).

## What Has Been Built

Eight sprints completed. **1,747 tests, 95% overall coverage, ruff clean.**

| Sprint | Domain | Package |
|---|---|---|
| 1 | Platform Foundation | `athena.platform` |
| 2 | Time Domain | `athena.time` |
| 3 | Storage Foundation | `athena.storage` |
| 4 | Asset Domain | `athena.assets` |
| 5 | Market Domain | `athena.market` |
| 6 | Market Data Domain | `athena.market_data` |
| 7 | Feature Domain | `athena.features` |
| 8 | Experiment Domain | `athena.experiments` |

## What Has NOT Been Built Yet

- Broker integrations (Fyers WebSocket, REST clients)
- Database implementations (TimescaleDB adapters)
- Redis cache implementations
- Engine layer (Data, Research, Intelligence, Trading, Governance)
- Live trading execution
- ML/AI models
- REST/WebSocket API
- Web dashboard
- Backtesting engine

## Developer Setup

```bash
git clone https://github.com/ramankedar/athena.git && cd athena
make dev          # install deps, hooks, start Docker services
cp .env.example .env
make check        # full CI gate: lint + format + type-check + unit tests
```

## Useful Commands

```bash
make test-unit        # fast unit tests only (< 5s)
make test-cov         # unit tests with HTML coverage report
make lint             # ruff check
make format           # ruff format
make type-check       # mypy strict
make import-check     # verify import-linter contracts
make docker-up        # start TimescaleDB + Redis
make check            # everything CI runs
```
