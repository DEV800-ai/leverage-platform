# Handoff — leverage-platform design review

**Purpose of this doc:** a self-contained briefing so a fresh Claude session (in Slack or elsewhere) can pick up this design conversation without seeing the prior thread.

---

## Mission

`~/git/leverage-platform/` is a **reusable AI-platform Python library**. No product is attached. It's being designed to support future B2C / small-B2B / SaaS products that need: LLM provider abstraction, agent runtime with audit, multi-tenant cost attribution, structured-output validation, workflow composition, and eval.

**Not** to be confused with: `~/git/signalalpha` (a separate, already-built single-user stock-signal tool). The platform must stand alone — no code lift from signalalpha.

## Locked decisions (from the user, 2026-05-12)

1. Repo name: `leverage-platform` (working name).
2. Monorepo (single package, internal modules — not workspace packages).
3. Income/monetization thesis: **deferred**.
4. No commercial product first; build infra grounded in **one concrete reference scenario**.
5. No relationship to signalalpha.
6. Future products will be SaaS / SMB B2B / B2C (multi-user, web-shaped).
7. The reference scenario is now **"30-Day Leverage Bet"** (per `CLAUDE_DESIGN_UPDATE_INSTRUCTIONS.md`).

## Repo state (as of this handoff)

```
leverage-platform/
├── PLAN.md          ← v0.2, needs update to v0.3
├── README.md
├── HANDOFF.md       ← this file
└── docs/source/
    ├── DESIGN.md    ← original product proposal (reference only)
    ├── CLAUDE.md    ← original
    └── AGENTS.md    ← original
```

**Important external file** (not yet in repo): `/home/ipinto/Downloads/CLAUDE_DESIGN_UPDATE_INSTRUCTIONS.md` — the v0.3 update instructions. Copy this into the repo and treat as authoritative input. It rewrites the proof scenario from a generic 3-agent placeholder into a concrete 5-agent "30-Day Leverage Bet" workflow.

## Pending task — apply v0.3 update

The v0.3 instructions ask for: revised `PLAN.md`, new `DESIGN.md`, `CLAUDE.md`, `AGENTS.md` at repo root, plus optional ADRs under `docs/adr/`. **No code yet.**

### 🔴 Six issues to resolve INLINE while applying

The v0.3 doc is directionally correct but has 6 gaps that should be fixed in the same pass:

1. **Keep domain schemas OUT of the platform package.**
   The doc lists `UserProfile`, `RiskMap`, `OpportunityMap`, `ThirtyDayBet` as proof-scenario schemas — they must live in `proof/thirty_day_leverage_bet/`, NOT in `src/leverage_platform/schemas/`. The platform's `schemas/` contains only `Tenant`, `AgentRun`, `WorkflowRun`, `Artifact`, `CostEntry`, and `EvalReport` (see fix #5). State this explicitly in PLAN.md.

2. **Do not implement `storage/postgres.py` in v0.**
   v0 ships `storage/protocol.py` + `storage/sqlite.py` only. Postgres is a **schema-design constraint** (TEXT not VARCHAR(n), UUID-as-TEXT, ISO datetimes, JSON-as-TEXT), portable to JSONB/UUID/TIMESTAMPTZ later. Don't maintain two adapters before a consumer exists.

3. **Proof-scenario Critic must USE the platform `eval` primitive, not duplicate it.**
   The doc says the Critic agent produces an `EvalReport`. The platform exposes a rule-based + LLM-judge eval primitive. Make the Critic a *consumer* of that primitive, not a parallel implementation. Otherwise the eval primitive isn't actually exercised by the proof.

4. **Specify `prompt_hash` semantics: template, not rendered.**
   `prompt_hash` = hash of the prompt **template** (before variable substitution). `input_hash` = hash of the variables. Together they reproduce the rendered prompt. Without this, every call hashes differently and "did the template change?" tracking is impossible.

