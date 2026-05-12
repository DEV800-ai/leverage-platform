# Personal Leverage OS — Design Document

## 1. Working Name

**Personal Leverage OS**  
Alternative product names: **PivotOS**, **LeverageOS**, **ReinventOS**, **Human Leverage Engine**.

## 2. One-Line Vision

A system that helps individuals continuously adapt, build leverage, and create income opportunities in an AI-native economy.

## 3. Core Thesis

AI will make execution cheaper, faster, and more abundant. The scarce resources will become:

- judgment
- trust
- direction
- personal differentiation
- opportunity selection
- coordination of AI agents
- reputation
- compounding personal assets

The product should not be “another AI assistant.” It should become an **infrastructure layer for personal economic adaptation**.

## 4. Problem Statement

Many people will face career uncertainty as AI reshapes work. Some jobs will disappear, many jobs will change, and new forms of income will emerge. Most people will not need another productivity app. They will need help answering:

- What is my current economic risk?
- Which parts of my work are becoming automated?
- What new opportunities fit my skills, interests, and constraints?
- How can I build a small but real income stream?
- Which AI tools or agents should I use?
- What should I do this month?
- How do I avoid wasting time on fake opportunities?

## 5. Target Users

### Primary ICP — Individual Users

People aged roughly 30–60 who feel career or income uncertainty and want a practical AI-powered path forward.

Examples:

- knowledge workers worried about AI displacement
- freelancers who want better leverage
- mid-career professionals who want to reinvent themselves
- people who want a side income but do not know where to start
- domain experts who want to turn knowledge into assets
- workers in administrative, support, QA, content, marketing, education, or operations roles

### Secondary ICP — Small B2B

Small organizations that support individuals through transition:

- career coaches
- small training programs
- bootcamps
- local business consultants
- creator communities
- professional communities
- employment support organizations

The small-B2B angle can reduce customer acquisition cost and increase trust.

## 6. Product Positioning

### Not This

- generic chatbot
- productivity app
- job board
- course marketplace
- resume builder only
- financial budgeting app only
- autonomous company builder

### This

A guided AI system that turns a user’s profile into:

1. a personal risk map
2. an opportunity map
3. a 30-day practical bet
4. an AI-assisted execution plan
5. a compounding personal memory graph

## 7. Initial Product Slice

### MVP Name

**Opportunity & Reinvention Engine**

### MVP Promise

“Tell us who you are and where you are stuck. We will generate a realistic 30-day path to build leverage, reduce career risk, and test one practical income or reinvention opportunity.”

### MVP User Flow

1. **Profile Intake**
   - current work
   - skills
   - interests
   - constraints
   - time available
   - financial pressure level
   - preferred work style
   - AI comfort level
   - existing assets: audience, network, expertise, capital, location, language

2. **Risk Map**
   - what parts of the user’s role are vulnerable to automation
   - what skills are becoming commoditized
   - what skills are durable
   - what career paths may become stronger

3. **Opportunity Graph**
   - list of possible opportunity paths
   - ranked by fit, speed, risk, defensibility, and compounding value

4. **30-Day Bet**
   - one selected opportunity
   - practical execution plan
   - weekly milestones
   - daily tasks
   - evidence to collect
   - stop/pivot criteria

5. **Agent Workforce Suggestions**
   - research agent
   - content agent
   - outreach agent
   - learning agent
   - product agent
   - financial sanity-check agent

6. **Progress Tracking**
   - what was tried
   - what worked
   - what failed
   - what evidence came from the market
   - what should happen next

## 8. Product Principles

1. **Memory-first, not chat-first**  
   The system should remember structured facts, decisions, experiments, preferences, and outcomes.

2. **Human agency over full automation**  
   The user makes important decisions. The system improves clarity and leverage.

3. **Small executable bets**  
   The product should avoid abstract life advice. It should produce concrete experiments.

4. **Compounding over one-off answers**  
   Every interaction should improve the user model or opportunity model.

5. **Evidence over motivation**  
   The system should push users to collect market evidence, not just feel inspired.

6. **Reusable infrastructure**  
   The first app is a vertical slice. The architecture should support future products.

## 9. Future Product Directions Supported by the Same Infrastructure

