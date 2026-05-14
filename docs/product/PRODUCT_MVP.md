# Product MVP — AI Leverage Audit V1

**Status:** Draft v0.1 — 2026-05-14
**Scope:** Concrete specification for V1 of the AI Leverage Audit product. Implementation lives in a future forked repo (working name: `ai-leverage-audit`). This doc is the contract that fork must implement.
**Companion docs:** [`PRODUCT_VISION.md`](PRODUCT_VISION.md) (positioning), `PRODUCT_ROADMAP.md` (validation experiments — to be written).

---

## 1. What V1 does

A small-business owner fills a short text-based intake. The system runs the Audit and returns a personalised report containing:

- A map of the recurring workflows in the business
- Per-workflow analysis: how much leverage AI can create, what to automate vs assist vs keep human
- One concrete 30-day experiment with success and failure metrics
- Risks and explicit "keep human" areas
- Owner-agency checkpoints (where the owner stays in control)
- A first-version Playbook for the business

**V1 is one-shot.** It runs once, produces a static report, and ends. Continuous tracking, weekly reviews, integrations with the customer's tools, and ongoing learning are explicitly V2+.

---

## 2. Intake schema

A single Pydantic model defines everything the owner gives us. Free-text fields are preferred over dropdowns at V1 — the LLM can extract structure.

```python
class AuditIntake(BaseModel):
    # Business identity
    business_type: str                   # "dental clinic", "freelance designer", "SaaS founder"
    current_role: str                    # "owner-operator", "founder", "solopreneur"
    team_size: int                       # 1 if solo
    months_in_business: int              # 0 if pre-launch

    # Workflows (free-text — LLM extracts structure)
    weekly_tasks_text: str               # 5–10 recurring tasks the owner does each week
    current_tools_text: str              # CRMs, email, calendar, accounting, etc.
    top_time_sinks_text: str             # what eats the most time
    error_sensitive_areas_text: str      # where mistakes are costly
    customer_facing_areas_text: str      # what touches customer trust / reputation

    # Goal + constraints
    primary_goal_text: str               # "more leads", "faster invoicing", "stop missing calls"
    weekly_time_to_invest_hours: int     # how much time available for an experiment
    monthly_budget_usd: int              # ceiling for AI tools / SaaS / setup
    things_owner_refuses_to_automate_text: str | None = None
```

**Validation:** all free-text fields require ≥30 characters. `weekly_time_to_invest_hours` ∈ [1, 40]. `monthly_budget_usd` ≥ 0. The LLM parser tolerates messy English; the platform validates after parsing.

---

## 3. Output artifacts

The Vision doc named **seven conceptual outputs**. V1 produces them as **six LLM-derived artifacts plus one eval report** — totalling seven Artifact rows per Audit run. The merging (Leverage ↔ Ratio, Risks ↔ Checkpoints) avoids needing `ctx.write_artifact(...)` (a Phase 4 platform backlog item).

| # | Artifact | Produced by | Maps to Vision output(s) |
| --- | --- | --- | --- |
| 1 | `ParsedIntake` | `intake_parser_agent` | (internal — normalises free-text intake) |
| 2 | `WorkflowMap` | `workflow_diagnoser_agent` | Vision output 1 |
| 3 | `LeverageAnalysis` | `leverage_analyst_agent` | Vision outputs 2 (Score) + 3 (Ratio), combined |
| 4 | `ThirtyDayBet` | `bet_designer_agent` | Vision output 4 |
| 5 | `RiskAndAgencyMap` | `risk_mapper_agent` | Vision outputs 5 (Risks) + 6 (Checkpoints), combined |
| 6 | `FirstPlaybook` | `playbook_builder_agent` | Vision output 7 |
| 7 | `EvalReport` | `critic_eval_agent` (pure) | platform-side, gates acceptance |

### 3.1 `ParsedIntake`

Owner's free-text intake, parsed into structured fields the rest of the pipeline can consume.

