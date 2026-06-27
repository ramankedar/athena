"""Integration test fixtures.

Integration tests require live services. Start them with:
    make docker-up

Environment variables are set via .env or CI service containers.
See .github/workflows/ci.yml for the CI service configuration.
"""

from __future__ import annotations

import pytest

from athena.shared.config import AthenaSettings


@pytest.fixture(scope="session")
def settings() -> AthenaSettings:
    """Platform settings loaded from the test environment."""
    return AthenaSettings()


# Database and Redis fixtures will be added when the infrastructure
# adapters are implemented. They will use the settings fixture above
# to construct real connections.
