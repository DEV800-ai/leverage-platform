# ADR-006 — Async-first runtime; SQLite via `asyncio.to_thread`

**Status:** Accepted (2026-05-12)

## Context

The platform exposes async APIs (`async def` everywhere) to support FastAPI / async product shapes. SQLite's stdlib driver (`sqlite3`) is synchronous; calling it from an async context blocks the event loop. Three options were considered:

- **(a)** Add `aiosqlite` dependency (async wrapper around stdlib).
- **(b)** Wrap stdlib `sqlite3` calls in `asyncio.to_thread(...)`.
- **(c)** Accept the blocking (SQLite writes are typically <1ms).

## Decision

Option **(b)**. The platform uses stdlib `sqlite3` wrapped in `asyncio.to_thread`. No `aiosqlite` dependency.

A sync helper `run_sync(workflow, ctx, input_data)` exists for CLI / script callers (internally `asyncio.run(...)`).

## Consequences

- **No extra dependency.** Stdlib only.
- **`to_thread` overhead** is dominated by the LLM call time (~1–10s per call); the wrapper adds microseconds, not milliseconds.
- **Behind a clean boundary.** All sync DB access lives inside `storage/sqlite.py`; callers see only `async def` methods on the `Store` protocol. Swapping to `aiosqlite` later is a one-file change.
- **FastAPI compatibility preserved.** Event loop isn't blocked by `to_thread` (it suspends the coroutine and resumes after the thread returns).
- Option (c) rejected: FastAPI under load with even 1ms event-loop blocks per request degrades p99 noticeably. Not worth saving.

## Alternatives considered

- **`aiosqlite`.** Rejected: extra dep with marginal benefit at v0 scale. Reconsider if profiling shows `to_thread` overhead matters.
- **Synchronous platform.** Rejected: rules out async product shapes (FastAPI is the most likely first consumer).
- **Anyio (sync/async dual API).** Rejected: too much abstraction for v0; commit to one runtime model.

## Implementation note

Code pattern inside `storage/sqlite.py`:

```python
import asyncio
import sqlite3

class SQLiteStore:
    async def insert_agent_run(self, row: AgentRun) -> None:
        await asyncio.to_thread(self._insert_agent_run_sync, row)

    def _insert_agent_run_sync(self, row: AgentRun) -> None:
        with self._conn as conn:
            conn.execute(...)
```

The sync method is private (`_*_sync` convention). External callers always go through the async API.
