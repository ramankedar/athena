"""Market domain validation utilities.

Returns ``ValidationResult`` (structured result with failure messages) rather
than raising immediately. This allows callers to collect all validation errors
in a single pass — useful when loading market configuration at startup and
wanting to report all issues before halting.

Note on ``ValidationResult`` duplication:
    ``ValidationResult`` is also defined in ``athena.assets.validation``.
    The two are structurally identical but independent. Since ``athena.market``
    and ``athena.assets`` are peer layers, neither may import from the other.
    Each bounded context defines its own value types.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.market.capabilities import MarketCapabilities, OrderCapabilities
    from athena.market.exchange import ExchangeMetadata
    from athena.market.rules import (
        CircuitBreakerThreshold,
        IndexCircuitBreakerConfig,
        PriceBandConfig,
    )
    from athena.market.sessions import DailySchedule, SessionWindow


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a market domain validation pass.

    Attributes:
        is_valid: ``True`` when no failures were found.
        failures: Tuple of human-readable failure descriptions. Empty when valid.

    Example::

        result = validate_exchange_metadata(metadata)
        if not result.is_valid:
            for msg in result.failures:
                log.warning("market.config.invalid", message=msg)
    """

    is_valid: bool
    failures: tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> ValidationResult:
        """Return a result indicating no validation failures.

        Returns:
            A ``ValidationResult`` with ``is_valid=True``.
        """
        return cls(is_valid=True)

    @classmethod
    def failed(cls, *messages: str) -> ValidationResult:
        """Return a result indicating one or more failures.

        Args:
            *messages: One or more failure descriptions.

        Returns:
            A ``ValidationResult`` with ``is_valid=False``.
        """
        return cls(is_valid=False, failures=tuple(messages))

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Combine two results. Invalid if either input is invalid.

        Args:
            other: The other result to merge.

        Returns:
            A new ``ValidationResult`` combining both failure sets.
        """
        combined = self.failures + other.failures
        return ValidationResult(is_valid=len(combined) == 0, failures=combined)


# ── Domain validators ──────────────────────────────────────────────────────────


def validate_exchange_metadata(metadata: ExchangeMetadata) -> ValidationResult:
    """Validate ``ExchangeMetadata`` for completeness and consistency.

    Args:
        metadata: The exchange metadata to validate.

    Returns:
        A ``ValidationResult`` — valid when no rules are violated.
    """
    failures: list[str] = []

    if not metadata.name.strip():
        failures.append(f"Exchange {metadata.id!s}: name must not be empty")
    if not metadata.short_name.strip():
        failures.append(f"Exchange {metadata.id!s}: short_name must not be empty")
    if not metadata.regulator.strip():
        failures.append(f"Exchange {metadata.id!s}: regulator must not be empty")
    if metadata.established_year is not None and metadata.established_year < 1600:
        failures.append(
            f"Exchange {metadata.id!s}: established_year {metadata.established_year} "
            "is implausibly early"
        )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_session_window(window: SessionWindow) -> ValidationResult:
    """Validate a single ``SessionWindow``.

    Args:
        window: The session window to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if window.start_time >= window.end_time:
        failures.append(
            f"SessionWindow [{window.session_type.value}]: "
            f"start_time ({window.start_time}) must be before end_time ({window.end_time})"
        )
    if window.duration_minutes < 1:
        failures.append(
            f"SessionWindow [{window.session_type.value}]: "
            f"duration must be at least 1 minute (got {window.duration_minutes})"
        )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_daily_schedule(schedule: DailySchedule) -> ValidationResult:
    """Validate a ``DailySchedule`` for ordering and non-overlap.

    Args:
        schedule: The daily schedule to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not schedule.sessions:
        failures.append("DailySchedule must contain at least one session window")
        return ValidationResult.failed(*failures)

    # Validate each window
    for window in schedule.sessions:
        window_result = validate_session_window(window)
        if not window_result.is_valid:
            failures.extend(window_result.failures)

    # Validate ordering and non-overlap
    for i in range(len(schedule.sessions) - 1):
        current = schedule.sessions[i]
        following = schedule.sessions[i + 1]
        if current.end_time > following.start_time:
            failures.append(
                f"Session windows overlap: {current.session_type.value} ends at "
                f"{current.end_time} but {following.session_type.value} starts at "
                f"{following.start_time}"
            )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_price_band_config(config: PriceBandConfig) -> ValidationResult:
    """Validate a ``PriceBandConfig`` value object.

    Args:
        config: The price band configuration to validate.

    Returns:
        A ``ValidationResult``.
    """
    from athena.market.rules import PriceBandType

    failures: list[str] = []

    if config.band_type != PriceBandType.NONE:
        if config.upper_limit_pct is None and config.lower_limit_pct is None:
            failures.append(
                "PriceBandConfig: at least one of upper_limit_pct or lower_limit_pct "
                "must be set when band_type is not NONE"
            )
        for name, val in (
            ("upper_limit_pct", config.upper_limit_pct),
            ("lower_limit_pct", config.lower_limit_pct),
        ):
            if val is not None and val <= Decimal(0):
                failures.append(f"PriceBandConfig.{name} must be > 0 when provided (got {val})")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_circuit_breaker_config(config: IndexCircuitBreakerConfig) -> ValidationResult:
    """Validate an ``IndexCircuitBreakerConfig``.

    Args:
        config: The circuit breaker configuration to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not config.thresholds:
        failures.append(
            f"IndexCircuitBreakerConfig for {config.exchange_id!s}: thresholds must not be empty"
        )
        return ValidationResult.failed(*failures)

    # Validate each threshold
    for threshold in config.thresholds:
        result = validate_circuit_breaker_threshold(threshold)
        if not result.is_valid:
            failures.extend(result.failures)

    # Validate thresholds are in ascending order
    failures.extend(
        "Circuit breaker thresholds must be in ascending order by trigger_decline_pct"
        for i in range(len(config.thresholds) - 1)
        if config.thresholds[i].trigger_decline_pct >= config.thresholds[i + 1].trigger_decline_pct
    )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_circuit_breaker_threshold(threshold: CircuitBreakerThreshold) -> ValidationResult:
    """Validate a single ``CircuitBreakerThreshold``.

    Args:
        threshold: The threshold to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if threshold.trigger_decline_pct <= Decimal(0):
        failures.append(
            f"CircuitBreakerThreshold [{threshold.level.value}]: "
            f"trigger_decline_pct must be > 0 (got {threshold.trigger_decline_pct})"
        )
    if threshold.halt_duration_minutes is not None and threshold.halt_duration_minutes < 1:
        failures.append(
            f"CircuitBreakerThreshold [{threshold.level.value}]: "
            f"halt_duration_minutes must be >= 1 when set (got {threshold.halt_duration_minutes})"
        )

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_market_capabilities(capabilities: MarketCapabilities) -> ValidationResult:
    """Validate ``MarketCapabilities`` for internal consistency.

    Args:
        capabilities: The capabilities to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not capabilities.supported_asset_classes:
        failures.append(
            f"MarketCapabilities for {capabilities.exchange_id!s}: "
            "supported_asset_classes must not be empty"
        )

    # Validate order capabilities
    order_result = validate_order_capabilities(capabilities.order_capabilities)
    if not order_result.is_valid:
        failures.extend(order_result.failures)

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_order_capabilities(caps: OrderCapabilities) -> ValidationResult:
    """Validate ``OrderCapabilities`` for internal consistency.

    Args:
        caps: The order capabilities to validate.

    Returns:
        A ``ValidationResult``.
    """
    failures: list[str] = []

    if not caps.supported_order_types:
        failures.append("OrderCapabilities.supported_order_types must not be empty")

    if caps.default_order_type not in caps.supported_order_types:
        failures.append(
            f"OrderCapabilities.default_order_type {caps.default_order_type.value!r} "
            "is not in supported_order_types"
        )

    if (
        caps.max_order_value is not None
        and caps.min_order_value is not None
        and caps.max_order_value < caps.min_order_value
    ):
        failures.append("OrderCapabilities: max_order_value must be >= min_order_value")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)
