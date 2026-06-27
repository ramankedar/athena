# Changelog

All notable changes to the Athena platform are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Version bumps and this file are managed automatically by
[commitizen](https://commitizen-tools.github.io/commitizen/) on release.

<!-- commitizen: next version goes here -->

## [Unreleased]

### Added
- Complete repository scaffold with five-engine hexagonal architecture
- `athena.core` shared kernel: `Instrument`, `Tick`, `OHLCV`, `OptionChain` domain models
- Typed port interfaces (`Protocol`) for broker, market data feed, historical store, instrument repository
- `DomainEvent` base class with UUID identity and UTC timestamp
- `AthenaSettings` configuration via pydantic-settings with nested environment variable support
- `structlog` logging setup with environment-driven JSON/console renderer
- Structured exception hierarchy (`AthenaError`, `RiskError`, `BrokerError`, etc.)
- `pyproject.toml` with uv dependency groups (dev / test / lint / docs)
- Ruff linting and formatting (replaces flake8, isort, black)
- mypy strict mode configuration
- import-linter contracts enforcing engine boundary rules
- pytest configuration with asyncio auto-mode, hypothesis, and three-tier markers
- Pre-commit hooks: ruff, mypy, detect-secrets, commitizen, file hygiene
- GitHub Actions CI: quality, unit tests (3.12 + 3.13), integration tests, security audit
- GitHub Actions Release: changelog extraction + GitHub Release creation
- GitHub Actions CodeQL: weekly security analysis
- Multi-stage Dockerfile with non-root runtime user
- Docker Compose for local TimescaleDB and Redis services
- Makefile with 20+ targets covering dev, test, lint, docker, and docs
- Four Architecture Decision Records (ADR-0001 through ADR-0004)
- MkDocs + Material documentation site configuration
- `ARCHITECTURE.md` — comprehensive platform design document
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- Dependabot configuration for weekly dependency updates

[Unreleased]: https://github.com/ramankedar/athena/compare/HEAD...HEAD
