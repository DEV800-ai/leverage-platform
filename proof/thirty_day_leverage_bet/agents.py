"""The 5 agents that compose the 30-Day Leverage Bet workflow.

Per AGENTS.md and PLAN.md acceptance:
- Profile, Risk, Opportunity, BetDesigner: each makes one LLM call → 4 AgentRun rows.
- Critic: pure=True (no LLM call of its own); runs rule_eval, optionally fires llm_judge.
- llm_judge (called from Critic): @agent-decorated; produces a 6th AgentRun row when fired.

Per-run row count: exactly 5 AgentRun rows when Critic short-circuits, or 6 when judge fires.
Each of the 5 outer agents persists one Artifact, so the per-run Artifact count is always 5.
"""

from __future__ import annotations

import json

from leverage_platform.eval import llm_judge, rule_eval
from leverage_platform.llm import LLMParameters
from leverage_platform.runtime import AgentContext, agent
from leverage_platform.schemas import EvalReport
from proof.thirty_day_leverage_bet.eval_config import (
    THIRTY_DAY_BET_RUBRIC,
    THIRTY_DAY_BET_RULES,
)
from proof.thirty_day_leverage_bet.prompts import (
    BET_DESIGNER_PROMPT_TEMPLATE,
    OPPORTUNITY_PROMPT_TEMPLATE,
    PROFILE_PROMPT_TEMPLATE,
    RISK_PROMPT_TEMPLATE,
)
from proof.thirty_day_leverage_bet.schemas import (
    OpportunityMap,
    RiskMap,
    ThirtyDayBet,
    UserProfile,
)

# ---------- 1. Profile Agent ----------


@agent(
    name="profile_agent",
    schema=UserProfile,
    prompt_name="profile_agent.v1",
    artifact_type="user_profile",
)
async def profile_agent(ctx: AgentContext, raw_intake: dict) -> UserProfile:
    """Convert raw intake JSON into a typed UserProfile."""
    result = await ctx.invoke_llm(
        template=PROFILE_PROMPT_TEMPLATE,
        variables={"intake_json": json.dumps(raw_intake, sort_keys=True)},
        schema=UserProfile,
        prompt_name="profile_agent.v1",
        parameters=LLMParameters(temperature=0.0),
    )
    return result.value


# ---------- 2. Risk Agent ----------


@agent(
    name="risk_agent",
    schema=RiskMap,
    prompt_name="risk_agent.v1",
    artifact_type="risk_map",
)
async def risk_agent(ctx: AgentContext, profile: UserProfile) -> RiskMap:
    """Identify career/economic/AI-displacement risks for the user."""
    result = await ctx.invoke_llm(
        template=RISK_PROMPT_TEMPLATE,
        variables={"profile_json": json.dumps(profile.model_dump(mode="json"), sort_keys=True)},
        schema=RiskMap,
        prompt_name="risk_agent.v1",
        parameters=LLMParameters(temperature=0.2),
    )
    return result.value


# ---------- 3. Opportunity Agent ----------


@agent(
    name="opportunity_agent",
    schema=OpportunityMap,
    prompt_name="opportunity_agent.v1",
    artifact_type="opportunity_map",
)
async def opportunity_agent(
    ctx: AgentContext, profile: UserProfile, risk_map: RiskMap
) -> OpportunityMap:
    """Produce exactly 5 ranked Opportunity objects tailored to the user."""
    result = await ctx.invoke_llm(
        template=OPPORTUNITY_PROMPT_TEMPLATE,
        variables={
            "profile_json": json.dumps(profile.model_dump(mode="json"), sort_keys=True),
            "risk_map_json": json.dumps(risk_map.model_dump(mode="json"), sort_keys=True),
        },
        schema=OpportunityMap,
        prompt_name="opportunity_agent.v1",
        parameters=LLMParameters(temperature=0.4),
    )
    return result.value


# ---------- 4. Bet Designer Agent ----------


@agent(
    name="bet_designer_agent",
    schema=ThirtyDayBet,
    prompt_name="bet_designer_agent.v1",
    artifact_type="thirty_day_bet",
)
async def bet_designer_agent(
    ctx: AgentContext, opportunities: OpportunityMap, profile: UserProfile
) -> ThirtyDayBet:
    """Select the top opportunity and turn it into a concrete 30-day experiment."""
    result = await ctx.invoke_llm(
        template=BET_DESIGNER_PROMPT_TEMPLATE,
        variables={
            "opportunities_json": json.dumps(
                opportunities.model_dump(mode="json"), sort_keys=True
            ),
            "profile_json": json.dumps(profile.model_dump(mode="json"), sort_keys=True),
        },
        schema=ThirtyDayBet,
        prompt_name="bet_designer_agent.v1",
        parameters=LLMParameters(temperature=0.2),
    )
    return result.value


# ---------- 5. Critic / Eval Agent ----------


@agent(
    name="critic_eval_agent",
    schema=EvalReport,
    prompt_name="critic_eval_agent.v1",
    pure=True,  # may short-circuit on rule_eval without an LLM call
    artifact_type="eval_report",
)
async def critic_eval_agent(ctx: AgentContext, bet: ThirtyDayBet) -> EvalReport:
    """Reject generic or unrealistic bets.

    Two-stage eval:
    1. Rule-based check on structure (cheap, deterministic).
    2. LLM-as-judge for subjective fit, only if rules pass.

    The Critic itself makes no LLM call. The optional nested llm_judge call
    produces its own AgentRun row when fired.
    """
    rule_report = rule_eval(bet, THIRTY_DAY_BET_RULES)
    if not rule_report.accepted:
        return rule_report
    return await llm_judge(ctx, artifact=bet, rubric=THIRTY_DAY_BET_RUBRIC)
