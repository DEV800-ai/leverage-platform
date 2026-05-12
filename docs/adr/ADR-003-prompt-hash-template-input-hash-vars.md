# ADR-003 — `prompt_hash` = template, `input_hash` = vars

**Status:** Accepted (2026-05-12)

## Context

`AgentRun` records `prompt_hash` and `input_hash` for auditability and reproducibility. The semantics of `prompt_hash` are ambiguous without an explicit decision. Two interpretations:

- **(a)** `prompt_hash` = hash of the *rendered* prompt (template after variable substitution).
- **(b)** `prompt_hash` = hash of the *template only* (before substitution); `input_hash` = hash of the variables.

## Decision

Option **(b)**.

- `prompt_hash` = SHA-256 of the prompt template's UTF-8 bytes, before variable substitution.
- `input_hash` = SHA-256 of the variables passed into the template, in canonical JSON form.

### Hashing details

- Algorithm: **SHA-256**.
- DB storage: full 64-char hex string.
- CLI/log display: first 12 chars (e.g., `7f3a1b2c8e4d`).
- JSON canonicalization for `input_hash`: sorted keys, no whitespace, UTF-8, ensuring deterministic byte representation across Python versions.

## Consequences

- **"Did the template change?"** answerable by comparing `prompt_hash` across runs.
- **"Did the input change?"** answerable by comparing `input_hash`.
- **Reproducing a specific call:** `template[prompt_hash] + vars[input_hash]` → same rendered prompt → same call (within LLM determinism).
- **Drift detection:** a sudden `prompt_hash` change across many runs of the same agent name signals a template edit — worth a code review check.
- Option (a) was rejected because the rendered hash collapses both questions into one and answers neither — every call has different inputs, so the hash differs even when the template is unchanged.

## Alternatives considered

- **Hash rendered prompt only.** Rejected: defeats template-drift tracking; loses the (template, vars) decomposition.
- **Hash both rendered AND template.** Rejected: extra field with no information beyond (template, vars).
- **Don't hash at all; store the full template per run.** Rejected: bloats storage; template is the same across most runs.

## Notes

- `prompt_name` (a human-readable identifier like `profile_agent.v1`) coexists with `prompt_hash`. The name is for humans; the hash is for the auditor.
- Future prompt registry can use `prompt_hash` as the primary key for template lookups.
