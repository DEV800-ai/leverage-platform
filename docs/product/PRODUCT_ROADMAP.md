# Product Roadmap — AI Leverage Audit

**Status:** Draft v0.1 — 2026-05-14
**Scope:** The sequence between today (V1 spec frozen in [`PRODUCT_MVP.md`](PRODUCT_MVP.md)) and a decision on what V2 should be. Evidence-driven, not date-driven — there are no quarter-target promises in this doc.
**Companion docs:** [`PRODUCT_VISION.md`](PRODUCT_VISION.md) (positioning), [`PRODUCT_MVP.md`](PRODUCT_MVP.md) (V1 spec).

---

## 1. Positioning recap

V1 is one product: an **AI Leverage Audit** for solopreneurs and small business owners. One-shot, CLI + JSON output, runs on top of `leverage-platform`. It produces a Workflow Map, per-workflow Leverage Analysis, a 30-Day Bet, a Risk + Agency Map, and a first Playbook.

This roadmap covers what happens **after** V1 spec is frozen and before V2 is committed to.

---

## 2. Three gates to ship V1

The path from "spec written" to "V1 shipped to friend-and-family" runs through three sequential gates. No skipping.

### Gate 1 — Skeleton runs

**What ships:**

- New repo `ai-leverage-audit` (private, GitHub) forked from a clean template.
- `pyproject.toml` with `leverage-platform` as a local-path dependency.
- CLI entry point (`audit --help`) wired through, even if the only command prints version.
- `tests/test_smoke.py` proves the platform import works from the product side.
- GitHub Actions CI mirrors the platform's: ruff + pytest + uv build.

**Acceptance:** `uv run audit --help` works locally and in CI. No Audit logic yet.

**Why this is a gate:** every later step assumes the product can import the platform cleanly. Catching path / dependency / packaging issues here saves rework. ~1 day.

---

### Gate 2 — One synthetic intake produces an accepted Audit

**What ships (against the V1 spec in `PRODUCT_MVP.md`):**

- 7 Pydantic schemas (`ParsedIntake`, `WorkflowMap`, `LeverageAnalysis`, `ThirtyDayBet`, `RiskAndAgencyMap`, `FirstPlaybook`, plus the imported `EvalReport`).
- 7 agents (`intake_parser`, `workflow_diagnoser`, `leverage_analyst`, `bet_designer`, `risk_mapper`, `playbook_builder`, `critic_eval`) wired through `@agent`.
- 7 prompt templates in `prompts.py`.
- 10 deterministic eval rules + 6-question LLM-judge rubric (§5 + §6 of `PRODUCT_MVP.md`).
- `run_audit(ctx, intake) -> tuple[UUID, EvalReport]` workflow orchestration.
- `audit run --intake fixtures/intakes/synthetic.json` writes the full audit report (JSON) to stdout.
- One synthetic intake fixture covering a "median" small business (e.g. solo consultant, 5–8 weekly tasks, $200 budget, 8 hours/week).
- E2E test: synthetic intake → `EvalReport.accepted=true` against a `MockLLMProvider` with a multi-schema factory (same pattern as the proof scenario).

**Acceptance:**

- `pytest` runs the e2e test in <2 seconds.
- A second e2e test against a real Anthropic call (gated behind `RUN_LIVE_TESTS=1` env var) produces `EvalReport.accepted=true` on the synthetic intake.
- All 7 `AgentRun` rows have `prompt_version` set. The `@agent` fail-fast guard never triggers.

**Why this is a gate:** the synthetic intake proves the architecture works end-to-end on real prompts. Friend-and-family is not the right audience for "does the LLM produce valid JSON" debugging.

---

### Gate 3 — Five real intakes meet `PRODUCT_MVP.md` §7

**What we do:**

- Collect 5 real intakes from friends or contacts (5 different businesses, ideally spanning solo consultant / small services / e-commerce / SaaS founder / freelancer).
- Run each through the Audit.
- Hand each owner the JSON report (or a pretty-printed transcript).
- Have a 15-minute conversation per owner about whether the Bet is specific and doable.

**Acceptance (from `PRODUCT_MVP.md` §7):**

| Criterion | Bar |
| --- | --- |
| Intake fillable without help | <10 minutes for ≥4 of 5 |
| Per-run audit footprint | 1 WorkflowRun + 7–8 AgentRuns + 7 Artifacts, all `status=succeeded`, all 5 runs |
| `EvalReport.accepted=true` on first run | ≥3 of 5 |
| Owner says bet is "specific and doable" | ≥4 of 5 (qualitative, written notes) |
| Platform audit gaps | 0 (prompt_version set everywhere, no double-invoke errors, cost attributed) |

