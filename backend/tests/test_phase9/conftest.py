"""Phase 9 test fixtures — Supervisor Dashboard + FR-4/FR-9/FR-16.
Reuses the session-scoped engine + dependency-override pattern from Phase 8.
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


@pytest.fixture
def log_spy() -> list[InvocationRecord]:
    return []


@pytest.fixture
def log_callback(log_spy: list[InvocationRecord], _engine: Any) -> Any:
    """Test log callback that persists to the test DB."""
    _SessionLocal = sessionmaker(bind=_engine)

    async def _cb(record: InvocationRecord) -> None:
        from backend.app.models.ai_invocation_log import AIInvocationLog
        session = _SessionLocal()
        try:
            log_entry = AIInvocationLog(
                invocation_id=record.invocation_id,
                related_entity_type=record.related_entity_type,
                related_entity_id=record.related_entity_id,
                tier_used=record.tier_used or "NONE",
                purpose=record.purpose,
                input_summary=record.input_summary,
                output_text=record.output_text,
                confidence=record.confidence,
                latency_ms=record.latency_ms,
                model_provider=record.model_provider,
                model_name=record.model_name,
                override_type=record.override_type,
            )
            session.add(log_entry)
            session.commit()
        except Exception:
            import traceback
            traceback.print_exc()
        finally:
            session.close()

    return _cb


@pytest.fixture
def fast_cheap_provider() -> StubProvider:
    return StubProvider()


@pytest.fixture
def reasoning_provider() -> StubProvider:
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

    # _log_callback() in incidents.py calls get_log_callback(request) directly
    # (not through Depends), so dependency_overrides won't intercept it.
    # We must set app.state.log_callback directly so that get_log_callback
    # reads the test callback from request.app.state.log_callback.
    # IMPORTANT: do this AFTER TestClient enters context, because TestClient
    # triggers @app.on_event("startup") which resets app.state.log_callback
    # to the module-level _log_cb that writes to crewlinai.db.
    with TestClient(app) as c:
        app.state.log_callback = log_callback
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
