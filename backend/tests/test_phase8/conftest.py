"""Phase 8 test fixtures — Ask CrewLink service + route tests.

Reuses the same session-scoped engine, StubProvider, and dependency-override
pattern from Phase 6/7, with additional fixtures for Chroma retrieval mocking
via unittest.patch.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.deps import get_log_callback, get_model_router
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.seed.data import run_seed
from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord
from tests.test_orchestration.stub_provider import StubProvider

# ---------------------------------------------------------------------------
# DB fixtures (same pattern as Phase 6/7 conftest)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _engine() -> Generator[Any, None, None]:
    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{tmp_path}"
    test_engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    with test_engine.connect() as conn:
        run_seed(conn)
        conn.commit()
    yield test_engine
    test_engine.dispose()
    os.unlink(tmp_path)


@pytest.fixture
def db_session(_engine: Any) -> Generator[Session, None, None]:
    maker = sessionmaker(bind=_engine)
    session = maker()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ---------------------------------------------------------------------------
# Logging fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def log_spy() -> list[InvocationRecord]:
    return []


@pytest.fixture
def log_callback(log_spy: list[InvocationRecord]) -> Any:
    async def _cb(record: InvocationRecord) -> None:
        log_spy.append(record)
    return _cb


# ---------------------------------------------------------------------------
# Provider fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fast_cheap_provider() -> StubProvider:
    """Fast/Cheap stub — used for intent routing and translation."""
    return StubProvider()


@pytest.fixture
def reasoning_provider() -> StubProvider:
    """Reasoning stub — used for Ask CrewLink synthesis."""
    return StubProvider()


@pytest.fixture
def model_router(
    fast_cheap_provider: StubProvider,
    reasoning_provider: StubProvider,
) -> ModelRouter:
    return ModelRouter({
        ModelTier.FAST_CHEAP: fast_cheap_provider,
        ModelTier.REASONING: reasoning_provider,
    })


# ---------------------------------------------------------------------------
# Overridden TestClient
# ---------------------------------------------------------------------------


@pytest.fixture
def overridden_client(
    _engine: Any,
    model_router: ModelRouter,
    log_callback: Any,
) -> Generator[TestClient, None, None]:
    maker = sessionmaker(bind=_engine)

    def _override_db() -> Generator[Session, None, None]:
        session = maker()
        try:
            yield session
        finally:
            session.rollback()
            session.close()

    def _override_router() -> ModelRouter:
        return model_router

    def _override_log_cb() -> Any:
        return log_callback

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_model_router] = _override_router
    app.dependency_overrides[get_log_callback] = _override_log_cb

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth tokens
# ---------------------------------------------------------------------------


@pytest.fixture
def volunteer_token_zone_a() -> str:
    from backend.app.core.auth import create_jwt_token
    return create_jwt_token("vol_maria_alvarez", "volunteer", "zone_east_concourse")


@pytest.fixture
def supervisor_token() -> str:
    from backend.app.core.auth import create_jwt_token
    return create_jwt_token("vol_supervisor_1", "supervisor", None)


# ---------------------------------------------------------------------------
# Mock KB retrieval chunks
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_retrieved_chunks() -> list[dict[str, Any]]:
    """Simulated Chroma retrieval results for "accessible restroom East Concourse"."""
    return [
        {
            "chunk_id": "abc123_chunk_east_concourse",
            "text": (
                "The East Concourse serves Sections 100 through 120 on the east side "
                "of Founders Field. It contains two main concession stands, four restroom "
                "facilities (two accessible), Guest Services Desk East, and a first-aid "
                "station at the north end."
            ),
            "metadata": {
                "doc_title": "Founders Field Zone Guide",
                "doc_type": "VENUE_MAP",
                "section_heading": "East Concourse (Sections 100–120)",
                "token_count": "55",
            },
            "similarity": 0.82,
        },
        {
            "chunk_id": "def456_accessibility_restrooms",
            "text": (
                "Restrooms are located on every concourse at regular intervals. "
                "Accessible/family restrooms are adjacent to each standard restroom block. "
                "Wheelchair-accessible restrooms are located on every concourse adjacent "
                "to standard restrooms."
            ),
            "metadata": {
                "doc_title": "Founders Field Guest FAQ",
                "doc_type": "FAQ",
                "section_heading": "Where are the nearest restrooms?",
                "token_count": "40",
            },
            "similarity": 0.78,
        },
    ]


@pytest.fixture
def mock_retrieval_patch(mock_retrieved_chunks: list[dict[str, Any]]) -> Generator[Any, None, None]:
    """Patch retrieve_chunks inside ask_crewlink to return mock data.

    Because ask_crewlink.py does ``from ...kb_retrieval import retrieve_chunks``,
    the local name is bound in ask_crewlink's namespace — so we patch there.
    """
    mock_fn = AsyncMock(return_value=mock_retrieved_chunks)
    with patch("backend.app.services.ask_crewlink.retrieve_chunks", mock_fn):
        yield mock_fn
