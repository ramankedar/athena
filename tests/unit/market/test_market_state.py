"""Unit tests for market state value objects and transition rules."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime

import pytest

from athena.market.exceptions import InvalidMarketStateError
from athena.market.market_state import (
    VALID_TRANSITIONS,
    HaltReason,
    MarketState,
    MarketStateSnapshot,
    StateTransition,
    is_valid_transition,
    validate_transition,
)
from athena.market.models import MarketId

NOW_UTC = datetime(2025, 1, 15, 9, 15, tzinfo=UTC)
NSE_ID = MarketId("NSE")


class TestMarketState:
    def test_values(self) -> None:
        assert MarketState.CLOSED == "closed"
        assert MarketState.PRE_OPEN == "pre_open"
        assert MarketState.AUCTION == "auction"
        assert MarketState.OPEN == "open"
        assert MarketState.CLOSING == "closing"
        assert MarketState.AFTER_HOURS == "after_hours"
        assert MarketState.HALTED == "halted"
        assert MarketState.SUSPENDED == "suspended"
        assert MarketState.MAINTENANCE == "maintenance"

    def test_is_tradable_open(self) -> None:
        assert MarketState.OPEN.is_tradable is True

    def test_is_tradable_after_hours(self) -> None:
        assert MarketState.AFTER_HOURS.is_tradable is True

    def test_is_tradable_closed(self) -> None:
        assert MarketState.CLOSED.is_tradable is False

    def test_is_tradable_halted(self) -> None:
        assert MarketState.HALTED.is_tradable is False

    def test_is_operational_open(self) -> None:
        assert MarketState.OPEN.is_operational is True

    def test_is_operational_halted(self) -> None:
        assert MarketState.HALTED.is_operational is False

    def test_is_operational_maintenance(self) -> None:
        assert MarketState.MAINTENANCE.is_operational is False

    def test_accepts_orders_pre_open(self) -> None:
        assert MarketState.PRE_OPEN.accepts_orders is True

    def test_accepts_orders_open(self) -> None:
        assert MarketState.OPEN.accepts_orders is True

    def test_accepts_orders_closed(self) -> None:
        assert MarketState.CLOSED.accepts_orders is False

    def test_accepts_orders_halted(self) -> None:
        assert MarketState.HALTED.accepts_orders is False


class TestHaltReason:
    def test_values(self) -> None:
        assert HaltReason.INDEX_CIRCUIT_BREAKER == "index_circuit_breaker"
        assert HaltReason.REGULATORY == "regulatory"
        assert HaltReason.TECHNICAL == "technical"
        assert HaltReason.UNKNOWN == "unknown"


class TestMarketStateSnapshot:
    def test_open_state(self) -> None:
        snap = MarketStateSnapshot(
            exchange_id=NSE_ID,
            state=MarketState.OPEN,
            as_of=NOW_UTC,
        )
        assert snap.state == MarketState.OPEN
        assert snap.halt_reason is None

    def test_halted_state_with_reason(self) -> None:
        snap = MarketStateSnapshot(
            exchange_id=NSE_ID,
            state=MarketState.HALTED,
            as_of=NOW_UTC,
            halt_reason=HaltReason.INDEX_CIRCUIT_BREAKER,
            message="NIFTY declined >10%",
        )
        assert snap.halt_reason == HaltReason.INDEX_CIRCUIT_BREAKER
        assert snap.message == "NIFTY declined >10%"

    def test_naive_as_of_raises(self) -> None:
        with pytest.raises(InvalidMarketStateError):
            MarketStateSnapshot(
                exchange_id=NSE_ID,
                state=MarketState.OPEN,
                as_of=datetime(2025, 1, 15, 9, 15),  # naive
            )

    def test_halt_reason_on_non_halted_raises(self) -> None:
        with pytest.raises(InvalidMarketStateError, match="HALTED or SUSPENDED"):
            MarketStateSnapshot(
                exchange_id=NSE_ID,
                state=MarketState.OPEN,
                as_of=NOW_UTC,
                halt_reason=HaltReason.TECHNICAL,
            )

    def test_with_segment_id(self) -> None:
        snap = MarketStateSnapshot(
            exchange_id=NSE_ID,
            state=MarketState.OPEN,
            as_of=NOW_UTC,
            segment_id=MarketId("NSE_FO"),
        )
        assert snap.segment_id == MarketId("NSE_FO")

    def test_str(self) -> None:
        snap = MarketStateSnapshot(exchange_id=NSE_ID, state=MarketState.OPEN, as_of=NOW_UTC)
        s = str(snap)
        assert "NSE" in s
        assert "open" in s

    def test_is_frozen(self) -> None:
        snap = MarketStateSnapshot(exchange_id=NSE_ID, state=MarketState.OPEN, as_of=NOW_UTC)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            snap.state = MarketState.CLOSED  # type: ignore[misc]


class TestStateTransition:
    def test_valid_construction(self) -> None:
        t = StateTransition(
            exchange_id=NSE_ID,
            from_state=MarketState.CLOSED,
            to_state=MarketState.PRE_OPEN,
            occurred_at=NOW_UTC,
        )
        assert t.from_state == MarketState.CLOSED
        assert t.to_state == MarketState.PRE_OPEN

    def test_naive_occurred_at_raises(self) -> None:
        with pytest.raises(InvalidMarketStateError):
            StateTransition(
                exchange_id=NSE_ID,
                from_state=MarketState.CLOSED,
                to_state=MarketState.PRE_OPEN,
                occurred_at=datetime(2025, 1, 15, 9, 0),  # naive
            )


class TestTransitionRules:
    def test_closed_to_pre_open_valid(self) -> None:
        assert is_valid_transition(MarketState.CLOSED, MarketState.PRE_OPEN) is True

    def test_open_to_halted_valid(self) -> None:
        assert is_valid_transition(MarketState.OPEN, MarketState.HALTED) is True

    def test_halted_to_open_valid(self) -> None:
        assert is_valid_transition(MarketState.HALTED, MarketState.OPEN) is True

    def test_closed_to_open_invalid(self) -> None:
        assert is_valid_transition(MarketState.CLOSED, MarketState.OPEN) is False

    def test_same_state_is_valid(self) -> None:
        assert is_valid_transition(MarketState.OPEN, MarketState.OPEN) is True

    def test_valid_transitions_not_empty(self) -> None:
        assert len(VALID_TRANSITIONS) > 10

    def test_validate_transition_ok(self) -> None:
        validate_transition(MarketState.CLOSED, MarketState.PRE_OPEN, context="NSE")

    def test_validate_transition_raises_on_illegal(self) -> None:
        with pytest.raises(InvalidMarketStateError, match="Illegal"):
            validate_transition(MarketState.CLOSED, MarketState.OPEN, context="NSE")

    def test_all_valid_transitions_are_pairs(self) -> None:
        for pair in VALID_TRANSITIONS:
            assert isinstance(pair, tuple)
            assert len(pair) == 2
            assert isinstance(pair[0], MarketState)
            assert isinstance(pair[1], MarketState)
