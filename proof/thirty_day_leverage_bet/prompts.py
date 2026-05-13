"""Prompt templates for the proof scenario's agents.

Templates are simple Python format strings; the @agent decorator hashes the
template (not the rendered prompt) via ADR-003. The structured output is
constrained by the schema passed to invoke_llm — Anthropic's tool_use
guarantees a JSON match.
"""

from __future__ import annotations

PROFILE_PROMPT_TEMPLATE = """\
You are processing an intake form for someone trying to redesign their work in an AI-native economy.

Convert this raw intake into a typed UserProfile.

Raw intake JSON:
{intake_json}

Guidelines:
- current_role: their current job title in one short line
- skills: 3-10 concrete, named skills (not vague like "communication")
- interests: 3-5 themes they're drawn to
- weekly_time_hours: realistic hours/week, integer
- risk_tolerance: low | medium | high based on stated financial pressure and life context
- income_goal: their stated income goal if any, else null

Be honest: if a field isn't present in the intake, infer conservatively. Do NOT invent skills.
"""


RISK_PROMPT_TEMPLATE = """\
You are assessing career, economic, and AI-displacement risks for this person.

UserProfile:
{profile_json}

Produce a RiskMap with 3 to 5 RiskItems. Each item must have:
- title: short risk name (2-4 words)
- description: 1-2 sentences specific to this person's role/skills
- severity: low | medium | high
- time_horizon: now | 6_months | 1_year | 3_years
- mitigation_hint: one concrete action they could take

Set overall_risk_level to the aggregate severity. Be realistic, not alarmist.
"""


OPPORTUNITY_PROMPT_TEMPLATE = """\
Produce exactly 5 Opportunity objects tailored to this person.

UserProfile:
{profile_json}

RiskMap:
{risk_map_json}

Each Opportunity must have:
- title: one specific opportunity name
- thesis: 1-2 sentence "why this person, why now"
- target_user: who would pay or care (be specific — not "small businesses")
- required_skills: 3-5 skills this opportunity needs
- missing_skills: skills they don't have yet
- first_action: one concrete step they can take this week
- evidence_to_validate: 2-3 observable signals that say "this is working" in 30 days
- leverage_type: one of skill | audience | capital | automation | network | knowledge
- score: 0-100 fit score for this person

AVOID generic suggestions like "start a newsletter", "become a freelancer",
"build an audience". Each opportunity must be specific to THIS person's role,
skills, and constraints.
"""


BET_DESIGNER_PROMPT_TEMPLATE = """\
Select the highest-scoring opportunity from this OpportunityMap and design a 30-day experiment.

OpportunityMap:
{opportunities_json}

UserProfile:
{profile_json}

Produce a ThirtyDayBet with:
- title: short experiment name
- hypothesis: an if-then statement we are testing in 30 days
- weekly_plan: exactly 4 strings, one per week, in order
- success_metric: one measurable signal that says "continue past day 30"
- failure_metric: one measurable signal that says "stop or pivot at day 30"
- first_48h_actions: 2 to 4 concrete actions in the next 48 hours
- expected_asset_created: one tangible artifact the person will have at day 30
  (audience of N, paid pilot, prototype, dataset, etc.)

failure_metric must be a real off-ramp, not a face-saver. Keep weekly_plan
items realistic against the user's weekly_time_hours.
"""
