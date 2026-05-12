"""Phase 1 smoke tests — confirm the skeleton imports and schemas validate."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4


def test_package_imports() -> None:
    import leverage_platform

    assert leverage_platform.__version__ == "0.0.0"


def test_schemas_construct() -> None:
    """Sanity-check that the platform schemas can be instantiated with valid data."""
    from leverage_platform.schemas import (
        AgentRun,
        Artifact,
        CostEntry,
        EvalCriterion,
        EvalReport,
        Tenant,
        WorkflowRun,
    )

    tenant = Tenant(id="acme")
    assert tenant.id == "acme"

    now = datetime.now(UTC)
    workflow_id = uuid4()

    workflow = WorkflowRun(
        id=workflow_id,
        tenant_id="acme",
        workflow_name="test_workflow",
        status="running",
        started_at=now,
    )
    assert workflow.status == "running"

    agent_run = AgentRun(
        id=uuid4(),
        tenant_id="acme",
        workflow_run_id=workflow_id,
        agent_name="test_agent",
        prompt_name="test_prompt",
        prompt_hash="0" * 64,
        input_hash="0" * 64,
        output_hash="0" * 64,
        model="claude-opus-4-7",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.000123"),
        latency_ms=1234,
        status="succeeded",
        started_at=now,
    )
    assert agent_run.cost_usd == Decimal("0.000123")

    artifact = Artifact(
        id=uuid4(),
        tenant_id="acme",
        workflow_run_id=workflow_id,
        type="user_profile",
        schema_name="UserProfile@v1",
        data={"name": "Alice"},
        created_at=now,
    )
    assert artifact.schema_name == "UserProfile@v1"

    cost = CostEntry(
        tenant_id="acme",
        period_start=now,
        period_end=now,
        cost_usd=Decimal("1.23"),
        call_count=10,
    )
    assert cost.call_count == 10

    report = EvalReport(
        accepted=True,
        criteria=[EvalCriterion(name="has_title", passed=True, reason="title is non-empty")],
        summary="all checks passed",
    )
    assert report.accepted is True
