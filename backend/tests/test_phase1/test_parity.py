"""Test 2: Seed script produces identical row counts and key sets on SQLite and Postgres.

Doc #3 §1.4 explicitly warns a type that only works in prod is "a bug waiting to happen."
"""

import pytest
from sqlalchemy import create_engine, inspect, text

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.models import *  # noqa: F401,F403 — register all models
from backend.app.seed.data import run_seed


@pytest.mark.usefixtures("db_session")
class TestSeedParity:
    """Seed output must be identical across SQLite and Postgres engines."""

    def test_sqlite_and_postgres_have_identical_row_counts(self) -> None:
        sqlite_url = "sqlite://"
        pg_url = settings.database_url.replace("sqlite", "postgresql")

        try:
            pg_engine = create_engine(pg_url)
            pg_engine.connect().close()
        except Exception:
            pytest.skip("Postgres not available — parity test requires both engines")

        pg_engine = create_engine(pg_url)
        sqlite_engine = create_engine(sqlite_url)

        for eng in (sqlite_engine, pg_engine):
            Base.metadata.create_all(bind=eng)
            with eng.begin() as conn:
                run_seed(conn)
            eng.dispose()

        sqlite_engine = create_engine(sqlite_url)
        with (
            sqlite_engine.connect() as sqlite_conn,
            pg_engine.connect() as pg_conn,
        ):
            inspector = inspect(sqlite_engine)
            tables = sorted(inspector.get_table_names())

            mismatches: list[str] = []
            for table in tables:
                sqlite_count = sqlite_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                pg_count = pg_conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if sqlite_count != pg_count:
                    mismatches.append(f"{table}: sqlite={sqlite_count} pg={pg_count}")

                sqlite_pk = inspector.get_pk_constraint(table)["constrained_columns"][0]
                sqlite_keys = {
                    row[0]
                    for row in sqlite_conn.execute(
                        text(f"SELECT {sqlite_pk} FROM {table}")
                    ).fetchall()
                }
                pg_pk = inspector.get_pk_constraint(table)["constrained_columns"][0]
                pg_keys = {
                    row[0]
                    for row in pg_conn.execute(text(f"SELECT {pg_pk} FROM {table}")).fetchall()
                }
                missing = sqlite_keys - pg_keys
                extra = pg_keys - sqlite_keys
                if missing:
                    mismatches.append(f"{table}: missing in pg {missing}")
                if extra:
                    mismatches.append(f"{table}: extra in pg {extra}")

        pg_engine.dispose()

        assert not mismatches, "Parity failures:\n" + "\n".join(mismatches)
