"""Test fixtures for the 30-Day Leverage Bet proof scenario.

Uses MockLLMProvider with a multi-schema factory so the workflow can run
end-to-end in CI without burning Anthropic tokens.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import BaseModel

from leverage_platform.llm import MockLLMProvider
from leverage_platform.runtime import AgentContext
from leverage_platform.schemas import EvalCriterion, EvalReport
from leverage_platform.storage import SQLiteStore
from proof.thirty_day_leverage_bet.schemas import (
    Opportunity,
    OpportunityMap,
    RiskItem,
    RiskMap,
    ThirtyDayBet,
    UserProfile,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "intakes"


def _user_profile_from_intake(intake: dict) -> UserProfile:
    """Deterministic UserProfile constructed from a fixture intake."""
    raw_skills = intake.get("raw_skills_text", "")
    raw_interests = intake.get("raw_interests_text", "")
    skills = [s.strip() for s in raw_skills.split(",") if s.strip()][:8]
    interests = [s.strip() for s in raw_interests.split(",") if s.strip()][:5]
    pressure = intake.get("financial_pressure", "medium")
    # Tolerance correlates inversely with pressure: high pressure → low tolerance.
    tolerance_map = {"low": "high", "medium": "medium", "high": "low"}
    return UserProfile(
        current_role=intake.get("current_role", "unknown"),
        skills=skills or ["generalist"],
        interests=interests or ["unspecified"],
        weekly_time_hours=int(intake.get("weekly_time_hours", 5)),
        risk_tolerance=tolerance_map.get(pressure, "medium"),  # type: ignore[arg-type]
        income_goal=intake.get("wants"),
    )


def _risk_map_for(profile: UserProfile) -> RiskMap:
    return RiskMap(
        risks=[
            RiskItem(
                title="Role-level AI exposure",
                description=f"Tasks in '{profile.current_role}' face increasing AI automation.",
                severity="medium",
                time_horizon="1_year",
                mitigation_hint="Identify which tasks remain human-judgment-heavy.",
            ),
            RiskItem(
                title="Income concentration",
                description="Single-employer income is fragile under industry shifts.",
                severity="medium" if profile.risk_tolerance == "high" else "high",
                time_horizon="6_months",
                mitigation_hint="Build a parallel income stream with bounded test.",
            ),
            RiskItem(
                title="Skill commoditization",
                description="Some current skills will be table-stakes within 24 months.",
                severity="low",
                time_horizon="3_years",
                mitigation_hint=(
                    "Invest in skills that compound (judgment, domain depth, distribution)."
                ),
            ),
        ],
        overall_risk_level="medium",
    )


def _opportunity_map_for(profile: UserProfile) -> OpportunityMap:
    skills_subset = profile.skills[:3] if profile.skills else ["generalist"]
    return OpportunityMap(
        opportunities=[
            Opportunity(
                title=f"Audit consultancy for {profile.current_role}-adjacent SMBs",
                thesis=f"Bring {skills_subset[0]} expertise to a niche that needs AI-aware audits.",
                target_user="10-50 person companies in adjacent verticals",
                required_skills=skills_subset,
                missing_skills=["outbound sales"],
                first_action="Send 20 cold DMs proposing a free 30-min audit this week.",
                evidence_to_validate=[
                    "≥2 replies in week 1",
                    "≥1 booked audit call in week 2",
                ],
                leverage_type="knowledge",
                score=85,
            ),
            Opportunity(
                title="Paid niche newsletter on a specific workflow",
                thesis="Write deeply for a small audience that already pays for tools.",
                target_user="practitioners in the same role looking for sharper workflows",
                required_skills=["writing", "domain depth"],
                missing_skills=["audience building"],
                first_action="Publish 1 issue and share it with 30 hand-picked contacts.",
                evidence_to_validate=["≥5 replies", "≥1 paid sub after 4 issues"],
                leverage_type="audience",
                score=70,
            ),
            Opportunity(
                title="Automated workflow template for a known pain point",
                thesis="Sell a productized service / template that solves one recurring task.",
                target_user="solo operators in the same vertical",
                required_skills=skills_subset,
                missing_skills=["landing-page copy"],
                first_action="Spec the template and write a 1-page sales note.",
                evidence_to_validate=["≥3 outbound interest replies"],
                leverage_type="automation",
                score=72,
            ),
            Opportunity(
                title="Cohort-based teaching of a niche skill",
                thesis="Run a small paid cohort teaching one concrete workflow.",
                target_user="early-career peers in the same field",
                required_skills=["teaching"],
                missing_skills=["course platform setup"],
                first_action="Draft the curriculum and offer it to 10 acquaintances.",
                evidence_to_validate=["≥3 paying participants"],
                leverage_type="skill",
                score=65,
            ),
            Opportunity(
                title="Productized service in user's domain",
                thesis="Package a known workflow as a fixed-price service.",
                target_user="adjacent industry teams",
                required_skills=skills_subset,
                missing_skills=["pricing"],
                first_action="Define one fixed-scope offer with one price.",
                evidence_to_validate=["≥1 paid pilot in 30d"],
                leverage_type="skill",
                score=68,
            ),
        ]
    )


def _bet_for(profile: UserProfile, opportunities: OpportunityMap) -> ThirtyDayBet:
    top = max(opportunities.opportunities, key=lambda o: o.score)
    return ThirtyDayBet(
        title=top.title,
        hypothesis=(
            f"If we test {top.title} via {top.first_action}, "
            "we will see early-signal evidence within 30 days."
        ),
        weekly_plan=[
            f"Week 1: {top.first_action}; collect first signals.",
            "Week 2: Iterate based on responses; book ≥1 call.",
            "Week 3: Deliver a paid pilot or refined offer.",
            "Week 4: Decide continue / pivot / stop based on metrics.",
        ],
        success_metric="1 paid pilot signed by day 30",
        failure_metric="0 replies after 60 outbound messages",
        first_48h_actions=[
            "Draft the outreach message; refine for 30 min.",
            "Send to first 20 contacts within 48 hours.",
        ],
        expected_asset_created="A validated offer + ≥1 paid pilot relationship.",
    )


def _eval_report_accepted() -> EvalReport:
    return EvalReport(
        accepted=True,
        criteria=[
            EvalCriterion(name=q, passed=True, reason="judged acceptable")
            for q in [
                "Is this bet specific to the user's profile and skills, not generic advice?",
                "Can the first 48-hour actions realistically be completed in 48 hours?",
                "Is the success_metric observable within 30 days?",
                "Is the failure_metric a genuine off-ramp, not a face-saver?",
                "Does the weekly_plan fit the user's stated weekly_time_hours?",
                "Does the bet create a compounding asset, rather than just busywork?",
            ]
        ],
        summary="all rubric questions judged acceptable",
    )


def _make_factory(intake: dict):  # noqa: ANN202 — Callable type inferred
    """Construct a single multi-schema factory bound to the given intake."""
    profile = _user_profile_from_intake(intake)
    risk_map = _risk_map_for(profile)
    opportunities = _opportunity_map_for(profile)
    bet = _bet_for(profile, opportunities)
    accepted_report = _eval_report_accepted()

    def factory(schema: type[BaseModel], prompt: str) -> BaseModel:
        if schema is UserProfile:
            return profile
        if schema is RiskMap:
            return risk_map
        if schema is OpportunityMap:
            return opportunities
        if schema is ThirtyDayBet:
            return bet
        if schema is EvalReport:
            return accepted_report
        raise TypeError(f"No factory branch for schema {schema.__name__}")

    return factory


@pytest.fixture
def store() -> Iterator[SQLiteStore]:
    s = SQLiteStore(":memory:")
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(params=sorted(FIXTURES_DIR.glob("*.json")), ids=lambda p: p.stem)
def intake(request: pytest.FixtureRequest) -> dict:
    return json.loads(request.param.read_text())


@pytest.fixture
def ctx_for_intake(store: SQLiteStore, intake: dict) -> AgentContext:
    provider = MockLLMProvider(structured_factory=_make_factory(intake))
    return AgentContext(tenant_id="acme", provider=provider, store=store)