**Why this is a gate:** if real owners can't fill the intake, or the LLM produces generic advice, the wedge is wrong. We learn that with 5 intakes, not 50.

**If Gate 3 fails:** iterate on prompts and schemas only. No new features. Re-run with the same 5 intakes (or 5 new ones if the first batch is contaminated).

---

## 3. After V1 ships: instrument the first 25 real Audits

V1 is **deliberately under-instrumented**. The platform's `AgentRun` + `WorkflowRun` + cost ledger captures everything technical; the product captures only enough about owner behaviour to make V2 decisions.

### Signals to record (per real Audit run)

| Signal | How captured |
| --- | --- |
| Intake completion time | Wall-clock between intake start and submit |
| Audit walltime | Already in `WorkflowRun.ended_at - started_at` |
| Audit cost (USD) | Already in platform cost ledger |
| `EvalReport` status | accepted / rejected / needs_review |
| Which rules failed (if any) | From `EvalReport.criteria` |
| Workflow types in `WorkflowMap` | Tagged manually post-hoc into ~10 categories |
| Bet target workflow type | Same tag set |
| Owner's stated usefulness (1–5) | Asked at the end of the conversation, recorded by us |
| Did owner attempt the bet within 1 week? | Follow-up message at day 7 |
| Did owner re-run with edited intake? | New `WorkflowRun` with same `tenant_id` within 30 days |

### What we do **not** instrument in V1

- No analytics SDK, no Mixpanel, no PostHog.
- No web telemetry — V1 is CLI.
- No "did the owner read the report" beacons.
- No A/B testing infrastructure. Sample size is too small for it to be honest.

A spreadsheet (or one-off Python script over the SQLite DB) is the right tool for the first 25.

---

## 4. V2 directional bets — each with a go/no-go gate

V2 is **not committed to in advance**. Each bet below has an explicit gate based on V1 evidence. If the gate isn't met, the bet doesn't get built — even if it sounds appealing.

### 4.1 Solution Router (the "4 implementation paths per recommendation")

**Bet:** after the Audit identifies an opportunity, the product offers 4 routes to act on it — no-code template / SaaS tool / open-source workflow / partner install.

| Decision | Trigger |
| --- | --- |
| **GO** | ≥40% of accepted Audits result in the owner saying (in the follow-up conversation) some variant of "I don't know HOW to actually implement this." |
| **NO** | Owners say "this is clear, I can take it from here." The Audit itself is the value. |

### 4.2 Tech-readiness routing

**Bet:** intake asks owner to self-rate technical comfort 1–5; routing in §4.1 adapts to the level.

| Decision | Trigger |
| --- | --- |
| **GO** | §4.1 is GO **and** the 25 owners cluster into clearly distinct technical comfort levels (variance in tool sophistication across the cohort). |
| **NO** | §4.1 is NO, or the owners are mostly homogeneous in tech comfort. |

### 4.3 Continuous tracking / weekly reviews

**Bet:** the Audit is no longer one-shot. Owner gets a weekly check-in for 30 days following the bet.

| Decision | Trigger |
| --- | --- |
| **GO** | ≥50% of owners re-run the Audit within 30 days, **or** ≥40% spontaneously say "I wish the system checked in on me." |
| **NO** | Owners treat it as a static report. They don't come back. |

### 4.4 Integrations (CRM / calendar / email — read-only)

**Bet:** the product reads the owner's actual tools to refine the Workflow Map automatically.

| Decision | Trigger |
| --- | --- |
| **GO** | ≥30% of accepted Audits flag "data the owner has but didn't share in intake" as a gap **and** §4.3 is GO. |
| **NO** | Free-text intake is sufficient, or §4.3 is NO. |

**Note on platform cost:** §4.4 requires `ToolCall` as a platform primitive (see `PLAN.md` Phase 4 backlog and the ToolCall vs Anthropic tool_use note). Greenlighting §4.4 pulls a major platform investment forward; the V1 evidence bar is intentionally high.

### 4.5 Multi-business support (real `tenant_id` semantics)

**Bet:** one install supports many businesses. The platform's `tenant_id` (currently constant `"default"` per `PRODUCT_MVP.md` §10) becomes per-business.

| Decision | Trigger |
| --- | --- |
| **GO** | ≥3 consultants, agency owners, or AI freelancers reach out asking "can I use this for my clients?" |
| **NO** | Demand stays single-owner. |

