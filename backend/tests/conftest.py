"""Pytest fixtures for all phase tests + shared marker registration."""

from collections.abc import Generator
from typing import Any

import pytest

from backend.app.core.auth import create_jwt_token


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers to suppress PytestUnknownMarkWarning."""
    config.addinivalue_line("markers", "llm: marks tests that exercise an AI call site (golden-set / LLM component tests). Run separately in mocked-integration.")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.base import Base
from backend.app.models import *  # noqa: F401,F403 — register all models
from backend.app.seed.data import run_seed


def _make_token(volunteer_id: str, role: str, zone_id: str | None) -> str:
    return str(create_jwt_token(volunteer_id, role, zone_id))


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
    """Enable FK enforcement on SQLite."""
    if hasattr(dbapi_connection, "execute"):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    test_engine = create_engine("sqlite://", echo=False)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Generator[Session, None, None]:
    test_session_cls = sessionmaker(bind=engine)
    session = test_session_cls()
    Base.metadata.create_all(bind=engine)
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with engine.connect() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
            conn.commit()


@pytest.fixture
def seeded_db(db_session: Session) -> Session:
    run_seed(db_session.connection())
    return db_session


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    from backend.app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def volunteer_token_zone_a(client: TestClient) -> str:  # noqa: ARG001
    return _make_token("vol_maria_alvarez", "volunteer", "zone_east_concourse")


@pytest.fixture
def supervisor_token(client: TestClient) -> str:  # noqa: ARG001
    return _make_token("vol_supervisor_1", "supervisor", None)
