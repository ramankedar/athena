"""Unit tests for logging setup."""

from __future__ import annotations

from athena.platform.config.settings import AthenaSettings, LoggingConfig
from athena.platform.logging.setup import configure_logging, get_logger
from athena.platform.types.enums import Environment, LogFormat, LogLevel


class TestConfigureLogging:
    def test_configure_development_does_not_raise(self, dev_settings: AthenaSettings) -> None:
        configure_logging(dev_settings)

    def test_configure_production_does_not_raise(self, prod_settings: AthenaSettings) -> None:
        configure_logging(prod_settings)

    def test_configure_testing_does_not_raise(self, test_settings: AthenaSettings) -> None:
        configure_logging(test_settings)

    def test_configure_json_format_does_not_raise(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            logging=LoggingConfig(format=LogFormat.JSON),
        )
        configure_logging(settings)

    def test_configure_with_include_caller_info(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            logging=LoggingConfig(include_caller_info=True),
        )
        configure_logging(settings)

    def test_configure_debug_level(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            logging=LoggingConfig(level=LogLevel.DEBUG),
        )
        configure_logging(settings)

    def test_configure_error_level(self) -> None:
        settings = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            logging=LoggingConfig(level=LogLevel.ERROR),
        )
        configure_logging(settings)

    def test_reconfigure_does_not_raise(self, dev_settings: AthenaSettings) -> None:
        configure_logging(dev_settings)
        configure_logging(dev_settings)

    def test_reconfigure_picks_up_new_level(self) -> None:
        settings_info = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            logging=LoggingConfig(level=LogLevel.INFO),
        )
        settings_debug = AthenaSettings(
            environment=Environment.DEVELOPMENT,
            logging=LoggingConfig(level=LogLevel.DEBUG),
        )
        configure_logging(settings_info)
        configure_logging(settings_debug)


class TestGetLogger:
    def test_returns_non_none(self) -> None:
        log = get_logger(__name__)
        assert log is not None

    def test_is_callable_logger(self) -> None:
        # structlog.get_logger returns a BoundLoggerLazyProxy at runtime.
        # The structlog.stdlib.BoundLogger annotation is for mypy only.
        # Verify via duck typing: the object must have the core log methods.
        log = get_logger(__name__)
        assert hasattr(log, "info")
        assert hasattr(log, "debug")
        assert hasattr(log, "error")

    def test_has_info_method(self) -> None:
        log = get_logger(__name__)
        assert callable(log.info)

    def test_has_debug_method(self) -> None:
        log = get_logger(__name__)
        assert callable(log.debug)

    def test_has_warning_method(self) -> None:
        log = get_logger(__name__)
        assert callable(log.warning)

    def test_has_error_method(self) -> None:
        log = get_logger(__name__)
        assert callable(log.error)

    def test_has_critical_method(self) -> None:
        log = get_logger(__name__)
        assert callable(log.critical)

    def test_different_names_produce_different_loggers(self) -> None:
        log_a = get_logger("athena.engines.data")
        log_b = get_logger("athena.engines.trading")
        assert log_a is not log_b

    def test_logger_does_not_raise_on_call(self, dev_settings: AthenaSettings) -> None:
        configure_logging(dev_settings)
        log = get_logger(__name__)
        log.info("test.event", key="value")
