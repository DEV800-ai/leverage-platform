"""MockLLMProvider: basic behavior + structured_factory contract."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import BaseModel

from leverage_platform.llm import MockLLMProvider


class SampleSchema(BaseModel):
    name: str
    age: int


async def test_mock_provider_generate_text() -> None:
    p = MockLLMProvider(default_text="hello")
    result = await p.generate_text("anything")
    assert result.text == "hello"
    assert result.provider == "mock"
    assert result.cost_usd == Decimal("0.000100")


async def test_mock_provider_records_calls() -> None:
    p = MockLLMProvider()
    await p.generate_text("first")
    await p.generate_text("second")
    assert [c["prompt"] for c in p.calls] == ["first", "second"]


async def test_mock_provider_structured_requires_factory() -> None:
    p = MockLLMProvider()
    with pytest.raises(ValueError, match="no structured_factory"):
        await p.generate_structured("any prompt", SampleSchema)


async def test_mock_provider_structured_returns_factory_value() -> None:
    def factory(schema: type[BaseModel], prompt: str) -> BaseModel:
        return schema(name="alice", age=30)

    p = MockLLMProvider(structured_factory=factory)
    result = await p.generate_structured("any", SampleSchema)
    assert result.value.name == "alice"
    assert result.value.age == 30


async def test_mock_provider_structured_factory_must_return_schema_instance() -> None:
    class OtherSchema(BaseModel):
        x: int

    def bad_factory(schema: type[BaseModel], prompt: str) -> BaseModel:
        return OtherSchema(x=1)

    p = MockLLMProvider(structured_factory=bad_factory)
    with pytest.raises(TypeError, match="expected SampleSchema"):
        await p.generate_structured("any", SampleSchema)
