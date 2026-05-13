"""`@agent` decorator — wraps an async function as an audited agent.

Contract (v0): one `@agent` function makes exactly one LLM call (via
`AgentContext.invoke_llm`) and returns a Pydantic value matching the
declared `schema`. The decorator handles:

- AgentRun row open/close
- Output validation against `schema`
- Output hash computation
- Optional Artifact persistence (when `artifact_type` is set and we're in a workflow)
- Retry per `RetryConfig`
- Pydantic-validation failures are never retried (per ADR retry table)

Exception: agents decorated with `pure=True` are not required to call
invoke_llm. They are recorded as AgentRun rows with sentinel values for
prompt/model/tokens/cost. Useful for orchestrator steps (e.g., the proof
scenario's Critic) that conditionally delegate to a nested LLM agent.
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from pydantic import BaseModel

from leverage_platform._hashing import hash_inputs, hash_output
from leverage_platform.runtime.retry import DEFAULT_RETRY, RetryConfig, with_retry
from leverage_platform.schemas import AgentRun, Artifact

if TYPE_CHECKING:
    from leverage_platform.runtime.context import AgentContext


type AgentFunc[T: BaseModel] = Callable[..., Awaitable[T]]

_PURE_SENTINEL_PROMPT_HASH = "pure:no-llm-call"
_PURE_SENTINEL_MODEL = "(none)"


def agent[T: BaseModel](
    *,
    name: str,
    schema: type[T],
    prompt_name: str | None = None,
    pure: bool = False,
    artifact_type: str | None = None,
    artifact_schema_name: str | None = None,
    retry: RetryConfig | None = None,
) -> Callable[[AgentFunc[T]], AgentFunc[T]]:
    """Decorate an async function as a platform agent.

    Required:
      name:           unique agent identifier (becomes `AgentRun.agent_name`)
      schema:         Pydantic class the function must return

    Optional:
      prompt_name:    fallback for `AgentRun.prompt_name` if the body doesn't
                      override via invoke_llm. Defaults to `name`.
      pure:           if True, the agent need not call ctx.invoke_llm.
                      AgentRun is still written with sentinel prompt/model
                      values. Use for orchestrator steps that delegate to
                      nested agents (e.g., a Critic that may call llm_judge).
      artifact_type:  if set, the decorator writes one Artifact row per call
                      (when ctx.workflow_run_id is set). Skipped outside
                      workflows.
      artifact_schema_name: override the default "<SchemaName>@v1".
      retry:          per-agent retry config; defaults to PLAN.md defaults.
    """
    retry_cfg = retry or DEFAULT_RETRY

    def decorator(func: AgentFunc[T]) -> AgentFunc[T]:
        @functools.wraps(func)
        async def wrapper(ctx: AgentContext, *args: Any, **kwargs: Any) -> T:
            run_id = uuid4()
            started_at = datetime.now(UTC)

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

            # Save+restore so nested @agent calls (e.g. llm_judge inside a
            # Critic) don't bleed their LLM metadata into the outer agent.
            prior_last_llm_call = ctx.last_llm_call
            ctx.last_llm_call = None

            async def _run() -> T:
                return await func(ctx, *args, **kwargs)

            try:
                value = await with_retry(_run, config=retry_cfg)
            except BaseException as exc:  # noqa: BLE001 — record then re-raise
                ctx.last_llm_call = prior_last_llm_call
                await ctx.store.update_agent_run(
                    run_id,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                    ended_at=datetime.now(UTC),
                )
                raise

            # Capture THIS agent's LLM call metadata, then restore outer scope.
            meta = ctx.last_llm_call
            ctx.last_llm_call = prior_last_llm_call

            # Validate / coerce the return value against the declared schema.
            if isinstance(value, schema):
                validated = value
            else:
                validated = schema.model_validate(value)

            ended_at = datetime.now(UTC)

            if meta is not None:
                # Normal path: agent called invoke_llm; use its metadata.
                await ctx.store.update_agent_run(
                    run_id,
                    status="succeeded",
                    prompt_hash=meta.prompt_hash,
                    input_hash=meta.input_hash,
                    output_hash=hash_output(validated.model_dump(mode="json")),
                    model=meta.model,
                    model_parameters=meta.model_parameters,
                    input_tokens=meta.input_tokens,
                    output_tokens=meta.output_tokens,
                    cost_usd=meta.cost_usd,
                    latency_ms=meta.latency_ms,
                    ended_at=ended_at,
                )
            elif pure:
                # Pure agent path: no invoke_llm. Record with sentinels.
                input_hash = hash_inputs(_inputs_to_dict(args, kwargs))
                await ctx.store.update_agent_run(
                    run_id,
                    status="succeeded",
                    prompt_hash=_PURE_SENTINEL_PROMPT_HASH,
                    input_hash=input_hash,
                    output_hash=hash_output(validated.model_dump(mode="json")),
                    model=_PURE_SENTINEL_MODEL,
                    model_parameters={},
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0,
                    latency_ms=0,
                    ended_at=ended_at,
                )
            else:
                # Non-pure agent that didn't call invoke_llm — bug.
                await ctx.store.update_agent_run(
                    run_id,
                    status="failed",
                    error="agent did not call ctx.invoke_llm; cannot audit",
                    ended_at=datetime.now(UTC),
                )
                raise RuntimeError(
                    f"agent '{name}' returned without calling ctx.invoke_llm; "
                    "platform cannot audit. Make exactly one LLM call per agent, "
                    "or set pure=True on the decorator if no LLM call is intended."
                )

            # Optional Artifact persistence — only inside a workflow.
            if artifact_type and ctx.workflow_run_id is not None:
                schema_name = artifact_schema_name or f"{schema.__name__}@v1"
                artifact = Artifact(
                    id=uuid4(),
                    tenant_id=ctx.tenant_id,
                    workflow_run_id=ctx.workflow_run_id,
                    created_by_agent_run_id=run_id,
                    type=artifact_type,
                    schema_name=schema_name,
                    data=validated.model_dump(mode="json"),
                    created_at=ended_at,
                )
                await ctx.store.insert_artifact(artifact)

            return validated

        wrapper._agent_name = name  # type: ignore[attr-defined]
        wrapper._agent_schema = schema  # type: ignore[attr-defined]
        wrapper._agent_prompt_name = prompt_name  # type: ignore[attr-defined]
        wrapper._agent_pure = pure  # type: ignore[attr-defined]
        wrapper._agent_artifact_type = artifact_type  # type: ignore[attr-defined]
        wrapper._agent_retry = retry_cfg  # type: ignore[attr-defined]
        return wrapper

    return decorator


def _inputs_to_dict(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    """Best-effort serialization of agent inputs for hashing in pure mode."""
    out: dict[str, Any] = {}
    for i, a in enumerate(args):
        out[f"arg{i}"] = _coerce(a)
    for k, v in kwargs.items():
        out[k] = _coerce(v)
    return out


def _coerce(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict | list | tuple | str | int | float | bool) or value is None:
        return value
    return str(value)
