"""SQLiteStore: round-trip insert/get for all schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from leverage_platform.schemas import AgentRun, Artifact, WorkflowRun
from leverage_platform.storage import SQLiteStore


def _agent_run(workflow_id=None) -> AgentRun:
    return AgentRun(
        id=uuid4(),
        tenant_id="acme",
        workflow_run_id=workflow_id,
        agent_name="test_agent",
        prompt_name="test_agent.v1",
        prompt_hash="a" * 64,
        prompt_version=None,
        input_hash="b" * 64,
        output_hash="c" * 64,
        model="claude-sonnet-4-6",
        model_parameters={"temperature": 0.2},
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.000750"),
        latency_ms=1234,
        status="succeeded",
        error=None,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )


def _workflow_run() -> WorkflowRun:
    return WorkflowRun(
        id=uuid4(),
        tenant_id="acme",
        workflow_name="test_workflow",
        status="running",
        started_at=datetime.now(UTC),
    )


def _artifact(workflow_id, agent_id=None) -> Artifact:
    return Artifact(
        id=uuid4(),
        tenant_id="acme",
        workflow_run_id=workflow_id,
        created_by_agent_run_id=agent_id,
        type="user_profile",
        schema_name="UserProfile@v1",
        data={"name": "alice"},
        created_at=datetime.now(UTC),
    )


async def test_workflow_run_roundtrip(store: SQLiteStore) -> None:
    wf = _workflow_run()
    await store.insert_workflow_run(wf)
    got = await store.get_workflow_run(wf.id)
    assert got is not None
    assert got.id == wf.id
    assert got.workflow_name == "test_workflow"
    assert got.status == "running"


async def test_workflow_run_update(store: SQLiteStore) -> None:
    wf = _workflow_run()
    await store.insert_workflow_run(wf)
    await store.update_workflow_run(wf.id, status="succeeded", ended_at=datetime.now(UTC))
    got = await store.get_workflow_run(wf.id)
    assert got is not None
    assert got.status == "succeeded"
    assert got.ended_at is not None


async def test_agent_run_roundtrip_preserves_decimal_cost(store: SQLiteStore) -> None:
    ar = _agent_run()
    await store.insert_agent_run(ar)
    got = await store.get_agent_run(ar.id)
    assert got is not None
    assert got.cost_usd == Decimal("0.000750")
    assert got.model_parameters == {"temperature": 0.2}


async def test_agent_run_update(store: SQLiteStore) -> None:
    ar = _agent_run()
    ar = ar.model_copy(update={"status": "pending"})
    await store.insert_agent_run(ar)

    await store.update_agent_run(
        ar.id,
        status="succeeded",
        cost_usd=Decimal("0.001234"),
        output_hash="d" * 64,
    )
    got = await store.get_agent_run(ar.id)
    assert got is not None
    assert got.status == "succeeded"
    assert got.cost_usd == Decimal("0.001234")
    assert got.output_hash == "d" * 64


async def test_agent_run_update_rejects_unknown_field(store: SQLiteStore) -> None:
    ar = _agent_run()
    await store.insert_agent_run(ar)
    with pytest.raises(ValueError, match="non-updatable"):
        await store.update_agent_run(ar.id, agent_name="renamed")


async def test_artifact_roundtrip(store: SQLiteStore) -> None:
    wf = _workflow_run()
    await store.insert_workflow_run(wf)
    art = _artifact(workflow_id=wf.id)
    await store.insert_artifact(art)
    got = await store.get_artifact(art.id)
    assert got is not None
    assert got.schema_name == "UserProfile@v1"
    assert got.data == {"name": "alice"}


async def test_cost_query_aggregates_decimal(store: SQLiteStore) -> None:
    wf = _workflow_run()
    await store.insert_workflow_run(wf)
    for _ in range(3):
        await store.insert_agent_run(_agent_run(workflow_id=wf.id))

    entries = await store.query_cost("acme", since=datetime(2020, 1, 1, tzinfo=UTC))
    assert len(entries) == 1
    entry = entries[0]
    assert entry.tenant_id == "acme"
    assert entry.call_count == 3
    # 3 × 0.000750 = 0.002250 exactly, without float drift
    assert entry.cost_usd == Decimal("0.002250")
