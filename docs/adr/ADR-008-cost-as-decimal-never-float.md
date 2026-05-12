# ADR-008 — Cost as `Decimal`, never float

**Status:** Accepted (2026-05-12)

## Context

`AgentRun.cost_usd` stores the cost of a single LLM call. LLM pricing is denominated in fractional cents (current Anthropic pricing: ~$0.000003 per input token, ~$0.000015 per output token). A workflow with 5 agents at ~5K tokens each is ~$0.05 per run; at 10K runs/month, that's $500 per month per tenant.

Naive `float` arithmetic accumulates rounding error: `sum([0.0001] * 10_000_000)` in Python gives `1000.0000000142087`, not `1000.0`. At scale this produces off-by-rounding bugs and reconciliation headaches.

## Decision

Cost fields are `decimal.Decimal` (Python).

### DB storage

- **SQLite:** `TEXT` storing the decimal as ASCII (e.g., `"0.000123"`).
- **Postgres (future):** `NUMERIC(12, 6)`.

### Serialization

- **JSON:** string form (e.g., `"0.000123"`) — preserves precision; never use a JSON number.
- **Display layer:** format with locale-appropriate rounding; never round during arithmetic.

### Pydantic

Pydantic v2's `Decimal` field type handles validation and JSON (de)serialization correctly when configured with `JsonValue` serialization.

## Consequences

- Aggregation queries (`SUM(cost_usd) GROUP BY tenant_id`) work correctly across millions of rows. SQLite's TEXT comparison-ordering for decimal strings works for non-negative aligned-decimal values, but final aggregation should happen in Python with Decimal to avoid SQLite's lexical-only sort.
- **Cost math is always in Decimal.** Never `float(cost_usd)` for arithmetic. The CLI formatter is the only place a Decimal becomes a string for display.
- **Slightly more verbose** at the call site (`Decimal("0.000123")` vs `0.000123`).
- **Type-checker enforced.** A mistake (`cost_usd = 0.5`) fails Pydantic validation at runtime and mypy at static-check time.

## Alternatives considered

- **`float`.** Rejected: accumulating rounding error; off-by-rounding bugs at scale; reconciliation pain.
- **Integer micro-cents** (e.g., `cost_micro_cents: int`). Rejected: requires explicit conversion at every read/write; less readable; doesn't gain anything Decimal doesn't.
- **String-only (no Decimal type).** Rejected: defeats validation; arithmetic requires constant casting.

## Migration note

When/if Postgres is added (ADR-002), the SQLite `TEXT` columns map cleanly to `NUMERIC(12, 6)`. The Decimal API is unchanged on the Python side.
