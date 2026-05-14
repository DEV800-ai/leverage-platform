"""OpenAIProvider — concrete LLMProvider implementation using the openai SDK.

Uses `response_format={"type": "json_schema", ...}` for structured outputs.
Pydantic validates the returned JSON; ValidationError propagates per the
platform's retry policy (never retried for semantic bugs).

`strict_json` defaults to False because Pydantic schemas with optional
fields (`field: T | None = None`) are not compatible with OpenAI's strict
mode unless preprocessed (strict mode requires every field to be
required). Set strict_json=True at construction if your schemas are
strict-mode-compatible — adherence is then enforced server-side.

Pricing table is hardcoded for known model aliases and dated variants.
Unknown models fall back to Decimal("0") with a warning.
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any

import openai
from pydantic import BaseModel

from leverage_platform.llm.provider import (
    LLMParameters,
    StructuredResult,
    TextResult,
)

logger = logging.getLogger(__name__)

# Pricing in USD per 1K tokens. Update as OpenAI publishes new tiers.
# Tuple is (input_per_1k, output_per_1k).
OPENAI_PRICING: dict[str, tuple[Decimal, Decimal]] = {
    "gpt-4o": (Decimal("0.0025"), Decimal("0.010")),
    "gpt-4o-2024-11-20": (Decimal("0.0025"), Decimal("0.010")),
    "gpt-4o-2024-08-06": (Decimal("0.0025"), Decimal("0.010")),
    "gpt-4o-2024-05-13": (Decimal("0.005"), Decimal("0.015")),
    "gpt-4o-mini": (Decimal("0.00015"), Decimal("0.0006")),
    "gpt-4o-mini-2024-07-18": (Decimal("0.00015"), Decimal("0.0006")),
    "gpt-4.1": (Decimal("0.002"), Decimal("0.008")),
    "gpt-4.1-mini": (Decimal("0.0004"), Decimal("0.0016")),
    "gpt-4.1-nano": (Decimal("0.0001"), Decimal("0.0004")),
    "o1": (Decimal("0.015"), Decimal("0.060")),
    "o1-mini": (Decimal("0.003"), Decimal("0.012")),
}

DEFAULT_MODEL = "gpt-4o"


def _cost_usd(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Compute cost in USD for an OpenAI call. Unknown models return 0 with a warning."""
    pricing = OPENAI_PRICING.get(model)
    if pricing is None:
        # Try a prefix match for dated variants we haven't enumerated.
        for known, prices in OPENAI_PRICING.items():
            if model.startswith(known):
                pricing = prices
                break
    if pricing is None:
        logger.warning("Unknown OpenAI model %s; cost will be reported as 0.", model)
        return Decimal("0")
    in_price, out_price = pricing
    return (Decimal(input_tokens) * in_price + Decimal(output_tokens) * out_price) / Decimal(1000)


class OpenAIProvider:
    """LLM provider backed by the official `openai` SDK."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
        strict_json: bool = False,
    ) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._default_model = default_model
        self._strict_json = strict_json
        self.name = "openai"

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
            "messages": [{"role": "user", "content": prompt}],
        }
        if params.temperature is not None:
            kwargs["temperature"] = params.temperature
        if params.max_tokens is not None:
            kwargs["max_completion_tokens"] = params.max_tokens
        if params.top_p is not None:
            kwargs["top_p"] = params.top_p
        if params.stop_sequences:
            kwargs["stop"] = params.stop_sequences
        if params.provider_specific:
            kwargs.update(params.provider_specific)

        t0 = time.monotonic()
        response = await self._client.chat.completions.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)

        message = response.choices[0].message
        text = message.content or ""

        usage = response.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0

        return TextResult(
            text=text,
            model=response.model,
            provider=self.name,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=_cost_usd(response.model, in_tok, out_tok),
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

        json_schema = schema.model_json_schema()

        kwargs: dict[str, Any] = {
            "model": m,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": json_schema,
                    "strict": self._strict_json,
                },
            },
        }
        if params.temperature is not None:
            kwargs["temperature"] = params.temperature
        if params.max_tokens is not None:
            kwargs["max_completion_tokens"] = params.max_tokens
        if params.top_p is not None:
            kwargs["top_p"] = params.top_p
        if params.stop_sequences:
            kwargs["stop"] = params.stop_sequences
        if params.provider_specific:
            kwargs.update(params.provider_specific)

        t0 = time.monotonic()
        response = await self._client.chat.completions.create(**kwargs)
        latency_ms = int((time.monotonic() - t0) * 1000)

        message = response.choices[0].message
        content = message.content or ""
        if not content:
            raise ValueError(
                f"OpenAI response contained no JSON content; "
                f"model={response.model}, finish_reason={response.choices[0].finish_reason}"
            )

        # Pydantic validates here. ValidationError propagates per ADR retry policy.
        value = schema.model_validate_json(content)

        usage = response.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0

        return StructuredResult[schema](
            value=value,
            model=response.model,
            provider=self.name,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=_cost_usd(response.model, in_tok, out_tok),
            latency_ms=latency_ms,
            raw_response={
                "id": response.id,
                "finish_reason": response.choices[0].finish_reason,
            },
        )
