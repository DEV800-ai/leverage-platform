# ADR-009 — `WorkflowRun.status` enum

**Status:** Accepted (2026-05-12)

## Context

`WorkflowRun.status` needs a clearly enumerated set of values. Without one, products invent ad-hoc strings (`"done"`, `"finished"`, `"partial-success"`, `"weird-thing-happened"`) and UI / queries become brittle.

## Decision

Five values, locked:

| Status | Meaning |
| --- | --- |
| `running` | Workflow has started; not yet completed. Set on `WorkflowRun` creation. |
| `succeeded` | All agents completed successfully; final artifact written. |
| `failed` | One or more agents failed and the workflow could not recover (after retries exhausted). No final artifact. |
| `partial` | Workflow exited intentionally before producing a final artifact — e.g., an agent returned a "needs human review" signal. Some artifacts may exist. |
| `aborted` | Workflow was killed externally (process crash cleanup, user cancel, janitor process — see ADR-005). |

The enum lives in `src/leverage_platform/schemas/runs.py`:

```python
WorkflowStatus = Literal["running", "succeeded", "failed", "partial", "aborted"]
```

## Consequences

- **Products render workflow status uniformly.** Dashboards, CLI summaries, and queries all use the same vocabulary.
- **`partial` distinguishes "human-in-loop pause" from "system failure".** Without it, products would conflate the two or invent their own state.
- **`aborted` enables janitor recovery.** A startup hook (or periodic job) can scan for zombie `running` rows older than some threshold and mark them `aborted`. This is product-side per ADR-005, but the status value being available is platform-side.
- **No "rolled-back" or "compensated" status.** v0 doesn't support transactional rollback of partial workflows. Artifacts written before failure remain.

## State transitions

```
running → succeeded   (all agents ok)
running → failed      (an agent failed; retries exhausted)
running → partial     (an agent signaled human-in-loop)
running → aborted     (process crash; cleaned up later by janitor)
```

No other transitions are valid. A `succeeded` workflow stays `succeeded`. Re-running a workflow with the same input creates a **new** `WorkflowRun` row; old rows are immutable like artifacts (consistent with ADR-004).

## Alternatives considered

- **Single failure status (no `partial`/`aborted` distinction).** Rejected: loses information; common queries like "show me runs that need human attention" become impossible.
- **Boolean `completed`.** Rejected: too coarse; doesn't distinguish success from failure.
- **More granular states (`cancelled`, `timed_out`, `errored`).** Rejected: speculative; add only when a real product demands them. `aborted` is the catch-all for "ended without finishing."
