# AGENTS.md — Agent definitions for the 30-Day Leverage Bet reference scenario

This document defines the **five agents** that compose the proof-scenario workflow. These agents exist to stress-test the platform primitives; they are not products.

For the platform's agent **contract** (the `@agent` decorator, `AgentContext`, retry policy, audit fields), see `PLAN.md` and `DESIGN.md`. This doc defines the agents themselves.

## Where these live

```
proof/thirty_day_leverage_bet/
├── schemas.py        # domain types (UserProfile, RiskMap, OpportunityMap, ThirtyDayBet)
├── agents.py         # the 5 agents below
├── workflow.py       # orchestration
├── prompts/          # one .md file per agent's prompt template
└── fixtures/intakes/ # 5 sample intakes
```

**Important:** domain schemas (`UserProfile`, `RiskMap`, `OpportunityMap`, `ThirtyDayBet`) live in `proof/`, NOT in `src/leverage_platform/schemas/`. They are not platform types.

`EvalReport` and `EvalCriterion` are platform-owned (see PLAN.md and ADR-003-fix-5).

## General agent contract

Every agent in this scenario:

- Is an `async def` function decorated with `@agent(name=..., schema=...)`.
- Takes `ctx: AgentContext` as its first argument (carries `tenant_id`, `workflow_run_id`, provider, store).
- Returns a Pydantic model — the platform validates it and persists it as an `Artifact`.
- Produces **one** `AgentRun` row per call.
- Uses a named prompt template; `prompt_hash` is the hash of the template (ADR-003).

## The five agents

---

### 1. Profile Agent

**Purpose.** Convert raw intake JSON into a typed, validated `UserProfile`.

**Signature:**
```python
@agent(name="profile_agent", schema=UserProfile)
async def profile_agent(ctx: AgentContext, raw_intake: dict) -> UserProfile: ...
```

**Input.** Raw intake JSON. Loose shape; the agent's job is to normalize.

**Output schema** (`proof/thirty_day_leverage_bet/schemas.py`):
```python
class UserProfile(BaseModel):
    current_role: str
    skills: list[str]
    interests: list[str]
    weekly_time_hours: int
    risk_tolerance: Literal["low", "medium", "high"]
    income_goal: str | None = None
```

**Evaluation criteria (rule-based, applied by the eval primitive):**
- All required fields are present and non-empty.
- `skills` has at least 1 entry.
- `weekly_time_hours` ∈ [1, 80].
- No invented facts beyond what's in the raw intake.

**Failure modes:**
- Raw intake is too sparse — agent should still return a `UserProfile` with confidence indicators in optional fields (future addition; v0 does not include `missing_info`).
- LLM hallucinates skills not in the intake — caught by rule eval comparing against intake text.

---

### 2. Risk Agent

**Purpose.** Identify career / economic / AI-displacement risks for the user.

**Signature:**
```python
@agent(name="risk_agent", schema=RiskMap)
async def risk_agent(ctx: AgentContext, profile: UserProfile) -> RiskMap: ...
```

**Output schema:**
```python
class RiskItem(BaseModel):
    title: str
    description: str
    severity: Literal["low", "medium", "high"]
    time_horizon: Literal["now", "6_months", "1_year", "3_years"]
    mitigation_hint: str

class RiskMap(BaseModel):
    risks: list[RiskItem]
    overall_risk_level: Literal["low", "medium", "high"]
```

**Evaluation criteria (rule-based):**
- 3 ≤ `len(risks)` ≤ 8.
- Each risk has all four fields populated.
- `overall_risk_level` derivable from individual severities (sanity rule).

**Evaluation criteria (LLM judge — optional, applied in Critic):**
- Risks are specific to this user's role/skills, not generic ("AI will change everything").
- Time horizons are plausible.
- Mitigation hints are concrete, not motivational.

---

### 3. Opportunity Agent

**Purpose.** Produce exactly 5 ranked `Opportunity` objects tailored to the user.

**Signature:**
```python
@agent(name="opportunity_agent", schema=OpportunityMap)
async def opportunity_agent(
    ctx: AgentContext,
    profile: UserProfile,
    risk_map: RiskMap,
) -> OpportunityMap: ...
```

**Output schema:**
```python
class Opportunity(BaseModel):
    title: str
    thesis: str
    target_user: str
    required_skills: list[str]
    missing_skills: list[str]
    first_action: str
    evidence_to_validate: list[str]
    leverage_type: Literal[
        "skill", "audience", "capital", "automation", "network", "knowledge",
    ]
    score: int  # 0-100

class OpportunityMap(BaseModel):
    opportunities: list[Opportunity]
```

**Evaluation criteria (rule-based):**
- `len(opportunities)` == 5.
- Each `score` ∈ [0, 100].
- Each opportunity has a non-empty `first_action`.
- Each opportunity has at least 1 entry in `evidence_to_validate`.
- `leverage_type` is one of the 6 enums.
- `missing_skills` ⊆ skills NOT in `profile.skills`.

**Evaluation criteria (LLM judge — applied in Critic):**
- Opportunity is specific to the user, not generic ("start a newsletter").
- 30-day testability is plausible.
- `evidence_to_validate` describes real-world signals, not vibes.
- Doesn't require a budget the user doesn't have.

---

### 4. Bet Designer Agent

**Purpose.** Select one opportunity and turn it into a concrete 30-day experiment.

**Signature:**
```python
@agent(name="bet_designer_agent", schema=ThirtyDayBet)
async def bet_designer_agent(
    ctx: AgentContext,
    opportunities: OpportunityMap,
    profile: UserProfile,
) -> ThirtyDayBet: ...
```

The agent itself decides which opportunity to take (highest score by default; can deviate with reasoning in `hypothesis`).

