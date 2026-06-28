"""Market-domain exception hierarchy.

All market exceptions inherit from ``MarketError``, which inherits from
``AthenaError``. This allows callers to catch all market-domain failures
with a single clause while discriminating on subtype for specific handling.

Hierarchy::

    AthenaError
    └── MarketError
        ├── InvalidMarketIdError        — malformed market or segment identifier
        ├── ExchangeNotFoundError       — exchange not registered
        ├── SegmentNotFoundError        — trading segment not found
        ├── InvalidMarketStateError     — invalid state or illegal transition
        ├── InvalidScheduleError        — schedule fails consistency constraints
        ├── MarketHaltedError           — operation attempted while market is halted
        └── UnsupportedCapabilityError  — exchange does not support the operation
"""

from __future__ import annotations

from athena.platform.exceptions import AthenaError


class MarketError(AthenaError):
    """Root exception for all market-domain errors.

    Args:
        message: Human-readable description of the problem.
        error_code: Optional machine-readable code (prefix: ``MKT``).
        **context: Diagnostic key-value pairs.
    """


class InvalidMarketIdError(MarketError):
    """Raised when a ``MarketId`` or related identifier fails format validation.

    Args:
        identifier: The raw string that failed validation.
        reason: Human-readable explanation of the failure.
        **context: Additional diagnostic context.
    """

    def __init__(self, identifier: str, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid market identifier {identifier!r}: {reason}",
            error_code="MKT_001",
            identifier=identifier,
            reason=reason,
            **context,
        )
        self.identifier = identifier
        self.reason = reason


class ExchangeNotFoundError(MarketError):
    """Raised when an exchange lookup finds no registered exchange.

    Args:
        exchange_id: The identifier that was not found.
        **context: Additional diagnostic context.
    """

    def __init__(self, exchange_id: str, **context: object) -> None:
        super().__init__(
            f"Exchange not found: {exchange_id!r}",
            error_code="MKT_002",
            exchange_id=exchange_id,
            **context,
        )
        self.exchange_id = exchange_id


class SegmentNotFoundError(MarketError):
    """Raised when a market segment lookup finds no matching segment.

    Args:
        segment_id: The segment identifier that was not found.
        exchange_id: Optional exchange the segment was expected on.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        segment_id: str,
        exchange_id: str | None = None,
        **context: object,
    ) -> None:
        detail = f" on exchange {exchange_id!r}" if exchange_id else ""
        super().__init__(
            f"Market segment not found: {segment_id!r}{detail}",
            error_code="MKT_003",
            segment_id=segment_id,
            exchange_id=exchange_id,
            **context,
        )
        self.segment_id = segment_id
        self.exchange_id = exchange_id


class InvalidMarketStateError(MarketError):
    """Raised when a market state transition is illegal or a state is invalid.

    Args:
        message: Description of the state problem.
        from_state: Optional current state at the time of the error.
        to_state: Optional target state that was rejected.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        message: str,
        from_state: str | None = None,
        to_state: str | None = None,
        **context: object,
    ) -> None:
        super().__init__(
            message,
            error_code="MKT_004",
            from_state=from_state,
            to_state=to_state,
            **context,
        )
        self.from_state = from_state
        self.to_state = to_state


class InvalidScheduleError(MarketError):
    """Raised when a session schedule fails consistency or ordering constraints.

    Examples include sessions that overlap, a daily schedule with end_time
    before start_time, or a weekly schedule with invalid weekday integers.

    Args:
        message: Description of the constraint violation.
        **context: Additional diagnostic context.
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message, error_code="MKT_005", **context)


class MarketHaltedError(MarketError):
    """Raised when an operation is attempted while the market is halted.

    Args:
        exchange_id: The exchange that is currently halted.
        segment_id: Optional segment that is halted.
        halt_reason: Human-readable reason for the halt.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        exchange_id: str,
        segment_id: str | None = None,
        halt_reason: str = "unspecified",
        **context: object,
    ) -> None:
        scope = f"{exchange_id}" + (f"/{segment_id}" if segment_id else "")
        super().__init__(
            f"Market {scope!r} is currently halted: {halt_reason}",
            error_code="MKT_006",
            exchange_id=exchange_id,
            segment_id=segment_id,
            halt_reason=halt_reason,
            **context,
        )
        self.exchange_id = exchange_id
        self.segment_id = segment_id
        self.halt_reason = halt_reason


class UnsupportedCapabilityError(MarketError):
    """Raised when a requested capability is not supported by the exchange or segment.

    Args:
        capability: Name of the unsupported capability.
        exchange_id: The exchange that does not support it.
        segment_id: Optional segment context.
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        capability: str,
        exchange_id: str,
        segment_id: str | None = None,
        **context: object,
    ) -> None:
        scope = exchange_id + (f"/{segment_id}" if segment_id else "")
        super().__init__(
            f"Capability {capability!r} is not supported on {scope}",
            error_code="MKT_007",
            capability=capability,
            exchange_id=exchange_id,
            segment_id=segment_id,
            **context,
        )
        self.capability = capability
        self.exchange_id = exchange_id
        self.segment_id = segment_id
