"""Protocol interfaces for the Asset Domain.

These Protocols define the structural contracts for any instrument registry or
lookup service. Concrete implementations (in-memory, database-backed) satisfy
these protocols without inheriting from them.

Two interfaces are defined:

``InstrumentRegistryProtocol``
    Full read/write registry. Supports registration, lookup by multiple keys,
    removal, and filtered searches.

``InstrumentLookupProtocol``
    Read-only subset. Services that only need to resolve symbols to instruments
    should accept this narrower interface, which a wider set of implementations
    can satisfy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from athena.assets.classification import AssetClass
    from athena.assets.identifiers import ISIN, InstrumentId, Symbol
    from athena.assets.instruments import Instrument
    from athena.assets.registry import InstrumentQuery


@runtime_checkable
class InstrumentLookupProtocol(Protocol):
    """Read-only instrument resolution interface.

    Services that need to resolve market symbols to full ``Instrument`` objects
    should accept this interface. It is satisfied by both full registries and
    read-only lookup caches.
    """

    def get(self, instrument_id: InstrumentId) -> Instrument:
        """Return the instrument for the given platform-internal ID.

        Args:
            instrument_id: The ``InstrumentId`` to look up.

        Returns:
            The matching ``Instrument``.

        Raises:
            InstrumentNotFoundError: If no instrument is registered with
                this ID.
        """
        ...

    def get_by_symbol(self, symbol: Symbol) -> Instrument:
        """Return the instrument for the given market symbol.

        Args:
            symbol: The ``Symbol`` to look up (e.g. ``Symbol.parse("NSE:NIFTY50-INDEX")``).

        Returns:
            The matching ``Instrument``.

        Raises:
            InstrumentNotFoundError: If no instrument is registered with
                this symbol.
        """
        ...

    def get_or_none(self, instrument_id: InstrumentId) -> Instrument | None:
        """Return the instrument for the given ID, or ``None`` if not found.

        Args:
            instrument_id: The ``InstrumentId`` to look up.

        Returns:
            The matching ``Instrument``, or ``None``.
        """
        ...

    def exists(self, instrument_id: InstrumentId) -> bool:
        """Return ``True`` if an instrument with this ID is registered.

        Args:
            instrument_id: The ``InstrumentId`` to check.

        Returns:
            ``True`` when a matching instrument exists.
        """
        ...


@runtime_checkable
class InstrumentRegistryProtocol(InstrumentLookupProtocol, Protocol):
    """Full read/write instrument registry interface.

    Extends ``InstrumentLookupProtocol`` with registration, removal, and
    querying operations. The standard implementation is ``InMemoryInstrumentRegistry``
    in ``athena.assets.registry``.

    At platform startup, the Data Engine loads the NSE/BSE instrument master
    and registers all active instruments into this registry. Other engines
    then use ``InstrumentLookupProtocol`` to resolve symbols received in
    market data feeds.
    """

    def register(self, instrument: Instrument) -> None:
        """Register a new instrument.

        Args:
            instrument: The instrument to add to the registry.

        Raises:
            DuplicateInstrumentError: If an instrument with the same
                ``InstrumentId`` or ``Symbol`` already exists.
        """
        ...

    def register_many(self, instruments: tuple[Instrument, ...]) -> int:
        """Register multiple instruments in a single call.

        Instruments that already exist are silently skipped (upsert semantics).
        Use this for bulk loading from an exchange master file.

        Args:
            instruments: Tuple of instruments to register.

        Returns:
            The number of new instruments added (not counting skipped duplicates).
        """
        ...

    def remove(self, instrument_id: InstrumentId) -> bool:
        """Remove an instrument from the registry.

        Args:
            instrument_id: The ID of the instrument to remove.

        Returns:
            ``True`` if the instrument was found and removed; ``False``
            if no instrument with that ID was registered.
        """
        ...

    def find(self, query: InstrumentQuery) -> tuple[Instrument, ...]:
        """Search the registry using a structured query.

        All non-``None`` query fields are ANDed together. Results are returned
        in an unspecified but deterministic order.

        Args:
            query: A ``InstrumentQuery`` specifying filter criteria.

        Returns:
            Tuple of matching instruments. Empty tuple when no matches.
        """
        ...

    def get_by_isin(self, isin: ISIN) -> Instrument | None:
        """Return the instrument matching the given ISIN, or ``None``.

        Args:
            isin: The ``ISIN`` to look up.

        Returns:
            The matching ``Instrument``, or ``None`` if not found.

        Note:
            An ISIN may be shared across exchanges (same company listed on
            NSE and BSE). This method returns the first match found, which is
            implementation-defined. To find all listings for an ISIN, use
            ``find(InstrumentQuery(isin=isin))``.
        """
        ...

    def count(self, asset_class: AssetClass | None = None) -> int:
        """Return the number of registered instruments.

        Args:
            asset_class: When provided, count only instruments of this class.

        Returns:
            Total count matching the filter. Zero when the registry is empty
            or no instruments match.
        """
        ...

    def all_symbols(self) -> frozenset[Symbol]:
        """Return all registered symbols as a frozenset.

        Returns:
            A frozenset of every ``Symbol`` currently in the registry.
        """
        ...
