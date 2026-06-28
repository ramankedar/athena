"""Exchange metadata value objects and well-known exchange definitions.

An ``ExchangeMetadata`` is a rich, immutable description of a financial
exchange — more than an enum value, but less than a live data feed. It
encodes stable domain facts: timezone, primary currency, regulatory authority,
founding year, and ISO MIC code.

Well-known exchange constants (``NSE``, ``BSE``, ``MCX``) are provided as
module-level values, analogous to ``datetime.timezone.utc``. They represent
stable domain knowledge that belongs in code, not configuration. When a new
exchange is added to Athena's coverage, a new constant is defined here.

``InMemoryExchangeRepository`` provides a simple in-memory implementation of
``ExchangeRepositoryProtocol`` (defined in ``athena.market.interfaces``)
pre-populated with Indian exchange data.
"""

from __future__ import annotations

from dataclasses import dataclass

from athena.market.exceptions import ExchangeNotFoundError
from athena.market.models import CountryCode, MarketCurrency, MarketId, MarketTimezone

if __name__ == "__main__":
    pass


@dataclass(frozen=True)
class ExchangeMetadata:
    """Complete, immutable description of a financial exchange.

    Attributes:
        id:              Platform identifier (e.g. ``MarketId("NSE")``).
        name:            Full legal name of the exchange.
        short_name:      Commonly used abbreviation (may differ from ``id``).
        country:         ISO 3166-1 alpha-2 country code.
        primary_currency: The currency in which instruments are primarily
            priced on this exchange.
        timezone:        IANA timezone where the exchange is located.
        regulator:       Name of the primary regulatory body (e.g. ``"SEBI"``).
        established_year: Year the exchange was founded. ``None`` if unknown.
        mic_code:        ISO 10383 Market Identifier Code (e.g. ``"XNSE"``).
            ``None`` if the exchange is not yet assigned a MIC.
        website:         Official exchange website URL. ``None`` if unknown.

    Example::

        nse = ExchangeMetadata(
            id=MarketId("NSE"),
            name="National Stock Exchange of India",
            short_name="NSE",
            country=CountryCode("IN"),
            primary_currency=MarketCurrency("INR"),
            timezone=MarketTimezone("Asia/Kolkata"),
            regulator="SEBI",
            established_year=1992,
            mic_code="XNSE",
        )
    """

    id: MarketId
    name: str
    short_name: str
    country: CountryCode
    primary_currency: MarketCurrency
    timezone: MarketTimezone
    regulator: str
    established_year: int | None = None
    mic_code: str | None = None
    website: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            from athena.market.exceptions import InvalidMarketIdError

            raise InvalidMarketIdError(
                str(self.id),
                reason="ExchangeMetadata.name must not be empty",
            )
        if not self.short_name.strip():
            from athena.market.exceptions import InvalidMarketIdError

            raise InvalidMarketIdError(
                str(self.id),
                reason="ExchangeMetadata.short_name must not be empty",
            )
        if not self.regulator.strip():
            from athena.market.exceptions import InvalidMarketIdError

            raise InvalidMarketIdError(
                str(self.id),
                reason="ExchangeMetadata.regulator must not be empty",
            )
        if self.established_year is not None and self.established_year < 1600:
            from athena.market.exceptions import InvalidMarketIdError

            raise InvalidMarketIdError(
                str(self.id),
                reason=(
                    f"established_year {self.established_year} "
                    "predates the earliest known exchanges"
                ),
            )

    def __str__(self) -> str:
        return f"{self.short_name} ({self.id})"

    def __repr__(self) -> str:
        return (
            f"ExchangeMetadata(id={self.id!s}, name={self.name!r}, "
            f"country={self.country!s}, timezone={self.timezone!s})"
        )


# ── Well-known exchange constants ──────────────────────────────────────────────
#
# These represent stable domain knowledge — the equivalent of
# ``datetime.timezone.utc`` for market metadata.

#: National Stock Exchange of India.
NSE: ExchangeMetadata = ExchangeMetadata(
    id=MarketId("NSE"),
    name="National Stock Exchange of India Limited",
    short_name="NSE",
    country=CountryCode("IN"),
    primary_currency=MarketCurrency("INR"),
    timezone=MarketTimezone("Asia/Kolkata"),
    regulator="SEBI",
    established_year=1992,
    mic_code="XNSE",
    website="https://www.nseindia.com",
)

