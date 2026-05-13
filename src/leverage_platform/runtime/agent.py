"""`@agent` decorator — wraps an async function as an audited agent.

Contract (v0): one `@agent` function makes exactly one LLM call (via
`AgentContext.invoke_llm`) and returns a Pydantic value matching the
declared `schema`. The decorator handles:

- AgentRun row open/close
- Output validation against `schema`
- Output hash computation
- Retry per `RetryConfig`
- Pydantic-validation failures are never retried (per ADR retry table)
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel

from leverage_platform._hashing import hash_output
from leverage_platform.runtime.retry import DEFAULT_RETRY, RetryConfig, with_retry
from leverage_platform.schemas import AgentRun

if TYPE_CHECKING:
    from leverage_platform.runtime.context import AgentContext


type AgentFunc[T: BaseModel] = Callable[..., Awaitable[T]]


def agent[T: BaseModel](
    *,
    name: str,
    schema: type[T],
    prompt_name: str | None = None,
    retry: RetryConfig | None = None,
) -> Callable[[AgentFunc[T]], AgentFunc[T]]:
    """Decorate an async function as a platform agent.

    Required:
      name:        unique agent identifier (becomes `AgentRun.agent_name`)
      schema:      Pydantic class the function must return

    Optional:
      prompt_name: if provided, falls back when the function body forgets to
                   pass a `prompt_name` to `ctx.invoke_llm()`. Lets simple
                   agents inherit a stable identifier without restating it.
      retry:       per-agent retry config; defaults to PLAN.md defaults
    """
    retry_cfg = retry or DEFAULT_RETRY

    def decorator(func: AgentFunc[T]) -> AgentFunc[T]:
        @functools.wraps(func)
        async def wrapper(ctx: AgentContext, *args: Any, **kwargs: Any) -> T:
            run_id = uuid4()
            started_at = datetime.now(UTC)

            # Open the AgentRun row in pending state. Fields will be filled
            # in once the function body completes and the LLM metadata is known.
            pending = AgentRun(
                id=run_id,
                tenant_id=ctx.tenant_id,
                workflow_run_id=ctx.workflow_run_id,
                agent_name=name,
                prompt_name=prompt_name or name,
                prompt_hash="",
                prompt_version=None,
                input_hash="",
                output_hash="",
                model="",
                model_parameters={},
                input_tokens=0,
                output_tokens=0,
                cost_usd=0,
                latency_ms=0,
                status="pending",
                error=None,
                started_at=started_at,
                ended_at=None,
            )
            await ctx.store.insert_agent_run(pending)

            ctx.last_llm_call = None  # reset so we detect missing invoke_llm

            async def _run() -> T:
                return await func(ctx, *args, **kwargs)

            try:
                value = await with_retry(_run, config=retry_cfg)
            except BaseException as exc:  # noqa: BLE001 — record then re-raise
                await ctx.store.update_agent_run(
                    run_id,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                    ended_at=datetime.now(UTC),
                )
                raise

            # Coerce/validate the return value against the declared schema.
            if isinstance(value, schema):
                validated = value
            else:
                validated = schema.model_validate(value)

            meta = ctx.last_llm_call
            if meta is None:
                # Agent didn't call invoke_llm; we can't audit prompt/model — fail loud.
                await ctx.store.update_agent_run(
                    run_id,
                    status="failed",
                    error="agent did not call ctx.invoke_llm; cannot audit",
                    ended_at=datetime.now(UTC),
                )
                raise RuntimeError(
                    f"agent '{name}' returned without calling ctx.invoke_llm; "
                    "platform cannot audit. Make exactly one LLM call per agent."
                )

            output_hash = hash_output(validated.model_dump(mode="json"))
            ended_at = datetime.now(UTC)

            await ctx.store.update_agent_run(
                run_id,
                status="succeeded",
                prompt_hash=meta.prompt_hash,
                # prompt_version is set during init only; allow refining here if needed
                input_hash=meta.input_hash,
                output_hash=output_hash,
                model=meta.model,
                model_parameters=meta.model_parameters,
                input_tokens=meta.input_tokens,
                output_tokens=meta.output_tokens,
                cost_usd=meta.cost_usd,
                latency_ms=meta.latency_ms,
                ended_at=ended_at,
            )

            return validated

        # Expose the agent metadata for introspection / tests.
        wrapper._agent_name = name  # type: ignore[attr-defined]
        wrapper._agent_schema = schema  # type: ignore[attr-defined]
        wrapper._agent_prompt_name = prompt_name  # type: ignore[attr-defined]
        wrapper._agent_retry = retry_cfg  # type: ignore[attr-defined]
        return wrapper

    return decorator
