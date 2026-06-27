"""Structured logging context management.

Provides async-safe correlation ID and request ID tracking using Python's
``contextvars.ContextVar``. Context variables are isolated per-task in
asyncio — when a new ``Task`` is created, asyncio copies the current
``Context``, giving each task its own independent values.

Why ``ContextVar`` and not ``threading.local``?
    In an async application, many coroutines share a single OS thread.
    ``threading.local`` stores state per-thread, so all coroutines sharing
    that thread also share its ``threading.local`` values — there is no
    per-coroutine isolation. ``ContextVar`` solves this: asyncio copies the
    context snapshot for each new ``Task``, so concurrent request handlers
    never bleed correlation IDs into each other without any locking needed.

Nesting behaviour:
    ``bind_context`` saves the entire structlog context before binding new
    values and restores it on exit. This makes nesting correct::

        with bind_context(correlation_id="outer"):
            # correlation_id = "outer"
            with bind_context(correlation_id="inner"):
                # correlation_id = "inner"
            # correlation_id = "outer"  ← correctly restored

Structlog type notes:
    ``structlog.contextvars.get_contextvars()`` returns ``dict[str, Any]``
    per structlog's published type stubs. The ``# type: ignore[arg-type]``
    annotations on ``bind_contextvars(**previous_ctx)`` and
    ``bind_contextvars(**extra)`` are the minimum required suppressions for
    an API that inherently uses ``Any``. They are documented here rather
    than silently suppressed.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING
from uuid import uuid4

import structlog

if TYPE_CHECKING:
    from collections.abc import Generator

_CORRELATION_ID: ContextVar[str | None] = ContextVar("athena_correlation_id", default=None)
_REQUEST_ID: ContextVar[str | None] = ContextVar("athena_request_id", default=None)


def new_correlation_id() -> str:
    """Generate a new UUID-based correlation ID.

    Returns:
        A UUID4 string suitable for use as a correlation ID.
    """
    return str(uuid4())


def set_correlation_id(correlation_id: str) -> Token[str | None]:
    """Set the correlation ID for the current async context.

    Store the returned token and pass it to ``_CORRELATION_ID.reset(token)``
    to restore the previous value when the scope exits. Prefer
    ``bind_context`` for automatic cleanup.

    Args:
        correlation_id: The correlation ID to set.

    Returns:
        A reset token for restoring the previous value.
    """
    return _CORRELATION_ID.set(correlation_id)


def get_correlation_id() -> str | None:
    """Return the correlation ID for the current async context.

    Returns:
        The current correlation ID, or ``None`` if not set.
    """
    return _CORRELATION_ID.get()


def set_request_id(request_id: str) -> Token[str | None]:
    """Set the request ID for the current async context.

    Args:
        request_id: The request ID to set.

    Returns:
        A reset token for restoring the previous value.
    """
    return _REQUEST_ID.set(request_id)


def get_request_id() -> str | None:
    """Return the request ID for the current async context.

    Returns:
        The current request ID, or ``None`` if not set.
    """
    return _REQUEST_ID.get()


@contextmanager
def bind_context(
    *,
    correlation_id: str | None = None,
    request_id: str | None = None,
    **extra: object,
) -> Generator[None, None, None]:
    """Context manager that binds structured log context for its duration.

    On enter:
        - Sets the correlation ID (generates a UUID4 if not provided).
        - Optionally sets a request ID.
        - Binds all values into structlog's context variable store.

    On exit (including on exception):
        - Resets the ``ContextVar`` values via token.
        - Restores the structlog context to its pre-entry state.

    Args:
        correlation_id: Correlation ID to use. A new UUID4 is generated
            when not provided, ensuring every scope has a tracing ID.
        request_id: Optional request-scoped identifier (e.g., an HTTP
            request ID, an order ID, or a signal ID).
        **extra: Additional key-value pairs to bind into structlog's
            context variables for the duration of the block.

    Yields:
        ``None``. All effects are on the structured log context.

    Example::

        async def handle_order(order_id: str) -> None:
            with bind_context(correlation_id=new_correlation_id(),
                              request_id=order_id,
                              engine="trading"):
                log.info("order.processing")   # includes all three fields
    """
    cid = correlation_id or new_correlation_id()

    previous_ctx: dict[str, object] = {
        k: v  # type: ignore[misc]
        for k, v in structlog.contextvars.get_contextvars().items()
    }

    cid_token = _CORRELATION_ID.set(cid)
    rid_token: Token[str | None] | None = None

    new_ctx: dict[str, object] = {"correlation_id": cid}
    if request_id is not None:
        rid_token = _REQUEST_ID.set(request_id)
        new_ctx["request_id"] = request_id
    if extra:
        new_ctx.update(extra)

    structlog.contextvars.bind_contextvars(**new_ctx)  # type: ignore[arg-type]

    try:
        yield
    finally:
        _CORRELATION_ID.reset(cid_token)
        if rid_token is not None:
            _REQUEST_ID.reset(rid_token)
        structlog.contextvars.clear_contextvars()
        if previous_ctx:
            structlog.contextvars.bind_contextvars(  # type: ignore[arg-type]
                **previous_ctx
            )
