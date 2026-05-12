# AGENTS.md

## Purpose

This document defines the initial agent system for **Personal Leverage OS**.

The first product slice is:

```text
Profile → Risk Map → Opportunity Map → 30-Day Bet → Weekly Review
```

Agents should be specialized, structured, auditable, and memory-aware.

## Agent Design Rules

Every agent must define:

- name
- purpose
- input schema
- output schema
- tools allowed
- memory read access
- memory write access
- evaluation criteria
- failure modes

Agents should not freely call each other. A workflow orchestrator should decide the sequence.

## Core Agents — MVP

---

# 1. Profile Structuring Agent

## Purpose

Convert raw onboarding answers into a structured user profile.

## Inputs

- raw questionnaire answers
- optional free-text user description

## Outputs

- structured UserProfile
- missing information list
- confidence score

## Memory Read

- previous UserProfile if available
- previous user preferences

## Memory Write

- stable profile facts
- user goals
- user constraints
- user preferences

## Evaluation Criteria

- captures the user accurately
- does not invent facts
- separates facts from assumptions
- identifies missing information

## Example Output Shape

```json
{
  "current_role": "string",
  "skills": ["string"],
  "interests": ["string"],
  "constraints": ["string"],
  "goals": ["string"],
  "risk_tolerance": "low|medium|high",
  "time_available_per_week": 5,
  "financial_pressure": "low|medium|high",
  "assumptions": ["string"],
  "missing_info": ["string"],
  "confidence": 0.0
}
```

---

# 2. Career / Automation Risk Agent

## Purpose

Analyze how exposed the user’s current role and skills are to AI-driven change.

## Inputs

- UserProfile
- optional market notes

## Outputs

- risk map
- vulnerable tasks
- durable skills
- emerging skills
- recommended defensive moves

## Memory Read

- UserProfile
- past risk maps
- user goals

## Memory Write

- risk assessment snapshot
- recommended skill priorities

## Evaluation Criteria

- realistic, not alarmist
- task-level analysis rather than job-title-only analysis
- includes both risks and opportunities
- provides reasons

## Example Output Shape

```json
{
  "overall_risk": "low|medium|high",
  "vulnerable_tasks": [
    {"task": "string", "risk_reason": "string", "time_horizon": "near|medium|long"}
  ],
  "durable_skills": ["string"],
  "skills_to_build": ["string"],
  "recommended_moves": ["string"]
}
```

---

# 3. Opportunity Mapping Agent

## Purpose

Generate a ranked set of opportunities that fit the user’s profile, constraints, and future economic shifts.

## Inputs

- UserProfile
- RiskMap
- user goals

## Outputs

- 10 Opportunity objects
- opportunity scores
- reasoning
- first experiment suggestion for each opportunity

## Memory Read

- UserProfile
- RiskMap
- previous opportunities
- rejected opportunities
- experiment history

## Memory Write

- generated opportunity candidates
- opportunity scores

## Evaluation Criteria

- specific to the user
- practical within constraints
- not generic side-hustle spam
- contains clear first experiment
- balances near-term feasibility with long-term compounding

## Scoring Dimensions

- fit score
- speed to first signal
- monetization potential
- AI leverage potential
- compounding potential
- defensibility
- risk level
- personal energy fit

## Example Output Shape

```json
{
  "opportunities": [
    {
      "title": "string",
      "summary": "string",
      "target_customer": "string",
      "why_it_fits": "string",
      "monetization": "string",
      "first_experiment": "string",
      "fit_score": 85,
      "speed_score": 70,
      "risk_score": 40,
      "compounding_score": 90,
      "ai_leverage_score": 80,
      "missing_skills": ["string"],
      "main_risks": ["string"]
    }
  ]
}
```

---

# 4. Opportunity Critic Agent

## Purpose

Challenge weak, generic, unrealistic, or low-moat opportunities.

## Inputs

- list of Opportunity objects
- UserProfile

## Outputs

- filtered opportunities
- critique notes
- score adjustments
- questions to resolve

## Memory Read

- previous failed experiments
- user constraints
- rejected opportunity patterns

## Memory Write

- critique history
- reasons for rejection

## Evaluation Criteria

- removes generic ideas
- identifies hidden risks
- avoids false optimism
- improves quality without killing all creativity

## Critique Questions

- Is this opportunity too generic?
- Can the user realistically test it in 30 days?
- Is there a real paying customer?
- What evidence is missing?
- What would make this fail?
- Does AI make this more valuable or easier to copy?

---

# 5. 30-Day Bet Planner Agent

## Purpose

Turn one selected opportunity into a concrete 30-day experiment.

## Inputs

- selected Opportunity
- UserProfile
- user constraints

## Outputs

- experiment hypothesis
- weekly milestones
- daily/near-daily tasks
- success criteria
- stop/pivot criteria
- evidence checklist

## Memory Read

- UserProfile
- selected opportunity
- previous experiment outcomes

## Memory Write

- new Experiment
- planned tasks
- success criteria

## Evaluation Criteria

- concrete
- time-bounded
- realistic
- measurable
- focused on market evidence

## Example Output Shape

```json
{
  "hypothesis": "string",
  "goal": "string",
  "success_criteria": ["string"],
  "stop_criteria": ["string"],
  "weekly_plan": [
    {
      "week": 1,
      "objective": "string",
      "tasks": ["string"],
      "evidence_to_collect": ["string"]
    }
  ]
}
```

---

