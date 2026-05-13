# leverage-platform — Design

This document describes the architecture. For the build sequence and decisions, see `PLAN.md`. For decisions locked behind ADRs, see `docs/adr/`.

## Design principle

We are not building a system to optimize humans as economic resources.
We are building infrastructure that helps humans preserve and expand agency in an AI-native economy.

Every primitive should serve this principle: increasing user capability, decision quality, and accumulated learning over time. Primitives that only optimize throughput, cost, or automation — without making the user more capable or their decisions more legible — are not platform-justified.

This frames the rest of this document. See `CLAUDE.md` "Human Agency Guardrail" for the practical coding implications.

## Mental model

The platform is a **three-layer Python library** with one cross-cutting concern (audit).

```
┌────────────────────────────────────────────────────────────────┐
│                      product code (separate repo)               │
└──────────────────────────────┬──────────────────────────────────┘
                               │ depends on
┌──────────────────────────────▼──────────────────────────────────┐
│   leverage_platform.runtime          (workflow + @agent)        │
│   leverage_platform.eval             (rules + LLM judge)        │
├─────────────────────────────────────────────────────────────────┤
│   leverage_platform.llm              (provider abstraction)     │
│   leverage_platform.schemas          (Pydantic contracts)       │
├─────────────────────────────────────────────────────────────────┤
│   leverage_platform.storage          (SQLite v0; Postgres soon) │
│   leverage_platform.observability    (cost ledger, traces)      │
└─────────────────────────────────────────────────────────────────┘

                         AUDIT cross-cuts every layer:
                  every LLM call → one AgentRun row.
```

**Reading order:** product code → runtime → llm → storage. Each layer depends only on layers below it.

## Data flow — one workflow execution

```
1. caller creates AgentContext(tenant_id, workflow_run_id=None)
                                                  │
2. WorkflowRun row created (status="running")     │
                                                  ▼
3. @agent profile_agent(ctx, raw_intake) ────► AgentRun row pending
                                                  │
4.   provider.generate_structured(prompt, UserProfile)
                                                  │
5.   output validated → Artifact row created
                                                  │
6.   AgentRun row updated (succeeded, cost, tokens, latency)
                                                  ▼
7. @agent risk_agent(ctx, UserProfile) ─────► next AgentRun row
   ...                                            │
8. @agent critic_eval_agent(ctx, ThirtyDayBet)    │
   uses leverage_platform.eval.{rules, judge}     │
                                                  ▼
9. WorkflowRun row updated (status="succeeded", final_artifact_id)
```

Every box is one row in the database. Replay is read-only: take the `workflow_run_id`, follow `agent_run` rows in order, follow `artifact` rows by `created_by_agent_run_id`.

## Layered architecture

### Layer 1 — Schemas (`schemas/`)

The data contracts shared by every other layer. Pure Pydantic v2.

