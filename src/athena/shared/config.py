"""Platform configuration via pydantic-settings.

Configuration hierarchy (later sources override earlier ones):
    1. `configs/{environment}.toml`  — non-secret defaults per environment
    2. `.env` file                   — local developer overrides
    3. Environment variables         — CI, Docker, secrets manager injection

Variable naming convention:
    ATHENA_{SECTION}__{KEY}  maps to  settings.{section}.{key}

    Examples:
        ATHENA_DATABASE__HOST=db.prod.internal → settings.database.host
        ATHENA_LOG_LEVEL=INFO                  → settings.log_level
        ATHENA_REDIS__URL=redis://...          → settings.redis.url

Secret fields use pydantic's SecretStr: they are never serialised into
logs, repr(), or error messages. Access the raw value with .get_secret_value()
only at the infrastructure boundary where the secret is consumed.
"""

from __future__ import annotations

from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """TimescaleDB connection settings."""

    model_config = SettingsConfigDict(extra="ignore")

    host: str = "localhost"
    port: int = 5432
    name: str = "athena_dev"
    user: str = "athena"
    password: SecretStr = SecretStr("changeme")

    @property
    def dsn(self) -> str:
        """PostgreSQL connection DSN (password excluded from repr)."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.name}"
        )


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(extra="ignore")

    url: str = "redis://localhost:6379/0"
    max_connections: int = 20


class AthenaSettings(BaseSettings):
    """Root configuration for the Athena platform.

    Instantiate once at startup and pass to all engines. Do not re-instantiate
    per-request: pydantic-settings reads environment variables on construction.

    Usage:
        settings = AthenaSettings()
        configure_logging(settings)
    """

    model_config = SettingsConfigDict(
        env_prefix="ATHENA_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"
