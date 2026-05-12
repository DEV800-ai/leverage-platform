# ADR-001 — Tenant isolation is product-side

**Status:** Accepted (2026-05-12)

## Context

The platform supports multi-tenant audit/cost attribution via a `tenant_id` field carried on every `AgentRun`, `WorkflowRun`, `Artifact`, and `CostEntry`. The question: does the platform **enforce** row-level isolation (tenant A cannot read tenant B's rows) or just **attribute** rows to tenants?

## Decision

The platform **attributes only**. It does not enforce row-level isolation.

- Storage writes accept and require `tenant_id`.
- Storage reads return whatever the query asks for. The platform does not auto-filter by `tenant_id`.
- Products are responsible for filtering by `tenant_id` in their queries.

## Consequences

- Cross-tenant data leakage in a product is a **product bug**, not a platform bug.
- The platform surface stays small. No row-level security policy layer, no policy DSL, no test-overhead from enforcing rules nobody asked for.
- Products may legitimately want cross-tenant reads (admin views, aggregate analytics). Auto-filtering would force every such use case to opt out.
- If a future product demands enforced isolation, the path forward is a `tenant_scoped_store` wrapper that auto-filters — additive, opt-in, no breaking change.

## Alternatives considered

- **Enforced isolation at storage layer.** Rejected: doubles API surface; defeats legitimate cross-tenant queries.
- **Multi-database-per-tenant.** Rejected: ops overhead not justifiable for v0.
- **Row-level-security policies (Postgres RLS).** Rejected: SQLite doesn't support it; introducing a Postgres-only feature breaks the storage-portability rule (ADR-002).
