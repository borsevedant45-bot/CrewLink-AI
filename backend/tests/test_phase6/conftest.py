"""Phase 6 test fixtures — overrides app dependencies for integration tests.

Sets up a ModelRouter with StubProviders and a test DB on app.state
so that incident routes that depend on them work correctly.
"""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from typing import Any

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


@pytest.fixture(scope="session")
def _engine() -> Generator[Any, None, None]:
    """Session-scoped file-based SQLite engine with tables created once."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_url = f"sqlite:///{tmp.name}"
    test_engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    # Seed with zones, volunteers, etc.
    with test_engine.connect() as conn:
        run_seed(conn)
        conn.commit()
    yield test_engine
    test_engine.dispose()
    import os
    os.unlink(tmp.name)


@pytest.fixture
def db_session(_engine: Any) -> Generator[Session, None, None]:
    """Fresh session per test, backed by the session-scoped engine."""
    maker = sessionmaker(bind=_engine)
    session = maker()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def log_spy() -> list[InvocationRecord]:
    return []


@pytest.fixture
def log_callback(log_spy: list[InvocationRecord]) -> Any:
    async def _cb(record: InvocationRecord) -> None:
        log_spy.append(record)
    return _cb


@pytest.fixture
def stub_provider() -> StubProvider:
    return StubProvider()


@pytest.fixture
def stub_reasoning_provider() -> StubProvider:
    return StubProvider()


@pytest.fixture
def model_router(
    stub_provider: StubProvider,
    stub_reasoning_provider: StubProvider,
) -> ModelRouter:
    return ModelRouter({
        ModelTier.FAST_CHEAP: stub_provider,
        ModelTier.REASONING: stub_reasoning_provider,
    })


@pytest.fixture
def overridden_client(
    _engine: Any,
    model_router: ModelRouter,
    log_callback: Any,
) -> Generator[TestClient, None, None]:
    """TestClient with all Phase 6 dependencies overridden.

    Creates a fresh DB session per request from the same engine
    that has pre-created tables.
    """
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


@pytest.fixture
def volunteer_token_zone_a() -> str:
    from backend.app.core.auth import create_jwt_token
    return create_jwt_token("vol_maria_alvarez", "volunteer", "zone_east_concourse")


@pytest.fixture
def supervisor_token() -> str:
    from backend.app.core.auth import create_jwt_token
    return create_jwt_token("vol_supervisor_1", "supervisor", None)
