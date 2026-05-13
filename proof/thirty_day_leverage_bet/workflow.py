"""30-Day Leverage Bet workflow orchestration.

Per AGENTS.md:
    raw_intake
      → profile_agent      → UserProfile
      → risk_agent         → RiskMap
      → opportunity_agent  → OpportunityMap
      → bet_designer_agent → ThirtyDayBet
      → critic_eval_agent  → EvalReport

Per-run audit summary:
    - 1 WorkflowRun row
    - 5 AgentRun rows (Critic always writes one as pure=True; +1 if llm_judge fires)
    - 5 Artifact rows (one per outer agent)
"""

from __future__ import annotations

from uuid import UUID

from leverage_platform.runtime import AgentContext, run_workflow
from leverage_platform.schemas import EvalReport
from proof.thirty_day_leverage_bet.agents import (
    bet_designer_agent,
    critic_eval_agent,
    opportunity_agent,
    profile_agent,
    risk_agent,
)


async def run_thirty_day_leverage_bet(
    ctx: AgentContext, raw_intake: dict
) -> tuple[UUID, EvalReport]:
    """Run the full 30-Day Leverage Bet workflow on one raw intake.

    Returns (workflow_run_id, EvalReport). The intermediate artifacts
    (UserProfile, RiskMap, OpportunityMap, ThirtyDayBet) are persisted as
    Artifact rows in the store; query them via store.get_artifact() or by
    workflow_run_id.
    """

    async def body(ctx: AgentContext) -> EvalReport:
        profile = await profile_agent(ctx, raw_intake)
        risk_map = await risk_agent(ctx, profile)
        opportunities = await opportunity_agent(ctx, profile, risk_map)
        bet = await bet_designer_agent(ctx, opportunities, profile)
        return await critic_eval_agent(ctx, bet)

    return await run_workflow(name="thirty_day_leverage_bet", ctx=ctx, body=body)
