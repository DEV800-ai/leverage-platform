"""Artifact — typed output of a workflow step. Immutable per run (see ADR-004)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from leverage_platform.schemas.base import TenantId


class Artifact(BaseModel):
    """A typed output produced by a workflow step.

    Artifacts are immutable: re-running a workflow produces new rows.
    Schema evolution is versioned via the `schema_name` field
    (e.g., "UserProfile@v1"). See ADR-004.
    """

    id: UUID
    tenant_id: TenantId
    workflow_run_id: UUID
    created_by_agent_run_id: UUID | None = None
    type: str  # short kind label, e.g., "user_profile"
    schema_name: str  # versioned, e.g., "UserProfile@v1"
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