### 4.6 Hebrew localisation

**Bet:** Hebrew intake + report. Prompts localised; schemas remain English.

| Decision | Trigger |
| --- | --- |
| **GO** | ≥5 Hebrew-speaking owners express interest unsolicited. |
| **NO** | Demand stays English-side. |

### 4.7 ReflectionEvent platform primitive

**Bet:** owner can mark "this bet is wrong" / "this risk is wrong" / "don't recommend that again." Captured as a new platform-level primitive (Tier 2 in `DESIGN.md`).

| Decision | Trigger |
| --- | --- |
| **GO** | ≥30% of owners spontaneously want a way to reject or correct Audit outputs. |
| **NO** | Owners accept the Audit as-is or ignore the rejected parts silently. |

### 4.8 Web UI

**Bet:** a hosted web app replaces the CLI.

| Decision | Trigger |
| --- | --- |
| **GO** | Intake completion in CLI falls below ~60% of attempted intakes, **and** §4.3 is GO (so there's something to come back to). |
| **NO** | CLI fills are acceptable, and the use case stays one-shot. |

---

## 5. Decisions this roadmap deliberately does NOT make

These are real questions, but they should be answered **after** V1 evidence, not now:

- **Pricing.** Free / freemium / one-time / subscription. Premature without V1 demand signal.
- **GTM / distribution.** Subreddit posts, founder communities, agency partnerships, paid ads. Premature.
- **Marketplace.** Paid playbooks, recipe library. Vision-doc V3+ territory.
- **Partner / certification program.** Vision-doc V3+ territory.
- **Public landing page / brand.** No public surface area until V1 evidence justifies it.
- **Investor / funding shape.** Out of scope for this doc entirely.

If V1 evidence pushes a decision earlier than the roadmap suggests, fine — but the default is "wait for evidence, then decide."

---

## 6. What "V1 done" means for the platform repo

Once Gate 3 is met:

- The product fork (`ai-leverage-audit`) lives on its own, importing `leverage-platform` as a dependency.
- The platform repo's `proof/thirty_day_leverage_bet/` scenario stays as the platform's internal stress test — not removed.
- Any platform changes triggered by the product fork get committed to `leverage-platform` (and the product picks up a new version). The fork never owns platform code.
- Phase 4 backlog items in `PLAN.md` are pulled into the platform on demand, item by item, as the product surfaces concrete needs.

This keeps the platform demand-driven (per the discipline established when the pivot happened) and avoids speculative API design.

---

## 7. Failure modes the roadmap is designed to catch

| If we observe | The roadmap says |
| --- | --- |
| Gate 1 takes >2 days | Probably a packaging / dependency issue — stop and fix the platform-as-dependency story before continuing. |
| Gate 2's e2e test passes but the synthetic Audit reads as generic | Schemas + prompts are too vague. Iterate on prompts. Do not advance to Gate 3 with generic output. |
| Gate 3 misses ≥3-of-5 acceptance | Either rules are too strict or the LLM judge is over-rejecting. Inspect failure mode before adding features. |
| Gate 3 acceptance passes but owners ignore the Bet | The Audit is technically valid but practically useless. **This is the hardest failure.** Probably means the Bet schema is too abstract; rewrite §3.4 of `PRODUCT_MVP.md` and re-spec. |
| All gates pass, but cost per Audit is painful at scale | Switch some agents to a cheaper model. Cost was deliberately left out of V1 acceptance — it's an operator concern, not a user gate. |

---

## 8. Out of scope (already covered in other docs, repeated here for completeness)

- Platform Phase 4 items (cost CLI, structured logging, `Prompt` object, `ctx.write_artifact`, eval hardening) — see `PLAN.md` Phase 4 backlog.
- The `proof/thirty_day_leverage_bet/` reference scenario — stays in the platform repo as the platform's own stress test.
- ADR-011 (one LLM call per @agent) and the audit-correctness guarantees the platform now enforces.

---

## Summary

| Track | Status |
| --- | --- |
| Gate 1 — Skeleton runs | ⏭️ to start after `git push` of these docs |
| Gate 2 — Synthetic Audit accepted | after Gate 1 |
| Gate 3 — 5 real intakes meet §7 | after Gate 2 |
| Instrument first 25 real Audits | after Gate 3 |
| Decide each V2 bet (§4.1–§4.8) | based on the 25-Audit evidence |
| Pricing / GTM / marketplace / partner program | deliberately deferred (§5) |
