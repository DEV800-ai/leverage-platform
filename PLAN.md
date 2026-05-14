# leverage-platform — Plan (v0.3)

## What changed in v0.3

- Replaced the generic "Profile → Suggestion → Critic" proof with a concrete reference scenario: **30-Day Leverage Bet**.
- Added `Artifact` as the 8th v0 primitive.
- Removed `embed()` from the LLMProvider contract — moved to Tier 2.
- Added minimal prompt traceability fields to `AgentRun` (`prompt_name`, `prompt_hash`, `input_hash`, `output_hash`, `model_parameters`, optional `prompt_version`).
- Storage: SQLite-first for local dev, Postgres-compatible schema design. DuckDB rejected as audit store.
- Package layout: single Python package with internal modules (not workspace packages).
- Eval: deterministic-first (Pydantic + rules), LLM-as-judge second.
- Async-first runtime with `run_sync()` helpers for scripts.
- Tenant ID is an opaque string; the platform does not provide auth.
- Locked 10 architecture decisions as ADRs under `docs/adr/`.

## North star

`leverage-platform` is a Python infrastructure layer for building AI-native products that help individuals and small teams **coordinate intelligence, evaluate opportunities, run agent workflows, and compound learning over time** — in service of *expanding human agency*, not replacing or instrumentalizing it.

It is a library + CLI, not a SaaS. Products built on top of it will be separate repos.

### Design lens

Two external lenses shape the platform's posture:

- **From the Microsoft Work Trend Index 2026 line of thinking:** agents take over more *execution*; humans gain more *agency* (intent-setting, judgment, orchestration, ownership of outcomes). The systems that win in this world are **Learning Systems** — they accumulate proprietary intelligence from real work. The platform's `AgentRun` + `WorkflowRun` + `Artifact` triple is *already* a Learning System substrate; products on top can derive what worked, what failed, and what should change, without reinstrumenting.
- **From Heidegger's "The Question Concerning Technology":** modern technology risks enframing the world — including humans — as *standing-reserve* (resources to be measured, optimized, used). The platform must therefore avoid embedding "user-as-resource" assumptions. "What the user chose NOT to optimize" is first-class signal, not noise. See `CLAUDE.md` "Human Agency Guardrail."

These are *design lenses* — they shape which primitives we accept into v0 and how we frame them. They do not require new primitives by themselves; the existing 8 cover the Learning System substrate already.

## Reference scenario: 30-Day Leverage Bet

Pure infrastructure produces guessed APIs. A real product produces premature coupling. The reference scenario is the middle path: a concrete workflow the platform must support end-to-end, used only to stress-test the primitives.

**Goal of the scenario:** given a raw intake JSON for a person, produce one validated 30-day experiment that builds leverage, skills, economic optionality, or career resilience.

```
raw_intake
  → profile_agent      → UserProfile
  → risk_agent         → RiskMap
  → opportunity_agent  → OpportunityMap
  → bet_designer_agent → ThirtyDayBet
  → critic_eval_agent  → EvalReport (accepted/rejected)
```

Full agent definitions live in `AGENTS.md`. Domain schemas (`UserProfile`, `RiskMap`, `OpportunityMap`, `ThirtyDayBet`) live in `proof/thirty_day_leverage_bet/` — **not** in the platform.

The scenario is here so primitives have something realistic to push against. It is not a product. No UI, no users, no income.

## v0 discipline check

A primitive belongs in v0 only if **all three** hold:

1. The 30-Day Leverage Bet reference scenario requires it.
2. At least two plausible future product shapes (career copilot, venture builder, opportunity engine, SMB AI operator, learning system, personal economic dashboard) would need it.
3. **Agency check:** the primitive serves human agency — it increases user capability, decision quality, or legibility of outcomes. A primitive whose only purpose is throughput, cost, or automation, *without* making the user more capable, does not pass.

If a primitive serves only one product, it belongs in product code, not the platform. If it fails the agency check, it belongs in product code regardless of how many products would use it.

## v0 primitives (8)

