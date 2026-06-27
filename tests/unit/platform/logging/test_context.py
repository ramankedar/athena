"""Unit tests for structured logging context management."""

from __future__ import annotations

import asyncio

import pytest

from athena.platform.logging.context import (
    bind_context,
    get_correlation_id,
    get_request_id,
    new_correlation_id,
    set_correlation_id,
    set_request_id,
)


class TestNewCorrelationId:
    def test_returns_string(self) -> None:
        assert isinstance(new_correlation_id(), str)

    def test_returns_non_empty_string(self) -> None:
        assert len(new_correlation_id()) > 0

    def test_returns_unique_values(self) -> None:
        ids = {new_correlation_id() for _ in range(100)}
        assert len(ids) == 100

    def test_uuid_format(self) -> None:
        cid = new_correlation_id()
        parts = cid.split("-")
        assert len(parts) == 5


class TestCorrelationId:
    def test_default_is_none(self) -> None:
        assert get_correlation_id() is None

    def test_set_and_get(self) -> None:
        token = set_correlation_id("abc-123")
        try:
            assert get_correlation_id() == "abc-123"
        finally:
            from athena.platform.logging.context import _CORRELATION_ID

            _CORRELATION_ID.reset(token)

    def test_reset_restores_none(self) -> None:
        from athena.platform.logging.context import _CORRELATION_ID

        token = set_correlation_id("abc-123")
        _CORRELATION_ID.reset(token)
        assert get_correlation_id() is None


class TestRequestId:
    def test_default_is_none(self) -> None:
        assert get_request_id() is None

    def test_set_and_get(self) -> None:
        from athena.platform.logging.context import _REQUEST_ID

        token = set_request_id("req-999")
        try:
            assert get_request_id() == "req-999"
        finally:
            _REQUEST_ID.reset(token)

    def test_reset_restores_none(self) -> None:
        from athena.platform.logging.context import _REQUEST_ID

        token = set_request_id("req-1")
        _REQUEST_ID.reset(token)
        assert get_request_id() is None


class TestBindContext:
    def test_generates_correlation_id_when_not_provided(self) -> None:
        with bind_context():
            cid = get_correlation_id()
        assert cid is not None
        assert len(cid) > 0

    def test_uses_provided_correlation_id(self) -> None:
        with bind_context(correlation_id="test-cid-123"):
            assert get_correlation_id() == "test-cid-123"

    def test_clears_correlation_id_on_exit(self) -> None:
        with bind_context(correlation_id="temp"):
            pass
        assert get_correlation_id() is None

    def test_sets_request_id(self) -> None:
        with bind_context(request_id="req-42"):
            assert get_request_id() == "req-42"

    def test_clears_request_id_on_exit(self) -> None:
        with bind_context(request_id="req-42"):
            pass
        assert get_request_id() is None

    def test_no_request_id_not_set(self) -> None:
        with bind_context(correlation_id="cid"):
            assert get_request_id() is None

    def test_restores_state_on_exception(self) -> None:
        with pytest.raises(ValueError, match="deliberate"), bind_context(correlation_id="cid-exc"):
            raise ValueError("deliberate")
        assert get_correlation_id() is None

    def test_nesting_restores_outer_correlation_id(self) -> None:
        with bind_context(correlation_id="outer"):
            assert get_correlation_id() == "outer"
            with bind_context(correlation_id="inner"):
                assert get_correlation_id() == "inner"
            assert get_correlation_id() == "outer"

    def test_nesting_restores_outer_request_id(self) -> None:
        with bind_context(request_id="outer-req"):
            assert get_request_id() == "outer-req"
            with bind_context(request_id="inner-req"):
                assert get_request_id() == "inner-req"
            assert get_request_id() == "outer-req"

    def test_extra_kwargs_do_not_affect_context_vars(self) -> None:
        with bind_context(correlation_id="cid", engine="trading", symbol="NSE:X"):
            assert get_correlation_id() == "cid"

    async def test_async_task_isolation(self) -> None:
        """Each asyncio Task gets its own context copy."""
        results: dict[str, str | None] = {}

        async def task(name: str, cid: str) -> None:
            with bind_context(correlation_id=cid):
                await asyncio.sleep(0.001)
                results[name] = get_correlation_id()

        await asyncio.gather(
            asyncio.ensure_future(task("t1", "cid-task-1")),
            asyncio.ensure_future(task("t2", "cid-task-2")),
        )

        assert results["t1"] == "cid-task-1"
        assert results["t2"] == "cid-task-2"
