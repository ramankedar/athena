"""Structured logging for the Athena platform.

Re-exports the public logging API so callers can import from the package::

    from athena.platform.logging import configure_logging, get_logger
    from athena.platform.logging import bind_context, get_correlation_id
"""

from athena.platform.logging.context import (
    bind_context,
    get_correlation_id,
    get_request_id,
    new_correlation_id,
    set_correlation_id,
    set_request_id,
)
from athena.platform.logging.setup import configure_logging, get_logger

__all__ = [
    "bind_context",
    "configure_logging",
    "get_correlation_id",
    "get_logger",
    "get_request_id",
    "new_correlation_id",
    "set_correlation_id",
    "set_request_id",
]