| # | Primitive | Why in v0 |
| --- | --- | --- |
| 1 | **LLM provider abstraction** | Future products must avoid provider lock-in. Anthropic in v0; Protocol contract is the deliverable. |
| 2 | **AgentRun audit table** | Every LLM/agent call must be traceable for cost, debugging, quality, and trust. |
| 3 | **Tenant identity contract** | Multi-user products need cost/data/audit attribution. Platform carries `tenant_id`; it does **not** issue or validate identities (see ADR-001). |
| 4 | **Cost ledger** | A SaaS or paid tool must know cost per tenant / workflow / agent. Derived from AgentRun. |
| 5 | **Structured output validation** | Agent-to-agent contracts must be typed and validated (Pydantic). |
| 6 | **Workflow primitive** | Compose 2+ agents with retry, run-tree, and audit. Explicit Python, not DSL. |
| 7 | **Eval primitive** | Judge outputs: deterministic rules first, LLM-judge second. |
| 8 | **Artifact primitive** | Typed workflow outputs (immutable per run), separate from raw agent logs so workflows can pass durable typed objects between steps. |

## What lives where — platform vs. proof scenario

**Hard rule:** domain schemas never enter the platform package.

| Schema | Lives in | Owned by |
| --- | --- | --- |
| `Tenant`, `AgentRun`, `WorkflowRun`, `Artifact`, `CostEntry`, `EvalReport`, `EvalCriterion` | `src/leverage_platform/schemas/` | Platform |
| `LLMParameters`, `TextResult`, `StructuredResult` | `src/leverage_platform/llm/` | Platform |
| `AgentContext` | `src/leverage_platform/runtime/` | Platform |
| `UserProfile`, `RiskItem`, `RiskMap`, `Opportunity`, `OpportunityMap`, `ThirtyDayBet` | `proof/thirty_day_leverage_bet/schemas.py` | Proof scenario only |