**Output schema:**
```python
class ThirtyDayBet(BaseModel):
    title: str
    hypothesis: str
    weekly_plan: list[str]    # one string per week
    success_metric: str       # one observable, measurable signal
    failure_metric: str       # one observable signal that says STOP
    first_48h_actions: list[str]
    expected_asset_created: str
```

**Evaluation criteria (rule-based):**
- `len(weekly_plan)` == 4.
- `success_metric` and `failure_metric` are both non-empty.
- `len(first_48h_actions) >= 2`.
- `expected_asset_created` is non-empty.

**Evaluation criteria (LLM judge — applied in Critic):**
- Bet fits `profile.weekly_time_hours`.
- Bet creates compounding leverage (asset, audience, skill) — not just busywork.
- `success_metric` is testable within 30 days.
- `failure_metric` is a real off-ramp, not a face-saver.

---

### 5. Critic / Eval Agent

**Purpose.** Reject generic / unrealistic bets. Returns the platform's `EvalReport`.

**Signature:**
```python
@agent(name="critic_eval_agent", schema=EvalReport)
async def critic_eval_agent(ctx: AgentContext, bet: ThirtyDayBet) -> EvalReport: ...
```

**Implementation:** the Critic **consumes** the platform eval primitive — it does NOT define its own rules or judge logic:

```python
from leverage_platform.eval import rule_eval, llm_judge

@agent(name="critic_eval_agent", schema=EvalReport)
async def critic_eval_agent(ctx: AgentContext, bet: ThirtyDayBet) -> EvalReport:
    rule_report = rule_eval(bet, THIRTY_DAY_BET_RULES)
    if not rule_report.accepted:
        return rule_report  # short-circuit; no LLM call needed
    return await llm_judge(bet, THIRTY_DAY_BET_RUBRIC, ctx=ctx)
```

`THIRTY_DAY_BET_RULES` and `THIRTY_DAY_BET_RUBRIC` live in `proof/thirty_day_leverage_bet/eval_config.py`.

**Output schema** (platform-owned, in `src/leverage_platform/schemas/eval.py`):
```python
class EvalCriterion(BaseModel):
    name: str
    passed: bool
    reason: str

class EvalReport(BaseModel):
    accepted: bool
    criteria: list[EvalCriterion]
    summary: str
```

**Why the Critic uses the eval primitive (not its own logic):**
- The eval primitive is one of the 8 v0 primitives. If the Critic implements its own eval, the primitive is decorative.
- Deterministic-first / LLM-second is a platform discipline; baking it into the proof's Critic forces the platform's contract to be real.

---

## Workflow orchestration

```python
class ThirtyDayLeverageBetWorkflow:
    async def run(self, ctx: AgentContext, raw_intake: dict) -> EvalReport:
        profile = await profile_agent(ctx, raw_intake)
        risk_map = await risk_agent(ctx, profile)
        opportunities = await opportunity_agent(ctx, profile, risk_map)
        bet = await bet_designer_agent(ctx, opportunities, profile)
        report = await critic_eval_agent(ctx, bet)
        return report
```

The runtime wraps `run()` with `WorkflowRun` lifecycle. Five `AgentRun` rows are written; five `Artifact` rows are written; one `WorkflowRun` row is written.

## Per-run audit summary

| Row type | How many per workflow run |
| --- | --- |
| `WorkflowRun` | 1 |
| `AgentRun` | 5 (one per agent) — *or 6 if the LLM judge fires inside Critic, since `llm_judge` is itself an `@agent`-decorated call* |
| `Artifact` | 5 — `UserProfile`, `RiskMap`, `OpportunityMap`, `ThirtyDayBet`, `EvalReport` |

If the Critic short-circuits on rule eval (no LLM judge call), the run produces 5 `AgentRun` rows. If the judge fires, it produces 6.

## Agent quality bar

Outputs must be:

- **Specific** to this user's profile (no boilerplate).
- **Structured** per the Pydantic schema (Pydantic enforces).
- **Actionable** — every bullet/field points to a thing the user could do.
- **Honest about uncertainty** — if data is missing, say so in the relevant field.
- **Focused on testable next steps** — `first_action`, `evidence_to_validate`, `success_metric`, `failure_metric`.

### Bad output example

> Title: "Start an AI consultancy"
> First action: "Network with potential clients."

Generic, untestable, no measurable signal.

### Good output example

> Title: "AI workflow audits for Israeli SMB law firms"
> Target user: 5–20 person law firms using paper-heavy intake.
> First action: "Send a 4-sentence outreach DM to 20 firm partners on LinkedIn proposing a free 30-min workflow audit. Track replies."
> Evidence to validate: "≥ 2 replies in week 1; ≥ 1 booked audit call in week 2."
> Success metric: "1 paid pilot audit ($500–$1000) signed by day 30."
> Failure metric: "0 replies after 60 outreach messages — kill or pivot."

## Anti-patterns for these agents

- **Generic "start a newsletter" / "build an audience" suggestions.** If the Opportunity Agent emits these without user-specific context, rule eval catches the lack of `evidence_to_validate`; LLM judge catches the genericness.
- **Optimistic forecasts.** "This will make $5k/month by day 30." Rule eval + judge should reject.
- **Tasks dressed up as opportunities.** "Take a Coursera course in AI." This is consumption, not leverage. The `leverage_type` enum forces a categorization.
- **Hidden failure modes.** `failure_metric` must be a real off-ramp, not "if it doesn't work, keep trying."

## Future agents (not in v0)

Listed in `docs/source/AGENTS.md` (the original product spec). Examples: Research Agent (web evidence), Coach Mode Agent (cohort view), Product Builder Agent, Memory Curator. **None of these are implemented in v0.** They are out of scope until a real product asks for them.
