"""Price adjustment value objects.

Separates the FACT of an adjustment (``AdjustmentFactor`` — what multiplier
was applied to a symbol on a given date, and why) from the RESULT of an
adjustment (``AdjustedPrice`` — the specific price that was produced after
applying the factor).

This separation matters because:
    - The factor is a property of the corporate action and methodology.
    - The result is a specific computation that depends on the original price.
    - Audit trails need both: "what was the factor?" and "what did we compute?"

The ``AdjustmentFactor.cumulative_from`` method computes the combined factor
for a sequence of adjustments, which is the standard approach in backward-
adjusted price series construction.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from athena.core.domain.primitives import Price, Symbol
from athena.market_data.exceptions import InvalidAdjustmentError

if TYPE_CHECKING:
    from datetime import date

    from athena.market_data.corporate_actions import CorporateActionType
    from athena.market_data.models import AdjustmentMethodology


@dataclass(frozen=True)
class AdjustmentFactor:
    """An adjustment factor applied to a symbol's historical price series.

    Attributes:
        symbol:             Instrument symbol.
        effective_date:     Date from which this adjustment applies.
            For BACKWARD methodology: all bars *before* this date are adjusted.
        price_factor:       Multiplicative factor for prices (e.g. 0.5 for a
            2:1 split means historical prices are halved). Must be > 0.
        volume_factor:      Multiplicative factor for volumes (e.g. 2.0 for a
            2:1 split means historical volumes are doubled). Must be > 0.
        methodology:        How the adjustment is applied (backward, forward).
        source_action_type: The corporate action type that generated this factor.
            ``None`` when the adjustment was manual or from an unknown source.
        notes:              Optional human-readable notes about this adjustment.

    Raises:
        InvalidAdjustmentError: If ``price_factor`` or ``volume_factor`` <= 0.

    Example::

        # Adjustment for a 2:1 split: halve historical prices, double volumes
        factor = AdjustmentFactor(
            symbol=Symbol("NSE:HDFCBANK"),
            effective_date=date(2025, 1, 20),
            price_factor=Decimal("0.5"),
            volume_factor=Decimal("2.0"),
            methodology=AdjustmentMethodology.BACKWARD,
            source_action_type=CorporateActionType.STOCK_SPLIT,
        )
    """

    symbol: Symbol
    effective_date: date
    price_factor: Decimal
    volume_factor: Decimal
    methodology: AdjustmentMethodology
    source_action_type: CorporateActionType | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.price_factor <= 0:
            raise InvalidAdjustmentError("price_factor", self.price_factor, "must be > 0")
        if self.volume_factor <= 0:
            raise InvalidAdjustmentError("volume_factor", self.volume_factor, "must be > 0")

    def is_identity(self) -> bool:
        """Return ``True`` when this factor has no net effect (both factors = 1).

        Returns:
            ``True`` when ``price_factor == 1`` and ``volume_factor == 1``.
        """
        return self.price_factor == Decimal("1") and self.volume_factor == Decimal("1")

    def inverse(self) -> AdjustmentFactor:
        """Return the inverse adjustment factor.

        Useful when converting between adjusted and unadjusted prices.

        Returns:
            A new ``AdjustmentFactor`` with ``1 / price_factor`` and
            ``1 / volume_factor``.
        """
        return AdjustmentFactor(
            symbol=self.symbol,
            effective_date=self.effective_date,
            price_factor=Decimal("1") / self.price_factor,
            volume_factor=Decimal("1") / self.volume_factor,
            methodology=self.methodology,
            source_action_type=self.source_action_type,
            notes=f"Inverse of: {self.notes}" if self.notes else "Inverse adjustment",
        )

    def __str__(self) -> str:
        return (
            f"AdjustmentFactor({self.symbol} "
            f"@{self.effective_date.isoformat()} "
            f"pricex{self.price_factor} volx{self.volume_factor} "
            f"[{self.methodology.value}])"
        )


@dataclass(frozen=True)
class AdjustedPrice:
    """The result of applying an adjustment factor to a single price.

    This is a computation result, not configuration. It captures both the
    original price and the adjusted price for full auditability.

    Attributes:
        original_price:    The unadjusted raw price.
        adjustment_factor: The factor that was applied.
        adjusted_price:    The resulting adjusted price.
        adjusted_for_date: The date the adjustment was applied relative to.
        methodology:       The methodology used (backward or forward).

    Raises:
        InvalidAdjustmentError: If ``original_price`` or ``adjusted_price`` <= 0.
    """

    original_price: Price
    adjustment_factor: Decimal
    adjusted_price: Price
    adjusted_for_date: date
    methodology: AdjustmentMethodology

    def __post_init__(self) -> None:
        if self.original_price <= 0:
            raise InvalidAdjustmentError("original_price", self.original_price, "must be > 0")
        if self.adjusted_price <= 0:
            raise InvalidAdjustmentError("adjusted_price", self.adjusted_price, "must be > 0")
        if self.adjustment_factor <= 0:
            raise InvalidAdjustmentError("adjustment_factor", self.adjustment_factor, "must be > 0")

    @property
    def price_change(self) -> Decimal:
        """Absolute change between original and adjusted price.

        Returns:
            ``adjusted_price - original_price`` (may be negative).
        """
        return Decimal(self.adjusted_price) - Decimal(self.original_price)

    def __str__(self) -> str:
        return (
            f"AdjustedPrice({self.original_price} -> {self.adjusted_price} "
            f"{self.adjustment_factor} [{self.methodology.value}])"
        )


def apply_adjustment(price: Price, factor: AdjustmentFactor) -> AdjustedPrice:
    """Apply an ``AdjustmentFactor`` to a single price and return the result.

    Args:
        price:  The unadjusted price to transform.
        factor: The adjustment factor to apply.

    Returns:
        An ``AdjustedPrice`` recording both the input and output.
    """
    adjusted = Price(Decimal(price) * factor.price_factor)
    return AdjustedPrice(
        original_price=price,
        adjustment_factor=factor.price_factor,
        adjusted_price=adjusted,
        adjusted_for_date=factor.effective_date,
        methodology=factor.methodology,
    )


def cumulative_price_factor(factors: tuple[AdjustmentFactor, ...]) -> Decimal:
    """Compute the combined price adjustment factor for a sequence of factors.

    Used when multiple corporate actions have occurred between two dates.
    The factors are multiplied together in the order provided.

    Args:
        factors: Sequence of adjustment factors, ordered by effective date.

    Returns:
        The product of all ``price_factor`` values. Returns ``Decimal("1")``
        for an empty sequence.
    """
    result = Decimal("1")
    for f in factors:
        result *= f.price_factor
    return result
