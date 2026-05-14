"""@agent decorator: lifecycle + audit + missing-invoke-llm guard."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel

from leverage_platform.llm import LLMParameters, MockLLMProvider
from leverage_platform.runtime import AgentContext, agent
from leverage_platform.storage import SQLiteStore


class Greeting(BaseModel):
    text: str
    enthusiasm: int


def _greeting_factory(schema: type[BaseModel], prompt: str) -> BaseModel:
    return schema(text="hello, world", enthusiasm=5)


async def test_agent_writes_agentrun_row_on_success(store: SQLiteStore) -> None:
    provider = MockLLMProvider(structured_factory=_greeting_factory)
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="greeter", schema=Greeting, prompt_name="greeter.v1")
    async def greeter(ctx: AgentContext, who: str) -> Greeting:
        result = await ctx.invoke_llm(
            template="Greet {who}.",
            variables={"who": who},
            schema=Greeting,
            prompt_name="greeter.v1",
            parameters=LLMParameters(temperature=0.0),
        )
        return result.value

    value = await greeter(ctx, "alice")
    assert value.text == "hello, world"

    # Find the row by scanning — for v0 there's only one agent_run.
    rows = store._conn.execute("SELECT * FROM agent_run").fetchall()  # type: ignore[attr-defined]
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "succeeded"
    assert row["agent_name"] == "greeter"
    assert row["prompt_name"] == "greeter.v1"
    assert len(row["prompt_hash"]) == 64
    assert len(row["input_hash"]) == 64
    assert len(row["output_hash"]) == 64
    assert Decimal(row["cost_usd"]) == Decimal("0.000100")
    assert row["input_tokens"] == 100
    assert row["output_tokens"] == 50
    assert row["ended_at"] is not None


async def test_agent_fails_if_invoke_llm_not_called(store: SQLiteStore) -> None:
    provider = MockLLMProvider()  # no factory; we won't reach generate_structured
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="forgetful", schema=Greeting)
    async def forgetful(ctx: AgentContext) -> Greeting:
        return Greeting(text="hi", enthusiasm=1)

    with pytest.raises(RuntimeError, match="without calling ctx.invoke_llm"):
        await forgetful(ctx)

    rows = store._conn.execute("SELECT status, error FROM agent_run").fetchall()  # type: ignore[attr-defined]
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert "invoke_llm" in rows[0]["error"]


async def test_agent_coerces_dict_return_to_schema(store: SQLiteStore) -> None:
    provider = MockLLMProvider(structured_factory=_greeting_factory)
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="dict_returner", schema=Greeting)
    async def dict_returner(ctx: AgentContext) -> Greeting:
        result = await ctx.invoke_llm(
            template="anything {x}",
            variables={"x": 1},
            schema=Greeting,
            prompt_name="dr.v1",
        )
        # Return a dict instead of a Greeting; decorator should coerce via model_validate.
        return result.value.model_dump()  # type: ignore[return-value]

    value = await dict_returner(ctx)
    assert isinstance(value, Greeting)
    assert value.text == "hello, world"


async def test_agent_persists_prompt_version(store: SQLiteStore) -> None:
    """invoke_llm's prompt_version must be written to the AgentRun row."""
    provider = MockLLMProvider(structured_factory=_greeting_factory)
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="versioned", schema=Greeting, prompt_name="versioned.v1")
    async def versioned(ctx: AgentContext) -> Greeting:
        result = await ctx.invoke_llm(
            template="Greet {who}.",
            variables={"who": "world"},
            schema=Greeting,
            prompt_name="versioned",
            prompt_version="v1",
        )
        return result.value

    await versioned(ctx)

    rows = store._conn.execute(  # type: ignore[attr-defined]
        "SELECT prompt_version FROM agent_run"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["prompt_version"] == "v1"


async def test_agent_persists_none_prompt_version_when_not_provided(
    store: SQLiteStore,
) -> None:
    """When invoke_llm is called without prompt_version, the column stays NULL."""
    provider = MockLLMProvider(structured_factory=_greeting_factory)
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="unversioned", schema=Greeting)
    async def unversioned(ctx: AgentContext) -> Greeting:
        result = await ctx.invoke_llm(
            template="Greet {who}.",
            variables={"who": "world"},
            schema=Greeting,
            prompt_name="unversioned",
        )
        return result.value

    await unversioned(ctx)

    rows = store._conn.execute(  # type: ignore[attr-defined]
        "SELECT prompt_version FROM agent_run"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["prompt_version"] is None


async def test_agent_fails_fast_on_double_invoke_llm(store: SQLiteStore) -> None:
    """Two ctx.invoke_llm calls in the same agent body must raise."""
    provider = MockLLMProvider(structured_factory=_greeting_factory)
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="double_caller", schema=Greeting)
    async def double_caller(ctx: AgentContext) -> Greeting:
        result = await ctx.invoke_llm(
            template="first {x}",
            variables={"x": 1},
            schema=Greeting,
            prompt_name="first",
        )
        # Second call should raise — audit/cost rows would otherwise be silently
        # overwritten.
        await ctx.invoke_llm(
            template="second {x}",
            variables={"x": 2},
            schema=Greeting,
            prompt_name="second",
        )
        return result.value

    with pytest.raises(RuntimeError, match="more than once"):
        await double_caller(ctx)

    # The failed AgentRun row should still exist with status=failed.
    rows = store._conn.execute(  # type: ignore[attr-defined]
        "SELECT status, error FROM agent_run"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert "more than once" in rows[0]["error"]
