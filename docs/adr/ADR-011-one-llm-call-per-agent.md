# ADR-011 — One LLM call per `@agent` function (fail-fast enforced)

**Status:** Accepted (2026-05-14)

## Context

Every `AgentRun` row is 1:1 with one `@agent` invocation. The row records exactly one `prompt_hash`, one `input_hash`, one `model`, one `cost_usd`, one `latency_ms`. This 1:1 invariant underlies cost attribution, audit reproducibility, and the SQLite schema.

Before this ADR, the runtime did not enforce the corresponding rule on the agent body. If an agent called `ctx.invoke_llm()` twice, the second call silently overwrote `ctx.last_llm_call`, and the `@agent` wrapper read only the last metadata. The first call's tokens, cost, prompt_hash, and latency were silently dropped from audit. Cost was undercounted by exactly one call per offending agent run; debugging "which prompt produced this output?" became impossible.

Three options:

- **(a)** Allow multiple calls; record only the last. (Accidental pre-ADR behaviour.)
- **(b)** Allow multiple calls; record all of them — one `AgentRun` row per LLM call. Requires breaking the 1:1 invariant.
- **(c)** Forbid multiple calls; fail fast.

## Decision

Option **(c)**. One `@agent` function makes **at most one** LLM call via `ctx.invoke_llm`.

Enforced in `AgentContext.invoke_llm`: if `self.last_llm_call is not None`, raise `RuntimeError` with a message naming the previous and new `prompt_name`. The wrapping `@agent` decorator catches the raise, marks the `AgentRun` row `status="failed"`, and re-raises.

Agents that intentionally make no LLM call must use `@agent(pure=True)`. Pure agents get an `AgentRun` row with sentinel values (`model="(none)"`, `cost_usd=0`, `prompt_hash="pure:no-llm-call"`, `input_hash` derived from the agent's arguments). Pure agents may still delegate work to nested `@agent` calls — each nested call produces its own `AgentRun`.

To make nested calls work, the `@agent` decorator saves `ctx.last_llm_call` at entry, clears it to `None` for the body, and restores the prior value after. Without this, an outer agent's LLM metadata would bleed into the inner agent's row (or vice versa). This pattern was added in Phase 3 after the proof scenario's Critic-with-`llm_judge` exposed it as a real bug.

```python
async def invoke_llm(self, ...) -> StructuredResult[T]:
    if self.last_llm_call is not None:
        raise RuntimeError(
            "ctx.invoke_llm called more than once during a single @agent run "
            "(previous: prompt_name={prev!r}, new: prompt_name={new!r}). "
            "Split the second call into its own @agent, or set pure=True."
        )
    ...
```

## Consequences

- **Audit correctness.** Every `AgentRun` row's `prompt_hash`, `input_hash`, and cost reflect a real, single LLM call. No silent undercount.
- **Cost correctness.** Per-tenant / per-workflow / per-agent cost sums are exact. The cost ledger is trustworthy by construction, not by convention.
- **Forces clean decomposition.** "Two LLM calls means two agents" becomes a structural rule, not a stylistic preference. Agents stay small and inspectable.
- **`pure=True` escape hatch.** Orchestrator-style steps (rule-evals, conditional delegation, aggregation, the Critic pattern) get an `AgentRun` row without being forced to invent a sham LLM call.
- **Nested agents are safe.** Save+restore in the wrapper keeps each agent's metadata local to its own scope.
- **Clear failure mode.** A second call gets a fast, named error pointing at the previous `prompt_name`, not a corrupted row that surfaces hours later in a cost query.

## Alternatives considered

- **Multi-call `AgentRun`** (one row, list of LLM calls). Rejected: breaks the 1:1 invariant; complicates SQLite schema (a new `agent_run_llm_call` child table); breaks every existing query and the cost ledger projection.
- **One row per LLM call** (relax the `@agent` boundary so an agent IS its LLM calls). Rejected: makes "agent" a fuzzy concept; complicates retry semantics (do we retry the agent or just the failed call?); the mental model that "agent = unit of audit + retry + artifact" is load-bearing for the rest of the platform.
- **Warn-only.** Rejected: the silent-overwrite behaviour is what we already had; a log warning is too easy to ignore, and audit correctness is non-negotiable for a platform whose value proposition includes "every LLM call is traceable."

## Note on the asymmetric constraint

The rule is **at most one** call, but a non-`pure` agent that returns without calling `invoke_llm` at all is also treated as a bug — see the existing failure path in `runtime/agent.py` ("agent did not call ctx.invoke_llm; cannot audit"). Combined: non-pure agents must call `invoke_llm` exactly once; pure agents must not call it at all. The choice between them is explicit at the decorator.

## Related

- ADR-003 (`prompt_hash` = template, `input_hash` = vars): the metadata fields whose 1:1 mapping with `AgentRun` this ADR protects.
- ADR-010 (`AgentContext` first-arg): the mechanism `last_llm_call` lives on.
