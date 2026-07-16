"""Test 1: source is non-nullable at the DB level on Incident, CrowdDensityReading, VolunteerPositionPing.

Doc #3 §4.4 — this is safety-critical, not cosmetic.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from backend.app.models.crowd_density_reading import CrowdDensityReading
from backend.app.models.incident import Incident
from backend.app.models.volunteer_position_ping import VolunteerPositionPing
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

NOW = datetime.now(UTC)


@pytest.mark.usefixtures("db_session")
class TestSourceNonNullable:
    """source must be non-nullable on the three simulation-origin entities."""

    @pytest.mark.parametrize(
        "model_class",
        [Incident, CrowdDensityReading, VolunteerPositionPing],
    )
    def test_source_column_is_non_nullable(self, model_class: type[Any], db_session: Session) -> None:
        assert db_session.bind is not None
        inspector = inspect(db_session.bind)
        tablename: str = model_class.__tablename__
        columns = {c["name"]: c for c in inspector.get_columns(tablename)}
        assert "source" in columns, f"{tablename} has no source column"
        assert not columns["source"]["nullable"], (
            f"{tablename}.source is nullable — §4.4 requires non-nullable"
        )

    @pytest.mark.parametrize(
        "model_class",
        [Incident, CrowdDensityReading, VolunteerPositionPing],
    )
    def test_insert_without_source_raises(self, model_class: type[Any], db_session: Session) -> None:
        if model_class is CrowdDensityReading:
            kwargs = {"zone_id": "zone_placeholder", "timestamp": NOW,
                      "occupancy_estimate": 0, "density_ratio": 0.0, "density_level": "LOW"}
        elif model_class is VolunteerPositionPing:
            kwargs = {"volunteer_id": "vol_placeholder", "zone_id": "zone_placeholder",
                      "timestamp": NOW}
        else:
            kwargs = {"zone_id": "zone_placeholder", "raw_description": "test",
                      "priority_score": 0, "status": "Reported"}

        instance = model_class(**kwargs)
        db_session.add(instance)
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()
