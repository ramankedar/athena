# Athena

> AI-powered quantitative research and automated trading platform for Indian derivative markets (NIFTY, BANKNIFTY, SENSEX, BANKEX).

[![CI](https://github.com/ramankedar/athena/actions/workflows/ci.yml/badge.svg)](https://github.com/ramankedar/athena/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/ramankedar/athena/branch/main/graph/badge.svg)](https://codecov.io/gh/ramankedar/athena)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Overview

Athena is a production-grade platform organised around **five independent engines**:

| Engine | Responsibility |
|--------|---------------|
| **Data** | Real-time tick ingestion, OHLCV storage, options chain management via Fyers API |
| **Research** | Event-driven backtesting, signal development, performance analytics |
| **Intelligence** | ML model training and serving *(planned — not implemented in v1)* |
| **Trading** | Order lifecycle management, pre-trade risk checks, position reconciliation |
| **Governance** | Immutable audit trail, SEBI compliance, regulatory reporting |

Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the complete system design.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | 24+ | [docker.com](https://www.docker.com/get-started) |
| Git | 2.40+ | System package manager |

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/ramankedar/athena.git
cd athena

# 2. Set up the full local environment (installs deps, hooks, starts services)
make dev

# 3. Configure your environment
cp .env.example .env
# Edit .env with your credentials

# 4. Verify everything works
make check
```

## Development Workflow

```bash
make help           # Show all available targets

make test-unit      # Run fast unit tests (no services required)
make test-cov       # Unit tests with HTML coverage report
make lint           # Ruff linter
make format         # Auto-format code
make type-check     # mypy strict mode
make import-check   # Verify engine boundary contracts
make check          # Run everything CI runs (pre-push gate)

make docker-up      # Start TimescaleDB + Redis
make docker-down    # Stop services
make docs           # Serve documentation at localhost:8000
```

## Project Structure

```
athena/
├── src/athena/
│   ├── core/           # Shared kernel — zero external dependencies
│   │   ├── domain/     # Instruments, ticks, OHLCV (frozen dataclasses)
│   │   ├── ports/      # Typed interfaces (Protocols) for adapters
│   │   └── events/     # Domain event base types
│   ├── engines/
│   │   ├── data/       # Ingestion, normalisation, storage
│   │   ├── research/   # Backtesting, signals, analytics
│   │   ├── intelligence/ # ML pipeline (planned)
│   │   ├── trading/    # OMS, EMS, risk, positions
│   │   └── governance/ # Audit trail, compliance, reporting
│   ├── shared/         # Logging, config, exceptions (cross-cutting)
│   └── interfaces/     # CLI delivery layer
├── tests/
│   ├── unit/           # Fast, no I/O — must pass in < 30s
│   ├── integration/    # Requires TimescaleDB + Redis
│   └── e2e/            # Full stack
├── configs/            # Environment-specific TOML (no secrets)
├── docs/adr/           # Architecture Decision Records
└── infrastructure/     # Docker, Compose, future IaC
```

## Architecture

The platform uses **hexagonal architecture** (Ports & Adapters). The dependency rule is strict and CI-enforced:

```
athena.interfaces → athena.engines → athena.shared → athena.core
                                                              ↑
                                                    zero external imports
```

Engine peers never import each other directly. All cross-engine communication flows through domain events and typed `Protocol` ports defined in `athena.core`.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full design, all five engines in depth, failure isolation, scalability strategy, and future evolution plan.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Security

See [`SECURITY.md`](SECURITY.md) for how to report vulnerabilities.

## License

[MIT](LICENSE)