```python
class WeeklyTask(BaseModel):
    title: str
    estimated_time_minutes_per_week: int
    is_customer_facing: bool
    is_error_sensitive: bool
    current_tool: str | None       # tool used today, if any

class ParsedIntake(BaseModel):
    business_summary: str          # 1–2 sentences synthesising the business
    weekly_tasks: list[WeeklyTask] # extracted from weekly_tasks_text, 3–15 items
    tools_in_use: list[str]
    top_pain_points: list[str]     # ≤5
    primary_goal: str
    weekly_time_budget_hours: int
    monthly_budget_usd: int
    refused_automation_areas: list[str]
```

**Invariant:** `weekly_tasks` must contain at least 3 tasks. If fewer can be extracted, the agent retries (per platform retry policy) before failing.

### 3.2 `WorkflowMap`

The recurring workflows in the business — clusters of related tasks, not individual tasks.

```python
class Workflow(BaseModel):
    id: str                              # short slug, unique within Audit, e.g. "lead-followup"
    title: str
    description: str
    frequency: Literal["daily", "weekly", "monthly", "event_driven"]
    minutes_per_occurrence: int
    occurrences_per_week: int
    inputs: str                          # what triggers it
    outputs: str                         # what it produces
    pain_points: list[str]
    tools_used: list[str]

class WorkflowMap(BaseModel):
    workflows: list[Workflow]            # 3–8 items
```

**Invariant:** `len(workflows) ∈ [3, 8]`. Workflow IDs are unique (slug-style, lowercase, hyphenated).

### 3.3 `LeverageAnalysis`

Per-workflow: how valuable AI is here, and what mix to apply.

```python
class WorkflowLeverage(BaseModel):
    workflow_id: str                              # references WorkflowMap
    # Scoring
    time_saved_hours_per_week_estimate: float
    risk_if_ai_gets_it_wrong: Literal["low", "medium", "high"]
    setup_complexity: Literal["low", "medium", "high"]
    human_judgment_needed: Literal["low", "medium", "high"]
    rank: int                                     # 1 = highest leverage
    rationale: str                                # 1–3 sentences
    # Ratio
    automate_pct: int                             # 0–100
    assist_pct: int                               # 0–100
    keep_human_pct: int                           # 0–100
    automate_examples: list[str]                  # ≥1 if automate_pct > 0
    assist_examples: list[str]                    # ≥1 if assist_pct > 0
    keep_human_examples: list[str]                # ≥1 if keep_human_pct > 0

class LeverageAnalysis(BaseModel):
    per_workflow: list[WorkflowLeverage]
    overall_top_three_ids: list[str]              # 3 highest-rank workflow ids
```

**Invariants:**
- One `WorkflowLeverage` per `Workflow` in the `WorkflowMap`.
- `automate_pct + assist_pct + keep_human_pct == 100` for every workflow.
- `rank` values are a permutation of `1..len(per_workflow)`.
- `overall_top_three_ids` are the three workflow IDs with `rank ∈ {1, 2, 3}`.

### 3.4 `ThirtyDayBet`

Same shape as the proof scenario's `ThirtyDayBet`, parameterised by the top-ranked workflow.

```python
class ThirtyDayBet(BaseModel):
    target_workflow_id: str
    title: str
    hypothesis: str
    success_metric: str                 # observable within 30 days
    failure_metric: str                 # genuine off-ramp, not face-saver
    weekly_plan: list[str]              # exactly 4 entries
    first_48h_actions: list[str]        # ≥2
    expected_asset_created: str
    estimated_weekly_time_hours: int    # ≤ ParsedIntake.weekly_time_budget_hours
    estimated_setup_cost_usd: int       # ≤ ParsedIntake.monthly_budget_usd
```

**Invariants:**
- `len(weekly_plan) == 4`
- `len(first_48h_actions) >= 2`
- `success_metric.strip() != failure_metric.strip()`
- `estimated_weekly_time_hours <= ParsedIntake.weekly_time_budget_hours`
- `estimated_setup_cost_usd <= ParsedIntake.monthly_budget_usd`
- `target_workflow_id ∈ LeverageAnalysis.overall_top_three_ids`

### 3.5 `RiskAndAgencyMap`

Where automation is dangerous, and where the owner stays in control.

