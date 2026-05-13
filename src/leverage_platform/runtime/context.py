"""AgentContext — carries platform plumbing into every `@agent` call.

The context is the first argument of every `@agent` function (ADR-010). It
holds the provider, store, tenant id, and current workflow id, and offers
`invoke_llm()` — the canonical way for agents to call the LLM so the platform
captures all audit metadata in one place.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel

from leverage_platform._hashing import hash_inputs, hash_template
from leverage_platform.llm.provider import LLMParameters, StructuredResult

if TYPE_CHECKING:
    from leverage_platform.llm.provider import LLMProvider
    from leverage_platform.storage.protocol import Store


@dataclass
class LLMCallMetadata:
    """Audit metadata produced by one `invoke_llm` call."""

    prompt_name: str
    prompt_hash: str
    prompt_version: str | None
    input_hash: str
    model: str
    model_parameters: dict[str, Any]
    input_tokens: int
    output_tokens: int
    cost_usd: Any  # Decimal — avoid importing for typing only
    latency_ms: int


@dataclass
class AgentContext:
    """Per-call context threaded by the runtime into every `@agent` function.

    Created by the runtime (workflow or direct caller); agents read from it,
    `invoke_llm()` writes to it. The `@agent` decorator reads the last LLM
    call's metadata to populate the AgentRun row.
    """

    tenant_id: str
    provider: LLMProvider
    store: Store
    workflow_run_id: UUID | None = None

    # Set by invoke_llm; read by the @agent decorator on completion.
    last_llm_call: LLMCallMetadata | None = field(default=None, init=False, repr=False)

    async def invoke_llm[T: BaseModel](
        self,
        *,
        template: str,
        variables: dict[str, Any],
        schema: type[T],
        prompt_name: str,
        prompt_version: str | None = None,
        rendered_prompt: str | None = None,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> StructuredResult[T]:
        """Canonical LLM invocation that captures audit metadata onto the context.

        - `template` is the raw template string (hashed for prompt_hash, ADR-003).
        - `variables` are the inputs (hashed for input_hash).
        - `rendered_prompt` is the final string sent to the LLM. If omitted, the
          template is rendered with `template.format(**variables)`.
        """
        prompt_hash = hash_template(template)
        input_hash = hash_inputs(variables)
        prompt = rendered_prompt if rendered_prompt is not None else template.format(**variables)

        result = await self.provider.generate_structured(
            prompt=prompt,
            schema=schema,
            model=model,
            parameters=parameters,
        )

        model_params_dict = (
            parameters.model_dump(mode="json", exclude_none=True) if parameters else {}
        )

        self.last_llm_call = LLMCallMetadata(
            prompt_name=prompt_name,
            prompt_hash=prompt_hash,
            prompt_version=prompt_version,
            input_hash=input_hash,
            model=result.model,
            model_parameters=model_params_dict,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
        )
        return result
