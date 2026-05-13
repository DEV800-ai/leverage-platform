"""Workflow primitive — wraps an explicit sequence of agent calls with one WorkflowRun row.

v0 workflows are explicit Python (no DSL). They are NOT crash-durable (ADR-005);
a process crash leaves the WorkflowRun row in status="running" for a janitor
to mark `aborted`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from leverage_platform.schemas import WorkflowRun

if TYPE_CHECKING:
    from leverage_platform.runtime.context import AgentContext


async def run_workflow[T](
    *,
    name: str,
    ctx: AgentContext,
    body: Callable[[AgentContext], Awaitable[T]],
) -> tuple[UUID, T]:
    """Run an async workflow `body` with WorkflowRun lifecycle around it.

    Returns (workflow_run_id, value-from-body).

    - Inserts a WorkflowRun row in status='running' before calling body.
    - On success: marks status='succeeded'.
    - On exception: marks status='failed' with the error message.
    - The body receives a `ctx` whose `workflow_run_id` is set to the new UUID
      (the platform mutates the existing ctx to keep child agents linked).
    """
    run_id = uuid4()
    started_at = datetime.now(UTC)

    row = WorkflowRun(
        id=run_id,
        tenant_id=ctx.tenant_id,
        workflow_name=name,
        status="running",
        started_at=started_at,
    )
    await ctx.store.insert_workflow_run(row)

    prior_workflow_id = ctx.workflow_run_id
    ctx.workflow_run_id = run_id

    try:
        value = await body(ctx)
    except BaseException as exc:  # noqa: BLE001 — record then re-raise
        await ctx.store.update_workflow_run(
            run_id,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
            ended_at=datetime.now(UTC),
        )
        ctx.workflow_run_id = prior_workflow_id
        raise

    await ctx.store.update_workflow_run(
        run_id,
        status="succeeded",
        ended_at=datetime.now(UTC),
    )
    ctx.workflow_run_id = prior_workflow_id
    return run_id, value


def run_sync(coro: Awaitable[Any]) -> Any:
    """Sync entry point for CLI / scripts; thin wrapper over asyncio.run.

    Useful for short-lived scripts; for FastAPI / async services, use the
    coroutine directly.
    """
    import asyncio

    return asyncio.run(coro)
