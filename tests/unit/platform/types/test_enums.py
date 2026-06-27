"""Unit tests for platform enumerations."""

from __future__ import annotations

import logging

import pytest

from athena.platform.types.enums import (
    ApplicationMode,
    Environment,
    LogFormat,
    LogLevel,
    MarketType,
)


class TestEnvironment:
    def test_values_are_lowercase_strings(self) -> None:
        assert Environment.DEVELOPMENT == "development"
        assert Environment.TESTING == "testing"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"

    def test_is_str_at_runtime(self) -> None:
        assert isinstance(Environment.PRODUCTION, str)

    def test_string_comparison(self) -> None:
        assert Environment.DEVELOPMENT == "development"
        assert Environment.PRODUCTION != "development"

    def test_all_members_present(self) -> None:
        members = {e.value for e in Environment}
        assert members == {"development", "testing", "staging", "production"}

    def test_case_insensitive_construction_fails(self) -> None:
        with pytest.raises(ValueError, match="PRODUCTION"):
            Environment("PRODUCTION")

    def test_correct_case_construction(self) -> None:
        assert Environment("production") == Environment.PRODUCTION


class TestLogLevel:
    def test_values_are_lowercase_strings(self) -> None:
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARNING == "warning"
        assert LogLevel.ERROR == "error"
        assert LogLevel.CRITICAL == "critical"

    def test_to_int_debug(self) -> None:
        assert LogLevel.DEBUG.to_int() == logging.DEBUG

    def test_to_int_info(self) -> None:
        assert LogLevel.INFO.to_int() == logging.INFO

    def test_to_int_warning(self) -> None:
        assert LogLevel.WARNING.to_int() == logging.WARNING

    def test_to_int_error(self) -> None:
        assert LogLevel.ERROR.to_int() == logging.ERROR

    def test_to_int_critical(self) -> None:
        assert LogLevel.CRITICAL.to_int() == logging.CRITICAL

    def test_to_int_returns_int(self) -> None:
        assert isinstance(LogLevel.INFO.to_int(), int)

    def test_levels_are_ordered(self) -> None:
        assert LogLevel.DEBUG.to_int() < LogLevel.INFO.to_int()
        assert LogLevel.INFO.to_int() < LogLevel.WARNING.to_int()
        assert LogLevel.WARNING.to_int() < LogLevel.ERROR.to_int()
        assert LogLevel.ERROR.to_int() < LogLevel.CRITICAL.to_int()


class TestLogFormat:
    def test_values(self) -> None:
        assert LogFormat.CONSOLE == "console"
        assert LogFormat.JSON == "json"

    def test_is_str_at_runtime(self) -> None:
        assert isinstance(LogFormat.JSON, str)

    def test_all_members_present(self) -> None:
        members = {f.value for f in LogFormat}
        assert members == {"console", "json"}


class TestApplicationMode:
    def test_values(self) -> None:
        assert ApplicationMode.LIVE == "live"
        assert ApplicationMode.PAPER == "paper"
        assert ApplicationMode.BACKTEST == "backtest"
        assert ApplicationMode.RESEARCH == "research"

    def test_is_str_at_runtime(self) -> None:
        assert isinstance(ApplicationMode.LIVE, str)

    def test_all_members_present(self) -> None:
        members = {m.value for m in ApplicationMode}
        assert members == {"live", "paper", "backtest", "research"}

    def test_string_equality(self) -> None:
        assert ApplicationMode.RESEARCH == "research"
        assert ApplicationMode.LIVE != "research"


class TestMarketType:
    def test_values(self) -> None:
        assert MarketType.EQUITY == "equity"
        assert MarketType.DERIVATIVES == "derivatives"
        assert MarketType.CURRENCY == "currency"
        assert MarketType.COMMODITY == "commodity"

    def test_is_str_at_runtime(self) -> None:
        assert isinstance(MarketType.EQUITY, str)

    def test_all_members_present(self) -> None:
        members = {m.value for m in MarketType}
        assert members == {"equity", "derivatives", "currency", "commodity"}
