"""Strongly typed identifier value objects for the Asset Domain.

Every external string that identifies a financial instrument is wrapped in a
typed value object that validates format on construction. This eliminates an
entire class of bugs where raw strings are passed in the wrong position.

Identifiers defined here:
    ``InstrumentId``  — Platform-internal UUID v4 uniquely identifying an instrument.
    ``ExchangeId``    — Uppercase exchange code (``"NSE"``, ``"BSE"``, ``"MCX"``).
    ``Symbol``        — Structured ``EXCHANGE:TICKER`` market identifier.
    ``ISIN``          — 12-character ISO 6166 identifier with checksum validation.
    ``CurrencyCode``  — ISO 4217 three-letter currency code (``"INR"``, ``"USD"``).

Design note on ``Symbol``:
    The ``athena.core.domain.primitives.Symbol`` is a ``NewType(str)`` used in
    events and ticks for lightweight identification. This ``Symbol`` is a richer
    value object with exchange and ticker components, used in the instrument master.
    The two serve different purposes and coexist without conflict.

ISIN validation:
    Implements the ISO 6166 check digit algorithm (modified Luhn) verified against
    real ISINs: ``INE040A01034`` (HDFC Bank), ``US0231351067`` (Apple).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID, uuid4

from athena.assets.exceptions import InvalidIdentifierError


@dataclass(frozen=True)
class InstrumentId:
    """Platform-internal UUID v4 identifier for an ``Instrument``.

    Instruments are uniquely identified within Athena by a UUID. The UUID is
    opaque to external systems — market participants use ``Symbol`` or ``ISIN``
    for cross-system references. UUIDs are stable across exchange re-listings
    and symbol changes.

    Attributes:
        value: The underlying ``UUID`` object.

    Example::

        instrument_id = InstrumentId.generate()
        from_string = InstrumentId.from_string("550e8400-e29b-41d4-a716-446655440000")
    """

    value: UUID

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return f"InstrumentId({self.value!s})"

    @classmethod
    def generate(cls) -> InstrumentId:
        """Generate a new random UUID v4 instrument identifier.

        Returns:
            A new ``InstrumentId`` backed by a UUID v4.
        """
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> InstrumentId:
        """Parse a UUID string into an ``InstrumentId``.

        Args:
            value: A valid UUID string (hyphenated or not).

        Returns:
            An ``InstrumentId`` wrapping the parsed UUID.

        Raises:
            InvalidIdentifierError: If the string is not a valid UUID.
        """
        try:
            return cls(UUID(value))
        except ValueError as exc:
            raise InvalidIdentifierError(
                value,
                reason="InstrumentId must be a valid UUID",
            ) from exc


@dataclass(frozen=True)
class ExchangeId:
    """Uppercase exchange code identifying a financial exchange.

    Exchange codes follow the ISO 10383 Market Identifier Code (MIC) convention
    in spirit, though Athena uses abbreviated forms for brevity (``"NSE"``
    rather than ``"XNSE"``).

    Attributes:
        code: Uppercase alphanumeric exchange identifier.

    Example::

        nse = ExchangeId("NSE")
        bse = ExchangeId("BSE")
        mcx = ExchangeId("MCX")
    """

    code: str

    def __post_init__(self) -> None:
        stripped = self.code.strip()
        if not stripped:
            raise InvalidIdentifierError(self.code, reason="ExchangeId.code must not be empty")
        if not stripped.isupper() or not stripped.isalnum():
            raise InvalidIdentifierError(
                self.code,
                reason="ExchangeId.code must be uppercase alphanumeric (e.g. 'NSE', 'BSE')",
            )

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"ExchangeId({self.code!r})"


@dataclass(frozen=True)
class Symbol:
    """Structured market symbol in ``EXCHANGE:TICKER`` format.

    A Symbol uniquely identifies an instrument within its exchange listing.
    The ``exchange_code`` component mirrors ``ExchangeId.code``. The ``ticker``
    component is the exchange-assigned identifier and may contain hyphens,
    digits, and uppercase letters.

    Attributes:
        exchange_code: Uppercase exchange identifier (e.g. ``"NSE"``).
        ticker:        Exchange-assigned instrument ticker (e.g. ``"NIFTY50-INDEX"``).

    Example::

        nifty = Symbol("NSE", "NIFTY50-INDEX")
        call  = Symbol.parse("NSE:NIFTY25JAN24500CE")
        str(nifty)  # "NSE:NIFTY50-INDEX"
    """

    SEPARATOR: ClassVar[str] = ":"

    exchange_code: str
    ticker: str

    def __post_init__(self) -> None:
        if not self.exchange_code.strip():
            raise InvalidIdentifierError(
                f"{self.exchange_code}:{self.ticker}",
                reason="Symbol.exchange_code must not be empty",
            )
        if not self.ticker.strip():
            raise InvalidIdentifierError(
                f"{self.exchange_code}:{self.ticker}",
                reason="Symbol.ticker must not be empty",
            )
        if self.SEPARATOR in self.ticker:
            raise InvalidIdentifierError(
                f"{self.exchange_code}:{self.ticker}",
                reason=f"Symbol.ticker must not contain '{self.SEPARATOR}'",
            )

    def __str__(self) -> str:
        return f"{self.exchange_code}{self.SEPARATOR}{self.ticker}"

    def __repr__(self) -> str:
        return f"Symbol({self.exchange_code!r}, {self.ticker!r})"

    @classmethod
    def parse(cls, symbol_str: str) -> Symbol:
        """Parse a ``EXCHANGE:TICKER`` string into a ``Symbol``.

        Args:
            symbol_str: A string in the form ``"EXCHANGE:TICKER"``.

        Returns:
            A new ``Symbol`` with the parsed components.

        Raises:
            InvalidIdentifierError: If the string does not contain exactly
                one ``:`` separator, or if either component is empty.
        """
        if cls.SEPARATOR not in symbol_str:
            raise InvalidIdentifierError(
                symbol_str,
                reason=(
                    f"Symbol must contain '{cls.SEPARATOR}' separator (e.g. 'NSE:NIFTY50-INDEX')"
                ),
            )
        exchange_code, _, ticker = symbol_str.partition(cls.SEPARATOR)
        return cls(exchange_code=exchange_code, ticker=ticker)


@dataclass(frozen=True)
class ISIN:
    """ISO 6166 International Securities Identification Number.

    Format: 2-letter country code + 9 alphanumeric NSIN + 1 check digit.
    The check digit is verified using the ISO 6166 modified Luhn algorithm.

    Attributes:
        value: The 12-character ISIN string (uppercase).

    Raises:
        InvalidIdentifierError: On construction if the ISIN is malformed or
            the check digit does not match.

    Example::

        hdfc = ISIN("INE040A01034")   # HDFC Bank
        apple = ISIN("US0231351067")  # Apple Inc.
    """

    value: str

    def __post_init__(self) -> None:
        v = self.value.upper()
        if len(v) != 12:
            raise InvalidIdentifierError(
                self.value,
                reason="ISIN must be exactly 12 characters (CC + 9 alphanumeric + 1 check digit)",
            )
        country_code = v[:2]
        if not country_code.isalpha():
            raise InvalidIdentifierError(
                self.value,
                reason="ISIN first two characters must be alphabetic (ISO 3166-1 country code)",
            )
        nsin = v[2:11]
        if not nsin.isalnum():
            raise InvalidIdentifierError(
                self.value,
                reason="ISIN characters 3-11 (NSIN) must be alphanumeric",
            )
        check_char = v[11]
        if not check_char.isdigit():
            raise InvalidIdentifierError(
                self.value,
                reason="ISIN final character (check digit) must be a digit",
            )
        expected = _compute_isin_check_digit(v[:11])
        if int(check_char) != expected:
            raise InvalidIdentifierError(
                self.value,
                reason=(f"ISIN check digit is incorrect — expected {expected}, got {check_char}"),
            )

    @property
    def country_code(self) -> str:
        """ISO 3166-1 alpha-2 country code.

        Returns:
            Two-letter country code (e.g. ``"IN"``, ``"US"``).
        """
        return self.value[:2]

    @property
    def nsin(self) -> str:
        """National Securities Identifying Number (9 characters).

        Returns:
            The exchange-specific 9-character NSIN portion of the ISIN.
        """
        return self.value[2:11]

    @property
    def check_digit(self) -> int:
        """The ISO 6166 Luhn check digit.

        Returns:
            Integer check digit (0-9).
        """
        return int(self.value[11])

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"ISIN({self.value!r})"


@dataclass(frozen=True)
class CurrencyCode:
    """ISO 4217 three-letter currency code.

    Validates that the code is exactly 3 uppercase alphabetic characters.
    Does not validate against the official ISO 4217 list — new currencies
    and platform-specific codes (e.g. settlement currencies) may not appear
    in any published list.

    Attributes:
        code: The 3-letter currency code (e.g. ``"INR"``, ``"USD"``).

    Example::

        inr = CurrencyCode("INR")
        usd = CurrencyCode("USD")
    """

    code: str

    def __post_init__(self) -> None:
        if len(self.code) != 3 or not self.code.isalpha() or not self.code.isupper():
            raise InvalidIdentifierError(
                self.code,
                reason="CurrencyCode must be exactly 3 uppercase letters (ISO 4217, e.g. 'INR')",
            )

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"CurrencyCode({self.code!r})"


# ── Internal helper ────────────────────────────────────────────────────────────


def _compute_isin_check_digit(prefix: str) -> int:
    """Compute the ISO 6166 check digit for the 11-character ISIN prefix.

    Algorithm (modified Luhn):
    1. Convert each alphanumeric character to its digit string
       (letters A-Z become 10-35).
    2. Starting from the rightmost digit of the resulting string, double
       every digit at an odd position (position 1, 3, 5, … from the right).
    3. If a doubled value exceeds 9, subtract 9.
    4. Sum all values.
    5. Return ``(10 - sum % 10) % 10``.

    Args:
        prefix: The 11-character ISIN prefix (country code + NSIN).

    Returns:
        Integer check digit (0-9).
    """
    # Step 1: expand alphanumeric to digit string
    digit_str = ""
    for ch in prefix.upper():
        if ch.isdigit():
            digit_str += ch
        else:
            # A=10, B=11, ..., Z=35
            digit_str += str(ord(ch) - ord("A") + 10)

    # Step 2-4: Luhn doubling from right
    total = 0
    for i, ch in enumerate(reversed(digit_str)):
        n = int(ch)
        if i % 2 == 0:  # odd position from right (1, 3, 5, …) → double
            n *= 2
            if n > 9:
                n -= 9
        total += n

    # Step 5
    return (10 - total % 10) % 10
