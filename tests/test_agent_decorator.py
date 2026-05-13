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
