"""Retry policy for `@agent` calls.

Per PLAN.md retry-policy table:
  - Retry: network timeouts, HTTP 429, HTTP 5xx, provider JSON-parse failures.
  - Do NOT retry: Pydantic validation failures, HTTP 4xx (other than 429),
    user-cancelled, eval failures.

Backoff: exponential with jitter, base 1s, factor 2, jitter ±25%, capped 30s.
Max retries: 2 (configurable per-agent via decorator).
"""

from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Anthropic SDK exceptions we want to identify. Imported lazily to keep this
# module usable without the anthropic dep at import time.
_anthropic_imported = False
_AnthropicAPITimeoutError: type[Exception] | None = None
_AnthropicAPIConnectionError: type[Exception] | None = None
_AnthropicRateLimitError: type[Exception] | None = None
_AnthropicInternalServerError: type[Exception] | None = None
_AnthropicBadRequestError: type[Exception] | None = None


def _import_anthropic_exceptions() -> None:
    global _anthropic_imported
    global _AnthropicAPITimeoutError
    global _AnthropicAPIConnectionError
    global _AnthropicRateLimitError
    global _AnthropicInternalServerError
    global _AnthropicBadRequestError
    if _anthropic_imported:
        return
    try:
        import anthropic

        _AnthropicAPITimeoutError = anthropic.APITimeoutError
        _AnthropicAPIConnectionError = anthropic.APIConnectionError
        _AnthropicRateLimitError = anthropic.RateLimitError
        _AnthropicInternalServerError = anthropic.InternalServerError
        _AnthropicBadRequestError = anthropic.BadRequestError
    except Exception:  # noqa: BLE001 — anthropic optional at import time
        pass
    _anthropic_imported = True


@dataclass(frozen=True)
class RetryConfig:
    """Per-agent retry configuration. Defaults match PLAN.md."""

    max_retries: int = 2
    base_delay_s: float = 1.0
    factor: float = 2.0
    jitter: float = 0.25
    max_delay_s: float = 30.0


DEFAULT_RETRY = RetryConfig()


def is_retryable(exc: BaseException) -> bool:
    """Classify whether an exception should trigger a retry per ADR retry table."""
    _import_anthropic_exceptions()

    # Never retry on user cancellation.
    if isinstance(exc, asyncio.CancelledError):
        return False

    # Pydantic validation failures are semantic bugs — never retry.
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        return False

    # JSON parse failures from the provider are retryable.
    if isinstance(exc, json.JSONDecodeError):
        return True

    # Anthropic SDK exceptions.
    if _AnthropicRateLimitError and isinstance(exc, _AnthropicRateLimitError):
        return True
    if _AnthropicInternalServerError and isinstance(exc, _AnthropicInternalServerError):
        return True
    if _AnthropicAPITimeoutError and isinstance(exc, _AnthropicAPITimeoutError):
        return True
    if _AnthropicAPIConnectionError and isinstance(exc, _AnthropicAPIConnectionError):
        return True
    if _AnthropicBadRequestError and isinstance(exc, _AnthropicBadRequestError):
        return False  # 4xx other than 429 — not retryable

    # Generic timeout / connection exceptions.
    if isinstance(exc, TimeoutError | ConnectionError):
        return True

    # Default: do not retry unknown exceptions. Better to surface than re-burn tokens.
    return False


def _backoff_delay(attempt: int, cfg: RetryConfig) -> float:
    """Compute delay for the given attempt number (0-indexed for the first retry)."""
    delay = cfg.base_delay_s * (cfg.factor**attempt)
    jitter = delay * cfg.jitter
    delay += random.uniform(-jitter, jitter)
    return min(max(0.0, delay), cfg.max_delay_s)


async def with_retry[T](
    fn: Callable[[], Awaitable[T]],
    *,
    config: RetryConfig = DEFAULT_RETRY,
) -> T:
    """Run an async callable, retrying transient failures per `config`."""
    last_exc: BaseException | None = None
    for attempt in range(config.max_retries + 1):
        try:
            return await fn()
        except BaseException as exc:  # noqa: BLE001 — classify, re-raise non-retryable
            if not is_retryable(exc) or attempt == config.max_retries:
                raise
            last_exc = exc
            await asyncio.sleep(_backoff_delay(attempt, config))
    # Unreachable; the loop either returns or raises.
    raise RuntimeError("with_retry exhausted retries") from last_exc
