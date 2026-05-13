"""AnthropicProvider — concrete LLMProvider implementation using the anthropic SDK.

Uses tool_use for structured outputs: the model is told its only valid output is
a tool call whose `input` matches the requested Pydantic schema. The platform
parses and validates the resulting JSON.

Pricing table is hardcoded for known models; unknown models fall back to
Decimal("0") with a warning logged via stdlib logging.
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any

import anthropic
from pydantic import BaseModel

from leverage_platform.llm.provider import (
    LLMParameters,
    StructuredResult,
    TextResult,
)

logger = logging.getLogger(__name__)

# Pricing in USD per 1K tokens. Update as Anthropic publishes new tiers.
# Tuple is (input_per_1k, output_per_1k).
ANTHROPIC_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "claude-opus-4-7": (Decimal("0.015"), Decimal("0.075")),
    "claude-sonnet-4-6": (Decimal("0.003"), Decimal("0.015")),
    "claude-haiku-4-5-20251001": (Decimal("0.001"), Decimal("0.005")),
}

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_MAX_TOKENS = 4096


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Compute cost in USD for an Anthropic call. Unknown models return 0 with a warning."""
    pricing = ANTHROPIC_PRICING.get(model)
    if pricing is None:
        logger.warning("Unknown model %s; cost will be reported as 0.", model)
        return Decimal("0")
    in_price, out_price = pricing
    return (Decimal(input_tokens) * in_price + Decimal(output_tokens) * out_price) / Decimal(1000)


class AnthropicProvider:
    """LLM provider backed by the official `anthropic` SDK."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._default_model = default_model
        self.name = "anthropic"

    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> TextResult:
        m = model or self._default_model
        params = parameters or LLMParameters()

        kwargs: dict[str, Any] = {
            "model": m,
            "max_tokens": params.max_tokens or DEFAULT_MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if params.temperature is not None:
            kwargs["temperature"] = params.temperature
        if params.top_p is not None:
            kwargs["top_p"] = params.top_p
        if params.stop_sequences:
            kwargs["stop_sequences"] = params.stop_sequences
        if params.provider_specific:
            kwargs.update(params.provider_specific)

        t0 = time.monotonic()
        response = await self._client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)

        text_parts = [b.text for b in response.content if b.type == "text"]
        text = "".join(text_parts)

        return TextResult(
            text=text,
            model=response.model,
            provider=self.name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=_cost_usd(
                response.model, response.usage.input_tokens, response.usage.output_tokens
            ),
            latency_ms=latency_ms,
        )

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> StructuredResult[T]:
        m = model or self._default_model
        params = parameters or LLMParameters()

        tool_name = "emit_" + schema.__name__.lower()
        tool_schema = schema.model_json_schema()

        kwargs: dict[str, Any] = {
            "model": m,
            "max_tokens": params.max_tokens or DEFAULT_MAX_TOKENS,
            "tools": [
                {
                    "name": tool_name,
                    "description": f"Emit a valid {schema.__name__} object.",
                    "input_schema": tool_schema,
                }
            ],
            "tool_choice": {"type": "tool", "name": tool_name},
            "messages": [{"role": "user", "content": prompt}],
        }
        if params.temperature is not None:
            kwargs["temperature"] = params.temperature
        if params.top_p is not None:
            kwargs["top_p"] = params.top_p
        if params.stop_sequences:
            kwargs["stop_sequences"] = params.stop_sequences
        if params.provider_specific:
            kwargs.update(params.provider_specific)

        t0 = time.monotonic()
        response = await self._client.messages.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            raise ValueError(
                f"Anthropic response contained no tool_use block; model={response.model}"
            )

        # Pydantic validates here. ValidationError propagates per ADR retry policy.
        value = schema.model_validate(tool_use_blocks[0].input)

        return StructuredResult[schema](
            value=value,
            model=response.model,
            provider=self.name,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost_usd=_cost_usd(
                response.model, response.usage.input_tokens, response.usage.output_tokens
            ),
            latency_ms=latency_ms,
            raw_response={"id": response.id, "stop_reason": response.stop_reason},
        )
