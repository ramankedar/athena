"""Application bootstrapper.

``bootstrap_application()`` is the single entry point for platform
initialisation. It performs these steps in order:

1. **Resolve settings**: Use provided settings or load from the environment.
2. **Configure logging**: Install the structlog processor chain.
3. **Validate mode-environment compatibility**: Catch dangerous mismatches
   (e.g. LIVE trading mode outside production) before any engine starts.
4. **Emit startup log entry**: Record the resolved configuration.
5. **Return** an immutable ``ApplicationContext``.

A function is used instead of a class because there is no persistent state
between calls. Each call produces an independent ``ApplicationContext`` with
its own ``started_at`` timestamp. If lifecycle hooks become necessary in a
future sprint, they will be added as optional parameters to this function
rather than as methods on a bootstrapper class.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from athena.platform.bootstrap.context import ApplicationContext
from athena.platform.config.settings import AthenaSettings
from athena.platform.exceptions.errors import ConfigurationError
from athena.platform.logging.setup import configure_logging
from athena.platform.types.enums import ApplicationMode, Environment

_log = structlog.get_logger(__name__)


def bootstrap_application(
    settings: AthenaSettings | None = None,
) -> ApplicationContext:
    """Bootstrap the Athena platform and return an application context.

    Loads and validates configuration, configures the structured logging
    pipeline, enforces mode-environment compatibility constraints, and
    returns an immutable ``ApplicationContext`` capturing the startup state.

    This function is idempotent with respect to the settings it receives:
    calling it multiple times with the same settings produces independent
    contexts with different ``started_at`` timestamps.

    Args:
        settings: Pre-constructed settings instance. When ``None``, settings
            are loaded from process environment variables and the ``.env``
            file. Providing settings explicitly is the recommended pattern
            in tests to avoid reading from the live environment.

    Returns:
        An immutable ``ApplicationContext`` with fully resolved settings.

    Raises:
        ConfigurationError: If settings cannot be loaded from the environment,
            or if the configured mode is incompatible with the environment
            (e.g. ``LIVE`` mode outside ``PRODUCTION``).
        pydantic.ValidationError: If environment variable values cannot be
            coerced to the declared types, or if production constraints are
            violated (from ``AthenaSettings`` model validation).

    Example::

        ctx = bootstrap_application()
        log = get_logger(__name__)
        log.info("engines.starting", environment=ctx.environment.value)
    """
    resolved = _resolve_settings(settings)
    configure_logging(resolved)
    _validate_mode_environment(resolved)

    ctx = ApplicationContext(
        settings=resolved,
        started_at=datetime.now(UTC),
    )

    _log.info(
        "platform.bootstrapped",
        environment=ctx.environment.value,
        mode=ctx.mode.value,
        log_level=resolved.logging.level.value,
        log_format=resolved.logging.format.value,
        debug=resolved.app.debug,
        version=resolved.app.version,
    )

    return ctx


def _resolve_settings(override: AthenaSettings | None) -> AthenaSettings:
    """Return the provided settings or load from the process environment.

    Args:
        override: Caller-supplied settings, or ``None`` to load from
            the environment.

    Returns:
        Resolved and validated ``AthenaSettings``.

    Raises:
        ConfigurationError: If environment loading fails with an unexpected
            error not covered by pydantic's ``ValidationError``.
    """
    if override is not None:
        return override

    try:
        return AthenaSettings()
    except Exception as exc:
        raise ConfigurationError(
            "Failed to load platform settings from environment",
            error_code="CFG_100",
            cause=str(exc),
        ) from exc


def _validate_mode_environment(settings: AthenaSettings) -> None:
    """Enforce mode-environment compatibility constraints.

    ``LIVE`` trading is restricted to the ``PRODUCTION`` environment as a
    last line of defence: even if a developer manages to construct settings
    with ``mode=LIVE`` and ``environment=DEVELOPMENT``, the bootstrap will
    refuse to start. This prevents accidental real-money order submission
    on developer or staging machines.

    Args:
        settings: Fully validated platform settings.

    Raises:
        ConfigurationError: If ``LIVE`` mode is used outside ``PRODUCTION``,
            or if ``LIVE`` mode is combined with ``debug=True``.
    """
    if settings.app.mode != ApplicationMode.LIVE:
        return

    if settings.environment != Environment.PRODUCTION:
        raise ConfigurationError(
            "LIVE trading mode is only permitted in the PRODUCTION environment",
            error_code="CFG_101",
            mode=settings.app.mode.value,
            environment=settings.environment.value,
        )

    if settings.app.debug:
        raise ConfigurationError(
            "LIVE trading mode cannot run with debug=True",
            error_code="CFG_102",
            mode=settings.app.mode.value,
        )
