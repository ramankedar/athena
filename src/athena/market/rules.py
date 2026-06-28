"""Market rule configuration value objects and rule Protocols.

This module defines the SHAPE of market rules — the configuration that
describes what rules apply and at what thresholds. It deliberately does
NOT implement the rules themselves (i.e. "given current prices and volumes,
should the circuit breaker trigger?"). Rule evaluation belongs in a future
sprint's rule-engine service.

Two categories are defined:

1. **Configuration value objects** (frozen dataclasses):
   - ``PriceBandConfig``             — upper/lower price band settings
   - ``CircuitBreakerThreshold``     — a single circuit breaker trigger level
   - ``IndexCircuitBreakerConfig``   — multi-level index-wide circuit breaker
   - ``TradingRestriction``          — administrative restriction on trading

2. **Rule Protocols** (runtime-checkable):
   - ``PriceBandRuleProtocol``       — computes allowed price range
   - ``CircuitBreakerRuleProtocol``  — evaluates circuit breaker trigger

Design decision — restrictions are facts, rules are computations:
    A ``TradingRestriction`` is a data fact: "HDFCBANK is restricted from
    trading from 2025-01-15 due to an insider trading investigation."
    A ``PriceBandRuleProtocol`` is an executable: given a reference price,
    compute the allowed range. Mixing them would confuse static configuration
    with dynamic computation.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from athena.market.exceptions import InvalidMarketIdError
from athena.market.models import MarketId

if TYPE_CHECKING:
    from datetime import date


class PriceBandType(StrEnum):
    """How price band limits are determined for an instrument.

    Attributes:
        STATIC:  Fixed upper and lower percentage limits around a reference
            price (e.g. ±20% of yesterday's close for most equities).
        DYNAMIC: Limits computed from intraday volatility or real-time
            reference prices (e.g. ±0.5% of the last traded price for index
            futures in some regimes).
        NONE:    No price band applies (e.g. derivatives in their first
            trading session, or certain institutional markets).
    """

    STATIC = "static"
    DYNAMIC = "dynamic"
    NONE = "none"


class CircuitBreakerLevel(StrEnum):
    """Severity level for a market-wide index circuit breaker.

    NSE/SEBI uses three levels triggered by NIFTY 50 or SENSEX decline:
        LEVEL_1: 10% decline → 45-minute halt (before 13:00) or 15-minute halt (13:00-14:30)
        LEVEL_2: 15% decline → 1 hr 45 min halt (before 13:00) or 45-minute halt
        LEVEL_3: 20% decline → remainder of trading day halted

    Attributes:
        LEVEL_1: First (least severe) circuit breaker level.
        LEVEL_2: Second (moderate) circuit breaker level.
        LEVEL_3: Third (most severe) circuit breaker level.
    """

    LEVEL_1 = "level_1"
    LEVEL_2 = "level_2"
    LEVEL_3 = "level_3"


class RestrictionType(StrEnum):
    """Classification of a trading restriction.

    Attributes:
        TRADING_BAN:         Security is completely banned from trading.
        PRICE_BAND_MODIFIED: Standard price band replaced with a tighter
            or wider band (e.g. following a large corporate event).
        SHORT_SELL_BAN:      Short selling disallowed for this instrument.
        INSIDER_RESTRICTION: Restricted period (e.g. ahead of earnings).
        CIRCUIT_FILTER:      Instrument-specific circuit filter applied.
        OTHER:               Any other type of trading restriction.
    """

    TRADING_BAN = "trading_ban"
    PRICE_BAND_MODIFIED = "price_band_modified"
    SHORT_SELL_BAN = "short_sell_ban"
    INSIDER_RESTRICTION = "insider_restriction"
    CIRCUIT_FILTER = "circuit_filter"
    OTHER = "other"


@dataclass(frozen=True)
class PriceBandConfig:
    """Configuration for price band limits on an instrument or market segment.

    Attributes:
        band_type:             How price limits are computed.
        upper_limit_pct:       Maximum allowed upward price move as a percentage
            (e.g. ``Decimal("20")`` for 20%). ``None`` when no upper limit.
        lower_limit_pct:       Maximum allowed downward price move as a percentage.
            ``None`` when no lower limit.
        reference_price_field: Name of the price field used as reference
            (e.g. ``"previous_close"``, ``"base_price"``, ``"last_traded_price"``).
            This is a label, not a computed value.

    Raises:
        InvalidMarketIdError: If ``band_type != NONE`` but both limits are ``None``.

    Example::

        equity_band = PriceBandConfig(
            band_type=PriceBandType.STATIC,
            upper_limit_pct=Decimal("20"),
            lower_limit_pct=Decimal("20"),
            reference_price_field="previous_close",
        )
    """

    band_type: PriceBandType
    upper_limit_pct: Decimal | None = None
    lower_limit_pct: Decimal | None = None
    reference_price_field: str = "previous_close"

    def __post_init__(self) -> None:
        if (
            self.band_type != PriceBandType.NONE
            and self.upper_limit_pct is None
            and self.lower_limit_pct is None
        ):
            raise InvalidMarketIdError(
                self.band_type.value,
                reason=(
                    "PriceBandConfig requires at least one of upper_limit_pct or "
                    "lower_limit_pct when band_type is not NONE"
                ),
            )
        for name, val in (
            ("upper_limit_pct", self.upper_limit_pct),
            ("lower_limit_pct", self.lower_limit_pct),
        ):
            if val is not None and val <= Decimal(0):
                raise InvalidMarketIdError(
                    self.band_type.value,
                    reason=f"{name} must be positive when provided (got {val})",
                )

    @property
    def is_symmetric(self) -> bool:
        """Return ``True`` when upper and lower limits are equal.

        Returns:
            ``True`` when both limits are set and identical.
        """
        return (
            self.upper_limit_pct is not None
            and self.lower_limit_pct is not None
            and self.upper_limit_pct == self.lower_limit_pct
        )


@dataclass(frozen=True)
class CircuitBreakerThreshold:
    """A single trigger level within a multi-level circuit breaker.

    Attributes:
        level:                    Severity classification.
        trigger_decline_pct:      Percentage decline from the reference value
            that activates this threshold (e.g. ``Decimal("10")`` for 10%).
        halt_duration_minutes:    Minutes the market halts after this level
            triggers. ``None`` means "halt for the rest of the trading day."

    Example::

        level_1 = CircuitBreakerThreshold(
            level=CircuitBreakerLevel.LEVEL_1,
            trigger_decline_pct=Decimal("10"),
            halt_duration_minutes=45,
        )
    """

    level: CircuitBreakerLevel
    trigger_decline_pct: Decimal
    halt_duration_minutes: int | None

    def __post_init__(self) -> None:
        if self.trigger_decline_pct <= Decimal(0):
            raise InvalidMarketIdError(
                self.level.value,
                reason=f"trigger_decline_pct must be > 0 (got {self.trigger_decline_pct})",
            )
        if self.halt_duration_minutes is not None and self.halt_duration_minutes < 1:
            raise InvalidMarketIdError(
                self.level.value,
                reason=(
                    f"halt_duration_minutes must be >= 1 when provided "
                    f"(got {self.halt_duration_minutes})"
                ),
            )

    @property
    def halts_for_day(self) -> bool:
        """Return ``True`` if this threshold triggers a rest-of-day halt.

        Returns:
            ``True`` when ``halt_duration_minutes`` is ``None``.
        """
        return self.halt_duration_minutes is None


@dataclass(frozen=True)
class IndexCircuitBreakerConfig:
    """Multi-level index-wide circuit breaker configuration.

    Defines the thresholds at which the entire market (or a segment) halts
    when a reference index declines by specified percentages.

    Attributes:
        exchange_id:        The exchange this configuration applies to.
        reference_index_id: The index whose decline triggers the breaker
            (e.g. ``MarketId("NIFTY50")`` for NSE, ``MarketId("SENSEX")`` for BSE).
        thresholds:         Ordered tuple of circuit breaker threshold levels.
            Must contain at least one threshold.

    Example (SEBI NSE circuit breaker rules)::

        nse_cb = IndexCircuitBreakerConfig(
            exchange_id=MarketId("NSE"),
            reference_index_id=MarketId("NIFTY50"),
            thresholds=(
                CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_1, Decimal("10"), 45),
                CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_2, Decimal("15"), 105),
                CircuitBreakerThreshold(CircuitBreakerLevel.LEVEL_3, Decimal("20"), None),
            ),
        )
    """

    exchange_id: MarketId
    reference_index_id: MarketId
    thresholds: tuple[CircuitBreakerThreshold, ...]

    def __post_init__(self) -> None:
        if not self.thresholds:
            raise InvalidMarketIdError(
                str(self.exchange_id),
                reason="IndexCircuitBreakerConfig.thresholds must not be empty",
            )
        # Verify thresholds are in ascending order by trigger percentage
        for i in range(len(self.thresholds) - 1):
            if self.thresholds[i].trigger_decline_pct >= self.thresholds[i + 1].trigger_decline_pct:
                raise InvalidMarketIdError(
                    str(self.exchange_id),
                    reason=(
                        "Circuit breaker thresholds must be in ascending order "
                        "by trigger_decline_pct"
                    ),
                )

    def threshold_for_level(self, level: CircuitBreakerLevel) -> CircuitBreakerThreshold | None:
        """Return the threshold for the given level, or ``None`` if not configured.

        Args:
            level: The circuit breaker level to look up.

        Returns:
            The matching ``CircuitBreakerThreshold``, or ``None``.
        """
        for threshold in self.thresholds:
            if threshold.level == level:
                return threshold
        return None


@dataclass(frozen=True)
class TradingRestriction:
    """An administrative restriction limiting trading of an instrument or market.

    A restriction is a data fact (not a rule) — it records that some authority
    has imposed a trading limitation with a defined scope and time period.

    Attributes:
        restriction_id:  Unique identifier for this restriction record.
        exchange_id:     Exchange where the restriction applies.
        restriction_type: Classification of the restriction.
        reason:          Human-readable reason (regulatory notification, etc.).
        effective_date:  First date the restriction is in effect.
        segment_id:      Optional segment scope (``None`` = exchange-wide).
        instrument_symbol: Optional specific instrument symbol affected
            (``None`` = all instruments in scope).
        expiry_date:     Last date of the restriction. ``None`` = indefinite.

    Example::

        restriction = TradingRestriction(
            restriction_id="SEBI-2025-0042",
            exchange_id=MarketId("NSE"),
            restriction_type=RestrictionType.TRADING_BAN,
            reason="SEBI order pending investigation",
            effective_date=date(2025, 1, 15),
        )
    """

    restriction_id: str
    exchange_id: MarketId
    restriction_type: RestrictionType
    reason: str
    effective_date: date
    segment_id: MarketId | None = None
    instrument_symbol: str | None = None
    expiry_date: date | None = None

    def __post_init__(self) -> None:
        if not self.restriction_id.strip():
            raise InvalidMarketIdError(
                str(self.exchange_id),
                reason="TradingRestriction.restriction_id must not be empty",
            )
        if not self.reason.strip():
            raise InvalidMarketIdError(
                str(self.exchange_id),
                reason="TradingRestriction.reason must not be empty",
            )
        if self.expiry_date is not None and self.expiry_date < self.effective_date:
            raise InvalidMarketIdError(
                str(self.exchange_id),
                reason=(
                    f"expiry_date ({self.expiry_date}) must be >= "
                    f"effective_date ({self.effective_date})"
                ),
            )

    def is_active_on(self, d: date) -> bool:
        """Return ``True`` if the restriction is active on date ``d``.

        Args:
            d: The date to check.

        Returns:
            ``True`` when ``effective_date <= d`` and (``expiry_date is None``
            or ``d <= expiry_date``).
        """
        if d < self.effective_date:
            return False
        return self.expiry_date is None or d <= self.expiry_date


# ── Rule Protocols ─────────────────────────────────────────────────────────────


@runtime_checkable
class PriceBandRuleProtocol(Protocol):
    """Protocol for a rule that computes allowed price ranges.

    Implementations receive a reference price and return the upper and lower
    bounds of the allowed range. The config driving the computation is
    provided at rule construction time (not at call time).
    """

    def compute_upper_band(self, reference_price: Decimal) -> Decimal | None:
        """Compute the maximum allowed price given a reference price.

        Args:
            reference_price: The base price for band calculation.

        Returns:
            Upper price limit, or ``None`` if no upper limit applies.
        """
        ...

    def compute_lower_band(self, reference_price: Decimal) -> Decimal | None:
        """Compute the minimum allowed price given a reference price.

        Args:
            reference_price: The base price for band calculation.

        Returns:
            Lower price limit, or ``None`` if no lower limit applies.
        """
        ...

    def is_within_band(self, price: Decimal, reference_price: Decimal) -> bool:
        """Return ``True`` if ``price`` is within the computed band.

        Args:
            price:           The price to validate.
            reference_price: The base price for band calculation.

        Returns:
            ``True`` when ``price`` falls within the band defined by
            ``compute_lower_band`` and ``compute_upper_band``.
        """
        ...


@runtime_checkable
class CircuitBreakerRuleProtocol(Protocol):
    """Protocol for a rule that evaluates circuit breaker triggers.

    Implementations receive current and reference index values and determine
    whether a circuit breaker has been triggered and, if so, how long the
    resulting halt should be.
    """

    def is_triggered(self, current_value: Decimal, reference_value: Decimal) -> bool:
        """Return ``True`` if the circuit breaker condition is met.

        Args:
            current_value:   The current index level.
            reference_value: The reference (opening or previous close) level.

        Returns:
            ``True`` when the decline exceeds the trigger threshold.
        """
        ...

    def get_halt_duration_minutes(
        self, current_value: Decimal, reference_value: Decimal
    ) -> int | None:
        """Return the halt duration in minutes for the triggered level.

        Args:
            current_value:   The current index level.
            reference_value: The reference level.

        Returns:
            Minutes to halt trading, or ``None`` for a rest-of-day halt.
            Returns ``0`` (or a negative value) when no circuit breaker
            is triggered.
        """
        ...


# ── Named constant: SEBI NSE index circuit breaker (informational) ────────────

#: SEBI-mandated NSE index circuit breaker configuration (NIFTY 50 / SENSEX).
#: Source: SEBI circular dated 2013-06-28, revised 2016.
SEBI_NSE_CIRCUIT_BREAKER: IndexCircuitBreakerConfig = IndexCircuitBreakerConfig(
    exchange_id=MarketId("NSE"),
    reference_index_id=MarketId("NIFTY50"),
    thresholds=(
        CircuitBreakerThreshold(
            level=CircuitBreakerLevel.LEVEL_1,
            trigger_decline_pct=Decimal("10"),
            halt_duration_minutes=45,
        ),
        CircuitBreakerThreshold(
            level=CircuitBreakerLevel.LEVEL_2,
            trigger_decline_pct=Decimal("15"),
            halt_duration_minutes=105,
        ),
        CircuitBreakerThreshold(
            level=CircuitBreakerLevel.LEVEL_3,
            trigger_decline_pct=Decimal("20"),
            halt_duration_minutes=None,  # rest of day
        ),
    ),
)
