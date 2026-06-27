# ── Athena Platform — Makefile ────────────────────────────────────────────────
# Usage: make <target>
# Run `make help` for a full list of targets.

.DEFAULT_GOAL := help
.PHONY: help install install-hooks dev test test-unit test-integration test-e2e \
        test-cov lint format format-check type-check import-check check \
        clean docker-up docker-down docker-build docs docs-build secrets-baseline

# ── Colours ───────────────────────────────────────────────────────────────────
CYAN  := \033[36m
RESET := \033[0m

# ── Help ──────────────────────────────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "$(CYAN)%-22s$(RESET) %s\n", $$1, $$2}'

# ── Installation ──────────────────────────────────────────────────────────────
install: ## Install all dependency groups (dev + test + lint + docs)
	uv sync --all-groups

install-hooks: install ## Install and activate pre-commit hooks
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg
	@echo "✓ Pre-commit hooks installed"

dev: docker-up install install-hooks ## Full local dev environment setup (services + deps + hooks)
	@echo "✓ Development environment ready. Run 'make test' to verify."

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run all tests
	uv run pytest

test-unit: ## Run unit tests only (fast, no I/O, safe to run anywhere)
	uv run pytest tests/unit/ -m unit -v

test-integration: ## Run integration tests (requires running services: make docker-up)
	uv run pytest tests/integration/ -m integration -v

test-e2e: ## Run end-to-end tests (requires full stack)
	uv run pytest tests/e2e/ -m e2e -v

test-cov: ## Run unit tests with HTML coverage report
	uv run pytest tests/unit/ \
		--cov=athena \
		--cov-report=html:htmlcov \
		--cov-report=term-missing \
		--cov-fail-under=80
	@echo "✓ Coverage report: htmlcov/index.html"

test-parallel: ## Run unit tests in parallel (faster on multi-core machines)
	uv run pytest tests/unit/ -n auto

# ── Code quality ──────────────────────────────────────────────────────────────
lint: ## Run ruff linter (errors only, no auto-fix)
	uv run ruff check src/ tests/

lint-fix: ## Run ruff linter and auto-fix safe violations
	uv run ruff check --fix src/ tests/

format: ## Format code with ruff
	uv run ruff format src/ tests/ scripts/

format-check: ## Check formatting without modifying files (CI mode)
	uv run ruff format --check src/ tests/ scripts/

type-check: ## Run mypy static type checker (strict mode)
	uv run mypy src/

import-check: ## Verify engine import boundary contracts (import-linter)
	uv run lint-imports

security-audit: ## Audit dependencies for known CVEs
	uv run pip-audit

# ── Composite check (mirrors CI) ──────────────────────────────────────────────
check: lint format-check type-check import-check test-unit ## Run all checks (CI equivalent — run before pushing)
	@echo "✓ All checks passed"

# ── Cleaning ──────────────────────────────────────────────────────────────────
clean: ## Remove all build artefacts, caches, and temporary files
	rm -rf dist/ htmlcov/ .coverage .coverage.* coverage.xml
	rm -rf .mypy_cache .ruff_cache .pytest_cache .hypothesis
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	find . -type f -name "*.pyc" -not -path "./.venv/*" -delete
	@echo "✓ Clean"

# ── Docker services ───────────────────────────────────────────────────────────
docker-up: ## Start local services (TimescaleDB, Redis) in background
	docker compose up -d timescaledb redis
	@echo "Waiting for services to be healthy..."
	@docker compose exec timescaledb sh -c 'until pg_isready -U athena -d athena_dev; do sleep 1; done' 2>/dev/null || true
	@echo "✓ Services ready"

docker-down: ## Stop and remove local service containers
	docker compose down

docker-down-volumes: ## Stop containers and delete all volumes (destroys local data)
	docker compose down -v
	@echo "⚠ All local data volumes removed"

docker-build: ## Build the Athena application Docker image
	docker build -t athena:local .
	@echo "✓ Image built: athena:local"

docker-logs: ## Tail logs from all running compose services
	docker compose logs -f

# ── Documentation ─────────────────────────────────────────────────────────────
docs: ## Serve documentation locally with live reload
	uv run mkdocs serve

docs-build: ## Build static documentation site
	uv run mkdocs build --strict

# ── Security baseline ─────────────────────────────────────────────────────────
secrets-baseline: ## Initialise detect-secrets baseline (run once after setup)
	uv run detect-secrets scan --exclude-files '\.env\.example' > .secrets.baseline
	@echo "✓ .secrets.baseline created. Commit it."
