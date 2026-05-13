"""Retry classification + backoff behavior."""

from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import BaseModel, ValidationError

from leverage_platform.runtime.retry import RetryConfig, is_retryable, with_retry


def test_validation_error_is_not_retryable() -> None:
    class S(BaseModel):
        x: int

    try:
        S.model_validate({"x": "not an int"})
    except ValidationError as e:
        assert is_retryable(e) is False


def test_cancelled_error_is_not_retryable() -> None:
    assert is_retryable(asyncio.CancelledError()) is False


def test_json_decode_error_is_retryable() -> None:
    try:
        json.loads("not json")
    except json.JSONDecodeError as e:
        assert is_retryable(e) is True


def test_timeout_error_is_retryable() -> None:
    assert is_retryable(TimeoutError("slow")) is True


def test_connection_error_is_retryable() -> None:
    assert is_retryable(ConnectionError("refused")) is True


def test_unknown_exception_is_not_retryable() -> None:
    """Defaults to NOT retrying unknown exceptions — better to surface than re-burn."""
    assert is_retryable(RuntimeError("???")) is False


async def test_with_retry_succeeds_on_first_attempt() -> None:
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await with_retry(fn)
    assert result == "ok"
    assert calls == 1


async def test_with_retry_retries_on_retryable_exception() -> None:
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TimeoutError("flaky")
        return "ok"

    # Use a fast config so the test doesn't sleep for real.
    config = RetryConfig(max_retries=2, base_delay_s=0.0, factor=1.0, jitter=0.0, max_delay_s=0.0)
    result = await with_retry(fn, config=config)
    assert result == "ok"
    assert calls == 3


async def test_with_retry_does_not_retry_non_retryable() -> None:
    calls = 0

    async def fn() -> None:
        nonlocal calls
        calls += 1
        raise RuntimeError("not retryable")

    config = RetryConfig(max_retries=2, base_delay_s=0.0, factor=1.0, jitter=0.0, max_delay_s=0.0)
    with pytest.raises(RuntimeError):
        await with_retry(fn, config=config)
    assert calls == 1


async def test_with_retry_exhausts_then_raises() -> None:
    calls = 0

    async def fn() -> None:
        nonlocal calls
        calls += 1
        raise TimeoutError("flaky")

    config = RetryConfig(max_retries=2, base_delay_s=0.0, factor=1.0, jitter=0.0, max_delay_s=0.0)
    with pytest.raises(TimeoutError):
        await with_retry(fn, config=config)
    assert calls == 3  # initial + 2 retries
