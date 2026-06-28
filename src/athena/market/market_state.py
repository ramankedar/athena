"""Market operational state value objects and transition rules.

``MarketState`` is orthogonal to ``SessionType`` from the time domain:
    - ``SessionType`` answers: "What session is scheduled right now?"
      (pre-open, normal trading, closing auction).
    - ``MarketState`` answers: "Is the market actually operable right now?"
      (open, halted, suspended, under maintenance).

A market can be in ``SessionType.CONTINUOUS`` (normal session is scheduled)
while simultaneously in ``MarketState.HALTED`` (trading suspended by a
circuit breaker). Both dimensions are necessary.

State transition rules:
    Not every transition is legal. ``VALID_TRANSITIONS`` is a frozenset of
    ``(from_state, to_state)`` pairs that represent the allowed moves. Any
    code performing a state change should call ``is_valid_transition()``
    first. Implementations that manage state (future sprint) raise
    ``InvalidMarketStateError`` on illegal transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from athena.market.exceptions import InvalidMarketStateError

if TYPE_CHECKING:
    from datetime import datetime

    from athena.market.models import MarketId


class MarketState(StrEnum):
    """Operational state of a market exchange or segment.

    Attributes:
        CLOSED:       Market is not operating. No order placement or
            matching. Normal overnight/weekend state.
        PRE_OPEN:     Market accepts orders but does not match them.
            Price discovery has not begun.
        AUCTION:      Call auction in progress (opening or closing).
            Orders are batched and matched at a single price.
        OPEN:         Continuous trading. Orders are matched in real time.
        CLOSING:      Transition phase before or during closing auction.
            New order entry may be restricted.
        AFTER_HOURS:  Post-close session with limited order types.
            Typically for institutional participants only.
        HALTED:       Trading suspended by a circuit breaker or regulatory
            action. Temporary — market expects to resume.
        SUSPENDED:    Administratively suspended. Longer-duration stop;
            may be instrument-level or exchange-level.
        MAINTENANCE:  Exchange systems are undergoing maintenance.
            No trading or order entry possible.
    """

    CLOSED = "closed"
    PRE_OPEN = "pre_open"
    AUCTION = "auction"
    OPEN = "open"
    CLOSING = "closing"
    AFTER_HOURS = "after_hours"
    HALTED = "halted"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"

    @property
    def is_tradable(self) -> bool:
        """Return ``True`` when orders can be submitted and matched.

        Returns:
            ``True`` for ``OPEN`` and ``AFTER_HOURS`` only.
        """
        return self in (MarketState.OPEN, MarketState.AFTER_HOURS)

    @property
    def is_operational(self) -> bool:
        """Return ``True`` when the exchange is in a normal operating state.

        Returns:
            ``True`` for all states except ``HALTED``, ``SUSPENDED``,
            and ``MAINTENANCE``.
        """
        return self not in (
            MarketState.HALTED,
            MarketState.SUSPENDED,
            MarketState.MAINTENANCE,
        )

    @property
    def accepts_orders(self) -> bool:
        """Return ``True`` when new orders can be placed (even if not matched).

        Returns:
            ``True`` for ``PRE_OPEN``, ``AUCTION``, ``OPEN``, ``CLOSING``,
            and ``AFTER_HOURS``.
        """
        return self in (
            MarketState.PRE_OPEN,
            MarketState.AUCTION,
            MarketState.OPEN,
            MarketState.CLOSING,
            MarketState.AFTER_HOURS,
        )


class HaltReason(StrEnum):
    """Reason for a market halt or suspension.

    Attributes:
        INDEX_CIRCUIT_BREAKER: Market-wide halt triggered by index declining
            beyond a regulatory threshold (e.g. NIFTY drops 10%).
        STOCK_CIRCUIT_BREAKER: Single-instrument halt triggered by the
            instrument's price band being hit.
        REGULATORY:            Regulatory or exchange authority ordered halt
            (e.g. pending announcement, investigation).
        TECHNICAL:             Exchange system or connectivity failure
            preventing normal market operation.
        VOLATILITY:            Excessive volatility warranting a cooldown period.
        LIQUIDITY:             Insufficient liquidity to ensure fair price
            discovery.
        UNKNOWN:               Reason not yet determined or disclosed.
    """

    INDEX_CIRCUIT_BREAKER = "index_circuit_breaker"
    STOCK_CIRCUIT_BREAKER = "stock_circuit_breaker"
    REGULATORY = "regulatory"
    TECHNICAL = "technical"
    VOLATILITY = "volatility"
    LIQUIDITY = "liquidity"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class MarketStateSnapshot:
    """Point-in-time snapshot of a market's operational state.

    Attributes:
        exchange_id:       The exchange this snapshot describes.
        state:             Current operational state.
        as_of:             UTC timestamp when this snapshot was captured.
        segment_id:        Optional segment (``None`` = exchange-wide state).
        halt_reason:       When ``state`` is ``HALTED`` or ``SUSPENDED``,
            the reason for the halt. ``None`` otherwise.
        expected_resume_at: UTC timestamp when the market is expected to
            resume. ``None`` when unknown or not applicable.
        message:           Optional human-readable status message (e.g.
            "Circuit breaker activated — NIFTY declined >10%").

    Example::

        snapshot = MarketStateSnapshot(
            exchange_id=MarketId("NSE"),
            state=MarketState.OPEN,
            as_of=datetime(2025, 1, 15, 5, 30, tzinfo=UTC),
        )
    """

    exchange_id: MarketId
    state: MarketState
    as_of: datetime
    segment_id: MarketId | None = None
    halt_reason: HaltReason | None = None
    expected_resume_at: datetime | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None:
            from athena.market.exceptions import InvalidMarketStateError

            raise InvalidMarketStateError(
                "MarketStateSnapshot.as_of must be timezone-aware",
                from_state=None,
                to_state=self.state.value,
            )
        if self.halt_reason is not None and self.state not in (
            MarketState.HALTED,
            MarketState.SUSPENDED,
        ):
            from athena.market.exceptions import InvalidMarketStateError

            raise InvalidMarketStateError(
                f"halt_reason may only be set when state is HALTED or SUSPENDED "
                f"(got state={self.state.value})",
            )

    def __str__(self) -> str:
        scope = str(self.exchange_id)
        if self.segment_id:
            scope += f"/{self.segment_id}"
        return f"MarketStateSnapshot({scope}: {self.state.value})"


@dataclass(frozen=True)
class StateTransition:
    """An immutable record of a market state change.

    Attributes:
        exchange_id:  The exchange that changed state.
        from_state:   The state before the transition.
        to_state:     The state after the transition.
        occurred_at:  UTC timestamp of the transition.
        segment_id:   Optional segment scope.
        reason:       Human-readable reason for the transition.
        halt_reason:  Structured halt reason (for HALTED/SUSPENDED transitions).
    """

    exchange_id: MarketId
    from_state: MarketState
    to_state: MarketState
    occurred_at: datetime
    segment_id: MarketId | None = None
    reason: str | None = None
    halt_reason: HaltReason | None = None

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            from athena.market.exceptions import InvalidMarketStateError

            raise InvalidMarketStateError(
                "StateTransition.occurred_at must be timezone-aware",
            )


# ── Valid state transition graph ───────────────────────────────────────────────
#
# Each tuple (from, to) represents a permitted state machine edge.
# Any transition not in this set is illegal.

VALID_TRANSITIONS: frozenset[tuple[MarketState, MarketState]] = frozenset(
    {
        # From CLOSED
        (MarketState.CLOSED, MarketState.MAINTENANCE),
        (MarketState.CLOSED, MarketState.PRE_OPEN),
        # From MAINTENANCE
        (MarketState.MAINTENANCE, MarketState.CLOSED),
        (MarketState.MAINTENANCE, MarketState.PRE_OPEN),
        # From PRE_OPEN
        (MarketState.PRE_OPEN, MarketState.AUCTION),
        (MarketState.PRE_OPEN, MarketState.OPEN),
        (MarketState.PRE_OPEN, MarketState.HALTED),
        (MarketState.PRE_OPEN, MarketState.CLOSED),
        # From AUCTION
        (MarketState.AUCTION, MarketState.OPEN),
        (MarketState.AUCTION, MarketState.HALTED),
        (MarketState.AUCTION, MarketState.CLOSED),
        # From OPEN
        (MarketState.OPEN, MarketState.CLOSING),
        (MarketState.OPEN, MarketState.AFTER_HOURS),
        (MarketState.OPEN, MarketState.HALTED),
        (MarketState.OPEN, MarketState.SUSPENDED),
        (MarketState.OPEN, MarketState.CLOSED),
        # From CLOSING
        (MarketState.CLOSING, MarketState.AFTER_HOURS),
        (MarketState.CLOSING, MarketState.CLOSED),
        (MarketState.CLOSING, MarketState.HALTED),
        (MarketState.CLOSING, MarketState.AUCTION),
        # From AFTER_HOURS
        (MarketState.AFTER_HOURS, MarketState.CLOSED),
        (MarketState.AFTER_HOURS, MarketState.SUSPENDED),
        # From HALTED — resumes to state before halt or closes
        (MarketState.HALTED, MarketState.PRE_OPEN),
        (MarketState.HALTED, MarketState.OPEN),
        (MarketState.HALTED, MarketState.AUCTION),
        (MarketState.HALTED, MarketState.CLOSED),
        # From SUSPENDED
        (MarketState.SUSPENDED, MarketState.OPEN),
        (MarketState.SUSPENDED, MarketState.CLOSED),
        (MarketState.SUSPENDED, MarketState.HALTED),
    }
)


def is_valid_transition(from_state: MarketState, to_state: MarketState) -> bool:
    """Return ``True`` if transitioning from ``from_state`` to ``to_state`` is permitted.

    Identical states are trivially valid (no-op transitions are allowed).

    Args:
        from_state: The current market state.
        to_state:   The proposed target state.

    Returns:
        ``True`` when the transition is in ``VALID_TRANSITIONS`` or
        when ``from_state == to_state``.
    """
    if from_state == to_state:
        return True
    return (from_state, to_state) in VALID_TRANSITIONS


def validate_transition(
    from_state: MarketState,
    to_state: MarketState,
    context: str = "",
) -> None:
    """Assert that a state transition is valid, raising on illegal moves.

    Args:
        from_state: The current market state.
        to_state:   The proposed target state.
        context:    Optional description for error messages (e.g. exchange name).

    Raises:
        InvalidMarketStateError: If the transition is not in ``VALID_TRANSITIONS``.
    """
    if not is_valid_transition(from_state, to_state):
        prefix = f"[{context}] " if context else ""
        raise InvalidMarketStateError(
            f"{prefix}Illegal market state transition: {from_state.value!r} -> {to_state.value!r}",
            from_state=from_state.value,
            to_state=to_state.value,
        )
