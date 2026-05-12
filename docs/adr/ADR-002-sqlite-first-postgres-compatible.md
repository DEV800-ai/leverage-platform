# ADR-002 — SQLite-first storage; Postgres-compatible schema design

**Status:** Accepted (2026-05-12)

## Context

Audit/transactional storage is needed for `agent_run`, `workflow_run`, `artifact`, and `cost_ledger`. Options considered: DuckDB, SQLite, Postgres, or a combination.

## Decision

v0 implements **only** `storage/sqlite.py`. The schema is designed to be Postgres-portable so a `postgres.py` adapter can be added later without breaking changes. A Postgres adapter is **explicitly NOT** built in v0.

### Schema-portability rules

| Concept | SQLite (v0) | Postgres (future) |
| --- | --- | --- |
| UUID | `TEXT` storing canonical 36-char UUID | `UUID` |
| JSON blob | `TEXT` storing JSON | `JSONB` |
| Datetime | `TEXT` storing ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SS.ffffffZ`) | `TIMESTAMPTZ` |
| Decimal money | `TEXT` storing decimal string (see ADR-008) | `NUMERIC(12, 6)` |
| String | `TEXT` (never `VARCHAR(n)`) | `TEXT` |
| Boolean | `INTEGER` 0/1 | `BOOLEAN` |
| Foreign keys | `PRAGMA foreign_keys = ON` | always on |
| Concurrency | WAL mode | n/a |

### SQLite-specific bootstrap

- WAL mode enabled on connection: `PRAGMA journal_mode = WAL`.
- `PRAGMA foreign_keys = ON` on every connection.
- Embedded migrations as a list of SQL strings, applied in order; tracked in a `_migrations(version, applied_at)` table.

## Consequences

- Local dev requires zero setup; SQLite is a file on disk.
- DuckDB rejected as primary audit store: it is columnar/analytic, optimized for read-heavy workloads. Audit is row-by-row write-heavy. Wrong tool.
- A future product needing Postgres adds `storage/postgres.py` mirroring the SQLite adapter; schemas port cleanly because column types are constrained.
- DuckDB *can* still be used later as an analytics export target (read-only mirror of audit tables) — but never as primary write store.
- Maintenance cost is one adapter, not two.

## Alternatives considered

- **Implement Postgres adapter in v0.** Rejected: no consumer yet; two adapters double bug surface and double tests.
- **DuckDB as audit store.** Rejected: wrong tool for transactional row-level writes.
- **In-memory only.** Rejected: defeats the audit purpose; loses state on process exit.
