"""CostEntry — one row of the cost ledger view (derived from AgentRun)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from leverage_platform.schemas.base import TenantId


class CostEntry(BaseModel):
    """A bucket of accumulated LLM cost.

    Cost ledger is a derived view over AgentRun (see ADR-008). This schema
    describes the shape of a single grouped row — by tenant, time bucket,
    and optionally by workflow or agent.
    """

    tenant_id: TenantId
    period_start: datetime
    period_end: datetime
    workflow_name: str | None = None
    agent_name: str | None = None
    cost_usd: Decimal
    call_count: int
