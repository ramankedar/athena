"""Unit tests for platform settings."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from athena.platform.config.settings import AppConfig, AthenaSettings, LoggingConfig
from athena.platform.types.enums import ApplicationMode, Environment, LogFormat, LogLevel


class TestAppConfig:
    def test_defaults(self) -> None:
        cfg = AppConfig()
        assert cfg.name == "athena"
        assert cfg.version == "0.1.0"
        assert cfg.mode == ApplicationMode.RESEARCH
        assert cfg.debug is False

    def test_mode_override(self) -> None:
        cfg = AppConfig(mode=ApplicationMode.PAPER)
        assert cfg.mode == ApplicationMode.PAPER

    def test_debug_override(self) -> None:
        cfg = AppConfig(debug=True)
        assert cfg.debug is True

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs"):
            AppConfig(unknown_field="value")  # type: ignore[call-arg]

    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AppConfig(mode="invalid_mode")  # type: ignore[arg-type]


class TestLoggingConfig:
    def test_defaults(self) -> None:
        cfg = LoggingConfig()
        assert cfg.level == LogLevel.INFO
        assert cfg.format == LogFormat.CONSOLE
        assert cfg.include_caller_info is False

    def test_level_override(self) -> None:
        cfg = LoggingConfig(level=LogLevel.DEBUG)
        assert cfg.level == LogLevel.DEBUG

    def test_format_override(self) -> None:
        cfg = LoggingConfig(format=LogFormat.JSON)
        assert cfg.format == LogFormat.JSON

    def test_include_caller_info_override(self) -> None:
        cfg = LoggingConfig(include_caller_info=True)
        assert cfg.include_caller_info is True

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs"):
            LoggingConfig(unknown="x")  # type: ignore[call-arg]

    def test_invalid_level_rejected(self) -> None:
        with pytest.raises(ValidationError):
            LoggingConfig(level="trace")  # type: ignore[arg-type]


class TestAthenaSettings:
    def test_default_environment_is_development(self) -> None:
        settings = AthenaSettings()
        assert settings.environment == Environment.DEVELOPMENT

    def test_default_app_config(self) -> None:
        settings = AthenaSettings()
        assert settings.app.name == "athena"
        assert settings.app.mode == ApplicationMode.RESEARCH
        assert settings.app.debug is False

    def test_default_logging_config(self) -> None:
        settings = AthenaSettings()
        assert settings.logging.level == LogLevel.INFO
        assert settings.logging.format == LogFormat.CONSOLE

    def test_environment_override_via_constructor(self) -> None:
        settings = AthenaSettings(environment=Environment.TESTING)
        assert settings.environment == Environment.TESTING

    def test_nested_override_via_constructor(self) -> None:
        settings = AthenaSettings(logging=LoggingConfig(level=LogLevel.DEBUG))
        assert settings.logging.level == LogLevel.DEBUG

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_ENVIRONMENT", "staging")
        settings = AthenaSettings()
        assert settings.environment == Environment.STAGING

    def test_nested_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_LOGGING__LEVEL", "debug")
        settings = AthenaSettings()
        assert settings.logging.level == LogLevel.DEBUG

    def test_nested_format_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_LOGGING__FORMAT", "json")
        settings = AthenaSettings()
        assert settings.logging.format == LogFormat.JSON

    def test_unknown_env_var_is_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_COMPLETELY_UNKNOWN", "value")
        settings = AthenaSettings()
        assert settings.environment == Environment.DEVELOPMENT

    def test_is_development_true(self) -> None:
        settings = AthenaSettings(environment=Environment.DEVELOPMENT)
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False
        assert settings.is_staging is False

    def test_is_testing_true(self) -> None:
        settings = AthenaSettings(environment=Environment.TESTING)
        assert settings.is_testing is True
        assert settings.is_development is False
        assert settings.is_production is False

    def test_is_staging_true(self) -> None:
        settings = AthenaSettings(environment=Environment.STAGING)
        assert settings.is_staging is True
        assert settings.is_development is False

    def test_is_production_true(self, prod_settings: AthenaSettings) -> None:
        assert prod_settings.is_production is True
        assert prod_settings.is_development is False


class TestProductionConstraints:
    def test_valid_production_settings_accepted(self, prod_settings: AthenaSettings) -> None:
        assert prod_settings.is_production is True

    def test_debug_true_in_production_raises(self) -> None:
        with pytest.raises(ValidationError, match="debug"):
            AthenaSettings(
                environment=Environment.PRODUCTION,
                app=AppConfig(debug=True),
                logging=LoggingConfig(format=LogFormat.JSON),
            )

    def test_console_format_in_production_raises(self) -> None:
        with pytest.raises(ValidationError, match=r"logging\.format"):
            AthenaSettings(
                environment=Environment.PRODUCTION,
                app=AppConfig(debug=False),
                logging=LoggingConfig(format=LogFormat.CONSOLE),
            )

    def test_both_violations_reported(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            AthenaSettings(
                environment=Environment.PRODUCTION,
                app=AppConfig(debug=True),
                logging=LoggingConfig(format=LogFormat.CONSOLE),
            )
        error_text = str(exc_info.value)
        assert "debug" in error_text
        assert "logging.format" in error_text

    def test_debug_allowed_in_development(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            app=AppConfig(debug=True),
        )
        assert settings.app.debug is True

    def test_console_format_allowed_in_staging(self) -> None:
        settings = AthenaSettings(
            environment=Environment.STAGING,
            logging=LoggingConfig(format=LogFormat.CONSOLE),
        )
        assert settings.logging.format == LogFormat.CONSOLE
