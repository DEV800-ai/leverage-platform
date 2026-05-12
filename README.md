# leverage-platform

Reusable infrastructure for future AI-native products (SaaS / SMB B2B / B2C).

**Status:** design phase. v0 scope locked. No products attached yet — by design.

See [`PLAN.md`](PLAN.md) for the v0 plan, primitives list, and sequencing.

Original product-design docs (reference only, not the build plan): [`docs/source/`](docs/source/).

## What this is and is not

- **Is**: a Python library of seven primitives every multi-user AI product will need (LLM provider abstraction, agent runtime with audit, tenant identity contract, cost ledger, structured-output validation, workflow primitive, eval primitive).
- **Is not**: a product. No UI, no auth, no payment, no SaaS framing, no agent fleet, no opinion on memory store or vector DB.

The platform is a library. Products will be separate repos that depend on it.

## Hard "no"s

- No frontend / UI / dashboard.
- No primitive added without 2+ plausible product shapes needing it.
- No connection to `signalalpha` or any other existing repo.
- No autonomous agent chains.
- No premature stack expansion.
