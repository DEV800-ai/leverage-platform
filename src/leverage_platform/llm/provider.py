"""LLM provider abstraction — Protocol + typed parameters + result types.

See ADR-007 for the LLMParameters design rationale.
The `embed()` method is deliberately not in v0 (vector-store concerns deferred).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class LLMParameters(BaseModel):
    """Typed parameters for LLM calls (ADR-007).

    Common fields are top-level; vendor-specific options live in `provider_specific`.
    """

    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: list[str] | None = None
    provider_specific: dict[str, Any] | None = None


class TextResult(BaseModel):
    """Result of a free-text LLM call."""

    text: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: int


class StructuredResult[T: BaseModel](BaseModel):
    """Result of a structured (Pydantic-validated) LLM call.

    The generic parameter T is the Pydantic schema the LLM was asked to produce.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    value: T
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: int
    raw_response: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """LLM provider contract. Implementations must be async.

    `embed()` is intentionally absent in v0; see PLAN.md and ADR for rationale.
    """

    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> TextResult:
        """Generate free-text completion."""
        ...

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> StructuredResult[T]:
        """Generate output validated against `schema`. Raises on validation failure."""
        ...
