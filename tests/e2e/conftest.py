"""End-to-end test fixtures.

E2E tests run against the full Athena stack. They are gated in CI behind
a nightly schedule and are never run on PR.

These tests require:
    - All services running (make docker-up)
    - A Fyers paper/sandbox account configured in .env
    - ATHENA_ENVIRONMENT=development
"""

from __future__ import annotations
