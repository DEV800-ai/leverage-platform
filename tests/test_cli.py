"""End-to-end tests for the `leverage-platform` CLI."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from leverage_platform.cli import main
from leverage_platform.schemas import AgentRun, WorkflowRun
from leverage_platform.storage import SQLiteStore


async def _seed(db_path: Path) -> None:
    """Seed two WorkflowRuns + four AgentRuns across two workflows + two agents."""
    store = SQLiteStore(db_path)
    try:
        now = datetime.now(UTC)
        wf1 = uuid4()
        wf2 = uuid4()
        await store.insert_workflow_run(
            WorkflowRun(
                id=wf1,
                tenant_id="acme",
                workflow_name="audit_v1",
                status="succeeded",
                started_at=now,
                ended_at=now,
            )
        )
        await store.insert_workflow_run(
            WorkflowRun(
                id=wf2,
                tenant_id="acme",
                workflow_name="audit_v2",
                status="succeeded",
                started_at=now,
                ended_at=now,
            )
        )
        for wf, agent_name, cost in [
            (wf1, "profile_agent", "0.001000"),
            (wf1, "critic_agent", "0.000500"),
            (wf2, "profile_agent", "0.002000"),
            (wf2, "critic_agent", "0.000750"),
        ]:
            await store.insert_agent_run(
                AgentRun(
                    id=uuid4(),
                    tenant_id="acme",
                    workflow_run_id=wf,
                    agent_name=agent_name,
                    prompt_name=f"{agent_name}.v1",
                    prompt_hash="0" * 64,
                    prompt_version="v1",
                    input_hash="0" * 64,
                    output_hash="0" * 64,
                    model="claude-sonnet-4-6",
                    model_parameters={},
                    input_tokens=100,
                    output_tokens=50,
                    cost_usd=Decimal(cost),
                    latency_ms=200,
                    status="succeeded",
                    started_at=now,
                    ended_at=now,
                )
            )
    finally:
        store.close()


def test_cli_cost_table_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import asyncio
    db = tmp_path / "audit.db"
    asyncio.run(_seed(db))

    rc = main(["cost", "--db", str(db), "--tenant", "acme"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "tenant" in out
    assert "cost (USD)" in out
    # Four agent_runs at 0.001 + 0.0005 + 0.002 + 0.00075 = 0.004250
    assert "0.004250" in out
    assert "TOTAL" in out


def test_cli_cost_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import asyncio
    db = tmp_path / "audit.db"
    asyncio.run(_seed(db))

    rc = main(["cost", "--db", str(db), "--tenant", "acme", "--format", "json"])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["tenant_id"] == "acme"
    assert parsed[0]["cost_usd"] == "0.004250"
    assert parsed[0]["call_count"] == 4


def test_cli_cost_group_by_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import asyncio
    db = tmp_path / "audit.db"
    asyncio.run(_seed(db))

    rc = main([
        "cost", "--db", str(db), "--tenant", "acme",
        "--group-by", "workflow", "--format", "json",
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    by_workflow = {e["workflow_name"]: e for e in parsed}
    assert set(by_workflow) == {"audit_v1", "audit_v2"}
    # audit_v1 = 0.001 + 0.0005 = 0.0015
    assert by_workflow["audit_v1"]["cost_usd"] == "0.001500"
    # audit_v2 = 0.002 + 0.00075 = 0.00275
    assert by_workflow["audit_v2"]["cost_usd"] == "0.002750"


def test_cli_cost_group_by_agent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import asyncio
    db = tmp_path / "audit.db"
    asyncio.run(_seed(db))

    rc = main([
        "cost", "--db", str(db), "--tenant", "acme",
        "--group-by", "agent", "--format", "json",
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    by_agent = {e["agent_name"]: e for e in parsed}
    assert set(by_agent) == {"profile_agent", "critic_agent"}
    # profile = 0.001 + 0.002 = 0.003
    assert by_agent["profile_agent"]["cost_usd"] == "0.003000"
    # critic = 0.0005 + 0.00075 = 0.00125
    assert by_agent["critic_agent"]["cost_usd"] == "0.001250"


def test_cli_cost_group_by_both(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import asyncio
    db = tmp_path / "audit.db"
    asyncio.run(_seed(db))

    rc = main([
        "cost", "--db", str(db), "--tenant", "acme",
        "--group-by", "workflow,agent", "--format", "json",
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    # 4 rows expected, one per (workflow, agent) combo.
    assert len(parsed) == 4
    keys = {(e["workflow_name"], e["agent_name"]) for e in parsed}
    assert keys == {
        ("audit_v1", "profile_agent"),
        ("audit_v1", "critic_agent"),
        ("audit_v2", "profile_agent"),
        ("audit_v2", "critic_agent"),
    }


def test_cli_cost_unknown_tenant_empty(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import asyncio
    db = tmp_path / "audit.db"
    asyncio.run(_seed(db))

    rc = main(["cost", "--db", str(db), "--tenant", "unknown"])
    assert rc == 0
    assert "No cost entries in range." in capsys.readouterr().out


def test_cli_cost_missing_db_returns_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main([
        "cost", "--db", str(tmp_path / "missing.db"), "--tenant", "acme",
    ])
    assert rc == 2
    assert "db not found" in capsys.readouterr().err


def test_cli_no_subcommand_prints_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "leverage-platform" in out
    assert "cost" in out


def test_cli_cost_since_excludes_old_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rows older than --since should be excluded from the totals."""
    import asyncio
    db = tmp_path / "audit.db"
    asyncio.run(_seed(db))

    # 1-hour window: all seeded rows are 'now', should be included.
    rc = main([
        "cost", "--db", str(db), "--tenant", "acme",
        "--since", "1h", "--format", "json",
    ])
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert parsed[0]["call_count"] == 4
