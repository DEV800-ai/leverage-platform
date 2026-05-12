"""AgentRun and WorkflowRun — the platform's audit records."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from leverage_platform.schemas.base import TenantId

type AgentRunStatus = Literal["pending", "running", "succeeded", "failed", "needs_review"]

type WorkflowStatus = Literal["running", "succeeded", "failed", "partial", "aborted"]


class AgentRun(BaseModel):
    """One LLM/agent call. One row per call. Required by every audit path."""

    id: UUID
    tenant_id: TenantId
    workflow_run_id: UUID | None = None
    agent_name: str

    # Prompt traceability (see ADR-003).
    prompt_name: str
    prompt_hash: str  # SHA-256 of the template
    prompt_version: str | None = None
    input_hash: str  # SHA-256 of the canonical-JSON variables
    output_hash: str  # SHA-256 of the validated output JSON

    # Model + parameters (see ADR-007).
    model: str
    model_parameters: dict[str, Any] = Field(default_factory=dict)

    # Cost + latency (cost as Decimal, see ADR-008).
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    latency_ms: int

    # Status (see ADR-009 sibling for the WorkflowRun enum).
    status: AgentRunStatus
    error: str | None = None

    started_at: datetime
    ended_at: datetime | None = None


class WorkflowRun(BaseModel):
    """One workflow invocation. Parent of agent runs."""

    id: UUID
    tenant_id: TenantId
    workflow_name: str
    status: WorkflowStatus
    input_artifact_id: UUID | None = None
    final_artifact_id: UUID | None = None
    started_at: datetime
    ended_at: datetime | None = None
    error: str | None = None
