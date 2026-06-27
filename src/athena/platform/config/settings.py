"""Platform configuration via pydantic-settings.

Configuration is loaded in this order (later sources override earlier ones):

1. Typed field defaults defined in the model.
2. ``.env`` file in the current working directory (skipped if absent).
3. Process environment variables prefixed with ``ATHENA_``.

Nested settings use double-underscore as the delimiter::

    ATHENA_APP__DEBUG=true         →  settings.app.debug = True
    ATHENA_APP__MODE=paper         →  settings.app.mode = ApplicationMode.PAPER
    ATHENA_LOGGING__LEVEL=debug    →  settings.logging.level = LogLevel.DEBUG
    ATHENA_LOGGING__FORMAT=json    →  settings.logging.format = LogFormat.JSON

Production constraints (enforced at construction, before any engine starts):

- ``app.debug`` must be ``False``.
- ``logging.format`` must be ``LogFormat.JSON``.

These constraints are validated in a ``model_validator`` so they fail at
``AthenaSettings()`` construction time — never silently during trading.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from athena.platform.types.enums import ApplicationMode, Environment, LogFormat, LogLevel


class AppConfig(BaseModel):
    """Application-level metadata and operational mode.

    Attributes:
        name: Human-readable platform identifier. Appears in log headers
            and operational dashboards.
        version: Semantic version string. Set at startup from package
            metadata; do not override via environment variable.
        mode: Operational mode. Determines which subsystems are active
            and which safety interlocks apply. See ``ApplicationMode``.
        debug: When ``True``, enables verbose diagnostics and relaxes
            some performance optimisations. Forbidden in production.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = "athena"
    version: str = "0.1.0"
    mode: ApplicationMode = ApplicationMode.RESEARCH
    debug: bool = False


class LoggingConfig(BaseModel):
    """Logging subsystem configuration.

    Attributes:
        level: Minimum log level to emit. Messages below this level are
            discarded before reaching any handler or renderer.
        format: Output format. ``CONSOLE`` is human-readable and suited
            for development. ``JSON`` is machine-parseable and required
            in all deployed environments. See ``LogFormat``.
        include_caller_info: When ``True``, attaches the source filename,
            line number, and function name to every log entry. Useful for
            debugging; adds ~500ns overhead per log call.
    """

    model_config = ConfigDict(extra="forbid")

    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.CONSOLE
    include_caller_info: bool = False


class AthenaSettings(BaseSettings):
    """Root platform settings for the Athena platform.

    Instantiate once at application startup and pass the resulting object
    to all engines and subsystems. Do not re-instantiate per-request:
    pydantic-settings reads from the process environment at construction.

    Attributes:
        environment: Deployment environment. Controls which defaults
            are applied and which safety constraints are enforced.
        app: Application metadata and operational mode.
        logging: Logging subsystem configuration.

    Raises:
        pydantic.ValidationError: If any field value cannot be coerced
            to the declared type (e.g., an invalid enum value).
        pydantic.ValidationError: If production safety constraints are
            violated (``app.debug=True`` or ``logging.format=CONSOLE``
            in the production environment).

    Example::

        # Load from environment variables and .env file
        settings = AthenaSettings()

        # Construct explicitly for testing
        settings = AthenaSettings(
            environment=Environment.TESTING,
            logging=LoggingConfig(level=LogLevel.DEBUG, format=LogFormat.CONSOLE),
        )
    """

    model_config = SettingsConfigDict(
        env_prefix="ATHENA_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Environment = Environment.DEVELOPMENT
    app: AppConfig = AppConfig()
    logging: LoggingConfig = LoggingConfig()

    @model_validator(mode="after")
    def enforce_production_constraints(self) -> AthenaSettings:
        """Enforce safety constraints required in the production environment.

        Checks that debug mode is disabled and that JSON logging is
        configured before any engine is allowed to initialise.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If one or more production constraints are violated.
                The message lists all violations so the operator can fix
                them in a single deployment iteration.
        """
        if self.environment != Environment.PRODUCTION:
            return self

        violations: list[str] = []

        if self.app.debug:
            violations.append("app.debug must be False in production (set ATHENA_APP__DEBUG=false)")

        if self.logging.format != LogFormat.JSON:
            violations.append(
                f"logging.format must be 'json' in production "
                f"(got '{self.logging.format.value}', "
                f"set ATHENA_LOGGING__FORMAT=json)"
            )

        if violations:
            joined = "\n".join(f"  - {v}" for v in violations)
            raise ValueError(f"Production configuration violations:\n{joined}")

        return self

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in the production environment.

        Returns:
            ``True`` if ``environment`` is ``Environment.PRODUCTION``.
        """
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Return ``True`` when running in the development environment.

        Returns:
            ``True`` if ``environment`` is ``Environment.DEVELOPMENT``.
        """
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Return ``True`` when running under the automated test suite.

        Returns:
            ``True`` if ``environment`` is ``Environment.TESTING``.
        """
        return self.environment == Environment.TESTING

    @property
    def is_staging(self) -> bool:
        """Return ``True`` when running in the staging environment.

        Returns:
            ``True`` if ``environment`` is ``Environment.STAGING``.
        """
        return self.environment == Environment.STAGING
