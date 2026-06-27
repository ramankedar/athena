"""Shared fixtures for platform unit tests.

Provides pre-built settings instances for each environment so test
modules do not repeat construction boilerplate. Also provides a cleanup
fixture that resets structlog and the logging ContextVars after each
test, preventing state leakage between test cases.
"""

from __future__ import annotations

import pytest
import structlog

from athena.platform.config.settings import AppConfig, AthenaSettings, LoggingConfig
from athena.platform.logging.context import (
    _CORRELATION_ID,
    _REQUEST_ID,
)
from athena.platform.types.enums import (
    ApplicationMode,
    Environment,
    LogFormat,
    LogLevel,
)


@pytest.fixture
def dev_settings() -> AthenaSettings:
    """Development environment settings with DEBUG logging.

    Returns:
        ``AthenaSettings`` configured for ``DEVELOPMENT``.
    """
    return AthenaSettings(
        environment=Environment.DEVELOPMENT,
        logging=LoggingConfig(level=LogLevel.DEBUG, format=LogFormat.CONSOLE),
    )


@pytest.fixture
def test_settings() -> AthenaSettings:
    """Testing environment settings.

    Returns:
        ``AthenaSettings`` configured for ``TESTING``.
    """
    return AthenaSettings(
        environment=Environment.TESTING,
        logging=LoggingConfig(level=LogLevel.DEBUG, format=LogFormat.CONSOLE),
    )


@pytest.fixture
def prod_settings() -> AthenaSettings:
    """Production-valid settings with mandatory JSON logging.

    Returns:
        ``AthenaSettings`` configured for ``PRODUCTION`` that passes all
        production constraints.
    """
    return AthenaSettings(
        environment=Environment.PRODUCTION,
        app=AppConfig(debug=False, mode=ApplicationMode.PAPER),
        logging=LoggingConfig(level=LogLevel.INFO, format=LogFormat.JSON),
    )


@pytest.fixture(autouse=True)
def reset_logging_state() -> None:
    """Reset structlog and ContextVar state after every platform test.

    Prevents test ordering from affecting results. Structlog is reset to
    its defaults so that tests that call ``configure_logging`` do not
    affect subsequent tests.
    """
    yield
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()
    _CORRELATION_ID.set(None)
    _REQUEST_ID.set(None)
