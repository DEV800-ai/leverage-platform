"""MockLLMProvider — deterministic provider for unit tests. No network calls.

Tests that want to exercise the platform without burning Anthropic tokens
should use this provider.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from leverage_platform.llm.provider import (
    LLMParameters,
    StructuredResult,
    TextResult,
)


class MockLLMProvider:
    """Deterministic LLM provider for tests.

    Callers register response factories per (model, schema) pair, or pass a
    single default factory. Token counts and cost are synthetic.
    """

    def __init__(
        self,
        *,
        default_text: str = "mock response",
        structured_factory: Callable[[type[BaseModel], str], BaseModel] | None = None,
        model: str = "mock-model",
        input_tokens: int = 100,
        output_tokens: int = 50,
        cost_usd: Decimal = Decimal("0.000100"),
        latency_ms: int = 10,
    ) -> None:
        self._default_text = default_text
        self._structured_factory = structured_factory
        self._model = model
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._cost_usd = cost_usd
        self._latency_ms = latency_ms
        self.calls: list[dict[str, Any]] = []

    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> TextResult:
        self.calls.append(
            {"method": "generate_text", "prompt": prompt, "model": model, "parameters": parameters}
        )
        return TextResult(
            text=self._default_text,
            model=model or self._model,
            provider="mock",
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            cost_usd=self._cost_usd,
            latency_ms=self._latency_ms,
        )

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> StructuredResult[T]:
        self.calls.append(
            {
                "method": "generate_structured",
                "prompt": prompt,
                "schema": schema.__name__,
                "model": model,
                "parameters": parameters,
            }
        )

        if self._structured_factory is None:
            raise ValueError(
                "MockLLMProvider was called with generate_structured but no "
                "structured_factory was provided. Set one in the test setup."
            )

        value = self._structured_factory(schema, prompt)
        if not isinstance(value, schema):
            raise TypeError(
                f"structured_factory returned {type(value).__name__}, expected {schema.__name__}"
            )

        return StructuredResult[schema](
            value=value,
            model=model or self._model,
            provider="mock",
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            cost_usd=self._cost_usd,
            latency_ms=self._latency_ms,
        )
