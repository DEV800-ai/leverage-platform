# Claude Design Update Instructions — leverage-platform v0.3

## Purpose

Update the existing `leverage-platform` plan from a generic AI-agent infrastructure plan into a small, grounded platform shaped by a concrete reference scenario.

This is still **not** a commercial product. It is a reusable infrastructure layer for future B2C / small-B2B AI-native products. The goal is to avoid building a framework in the abstract while also avoiding premature product commitment.

## Executive instruction to Claude

Do **not** implement code yet.

First update the design documents only:

- `PLAN.md`
- `DESIGN.md`
- `CLAUDE.md`
- `AGENTS.md`
- optionally add ADR drafts under `docs/adr/`

The output should be a revised design package that is ready for Phase 1 implementation.

---

## Core verdict

The current plan is directionally correct: it defines a small set of reusable primitives, avoids UI/auth/memory/RAG too early, and includes a proof scenario to prevent pure infrastructure drift.

However, the current proof scenario is too generic:

> Profile Agent → Suggestion Agent → Critic Agent

It tests the API shape but does not test the future category we care about: helping individuals build leverage, income options, adaptability, and economic resilience in an AI-native world.

Replace it with a more concrete reference scenario:

> **30-Day Leverage Bet** — convert a person’s profile into a validated 30-day experiment for building leverage, skills, assets, income optionality, or career resilience.

---

## Revised product framing

Replace this decision:

> No product first — build infra.

With this:

> No commercial product first. Build reusable infrastructure through one concrete reference scenario: **30-Day Leverage Bet**.

This keeps the platform product-agnostic while grounding the primitives in a real workflow.

### Why this matters

Pure infrastructure creates guessed APIs. A commercial product creates premature coupling. A reference scenario gives the platform something realistic to push against without committing to a market or UI.

---

## Updated north star

`leverage-platform` is a Python-first infrastructure layer for building AI-native products that help individuals and small teams coordinate intelligence, evaluate opportunities, run agent workflows, and compound leverage over time.

It starts as a library + CLI, not a SaaS.

Future products may include:

- career reinvention copilots
- personal venture builders
- opportunity engines
- small-business AI operators
- learning/adaptation systems
- personal economic operating systems

The platform itself must remain reusable.

---

## v0 discipline check

A primitive belongs in v0 only if it is required by:

1. the `30-Day Leverage Bet` reference scenario, and
2. at least two plausible future product shapes.

If a primitive serves only one product, it belongs in product code, not the platform.

---

## Required v0 primitives

Keep the plan small. v0 should include the following primitives:

| Primitive | Why it belongs in v0 |
| --- | --- |
| LLM provider abstraction | Future products must avoid provider lock-in. |
| AgentRun audit table | Every LLM/agent call must be traceable for cost, debugging, quality, and trust. |
| Tenant identity contract | Multi-user products need cost/data/audit attribution. Platform carries `tenant_id`; it does not provide auth. |
| Cost ledger | A SaaS or paid tool must know cost per tenant/workflow/agent. |
| Structured output validation | Agent-to-agent contracts must be typed and validated. |
| Workflow primitive | Compose 2+ agents with retry, run-tree, and audit. Use explicit Python, not DSL. |
| Eval primitive | Judge outputs using deterministic rules first, LLM judge second. |
| Artifact primitive | Store typed workflow outputs separately from raw agent logs so workflows can pass durable objects between steps. |

### Important change

`Artifact` should be added as a v0 primitive.

It is not memory. It is not a knowledge graph. It is simply the typed output object produced by an agent or workflow step.

---

## Remove embeddings from v0

The existing provider contract includes:

```python
async def embed(self, texts: list[str], *, model: str | None = None) -> EmbedResult: ...
```

Remove this from v0.

Reason: embeddings imply vector storage, retrieval, memory, dimensions, model choices, and RAG. The current plan explicitly defers vector store and memory to Tier 2, so `embed()` creates an inconsistency.

### Revised v0 provider contract

```python
class LLMProvider(Protocol):
    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        parameters: dict | None = None,
    ) -> TextResult: ...

    async def generate_structured[T: BaseModel](
        self,
        prompt: str,
        schema: type[T],
        *,
        model: str | None = None,
        parameters: dict | None = None,
    ) -> StructuredResult[T]: ...
```

Embeddings move to Tier 2.

---

## Add minimum prompt traceability

Prompt versioning can stay out of v0 as a full system, but prompt traceability cannot be skipped.

Add the following fields to `AgentRun`:

```text
prompt_name
prompt_hash
prompt_version optional
model
model_parameters
input_hash
output_hash
```

This gives enough auditability without creating a prompt registry too early.

---

## Storage decision

