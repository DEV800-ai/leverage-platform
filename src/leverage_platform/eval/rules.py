"""Rule-based evaluation — deterministic, fast, no LLM call.

Per ADR: deterministic-first / LLM-judge-second. Rules run on validated
Pydantic artifacts and produce structured EvalCriterion outcomes.

Phase 3: minimum-viable surface. Phase 4 hardens (adds parallel rule execution,
configurable severity, rule-suite versioning).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from leverage_platform.schemas import EvalCriterion, EvalReport


@dataclass(frozen=True)
class RuleResult:
    """The verdict of one rule check."""

    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class Rule[T: BaseModel]:
    """A single named check on an artifact.

    The check function returns (passed, reason). The platform wraps this in
    a RuleResult and EvalCriterion. Rules must be pure functions — no I/O,
    no state.
    """

    name: str
    check: Callable[[T], tuple[bool, str]]

    def evaluate(self, artifact: T) -> RuleResult:
        passed, reason = self.check(artifact)
        return RuleResult(name=self.name, passed=passed, reason=reason)


def rule_eval[T: BaseModel](artifact: T, rules: list[Rule[T]]) -> EvalReport:
    """Run all rules against `artifact`. Returns an EvalReport.

    `accepted` is True iff every rule passed. The criteria list is in the
    order rules were declared. The summary is a short human-readable string.
    """
    criteria: list[EvalCriterion] = []
    for rule in rules:
        result = rule.evaluate(artifact)
        criteria.append(
            EvalCriterion(name=result.name, passed=result.passed, reason=result.reason)
        )

    failures = [c for c in criteria if not c.passed]
    accepted = not failures
    summary = (
        "all rules passed"
        if accepted
        else f"{len(failures)} of {len(criteria)} rules failed"
    )
    return EvalReport(accepted=accepted, criteria=criteria, summary=summary)
