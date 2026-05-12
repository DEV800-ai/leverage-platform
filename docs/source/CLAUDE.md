# CLAUDE.md

## Project Context

This repository is for building **Personal Leverage OS**, an AI-native platform that helps individuals adapt, build leverage, and create income opportunities in a rapidly changing AI economy.

The first product slice is the **Opportunity & Reinvention Engine**:

```text
Profile → Risk Map → Opportunity Map → 30-Day Bet → Weekly Review
```

The long-term goal is not to build a generic chatbot. The goal is to build reusable infrastructure for future products such as:

- AI Career Navigator
- Personal Venture Builder
- AI Side Income Operator
- Personal Economic Dashboard
- AI Agent Fleet Manager
- Opportunity Intelligence Network

## Product Principles

1. **Memory-first, not chat-first**  
   Persist structured user facts, decisions, experiments, and outcomes.

2. **Human agency over full automation**  
   The system should recommend, structure, and coordinate. Important decisions stay with the user.

3. **Small executable bets**  
   Avoid vague advice. Convert insights into 30-day experiments.

4. **Compounding data layer**  
   Every workflow should improve the user model, opportunity model, or experiment history.

5. **Reusable infrastructure**  
   Build services, schemas, and agents that can support multiple future products.

6. **Evidence over motivation**  
   The system should ask: what market evidence did we collect?

## Current MVP Scope

Build only this vertical slice first:

1. User onboarding / profile intake
2. Structured user profile generation
3. Risk map generation
4. Opportunity map generation
5. 30-day bet planning
6. Weekly review loop
7. Memory persistence

Do **not** build a full autonomous agent platform yet.

## Recommended Stack

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

### Backend

Preferred:

- Python FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- pgvector later

Alternative if using full TypeScript:

- Next.js API routes or NestJS
- Prisma
- PostgreSQL

### AI Layer

Create a thin provider abstraction. Do not hard-code the product to one provider.

Supported providers should be abstracted as:

```text
LLMProvider.generateStructured()
LLMProvider.generateText()
LLMProvider.embed()
```

Initial provider can be Claude or OpenAI.

## Architecture Rules

### 1. No Agent Spaghetti

Do not create uncontrolled chains of agents. Each agent must have:

- name
- purpose
- input schema
- output schema
- allowed tools
- memory read/write policy
- evaluation criteria

### 2. Structured Outputs Required

All important LLM outputs should be JSON or Pydantic-validated structures.

Avoid storing only raw text.

### 3. Separate Domain Logic from Prompt Logic

Prompts should live in a clear prompts directory or agent specification layer.

Do not bury long prompts inside UI components.

### 4. Memory Writes Must Be Intentional

Only write durable memory after deciding the information is useful.

Memory categories:

- profile facts
- goals
- constraints
- decisions
- experiments
- outcomes
- preferences
- opportunity feedback

### 5. Every Recommendation Needs a Reason

When the system recommends an opportunity or task, include:

- why it fits the user
- what evidence supports it
- what risk exists
- how to test it quickly

### 6. The MVP Should Be Useful Without External APIs

Do not depend on complex government, bank, LinkedIn, or job-board APIs for the first version.

The MVP can work with:

- structured user input
- uploaded notes later
- manual links later
- LLM reasoning
- optional web research in a later phase

## Folder Structure Suggestion

```text
/
├── apps/
│   ├── web/                  # Next.js frontend
│   └── api/                  # FastAPI backend, if separated
├── packages/
│   ├── agents/               # agent definitions and prompts
│   ├── schemas/              # shared schemas
│   ├── memory/               # memory service
│   ├── llm/                  # provider abstraction
│   └── workflows/            # workflow orchestration
├── docs/
│   ├── DESIGN.md
│   ├── AGENTS.md
│   └── product-notes.md
├── CLAUDE.md
└── README.md
```

If starting smaller, keep a clean monorepo structure but avoid premature complexity.

## Core Domain Objects

Implement or model these early:

- UserProfile
- UserGoal
- UserConstraint
- Skill
- Opportunity
- RiskMap
- Experiment
- Task
- AgentRun
- MemoryItem
- WeeklyReview

## Initial Workflows

### Workflow 1: Onboarding

Input:

- raw form answers

Output:

- structured UserProfile
- missing information questions

### Workflow 2: Risk Map

Input:

- UserProfile

Output:

- automation risks
- durable skills
- skills to strengthen
- career threats
- career opportunities

### Workflow 3: Opportunity Map

Input:

- UserProfile
- RiskMap

Output:

- 10 ranked Opportunity objects
- scores
- reasoning
- suggested first experiments

### Workflow 4: 30-Day Bet

Input:

- selected Opportunity
- UserProfile

Output:

- 30-day experiment
- weekly milestones
- daily tasks
- success criteria
- stop/pivot criteria

### Workflow 5: Weekly Review

Input:

- experiment status
- user feedback
- evidence collected

Output:

- continue / pivot / stop recommendation
- updated lessons
- updated user memory

## Coding Guidelines

- Use type-safe models everywhere.
- Keep functions small and testable.
- Prefer explicit schemas over free-form dictionaries.
- Add docstrings to non-trivial functions.
- Write tests for scoring and workflow logic.
- Make all AI calls traceable with AgentRun records.
- Never silently discard LLM validation errors.
- Prefer clear code over clever abstractions.

## UX Guidelines

The product should feel serious, clear, and practical.

Avoid:

- hype language
- magical AI claims
- overwhelming dashboards
- endless chat interface

Prefer:

- guided workflows
- clear next actions
- visible reasoning
- progress over time
- calm and trustworthy UI

## Tone of Product Copy

Use language like:

- “Here is the strongest 30-day bet for you.”
- “This opportunity fits because...”
- “The main risk is...”
- “Here is the fastest way to test it.”
- “The market evidence we need is...”

Avoid language like:

- “Become rich with AI”
- “Replace your job instantly”
- “Fully automated income”

## Security and Privacy Requirements

- Treat user profile and career/financial data as sensitive.
- Do not expose private profile data in logs.
- Add deletion/export design early.
- Keep AI prompts free from unnecessary personal data.
- Store only what is useful.
- Add a clear memory visibility layer later.

## Development Priorities

### First Sprint

1. Create project structure
2. Define schemas
3. Build onboarding form
4. Implement mock RiskMap and OpportunityMap
5. Build dashboard UI with mock data

### Second Sprint

1. Add real LLM structured generation
2. Persist user profile
3. Persist opportunities
4. Generate 30-day plan
5. Add basic AgentRun audit table

### Third Sprint

1. Add weekly review
2. Add memory updates
3. Add opportunity scoring improvements
4. Add tests and evaluations

## Important Product Constraint

Do not build the entire “Personal OS” now.  
Build the smallest product that proves the core loop:

```text
profile → opportunity → action → evidence → learning → better opportunity
```

That loop is the foundation of the whole company.
