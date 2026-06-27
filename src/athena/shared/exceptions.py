"""Platform exception hierarchy.

All Athena-specific exceptions inherit from AthenaError. This allows callers
to catch all platform exceptions with a single except clause while still
being able to discriminate on subtype.

Design rule: exceptions carry context in their message. Never raise a bare
AthenaError("something went wrong") - always include what went wrong and why.
"""

from __future__ import annotations


class AthenaError(Exception):
    """Root exception for all Athena-specific errors."""


# ── Configuration ─────────────────────────────────────────────────────────────


class ConfigurationError(AthenaError):
    """Raised when required configuration is missing or invalid.

    The platform fails fast at startup on configuration errors rather than
    discovering them at runtime during trading hours.
    """


# ── Data ──────────────────────────────────────────────────────────────────────


class DataError(AthenaError):
    """Raised when market data is invalid, missing, or inconsistent."""


class InstrumentNotFoundError(DataError):
    """Raised when a symbol cannot be resolved in the instrument master."""

    def __init__(self, symbol: str) -> None:
        super().__init__(f"Instrument not found in master: {symbol!r}")
        self.symbol = symbol


class DataQualityError(DataError):
    """Raised when incoming market data fails quality validation."""


class StaleDataError(DataError):
    """Raised when the data feed has not produced updates within the staleness threshold."""


# ── Risk ──────────────────────────────────────────────────────────────────────


class RiskError(AthenaError):
    """Raised when a pre-trade or post-trade risk check fails.

    When this exception propagates from the pre-trade gate, the order
    must not be submitted. The Trading Engine treats this as a definitive
    rejection, not a transient failure.
    """


class PositionLimitBreachedError(RiskError):
    """Raised when an order would cause a position limit breach."""


class NotionalLimitBreachedError(RiskError):
    """Raised when an order would exceed the configured notional limit."""


class DrawdownLimitBreachedError(RiskError):
    """Raised when the intraday drawdown limit has been reached.

    When raised, automated trading must halt for the affected strategy
    until a human operator explicitly resets the limit.
    """


# ── Broker ────────────────────────────────────────────────────────────────────


class BrokerError(AthenaError):
    """Raised when broker communication fails or the broker rejects a request."""


class OrderSubmissionError(BrokerError):
    """Raised when an order cannot be submitted after all retries are exhausted."""


class OrderNotFoundError(BrokerError):
    """Raised when a broker order ID cannot be found."""

    def __init__(self, broker_order_id: str) -> None:
        super().__init__(f"Order not found at broker: {broker_order_id!r}")
        self.broker_order_id = broker_order_id


# ── Governance ────────────────────────────────────────────────────────────────


class ReconciliationError(AthenaError):
    """Raised when the internal position ledger diverges from the broker's state.

    Automated trading must halt and require human acknowledgement before resuming.
    """


class AuditError(AthenaError):
    """Raised when the audit trail cannot be written.

    This is a critical failure. The Governance Engine must alert immediately.
    """
