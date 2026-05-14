# leverage-platform

Reusable infrastructure for AI-native products that help people **preserve and expand agency** in an AI economy. Not a productivity-maximization toolkit.

Working name. The repo may be renamed once a first product picks a permanent positioning.

**Status:** Phases 0–3 shipped. Runtime, `@agent` decorator, SQLite storage, eval primitives (rules + LLM judge), Anthropic + Mock providers, and the 30-Day Leverage Bet reference scenario are all in place. 47 tests pass. Phase 4 (cost CLI, observability, eval hardening) is captured as a demand-driven backlog in [`PLAN.md`](PLAN.md) — items get pulled in when the first product on top of the platform asks for them.

## What this is

A Python library + CLI of small, composable primitives every multi-user AI product needs:

- LLM provider abstraction (vendor-neutral)
- Agent runtime with full audit (`AgentRun`)
- Multi-tenant cost attribution (`tenant_id` + cost ledger)
- Structured output validation (Pydantic)
- Workflow composition (typed run-log, not a DSL)
- Eval primitive (deterministic rules first, LLM-judge second)
- Typed artifact persistence (immutable per run)

Together, `AgentRun` + `WorkflowRun` + `Artifact` form a **Learning System substrate** — products built on top can derive what worked, what failed, and what should change next, without re-instrumenting from scratch.

## What this is NOT

- Not a product. No UI, no auth, no payment, no SaaS framing.
- Not a productivity-optimization layer. The platform never reduces the user to a productivity / income / optimization target. See [`CLAUDE.md`](CLAUDE.md) "Human Agency Guardrail."
- Not a vector store, RAG layer, memory graph, agent fleet manager, or autonomous-execution engine.
- Not connected to any other repo.

## Where to start

- [`PLAN.md`](PLAN.md) — strategy, primitives, phases, design lens.
- [`DESIGN.md`](DESIGN.md) — architecture and data flow.
- [`CLAUDE.md`](CLAUDE.md) — coding/working guidelines.
- [`AGENTS.md`](AGENTS.md) — the reference proof scenario (30-Day Leverage Bet).
- [`docs/adr/`](docs/adr/) — 10 locked architecture decisions.

## Hard "no"s for v0

- No frontend / UI / dashboard.
- No primitive added without 2+ plausible product shapes needing it.
- No primitive that fails the agency check (see PLAN.md "v0 discipline check").
- No connection to `signalalpha` or other existing repos.
- No autonomous agent chains, no Temporal, no SaaS deployment.
- No vector store, embeddings, RAG, or memory graph in v0.
