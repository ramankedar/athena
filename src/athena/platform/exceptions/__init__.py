"""Platform exception hierarchy.

Re-exports the complete exception hierarchy so callers can import from
the package root::

    from athena.platform.exceptions import AthenaError, ConfigurationError
"""

from athena.platform.exceptions.errors import (
    AthenaError,
    ConfigurationError,
    DataIntegrityError,
    ExternalServiceError,
    InfrastructureError,
    NotImplementedFeatureError,
    ValidationError,
)

__all__ = [
    "AthenaError",
    "ConfigurationError",
    "DataIntegrityError",
    "ExternalServiceError",
    "InfrastructureError",
    "NotImplementedFeatureError",
    "ValidationError",
]
