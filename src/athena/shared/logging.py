"""Structured logging configuration for the Athena platform.

Call `configure_logging(settings)` once at process startup — before any
engine initialises. All subsequent `structlog.get_logger()` calls return
a pre-configured, context-bound logger.

Two rendering modes:
    development  → ColourfulConsoleRenderer with key=value formatting for readability
    production   → JSONRenderer for machine-parseable output collected by log infra

Standard fields on every log entry (enforced by the shared processor chain):
    timestamp    — ISO-8601 UTC string with microsecond precision
    level        — debug | info | warning | error | critical
    logger       — dotted module path of the calling logger
    event        — human-readable description of what happened
    + any context variables bound with structlog.contextvars.bind_contextvars()
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from athena.shared.config import AthenaSettings


def configure_logging(settings: AthenaSettings) -> None:
    """Configure structlog and route stdlib logging through it.

    Must be called exactly once, at process startup, before any engine
    or adapter is initialised.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Processors applied to every log entry regardless of renderer.
    shared_processors: list[structlog.types.Processor] = [
        # Merge context variables set with bind_contextvars() into the event dict.
        structlog.contextvars.merge_contextvars,
        # Add the calling module's dotted path as "logger".
        structlog.stdlib.add_logger_name,
        # Add the log level string as "level".
        structlog.stdlib.add_log_level,
        # Expand positional log arguments: log.info("x=%s", value) → "x=42".
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Attach UTC ISO-8601 timestamp.
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Render tracebacks as structured dicts (not multi-line strings).
        structlog.processors.ExceptionRenderer(),
        # Attach stack info when log(..., stack_info=True) is called.
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.environment == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=True,
            exception_formatter=structlog.dev.plain_traceback,
        )
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (from third-party libraries) through structlog
    # so all log output shares the same structured format.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    # Silence noisy third-party loggers that pollute market-hours output.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named logger bound to the platform's configured processors.

    Usage:
        log = get_logger(__name__)
        log.info("tick_received", symbol="NSE:NIFTY50-INDEX", price=24500.50)
    """
    return structlog.get_logger(name)
