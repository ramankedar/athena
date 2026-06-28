"""Instrument and contract validation utilities.

Provides structured validation that returns a ``ValidationResult`` instead of
immediately raising. This allows callers to collect all validation failures in
a single pass — important when loading hundreds of instruments from an exchange
master file and wanting to report all errors at once rather than stopping on
the first.

Two categories of validation are provided:

1. **Identity validation** (``is_valid_isin``, ``is_valid_symbol_string``):
   Boolean predicates over raw strings, useful before constructing value
   objects that raise on invalid input.

2. **Domain validation** (``validate_instrument``, ``validate_contract``):
   Business-rule checks over fully-constructed domain objects. These catch
   cross-field inconsistencies that cannot be expressed in a single field's
   ``__post_init__`` (e.g. a ``FuturesSpec`` attached to an instrument whose
   ``asset_class`` is ``EQUITY``).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from athena.assets.contracts import ContractSpec
    from athena.assets.instruments import Instrument

from athena.assets.classification import AssetClass
from athena.assets.contracts import (
    CommoditySpec,
    CurrencySpec,
    EquitySpec,
    ETFSpec,
    FuturesSpec,
    IndexSpec,
    OptionsSpec,
)
from athena.assets.identifiers import _compute_isin_check_digit

# ── Validation result ──────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of a domain validation pass.

    Attributes:
        is_valid: ``True`` when no failures were found.
        failures: Tuple of human-readable failure messages. Empty when valid.

    Example::

        result = validate_instrument(instrument)
        if not result.is_valid:
            for msg in result.failures:
                log.warning("validation.failure", message=msg)
    """

    is_valid: bool
    failures: tuple[str, ...] = ()

    @classmethod
    def ok(cls) -> ValidationResult:
        """Return a result indicating no validation failures.

        Returns:
            A ``ValidationResult`` with ``is_valid=True`` and no failures.
        """
        return cls(is_valid=True)

    @classmethod
    def failed(cls, *messages: str) -> ValidationResult:
        """Return a result indicating one or more validation failures.

        Args:
            *messages: One or more failure descriptions.

        Returns:
            A ``ValidationResult`` with ``is_valid=False`` and the given messages.
        """
        return cls(is_valid=False, failures=tuple(messages))

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Combine two ``ValidationResult`` objects into one.

        Args:
            other: The other result to merge with this one.

        Returns:
            A new ``ValidationResult`` that is invalid if either input is
            invalid, and whose failures are the union of both.
        """
        combined = self.failures + other.failures
        return ValidationResult(is_valid=len(combined) == 0, failures=combined)


# ── Identity validators ────────────────────────────────────────────────────────


def is_valid_isin(isin_str: str) -> bool:
    """Return ``True`` if ``isin_str`` is a valid ISO 6166 ISIN.

    Checks format (12 chars, country code prefix, alphanumeric NSIN) and
    verifies the check digit using the modified Luhn algorithm.

    Args:
        isin_str: The raw ISIN string to validate.

    Returns:
        ``True`` when the string is a structurally valid ISIN with a correct
        check digit.
    """
    if len(isin_str) != 12:
        return False
    v = isin_str.upper()
    country = v[:2]
    if not country.isalpha():
        return False
    nsin = v[2:11]
    if not nsin.isalnum():
        return False
    check = v[11]
    if not check.isdigit():
        return False
    return int(check) == _compute_isin_check_digit(v[:11])


def is_valid_symbol_string(symbol_str: str) -> bool:
    """Return ``True`` if ``symbol_str`` has the expected ``EXCHANGE:TICKER`` format.

    This is a lightweight predicate. The full structural validation (non-empty
    components, no nested colons) is enforced by ``Symbol.__post_init__``.

    Args:
        symbol_str: The raw symbol string to check.

    Returns:
        ``True`` when the string contains exactly one ``:`` with non-empty
        components on each side.
    """
    if ":" not in symbol_str:
        return False
    exchange, _, ticker = symbol_str.partition(":")
    return bool(exchange.strip()) and bool(ticker.strip()) and ":" not in ticker


# ── Domain validators ──────────────────────────────────────────────────────────


def validate_contract(spec: ContractSpec) -> ValidationResult:
    """Validate a ``ContractSpec`` against domain business rules.

    Checks beyond those already enforced in ``ContractSpec.__post_init__``
    (which validates non-negativity of shared fields). This function catches
    higher-level semantic rules.

    Args:
        spec: The contract specification to validate.

    Returns:
        A ``ValidationResult`` — valid when no rules are violated.
    """
    failures: list[str] = []

    if isinstance(spec, OptionsSpec) and spec.strike <= Decimal(0):
        failures.append(f"OptionsSpec.strike must be > 0 (got {spec.strike})")

    if isinstance(spec, CurrencySpec) and spec.base_currency == spec.quote_currency:
        failures.append(
            "CurrencySpec.base_currency and quote_currency must differ "
            f"(both are {spec.base_currency})"
        )

    if (
        isinstance(spec, ETFSpec)
        and spec.total_expense_ratio is not None
        and not (Decimal(0) <= spec.total_expense_ratio < Decimal(1))
    ):
        failures.append(
            f"ETFSpec.total_expense_ratio must be in [0, 1) (got {spec.total_expense_ratio})"
        )

    if isinstance(spec, IndexSpec) and spec.num_components is not None and spec.num_components < 1:
        failures.append(f"IndexSpec.num_components must be >= 1 (got {spec.num_components})")

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


def validate_instrument(instrument: Instrument) -> ValidationResult:
    """Validate an ``Instrument`` against domain business rules.

    Checks cross-field consistency that cannot be expressed in any individual
    field's ``__post_init__``.

    Rules enforced:
    - ``name`` must not be blank (already in ``Instrument.__post_init__``).
    - ``asset_class`` must be consistent with the ``ContractSpec`` type.
    - ``instrument_type`` must be consistent with ``asset_class``.

    Args:
        instrument: The instrument to validate.

    Returns:
        A ``ValidationResult`` — valid when no rules are violated.
    """
    failures: list[str] = []

    # name already validated in __post_init__; double-check defensively
    if not instrument.name.strip():
        failures.append("Instrument.name must not be empty")

    # asset_class ↔ ContractSpec type consistency
    spec = instrument.contract
    expected_spec_type = _ASSET_CLASS_TO_SPEC_TYPE.get(instrument.asset_class)
    if expected_spec_type is not None and not isinstance(spec, expected_spec_type):
        failures.append(
            f"Instrument with asset_class={instrument.asset_class.value!r} "
            f"must have a {expected_spec_type.__name__} contract spec, "
            f"got {type(spec).__name__}"
        )

    # instrument_type ↔ asset_class consistency
    allowed_types = _ASSET_CLASS_TO_INSTRUMENT_TYPES.get(instrument.asset_class, frozenset())
    if allowed_types and instrument.instrument_type not in allowed_types:
        failures.append(
            f"instrument_type={instrument.instrument_type.value!r} is not valid "
            f"for asset_class={instrument.asset_class.value!r}"
        )

    # also validate the contract spec itself
    contract_result = validate_contract(instrument.contract)
    if not contract_result.is_valid:
        failures.extend(contract_result.failures)

    return ValidationResult.ok() if not failures else ValidationResult.failed(*failures)


# ── Internal mapping tables ────────────────────────────────────────────────────

from athena.assets.classification import InstrumentType  # noqa: E402

_ASSET_CLASS_TO_SPEC_TYPE: dict[AssetClass, type[ContractSpec]] = {
    AssetClass.EQUITY: EquitySpec,
    AssetClass.INDEX: IndexSpec,
    AssetClass.DERIVATIVE: (FuturesSpec, OptionsSpec),  # type: ignore[dict-item]
    AssetClass.ETF: ETFSpec,
    AssetClass.CURRENCY: CurrencySpec,
    AssetClass.COMMODITY: CommoditySpec,
}

_EQUITY_TYPES = frozenset({InstrumentType.COMMON_STOCK, InstrumentType.PREFERRED_STOCK})
_INDEX_TYPES = frozenset(
    {
        InstrumentType.BROAD_MARKET_INDEX,
        InstrumentType.SECTOR_INDEX,
        InstrumentType.STRATEGY_INDEX,
        InstrumentType.THEMATIC_INDEX,
    }
)
_DERIVATIVE_TYPES = frozenset(
    {
        InstrumentType.FUTURES,
        InstrumentType.CALL_OPTION,
        InstrumentType.PUT_OPTION,
    }
)
_ETF_TYPES = frozenset(
    {
        InstrumentType.EQUITY_ETF,
        InstrumentType.DEBT_ETF,
        InstrumentType.GOLD_ETF,
        InstrumentType.COMMODITY_ETF,
        InstrumentType.INTERNATIONAL_ETF,
    }
)
_CURRENCY_TYPES = frozenset(
    {
        InstrumentType.FX_SPOT,
        InstrumentType.FX_FUTURES,
        InstrumentType.FX_OPTIONS,
    }
)
_COMMODITY_TYPES = frozenset(
    {
        InstrumentType.COMMODITY_FUTURES,
        InstrumentType.COMMODITY_SPOT,
        InstrumentType.COMMODITY_OPTIONS,
    }
)

_ASSET_CLASS_TO_INSTRUMENT_TYPES: dict[AssetClass, frozenset[InstrumentType]] = {
    AssetClass.EQUITY: _EQUITY_TYPES,
    AssetClass.INDEX: _INDEX_TYPES,
    AssetClass.DERIVATIVE: _DERIVATIVE_TYPES,
    AssetClass.ETF: _ETF_TYPES,
    AssetClass.CURRENCY: _CURRENCY_TYPES,
    AssetClass.COMMODITY: _COMMODITY_TYPES,
}
