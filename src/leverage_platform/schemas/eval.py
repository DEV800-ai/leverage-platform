"""EvalReport and EvalCriterion — the platform eval primitive's output shape."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvalCriterion(BaseModel):
    """One named check applied to an artifact during evaluation."""

    name: str
    passed: bool
    reason: str


class EvalReport(BaseModel):
    """The result of running rule-based and/or LLM-judge evaluation on an artifact.

    Platform-owned: the proof scenario's Critic agent consumes this type
    rather than defining its own (see ADR-003 follow-up and AGENTS.md).
    """

    accepted: bool
    criteria: list[EvalCriterion] = Field(default_factory=list)
    summary: str
