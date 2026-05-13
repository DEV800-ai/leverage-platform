"""Domain schemas for the 30-Day Leverage Bet reference scenario.

These types live in `proof/` — they are NOT platform schemas. They exist only
to give the platform a realistic shape to push against.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

type RiskTolerance = Literal["low", "medium", "high"]
type Severity = Literal["low", "medium", "high"]
type TimeHorizon = Literal["now", "6_months", "1_year", "3_years"]
type LeverageType = Literal[
    "skill", "audience", "capital", "automation", "network", "knowledge"
]


class UserProfile(BaseModel):
    """A normalized profile of one person trying to redesign their work."""

    current_role: str
    skills: list[str]
    interests: list[str]
    weekly_time_hours: int
    risk_tolerance: RiskTolerance
    income_goal: str | None = None


class RiskItem(BaseModel):
    """One concrete career or economic risk."""

    title: str
    description: str
    severity: Severity
    time_horizon: TimeHorizon
    mitigation_hint: str


class RiskMap(BaseModel):
    """A small set of risks scoped to one person."""

    risks: list[RiskItem]
    overall_risk_level: Severity


class Opportunity(BaseModel):
    """One opportunity tailored to the user's profile."""

    title: str
    thesis: str
    target_user: str
    required_skills: list[str]
    missing_skills: list[str]
    first_action: str
    evidence_to_validate: list[str]
    leverage_type: LeverageType
    score: int = Field(ge=0, le=100)


class OpportunityMap(BaseModel):
    """A ranked set of opportunities."""

    opportunities: list[Opportunity]


class ThirtyDayBet(BaseModel):
    """One concrete 30-day experiment built from a chosen opportunity."""

    title: str
    hypothesis: str
    weekly_plan: list[str]
    success_metric: str
    failure_metric: str
    first_48h_actions: list[str]
    expected_asset_created: str