```python
class KeepHumanArea(BaseModel):
    area: str                                       # e.g. "pricing negotiations"
    reason: str
    severity: Literal["low", "medium", "high"]

class AutomationRisk(BaseModel):
    automation: str                                 # what could be automated
    what_could_break: str
    mitigation: str

class AgencyCheckpoint(BaseModel):
    trigger: str                                    # condition that pages the owner
    required_action: str                            # what the owner must do
    cadence: Literal["per_event", "daily", "weekly", "monthly"] | None = None

class RiskAndAgencyMap(BaseModel):
    keep_human_areas: list[KeepHumanArea]           # ≥2
    automation_risks: list[AutomationRisk]          # ≥2
    agency_checkpoints: list[AgencyCheckpoint]      # ≥3
    weekly_review_questions: list[str]              # 3–6, owner asks themselves each week
    compliance_or_legal_flags: list[str]            # may be empty
```

**Invariant:** every `keep_human_area` overlaps with at least one `weekly_review_question` thematically (this is rule-checked at eval time, not LLM-checked).

### 3.6 `FirstPlaybook`

Living document that future Audits / re-runs will update. V1 emits the first version.

```python
class PlaybookEntry(BaseModel):
    workflow_id: str
    current_status: Literal["not_yet_tested", "experimenting", "validated", "rejected"]
    summary: str                                  # 1–2 sentences

class FirstPlaybook(BaseModel):
    title: str                                    # e.g. "Acme Dental — AI Playbook v1"
    business_summary: str
    workflow_entries: list[PlaybookEntry]         # one per workflow in WorkflowMap
    rules_for_human_involvement: list[str]        # ≥3
    open_questions: list[str]                     # things V1 couldn't answer
    next_review_offset_days: int                  # default 30
```

**Invariants:**
- `len(workflow_entries) == len(WorkflowMap.workflows)`
- The `target_workflow_id` of `ThirtyDayBet` has `current_status = "experimenting"` in `FirstPlaybook`.
- Workflows not in `LeverageAnalysis.overall_top_three_ids` get `current_status = "not_yet_tested"`.

### 3.7 `EvalReport`

Platform-side type (`leverage_platform.schemas.EvalReport`). Produced by the Critic agent. Two-stage evaluation, identical pattern to the proof scenario:

1. **Rule-based eval** — invariants from §3.1–3.6 + cross-artifact consistency rules.
2. **LLM judge** — fires only if all rules pass. Rubric questions are listed in §6.

---

## 4. Agent workflow

```
AuditIntake (raw)
    → intake_parser_agent        → ParsedIntake
    → workflow_diagnoser_agent   → WorkflowMap
    → leverage_analyst_agent     → LeverageAnalysis
    → bet_designer_agent         → ThirtyDayBet
    → risk_mapper_agent          → RiskAndAgencyMap
    → playbook_builder_agent     → FirstPlaybook
    → critic_eval_agent          → EvalReport
```

Each agent makes **exactly one** `ctx.invoke_llm` call (enforced by the platform). The Critic is the only `pure=True` agent — it short-circuits on rule failures and delegates subjective judgment to a nested `llm_judge` call.

| Agent | `pure` | Persists artifact? | Notes |
| --- | --- | --- | --- |
| `intake_parser_agent` | no | yes (`type="parsed_intake"`) | strict — must extract ≥3 weekly tasks |
| `workflow_diagnoser_agent` | no | yes (`type="workflow_map"`) | 3–8 workflows |
| `leverage_analyst_agent` | no | yes (`type="leverage_analysis"`) | one entry per workflow |
| `bet_designer_agent` | no | yes (`type="thirty_day_bet"`) | constrained by intake budgets |
| `risk_mapper_agent` | no | yes (`type="risk_agency_map"`) | ≥2 keep-human areas |
| `playbook_builder_agent` | no | yes (`type="first_playbook"`) | aggregates priors |
| `critic_eval_agent` | **yes** | yes (`type="eval_report"`) | rule_eval → llm_judge |

**Per Audit run, the platform writes:**

