"""Workflow primitive: lifecycle, status, error handling."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from leverage_platform.llm import MockLLMProvider
from leverage_platform.runtime import AgentContext, agent, run_workflow
from leverage_platform.storage import SQLiteStore


class Item(BaseModel):
    label: str


def _item_factory(schema: type[BaseModel], prompt: str) -> BaseModel:
    return schema(label="thing")


async def test_workflow_writes_workflowrun_row(store: SQLiteStore) -> None:
    provider = MockLLMProvider(structured_factory=_item_factory)
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="picker", schema=Item)
    async def picker(ctx: AgentContext) -> Item:
        return (await ctx.invoke_llm(
            template="pick a {what}",
            variables={"what": "thing"},
            schema=Item,
            prompt_name="picker.v1",
        )).value

    async def body(ctx: AgentContext) -> Item:
        return await picker(ctx)

    workflow_id, value = await run_workflow(name="test_workflow", ctx=ctx, body=body)
    assert value.label == "thing"

    wf = await store.get_workflow_run(workflow_id)
    assert wf is not None
    assert wf.status == "succeeded"
    assert wf.ended_at is not None


async def test_workflow_links_agent_runs_to_workflow(store: SQLiteStore) -> None:
    provider = MockLLMProvider(structured_factory=_item_factory)
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="picker", schema=Item)
    async def picker(ctx: AgentContext) -> Item:
        return (await ctx.invoke_llm(
            template="pick",
            variables={},
            schema=Item,
            prompt_name="picker.v1",
        )).value

    async def body(ctx: AgentContext) -> Item:
        return await picker(ctx)

    workflow_id, _ = await run_workflow(name="t", ctx=ctx, body=body)

    rows = store._conn.execute("SELECT workflow_run_id FROM agent_run").fetchall()  # type: ignore[attr-defined]
    assert len(rows) == 1
    assert rows[0]["workflow_run_id"] == str(workflow_id)


async def test_workflow_marks_failed_on_exception(store: SQLiteStore) -> None:
    provider = MockLLMProvider()
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    async def body(ctx: AgentContext) -> None:
        raise ValueError("intentional")

    with pytest.raises(ValueError, match="intentional"):
        await run_workflow(name="failing", ctx=ctx, body=body)

    rows = store._conn.execute("SELECT id, status, error FROM workflow_run").fetchall()  # type: ignore[attr-defined]
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert "intentional" in rows[0]["error"]


async def test_workflow_restores_prior_workflow_id(store: SQLiteStore) -> None:
    provider = MockLLMProvider()
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    assert ctx.workflow_run_id is None

    async def body(ctx: AgentContext) -> str:
        assert ctx.workflow_run_id is not None
        return "ok"

    await run_workflow(name="t", ctx=ctx, body=body)
    # After workflow completes, ctx should be back to the prior state.
    assert ctx.workflow_run_id is None
