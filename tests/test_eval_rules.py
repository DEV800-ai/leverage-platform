"""Platform eval primitive: rule_eval correctness."""

from __future__ import annotations

from pydantic import BaseModel

from leverage_platform.eval import Rule, rule_eval


class _Item(BaseModel):
    label: str
    count: int


def test_rule_eval_all_pass() -> None:
    rules: list[Rule[_Item]] = [
        Rule(name="has_label", check=lambda i: (bool(i.label), "label set")),
        Rule(name="positive_count", check=lambda i: (i.count > 0, f"count={i.count}")),
    ]
    report = rule_eval(_Item(label="x", count=5), rules)
    assert report.accepted is True
    assert len(report.criteria) == 2
    assert all(c.passed for c in report.criteria)
    assert "all rules passed" in report.summary


def test_rule_eval_one_fails() -> None:
    rules: list[Rule[_Item]] = [
        Rule(name="has_label", check=lambda i: (bool(i.label), "label set")),
        Rule(name="positive_count", check=lambda i: (i.count > 0, f"count={i.count}")),
    ]
    report = rule_eval(_Item(label="x", count=0), rules)
    assert report.accepted is False
    assert report.criteria[0].passed is True
    assert report.criteria[1].passed is False
    assert "1 of 2 rules failed" in report.summary


def test_rule_eval_preserves_order() -> None:
    rules: list[Rule[_Item]] = [
        Rule(name="r1", check=lambda i: (True, "ok")),
        Rule(name="r2", check=lambda i: (True, "ok")),
        Rule(name="r3", check=lambda i: (True, "ok")),
    ]
    report = rule_eval(_Item(label="x", count=1), rules)
    assert [c.name for c in report.criteria] == ["r1", "r2", "r3"]


def test_rule_eval_empty_rules_accepts() -> None:
    report = rule_eval(_Item(label="x", count=1), [])
    assert report.accepted is True
    assert report.criteria == []
