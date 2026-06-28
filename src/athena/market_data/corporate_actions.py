"""Corporate action value objects.

Corporate actions alter the number of shares outstanding, the price of
individual shares, or both. Historical price series must be adjusted to
account for these events to avoid artificial discontinuities in charts and
quantitative models.

``CorporateAction`` is an immutable record of a single corporate event. It
uses separate ``ratio_numerator`` and ``ratio_denominator`` fields rather than
a single ``factor`` to avoid sign-convention ambiguity: a 2:1 split has
``numerator=2, denominator=1``; a 1:2 reverse split has ``numerator=1,
denominator=2``. The derived ``split_factor`` property computes the actual
price adjustment multiplier (denominator / numerator).

Indian market note:
    BONUS_ISSUE is common in Indian markets (BSE/NSE). A 1:1 bonus issue
    means each holder receives 1 new share for each share held (similar to
    a 2:1 stock split but via capitalization of reserves).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from athena.market_data.exceptions import InvalidBarError

if TYPE_CHECKING:
    from datetime import date

    from athena.core.domain.primitives import Symbol


class CorporateActionType(StrEnum):
    """Classification of a corporate action event.

    Attributes:
        CASH_DIVIDEND:    Regular cash dividend payment to shareholders.
        SPECIAL_DIVIDEND: One-time (non-recurring) cash dividend.
        STOCK_DIVIDEND:   Dividend paid in additional shares.
        STOCK_SPLIT:      Increase in share count with proportional price
            reduction (e.g. 2:1 split doubles shares, halves price).
        REVERSE_SPLIT:    Decrease in share count with proportional price
            increase (e.g. 1:2 reverse halves shares, doubles price).
        BONUS_ISSUE:      Additional shares issued free to existing holders
            from company reserves (Indian market convention).
        RIGHTS_ISSUE:     Existing holders offered new shares at a discount.
        MERGER:           Company absorbed into another.
        DEMERGER:         Business unit separated into a new company.
        SPINOFF:          Subsidiary separated and listed independently.
        BUYBACK:          Company repurchases its own shares.
        NAME_CHANGE:      Symbol or company name change (no price impact).
        EXCHANGE_CHANGE:  Instrument moved to a different exchange or segment.
    """

    CASH_DIVIDEND = "cash_dividend"
    SPECIAL_DIVIDEND = "special_dividend"
    STOCK_DIVIDEND = "stock_dividend"
    STOCK_SPLIT = "stock_split"
    REVERSE_SPLIT = "reverse_split"
    BONUS_ISSUE = "bonus_issue"
    RIGHTS_ISSUE = "rights_issue"
    MERGER = "merger"
    DEMERGER = "demerger"
    SPINOFF = "spinoff"
    BUYBACK = "buyback"
    NAME_CHANGE = "name_change"
    EXCHANGE_CHANGE = "exchange_change"


@dataclass(frozen=True)
class CorporateAction:
    """An immutable record of a single corporate action event.

    Attributes:
        symbol:              Instrument symbol affected.
        action_type:         Classification of the corporate event.
        announcement_date:   Date the action was publicly announced.
        ex_date:             Ex-dividend / ex-rights date. Shares purchased
            on or after this date do not qualify for the action.
        record_date:         Date shareholders must be on record to receive
            the action. ``None`` when not applicable or unknown.
        effective_date:      Date the action takes effect for pricing. ``None``
            when not applicable.
        pay_date:            Date the dividend or other cash is paid. ``None``
            for non-cash actions.
        ratio_numerator:     New share count in the split ratio (e.g. 2 for 2:1).
            ``None`` for non-split/bonus actions.
        ratio_denominator:   Old share count in the split ratio (e.g. 1 for 2:1).
            ``None`` for non-split/bonus actions.
        amount:              Cash amount per share for dividend actions.
            ``None`` for non-cash actions.
        currency:            Currency of ``amount``. ``None`` when ``amount``
            is not applicable.
        description:         Human-readable description of the event.
        source:              Data vendor that provided this corporate action
            record (e.g. ``"nse_corporate_actions"``, ``"bse_direct"``).

    Raises:
        InvalidBarError: If both ratio fields are provided but either is <= 0.

    Example::

        # 2:1 stock split — each share becomes 2 shares, price halves
        split = CorporateAction(
            symbol=Symbol("NSE:HDFCBANK"),
            action_type=CorporateActionType.STOCK_SPLIT,
            announcement_date=date(2025, 1, 10),
            ex_date=date(2025, 1, 20),
            ratio_numerator=Decimal("2"),
            ratio_denominator=Decimal("1"),
        )
        assert split.split_factor == Decimal("0.5")  # prices halved
    """

    symbol: Symbol
    action_type: CorporateActionType
    announcement_date: date
    ex_date: date
    record_date: date | None = None
    effective_date: date | None = None
    pay_date: date | None = None
    ratio_numerator: Decimal | None = None
    ratio_denominator: Decimal | None = None
    amount: Decimal | None = None
    currency: str | None = None
    description: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        if self.ratio_numerator is not None and self.ratio_numerator <= 0:
            raise InvalidBarError("ratio_numerator", self.ratio_numerator, "must be > 0")
        if self.ratio_denominator is not None and self.ratio_denominator <= 0:
            raise InvalidBarError("ratio_denominator", self.ratio_denominator, "must be > 0")
        if self.amount is not None and self.amount < 0:
            raise InvalidBarError("amount", self.amount, "must be >= 0")

    @property
    def split_factor(self) -> Decimal | None:
        """Price adjustment multiplier for split/bonus actions.

        The split factor is ``denominator / numerator``. For a 2:1 split:
        each share becomes 2 shares, so the price is halved. Factor = 1/2 = 0.5.

        Returns:
            ``Decimal(ratio_denominator / ratio_numerator)`` or ``None``
            when either ratio field is not set.
        """
        if self.ratio_numerator is not None and self.ratio_denominator is not None:
            return Decimal(self.ratio_denominator) / Decimal(self.ratio_numerator)
        return None

    @property
    def volume_factor(self) -> Decimal | None:
        """Volume adjustment multiplier for split/bonus actions.

        The volume factor is ``numerator / denominator`` (inverse of price
        factor). For a 2:1 split, volume is doubled. Factor = 2/1 = 2.0.

        Returns:
            ``Decimal(ratio_numerator / ratio_denominator)`` or ``None``
            when either ratio field is not set.
        """
        if self.ratio_numerator is not None and self.ratio_denominator is not None:
            return Decimal(self.ratio_numerator) / Decimal(self.ratio_denominator)
        return None

    @property
    def affects_price(self) -> bool:
        """Return ``True`` when this action requires price series adjustment.

        Returns:
            ``True`` for STOCK_SPLIT, REVERSE_SPLIT, BONUS_ISSUE,
            STOCK_DIVIDEND, CASH_DIVIDEND, and SPECIAL_DIVIDEND.
        """
        return self.action_type in (
            CorporateActionType.STOCK_SPLIT,
            CorporateActionType.REVERSE_SPLIT,
            CorporateActionType.BONUS_ISSUE,
            CorporateActionType.STOCK_DIVIDEND,
            CorporateActionType.CASH_DIVIDEND,
            CorporateActionType.SPECIAL_DIVIDEND,
        )

    def __str__(self) -> str:
        return (
            f"CorporateAction({self.symbol} {self.action_type.value} ex={self.ex_date.isoformat()})"
        )
