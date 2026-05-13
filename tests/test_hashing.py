"""Hashing utilities: determinism, canonical JSON, scheme rules from ADR-003."""

from __future__ import annotations

from leverage_platform._hashing import hash_inputs, hash_output, hash_template


def test_template_hash_is_64_hex() -> None:
    h = hash_template("Convert {intake} to a profile.")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_template_hash_is_deterministic() -> None:
    h1 = hash_template("Convert {intake} to a profile.")
    h2 = hash_template("Convert {intake} to a profile.")
    assert h1 == h2


def test_template_hash_changes_when_template_changes() -> None:
    h1 = hash_template("Convert {intake} to a profile.")
    h2 = hash_template("Convert {intake} to a profile!")
    assert h1 != h2


def test_inputs_hash_is_key_order_independent() -> None:
    a = hash_inputs({"a": 1, "b": 2})
    b = hash_inputs({"b": 2, "a": 1})
    assert a == b


def test_inputs_hash_changes_when_value_changes() -> None:
    a = hash_inputs({"name": "Alice"})
    b = hash_inputs({"name": "Bob"})
    assert a != b


def test_output_and_inputs_use_same_canonicalization() -> None:
    payload = {"x": 1, "y": [1, 2, 3]}
    assert hash_output(payload) == hash_inputs(payload)
