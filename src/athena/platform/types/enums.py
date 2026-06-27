"""Shared platform enumerations.

Defines the vocabulary for platform-level concerns: deployment environments,
logging configuration, operational modes, and market classifications.

All enumerations use ``StrEnum`` (Python 3.11+) so that enum values *are*
strings. This enables direct comparison with environment variable values,
automatic JSON serialisation, and pydantic-settings validation without
custom validators.

Note:
    Market domain types (``Exchange``, ``Segment``, ``OptionType``) are
    defined in ``athena.core.domain.instrument`` and should be imported
    from there when working with tradable instruments. The enumerations
    here are for platform-level configuration, not market-domain entities.
"""

from __future__ import annotations

from enum import StrEnum


class Environment(StrEnum):
    """Deployment environment in which the platform is running.

    Controls environment-specific default values and enforces safety
    constraints. For example, the production environment requires
    JSON-format logging and forbids debug mode.

    Attributes:
        DEVELOPMENT: Local engineer machines. Connects to local services.
        TESTING: Automated test suite. Ephemeral fixtures, no real services.
        STAGING: Pre-production validation. Live feed, paper orders only.
        PRODUCTION: Live trading. All safety interlocks enforced.
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(StrEnum):
    """Logging verbosity level.

    Values match Python's ``logging`` module level names (case-insensitive).
    pydantic-settings validates environment variable values against these
    automatically when the field type is ``LogLevel``.

    Attributes:
        DEBUG: Verbose diagnostic output. Never use in production.
        INFO: Normal operational events.
        WARNING: Recoverable anomalies that deserve attention.
        ERROR: Failures that affect functionality but allow continuation.
        CRITICAL: Failures that require immediate intervention or halt.
    """

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    def to_int(self) -> int:
        """Convert to the stdlib ``logging`` module integer level.

        Returns:
            An integer level constant (e.g. ``logging.DEBUG == 10``),
            suitable for use with ``logging.setLevel()`` and
            ``structlog.make_filtering_bound_logger()``.
        """
        import logging

        return int(getattr(logging, self.upper()))


class LogFormat(StrEnum):
    """Log output format.

    Attributes:
        CONSOLE: Human-readable, colour-coded output for interactive
            terminals. Not machine-parseable.
        JSON: One JSON object per line. Required in deployed environments
            for log aggregation (Datadog, Loki, CloudWatch, etc.).
    """

    CONSOLE = "console"
    JSON = "json"


class ApplicationMode(StrEnum):
    """Operational mode of the Athena platform.

    The platform runs in exactly one mode at a time. Modes control which
    subsystems are activated and which safety interlocks are applied.

    Attributes:
        LIVE: Live trading with real money. All risk checks enforced.
            Only permitted in the ``PRODUCTION`` environment.
        PAPER: Simulated order submission. No financial exposure.
        BACKTEST: Historical simulation mode. No live market feeds.
        RESEARCH: Analysis and development only. No order capability.
    """

    LIVE = "live"
    PAPER = "paper"
    BACKTEST = "backtest"
    RESEARCH = "research"


class MarketType(StrEnum):
    """Classification of a financial market segment.

    Used for instrument categorisation and segment-specific configuration
    (margin rules, session schedules, lot sizes).

    Attributes:
        EQUITY: Cash equity instruments.
        DERIVATIVES: Futures and options on equities and indices.
        CURRENCY: Foreign exchange and currency derivatives.
        COMMODITY: Commodity futures (MCX instruments).
    """

    EQUITY = "equity"
    DERIVATIVES = "derivatives"
    CURRENCY = "currency"
    COMMODITY = "commodity"
