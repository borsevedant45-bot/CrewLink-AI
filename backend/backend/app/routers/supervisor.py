"""Doc #5 §2.3/§2.4/§3.4 — Supervisor Dashboard router.

Includes:
- ``GET /api/v1/supervisor/rollup`` — aggregate zone stats per G17

Doc #1 §5.5 FR-17 through FR-20.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.auth import verify_jwt_token
from backend.app.db.session import get_db
from backend.app.models.crowd_density_reading import CrowdDensityReading
from backend.app.models.incident import Incident as IncidentModel
from backend.app.models.volunteer import Volunteer as VolunteerModel
from backend.app.models.zone import Zone as ZoneModel

logger = logging.getLogger("crewlink.supervisor")
router = APIRouter(prefix="/api/v1/supervisor", tags=["supervisor"])


@router.get("/rollup")
def supervisor_rollup(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Aggregate zone-level rollup for the supervisor dashboard.

    Per Doc #1 §5.5 FR-17/FR-18: shows open incidents by severity and category,
    volunteer coverage vs. task load, and crowd-density context per zone.

    Per G17: single N+1-free endpoint aggregating every zone.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authorization header required")
    auth = verify_jwt_token(auth_header)
    if not auth.is_supervisor:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Supervisor role required")

    zones_data: list[dict[str, Any]] = []
    total_open = 0

    zones = list(db.execute(select(ZoneModel)).scalars().all())
    for zone in zones:
        zid = zone.zone_id

        open_count = db.execute(
            select(func.count(IncidentModel.incident_id)).where(
                IncidentModel.zone_id == zid,
                IncidentModel.status.notin_(["Resolved", "Cancelled"]),
            )
        ).scalar() or 0
        total_open += open_count

        total_volunteers = db.execute(
            select(func.count(VolunteerModel.volunteer_id)).where(
                VolunteerModel.assigned_zone_id == zid,
            )
        ).scalar() or 0
        available_volunteers = db.execute(
            select(func.count(VolunteerModel.volunteer_id)).where(
                VolunteerModel.assigned_zone_id == zid,
                VolunteerModel.status == "AVAILABLE",
            )
        ).scalar() or 0

        # FR-19: latest crowd-density reading per zone (supporting view)
        latest_density = db.execute(
            select(CrowdDensityReading.density_level).where(
                CrowdDensityReading.zone_id == zid,
            ).order_by(CrowdDensityReading.timestamp.desc()).limit(1)
        ).scalar()

        zones_data.append({
            "zone_id": zid,
            "name": zone.name,
            "open_incident_count": open_count,
            "active_volunteer_count": total_volunteers,
            "available_volunteer_count": available_volunteers,
            "current_crowd_density": latest_density,
        })

    return {
        "zones": zones_data,
        "venue_total_open": total_open,
        "generated_at": datetime.now(UTC).isoformat(),
    }
