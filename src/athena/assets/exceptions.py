"""Asset-domain exception hierarchy.

All asset exceptions inherit from ``AssetError``, which itself inherits
from ``AthenaError``. This allows callers to catch all asset failures with
a single clause while discriminating on subtype for specific handling.

Hierarchy::

    AthenaError
    └── AssetError
        ├── InvalidIdentifierError   — malformed identifier string
        ├── InvalidInstrumentError   — instrument fails domain rules
        ├── InvalidContractSpecError — contract spec violates constraints
        ├── InstrumentNotFoundError  — registry lookup found nothing
        ├── DuplicateInstrumentError — registry insert found a collision
        ├── InstrumentExpiredError   — operation attempted on expired instrument
        └── UnsupportedAssetClassError — asset class not yet implemented
"""

from __future__ import annotations

from athena.platform.exceptions import AthenaError


class AssetError(AthenaError):
    """Root exception for all asset-domain errors.

    Args:
        message: Human-readable description of the failure.
        error_code: Optional machine-readable code (prefix: ``AST``).
        **context: Diagnostic key-value pairs.
    """


class InvalidIdentifierError(AssetError):
    """Raised when an identifier string fails format or checksum validation.

    Examples include an ISIN with a bad check digit, a Symbol without the
    required ``EXCHANGE:TICKER`` separator, or an InstrumentId that is not a
    valid UUID.

    Args:
        identifier: The raw string that failed validation.
        reason: Human-readable explanation of the failure.
        **context: Additional diagnostic context.
    """

    def __init__(self, identifier: str, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid identifier {identifier!r}: {reason}",
            error_code="AST_001",
            identifier=identifier,
            reason=reason,
            **context,
        )
        self.identifier = identifier
        self.reason = reason


class InvalidInstrumentError(AssetError):
    """Raised when an ``Instrument`` value object violates domain rules.

    This covers cross-field consistency failures that cannot be expressed
    in a single field's ``__post_init__`` — for example, an Options contract
    with a ``ContractSpec`` type that does not match ``AssetClass.DERIVATIVE``.

    Args:
        message: Description of which rule was violated.
        **context: Additional diagnostic context (field names, values).
    """

    def __init__(self, message: str, **context: object) -> None:
        super().__init__(message, error_code="AST_002", **context)


class InvalidContractSpecError(AssetError):
    """Raised when a ``ContractSpec`` subclass fails its own validation.

    Examples: negative lot size, zero tick size, strike price <= 0 on an
    option, or an expiry date that pre-dates the instrument's listing.

    Args:
        field: The name of the field that is invalid.
        value: The offending value (typed as ``object`` to avoid ``Any``).
        reason: Explanation of the constraint that was violated.
        **context: Additional diagnostic context.
    """

    def __init__(self, field: str, value: object, reason: str, **context: object) -> None:
        super().__init__(
            f"Invalid contract spec — {field}={value!r}: {reason}",
            error_code="AST_003",
            field=field,
            value=value,
            reason=reason,
            **context,
        )
        self.field = field
        self.value = value
        self.reason = reason


class InstrumentNotFoundError(AssetError):
    """Raised when an instrument registry lookup finds no matching record.

    Args:
        lookup_key: The identifier or symbol used in the lookup.
        lookup_type: How the lookup was attempted (``"id"``, ``"symbol"``,
            ``"isin"``).
        **context: Additional diagnostic context.
    """

    def __init__(
        self,
        lookup_key: str,
        lookup_type: str = "id",
        **context: object,
    ) -> None:
        super().__init__(
            f"Instrument not found by {lookup_type}: {lookup_key!r}",
            error_code="AST_004",
            lookup_key=lookup_key,
            lookup_type=lookup_type,
            **context,
        )
        self.lookup_key = lookup_key
        self.lookup_type = lookup_type


class DuplicateInstrumentError(AssetError):
    """Raised when an instrument is registered but its key already exists.

    Args:
        instrument_id: String representation of the conflicting id.
        **context: Additional diagnostic context.
    """

    def __init__(self, instrument_id: str, **context: object) -> None:
        super().__init__(
            f"Instrument already registered: {instrument_id!r}",
            error_code="AST_005",
            instrument_id=instrument_id,
            **context,
        )
        self.instrument_id = instrument_id


class InstrumentExpiredError(AssetError):
    """Raised when an operation is attempted on a derivative past its expiry date.

    Args:
        symbol: String representation of the expired instrument's symbol.
        expiry: ISO-formatted expiry date string.
        **context: Additional diagnostic context.
    """

    def __init__(self, symbol: str, expiry: str, **context: object) -> None:
        super().__init__(
            f"Instrument {symbol!r} expired on {expiry}",
            error_code="AST_006",
            symbol=symbol,
            expiry=expiry,
            **context,
        )
        self.symbol = symbol
        self.expiry = expiry


class UnsupportedAssetClassError(AssetError):
    """Raised when an operation is not yet implemented for a given asset class.

    Args:
        asset_class: Name of the unsupported asset class.
        operation: Description of the attempted operation.
        **context: Additional diagnostic context.
    """

    def __init__(self, asset_class: str, operation: str, **context: object) -> None:
        super().__init__(
            f"Asset class {asset_class!r} not supported for: {operation}",
            error_code="AST_007",
            asset_class=asset_class,
            operation=operation,
            **context,
        )
        self.asset_class = asset_class
        self.operation = operation
