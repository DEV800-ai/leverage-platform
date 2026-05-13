"""Eval configuration for the proof scenario's Critic agent.

Two layers:
- THIRTY_DAY_BET_RULES — deterministic structural checks via the platform
  eval primitive. Cheap, fast, stable.
- THIRTY_DAY_BET_RUBRIC — subjective questions for llm_judge. Fired only
  if rule_eval passes.
"""

from __future__ import annotations

from leverage_platform.eval import Rule
from proof.thirty_day_leverage_bet.schemas import ThirtyDayBet


def _has_title(bet: ThirtyDayBet) -> tuple[bool, str]:
    ok = bool(bet.title.strip())
    return ok, "title is non-empty" if ok else "title is empty"


def _weekly_plan_has_four_items(bet: ThirtyDayBet) -> tuple[bool, str]:
    n = len(bet.weekly_plan)
    return n == 4, f"weekly_plan has {n} items (expected exactly 4)"


def _weekly_plan_items_non_empty(bet: ThirtyDayBet) -> tuple[bool, str]:
    empty = [i for i, item in enumerate(bet.weekly_plan) if not item.strip()]
    if empty:
        return False, f"weekly_plan items {empty} are empty"
    return True, "all weekly_plan items non-empty"


def _success_metric_set(bet: ThirtyDayBet) -> tuple[bool, str]:
    ok = bool(bet.success_metric.strip())
    return ok, "success_metric set" if ok else "success_metric is empty"


def _failure_metric_set(bet: ThirtyDayBet) -> tuple[bool, str]:
    ok = bool(bet.failure_metric.strip())
    return ok, "failure_metric set" if ok else "failure_metric is empty"


def _failure_metric_differs_from_success(bet: ThirtyDayBet) -> tuple[bool, str]:
    if bet.success_metric.strip() == bet.failure_metric.strip():
        return False, "failure_metric is identical to success_metric"
    return True, "failure_metric differs from success_metric"


def _first_48h_at_least_two(bet: ThirtyDayBet) -> tuple[bool, str]:
    n = len(bet.first_48h_actions)
    return n >= 2, f"first_48h_actions has {n} item(s) (expected ≥2)"


def _expected_asset_set(bet: ThirtyDayBet) -> tuple[bool, str]:
    ok = bool(bet.expected_asset_created.strip())
    return ok, "expected_asset_created set" if ok else "expected_asset_created is empty"


THIRTY_DAY_BET_RULES: list[Rule[ThirtyDayBet]] = [
    Rule(name="has_title", check=_has_title),
    Rule(name="weekly_plan_has_four_items", check=_weekly_plan_has_four_items),
    Rule(name="weekly_plan_items_non_empty", check=_weekly_plan_items_non_empty),
    Rule(name="success_metric_set", check=_success_metric_set),
    Rule(name="failure_metric_set", check=_failure_metric_set),
    Rule(name="failure_metric_differs_from_success", check=_failure_metric_differs_from_success),
    Rule(name="first_48h_at_least_two", check=_first_48h_at_least_two),
    Rule(name="expected_asset_set", check=_expected_asset_set),
]


THIRTY_DAY_BET_RUBRIC: list[str] = [
    "Is this bet specific to the user's profile and skills, not generic advice?",
    "Can the first 48-hour actions realistically be completed in 48 hours?",
    "Is the success_metric observable within 30 days?",
    "Is the failure_metric a genuine off-ramp, not a face-saver?",
    "Does the weekly_plan fit the user's stated weekly_time_hours?",
    "Does the bet create a compounding asset (audience, skill, product, dataset), "
    "rather than just busywork?",
]
