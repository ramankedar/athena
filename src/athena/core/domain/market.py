"""Market session domain model.

Indian equity and derivative markets operate on fixed IST sessions.
The SessionType enum captures every distinct phase of the NSE/BSE trading day.

All timestamps in the platform are timezone-aware UTC internally. IST
(UTC+5:30) conversion happens only at the presentation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class SessionType(StrEnum):
    """Phases of the NSE/BSE trading day."""

    PRE_OPEN = "pre_open"  # 09:00-09:08 IST: order collection
    PRE_OPEN_MATCHING = "pre_open_matching"  # 09:08-09:15 IST: price discovery
    NORMAL = "normal"  # 09:15-15:30 IST: continuous trading
    CLOSING = "closing"  # 15:30-15:40 IST: closing price calculation
    POST_CLOSE = "post_close"  # 15:40-16:00 IST: after-hours session (BSE)
    CLOSED = "closed"  # Outside all above windows


@dataclass(frozen=True)
class MarketSession:
    """A specific trading session instance with its start and end timestamps.

    Timestamps are UTC. Both bounds are inclusive.
    """

    session_type: SessionType
    opens_at_utc: datetime
    closes_at_utc: datetime

    def __post_init__(self) -> None:
        if self.opens_at_utc >= self.closes_at_utc:
            raise ValueError(
                f"Session opens_at must be before closes_at: "
                f"{self.opens_at_utc} >= {self.closes_at_utc}"
            )

    def is_active(self, at: datetime) -> bool:
        """Return True if `at` falls within this session (inclusive bounds)."""
        return self.opens_at_utc <= at <= self.closes_at_utc
