# ADR-005 — v0 workflows are not crash-durable

**Status:** Accepted (2026-05-12)

## Context

A workflow spans multiple LLM calls. Typical run: 5 agents × ~10s per call = ~1 minute; longer if rate limits hit. If the process crashes mid-workflow, the runtime can't recover. The question: does v0 ship a durable-workflow engine?

## Decision

v0 workflows are **in-process and not crash-durable.**

- A crashed workflow leaves a `WorkflowRun` row in `status="running"` (the runtime cannot mark it `failed` if the process is gone).
- Partial work (artifacts written by completed steps) is preserved in the database, but the workflow cannot resume from where it left off.
- The caller (product) is expected to either: re-run the workflow from scratch, or use the partial artifacts manually if the product has logic to do so.

The platform does **not** integrate Temporal, Trigger.dev, Celery, dramatiq, or any durable-execution engine in v0.

## Consequences

- **Crash recovery is the product's call.** A janitor query identifies zombie rows: `SELECT * FROM workflow_run WHERE status='running' AND started_at < datetime('now', '-1 hour')`. Marking these as `aborted` (ADR-009) is a product responsibility.
- **A product needing crash-durability for long-running workflows should NOT use the platform's `Workflow` primitive yet.** It can still use `@agent` directly (each agent call is audited) and provide its own orchestration with whatever durability layer it chooses.
- **v0 is biased toward "small in-process scripts and FastAPI endpoints,"** not "long-running background jobs."
- **Operational complexity stays low.** No queues, no workers, no schedulers, no separate runtime to monitor.

## Alternatives considered

- **Integrate Temporal in v0.** Rejected: operational complexity (Temporal cluster, workers, signal/query semantics, retry policies, timeouts) is too high without a consumer demanding it.
- **Build a durable workflow primitive ourselves.** Rejected: re-implementing Temporal poorly is a well-known failure mode. v0 doesn't have the discipline.
- **Mark crashed workflows automatically on next startup.** Rejected: requires a startup hook that scans for stale rows — small implementation, deferred until a product asks.

## When to revisit

A real product reports that a crashed workflow caused user-visible damage **and** the workaround (re-run from scratch) is unacceptable. At that point, options to consider:

1. Add a `DurableWorkflow` primitive alongside `Workflow`, backed by Temporal or similar.
2. Add a checkpoint-based recovery using artifact persistence (workflow re-runs only the agents whose artifacts are missing).
3. Recommend the product use its own orchestration layer and just consume `@agent` directly.

Until then: the workflow primitive in v0 is best-effort, not durable.
