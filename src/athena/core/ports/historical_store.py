"""Port: historical market data store.

The concrete adapter (e.g. TimescaleHistoricalStore) lives in
athena.engines.data.infrastructure and implements this protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import datetime

    from athena.core.domain.ohlcv import OHLCV, BarInterval
    from athena.core.domain.primitives import Symbol
    from athena.core.domain.tick import Tick


@runtime_checkable
class HistoricalStorePort(Protocol):
    """Read and write historical OHLCV bars and tick data."""

    async def write_ohlcv(self, bars: list[OHLCV]) -> None:
        """Persist a batch of closed OHLCV bars.

        Implementations must be idempotent: writing a bar that already
        exists (same symbol + interval + open_time) must not raise.
        """
        ...

    async def write_ticks(self, ticks: list[Tick]) -> None:
        """Persist a batch of normalised ticks.

        Implementations must be idempotent on (symbol, timestamp_utc).
        """
        ...

    def fetch_ohlcv(
        self,
        symbol: Symbol,
        interval: BarInterval,
        from_utc: datetime,
        to_utc: datetime,
    ) -> AsyncIterator[OHLCV]:
        """Yield OHLCV bars for `symbol` in ascending timestamp order.

        The range [from_utc, to_utc] is inclusive on both ends.
        Gaps (missing bars due to holidays or halts) are omitted - callers
        must handle non-contiguous sequences.
        """
        ...

    def fetch_ticks(
        self,
        symbol: Symbol,
        from_utc: datetime,
        to_utc: datetime,
    ) -> AsyncIterator[Tick]:
        """Yield Ticks for `symbol` in ascending timestamp order."""
        ...

    async def get_latest_bar_time(
        self,
        symbol: Symbol,
        interval: BarInterval,
    ) -> datetime | None:
        """Return the open_time of the most recent stored bar, or None if empty."""
        ...
