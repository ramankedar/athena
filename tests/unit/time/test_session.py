"""Unit tests for NSESessionService."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from athena.core.domain.market import MarketSession, SessionType
from athena.time.exceptions import NaiveDatetimeError
from athena.time.session import NSESessionService
from athena.time.timezone import UTC
from tests.unit.time.conftest import (
    AFTER_CLOSE_UTC,
    BEFORE_OPEN_UTC,
    CLOSING_UTC,
    NORMAL_UTC,
    POST_CLOSE_UTC,
    PRE_OPEN_MATCH_UTC,
    PRE_OPEN_UTC,
    TRADING_DATE,
    WEEKEND_DATE,
)


class TestGetSessionType:
    def test_before_open_is_closed(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session_type(BEFORE_OPEN_UTC) == SessionType.CLOSED

    def test_pre_open_session(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session_type(PRE_OPEN_UTC) == SessionType.PRE_OPEN

    def test_pre_open_matching_session(self, nse_session_service: NSESessionService) -> None:
        assert (
            nse_session_service.get_session_type(PRE_OPEN_MATCH_UTC)
            == SessionType.PRE_OPEN_MATCHING
        )

    def test_normal_session(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session_type(NORMAL_UTC) == SessionType.NORMAL

    def test_closing_session(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session_type(CLOSING_UTC) == SessionType.CLOSING

    def test_post_close_session(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session_type(POST_CLOSE_UTC) == SessionType.POST_CLOSE

    def test_after_close_is_closed(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session_type(AFTER_CLOSE_UTC) == SessionType.CLOSED

    def test_weekend_is_closed(self, nse_session_service: NSESessionService) -> None:
        saturday_normal_time = datetime(2025, 1, 18, 5, 30, tzinfo=UTC)
        assert nse_session_service.get_session_type(saturday_normal_time) == SessionType.CLOSED

    def test_uses_clock_when_at_is_none(self, nse_session_service: NSESessionService) -> None:
        # Clock is frozen at NORMAL_UTC
        assert nse_session_service.get_session_type() == SessionType.NORMAL

    def test_raises_on_naive_datetime(self, nse_session_service: NSESessionService) -> None:
        with pytest.raises(NaiveDatetimeError):
            nse_session_service.get_session_type(datetime(2025, 1, 15, 9, 0))


class TestGetSession:
    def test_returns_none_before_open(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session(BEFORE_OPEN_UTC) is None

    def test_returns_none_after_close(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.get_session(AFTER_CLOSE_UTC) is None

    def test_returns_none_on_weekend(self, nse_session_service: NSESessionService) -> None:
        saturday = datetime(2025, 1, 18, 5, 30, tzinfo=UTC)
        assert nse_session_service.get_session(saturday) is None

    def test_returns_market_session_during_normal(
        self, nse_session_service: NSESessionService
    ) -> None:
        session = nse_session_service.get_session(NORMAL_UTC)
        assert session is not None
        assert isinstance(session, MarketSession)
        assert session.session_type == SessionType.NORMAL

    def test_session_times_span_at(self, nse_session_service: NSESessionService) -> None:
        session = nse_session_service.get_session(NORMAL_UTC)
        assert session is not None
        assert session.opens_at_utc <= NORMAL_UTC < session.closes_at_utc

    def test_uses_clock_when_at_is_none(self, nse_session_service: NSESessionService) -> None:
        session = nse_session_service.get_session()
        assert session is not None
        assert session.session_type == SessionType.NORMAL


class TestNextSession:
    def test_next_from_before_open(self, nse_session_service: NSESessionService) -> None:
        # Before open → next session is PRE_OPEN same day
        session = nse_session_service.next_session(BEFORE_OPEN_UTC)
        assert session.session_type == SessionType.PRE_OPEN
        assert session.opens_at_utc.date() == TRADING_DATE

    def test_next_from_pre_open(self, nse_session_service: NSESessionService) -> None:
        # During PRE_OPEN → next is PRE_OPEN_MATCHING
        session = nse_session_service.next_session(PRE_OPEN_UTC)
        assert session.session_type == SessionType.PRE_OPEN_MATCHING

    def test_next_from_normal(self, nse_session_service: NSESessionService) -> None:
        # During NORMAL → next is CLOSING
        session = nse_session_service.next_session(NORMAL_UTC)
        assert session.session_type == SessionType.CLOSING

    def test_next_from_after_close_is_next_day(
        self, nse_session_service: NSESessionService
    ) -> None:
        # After market close → next session is PRE_OPEN on next trading day
        session = nse_session_service.next_session(AFTER_CLOSE_UTC)
        assert session.session_type == SessionType.PRE_OPEN
        assert session.opens_at_utc.date() > TRADING_DATE

    def test_next_from_weekend_is_monday(self, nse_session_service: NSESessionService) -> None:
        saturday_noon = datetime(2025, 1, 18, 6, 0, tzinfo=UTC)
        session = nse_session_service.next_session(saturday_noon)
        assert session.session_type == SessionType.PRE_OPEN
        # Monday Jan 20
        assert session.opens_at_utc.astimezone().date() >= date(2025, 1, 19)

    def test_raises_on_naive_datetime(self, nse_session_service: NSESessionService) -> None:
        with pytest.raises(NaiveDatetimeError):
            nse_session_service.next_session(datetime(2025, 1, 15, 9, 0))


class TestPreviousSession:
    def test_previous_from_after_close(self, nse_session_service: NSESessionService) -> None:
        # After close → previous is POST_CLOSE same day
        session = nse_session_service.previous_session(AFTER_CLOSE_UTC)
        assert session.session_type == SessionType.POST_CLOSE
        assert session.closes_at_utc < AFTER_CLOSE_UTC

    def test_previous_from_closing(self, nse_session_service: NSESessionService) -> None:
        # During CLOSING → previous is NORMAL
        session = nse_session_service.previous_session(CLOSING_UTC)
        assert session.session_type == SessionType.NORMAL

    def test_previous_from_before_open_is_previous_day(
        self, nse_session_service: NSESessionService
    ) -> None:
        session = nse_session_service.previous_session(BEFORE_OPEN_UTC)
        assert session.session_type == SessionType.POST_CLOSE
        assert session.closes_at_utc < BEFORE_OPEN_UTC

    def test_raises_on_naive_datetime(self, nse_session_service: NSESessionService) -> None:
        with pytest.raises(NaiveDatetimeError):
            nse_session_service.previous_session(datetime(2025, 1, 15, 9, 0))


class TestSessionsForDate:
    def test_returns_five_sessions_for_trading_day(
        self, nse_session_service: NSESessionService
    ) -> None:
        sessions = nse_session_service.sessions_for_date(TRADING_DATE)
        assert len(sessions) == 5

    def test_sessions_in_chronological_order(self, nse_session_service: NSESessionService) -> None:
        sessions = nse_session_service.sessions_for_date(TRADING_DATE)
        for i in range(len(sessions) - 1):
            assert sessions[i].opens_at_utc < sessions[i + 1].opens_at_utc

    def test_returns_empty_for_weekend(self, nse_session_service: NSESessionService) -> None:
        assert nse_session_service.sessions_for_date(WEEKEND_DATE) == []

    def test_all_sessions_are_market_sessions(self, nse_session_service: NSESessionService) -> None:
        sessions = nse_session_service.sessions_for_date(TRADING_DATE)
        assert all(isinstance(s, MarketSession) for s in sessions)

    def test_first_session_is_pre_open(self, nse_session_service: NSESessionService) -> None:
        sessions = nse_session_service.sessions_for_date(TRADING_DATE)
        assert sessions[0].session_type == SessionType.PRE_OPEN

    def test_last_session_is_post_close(self, nse_session_service: NSESessionService) -> None:
        sessions = nse_session_service.sessions_for_date(TRADING_DATE)
        assert sessions[-1].session_type == SessionType.POST_CLOSE
