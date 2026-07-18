"""Integration test fixtures — shared across all 5 Doc #7 §4 flows.

Session-scoped SQLite engine with seeded data, ModelRouter with StubProvider
for LLM_MODE=recorded, and dependency-override TestClient.
"""

from __future__ import annotations

import os
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
from backend.app.models import *  # noqa: F401,F403 — register all models for Base.metadata
from backend.app.seed.data import run_seed
from backend.orchestration.interfaces import ModelRouter, ModelTier
from backend.orchestration.logging_ import InvocationRecord
from tests.test_orchestration.stub_provider import StubProvider

# ---------------------------------------------------------------------------
# Session-scoped engine (one per test run)
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
# Stub providers (LLM_MODE=recorded)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Logging
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
# Overridden TestClient (applied once per test)
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
def volunteer_token_zone_b(_engine: Any) -> str:
    from backend.app.core.auth import create_jwt_token
    maker = sessionmaker(bind=_engine)
    session = maker()
    try:
        from backend.app.models.volunteer import Volunteer
        existing = session.get(Volunteer, "vol_west")
        if existing is None:
            from backend.app.models.zone import Zone
            zone = session.get(Zone, "zone_west_concourse")
            if zone is None:
                from sqlalchemy import text
                session.execute(
                    text("INSERT INTO zones (zone_id, name, zone_type, venue_code, capacity_estimate) VALUES ('zone_west_concourse', 'West Concourse', 'CONCOURSE', 'founders_field', 7500)")
                )
            volunteer = Volunteer(
                volunteer_id="vol_west",
                display_name="West Volunteer",
                role="VOLUNTEER",
                primary_language="en",
                secondary_languages=[],
                assigned_zone_id="zone_west_concourse",
                skills_tags=[],
                status="AVAILABLE",
                auth_subject_id="vol_west",
            )
            session.add(volunteer)
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
    return create_jwt_token("vol_west", "volunteer", "zone_west_concourse")


@pytest.fixture
def supervisor_token_all_zones() -> str:
    from backend.app.core.auth import create_jwt_token
    return create_jwt_token("vol_supervisor_1", "supervisor", None)


@pytest.fixture
def supervisor_token_zone_a_only(_engine: Any) -> str:
    from backend.app.core.auth import create_jwt_token
    maker = sessionmaker(bind=_engine)
    session = maker()
    try:
        from backend.app.models.volunteer import Volunteer
        existing = session.get(Volunteer, "vol_sup_zone_a")
        if existing is None:
            volunteer = Volunteer(
                volunteer_id="vol_sup_zone_a",
                display_name="Zone A Supervisor",
                role="SUPERVISOR",
                primary_language="en",
                secondary_languages=[],
                assigned_zone_id="zone_east_concourse",
                skills_tags=[],
                status="AVAILABLE",
                auth_subject_id="vol_sup_zone_a",
            )
            session.add(volunteer)
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
    return create_jwt_token("vol_sup_zone_a", "supervisor", "zone_east_concourse")

