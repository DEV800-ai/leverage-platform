"""Phase 3 acceptance test for the 30-Day Leverage Bet proof scenario.

Per PLAN.md Phase 3 acceptance:
- Workflow runs end-to-end on each of the 5 fixture intakes.
- Per run: exactly 5 AgentRun rows + 1 WorkflowRun row + 5 Artifact rows
  (or 6 AgentRuns when llm_judge fires; here it always fires because rules pass).
- Cost attributed to tenant.
- Rule-based eval passes 100% (structure rules are well-defined and stable).
- LLM-judge returns accepted=true on ≥ 3 of 5 sample profiles.

This test uses MockLLMProvider — no Anthropic tokens are spent in CI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from leverage_platform.runtime import AgentContext
from leverage_platform.schemas import EvalReport
from leverage_platform.storage import SQLiteStore
from proof.thirty_day_leverage_bet.workflow import run_thirty_day_leverage_bet


async def test_proof_scenario_runs_end_to_end(
    intake: dict, ctx_for_intake: AgentContext, store: SQLiteStore
) -> None:
    """Per-fixture acceptance: workflow runs, rows + artifacts written, eval accepts."""
    workflow_id, report = await run_thirty_day_leverage_bet(ctx_for_intake, intake)

    # 1. Returns a typed EvalReport.
    assert isinstance(report, EvalReport)
    # Rule eval should pass for all 5 fixtures (factories produce valid bets).
    assert report.accepted is True, f"intake produced rejected bet: {report.summary}"

    # 2. Exactly one WorkflowRun row, succeeded.
    wf_rows = store._conn.execute(  # type: ignore[attr-defined]
        "SELECT id, status, started_at, ended_at FROM workflow_run"
    ).fetchall()
    assert len(wf_rows) == 1
    assert str(workflow_id) == wf_rows[0]["id"]
    assert wf_rows[0]["status"] == "succeeded"
    assert wf_rows[0]["ended_at"] is not None

    # 3. AgentRun rows: 5 outer agents + 1 llm_judge (fired because rule_eval passed).
    agent_rows = store._conn.execute(  # type: ignore[attr-defined]
        "SELECT agent_name, status, cost_usd, model FROM agent_run "
        "WHERE workflow_run_id = ? ORDER BY started_at",
        (str(workflow_id),),
    ).fetchall()
    agent_names = [r["agent_name"] for r in agent_rows]

    assert agent_names == [
        "profile_agent",
        "risk_agent",
        "opportunity_agent",
        "bet_designer_agent",
        "critic_eval_agent",
        "llm_judge",
    ], f"unexpected agent sequence: {agent_names}"

    # All AgentRuns succeeded.
    assert all(r["status"] == "succeeded" for r in agent_rows)

    # The Critic itself is pure — model is sentinel; cost is zero.
    critic_row = next(r for r in agent_rows if r["agent_name"] == "critic_eval_agent")
    assert critic_row["model"] == "(none)"
    assert Decimal(critic_row["cost_usd"]) == Decimal("0")

    # The other 5 agents called the LLM.
    llm_rows = [r for r in agent_rows if r["agent_name"] != "critic_eval_agent"]
    assert all(r["model"] == "mock-model" for r in llm_rows)

    # 4. Artifact rows: exactly 5 (one per outer agent; llm_judge has no artifact_type).
    artifact_rows = store._conn.execute(  # type: ignore[attr-defined]
        "SELECT type, schema_name FROM artifact WHERE workflow_run_id = ? "
        "ORDER BY created_at",
        (str(workflow_id),),
    ).fetchall()
    artifact_types = [r["type"] for r in artifact_rows]
    assert artifact_types == [
        "user_profile",
        "risk_map",
        "opportunity_map",
        "thirty_day_bet",
        "eval_report",
    ], f"unexpected artifact sequence: {artifact_types}"

    # Schema names are versioned per ADR-004.
    schema_names = {r["schema_name"] for r in artifact_rows}
    assert all("@v1" in name for name in schema_names)

    # 5. Cost attributed to tenant.
    cost_entries = await store.query_cost(
        "acme", since=datetime(2020, 1, 1, tzinfo=UTC)
    )
    assert len(cost_entries) == 1
    assert cost_entries[0].tenant_id == "acme"
    assert cost_entries[0].cost_usd > Decimal("0")
    # 5 LLM calls (judge fires) + 1 pure Critic; call_count is the row count.
    assert cost_entries[0].call_count == 6
