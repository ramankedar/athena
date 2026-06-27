"""Port: instrument master repository.

The concrete adapter (e.g. RedisInstrumentCache backed by TimescaleDB)
lives in athena.engines.data.infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from athena.core.domain.instrument import Exchange, Instrument, Segment
    from athena.core.domain.primitives import Symbol


@runtime_checkable
class InstrumentRepositoryPort(Protocol):
    """Read-only access to the instrument master.

    The instrument master is loaded at startup and refreshed each market
    morning. It is never written to during trading hours.
    """

    async def get(self, symbol: Symbol) -> Instrument:
        """Return the Instrument for `symbol`.

        Raises:
            InstrumentNotFoundError: if the symbol is not in the master.
        """
        ...

    async def find(
        self,
        exchange: Exchange | None = None,
        segment: Segment | None = None,
        name_contains: str | None = None,
    ) -> list[Instrument]:
        """Search the instrument master with optional filters.

        Returns all instruments when all filters are None.
        Multiple filters are ANDed together.
        """
        ...

    async def exists(self, symbol: Symbol) -> bool:
        """Return True if the symbol is present in the master."""
        ...

    async def refresh(self) -> int:
        """Reload the instrument master from the upstream source.

        Returns the number of instruments loaded.
        """
        ...