Do not use DuckDB as the primary audit store.

Recommended v0 decision:

```text
Local development: SQLite
Production-compatible design: Postgres schema
Later analytics/export: DuckDB optional
```

Why:

- `agent_run`, `workflow_run`, `artifact`, and `cost_ledger` are audit/transactional records.
- The platform is shaped for multi-user web products.
- Postgres is the natural long-term home.
- SQLite keeps local development easy.

---

## Package structure decision

For v0, use a single Python package with internal modules instead of independently installable workspace packages.

Recommended layout:

```text
leverage-platform/
├── src/
│   └── leverage_platform/
│       ├── llm/
│       │   ├── provider.py
│       │   ├── anthropic.py
│       │   └── results.py
│       ├── runtime/
│       │   ├── agent.py
│       │   ├── workflow.py
│       │   ├── context.py
│       │   └── retry.py
│       ├── schemas/
│       │   ├── base.py
│       │   ├── runs.py
│       │   ├── artifacts.py
│       │   └── cost.py
│       ├── storage/
│       │   ├── protocol.py
│       │   ├── sqlite.py
│       │   └── postgres.py
│       ├── eval/
│       │   ├── schema.py
│       │   ├── rules.py
│       │   └── judge.py
│       └── observability/
│           ├── cost.py
│           └── traces.py
├── proof/
│   └── thirty_day_leverage_bet/
├── docs/
│   └── adr/
├── tests/
├── CLAUDE.md
├── AGENTS.md
├── PLAN.md
└── pyproject.toml
```

Rationale: workspace packages are conceptually nice, but premature. There is no real consumer yet that needs to install only one piece. Keep the repo simpler until a product forces the split.

---

## Runtime decision

Use async-first runtime.

But provide sync helpers for CLI/scripts:

```python
run_sync(workflow, ctx, input_data)
```

This preserves FastAPI/web compatibility while keeping local development ergonomic.

---

## Tenant ID decision

Use an opaque string:

```python
tenant_id: str
```

Do not enforce UUID in the platform. Future products may use org IDs, user IDs, slugs, UUIDs, or external IDs.

---

## Eval strategy

Make evaluation deterministic-first and LLM-judge-second.

### Layer 1 — Schema validation

Pydantic validates all structured outputs.

### Layer 2 — Rule-based evaluation

Example checks:

- exactly 5 opportunities
- each opportunity has score 0–100
- each opportunity includes evidence to validate
- each opportunity includes a first action
- `ThirtyDayBet` contains first 48-hour actions
- success and failure metrics are not empty

### Layer 3 — LLM judge

Only then use LLM-as-judge for subjective fit:

- Is this opportunity realistic for the user?
- Is it too generic?
- Does it fit available weekly time?
- Does it create leverage or just another task?
- Can it be validated in 30 days?

This saves cost and makes tests more stable.

---

## Reference scenario: 30-Day Leverage Bet

### Goal

Given a raw intake JSON for a person, produce one validated 30-day experiment that helps the person build leverage, skills, economic optionality, or career resilience.

### Workflow

```text
raw_intake
  -> profile_agent
  -> risk_agent
  -> opportunity_agent
  -> bet_designer_agent
  -> critic_eval_agent
  -> accepted_or_rejected ThirtyDayBet
```

### Agents

#### 1. Profile Agent

Converts raw intake JSON into typed `UserProfile`.

#### 2. Risk Agent

Identifies career/economic risks based on role, skills, market exposure, income dependency, and AI exposure.

Output: `RiskMap`.

#### 3. Opportunity Agent

Produces exactly 5 typed `Opportunity` objects scored against the profile.

Output: `OpportunityMap`.

#### 4. Bet Designer Agent

Chooses one opportunity and turns it into a concrete 30-day plan.

Output: `ThirtyDayBet`.

#### 5. Critic/Eval Agent

Rejects generic or unrealistic bets.

Output: `EvalReport`.

### Required audit behavior

Each agent call must create one `AgentRun` row with:

- tenant ID
- workflow run ID
- agent name
- prompt hash
- input hash
- output hash
- model/provider
- token usage
- cost
- latency
- status
- error if failed

The parent workflow creates one `WorkflowRun` row.

### Required artifacts

Each step should produce an `Artifact`:

- `UserProfile`
- `RiskMap`
- `OpportunityMap`
- `ThirtyDayBet`
- `EvalReport`

---

## Suggested domain schemas for proof scenario

```python
class UserProfile(BaseModel):
    current_role: str
    skills: list[str]
    interests: list[str]
    weekly_time_hours: int
    risk_tolerance: Literal["low", "medium", "high"]
    income_goal: str | None = None
```

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
        "skill",
        "audience",
        "capital",
        "automation",
        "network",
        "knowledge",
    ]
    score: int