The core platform should later support:

- Personal Venture Builder
- AI Career Navigator
- AI Side Income Operator
- AI Learning Path Engine
- Personal Economic Dashboard
- AI Agent Fleet Manager
- Opportunity Intelligence Network
- Family Economic Resilience Tool
- Small-Business-in-a-Box Assistant
- Personal Reputation / Asset Builder

## 10. Core Platform Primitives

### 10.1 User Model

Structured model of the person:

- skills
- experience
- interests
- constraints
- values
- energy level
- risk tolerance
- learning velocity
- financial goals
- preferred work style
- AI maturity
- existing assets

### 10.2 Memory Graph

Stores:

- goals
- decisions
- opportunities considered
- experiments
- outcomes
- user feedback
- generated plans
- skills gained
- documents and notes
- market evidence

### 10.3 Opportunity Graph

Stores opportunities as structured objects:

- title
- description
- target customer
- pain level
- monetization model
- required skills
- required assets
- time to first signal
- competition level
- AI leverage potential
- compounding potential
- evidence sources
- score history

### 10.4 Agent Runtime

A lightweight runtime that runs specialized agents as composable workers.

Core capabilities:

- task creation
- tool access
- memory read/write
- structured outputs
- evaluation
- retry policy
- audit log
- human approval points

### 10.5 Workflow Engine

Defines repeatable flows such as:

- onboarding flow
- risk assessment flow
- opportunity mapping flow
- 30-day bet flow
- weekly review flow
- pivot flow

### 10.6 Evaluation Layer

Every agent output should be evaluated for:

- clarity
- actionability
- fit to user
- realism
- evidence quality
- risk awareness
- hallucination risk

## 11. Suggested Technical Architecture

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend

- Python FastAPI or Node.js/NestJS
- Start simple; choose the stack that allows fast iteration.

Recommended for AI-heavy backend:

- FastAPI
- Pydantic
- SQLAlchemy
- async workers

### Database

- PostgreSQL
- pgvector for embeddings
- Supabase is acceptable for MVP speed

### Queue / Jobs

Start simple:

- background jobs with FastAPI / Celery / RQ / BullMQ

Later:

- Temporal.io or Trigger.dev for durable workflows

### AI Layer

Create a thin provider abstraction for:

- Claude
- OpenAI
- Gemini
- local models later

Do not deeply couple business logic to one LLM provider.

### Search / Research

MVP can start with user-provided sources and manual notes.  
Later add:

- web search APIs
- Perplexity
- Tavily
- SerpAPI
- browser automation
- social listening

### Observability

Track:

- prompts
- model calls
- latency
- cost
- success/failure
- agent outputs
- user feedback
- workflow status

## 12. Data Model — Initial Draft

### UserProfile

```yaml
id: uuid
name: string
current_role: string
industry: string
skills: list[string]
interests: list[string]
constraints: list[string]
time_available_per_week: number
risk_tolerance: low | medium | high
financial_pressure: low | medium | high
ai_maturity: beginner | intermediate | advanced
preferred_work_style: solo | team | consulting | product | creator | local_business
assets:
  network: string
  audience: string
  capital: string
  domain_expertise: list[string]
  languages: list[string]
created_at: datetime
updated_at: datetime
```

### Opportunity

```yaml
id: uuid
title: string
summary: string
target_customer: string
pain_level: 1-5
fit_score: 1-100
speed_score: 1-100
risk_score: 1-100
compounding_score: 1-100
ai_leverage_score: 1-100
required_skills: list[string]
missing_skills: list[string]
first_experiment: string
monetization: string
evidence: list[string]
status: candidate | selected | active | paused | rejected | completed
created_at: datetime
updated_at: datetime
```

### Experiment

```yaml
id: uuid
user_id: uuid
opportunity_id: uuid
title: string
hypothesis: string
start_date: date
end_date: date
success_criteria: list[string]
tasks: list[Task]
evidence_collected: list[string]
outcome: unknown | validated | invalidated | pivot | continue
lessons: list[string]
```

### AgentRun

```yaml
id: uuid
agent_name: string
workflow_name: string
user_id: uuid
input: json
output: json
status: pending | running | succeeded | failed | needs_review
cost_usd: number
model: string
started_at: datetime
ended_at: datetime
```

