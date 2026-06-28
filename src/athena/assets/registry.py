"""Instrument query specification and in-memory registry.

``InstrumentQuery`` is a value object that specifies search criteria for the
registry. ``InMemoryInstrumentRegistry`` is a pure in-memory (non-persistent)
concrete implementation of ``InstrumentRegistryProtocol``.

Why is an in-memory registry a domain concern (not infrastructure)?
    It holds no database connections, performs no I/O, and has no external
    dependencies. It is logically equivalent to ``NullHolidayProvider`` in
    the time domain — a safe default that works without infrastructure,
    enabling tests and the instrument master cache at startup. The Data Engine
    will load instruments into this registry from Fyers API; the registry
    itself knows nothing about how instruments were sourced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from athena.assets.exceptions import DuplicateInstrumentError, InstrumentNotFoundError

if TYPE_CHECKING:
    from athena.assets.classification import (
        AssetClass,
        ExchangeSegment,
        InstrumentStatus,
        InstrumentType,
    )
    from athena.assets.identifiers import ISIN, ExchangeId, InstrumentId, Symbol
    from athena.assets.instruments import Instrument


@dataclass(frozen=True)
class InstrumentQuery:
    """Structured query specification for filtering the instrument registry.

    All fields are optional and default to ``None``. Non-``None`` fields are
    ANDed together (every condition must match). Providing no filters returns
    all registered instruments.

    Attributes:
        asset_class:      Filter by broad asset class.
        instrument_type:  Filter by specific instrument type.
        exchange:         Filter by exchange.
        segment:          Filter by exchange segment.
        status:           Filter by lifecycle status.
        name_contains:    Case-insensitive substring match on instrument name.
        isin:             Filter by ISIN (exact match).

    Example::

        query = InstrumentQuery(
            asset_class=AssetClass.DERIVATIVE,
            status=InstrumentStatus.ACTIVE,
        )
        active_derivatives = registry.find(query)
    """

    asset_class: AssetClass | None = None
    instrument_type: InstrumentType | None = None
    exchange: ExchangeId | None = None
    segment: ExchangeSegment | None = None
    status: InstrumentStatus | None = None
    name_contains: str | None = None
    isin: ISIN | None = None

    @property
    def is_empty(self) -> bool:
        """Return ``True`` when all filter fields are ``None``.

        Returns:
            ``True`` when no filter criteria are set (matches all instruments).
        """
        return all(
            v is None
            for v in (
                self.asset_class,
                self.instrument_type,
                self.exchange,
                self.segment,
                self.status,
                self.name_contains,
                self.isin,
            )
        )


class InMemoryInstrumentRegistry:
    """Pure in-memory instrument registry with no persistence.

    Stores instruments in dictionaries keyed by ``InstrumentId``, ``Symbol``,
    and optionally ``ISIN``. All operations are O(1) for direct lookups.

    This implementation is suitable for:
    - Unit tests (no infrastructure required)
    - The platform's startup-time instrument master cache
    - Research notebooks and backtesting environments

    Thread safety:
        Standard CPython dict operations are GIL-protected, making single-dict
        reads and writes thread-safe within the GIL. For asyncio concurrent
        access, no additional locking is required as long as modifications happen
        before the event loop starts (startup loading). If instruments are
        registered concurrently at runtime, external locking is the caller's
        responsibility.
    """

    def __init__(self) -> None:
        self._by_id: dict[InstrumentId, Instrument] = {}
        self._by_symbol: dict[Symbol, Instrument] = {}
        self._by_isin: dict[ISIN, Instrument] = {}

    # ── Write operations ──────────────────────────────────────────────────────

    def register(self, instrument: Instrument) -> None:
        """Register a new instrument.

        Args:
            instrument: The instrument to add.

        Raises:
            DuplicateInstrumentError: If an instrument with the same
                ``InstrumentId`` is already registered.
        """
        if instrument.id in self._by_id:
            raise DuplicateInstrumentError(str(instrument.id))
        self._by_id[instrument.id] = instrument
        self._by_symbol[instrument.symbol] = instrument
        if instrument.isin is not None:
            self._by_isin[instrument.isin] = instrument

    def register_many(self, instruments: tuple[Instrument, ...]) -> int:
        """Register multiple instruments, skipping existing ones.

        Args:
            instruments: Instruments to register.

        Returns:
            Count of newly registered instruments.
        """
        added = 0
        for instrument in instruments:
            if instrument.id not in self._by_id:
                self.register(instrument)
                added += 1
        return added

    def remove(self, instrument_id: InstrumentId) -> bool:
        """Remove an instrument from the registry.

        Args:
            instrument_id: ID of the instrument to remove.

        Returns:
            ``True`` if removed; ``False`` if not found.
        """
        instrument = self._by_id.pop(instrument_id, None)
        if instrument is None:
            return False
        self._by_symbol.pop(instrument.symbol, None)
        if instrument.isin is not None:
            self._by_isin.pop(instrument.isin, None)
        return True

    # ── Read operations ───────────────────────────────────────────────────────

    def get(self, instrument_id: InstrumentId) -> Instrument:
        """Return the instrument for the given ID.

        Args:
            instrument_id: The ID to look up.

        Returns:
            The matching ``Instrument``.

        Raises:
            InstrumentNotFoundError: If not found.
        """
        instrument = self._by_id.get(instrument_id)
        if instrument is None:
            raise InstrumentNotFoundError(str(instrument_id), lookup_type="id")
        return instrument

    def get_by_symbol(self, symbol: Symbol) -> Instrument:
        """Return the instrument for the given market symbol.

        Args:
            symbol: The ``Symbol`` to look up.

        Returns:
            The matching ``Instrument``.

        Raises:
            InstrumentNotFoundError: If not found.
        """
        instrument = self._by_symbol.get(symbol)
        if instrument is None:
            raise InstrumentNotFoundError(str(symbol), lookup_type="symbol")
        return instrument

    def get_or_none(self, instrument_id: InstrumentId) -> Instrument | None:
        """Return the instrument for the given ID, or ``None``.

        Args:
            instrument_id: The ID to look up.

        Returns:
            The ``Instrument``, or ``None`` if not found.
        """
        return self._by_id.get(instrument_id)

    def get_by_isin(self, isin: ISIN) -> Instrument | None:
        """Return the first instrument matching the given ISIN, or ``None``.

        Args:
            isin: The ``ISIN`` to look up.

        Returns:
            The matching ``Instrument``, or ``None``.
        """
        return self._by_isin.get(isin)

    def exists(self, instrument_id: InstrumentId) -> bool:
        """Return ``True`` if an instrument with this ID is registered.

        Args:
            instrument_id: The ID to check.

        Returns:
            ``True`` when a matching instrument exists.
        """
        return instrument_id in self._by_id

    def find(self, query: InstrumentQuery) -> tuple[Instrument, ...]:
        """Filter the registry using a structured query.

        Args:
            query: Filter criteria. ``None`` fields are ignored.

        Returns:
            Tuple of matching instruments.
        """
        if query.is_empty:
            return tuple(self._by_id.values())

        results: list[Instrument] = []
        for instrument in self._by_id.values():
            if not _matches(instrument, query):
                continue
            results.append(instrument)
        return tuple(results)

    def count(self, asset_class: AssetClass | None = None) -> int:
        """Return the number of registered instruments.

        Args:
            asset_class: When provided, count only this asset class.

        Returns:
            Total count matching the filter.
        """
        if asset_class is None:
            return len(self._by_id)
        return sum(1 for i in self._by_id.values() if i.asset_class == asset_class)

    def all_symbols(self) -> frozenset[Symbol]:
        """Return all registered symbols.

        Returns:
            Frozenset of every ``Symbol`` in the registry.
        """
        return frozenset(self._by_symbol.keys())

    def __len__(self) -> int:
        return len(self._by_id)

    def __repr__(self) -> str:
        return f"InMemoryInstrumentRegistry(count={len(self._by_id)})"


# ── Internal filter helper ─────────────────────────────────────────────────────


def _matches(instrument: Instrument, query: InstrumentQuery) -> bool:
    """Return ``True`` if ``instrument`` satisfies all non-``None`` query fields."""
    if query.asset_class is not None and instrument.asset_class != query.asset_class:
        return False
    if query.instrument_type is not None and instrument.instrument_type != query.instrument_type:
        return False
    if query.exchange is not None and instrument.exchange != query.exchange:
        return False
    if query.segment is not None and instrument.segment != query.segment:
        return False
    if query.status is not None and instrument.status != query.status:
        return False
    if (
        query.name_contains is not None
        and query.name_contains.lower() not in instrument.name.lower()
    ):
        return False
    return query.isin is None or instrument.isin == query.isin
