"""Shared pytest fixtures for platform tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from leverage_platform.llm import MockLLMProvider
from leverage_platform.runtime import AgentContext
from leverage_platform.storage import SQLiteStore


@pytest.fixture
def store() -> Iterator[SQLiteStore]:
    """An in-memory SQLite store. Migrations run on construction."""
    s = SQLiteStore(":memory:")
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def mock_provider() -> MockLLMProvider:
    """A MockLLMProvider with no structured_factory; tests set one as needed."""
    return MockLLMProvider()


@pytest.fixture
def ctx(store: SQLiteStore, mock_provider: MockLLMProvider) -> AgentContext:
    """AgentContext for the 'acme' tenant with mock provider and in-memory store."""
    return AgentContext(tenant_id="acme", provider=mock_provider, store=store)
