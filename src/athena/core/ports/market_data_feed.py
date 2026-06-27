"""Port: real-time market data feed.

The concrete adapter (e.g. FyersWebSocketAdapter) lives in
athena.engines.data.infrastructure and implements this protocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from athena.core.domain.primitives import Symbol
    from athena.core.domain.tick import Tick


@runtime_checkable
class MarketDataFeedPort(Protocol):
    """Stream real-time tick data for a set of instruments.

    Implementations are expected to:
        - Reconnect automatically on connection loss
        - Emit a DataQualityAlert if the feed is stale beyond a threshold
        - Never yield a Tick whose timestamp is older than the previous Tick
          for the same symbol (monotonic time guarantee)
    """

    async def subscribe(self, symbols: frozenset[Symbol]) -> None:
        """Subscribe to real-time updates for the given symbols.

        Calling subscribe with an already-subscribed symbol is a no-op.
        """
        ...

    async def unsubscribe(self, symbols: frozenset[Symbol]) -> None:
        """Unsubscribe from updates for the given symbols."""
        ...

    def stream(self) -> AsyncIterator[Tick]:
        """Yield Tick events as they arrive from the feed.

        This is an infinite async generator. Callers must handle
        cancellation to stop iteration.
        """
        ...

    async def close(self) -> None:
        """Gracefully close the feed connection."""
        ...
