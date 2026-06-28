"""Data provenance and source metadata.

Every piece of market data in Athena carries provenance — a record of where
it came from, when it was retrieved, and what delays or limitations apply.
This allows research teams to:

- Reproduce results by knowing the exact data vintage used.
- Filter analysis to exclude delayed or low-confidence data.
- Audit discrepancies between what a vendor reported and what was stored.

``DataProvenance`` is attached to OHLCV bars, ticks, quotes, and order book
snapshots. It is optional (``None`` allowed) for data generated in-process
(e.g. synthetic fill-bars), but mandatory for any data loaded from an external
vendor or storage system.

``SymbolMapping`` records how an internal symbol (``"NSE:NIFTY50-INDEX"``)
maps to a vendor's native symbol (``"NIFTY_I"`` on Fyers, ``"^NSEI"`` on
Yahoo Finance). This is critical for debugging and for re-loading data from
the same vendor after a symbol remapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from athena.market_data.exceptions import InvalidBarError

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class DataProvenance:
    """Provenance record for a piece of market data.

    Attributes:
        vendor:          Name of the data vendor (``"fyers"``, ``"nse_direct"``,
            ``"yahoo_finance"``). Use lowercase, hyphenated identifiers.
        vendor_symbol:   The vendor's own symbol string for this instrument
            (may differ from Athena's internal symbol format).
        retrieved_at:    UTC timestamp when this data was fetched from the vendor.
            Must be timezone-aware.
        is_delayed:      ``True`` when the data is delayed (e.g. 15-minute delay
            on free market data feeds).
        delay_minutes:   Approximate delay in minutes. ``None`` when ``is_delayed``
            is ``False`` (real-time) or when the exact delay is unknown.
        data_version:    Optional vendor-supplied version or sequence identifier
            for this dataset (e.g. daily data file version).
        license_info:    Optional license or attribution string required by the
            vendor's terms of service.

    Example::

        provenance = DataProvenance(
            vendor="fyers",
            vendor_symbol="NSE:NIFTY50-INDEX",
            retrieved_at=datetime(2025, 1, 15, 10, 0, tzinfo=UTC),
        )
    """

    vendor: str
    vendor_symbol: str
    retrieved_at: datetime
    is_delayed: bool = False
    delay_minutes: int | None = None
    data_version: str | None = None
    license_info: str | None = None

    def __post_init__(self) -> None:
        if not self.vendor.strip():
            raise InvalidBarError("vendor", self.vendor, "vendor must not be empty")
        if not self.vendor_symbol.strip():
            raise InvalidBarError(
                "vendor_symbol", self.vendor_symbol, "vendor_symbol must not be empty"
            )
        if self.retrieved_at.tzinfo is None:
            raise InvalidBarError(
                "retrieved_at",
                str(self.retrieved_at),
                "retrieved_at must be timezone-aware",
            )
        if self.delay_minutes is not None and self.delay_minutes < 0:
            raise InvalidBarError(
                "delay_minutes",
                self.delay_minutes,
                "delay_minutes must be >= 0 when provided",
            )

    def __str__(self) -> str:
        delay = f" (+{self.delay_minutes}min)" if self.is_delayed else ""
        return f"DataProvenance(vendor={self.vendor!r}, symbol={self.vendor_symbol!r}{delay})"


@dataclass(frozen=True)
class SymbolMapping:
    """Maps an internal Athena symbol to a vendor's native symbol.

    Attributes:
        internal_symbol: Athena's canonical symbol (e.g. ``"NSE:NIFTY50-INDEX"``).
        vendor:          Data vendor name.
        vendor_symbol:   Vendor's own symbol identifier for the same instrument.
        is_active:       ``True`` when this mapping is currently valid.
            ``False`` for historical mappings (the vendor may have changed
            the symbol since the mapping was created).

    Example::

        mapping = SymbolMapping(
            internal_symbol="NSE:NIFTY50-INDEX",
            vendor="fyers",
            vendor_symbol="NSE:NIFTY50-INDEX",  # Fyers uses same format
        )
    """

    internal_symbol: str
    vendor: str
    vendor_symbol: str
    is_active: bool = True

    def __post_init__(self) -> None:
        if not self.internal_symbol.strip():
            raise InvalidBarError("internal_symbol", self.internal_symbol, "must not be empty")
        if not self.vendor.strip():
            raise InvalidBarError("vendor", self.vendor, "must not be empty")
        if not self.vendor_symbol.strip():
            raise InvalidBarError("vendor_symbol", self.vendor_symbol, "must not be empty")

    def __str__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return (
            f"SymbolMapping({self.internal_symbol!r} "
            f"-> {self.vendor!r}:{self.vendor_symbol!r} [{status}])"
        )
