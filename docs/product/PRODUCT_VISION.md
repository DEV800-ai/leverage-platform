# Product Vision — AI Leverage Audit

**Status:** Draft v0.1 — 2026-05-14
**Scope:** Product layer. Does **not** describe the underlying `leverage-platform` infrastructure.
**Companion docs:** `PRODUCT_MVP.md` (concrete spec), `PRODUCT_ROADMAP.md` (phases & validation experiments).

---

## 1. Positioning

> **We are building an AI Operating Mentor for solopreneurs and small business owners** — a system that diagnoses workflows, identifies where AI creates real leverage, helps run small experiments, measures outcomes, and builds a living playbook for the business over time.

### What we are not

| Not this | We are this |
| --- | --- |
| Another chatbot | An ongoing operational mentor |
| An agent builder | A diagnostic that identifies where an agent is even warranted |
| Automate-everything | Smart AI-to-human ratio per workflow |
| Generic AI advice | Accumulated, business-specific intelligence |
| A productivity tool | A system that expands the owner's agency and decision-making |

### The category, in one line

> **AI Operating Mentor for Small Business.**

Both an advisor (where AI helps), a coach (how to run a 30-day experiment), and a learning layer (what worked, what didn't, what fits this specific business).

---

## 2. The pain (validated)

Reddit research across `r/Solopreneur`, `r/smallbusiness`, `r/Entrepreneur`, `r/SaaS`, `r/n8n`, and `r/zapier` consistently surfaces the same recurring pain — not "give me an agent," but:

> *"I understand that AI exists, but I don't know where it actually gives me leverage without becoming another headache."*

Six recurring patterns:

| # | Pattern | Source |
| --- | --- | --- |
| 1 | AI tools feel like extra setup, not relief. Owners already wear too many hats; they don't want another system to learn. | [r/Entrepreneur — AI tools 2025](https://www.reddit.com/r/Entrepreneur/comments/1nv5l41/what_ai_tools_in_2025_are_actually_saving_you/) |
| 2 | AI agents sound powerful, but small business owners under ~$5M revenue have no team and no clear way to evaluate hype vs reality. | [r/smallbusiness — AI agents overhyped?](https://www.reddit.com/r/smallbusiness/comments/1r6r9fg/has_anyone_actually_used_ai_agents_to_automate/) |
| 3 | The pain is **orchestration**, not tools. Owners still have to be the "logic layer" connecting Claude / Make / Zapier / n8n by hand. | [r/Solopreneur — replacing first hires](https://www.reddit.com/r/Solopreneur/comments/1rxt5s0/solopreneurs_what_ai_tools_are_you_using_to/) |
| 4 | Full automation distrusted. Leverage wins: ~60% automate the repetitive, ~30% assist where judgment is needed, ~10% stay human. | [r/smallbusiness — stop automating everything](https://www.reddit.com/r/smallbusiness/comments/1p2k33p/stop_trying_to_automate_everything_with_ai/) |
| 5 | AI rarely sticks because it lives in a separate tab, disconnected from real workflows. Excitement → drift → abandonment. | [r/Entrepreneur — why AI rarely sticks](https://www.reddit.com/r/Entrepreneur/comments/1rqhsm0/i_asked_founders_why_ai_rarely_sticks_in_real/) |
| 6 | AI automation consultants/agencies serving SMBs need better diagnostic and ROI frameworks — they're a B2B wedge as well. | [r/smallbusiness — AI automation services](https://www.reddit.com/r/smallbusiness/comments/1m0z1fn/what_are_some_simple_ai_automation_services_i/) |

**Conclusion:** the market does not need more agent platforms or tool directories. It needs a **decision and learning layer** that helps owners pick, implement, measure, and improve AI workflows over time.

---

## 3. The MVP wedge — AI Leverage Audit

Don't start by building the full mentor. Start with the smallest possible value-delivery entry point:

> **The owner fills a short intake. The system returns a personalised AI Leverage Audit.**

The Audit produces seven typed outputs (full schemas live in `PRODUCT_MVP.md`):

1. **WorkflowMap** — the recurring workflows in the business (leads, follow-ups, invoices, scheduling, support, content, ops).
2. **AILeverageScore** — for each workflow: time_saved, frequency, risk, setup_complexity, human_judgment_needed, integration_difficulty, ROI potential.
3. **AIToHumanRatio** — per workflow: % automate, % assist, % keep human.
4. **ThirtyDayBet** — one concrete 30-day experiment with success metric and a real failure metric (genuine off-ramp, not a face-saver).
5. **RisksAndKeepHuman** — areas not to automate: trust, relationship, regulated decisions, high-blast-radius work.
6. **HumanAgencyCheckpoint** — explicit checkpoints where the owner stays in control and what triggers an escalation back to human.
7. **FirstPlaybook** — the first version of a business-specific playbook (workflows that work, prompts that work, rules for when to involve a human).

After the first Audit, the relationship continues — that's where retention lives.

---

## 4. Product loop

```
Understand the business
    → Map workflows
    → Score AI leverage per workflow
    → Choose one small bet
    → Assist implementation (route to template / SaaS / open-source / partner)
    → Measure outcome
    → Reflect with owner (what was rejected, what felt wrong)
    → Update Playbook
    → Recommend next bet
```

**Why this loop matters:** each iteration accumulates **business-owned intelligence** — not generic memory, but a learned model of *this specific business*: which automations actually stuck, which got rejected, which workflows are too sensitive, what kind of AI fits the owner's style.

After a few cycles the playbook becomes the moat. It cannot be replicated by a generic AI tool.

---

## 5. The seven product roles (the mentor's hats)

| Role | What it does |
| --- | --- |
| **Advisor** | Explains where AI is relevant and where it isn't. |
| **Workflow Diagnoser** | Maps recurring workflows in the business. |
| **AI Leverage Architect** | Decides per workflow: Automate / Assist / Keep Human. |
| **Experiment Coach** | Designs one small 30-day bet, not a giant project. |
| **Measurement Partner** | Checks whether the experiment actually saved time, reduced errors, or improved a real metric. |
| **Business Memory** | Remembers what worked, what failed, what the owner rejected. |
| **Playbook Builder** | Maintains an evolving operational playbook for the business. |

---

## 6. Why "evolves with the business" is the moat

In week 1 the system knows little: what the business does, what hurts, what the owner wants to improve.

By month 3 it knows:

- Which automations actually got adopted.
- Which were rejected, and why.
- Which workflows the owner refuses to hand off (trust, judgment, regulated).
- Which clients / processes are sensitive.
- Which AI shapes (template / SaaS / agent / partner install) fit this owner.
- What's been promoted from "experiment" to "habit."
- What's not worth the effort.

That accumulated state is **Business-Owned Intelligence**. It is the difference between "an AI tool" and "a mentor that knows my business."

---

## 7. The promise (and the non-promise)

The product does **not** say:

> *"Let me replace you."*

The product says:

> *"Let's build a way for AI to grow your business without you losing control of it."*

Human agency is a load-bearing design principle, not a tagline. Every output of the system should leave the owner more informed and more in control, not less.

---

## 8. Initial audiences

| Tier | Audience | Why now |
| --- | --- | --- |
| **Tier 1 — primary** | Solopreneurs (consultants, freelancers, micro-agencies, one-person SaaS) | Highest leverage from AI; most active discussion online; lowest sales friction. |
| **Tier 1 — primary** | Small business owners (1–10 employees, owner-operated services, professional services, e-commerce) | Largest TAM; clearest pain; willing to pay for time saved. |
| **Tier 2 — secondary B2B wedge** | AI automation consultants / agencies serving SMBs | They need a diagnostic + ROI framework to sell with. Faster sales cycle than B2C, smaller per-deal payment. |

---

## 9. Non-goals (for V1)

V1 deliberately does **not** include:

- Building custom agents per customer (that's a software agency model — doesn't scale).
- Hosting customers' tools (CRMs, calendars, email bots, webhooks).
- A full marketplace of paid Playbooks (later, once we have enough of them).
- An affiliate/partner program (later, once recommendations have evidence).
- Integration with customer systems (CRM/email/calendar) — read-only "ToolCall" comes in a later phase.
- Multi-user / team support — single-owner first.

These are real future opportunities (covered in `PRODUCT_ROADMAP.md`), but each one *added now* would dilute the wedge.

---

## 10. Discipline: platform vs product

This product is built on top of the `leverage-platform` infrastructure repo, but the platform knows nothing about Mentors, Audits, Playbooks, or "businesses." Those are product concepts.

- **Platform repo** (`leverage-platform`): provides `@agent`, `run_workflow`, `Artifact`, `EvalReport`, LLM provider abstraction, SQLite storage, cost ledger, retry, eval primitives. Product-agnostic.
- **Product repo** (future fork, e.g. `ai-leverage-audit`): defines the seven product schemas, the prompts, the audit workflow, the UI, the GTM. Product-specific.

**Until the product fork happens, all product work in this repo lives under `docs/product/` only — no schemas, no agents, no prompts, no UI code.** Platform discipline stays intact.

---

> **Note on ongoing market monitoring.** Continuous tracking of subreddits, search queries, and discussion patterns is **out of scope** for this product. It will be handled by a separate tool/repo that surfaces signals back to product planning. The Reddit citations in section 2 above are one-shot evidence for the V1 wedge — not an ongoing data feed.