- `Tenant` — identity envelope, opaque string ID (see ADR-001 for what isolation does and doesn't mean).
- `AgentRun` — one row per LLM call.
- `WorkflowRun` — one row per workflow invocation; parent of agent rows.
- `Artifact` — typed output of one workflow step; immutable (see ADR-004).
- `CostEntry` — derived view, not a write target.
- `EvalReport`, `EvalCriterion` — eval primitive output shape.

No domain types live here. Domain types (UserProfile, etc.) live in `proof/thirty_day_leverage_bet/`.

### Layer 2 — LLM (`llm/`)

Provider abstraction. v0 has Anthropic; the contract is the deliverable.

```python
class LLMProvider(Protocol):
    async def generate_text(prompt, *, model, parameters) -> TextResult
    async def generate_structured[T](prompt, schema, *, model, parameters) -> StructuredResult[T]
```

`embed()` is **not** in v0 (vector-store / RAG concerns deferred).

`LLMParameters` is typed (see ADR-007):

```python
class LLMParameters(BaseModel):
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: list[str] | None = None
    provider_specific: dict[str, Any] | None = None
```

`TextResult` / `StructuredResult[T]` carry: the output, model used, prompt tokens, completion tokens, `cost_usd: Decimal` (see ADR-008), provider name, latency ms.

### Layer 3 — Storage (`storage/`)

```python
class Store(Protocol):
    async def insert_agent_run(row: AgentRun) -> None
    async def update_agent_run(id: UUID, **fields) -> None
    async def insert_workflow_run(row: WorkflowRun) -> None
    async def update_workflow_run(id: UUID, **fields) -> None
    async def insert_artifact(row: Artifact) -> None
    async def get_artifact(id: UUID) -> Artifact | None
    async def query_cost(tenant_id: str, since: datetime) -> list[CostEntry]
    # ... read APIs for replay
```

v0 ships **only** `sqlite.py` (uses stdlib `sqlite3` via `asyncio.to_thread` — see ADR-006). The Postgres-portable schema design rules (TEXT not VARCHAR(n), UUID-as-TEXT, ISO datetimes, JSON-as-TEXT) live in ADR-002. A `postgres.py` adapter is **not** built until a product needs it.

SQLite-specific:
- WAL mode enabled
- `PRAGMA foreign_keys = ON`
- Embedded migrations as a list of SQL strings, applied in order; a `_migrations` table tracks applied versions

### Layer 4 — Runtime (`runtime/`)

The orchestration layer.

**`AgentContext`** (see ADR-010) — carried as the first arg to every `@agent` function:

```python
class AgentContext(BaseModel):
    tenant_id: str
    workflow_run_id: UUID | None
    provider: LLMProvider
    store: Store
    # ... whatever the runtime needs to thread through
```

**`@agent` decorator** — wraps an async function. On call:

1. Open `AgentRun` row (status="pending"); set `started_at`.
2. Run the user's function body.
3. Validate the return value against the declared schema (Pydantic).
4. On success: write `Artifact` (immutable), update `AgentRun` (status="succeeded", cost, tokens, output_hash, ended_at).
5. On failure: apply retry policy (see PLAN.md retry table). After exhausted retries, write `AgentRun` (status="failed", error).

**`Workflow`** — a Python class. v0 is deliberately not a DSL:

```python
class ThirtyDayLeverageBetWorkflow:
    async def run(self, ctx: AgentContext, raw_intake: dict) -> Artifact:
        profile = await profile_agent(ctx, raw_intake)
        risk = await risk_agent(ctx, profile)
        opportunities = await opportunity_agent(ctx, profile, risk)
        bet = await bet_designer_agent(ctx, opportunities)
        report = await critic_eval_agent(ctx, bet)
        return report
```

The runtime wraps `run()` with `WorkflowRun` lifecycle (open row, set status). The `workflow_run_id` propagates to nested `@agent` calls via `AgentContext` (ADR-010). v0 workflows are **not** crash-durable (ADR-005).

**`run_sync(workflow, ctx, input)`** — sync helper for CLI / scripts. Internally `asyncio.run(...)`.

### Layer 5 — Eval (`eval/`)

Two-stage evaluation. Schema-validation is implicit in `@agent` (Pydantic). What lives here is the *content* check.

**`rules.py`** — deterministic rule-based eval:

```python
class Rule(Protocol):
    name: str
    def check(self, artifact: BaseModel) -> RuleResult: ...  # passed | failed | skipped

def rule_eval(artifact: BaseModel, rules: list[Rule]) -> EvalReport: ...
```

Rules are pure Python — fast, deterministic, no LLM call. Example rule: "OpportunityMap has exactly 5 opportunities."

**`judge.py`** — LLM-as-judge:

```python
async def llm_judge(
    artifact: BaseModel,
    rubric: list[Criterion],
    *,
    ctx: AgentContext,
    model: str | None = None,
) -> EvalReport: ...
```

`llm_judge` is itself implemented using `@agent` — every judge call gets its own `AgentRun` row, attributed to the same tenant, with cost rolled into the same workflow.

**Order of operations** in the proof's Critic agent:

```python
@agent(name="critic_eval_agent", schema=EvalReport, ...)
async def critic_eval_agent(ctx, bet: ThirtyDayBet) -> EvalReport:
    rule_report = rule_eval(bet, THIRTY_DAY_BET_RULES)
    if not rule_report.accepted:
        return rule_report  # short-circuit: don't waste a judge call
    return await llm_judge(bet, THIRTY_DAY_BET_RUBRIC, ctx=ctx)
```

Deterministic-first means cheap, stable tests. LLM-judge second handles the subjective "is this realistic for the user" questions.

### Layer 6 — Observability (`observability/`)

**`cost.py`** — CLI: `uv run leverage-platform cost --tenant <id> --since 7d`. Aggregates `agent_run.cost_usd` by tenant + workflow + agent.

**`traces.py`** — log-shape helpers. Structured JSON logs on production; human-readable on TTY. Trace ID = `workflow_run_id`. Span ID = `agent_run.id`.

No Grafana / Honeycomb / OpenTelemetry integration in v0. Append when pain is concrete.

## Cross-cutting concerns

### Audit

Every LLM call produces exactly one `AgentRun` row. The row carries enough fields to:

- Bill the call (`tenant_id`, `cost_usd`).
- Replay the call (`prompt_hash` + `input_hash` together identify what was sent).
- Detect drift (`prompt_hash` changes → template was edited).
- Debug (`error`, `model_parameters`, `input_tokens`, `output_tokens`).
- Trace (`workflow_run_id`).

No "fire and forget" log call exists. If a call isn't audited, the platform's job isn't done.

### Tenant isolation (ADR-001)

The platform attributes via `tenant_id` but does **not** enforce row-level isolation. Products are responsible for filtering by `tenant_id` in their queries. The platform's `Store` accepts `tenant_id` on writes; reads return whatever the query asks for. Cross-tenant data exposure is a product bug, not a platform bug.

### Reproducibility

The pair `(prompt_hash, input_hash, model, model_parameters)` is the reproducibility key. Same key → same rendered prompt → same call (within LLM determinism). Anything that changes one of these four fields changes the call — fully audit-able. See ADR-003 for what each hash hashes.

### Cost discipline

`cost_usd: Decimal` (ADR-008). All cost math is in Decimal until display time. JSON serialization uses string form to preserve precision.

## Domain ↔ platform boundary

The clearest test of "is this platform code?":

```
A change to the proof scenario's UserProfile schema requires
    a change in src/leverage_platform/  ⟶  WRONG, boundary violation
                                       ⟶  FIX: domain coupling, move out
```

Domain schemas live in `proof/thirty_day_leverage_bet/schemas.py`. Future products keep their domain in their own package. The platform never imports from `proof/` or any product.

## Non-goals (explicit)

- The platform does not implement any UI.
- The platform does not implement auth.
- The platform does not implement payment, subscription, or billing.
- The platform does not implement vector storage or embeddings.
- The platform does not implement long-term memory or knowledge graphs.
- The platform does not implement browser automation or web search.
- The platform does not call agents from other agents implicitly — only via explicit workflow orchestration.
- The platform does not provide a workflow DSL — workflows are explicit Python classes.
- The platform does not provide crash-durability — products needing it should not use the workflow primitive yet (ADR-005).

## Performance characteristics

v0 targets:
- One `@agent` call adds < 5ms overhead on top of the LLM call (SQLite write, hash compute, Pydantic validation).
- Workflow with 5 agents: total platform overhead < 25ms (the 5 LLM calls dominate at ~1–10s each).
- SQLite WAL writes are not the bottleneck at this scale.

v0 does **not** target:
- High-concurrency (> 100 concurrent workflow runs per process — products needing this should not use the in-process workflow primitive).
- Sub-millisecond p99 (not the goal of a workflow tier).

## Testing strategy

- **Platform tests** (`tests/`) — primitive-level. Mock provider, in-memory SQLite, unit tests on `@agent`, retry, rule_eval, etc.
- **Proof tests** (`proof/thirty_day_leverage_bet/tests/`) — end-to-end with the real Anthropic provider on the 5 fixture intakes.
- **No** tests in the proof directory exercise the platform implementation — only its public API.

## What this design deliberately does NOT decide

- Whether to use Alembic or embedded SQL for migrations (Phase 2 call).
- Whether to use `aiosqlite` or `asyncio.to_thread`-wrapped stdlib `sqlite3` (Phase 2 call; ADR-006 leans toward stdlib + to_thread since SQLite is fast).
- Logging library (stdlib `logging` vs `structlog` vs `loguru`) — Phase 2 call.
- Secrets handling beyond env vars (Phase 2 call).
