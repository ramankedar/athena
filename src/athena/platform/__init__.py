"""Athena Platform Foundation — Sprint 1.

Provides cross-cutting platform concerns consumed by all five engines:

- ``config``      — Typed configuration via pydantic-settings
- ``exceptions``  — Rich exception hierarchy with structured context
- ``logging``     — Structured logging via structlog with correlation IDs
- ``types``       — Shared enumerations and type aliases
- ``bootstrap``   — Application lifecycle and context management

Typical usage at process startup::

    from athena.platform.bootstrap import bootstrap_application
    from athena.platform.logging import get_logger

    ctx = bootstrap_application()
    log = get_logger(__name__)
    log.info("platform.ready", version=ctx.settings.app.version)
"""

from athena.platform.bootstrap.bootstrapper import bootstrap_application
from athena.platform.bootstrap.context import ApplicationContext
from athena.platform.config.settings import AppConfig, AthenaSettings, LoggingConfig
from athena.platform.exceptions.errors import (
    AthenaError,
    ConfigurationError,
    DataIntegrityError,
    ExternalServiceError,
    InfrastructureError,
    NotImplementedFeatureError,
    ValidationError,
)
from athena.platform.logging.context import (
    bind_context,
    get_correlation_id,
    get_request_id,
    new_correlation_id,
)
from athena.platform.logging.setup import configure_logging, get_logger
from athena.platform.types.enums import (
    ApplicationMode,
    Environment,
    LogFormat,
    LogLevel,
    MarketType,
)

__all__ = [
    "AppConfig",
    "ApplicationContext",
    "ApplicationMode",
    "AthenaError",
    "AthenaSettings",
    "ConfigurationError",
    "DataIntegrityError",
    "Environment",
    "ExternalServiceError",
    "InfrastructureError",
    "LogFormat",
    "LogLevel",
    "LoggingConfig",
    "MarketType",
    "NotImplementedFeatureError",
    "ValidationError",
    "bind_context",
    "bootstrap_application",
    "configure_logging",
    "get_correlation_id",
    "get_logger",
    "get_request_id",
    "new_correlation_id",
]
