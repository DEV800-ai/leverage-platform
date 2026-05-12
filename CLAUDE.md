# CLAUDE.md — Working guidelines for `leverage-platform`

## Project context

`leverage-platform` is a Python infrastructure library for AI-native products. It is **not** a product, **not** a SaaS, **not** an end-user application. See `PLAN.md` and `DESIGN.md` for the full architecture.

The only sanctioned consumer is `proof/thirty_day_leverage_bet/` — an integration test, not a product.

## Core working principles

1. **Memory-first, not chat-first.** All durable state is structured (Pydantic + DB rows). No "free-text scratchpad" patterns.
2. **Human agency over full automation.** Workflows are explicit Python with predetermined exit conditions. No autonomous loops.
3. **Compounding data layer.** Every LLM call produces an `AgentRun` row. Every workflow step produces an `Artifact`. No "fire and forget."
4. **Reusable infrastructure, not product features.** A primitive belongs in the platform only if ≥ 2 plausible future products would need it. See PLAN.md "v0 discipline check."
5. **Deterministic-first, LLM-second.** Use rules / schema validation / hash checks before reaching for an LLM judge.
6. **Audit is not optional.** No path through the platform writes to the LLM without recording an `AgentRun`. Silent calls are a bug.

## Architecture rules

### 1. Layer hierarchy is one-way

`runtime` depends on `llm` + `schemas` + `storage`. `llm` depends on `schemas`. `storage` depends on `schemas`. `eval` depends on `runtime`. **No backward dependencies.** If you find yourself importing `runtime` from `schemas`, the design is wrong — push the type down, not the dependency up.

### 2. Domain schemas never enter the platform package

Anything in `src/leverage_platform/schemas/` must be domain-agnostic. `UserProfile`, `Opportunity`, `ThirtyDayBet`, etc. live in `proof/` or future product repos. **Hard rule, no exceptions.**

Platform schemas are: `Tenant`, `AgentRun`, `WorkflowRun`, `Artifact`, `CostEntry`, `EvalReport`, `EvalCriterion`, `LLMParameters`, `TextResult`, `StructuredResult`.

### 3. Structured outputs are required

All `@agent` functions return a Pydantic model. Raw strings are not allowed as agent return values. If a use case truly needs free text, wrap it: `class TextWrapper(BaseModel): text: str`.

### 4. No agent-to-agent calls

Agents call only: the LLM (via the provider abstraction), the platform's eval primitive, pure-function helpers. Agents **do not** call other agents directly. Composition is the workflow's job.

### 5. Audit writes are intentional, not aspirational

The `@agent` decorator writes an `AgentRun` row on every call. Don't bypass this. Don't add a `skip_audit=True` parameter "just for testing" — use an in-memory store fixture instead.

### 6. Every recommendation has a reason

When the eval primitive returns an `EvalReport`, every criterion is named and the failure reason is captured. No `accepted: False, reason: "didn't pass"` — say *why*.

## Coding guidelines

### Types

- **Pydantic v2** for all schemas. No `TypedDict`, no `dataclass` for data that crosses module boundaries.
- **Type hints everywhere.** `from __future__ import annotations` at the top of every file. Run `ruff` with type-related rules enabled.
- **No `Any`.** If you genuinely need `Any`, write a comment explaining why and link an issue to revisit.
- **`Decimal` for money.** Never float for `cost_usd`. See ADR-008.

### Async

- **Async-first.** All I/O-bound platform code is `async def`. Provide `run_sync(...)` for callers that can't be async.
- **`asyncio.to_thread` for sync DB code** (stdlib `sqlite3` is sync; wrap writes). See ADR-006.
- **Never** `time.sleep()` in async code — use `asyncio.sleep()`.

### Errors

- **Specific exceptions, not bare `Exception`.** Define per-module exception types in `errors.py` if needed.
- **Validation errors fail fast.** Don't catch a Pydantic `ValidationError` and continue silently — log it, write `AgentRun.status="failed"`, propagate.
- **No silent fallbacks.** If an LLM call returns malformed JSON 3 times, surface the failure; do not synthesize a default.

### Logging

- **Stdlib `logging`** in v0. Reconsider in Phase 2.
- **Structured logs in production.** JSON output with `tenant_id`, `workflow_run_id`, `agent_run_id` fields. Human-readable on TTY.
- **Never log secrets** (API keys, raw prompts that contain user PII).

### Comments

- **Default to no comments.** Code says what; commit messages say why.
- **Exception:** load-bearing invariants that aren't obvious. Write one-liners. Don't write multi-paragraph docstrings.

### Tests

- **Unit tests** for `@agent` retry, `rule_eval`, schema migration, hash computation.
- **Integration tests** in `proof/.../tests/` against the real provider, on the 5 fixture intakes.
- **No mock-everything tests** that pass even when the implementation is broken.

## Folder discipline

```
src/leverage_platform/    # ONLY platform code; ZERO domain types
proof/                    # the reference scenario; domain types live HERE
tests/                    # platform primitive tests
docs/adr/                 # one ADR per locked decision
docs/source/              # input docs (reference only — do not edit)
```

A pull request that adds a domain type under `src/leverage_platform/schemas/` is wrong. Reject it.

## Anti-patterns

- **Adding a primitive "just in case."** Every primitive needs a justification in PLAN.md or an ADR.
- **Adding a vector store, RAG, or embedding layer.** Out of v0 scope. Move to Tier 2.
- **Adding auth.** Not in v0. `tenant_id` is opaque.
- **Hard-coding model names** in the runtime. Models flow via `LLMParameters` or `LLMProvider` config; don't `if model == "claude-opus-4-7":` in `@agent`.
- **Long prompts hard-coded in agent functions.** Put prompts in `proof/.../prompts/` (or in the future, a prompt registry). Hash the template; pass variables separately.
- **Catching `Exception` to "be safe."** Specific exception types, or let it propagate.
- **Adding "TODO: refactor later"** without a linked issue or ADR. Permanent TODOs rot.

## Decisions locked behind ADRs

When in doubt, check `docs/adr/`. Currently locked (do not relitigate without a new ADR):

| ADR | Decision |
| --- | --- |
| 001 | Tenant isolation is product-side; platform attributes only |
| 002 | SQLite-first storage; Postgres-compatible schema design rules |
| 003 | `prompt_hash` = template; `input_hash` = vars |
| 004 | Artifacts immutable per workflow run; versioning via `schema_name` |
| 005 | v0 workflows are not crash-durable |
| 006 | Async-first runtime; SQLite via `asyncio.to_thread` |
| 007 | `LLMParameters` is a typed Pydantic model, not `dict` |
| 008 | Cost as `Decimal`, never float |
| 009 | `WorkflowRun.status` enum: running / succeeded / failed / partial / aborted |
| 010 | `workflow_run_id` propagates via `AgentContext` first-arg |

## When you (Claude or human) work on this repo

- **Read `PLAN.md` first** — it has the phase you're in.
- **Check the ADR list before changing a primitive's contract.** If an ADR locks the decision, write a new ADR (don't silently violate the old one).
- **Push back on scope creep.** "While I'm here, let me also add X" is how the framework-before-product trap closes.
- **No code outside the task scope.** Bug fixes don't get refactors. Spec docs don't get implementations.
- **Terse responses.** Bullets > paragraphs. No trailing summaries.

## What this repo deliberately does not have

No frontend. No auth. No payment. No SaaS deployment. No vector DB. No memory graph. No agent-to-agent calls. No autonomous loops. No Temporal. No connection to other repos.

If a task asks for any of these, push back — they're explicitly out of v0 scope per PLAN.md "Hard 'no's for v0."
