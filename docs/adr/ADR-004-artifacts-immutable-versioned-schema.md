# ADR-004 — Artifacts immutable per workflow run; schema versioning via `schema_name`

**Status:** Accepted (2026-05-12)

## Context

`Artifact` records the typed output of a workflow step. Two questions need locked answers:

1. **Mutability** — Are artifacts mutable (updated in place) or immutable (new rows only)?
2. **Schema evolution** — How does the platform handle a domain schema gaining/losing fields over time?

## Decision

1. **Immutable.** Each workflow run produces new `Artifact` rows. The platform's `Store` never updates an existing artifact's `data` after insertion.
2. **`schema_name` is versioned by convention.** Format: `"<TypeName>@v<N>"`. Example: `"UserProfile@v1"`. When a product evolves a schema, the product bumps the version: `"UserProfile@v2"`. Old artifact rows retain their original `schema_name`.

## Consequences

- Replay is trivial: artifacts at write-time stay that way forever.
- Re-running a workflow on the same input produces new artifacts; old ones are not overwritten. Costs storage; gains a complete audit trail.
- **Schema evolution is the product's problem.** When reading an old artifact with `schema_name="UserProfile@v1"` after the product has moved to v2, the product must either:
  - Migrate the dict (one-off code).
  - Maintain a v1 reader alongside the v2 reader.
  - Accept that the data is opaque for old runs.
- The platform does **not** provide schema migration tooling for artifacts in v0. If a real product asks for it, that's a future primitive.
- Storage estimate: 5 artifacts per workflow run × 1 KB average × 10K runs/year ≈ 50 MB/year. Not a concern at v0 scale.

## Alternatives considered

- **Mutable artifacts.** Rejected: defeats audit; what was the input to step N+1 if the step N artifact was rewritten?
- **Platform-managed schema migrations.** Rejected: couples platform to domain schemas; v0 doesn't have the maturity for this.
- **Unversioned `schema_name` (no `@vN`).** Rejected: schema evolution becomes silent and brittle. The version suffix is cheap insurance.

## Storage hint

`schema_name` should be indexed in the artifact table — products will commonly query `WHERE schema_name LIKE 'UserProfile@%'` to find all versions of a type.
