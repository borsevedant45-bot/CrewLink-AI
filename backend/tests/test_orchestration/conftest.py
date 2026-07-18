"""Shared fixtures for orchestration tests.

Provides ``stub_provider`` and ``log_spy`` fixtures that all
``test_completion.py`` tests use.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.orchestration.interfaces import LLMProvider
from backend.orchestration.logging_ import InvocationRecord

from .stub_provider import StubProvider


@pytest.fixture
def stub_provider() -> StubProvider:
    """Return a default (success) StubProvider.

    Tests that need error/timeout behavior override via ``.configure``
    or fixture override.
    """
    return StubProvider()


@pytest.fixture
def provider(stub_provider: StubProvider) -> LLMProvider:
    """Provide the StubProvider typed as the LLMProvider Protocol."""
    return stub_provider


@pytest.fixture
def log_spy() -> list[InvocationRecord]:
    """A simple list that records every ``InvocationRecord`` pushed to it.

    Tests assert on the list length, fallback_used flag, etc.
    """
    return []


@pytest.fixture
def log_callback(log_spy: list[InvocationRecord]) -> Any:
    """Return an async callable that appends to *log_spy*."""

    async def _cb(record: InvocationRecord) -> None:
        log_spy.append(record)

    return _cb
