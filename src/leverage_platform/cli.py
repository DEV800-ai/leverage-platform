"""leverage-platform CLI entry point.

Currently a single subcommand:

    leverage-platform cost --db PATH --tenant ID [--since 7d] [--until ...]
                           [--group-by workflow|agent|workflow,agent]
                           [--format table|json]

The cost subcommand reads an audit SQLite store and reports tenant-scoped
LLM cost over a time window. Built against `Store.query_cost(...)` so it
honours ADR-008 (cost is Decimal, never float).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from leverage_platform.observability.cost import (
    format_json,
    format_table,
    parse_since,
)
from leverage_platform.storage import SQLiteStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leverage-platform",
        description="Operational CLI for the leverage-platform infrastructure.",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    cost = subparsers.add_parser("cost", help="Query the cost ledger.")
    cost.add_argument("--db", required=True, help="SQLite database path.")
    cost.add_argument("--tenant", required=True, help="Tenant ID to query.")
    cost.add_argument(
        "--since",
        default="7d",
        help="Lookback window. Accepts '7d' / '24h' / '4w' or an ISO datetime. Default: 7d.",
    )
    cost.add_argument(
        "--until",
        default=None,
        help="Upper bound. Same formats as --since. Default: now.",
    )
    cost.add_argument(
        "--group-by",
        default=None,
        choices=["workflow", "agent", "workflow,agent", "agent,workflow"],
        help="Group results by workflow, agent, or both.",
    )
    cost.add_argument(
        "--format",
        default="table",
        choices=["table", "json"],
    )
    return parser


async def _run_cost(args: argparse.Namespace) -> int:
    if not Path(args.db).exists():
        print(f"db not found: {args.db}", file=sys.stderr)
        return 2

    store = SQLiteStore(args.db)
    try:
        gb = args.group_by or ""
        entries = await store.query_cost(
            args.tenant,
            since=parse_since(args.since),
            until=parse_since(args.until) if args.until else None,
            group_by_workflow="workflow" in gb,
            group_by_agent="agent" in gb,
        )
        if args.format == "json":
            print(format_json(entries))
        else:
            print(format_table(entries))
        return 0
    finally:
        store.close()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "cost":
        return asyncio.run(_run_cost(args))

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