## 13. MVP Screens

### 13.1 Landing Page

Message:

“Build your next source of leverage in the AI economy.”

Primary CTA:

“Generate my 30-day opportunity plan.”

### 13.2 Onboarding Wizard

Collect structured user profile.

### 13.3 Dashboard

Sections:

- Current Risk Map
- Top Opportunities
- Active 30-Day Bet
- This Week’s Actions
- Evidence Collected
- AI Agents Assigned

### 13.4 Opportunity Detail Page

Shows:

- why this fits the user
- required skills
- market hypothesis
- monetization path
- risks
- first experiment
- next tasks

### 13.5 Weekly Review

Asks:

- What did you do?
- What did the market say?
- What did you learn?
- Should we continue, stop, or pivot?

## 14. Agentic Flow — MVP

```text
User completes intake
        ↓
Profile Agent structures user model
        ↓
Risk Agent generates automation / career risk map
        ↓
Opportunity Agent generates 10 opportunities
        ↓
Critic Agent filters weak/generic options
        ↓
Planner Agent selects one 30-day bet
        ↓
Task Agent creates weekly execution plan
        ↓
Memory Agent stores profile, decisions, plan
        ↓
Weekly Review Agent updates model and recommends next move
```

## 15. Main Differentiation

The product should not give generic career advice. It should create a feedback loop:

```text
User profile → opportunity hypothesis → action → market evidence → learning → better opportunity selection
```

That loop is the product.

## 16. Moat Strategy

### Short-Term Moat

- high-quality workflows
- strong UX
- practical recommendations
- opinionated scoring
- specific niche positioning

### Medium-Term Moat

- personal memory graph
- accumulated experiments
- outcome data
- opportunity scoring history
- user-specific adaptation data

### Long-Term Moat

- proprietary opportunity graph
- anonymized benchmark data
- community intelligence
- reputation layer
- personal AI workforce orchestration

## 17. Risks

### Risk: Too abstract

Mitigation: focus the MVP on one concrete output: a 30-day opportunity bet.

### Risk: Generic AI advice

Mitigation: structured intake, scoring, critic agent, evidence requirements.

### Risk: User does not act

Mitigation: weekly reviews, smaller tasks, accountability, small-B2B coach mode.

### Risk: Overbuilding infrastructure

Mitigation: build one vertical slice first.

### Risk: Privacy concerns

Mitigation: transparent memory, user-controlled deletion, minimal data collection, encryption.

## 18. Build Phases

### Phase 0 — Design

- finalize positioning
- define ICP
- define agent specs
- define data model
- define MVP workflow

### Phase 1 — Clickable Prototype

- landing page
- onboarding form
- static dashboard
- mocked agent outputs

### Phase 2 — Functional MVP

- real LLM calls
- structured profile generation
- opportunity generation
- 30-day plan generation
- persistent storage

### Phase 3 — Memory + Review Loop

- user memory graph
- weekly review
- experiment tracking
- improved recommendations

### Phase 4 — Small B2B Mode

- coach/admin dashboard
- multiple users
- shared templates
- cohort view

### Phase 5 — Agent Fleet

- reusable agent runtime
- scheduled agents
- tool integration
- research sources

## 19. First Milestone Definition

The first milestone is complete when a user can:

1. create a profile
2. receive a personalized risk map
3. receive 10 ranked opportunities
4. choose one opportunity
5. receive a 30-day plan
6. save the plan
7. complete a weekly review
8. see the system update recommendations based on feedback

## 20. Open Questions

- Should the first version be Hebrew-first, English-first, or bilingual?
- Should the initial ICP be individuals or career coaches?
- Should the first opportunity categories be limited to AI-powered side income?
- Should the system include public market / investment thinking later?
- How much autonomy should agents have in the first version?
- Should we use a local-first memory option later?

## 21. Recommended First Decision

Start with a **B2C product for individuals**, but design the architecture so it can become **small-B2B for coaches and communities**.

Build the first vertical slice:

```text
Profile → Risk Map → Opportunity Map → 30-Day Bet → Weekly Review
```

This is small enough to build, but it creates the foundation for the larger Personal Leverage OS vision.