#: Bombay Stock Exchange (BSE Limited).
BSE: ExchangeMetadata = ExchangeMetadata(
    id=MarketId("BSE"),
    name="BSE Limited",
    short_name="BSE",
    country=CountryCode("IN"),
    primary_currency=MarketCurrency("INR"),
    timezone=MarketTimezone("Asia/Kolkata"),
    regulator="SEBI",
    established_year=1875,
    mic_code="XBOM",
    website="https://www.bseindia.com",
)

#: Multi Commodity Exchange of India.
MCX: ExchangeMetadata = ExchangeMetadata(
    id=MarketId("MCX"),
    name="Multi Commodity Exchange of India Limited",
    short_name="MCX",
    country=CountryCode("IN"),
    primary_currency=MarketCurrency("INR"),
    timezone=MarketTimezone("Asia/Kolkata"),
    regulator="SEBI",
    established_year=2003,
    mic_code="XIMC",
    website="https://www.mcxindia.com",
)

#: New York Stock Exchange (planned — international expansion).
NYSE: ExchangeMetadata = ExchangeMetadata(
    id=MarketId("NYSE"),
    name="New York Stock Exchange",
    short_name="NYSE",
    country=CountryCode("US"),
    primary_currency=MarketCurrency("USD"),
    timezone=MarketTimezone("America/New_York"),
    regulator="SEC",
    established_year=1792,
    mic_code="XNYS",
    website="https://www.nyse.com",
)

#: All well-known exchanges, keyed by ``MarketId``.
KNOWN_EXCHANGES: dict[MarketId, ExchangeMetadata] = {
    NSE.id: NSE,
    BSE.id: BSE,
    MCX.id: MCX,
    NYSE.id: NYSE,
}


# ── In-memory exchange repository ─────────────────────────────────────────────


class InMemoryExchangeRepository:
    """Pure in-memory repository for ``ExchangeMetadata`` objects.

    Pre-populated with Indian exchanges (NSE, BSE, MCX) and NYSE as a
    planned international exchange. Additional exchanges can be registered
    at runtime.

    This implementation is suitable for:
    - Unit tests (no infrastructure required)
    - Platform startup before a database-backed repository is available
    - Research and backtesting contexts

    Example::

        repo = InMemoryExchangeRepository()
        nse = repo.get(MarketId("NSE"))
        indian_exchanges = repo.find_by_country(CountryCode("IN"))
    """

    def __init__(self, preload_known: bool = True) -> None:
        self._exchanges: dict[MarketId, ExchangeMetadata] = {}
        if preload_known:
            for exchange in KNOWN_EXCHANGES.values():
                self._exchanges[exchange.id] = exchange

    def register(self, exchange: ExchangeMetadata) -> None:
        """Register an exchange. Overwrites any existing entry with the same id.

        Args:
            exchange: The exchange metadata to register.
        """
        self._exchanges[exchange.id] = exchange

    def get(self, exchange_id: MarketId) -> ExchangeMetadata:
        """Return the exchange for the given id.

        Args:
            exchange_id: The ``MarketId`` to look up.

        Returns:
            The matching ``ExchangeMetadata``.

        Raises:
            ExchangeNotFoundError: If no exchange is registered with this id.
        """
        result = self._exchanges.get(exchange_id)
        if result is None:
            raise ExchangeNotFoundError(str(exchange_id))
        return result

    def get_or_none(self, exchange_id: MarketId) -> ExchangeMetadata | None:
        """Return the exchange for the given id, or ``None`` if not found.

        Args:
            exchange_id: The ``MarketId`` to look up.

        Returns:
            The matching ``ExchangeMetadata``, or ``None``.
        """
        return self._exchanges.get(exchange_id)

    def exists(self, exchange_id: MarketId) -> bool:
        """Return ``True`` if the exchange is registered.

        Args:
            exchange_id: The ``MarketId`` to check.

        Returns:
            ``True`` when a matching exchange exists.
        """
        return exchange_id in self._exchanges

    def find_by_country(self, country: CountryCode) -> tuple[ExchangeMetadata, ...]:
        """Return all exchanges in the given country.

        Args:
            country: The ISO 3166-1 country code to filter by.

        Returns:
            A tuple of matching exchanges (may be empty).
        """
        return tuple(e for e in self._exchanges.values() if e.country == country)

    def all_exchanges(self) -> tuple[ExchangeMetadata, ...]:
        """Return all registered exchanges.

        Returns:
            A tuple of all registered ``ExchangeMetadata`` objects.
        """
        return tuple(self._exchanges.values())

    def __len__(self) -> int:
        return len(self._exchanges)

    def __repr__(self) -> str:
        return f"InMemoryExchangeRepository(count={len(self._exchanges)})"
