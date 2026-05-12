# ADR-010 — `workflow_run_id` propagates via `AgentContext` first-arg

**Status:** Accepted (2026-05-12)

## Context

Every `AgentRun` carries `workflow_run_id` linking it to its parent workflow. Every `AgentRun` also carries `tenant_id`. The mechanism by which these (and other runtime concerns: `provider`, `store`) flow into nested `@agent` calls needs an explicit decision. Three options were considered:

- **(a)** Thread `tenant_id`, `workflow_run_id`, `provider`, `store` through every agent function signature explicitly.
- **(b)** Pass an `AgentContext` object as the first arg of every agent; context carries all of the above.
- **(c)** Use `contextvars.ContextVar` set by the workflow primitive; agents read implicitly.

## Decision

Option **(b)**.

```python
class AgentContext(BaseModel):
    tenant_id: str
    workflow_run_id: UUID | None
    provider: LLMProvider          # excluded from JSON serialization
    store: Store                   # excluded from JSON serialization
    # ... whatever the runtime needs to thread through
    model_config = ConfigDict(arbitrary_types_allowed=True)

@agent(name="profile_agent", schema=UserProfile)
async def profile_agent(ctx: AgentContext, raw_intake: dict) -> UserProfile:
    ...
```

The runtime injects `AgentContext` as the first arg when an agent is invoked from within a workflow. Calling agents outside a workflow requires constructing a minimal `AgentContext` explicitly (with `workflow_run_id=None`).

## Consequences

- **Explicit dependency injection.** Agents see exactly what they get; no globals; no surprise.
- **Testable.** Pass a mock `AgentContext` with an in-memory store and a fake provider. No monkey-patching, no test-mode toggles.
- **No `contextvars` magic to debug.** ContextVars cross-task semantics (when async tasks fork) are subtle and a frequent source of bugs.
- **Slightly verbose at call site.** Every agent signature starts with `ctx: AgentContext, ...`. Acceptable cost.
- **Agents callable outside workflows.** Build an `AgentContext` with `workflow_run_id=None`, call the agent directly — the `AgentRun` row is still recorded, just with a `NULL` parent.

## Alternatives considered

- **Per-arg threading.** Rejected: pollutes every signature with `tenant_id, workflow_run_id, provider, store, ...`. Refactoring becomes painful as the platform adds runtime concerns.
- **`contextvars.ContextVar`.** Rejected: implicit; hard to test (forgetting to set/reset across task boundaries leads to silent bugs); surprising behavior when an `asyncio.gather` forks tasks.
- **Class-based agents** (subclass `BaseAgent`, override `run()`). Rejected: heavier syntax for the common case; `@agent` decorator over plain async functions is clearer.

## Note on `provider` and `store` in the context

These are runtime-only fields; they are NOT serialized when `AgentContext` is logged or stored. The `model_config = ConfigDict(arbitrary_types_allowed=True)` lets Pydantic carry them; a custom `model_dump()` (or convention of using `mode="python"` only) keeps them out of any persisted representation.
