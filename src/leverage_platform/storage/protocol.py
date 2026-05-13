"""Storage protocol — what every backend (SQLite v0, Postgres future) must implement."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from leverage_platform.schemas import (
    AgentRun,
    Artifact,
    CostEntry,
    WorkflowRun,
)
from leverage_platform.schemas.base import TenantId


@runtime_checkable
class Store(Protocol):
    """Async storage interface for audit + artifact persistence.

    All methods are async. SQLite-backed implementations use `asyncio.to_thread`
    (ADR-006). Postgres backends will be native-async.

    Tenant isolation: callers pass `tenant_id` on writes; the store records it
    faithfully but does NOT auto-filter reads (ADR-001 — products own isolation).
    """

    # --- AgentRun ---

    async def insert_agent_run(self, row: AgentRun) -> None:
        """Insert a new AgentRun row. Idempotent on (id) — raises on duplicate id."""
        ...

    async def update_agent_run(self, run_id: UUID, **fields: object) -> None:
        """Update mutable fields on an AgentRun row. Status/cost/tokens/timestamps/etc."""
        ...

    async def get_agent_run(self, run_id: UUID) -> AgentRun | None:
        ...

    # --- WorkflowRun ---

    async def insert_workflow_run(self, row: WorkflowRun) -> None:
        ...

    async def update_workflow_run(self, run_id: UUID, **fields: object) -> None:
        ...

    async def get_workflow_run(self, run_id: UUID) -> WorkflowRun | None:
        ...

    # --- Artifact (immutable per ADR-004) ---

    async def insert_artifact(self, row: Artifact) -> None:
        ...

    async def get_artifact(self, artifact_id: UUID) -> Artifact | None:
        ...

    # --- Cost ledger (derived view) ---

    async def query_cost(
        self,
        tenant_id: TenantId,
        *,
        since: datetime,
        until: datetime | None = None,
        group_by_workflow: bool = False,
        group_by_agent: bool = False,
    ) -> list[CostEntry]:
        ...
