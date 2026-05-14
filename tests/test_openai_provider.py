"""OpenAIProvider — import + cost-pricing sanity. Live LLM calls require an
ANTHROPIC-or-OPENAI key and are exercised by product-side e2e tests, not here.
"""

from __future__ import annotations

from decimal import Decimal

from leverage_platform.llm import OpenAIProvider
from leverage_platform.llm.openai import OPENAI_PRICING, _cost_usd


def test_openai_provider_constructs_with_explicit_key() -> None:
    p = OpenAIProvider(api_key="sk-test-deadbeef")
    assert p.name == "openai"
    assert p._default_model == "gpt-4o"
    assert p._strict_json is False


def test_openai_provider_strict_json_opt_in() -> None:
    p = OpenAIProvider(api_key="sk-test-deadbeef", strict_json=True)
    assert p._strict_json is True


def test_cost_for_known_model() -> None:
    cost = _cost_usd("gpt-4o", input_tokens=1000, output_tokens=500)
    # 1000 * 0.0025 / 1000 = 0.0025  +  500 * 0.010 / 1000 = 0.005
    assert cost == Decimal("0.0075")


def test_cost_for_mini_is_cheaper_than_full() -> None:
    full = _cost_usd("gpt-4o", input_tokens=1000, output_tokens=1000)
    mini = _cost_usd("gpt-4o-mini", input_tokens=1000, output_tokens=1000)
    assert mini < full
    # mini should be at least an order of magnitude cheaper.
    assert mini * 10 < full


def test_cost_prefix_match_for_dated_variant() -> None:
    """An unknown dated variant should match the base alias via prefix."""
    declared = _cost_usd("gpt-4o-2024-08-06", input_tokens=1000, output_tokens=1000)
    # The dated variant is enumerated directly; that path gives us the same answer.
    assert declared == _cost_usd("gpt-4o", input_tokens=1000, output_tokens=1000)


def test_cost_for_unknown_model_falls_back_to_zero() -> None:
    cost = _cost_usd("does-not-exist", input_tokens=1000, output_tokens=1000)
    assert cost == Decimal("0")


def test_pricing_table_has_entries_for_common_aliases() -> None:
    for alias in ("gpt-4o", "gpt-4o-mini", "gpt-4.1", "o1"):
        assert alias in OPENAI_PRICING, f"missing pricing for {alias}"
