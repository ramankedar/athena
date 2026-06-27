#!/usr/bin/env bash
# ── Athena Platform — Developer Setup Script ──────────────────────────────────
#
# Verifies all prerequisites and sets up the local development environment.
# Idempotent: safe to run multiple times.
#
# Usage: ./scripts/setup.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Colour

ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
fail() { echo -e "${RED}✗${NC} $*"; exit 1; }

echo ""
echo "Athena Platform — Developer Setup"
echo "==================================="
echo ""

# ── Check prerequisites ───────────────────────────────────────────────────────

echo "Checking prerequisites..."

# Python
if command -v python3 &>/dev/null; then
  PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
  PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
  PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
  if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
    ok "Python $PYTHON_VERSION"
  else
    fail "Python 3.12+ required (found $PYTHON_VERSION). Install from https://python.org"
  fi
else
  fail "Python 3 not found. Install from https://python.org"
fi

# uv
if command -v uv &>/dev/null; then
  ok "uv $(uv --version 2>&1 | awk '{print $2}')"
else
  warn "uv not found. Installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$PATH"
  ok "uv installed"
fi

# Docker
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
else
  warn "Docker not available. Integration tests and local services will not work."
  warn "Install Docker from https://docker.com/get-started"
fi

# Git
if command -v git &>/dev/null; then
  ok "git $(git --version | awk '{print $3}')"
else
  fail "git not found. Install git before continuing."
fi

echo ""

# ── Set up environment file ───────────────────────────────────────────────────

if [ ! -f .env ]; then
  cp .env.example .env
  ok "Created .env from .env.example — add your credentials"
else
  ok ".env already exists"
fi

# ── Install Python dependencies ───────────────────────────────────────────────

echo "Installing dependencies..."
uv sync --all-groups
ok "Dependencies installed"

# ── Install pre-commit hooks ──────────────────────────────────────────────────

echo "Installing pre-commit hooks..."
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
ok "Pre-commit hooks installed"

# ── Secrets baseline ──────────────────────────────────────────────────────────

if [ ! -f .secrets.baseline ]; then
  uv run detect-secrets scan \
    --exclude-files '\.env\.example' \
    --exclude-files 'tests/' > .secrets.baseline
  ok "Created .secrets.baseline"
else
  ok ".secrets.baseline already exists"
fi

echo ""
echo "==================================="
ok "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Fyers API credentials"
echo "  2. Start local services: make docker-up"
echo "  3. Verify setup:         make check"
echo ""