- 1 `WorkflowRun` row
- 7 `AgentRun` rows (8 if the Critic's `llm_judge` fires — and it will, when rules pass)
- 7 `Artifact` rows

This is the same shape pattern as the Phase 3 proof scenario (`proof/thirty_day_leverage_bet/`), proving the platform supports the product without extension.

---

## 5. Cross-artifact consistency rules (deterministic eval)

The Critic's rule-based eval enforces these in addition to the per-schema invariants in §3:

1. Every `Workflow.id` in `WorkflowMap` appears in `LeverageAnalysis.per_workflow` exactly once.
2. `ThirtyDayBet.target_workflow_id` is one of `LeverageAnalysis.overall_top_three_ids`.
3. `ThirtyDayBet.estimated_weekly_time_hours <= ParsedIntake.weekly_time_budget_hours`.
4. `ThirtyDayBet.estimated_setup_cost_usd <= ParsedIntake.monthly_budget_usd`.
5. `automate_pct + assist_pct + keep_human_pct == 100` for every `WorkflowLeverage`.
6. `len(FirstPlaybook.workflow_entries) == len(WorkflowMap.workflows)`.
7. The bet's target workflow is `current_status = "experimenting"` in `FirstPlaybook`.
8. Every `ParsedIntake.refused_automation_areas` entry is reflected in `RiskAndAgencyMap.keep_human_areas` (matched by substring or LLM-judged synonym).
9. Every `WorkflowLeverage` with `human_judgment_needed = "high"` has `keep_human_pct >= 30`.
10. `ThirtyDayBet.failure_metric` is **not** a paraphrase of the success metric (rule + LLM-judge backup).

Rule failure rejects the Audit. Owner sees a clear failure message; the LLM judge does not run on rejected outputs.

---

## 6. LLM-judge rubric

Fires only when all deterministic rules pass. Six questions, structured per the proof scenario's pattern:

1. Is each workflow in `WorkflowMap` genuinely a recurring pattern, not a one-off task?
2. Are `LeverageAnalysis.rationale` entries specific to the owner's actual business, not generic advice?
3. Does `ThirtyDayBet.first_48h_actions` realistically fit in 48 hours given the owner's stated weekly time budget?
4. Is `ThirtyDayBet.failure_metric` a genuine off-ramp (observable, decisive) rather than a face-saver?
5. Do the `RiskAndAgencyMap.keep_human_areas` reflect actual customer-trust / regulated / judgment-heavy work, rather than just things the owner finds tedious?
6. Does `FirstPlaybook` produce a compounding asset (knowledge, validated workflow, customer relationship) rather than just a saved-time list?

Judge returns `accepted: bool` plus per-question `passed: bool, reason: str`. Audit run status:

- All 10 rules pass + all 6 judge questions pass → **accepted**
- Any rule fails → **rejected** (judge skipped)
- Rules pass but judge says no → **needs_review** (owner sees report + judge concerns)

---

## 7. V1 success criteria

V1 is shipped when **all** of the following are true:

1. A founder-friend can fill the intake (§2) in <10 minutes without help.
2. Per Audit run: 1 WorkflowRun, 7 AgentRuns (or 8 with judge), 7 Artifacts, all `status=succeeded`.
3. ≥3 of 5 friend-and-family intakes produce `EvalReport.accepted=true` on first run (matching Phase 3 acceptance bar).
4. ≥4 of 5 of those intakes generate a `ThirtyDayBet` the owner finds "specific and doable" in an unprompted post-Audit conversation (qualitative bar — written notes count).
5. 0 platform-side audit gaps (all `AgentRun` rows have `prompt_version`, no double-`invoke_llm` runtime errors, cost attributed to tenant).

If any criterion fails on the first 5 intakes, V1 is not shipped — we iterate on prompts and schemas before opening to a wider audience.

Note on latency and cost: deliberately not exposed as user-facing acceptance gates. The Audit may be used from mobile and may take whatever time real LLM calls take; cost lives in the platform's ledger for the operator's own visibility, not as a public spec.

---

## 8. V1 non-goals (explicit)

V1 deliberately excludes:

| Excluded | Where it belongs |
| --- | --- |
| Web UI / dashboard | V1 is CLI + JSON output; UI is V2 |
| Auth, accounts, multi-tenant SaaS | V1 is single-user, locally run |
| Integrations with customer tools (CRM / email / calendar reads) | V2, requires platform-level `ToolCall` (Phase 4 backlog) |
| Continuous tracking / weekly reviews / re-runs | V2 (the "loop closes" part of the Vision doc) |
| Solution Router (4 implementation paths per recommendation) | V2 |
| Tech-readiness Score (Level 1–5) and routing on it | V2 |
| Paid Playbook marketplace | V3+ |
| Affiliate / partner / certification revenue | V3+ |
| Hosting the customer's automations | Never — explicitly out of business model |
| Building custom agents per customer | Never — that's the agency model trap |

If a feature feels tempting, the test is: *does V1 ship without it?* If yes, it's V2.

---

## 9. Platform usage summary

V1 consumes the following platform primitives (all already in Phase 3):

| Platform primitive | V1 usage |
| --- | --- |
| `@agent` decorator | 7 agents (6 LLM, 1 pure) |
| `run_workflow` | one `AuditWorkflow` per intake |
| `AgentContext` | carries `tenant_id`, store, provider |
| `LLMProvider` (Anthropic) | one provider instance per Audit |
| `SQLiteStore` | one DB file per deployment; per-tenant scoping is product-side |
| `Artifact` | 7 typed Pydantic schemas per Audit, all `schema_name="<Name>@v1"` |
| `eval.rule_eval` + `eval.llm_judge` | Critic's two-stage eval |
| Cost ledger (`store.query_cost`) | Audit-level cost reporting |
| Retry policy (default) | each agent retries on network / 429 / 5xx |

V1 does **not** require any Phase 4 platform feature. If a real V1 build surfaces a need (cost CLI, structured logs, `write_artifact`, Prompt object), that's a signal to pull the corresponding Phase 4 backlog item into the platform — not to extend the platform speculatively first.

---

## 10. Locked decisions

These were open at draft time and are now settled. They are written into the spec; implementation may not deviate without a new product-side ADR.

1. **Multi-tenancy boundary.** V1 uses a constant `tenant_id="default"` for every Audit run. All re-runs on the same install share the same tenant, which lets the cost ledger aggregate per-install spend trivially. "Tenant" remains an opaque attribution key per ADR-001 — the platform does not interpret it. When V2 introduces a real "business" concept, the product can switch the source of `tenant_id` without any platform change.
2. **Re-run semantics.** Re-running on an edited intake produces a **new** `WorkflowRun` and a **new** set of `Artifact` rows. Prior runs are kept (Artifacts are immutable per ADR-004). The product is responsible for surfacing the latest run; the platform stores them all.

## 11. Open questions (decide before implementation)

1. **Owner-rejected outputs.** If the owner reads the Audit and says "this bet is wrong," there is no V1 mechanism to capture that. Proposed: add a single `ReflectionEvent` (platform-side, deferred from DESIGN.md Tier 2) as the first V1.5 / V2 primitive. Out of scope for V1 itself.
2. **Model selection.** Hardcode `claude-opus-4-7` for all 7 agents, or allow per-agent overrides? Lean: hardcode for V1; per-agent in V2.
3. **Localisation.** Intake and output are English-only in V1. Hebrew support is V2 — implementation note: localise prompts only; schemas (field names, IDs, slugs) remain English.

---

## 12. Implementation outline (for the product fork)

When the `ai-leverage-audit` repo is forked, it will contain (roughly):

```
ai-leverage-audit/
├── src/
│   └── ai_leverage_audit/
│       ├── schemas.py            # AuditIntake + 6 output schemas + EvalReport import
│       ├── agents.py             # 7 agents per §4
│       ├── prompts.py            # prompt templates per agent
│       ├── eval_config.py        # 10 rules + 6-question rubric per §5–§6
│       ├── workflow.py           # run_audit(ctx, intake) -> (workflow_id, EvalReport)
│       └── cli.py                # `audit run --intake path/to/intake.json`
├── fixtures/
│   └── intakes/                  # 5+ friend-and-family intakes
├── tests/
│   ├── test_workflow_e2e.py
│   ├── test_rules.py
│   └── test_intake_validation.py
└── pyproject.toml                # depends on leverage-platform (local path or wheel)
```

No platform code lives in this repo. All platform features are imported from `leverage_platform.*`.
