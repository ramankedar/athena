"""Unit tests for the application bootstrapper."""

from __future__ import annotations

from datetime import UTC

import pytest

from athena.platform.bootstrap.bootstrapper import (
    _resolve_settings,
    _validate_mode_environment,
    bootstrap_application,
)
from athena.platform.bootstrap.context import ApplicationContext
from athena.platform.config.settings import AppConfig, AthenaSettings, LoggingConfig
from athena.platform.exceptions.errors import ConfigurationError
from athena.platform.types.enums import ApplicationMode, Environment, LogFormat


class TestBootstrapApplication:
    def test_returns_application_context(self, dev_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(dev_settings)
        assert isinstance(ctx, ApplicationContext)

    def test_context_settings_match_input(self, dev_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(dev_settings)
        assert ctx.settings is dev_settings

    def test_context_environment_matches_settings(self, dev_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(dev_settings)
        assert ctx.environment == Environment.DEVELOPMENT

    def test_context_mode_matches_settings(self, dev_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(dev_settings)
        assert ctx.mode == ApplicationMode.RESEARCH

    def test_started_at_is_utc_aware(self, dev_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(dev_settings)
        assert ctx.started_at.tzinfo is not None

    def test_started_at_is_utc(self, dev_settings: AthenaSettings) -> None:

        ctx = bootstrap_application(dev_settings)
        assert ctx.started_at.tzinfo == UTC

    def test_two_calls_produce_independent_contexts(self, dev_settings: AthenaSettings) -> None:
        ctx1 = bootstrap_application(dev_settings)
        ctx2 = bootstrap_application(dev_settings)
        assert ctx1 is not ctx2
        assert ctx1.started_at <= ctx2.started_at

    def test_context_is_immutable(self, dev_settings: AthenaSettings) -> None:
        import dataclasses

        ctx = bootstrap_application(dev_settings)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            ctx.settings = dev_settings  # type: ignore[misc]

    def test_production_mode_bootstraps_correctly(self, prod_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(prod_settings)
        assert ctx.is_production is True

    def test_testing_environment_bootstraps(self, test_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(test_settings)
        assert ctx.is_testing is True


class TestBootstrapWithNoSettings:
    def test_loads_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_ENVIRONMENT", "testing")
        monkeypatch.setenv("ATHENA_LOGGING__FORMAT", "console")
        ctx = bootstrap_application()
        assert ctx.environment == Environment.TESTING

    def test_bad_env_var_raises_configuration_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_ENVIRONMENT", "not_a_real_environment")
        with pytest.raises((ConfigurationError, Exception)):
            bootstrap_application()


class TestValidateModeEnvironment:
    def test_research_mode_in_development_is_allowed(self, dev_settings: AthenaSettings) -> None:
        _validate_mode_environment(dev_settings)

    def test_paper_mode_in_development_is_allowed(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            app=AppConfig(mode=ApplicationMode.PAPER),
        )
        _validate_mode_environment(settings)

    def test_backtest_mode_in_testing_is_allowed(self) -> None:
        settings = AthenaSettings(
            environment=Environment.TESTING,
            app=AppConfig(mode=ApplicationMode.BACKTEST),
        )
        _validate_mode_environment(settings)

    def test_live_mode_in_production_is_allowed(self, prod_settings: AthenaSettings) -> None:
        settings = AthenaSettings(
            environment=Environment.PRODUCTION,
            app=AppConfig(mode=ApplicationMode.LIVE, debug=False),
            logging=LoggingConfig(format=LogFormat.JSON),
        )
        _validate_mode_environment(settings)

    def test_live_mode_in_development_raises(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            app=AppConfig(mode=ApplicationMode.LIVE),
        )
        with pytest.raises(ConfigurationError, match="PRODUCTION"):
            _validate_mode_environment(settings)

    def test_live_mode_in_staging_raises(self) -> None:
        settings = AthenaSettings(
            environment=Environment.STAGING,
            app=AppConfig(mode=ApplicationMode.LIVE),
        )
        with pytest.raises(ConfigurationError, match="PRODUCTION"):
            _validate_mode_environment(settings)

    def test_live_mode_with_debug_in_production_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="debug"):
            AthenaSettings(
                environment=Environment.PRODUCTION,
                app=AppConfig(mode=ApplicationMode.LIVE, debug=True),
                logging=LoggingConfig(format=LogFormat.JSON),
            )

    def test_error_code_is_in_exception_context(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            app=AppConfig(mode=ApplicationMode.LIVE),
        )
        with pytest.raises(ConfigurationError) as exc_info:
            _validate_mode_environment(settings)
        assert exc_info.value.error_code == "CFG_101"
        assert exc_info.value.context["mode"] == "live"
        assert exc_info.value.context["environment"] == "development"


class TestResolveSettings:
    def test_returns_provided_settings(self, dev_settings: AthenaSettings) -> None:
        resolved = _resolve_settings(dev_settings)
        assert resolved is dev_settings

    def test_loads_from_env_when_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ATHENA_ENVIRONMENT", "testing")
        monkeypatch.setenv("ATHENA_LOGGING__FORMAT", "console")
        resolved = _resolve_settings(None)
        assert resolved.environment == Environment.TESTING


class TestApplicationContext:
    def test_is_production_false_in_development(self, dev_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(dev_settings)
        assert ctx.is_production is False

    def test_is_development_true_in_development(self, dev_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(dev_settings)
        assert ctx.is_development is True

    def test_is_testing_true_in_testing(self, test_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(test_settings)
        assert ctx.is_testing is True

    def test_is_production_true_in_production(self, prod_settings: AthenaSettings) -> None:
        ctx = bootstrap_application(prod_settings)
        assert ctx.is_production is True
        assert ctx.is_development is False
        assert ctx.is_testing is False