# 6. Task Breakdown Agent

## Purpose

Convert weekly milestones into small, doable tasks.

## Inputs

- 30-Day Bet plan
- user time availability
- user work style

## Outputs

- task list
- priority
- estimated effort
- dependencies

## Memory Read

- user preferences
- productivity constraints
- past completion patterns

## Memory Write

- task plan

## Evaluation Criteria

- tasks are small enough to execute
- sequence is logical
- avoids overloading the user
- includes visible progress

---

# 7. Weekly Review Agent

## Purpose

Run the weekly review loop and recommend continue, pivot, or stop.

## Inputs

- completed tasks
- user reflections
- evidence collected
- metrics

## Outputs

- progress summary
- lessons learned
- recommendation
- updated next actions
- memory updates

## Memory Read

- active experiment
- previous reviews
- user profile
- opportunity history

## Memory Write

- lessons learned
- evidence collected
- updated user preferences
- updated opportunity status

## Evaluation Criteria

- honest about progress
- does not overfit to one failure
- identifies useful learning
- recommends practical next step

## Example Output Shape

```json
{
  "summary": "string",
  "evidence_collected": ["string"],
  "lessons": ["string"],
  "recommendation": "continue|pivot|stop",
  "reasoning": "string",
  "next_week_actions": ["string"],
  "memory_updates": [
    {"type": "lesson|preference|constraint|evidence", "content": "string"}
  ]
}
```

---

# 8. Memory Curator Agent

## Purpose

Decide what should be stored as durable memory.

## Inputs

- agent outputs
- user feedback
- weekly reviews
- experiment outcomes

## Outputs

- memory items to create
- memory items to update
- memory items to ignore

## Memory Read

- all relevant user memory

## Memory Write

- curated MemoryItem records

## Evaluation Criteria

- avoids storing trivial information
- avoids duplicate memories
- separates stable facts from temporary states
- keeps memory useful for future recommendations

## Memory Categories

- profile_fact
- goal
- constraint
- preference
- decision
- experiment_outcome
- skill
- market_evidence
- opportunity_feedback

---

# 9. Product / Asset Builder Agent

## Purpose

Help the user convert an opportunity into a concrete asset.

Assets may include:

- landing page
- service offer
- newsletter issue
- outreach email
- lead magnet
- product spec
- course outline
- consulting package

## Inputs

- selected opportunity
- 30-day plan
- target customer

## Outputs

- asset draft
- improvement suggestions
- validation checklist

## Memory Read

- user style
- user expertise
- target audience
- previous assets

## Memory Write

- created asset metadata
- user feedback on asset

## Evaluation Criteria

- clear value proposition
- specific audience
- testable
- not overbuilt

---

# 10. Research Agent — Later Phase

## Purpose

Collect market evidence from external sources.

## MVP Status

Not required for first version. Can be mocked or manually triggered.

## Future Tools

- web search
- Reddit search
- LinkedIn/manual notes
- Google Trends
- product directories
- job boards
- newsletters
- government reports
- investment/news APIs

## Outputs

- evidence summaries
- market signals
- competitor notes
- customer pain quotes
- trend strength estimate

## Evaluation Criteria

- cites sources when available
- separates evidence from inference
- avoids shallow trend summaries

---

# 11. Coach Mode Agent — Later Phase

## Purpose

Support small-B2B users such as career coaches or community operators.

## Inputs

- cohort of users
- anonymized progress data
- active experiments

## Outputs

- cohort risk view
- who is stuck
- recommended interventions
- common opportunity clusters

## Memory Read

- cohort-level summaries
- individual progress, if permitted

## Memory Write

- coach notes
- intervention history

---

## Initial Workflow Definition

### Workflow: Generate First 30-Day Bet

```text
1. Profile Structuring Agent
2. Career / Automation Risk Agent
3. Opportunity Mapping Agent
4. Opportunity Critic Agent
5. User selects opportunity or system recommends strongest one
6. 30-Day Bet Planner Agent
7. Task Breakdown Agent
8. Memory Curator Agent
```

### Workflow: Weekly Review

```text
1. User submits progress and evidence
2. Weekly Review Agent summarizes and recommends
3. Memory Curator Agent stores lessons
4. Opportunity Mapping Agent may update scores
5. Task Breakdown Agent creates next-week actions
```

## Agent Output Quality Bar

Outputs must be:

- specific
- structured
- actionable
- grounded in user profile
- honest about uncertainty
- focused on testable next steps

Bad output:

> “Start a newsletter about AI.”

Good output:

> “Create a 4-issue newsletter for Israeli mid-career professionals explaining practical AI workflows. Test demand by sending the first issue to 30 contacts and measuring replies, forwards, and calls booked.”

## Anti-Patterns

Avoid:

- generic business ideas
- fake certainty
- motivational fluff
- huge plans without first experiments
- fully autonomous execution before trust is earned
- too many agents in one flow
- memory spam

## Future Agent Categories

The platform can later add:

- Financial Resilience Agent
- Personal Investment Learning Agent
- Reputation Builder Agent
- Community Builder Agent
- Local Opportunity Agent
- AI Tooling Advisor Agent
- Personal Brand Agent
- Negotiation Agent
- Learning Coach Agent
- Agent Fleet Manager

## North Star Loop

The system should optimize for this loop:

```text
Better user model
    → better opportunity selection
    → better 30-day experiments
    → better market evidence
    → better personal strategy
    → better leverage
```

That loop is the foundation of the product.
