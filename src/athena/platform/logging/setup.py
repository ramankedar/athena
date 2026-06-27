"""Structlog configuration for the Athena platform.

Call ``configure_logging(settings)`` once at process startup — before any
engine is initialised. The function is safe to call multiple times (e.g.
in tests) because ``cache_logger_on_first_use=False`` is set, which means
the processor chain is re-evaluated on each log call rather than being
frozen after the first. The stdlib bridge is reconfigured with
``logging.basicConfig(force=True)`` for the same reason.

Two rendering pipelines are supported:

CONSOLE (development / testing):
    Colourised ``key=value`` output for interactive terminals. Colour is
    enabled only when stdout is a TTY (suppressed when piped or redirected).
    Tracebacks are rendered inline as plain text.

JSON (staging / production):
    One compact JSON object per log call. Fields: ``timestamp``, ``level``,
    ``logger``, ``event``, plus any bound context variables. Designed for
    log aggregation systems (Datadog, Loki, CloudWatch, Grafana Cloud).

Third-party library logging is routed through the structlog stdlib bridge
so that all output shares a consistent structured format. Known noisy
loggers (``httpx``, ``httpcore``, ``asyncio``) are raised to ``WARNING``
to suppress verbose connection lifecycle chatter.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from athena.platform.config.settings import AthenaSettings


def configure_logging(settings: AthenaSettings) -> None:
    """Configure structlog and the stdlib logging bridge.

    Reads the logging configuration from ``settings.logging`` and
    installs the appropriate processor chain and renderer. Safe to call
    multiple times; each call fully replaces the previous configuration.

    Args:
        settings: Fully validated platform settings. The logging pipeline
            is derived from ``settings.logging.level``,
            ``settings.logging.format``, and
            ``settings.logging.include_caller_info``.

    Example::

        settings = AthenaSettings()
        configure_logging(settings)
        log = get_logger(__name__)
        log.info("platform.ready", version=settings.app.version)
    """
    from athena.platform.types.enums import LogFormat

    log_level_int = settings.logging.level.to_int()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    if settings.logging.include_caller_info:
        shared_processors.insert(
            0,
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                ]
            ),
        )

    renderer: structlog.types.Processor
    if settings.logging.format == LogFormat.JSON:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(
            colors=sys.stdout.isatty(),
            exception_formatter=structlog.dev.plain_traceback,
        )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level_int),
        context_class=dict,
        # LoggerFactory creates stdlib logging.Logger objects, which have a
        # .name attribute required by stdlib.add_logger_name. The rendered
        # structlog output is passed to the stdlib logger as the log message,
        # then emitted via the basicConfig StreamHandler below.
        logger_factory=structlog.stdlib.LoggerFactory(),
        # False: allows test suites to re-configure between test cases.
        # Production overhead is ~100 ns/call — acceptable.
        cache_logger_on_first_use=False,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level_int,
        force=True,
    )

    for noisy_name in ("httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy_name).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named logger bound to the platform's processor chain.

    The returned logger inherits the processor chain configured by the
    most recent ``configure_logging()`` call. If logging has not been
    configured, structlog's default (minimal) configuration is used.

    Args:
        name: Logger name; pass ``__name__`` of the calling module to
            produce dotted-path names (e.g. ``athena.engines.data``).

    Returns:
        A bound logger with the configured processor chain.

    Example::

        log = get_logger(__name__)
        log.info("tick.received", symbol="NSE:NIFTY50-INDEX", ltp=24500.50)
    """
    return structlog.get_logger(name)