class OpportunityMap(BaseModel):
    opportunities: list[Opportunity]
```

```python
class ThirtyDayBet(BaseModel):
    title: str
    hypothesis: str
    weekly_plan: list[str]
    success_metric: str
    failure_metric: str
    first_48h_actions: list[str]
    expected_asset_created: str
```

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

---

## Artifact primitive

Add this as a platform schema:

```python
class Artifact(BaseModel):
    id: UUID
    tenant_id: str
    workflow_run_id: UUID
    created_by_agent_run_id: UUID | None = None
    type: str
    schema_name: str
    data: dict
    created_at: datetime
```

Artifacts are typed workflow outputs, not long-term memory.

---

## Revised phases

### Phase 0 — Update design docs

Update `PLAN.md`, `DESIGN.md`, `CLAUDE.md`, and `AGENTS.md` according to this instruction document.

Acceptance:

- Reference scenario is now `30-Day Leverage Bet`.
- v0 primitives include Artifact.
- embeddings are removed from v0.
- storage decision is SQLite-local/Postgres-compatible.
- eval is deterministic-first.
- package layout is single package.
- no code is implemented.

### Phase 1 — Skeleton

- create `pyproject.toml`
- create package directories
- define base schemas only
- create placeholder proof scenario
- configure ruff + pytest

Acceptance:

```bash
uv run pytest
uv build
```

both pass.

### Phase 2 — Runtime + LLM provider

- implement Anthropic provider behind protocol
- implement `@agent` decorator
- implement `AgentRun` audit
- implement SQLite storage adapter
- implement basic retry policy

Acceptance:

A typed test agent runs and writes one `AgentRun` row.

### Phase 3 — Reference scenario

Implement `proof/thirty_day_leverage_bet/`.

Acceptance:

- workflow runs end-to-end
- five agent runs are recorded
- one workflow run is recorded
- artifacts are saved
- cost is attributed to tenant `acme`

### Phase 4 — Eval + observability

- implement rule-based eval
- implement LLM judge primitive
- implement cost CLI
- refine APIs based on proof scenario pain

Acceptance:

- deterministic eval catches invalid outputs
- LLM judge can reject weak bets
- cost CLI reports per-tenant cost

### Phase 5 — Documentation

- add ADRs for major decisions
- add getting-started guide
- explain how a future product would consume the platform

Acceptance:

A developer can understand the platform in 10 minutes and run the proof scenario locally.

---

## Updated hard no's for v0

- no frontend
- no dashboard
- no auth provider
- no payment/subscription logic
- no vector store
- no embeddings
- no RAG
- no long-term memory graph
- no browser automation
- no autonomous infinite loops
- no agent-to-agent hidden calls
- no product-specific UI
- no SaaS deployment
- no Temporal/Trigger.dev yet
- no relationship to `signalalpha`
- no primitive unless it serves the reference scenario and 2+ future products

---

## Specific instruction block for Claude

Use this block directly if needed:

```text
Update the leverage-platform design docs according to the v0.3 direction.

Do not implement code yet.

Required changes:

1. Replace the generic proof scenario with a concrete reference scenario named "30-Day Leverage Bet".
2. Keep the platform product-agnostic, but clarify that v0 is shaped by this reference scenario.
3. Remove embeddings from the v0 LLMProvider contract and move them to Tier 2.
4. Add minimal prompt traceability to AgentRun: prompt_name, prompt_hash, optional prompt_version, model_parameters, input_hash, output_hash.
5. Add an Artifact primitive for typed workflow outputs.
6. Choose async-first runtime with sync helpers.
7. Use a single Python package layout for v0 instead of independently installable workspace packages.
8. Use SQLite for local development and Postgres-compatible schema design; avoid DuckDB as the primary audit store.
9. Make eval deterministic-first and LLM-judge-second.
10. Update phases, acceptance criteria, and hard-no list accordingly.
11. Do not add memory, RAG, vector DB, UI, auth, payment, or SaaS deployment to v0.
12. Do not implement code in this step. Only revise PLAN.md, DESIGN.md, CLAUDE.md, AGENTS.md, and optionally ADR drafts.
```

---

## Final positioning

The platform should not be described as “agent infrastructure” only.

It should be described as:

> Reusable infrastructure for building AI-native products that help people coordinate intelligence, evaluate opportunities, and compound leverage.

The first reference workflow is:

> Help an individual turn their profile into a validated 30-day leverage bet.

This is small enough to implement, but strategically aligned with the larger thesis:

> In an AI-native economy, people will need systems that help them adapt, build leverage, and operate with the capabilities of much larger organizations.
