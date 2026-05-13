"""SQLite-backed implementation of the Store protocol.

Sync DB code runs inside `asyncio.to_thread` per ADR-006. All datetimes are
stored as ISO 8601 strings (UTC); UUIDs and Decimals as ASCII text.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from leverage_platform.schemas import (
    AgentRun,
    Artifact,
    CostEntry,
    WorkflowRun,
)
from leverage_platform.schemas.base import TenantId
from leverage_platform.storage.migrations import MIGRATIONS

# Field whitelists for partial updates — guards against arbitrary column names.
_AGENT_RUN_UPDATABLE = frozenset(
    {
        "status",
        "error",
        "ended_at",
        "input_tokens",
        "output_tokens",
        "cost_usd",
        "latency_ms",
        "prompt_hash",
        "prompt_version",
        "input_hash",
        "output_hash",
        "model",
        "model_parameters",
    }
)
_WORKFLOW_RUN_UPDATABLE = frozenset(
    {
        "status",
        "ended_at",
        "error",
        "input_artifact_id",
        "final_artifact_id",
    }
)


class SQLiteStore:
    """SQLite Store. Pass `:memory:` for tests; a file path for everything else."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._conn = sqlite3.connect(self._path, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._apply_migrations_sync()

    def close(self) -> None:
        self._conn.close()

    # ---------- migrations ----------

    def _apply_migrations_sync(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS _migrations ("
            "version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        cur.execute("SELECT version FROM _migrations")
        applied = {row[0] for row in cur.fetchall()}
        for version, sql in MIGRATIONS:
            if version in applied:
                continue
            cur.executescript(sql)
            cur.execute(
                "INSERT INTO _migrations (version, applied_at) VALUES (?, ?)",
                (version, datetime.now(UTC).isoformat()),
            )

    # ---------- AgentRun ----------

    async def insert_agent_run(self, row: AgentRun) -> None:
        await asyncio.to_thread(self._insert_agent_run_sync, row)

    def _insert_agent_run_sync(self, row: AgentRun) -> None:
        self._conn.execute(
            """
            INSERT INTO agent_run (
                id, tenant_id, workflow_run_id, agent_name,
                prompt_name, prompt_hash, prompt_version,
                input_hash, output_hash,
                model, model_parameters,
                input_tokens, output_tokens, cost_usd, latency_ms,
                status, error, started_at, ended_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(row.id),
                row.tenant_id,
                str(row.workflow_run_id) if row.workflow_run_id else None,
                row.agent_name,
                row.prompt_name,
                row.prompt_hash,
                row.prompt_version,
                row.input_hash,
                row.output_hash,
                row.model,
                json.dumps(row.model_parameters, sort_keys=True, separators=(",", ":")),
                row.input_tokens,
                row.output_tokens,
                str(row.cost_usd),
                row.latency_ms,
                row.status,
                row.error,
                row.started_at.isoformat(),
                row.ended_at.isoformat() if row.ended_at else None,
            ),
        )

    async def update_agent_run(self, run_id: UUID, **fields: Any) -> None:
        await asyncio.to_thread(self._update_agent_run_sync, run_id, fields)

    def _update_agent_run_sync(self, run_id: UUID, fields: dict[str, Any]) -> None:
        bad = set(fields) - _AGENT_RUN_UPDATABLE
        if bad:
            raise ValueError(f"non-updatable agent_run fields: {sorted(bad)}")
        if not fields:
            return
        sets: list[str] = []
        values: list[Any] = []
        for k, v in fields.items():
            sets.append(f"{k} = ?")
            values.append(_serialize(v))
        values.append(str(run_id))
        self._conn.execute(
            f"UPDATE agent_run SET {', '.join(sets)} WHERE id = ?",
            values,
        )

    async def get_agent_run(self, run_id: UUID) -> AgentRun | None:
        row = await asyncio.to_thread(self._get_agent_run_sync, run_id)
        return row

    def _get_agent_run_sync(self, run_id: UUID) -> AgentRun | None:
        cur = self._conn.execute("SELECT * FROM agent_run WHERE id = ?", (str(run_id),))
        r = cur.fetchone()
        if r is None:
            return None
        return AgentRun(
            id=UUID(r["id"]),
            tenant_id=r["tenant_id"],
            workflow_run_id=UUID(r["workflow_run_id"]) if r["workflow_run_id"] else None,
            agent_name=r["agent_name"],
            prompt_name=r["prompt_name"],
            prompt_hash=r["prompt_hash"],
            prompt_version=r["prompt_version"],
            input_hash=r["input_hash"],
            output_hash=r["output_hash"],
            model=r["model"],
            model_parameters=json.loads(r["model_parameters"]),
            input_tokens=r["input_tokens"],
            output_tokens=r["output_tokens"],
            cost_usd=Decimal(r["cost_usd"]),
            latency_ms=r["latency_ms"],
            status=r["status"],
            error=r["error"],
            started_at=datetime.fromisoformat(r["started_at"]),
            ended_at=datetime.fromisoformat(r["ended_at"]) if r["ended_at"] else None,
        )

    # ---------- WorkflowRun ----------

    async def insert_workflow_run(self, row: WorkflowRun) -> None:
        await asyncio.to_thread(self._insert_workflow_run_sync, row)

    def _insert_workflow_run_sync(self, row: WorkflowRun) -> None:
        self._conn.execute(
            """
            INSERT INTO workflow_run (
                id, tenant_id, workflow_name, status,
                input_artifact_id, final_artifact_id,
                started_at, ended_at, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(row.id),
                row.tenant_id,
                row.workflow_name,
                row.status,
                str(row.input_artifact_id) if row.input_artifact_id else None,
                str(row.final_artifact_id) if row.final_artifact_id else None,
                row.started_at.isoformat(),
                row.ended_at.isoformat() if row.ended_at else None,
                row.error,
            ),
        )

    async def update_workflow_run(self, run_id: UUID, **fields: Any) -> None:
        await asyncio.to_thread(self._update_workflow_run_sync, run_id, fields)

    def _update_workflow_run_sync(self, run_id: UUID, fields: dict[str, Any]) -> None:
        bad = set(fields) - _WORKFLOW_RUN_UPDATABLE
        if bad:
            raise ValueError(f"non-updatable workflow_run fields: {sorted(bad)}")
        if not fields:
            return
        sets: list[str] = []
        values: list[Any] = []
        for k, v in fields.items():
            sets.append(f"{k} = ?")
            values.append(_serialize(v))
        values.append(str(run_id))
        self._conn.execute(
            f"UPDATE workflow_run SET {', '.join(sets)} WHERE id = ?",
            values,
        )

    async def get_workflow_run(self, run_id: UUID) -> WorkflowRun | None:
        return await asyncio.to_thread(self._get_workflow_run_sync, run_id)

    def _get_workflow_run_sync(self, run_id: UUID) -> WorkflowRun | None:
        cur = self._conn.execute("SELECT * FROM workflow_run WHERE id = ?", (str(run_id),))
        r = cur.fetchone()
        if r is None:
            return None
        return WorkflowRun(
            id=UUID(r["id"]),
            tenant_id=r["tenant_id"],
            workflow_name=r["workflow_name"],
            status=r["status"],
            input_artifact_id=UUID(r["input_artifact_id"]) if r["input_artifact_id"] else None,
            final_artifact_id=UUID(r["final_artifact_id"]) if r["final_artifact_id"] else None,
            started_at=datetime.fromisoformat(r["started_at"]),
            ended_at=datetime.fromisoformat(r["ended_at"]) if r["ended_at"] else None,
            error=r["error"],
        )

    # ---------- Artifact ----------

    async def insert_artifact(self, row: Artifact) -> None:
        await asyncio.to_thread(self._insert_artifact_sync, row)

    def _insert_artifact_sync(self, row: Artifact) -> None:
        self._conn.execute(
            """
            INSERT INTO artifact (
                id, tenant_id, workflow_run_id, created_by_agent_run_id,
                type, schema_name, data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(row.id),
                row.tenant_id,
                str(row.workflow_run_id),
                str(row.created_by_agent_run_id) if row.created_by_agent_run_id else None,
                row.type,
                row.schema_name,
                json.dumps(row.data, sort_keys=True, separators=(",", ":")),
                row.created_at.isoformat(),
            ),
        )

    async def get_artifact(self, artifact_id: UUID) -> Artifact | None:
        return await asyncio.to_thread(self._get_artifact_sync, artifact_id)

    def _get_artifact_sync(self, artifact_id: UUID) -> Artifact | None:
        cur = self._conn.execute("SELECT * FROM artifact WHERE id = ?", (str(artifact_id),))
        r = cur.fetchone()
        if r is None:
            return None
        return Artifact(
            id=UUID(r["id"]),
            tenant_id=r["tenant_id"],
            workflow_run_id=UUID(r["workflow_run_id"]),
            created_by_agent_run_id=(
                UUID(r["created_by_agent_run_id"]) if r["created_by_agent_run_id"] else None
            ),
            type=r["type"],
            schema_name=r["schema_name"],
            data=json.loads(r["data"]),
            created_at=datetime.fromisoformat(r["created_at"]),
        )

    # ---------- Cost ledger ----------

    async def query_cost(
        self,
        tenant_id: TenantId,
        *,
        since: datetime,
        until: datetime | None = None,
        group_by_workflow: bool = False,
        group_by_agent: bool = False,
    ) -> list[CostEntry]:
        return await asyncio.to_thread(
            self._query_cost_sync, tenant_id, since, until, group_by_workflow, group_by_agent
        )

    def _query_cost_sync(
        self,
        tenant_id: TenantId,
        since: datetime,
        until: datetime | None,
        group_by_workflow: bool,
        group_by_agent: bool,
    ) -> list[CostEntry]:
        # SQLite TEXT-stored Decimals don't aggregate cleanly via SUM; do the
        # math in Python with Decimal to honor ADR-008.
        select_cols = ["agent_run.tenant_id", "agent_run.cost_usd", "agent_run.agent_name"]
        if group_by_workflow:
            select_cols.append("workflow_run.workflow_name")
        until_clause = " AND agent_run.started_at <= ?" if until else ""

        sql = (
            f"SELECT {', '.join(select_cols)}"
            " FROM agent_run"
            " LEFT JOIN workflow_run ON workflow_run.id = agent_run.workflow_run_id"
            " WHERE agent_run.tenant_id = ?"
            " AND agent_run.started_at >= ?"
            f"{until_clause}"
        )
        params: list[Any] = [tenant_id, since.isoformat()]
        if until:
            params.append(until.isoformat())

        cur = self._conn.execute(sql, params)
        rows = cur.fetchall()

        buckets: dict[tuple[str | None, str | None], dict[str, Any]] = {}
        for r in rows:
            wf_name = r["workflow_name"] if group_by_workflow else None
            agent_name = r["agent_name"] if group_by_agent else None
            key = (wf_name, agent_name)
            bucket = buckets.setdefault(
                key,
                {
                    "cost": Decimal("0"),
                    "count": 0,
                    "workflow_name": wf_name,
                    "agent_name": agent_name,
                },
            )
            bucket["cost"] += Decimal(r["cost_usd"])
            bucket["count"] += 1

        end = until or datetime.now(UTC)
        return [
            CostEntry(
                tenant_id=tenant_id,
                period_start=since,
                period_end=end,
                workflow_name=b["workflow_name"],
                agent_name=b["agent_name"],
                cost_usd=b["cost"],
                call_count=b["count"],
            )
            for b in buckets.values()
        ]


def _serialize(value: Any) -> Any:
    """Coerce common Python types into SQLite-friendly storage values."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value
