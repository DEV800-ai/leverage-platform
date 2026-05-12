"""30-Day Leverage Bet — reference scenario for stress-testing the platform.

Phase 3 deliverable. See AGENTS.md for the 5-agent workflow contract
and PLAN.md for the acceptance criteria.

TODO(Phase 3):
- schemas.py:  UserProfile, RiskItem, RiskMap, Opportunity, OpportunityMap, ThirtyDayBet
- agents.py:   profile_agent, risk_agent, opportunity_agent, bet_designer_agent, critic_eval_agent
- workflow.py: ThirtyDayLeverageBetWorkflow orchestration
- prompts/:    one .md prompt template per agent
- fixtures/intakes/: 5 sample intake JSONs
- tests/:      end-to-end tests against the real Anthropic provider
"""
