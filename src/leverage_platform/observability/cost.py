"""Cost ledger formatting + time-window parsing — pure functions, no IO.

The CLI wrapper in `leverage_platform.cli` constructs the SQLiteStore,
calls `store.query_cost(...)`, and renders the returned entries with the
helpers here. Keeping these pure makes them trivial to unit-test.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from leverage_platform.schemas import CostEntry

_DURATION_RE = re.compile(r"^(\d+)([hdw])$")


def parse_since(value: str) -> datetime:
    """Parse '7d', '24h', '4w', or an ISO datetime → timezone-aware UTC datetime.

    Raises argparse.ArgumentTypeError on unrecognised input so it composes
    cleanly with argparse's error path.
    """
    m = _DURATION_RE.match(value)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        delta = {
            "h": timedelta(hours=n),
            "d": timedelta(days=n),
            "w": timedelta(weeks=n),
        }[unit]
        return datetime.now(UTC) - delta
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid time value {value!r}; use '7d' / '24h' / '4w' or an ISO datetime"
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def format_json(entries: list[CostEntry]) -> str:
    """JSON-array rendering of CostEntry rows; Decimal cost serialised as string."""
    return json.dumps([e.model_dump(mode="json") for e in entries], indent=2)


def format_table(entries: list[CostEntry]) -> str:
    """Aligned-column table with a TOTAL row. Columns adapt to grouping.

    `workflow` column is included only if any entry has workflow_name set;
    `agent` column only if any entry has agent_name set. This keeps the
    no-group output narrow and the grouped output legible.
    """
    if not entries:
        return "No cost entries in range."

    has_workflow = any(e.workflow_name is not None for e in entries)
    has_agent = any(e.agent_name is not None for e in entries)

    headers = ["tenant"]
    if has_workflow:
        headers.append("workflow")
    if has_agent:
        headers.append("agent")
    headers.extend(["cost (USD)", "calls"])

    def _row_for(e: CostEntry) -> list[str]:
        row = [e.tenant_id]
        if has_workflow:
            row.append(e.workflow_name or "—")
        if has_agent:
            row.append(e.agent_name or "—")
        row.append(f"{e.cost_usd:.6f}")
        row.append(str(e.call_count))
        return row

    body = [_row_for(e) for e in entries]
    total_cost = sum((e.cost_usd for e in entries), Decimal("0"))
    total_calls = sum(e.call_count for e in entries)

    total_row = ["TOTAL"]
    if has_workflow:
        total_row.append("")
    if has_agent:
        total_row.append("")
    total_row.append(f"{total_cost:.6f}")
    total_row.append(str(total_calls))

    all_rows = [headers, *body, total_row]
    widths = [max(len(r[i]) for r in all_rows) for i in range(len(headers))]
    n_cols = len(headers)

    def fmt(r: list[str]) -> str:
        cells: list[str] = []
        for i, c in enumerate(r):
            if i < n_cols - 2:
                cells.append(c.ljust(widths[i]))
            else:
                cells.append(c.rjust(widths[i]))
        return "  ".join(cells)

    sep = "  ".join("-" * w for w in widths)
    lines = [fmt(headers), sep]
    lines.extend(fmt(r) for r in body)
    lines.append(sep)
    lines.append(fmt(total_row))
    return "\n".join(lines)
