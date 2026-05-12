# ADR-007 — `LLMParameters` is a typed Pydantic model

**Status:** Accepted (2026-05-12)

## Context

`LLMProvider.generate_text` and `LLMProvider.generate_structured` accept a `parameters` argument controlling LLM behavior: temperature, max_tokens, top_p, stop sequences, plus vendor-specific options. Two approaches were considered:

- **(a)** `parameters: dict | None = None` — flexible, vendor-agnostic, untyped.
- **(b)** `parameters: LLMParameters | None = None` — typed Pydantic model with common fields + a `provider_specific: dict` for the long tail.

## Decision

Option **(b)**.

```python
class LLMParameters(BaseModel):
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    stop_sequences: list[str] | None = None
    provider_specific: dict[str, Any] | None = None
```

## Consequences

- **Reproducibility.** `AgentRun.model_parameters` stores the JSON-serialized `LLMParameters`. With typed fields, the JSON is deterministic. With `dict`, key ordering and type coercion can vary, breaking `model_parameters` comparison across runs.
- **Typo safety.** `temperatue=0.7` (typo) raises a Pydantic validation error. With `dict`, it silently does nothing.
- **Vendor-specific escape hatch.** Options like Anthropic's `tool_choice`, OpenAI's `response_format`, or future providers' params live in `provider_specific`. The platform's typed top-level fields cover the common case; the dict covers the long tail.
- **Promotion path.** When a `provider_specific` field appears in 2+ providers, promote it to a top-level `LLMParameters` field. This is a deliberate, additive evolution; existing callers keep working.
- **The provider abstraction stays clean.** Callers don't need to know which provider they're targeting just to set temperature.

## Alternatives considered

- **`dict`.** Rejected: typos pass silently; reproducibility hashing breaks on key-ordering differences; no IDE autocomplete.
- **One type per provider (`AnthropicParameters`, `OpenAIParameters`).** Rejected: forces callers to know the provider; defeats the abstraction.
- **`Annotated[dict, ...]` with runtime validation.** Rejected: same downsides as plain `dict` plus complexity.

## Hashing detail

`AgentRun.model_parameters` is computed as the JSON-canonicalized form of `LLMParameters.model_dump(mode="json", exclude_none=True)`. Hashed identically to `input_hash` (sorted keys, no whitespace, UTF-8, SHA-256).