**Note on `EvalReport`:** the proof's Critic agent consumes the platform's `eval` primitive — it does NOT define its own `EvalReport` type. `EvalReport` is platform-owned (see ADR-003-fix-5 and `AGENTS.md` for the Critic's contract).

## Hard "no"s for v0

- No frontend, no dashboard, no UI.
- No auth provider (the platform carries `tenant_id`; doesn't issue or validate it — see ADR-001).
- No payment / subscription / billing logic.
- No vector store, no embeddings, no RAG, no long-term memory graph.
- No browser automation, no web search.
- No autonomous infinite loops, no agent-to-agent hidden calls.
- No product-specific UI or scaffolding.
- No SaaS deployment.
- No Temporal / Trigger.dev or other durable-workflow engine. v0 workflows are in-process (see ADR-005).
- No relationship to `signalalpha` or any other existing repo.
- No primitive unless it serves the reference scenario **and** ≥2 future product shapes.

## Storage decision (summary; details in ADR-002)

```
Local development: SQLite (with WAL mode)
Production-compatible schema: Postgres-portable column types and conventions
Later analytics: DuckDB optional, never primary audit store
```

v0 implements **only** `storage/protocol.py` + `storage/sqlite.py`. A `postgres.py` adapter is explicitly **not** built in v0 — Postgres is a schema-design constraint (TEXT not VARCHAR(n), UUID-as-TEXT, ISO datetimes, JSON-as-TEXT), not a v0 implementation. Implementing Postgres is the responsibility of the first product that needs it.

## Runtime decision (summary; details in ADR-006)

- Async-first (`async def` everywhere in the platform).
- Sync helper for CLI/scripts: `run_sync(workflow, ctx, input_data)`.
- SQLite stdlib driver is sync; calling it from async context blocks the event loop for ~1ms per write. Acceptable for v0; revisit if a real consumer measures it as painful.

## LLM provider contract (v0)

```python
class LLMProvider(Protocol):
    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> TextResult: ...

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        model: str | None = None,
        parameters: LLMParameters | None = None,
    ) -> StructuredResult[T]: ...
```

`embed()` is explicitly out of v0 (moved to Tier 2 — vector storage / RAG concerns).

`LLMParameters` is a typed Pydantic model (not `dict`) — see ADR-007.

### `ToolCall` vs Anthropic `tool_use`

The platform uses Anthropic's `tool_use` mechanism **internally** to coerce structured output (the provider builds a one-shot schema-as-tool to force JSON-shaped responses). This is an implementation detail of `generate_structured`. It is **not** the same thing as a platform-level `ToolCall` primitive.

A real `ToolCall` primitive — `ToolDefinition`, `ToolRegistry`, `ToolRuntime`, a `ToolCall` audit table, `ToolError`, permission boundaries, bounded tool loops — is the next major primitive candidate after Phase 2 stabilizes. It is **not** in v0.

Important corollary: do not sneak tools into agent bodies as plain Python helpers. Side effects performed by an agent that bypass `invoke_llm` are invisible to `AgentRun` and break auditability. When tools become a first-class primitive, they will be routed through the runtime and persisted as their own audit rows.

Related rule: a single `@agent` function makes **at most one** `invoke_llm` call. Multiple calls would silently corrupt the `AgentRun` row's `prompt_hash` / `cost_usd` / `model`; the runtime now fails fast on the second call. Orchestrator-style agents that make no LLM call must use `@agent(pure=True)` and may delegate to nested agents. See ADR-011.

## AgentRun fields (v0)

Required:
- `id: UUID`
- `tenant_id: str` (opaque)
- `workflow_run_id: UUID | None`
- `agent_name: str`
- `prompt_name: str` — human-readable name of the prompt template
- `prompt_hash: str` — SHA-256 of the **prompt template** (before variable substitution); see ADR-003
- `input_hash: str` — SHA-256 of the variables passed into the template
- `output_hash: str` — SHA-256 of the validated output JSON
- `model: str` — full model identifier (e.g., `claude-opus-4-7`)
- `model_parameters: dict` — JSON of the `LLMParameters` used
- `input_tokens: int`
- `output_tokens: int`
- `cost_usd: Decimal` — never float; see ADR-008
- `latency_ms: int`
- `status: Literal["pending", "running", "succeeded", "failed", "needs_review"]`
- `error: str | None`
- `started_at: datetime` (UTC, ISO)
- `ended_at: datetime | None`

Optional:
- `prompt_version: str | None` — for future prompt registries (not used in v0).

## WorkflowRun fields (v0)

- `id: UUID`
- `tenant_id: str`
- `workflow_name: str`
- `status: Literal["running", "succeeded", "failed", "partial", "aborted"]` — see ADR-009
- `input_artifact_id: UUID | None`
- `final_artifact_id: UUID | None`
- `started_at: datetime`
- `ended_at: datetime | None`
- `error: str | None`

## Artifact fields (v0)

- `id: UUID`
- `tenant_id: str`
- `workflow_run_id: UUID`
- `created_by_agent_run_id: UUID | None`
- `type: str` — short kind label (e.g., `"user_profile"`, `"risk_map"`)
- `schema_name: str` — versioned, e.g., `"UserProfile@v1"`; see ADR-004
- `data: dict` — JSON-serialized typed object
- `created_at: datetime`

Artifacts are immutable. Re-running a workflow produces new artifact rows; existing rows are never updated.

## Retry policy (v0)

The runtime's `@agent` decorator retries automatically. Defaults:

| Failure mode | Retry? |
| --- | --- |
| Network timeout, connection refused | Yes — up to 2 retries |
| HTTP 429 (rate limit) | Yes — exponential backoff with jitter, capped at 30s |
| HTTP 5xx | Yes — up to 2 retries |
| Provider JSON-parse failure | Yes — up to 1 retry |
| HTTP 4xx (other than 429) | **No** — likely a bug, not transient |
| Pydantic validation failure | **No** — semantic bug; retrying re-burns tokens |
| Platform eval failure | **No** — caller decides |
| User-cancelled (CancelledError) | **No** — propagate immediately |

Max retries: 2. Backoff: exponential with jitter (base 1s, factor 2, jitter ±25%, cap 30s). Configurable per-agent via decorator parameters.

## Package layout

```
leverage-platform/
├── src/
│   └── leverage_platform/
│       ├── llm/
│       │   ├── provider.py        # Protocol + LLMParameters / *Result types
│       │   ├── anthropic.py       # concrete implementation
│       │   └── results.py
│       ├── runtime/
│       │   ├── agent.py           # @agent decorator
│       │   ├── workflow.py        # workflow primitive
│       │   ├── context.py         # AgentContext (carries tenant + workflow_run_id)
│       │   └── retry.py
│       ├── schemas/
│       │   ├── base.py            # Tenant, base mixins
│       │   ├── runs.py            # AgentRun, WorkflowRun
│       │   ├── artifacts.py       # Artifact
│       │   ├── cost.py            # CostEntry
│       │   └── eval.py            # EvalReport, EvalCriterion
│       ├── storage/
│       │   ├── protocol.py        # storage interface
│       │   └── sqlite.py          # the only adapter in v0
│       ├── eval/
│       │   ├── rules.py           # rule-based eval
│       │   └── judge.py           # LLM-as-judge eval
│       └── observability/
│           ├── cost.py            # cost CLI
│           └── traces.py          # log-shape helpers
├── proof/
│   └── thirty_day_leverage_bet/
│       ├── __init__.py
│       ├── schemas.py             # UserProfile, RiskMap, OpportunityMap, ThirtyDayBet
│       ├── agents.py              # the 5 proof-scenario agents
│       ├── workflow.py            # the orchestration
│       ├── fixtures/
│       │   └── intakes/           # 5 sample intake JSONs
│       └── tests/
├── docs/
│   ├── adr/                       # ADR-001 .. ADR-010 (locked)
│   └── source/                    # original product-design docs (reference only)
├── tests/                         # platform primitive tests only
├── CLAUDE.md
├── DESIGN.md
├── AGENTS.md
├── PLAN.md
├── HANDOFF.md
├── README.md
└── pyproject.toml                 # created in Phase 1
```

Single Python package. No workspace packages until a product forces the split.

## Phases

### Phase 0 — Design (this doc)

**Status:** in progress.

Deliverables:
- `PLAN.md` (v0.3)
- `DESIGN.md`
- `CLAUDE.md`
- `AGENTS.md`
- 10 ADRs under `docs/adr/`
- Copy of v0.3 instructions in `docs/source/`

Acceptance: all documents written and consistent. No code yet.

### Phase 1 — Skeleton

Deliverables:
- `pyproject.toml` with uv config, Python ≥ 3.12, ruff + pytest dev deps.
- Empty package directories per the layout above (each with a one-line `__init__.py` docstring).
- Base schemas only (`Tenant`, `AgentRun`, `WorkflowRun`, `Artifact`, `CostEntry`, `EvalReport`, `EvalCriterion`) — Pydantic models, no behavior.
- Placeholder `proof/thirty_day_leverage_bet/` with `__init__.py` and a TODO marker.
- CI config: ruff lint + pytest on an empty suite.

Acceptance:
- `uv run pytest` passes (empty suite).
- `uv build` builds the package.
- `ruff check` passes.

### Phase 2 — Runtime + LLM provider

Deliverables:
- Anthropic provider implementing `LLMProvider` Protocol.
- `LLMParameters` typed model (ADR-007).
- `@agent` decorator with audit + retry per policy above.
- `storage/sqlite.py` implementing the storage protocol; schema migrations as embedded SQL.
- `AgentContext` with `tenant_id` and `workflow_run_id` carried through (ADR-010).
- `WorkflowRun` primitive (a Python class) that wraps an explicit sequence of agent calls.

Acceptance: a typed test agent runs end-to-end, produces a `StructuredResult[T]`, and writes one `AgentRun` row to SQLite with all required fields populated.

### Phase 3 — Reference scenario

Deliverables:
- `proof/thirty_day_leverage_bet/agents.py` — 5 agents per `AGENTS.md`.
- `proof/thirty_day_leverage_bet/workflow.py` — orchestration.
- `proof/thirty_day_leverage_bet/schemas.py` — domain types (UserProfile, RiskMap, OpportunityMap, ThirtyDayBet).
- `proof/thirty_day_leverage_bet/fixtures/intakes/*.json` — 5 sample intakes spanning income-pressure / skill-level / weekly-time dimensions.
- Critic agent **consumes** `leverage_platform.eval` (rules + judge); does not implement its own.

Acceptance:
- Workflow runs end-to-end on each of the 5 fixture intakes.
- Per run: exactly 5 `AgentRun` rows + 1 `WorkflowRun` row + 5 `Artifact` rows (one per step).
- Cost attributed to tenant `acme` (or per-fixture tenant).
- Rule-based eval passes 100% (structure rules are well-defined and stable).
- LLM-judge returns `accepted=true` on ≥ 3 of 5 sample profiles.

### Phase 4 — API hardening (backlog, demand-driven)

Phase 4 exists to reduce clumsiness discovered while implementing the proof workflow and the first product built on top of the platform. **It is not a feature-expansion phase.** Items get pulled in only when the first product asks for them; nothing is built speculatively.

Minimal eval primitives (`eval/rules.py`, `eval/judge.py`) shipped in Phase 3 because the proof scenario's Critic agent required them. They are intentionally small — hardening lives here.

**Accepted backlog items:**

1. **Tiny `Prompt` value object** — wrap `(name, version, template)` and compute `prompt_hash` once. Goal: cleaner `invoke_llm` and stable prompt traceability. *Not* a prompt registry, storage layer, lifecycle system, or marketplace.
2. **`ctx.write_artifact(...)`** — allow workflows to persist artifacts that are not produced by a single agent (aggregate summaries, merged artifacts, post-eval artifacts). Workflow-level artifacts persist with `agent_run_id = None` and `source = "workflow"`. Removes the need to invent "fake agents" just to write an artifact.
3. **Cost CLI + grouped queries** — `uv run leverage-platform cost --tenant <id> --since 7d`, plus `--group-by agent|model|workflow`. Table or JSON output. No dashboard.
4. **Minimal structured logging / traces** — emit log lines with `tenant_id`, `workflow_run_id`, `agent_run_id`, `agent_name`, `status`, `duration_ms`, `cost_usd`, `model`. JSON or simple `logger.info("agent_run.succeeded", extra={...})`. No OpenTelemetry, no Grafana, no distributed tracing infrastructure.
5. **Eval hardening** — improve `EvalReport` ergonomics, reusable rule-check helpers, better failure messages. **Must preserve deterministic-first order**: schema validation → rule checks → LLM judge only when needed. LLM judge must not become the first-line evaluator.

**Explicitly deferred (not Phase 4):**

- Prompt registry / prompt storage / prompt directory conventions
- `ToolCall` runtime (`ToolDefinition`, `ToolRegistry`, `ToolError`, permission boundaries)
- Memory graph
- Vector store / RAG
- UI / dashboard
- Auth / billing
- OpenTelemetry / full observability infrastructure
- Autonomous loops
- Agent-to-agent hidden calls
- Product-specific SaaS logic

**Acceptance for any Phase 4 item:**

- A real consumer (the product, or a clear shape from the product plan in `docs/product/`) needs it.
- It does not break the v0 discipline check (serves human agency, ≥2 product shapes plausible).
- It does not introduce any item from the "Explicitly deferred" list above as a side effect.

### Phase 5 — Documentation

Deliverables:
- ADRs reviewed and finalized.
- `docs/getting-started.md` — 10-minute read for a future product author.
- Update `DESIGN.md` and `PLAN.md` with anything that changed in Phases 3–4.

Acceptance: a developer who has never seen this repo can read `getting-started.md` and run the proof scenario locally within 10 minutes.

### Phase 6 — Wait

Don't add primitives in the abstract. The next change to the platform should be driven by the first real product asking for something specific.

## How a future product consumes the platform

```python
# in some_product/main.py
from leverage_platform.runtime import agent, workflow, AgentContext
from leverage_platform.llm import AnthropicProvider, LLMParameters
from leverage_platform.storage.sqlite import SQLiteStore
from leverage_platform.eval import rule_eval, llm_judge

from .schemas import MyProductOutput  # product-specific Pydantic model

provider = AnthropicProvider(api_key=...)
store = SQLiteStore(path="./product.db")

@agent(
    name="my_product_agent",
    schema=MyProductOutput,
    provider=provider,
    store=store,
)
async def my_product_agent(ctx: AgentContext, raw_input: dict) -> MyProductOutput:
    ...
```

The product brings: its Pydantic schemas, its prompts, its workflow shape, its UI, its auth, its deployment. The platform brings: LLM call, audit row, cost attribution, retry, eval, artifact persistence.

## Open questions remaining (small)

- **Logging format** — JSON-structured logs vs. human-readable? Lean: JSON in production, human-readable on TTY. To be settled in Phase 2.
- **Secrets handling** — env vars for v0 (no secrets manager integration). Confirm in Phase 2.
- **Schema migrations** — embedded SQL files, or Alembic? Lean: embedded SQL until pain. To be settled in Phase 2.

## What this plan deliberately does NOT do

- Doesn't promise a date.
- Doesn't pick a frontend (no frontend at this layer).
- Doesn't define future products. That conversation happens after v0 ships.
- Doesn't commit to a monetization model — deferred per locked decision #3.
- Doesn't pre-empt any of Phases 3–4 with code in Phase 0–1.
