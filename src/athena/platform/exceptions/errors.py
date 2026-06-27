"""Platform exception hierarchy.

All exceptions inherit from ``AthenaError``, which stores arbitrary
keyword context for structured logging without using ``Any``.

Every exception carries three standard fields:

- ``message``: Human-readable description of what went wrong.
- ``error_code``: Optional machine-readable identifier (e.g. ``CFG_001``).
- ``context``: Key-value pairs providing diagnostic detail.

Usage::

    raise ConfigurationError(
        "ATHENA_DATABASE__HOST is required in production",
        error_code="CFG_001",
        environment="production",
        missing_key="ATHENA_DATABASE__HOST",
    )

Design rationale — ``**context: object`` instead of ``**context: Any``:
    ``object`` is the root of Python's type hierarchy. Every Python value
    is an ``object``, so the signature accepts any value without disabling
    mypy's type checking. Callers that read a value back from
    ``self.context`` must narrow the type, which is intentional: exception
    context is diagnostic data consumed by log handlers, not by algorithm.
"""

from __future__ import annotations


class AthenaError(Exception):
    """Root exception for all Athena platform errors.

    All exceptions raised by Athena subclass this type, enabling callers
    to catch the entire exception hierarchy with a single clause.

    Attributes:
        message: Human-readable description of the error.
        error_code: Optional machine-readable identifier for this class
            of error.
        context: Key-value pairs providing diagnostic detail. Typed as
            ``dict[str, object]`` to avoid ``Any``.

    Args:
        message: Human-readable description of the error.
        error_code: Optional machine-readable identifier.
        **context: Arbitrary key-value diagnostic context.

    Example::

        raise AthenaError(
            "Unexpected state encountered",
            error_code="ATH_001",
            component="data_engine",
            symbol="NSE:NIFTY50-INDEX",
        )
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        **context: object,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context: dict[str, object] = dict(context)

    def to_dict(self) -> dict[str, object]:
        """Serialise the exception to a structured dictionary.

        Suitable for passing directly to structlog's log methods or for
        JSON serialisation in API error responses.

        Returns:
            A dictionary with ``error_type``, ``message``, ``error_code``,
            and ``context`` keys.

        Example::

            except AthenaError as exc:
                log.error("request.failed", **exc.to_dict())
        """
        return {
            "error_type": type(self).__name__,
            "message": self.message,
            "error_code": self.error_code,
            "context": self.context,
        }

    def __repr__(self) -> str:
        parts = [repr(self.message)]
        if self.error_code is not None:
            parts.append(f"error_code={self.error_code!r}")
        for key, value in self.context.items():
            parts.append(f"{key}={value!r}")
        return f"{type(self).__name__}({', '.join(parts)})"


class ConfigurationError(AthenaError):
    """Raised when platform configuration is invalid or incomplete.

    The platform validates all configuration at startup and raises this
    exception before any engine initialises. This ensures that silent
    misconfiguration cannot cause runtime failures during trading hours.

    Args:
        message: Description of the configuration problem.
        error_code: Optional error code (prefix: ``CFG``).
        **context: Key-value pairs identifying the offending setting,
            e.g. ``missing_key="ATHENA_DATABASE__HOST"``.
    """


class ValidationError(AthenaError):
    """Raised when runtime data fails schema or business-rule validation.

    Distinct from ``ConfigurationError`` (startup-time settings) and
    from pydantic's ``ValidationError`` (schema validation). This type
    represents domain-level validation failures during normal operation,
    such as an invalid tick price, a malformed instrument symbol, or a
    signal with contradictory parameters.

    Args:
        message: Description of the validation failure.
        error_code: Optional error code (prefix: ``VAL``).
        **context: Key-value pairs describing the invalid data.
    """


class InfrastructureError(AthenaError):
    """Raised when a required infrastructure component is unavailable.

    Examples: database connection failure, Redis unavailability, message
    bus partition. Callers should treat this as a transient failure
    unless the ``error_code`` indicates a permanent condition.

    Args:
        message: Description of the infrastructure problem.
        error_code: Optional error code (prefix: ``INF``).
        **context: Component identifier, retry count, last error, etc.
    """


class ExternalServiceError(InfrastructureError):
    """Raised when a call to an external service fails.

    Subclasses ``InfrastructureError`` because a failing external service
    (broker API, data vendor, market data feed) is a form of infrastructure
    unavailability. Carries additional context about the specific service
    and failed operation.

    Args:
        message: Description of the external service failure.
        error_code: Optional error code (prefix: ``EXT``).
        **context: Service name, endpoint, HTTP status, response body, etc.
    """


class DataIntegrityError(AthenaError):
    """Raised when data fails integrity or consistency checks.

    Covers higher-level consistency failures beyond schema validation:
    audit log hash-chain breaks, position reconciliation divergences,
    detected data tampering, or time-series gaps in market data that
    should be contiguous.

    Args:
        message: Description of the integrity violation.
        error_code: Optional error code (prefix: ``DIG``).
        **context: Details identifying the affected records or sequences.
    """


class NotImplementedFeatureError(AthenaError):
    """Raised when a planned but not yet implemented feature is invoked.

    Prefer this over Python's built-in ``NotImplementedError`` so that
    callers and monitoring systems can distinguish between abstract method
    stubs (which should never reach production code paths) and legitimately
    deferred features with a known delivery timeline.

    Attributes:
        feature: The name or description of the unimplemented feature.
        planned_sprint: Optional sprint identifier for delivery planning.

    Args:
        feature: Name or description of the unimplemented feature.
        error_code: Optional error code (prefix: ``NIF``).
        planned_sprint: Optional sprint identifier (e.g. ``"sprint-3"``).
        **context: Additional diagnostic context.

    Example::

        raise NotImplementedFeatureError(
            "ML-based signal confidence scoring",
            planned_sprint="sprint-5",
            engine="intelligence",
        )
    """

    def __init__(
        self,
        feature: str,
        *,
        error_code: str | None = None,
        planned_sprint: str | None = None,
        **context: object,
    ) -> None:
        extra: dict[str, object] = {"feature": feature, **context}
        if planned_sprint is not None:
            extra["planned_sprint"] = planned_sprint

        super().__init__(
            f"Feature not yet implemented: {feature}",
            error_code=error_code,
            **extra,
        )
        self.feature = feature
        self.planned_sprint = planned_sprint
