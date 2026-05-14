"""Unit tests for the cost CLI's pure helpers — no IO, no DB."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from leverage_platform.observability.cost import (
    format_json,
    format_table,
    parse_since,
)
from leverage_platform.schemas import CostEntry

NOW = datetime.now(UTC)
PERIOD = (NOW - timedelta(days=7), NOW)


def _entry(
    *,
    tenant: str = "acme",
    workflow: str | None = None,
    agent: str | None = None,
    cost: str = "0.001234",
    calls: int = 1,
) -> CostEntry:
    return CostEntry(
        tenant_id=tenant,
        period_start=PERIOD[0],
        period_end=PERIOD[1],
        workflow_name=workflow,
        agent_name=agent,
        cost_usd=Decimal(cost),
        call_count=calls,
    )


# ---------- parse_since ----------


def test_parse_since_days() -> None:
    before = datetime.now(UTC)
    result = parse_since("7d")
    after = datetime.now(UTC)
    expected_lo = before - timedelta(days=7)
    expected_hi = after - timedelta(days=7)
    assert expected_lo <= result <= expected_hi


def test_parse_since_hours() -> None:
    before = datetime.now(UTC)
    result = parse_since("24h")
    after = datetime.now(UTC)
    assert (before - timedelta(hours=24)) <= result <= (after - timedelta(hours=24))


def test_parse_since_weeks() -> None:
    before = datetime.now(UTC)
    result = parse_since("2w")
    after = datetime.now(UTC)
    assert (before - timedelta(weeks=2)) <= result <= (after - timedelta(weeks=2))


def test_parse_since_iso_with_tz() -> None:
    result = parse_since("2026-01-01T12:00:00+00:00")
    assert result == datetime(2026, 1, 1, 12, tzinfo=UTC)


def test_parse_since_iso_naive_assumed_utc() -> None:
    """Naive ISO datetimes get UTC attached for consistency with the DB convention."""
    result = parse_since("2026-01-01T12:00:00")
    assert result.tzinfo is UTC
    assert result == datetime(2026, 1, 1, 12, tzinfo=UTC)


def test_parse_since_invalid_raises() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="invalid time value"):
        parse_since("yesterday")


def test_parse_since_invalid_unit_raises() -> None:
    """'5m' (minutes) isn't supported; falls through to ISO and fails."""
    with pytest.raises(argparse.ArgumentTypeError):
        parse_since("5m")


# ---------- format_json ----------


def test_format_json_round_trip() -> None:
    entries = [_entry(cost="0.123456", calls=10)]
    out = format_json(entries)
    parsed = json.loads(out)
    assert len(parsed) == 1
    assert parsed[0]["tenant_id"] == "acme"
    assert parsed[0]["cost_usd"] == "0.123456"
    assert parsed[0]["call_count"] == 10


def test_format_json_empty() -> None:
    assert format_json([]) == "[]"


# ---------- format_table ----------


def test_format_table_empty() -> None:
    assert format_table([]) == "No cost entries in range."


def test_format_table_single_entry_no_grouping() -> None:
    out = format_table([_entry(cost="0.5", calls=3)])
    assert "tenant" in out
    assert "cost (USD)" in out
    assert "calls" in out
    assert "acme" in out
    assert "0.500000" in out
    assert "3" in out
    # No workflow/agent column when nothing is grouped.
    assert "workflow" not in out
    assert "agent" not in out
    assert "TOTAL" in out


def test_format_table_grouped_by_workflow() -> None:
    out = format_table([
        _entry(workflow="audit_v1", cost="0.20", calls=2),
        _entry(workflow="audit_v2", cost="0.30", calls=3),
    ])
    assert "workflow" in out
    assert "audit_v1" in out
    assert "audit_v2" in out
    assert "TOTAL" in out
    # Totals = 0.20 + 0.30 = 0.50
    assert "0.500000" in out


def test_format_table_grouped_by_workflow_and_agent() -> None:
    out = format_table([
        _entry(workflow="audit_v1", agent="profile_agent", cost="0.10", calls=1),
        _entry(workflow="audit_v1", agent="critic_agent", cost="0.05", calls=1),
        _entry(workflow="audit_v2", agent="profile_agent", cost="0.15", calls=1),
    ])
    assert "workflow" in out
    assert "agent" in out
    assert "profile_agent" in out
    assert "critic_agent" in out
    # Totals
    assert "0.300000" in out


def test_format_table_em_dash_for_ungrouped_field() -> None:
    """An entry without a grouped value should render '—', not 'None' or empty."""
    out = format_table([
        _entry(workflow="audit_v1", agent="profile_agent", cost="0.01", calls=1),
        _entry(workflow="audit_v1", agent=None, cost="0.02", calls=1),
    ])
    assert "—" in out