5. **Resolve `EvalReport` namespace collision (related to fix #3).**
   The doc puts `EvalReport` in *"Suggested domain schemas for proof scenario"* — but it's also what the platform's eval primitive returns. It cannot be both. Pick **(a) `EvalReport` lives in `src/leverage_platform/schemas/`** (the proof Critic returns it); domain-only schemas in `proof/` are `UserProfile`, `RiskMap`, `OpportunityMap`, `ThirtyDayBet`. (Recommended.) Otherwise the eval primitive is decorative.

6. **Define retry policy semantics explicitly.**
   "Implement basic retry policy" in Phase 2 is too vague. Pin defaults in PLAN.md or an ADR:
   - **Retry**: network timeouts, HTTP 429 (with backoff), HTTP 5xx, provider JSON-parse failures.
   - **Never retry**: Pydantic validation failures (semantic bug — retrying re-burns tokens), HTTP 4xx (other than 429), eval failures.
   - Max retries: 2. Backoff: exponential with jitter, capped at 30s.

### 🟡 ADR-worthy items (write as short ADRs, don't bury in PLAN.md)

- ADR-001 — Tenant isolation is **product-side**, not platform-side. Platform attributes via `tenant_id`; doesn't enforce row-level filtering.
- ADR-002 — SQLite-first for v0; Postgres-compatible schema design rules.
- ADR-003 — `prompt_hash` = template, `input_hash` = vars (see fix #4).
- ADR-004 — Artifacts immutable per workflow run; schema versioning via `schema_name` field (e.g., `"Opportunity@v2"`).
- ADR-005 — v0 workflows are **not durable** across process crashes; products needing durability shouldn't use the workflow primitive yet.
- ADR-006 — Async-first runtime; SQLite blocking is acceptable for v0 (writes <1ms). Revisit when proven painful.
- ADR-007 — `LLMProvider.parameters` is a typed `LLMParameters(BaseModel)` with `temperature`, `max_tokens`, `top_p`, plus `provider_specific: dict | None` for the long tail. Untyped `dict` was rejected because reproducibility requires hashing parameters into AgentRun's `model_parameters` field.
- ADR-008 — Cost is stored as `Decimal` (Python) → `NUMERIC(12,6)` in Postgres / `TEXT` (ISO decimal) in SQLite. **Never float** — accumulates rounding error.
- ADR-009 — `WorkflowRun.status` enum: `running / succeeded / failed / partial / aborted`. `partial` = some agents succeeded, some failed; product decides what to do with it.
- ADR-010 — `workflow_run_id` propagates to nested agent calls via `AgentContext` (passed as the first arg to every `@agent` function). The platform sets up the context; agents never roll their own globals or ContextVars.

### ⚪ Minor

- Bump PLAN.md header to v0.3.
- `proof/thirty_day_leverage_bet/` must be a Python sub-package (has `__init__.py`).
- Phase 3 acceptance: "rule-based eval layer passes 100%; LLM-judge accepts ≥3 of 5 sample profiles." (Replace loose "workflow runs end-to-end".)
- Phase 4 needs **5 sample intake JSONs** at `proof/thirty_day_leverage_bet/fixtures/intakes/*.json`, spanning the input space (varying income-pressure / skill-level / weekly-time). Without these, acceptance is fuzzy.
- Tests for the proof scenario live at `proof/thirty_day_leverage_bet/tests/`. The top-level `tests/` is for platform primitives only.
- `input_hash` is an audit field. v0 does NOT implement output caching keyed on it. Future caching layers can consume the field; the platform itself always re-executes. State this so a future contributor doesn't assume memoization.

## Confirmed v0 primitives (8)

1. LLM provider abstraction (Anthropic v0; `generate_text` + `generate_structured` only — embeddings removed).
2. AgentRun audit (with `prompt_name`, `prompt_hash`, `input_hash`, `output_hash`, `model_parameters`).
3. Tenant identity contract (opaque string `tenant_id`).
4. Cost ledger (derived from AgentRun).
5. Structured output validation (Pydantic).
6. Workflow primitive (typed run-log, explicit Python — no DSL, no Temporal).
7. Eval primitive (deterministic rules first, LLM-judge second).
8. Artifact primitive (typed workflow outputs, immutable per run).

## Hard "no"s for v0

No frontend, no auth provider, no payment, no vector store, no embeddings, no RAG, no memory graph, no agent-to-agent hidden calls, no autonomous loops, no Temporal, no SaaS deployment, no relationship to signalalpha.

## Concrete next session task

> Apply `CLAUDE_DESIGN_UPDATE_INSTRUCTIONS.md` to the repo:
>
> - Update `PLAN.md` to v0.3 (replace v0.2).
> - Create `DESIGN.md`, `CLAUDE.md`, `AGENTS.md` at repo root.
> - Bake in the **6** 🔴 fixes above.
> - Draft the **10** ADRs under `docs/adr/` (ADR-001 through ADR-010).
> - Copy `CLAUDE_DESIGN_UPDATE_INSTRUCTIONS.md` from `~/Downloads/` into `docs/source/` for reference.
> - Do NOT implement any code (`src/leverage_platform/` stays empty; that's Phase 1).

Estimated work: ~45 min of writing, no code.

## User's working style (read this first)

- **Terse responses.** Bullet points > paragraphs. No trailing summaries.
- **Push back when wrong.** Don't apply instructions blindly if they have gaps — flag and propose fixes (as I did with the 4 🔴 issues).
- **Infrastructure-first, no premature implementation.** Never write code without an explicit "go".
- **One concrete next step.** End with "want me to do X?" — don't stack 5 options.
- **No code outside the task scope.** Bug fixes don't get refactoring; spec docs don't get implementations.

---

## How to use this in Slack

1. Attach this `HANDOFF.md` file AND `~/Downloads/CLAUDE_DESIGN_UPDATE_INSTRUCTIONS.md` to your first message in the Slack thread.
2. Tell `@Claude` something like: *"Read HANDOFF.md and CLAUDE_DESIGN_UPDATE_INSTRUCTIONS.md. Apply the v0.3 update to the leverage-platform repo, baking in the 6 🔴 fixes and drafting all 10 ADRs. Don't implement code."*
3. Claude in Slack will create a new web session and post results back to the thread.
