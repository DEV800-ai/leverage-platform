"""Phase 2 acceptance test.

Per PLAN.md Phase 2 acceptance:
> A typed test agent runs end-to-end, produces a StructuredResult[T],
> and writes one AgentRun row to SQLite with all required fields populated.

This test uses MockLLMProvider so CI doesn't burn Anthropic tokens. The real
Anthropic integration test is a separate file gated by ANTHROPIC_API_KEY.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from leverage_platform.llm import LLMParameters, MockLLMProvider
from leverage_platform.runtime import AgentContext, agent
from leverage_platform.storage import SQLiteStore


class UserSummary(BaseModel):
    """A tiny domain type used for the e2e test only — NOT a platform schema."""

    name: str
    headline: str
    skills: list[str]


def _summary_factory(schema: type[BaseModel], prompt: str) -> BaseModel:
    return schema(
        name="Alice",
        headline="Senior backend engineer pivoting to AI tooling",
        skills=["python", "fastapi", "postgres"],
    )


async def test_phase2_acceptance_end_to_end(store: SQLiteStore) -> None:
    provider = MockLLMProvider(
        structured_factory=_summary_factory,
        model="mock-test",
        input_tokens=200,
        output_tokens=100,
        cost_usd=Decimal("0.000500"),
        latency_ms=42,
    )
    ctx = AgentContext(tenant_id="acme", provider=provider, store=store)

    @agent(name="summarizer", schema=UserSummary, prompt_name="summarizer.v1")
    async def summarizer(ctx: AgentContext, raw_intake: dict) -> UserSummary:
        result = await ctx.invoke_llm(
            template=(
                "You are a profile summarizer.\n"
                "Given this intake JSON: {intake_json}\n"
                "Produce a UserSummary."
            ),
            variables={"intake_json": raw_intake},
            schema=UserSummary,
            prompt_name="summarizer.v1",
            prompt_version="v1",
            parameters=LLMParameters(temperature=0.0, max_tokens=512),
        )
        return result.value

    value = await summarizer(
        ctx,
        raw_intake={"name": "Alice", "current_role": "backend engineer", "wants": "pivot"},
    )

    # 1. Typed output produced.
    assert isinstance(value, UserSummary)
    assert value.name == "Alice"
    assert "python" in value.skills

    # 2. One AgentRun row written with all required fields populated.
    rows = store._conn.execute("SELECT * FROM agent_run").fetchall()  # type: ignore[attr-defined]
    assert len(rows) == 1
    row = rows[0]

    assert row["tenant_id"] == "acme"
    assert row["agent_name"] == "summarizer"
    assert row["prompt_name"] == "summarizer.v1"
    assert row["status"] == "succeeded"
    assert row["error"] is None

    # All three hashes populated and valid.
    assert len(row["prompt_hash"]) == 64
    assert len(row["input_hash"]) == 64
    assert len(row["output_hash"]) == 64

    # Provider metadata captured.
    assert row["model"] == "mock-test"
    assert row["input_tokens"] == 200
    assert row["output_tokens"] == 100
    assert row["latency_ms"] == 42
    assert Decimal(row["cost_usd"]) == Decimal("0.000500")

    # Model parameters preserved (typed LLMParameters dumped to JSON, ADR-007).
    import json as _json

    params = _json.loads(row["model_parameters"])
    assert params["temperature"] == 0.0
    assert params["max_tokens"] == 512

    # Timestamps in order.
    assert row["started_at"] is not None
    assert row["ended_at"] is not None
    assert row["ended_at"] >= row["started_at"]
