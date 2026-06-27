# Contributing to Athena

Thank you for contributing to the Athena platform. This document covers everything you need to know to get your development environment set up and your changes merged efficiently.

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://www.python.org/downloads/) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | 24+ | Required for integration tests |
| Git | 2.40+ | System package manager |

## Setup

```bash
git clone https://github.com/ramankedar/athena.git
cd athena
make dev          # installs deps, hooks, and starts local services
cp .env.example .env
```

## Before Your First Commit

Run the full pre-push check suite — the same suite CI runs:

```bash
make check
```

This runs: `ruff check` → `ruff format --check` → `mypy` → `lint-imports` → `pytest tests/unit/`

If any step fails, fix it before pushing. CI will catch the same failures and block your PR.

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/). The `commitizen` pre-commit hook enforces this at commit time.

```
<type>(<scope>): <short description>

Types:  feat | fix | docs | refactor | test | chore | perf | ci
Scope:  core | data | research | trading | governance | shared | cli | infra

Examples:
  feat(data): add options chain snapshot use case
  fix(trading): correct idempotency key TTL on order retry
  docs(adr): add ADR-0005 for Redis cache strategy
  test(core): add hypothesis tests for Price arithmetic
```

Breaking changes append `!` after the type: `feat(trading)!: redesign order port interface`

## Architecture Rules

These are non-negotiable and CI-enforced via import-linter:

1. `athena.core` must have **zero imports** from any other `athena.*` subpackage
2. Engine peers must **never import each other directly** — use domain events or core ports
3. `athena.shared` must not import from engines or interfaces
4. Infrastructure adapters live in `athena.engines.{name}.infrastructure` — never in core or application layers

When in doubt, read `ARCHITECTURE.md` or open an issue to discuss the design.

## Adding a New Feature

1. Open an issue describing the feature and which engine it belongs to
2. Create a branch: `feat/<engine>-<short-description>` (e.g. `feat/data-options-chain`)
3. Implement in the correct engine layer (core → application → infrastructure)
4. Write unit tests first (or alongside) — 80% line coverage minimum on new code
5. Run `make check`
6. Open a PR against `main` using the PR template

## Adding a New Engine Adapter

1. Define a `Protocol` port in `athena.core.ports` if one doesn't exist
2. Write the adapter in `athena.engines.{name}.infrastructure`
3. Wire it in the engine's `__init__.py` or dependency injection module
4. Add a corresponding integration test in `tests/integration/`

## Architecture Decision Records

Any significant design decision — a new dependency, a pattern change, an infrastructure choice — needs an ADR in `docs/adr/`. Follow the numbered format of existing ADRs.

## Testing Tiers

| Tier | Location | When to run | Requires services |
|------|----------|-------------|-------------------|
| Unit | `tests/unit/` | Always, before every commit | No |
| Integration | `tests/integration/` | Before pushing; always in CI | TimescaleDB + Redis |
| E2E | `tests/e2e/` | CI nightly; pre-release manually | Full stack |

## Code Style

- **Ruff** handles formatting and linting — run `make format` then `make lint`
- **mypy strict** — all public APIs must be fully typed
- **No comments** explaining *what* the code does — names should do that
- **One short comment** only when the *why* is non-obvious (a subtle invariant, a regulatory constraint, a workaround for a known bug)
- **No placeholder implementations** — if a function is not implemented yet, raise `NotImplementedError`

## Questions

Open a [GitHub Discussion](https://github.com/ramankedar/athena/discussions) for questions that don't belong in an issue.
