"""Doc #5 §2.4 — Shift summary endpoint (Reasoning tier).

``GET /api/v1/shifts/{shift_id}/summary`` — summarises a volunteer's shift
using the Reasoning-tier LLM, with deterministic fallback per G18.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.core.auth import verify_jwt_token
from backend.app.core.deps import get_log_callback, get_model_router
from backend.app.db.session import get_db
from backend.app.models.crowd_density_reading import CrowdDensityReading
from backend.app.models.incident import Incident as IncidentModel
from backend.app.models.shift import Shift as ShiftModel
from backend.app.models.volunteer import Volunteer as VolunteerModel
from backend.app.services.prompts import SHIFT_SUMMARY_SYSTEM_PROMPT
from backend.orchestration.completion import complete_with_fallback
from backend.orchestration.interfaces import ModelRouter, TaskType
from backend.orchestration.logging_ import LogCallback
from backend.orchestration.schemas import ShiftSummary

logger = logging.getLogger("crewlink.shifts")
router = APIRouter(prefix="/api/v1/shifts", tags=["shifts"])


@router.get("/{shift_id}/summary")
async def shift_summary(
    shift_id: str,
    request: Request,
    db: Session = Depends(get_db),
    model_router: ModelRouter = Depends(get_model_router),
) -> dict[str, Any]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header required")
    auth = verify_jwt_token(auth_header)

    shift = db.execute(
        select(ShiftModel).where(ShiftModel.shift_id == shift_id)
    ).scalar_one_or_none()
    if shift is None:
        raise HTTPException(status_code=404, detail="Shift not found")

    if not auth.is_supervisor and shift.volunteer_id != auth.volunteer_id:
        raise HTTPException(status_code=403, detail="Cannot view another volunteer's shift summary")

    volunteer_zone_id = shift.zone_id

    incidents = list(db.execute(
        select(IncidentModel).where(
            IncidentModel.zone_id == volunteer_zone_id,
            IncidentModel.created_at >= shift.start_time,
            IncidentModel.created_at <= shift.end_time,
        ).order_by(IncidentModel.created_at.asc())
    ).scalars().all())

    crowd_readings = list(db.execute(
        select(CrowdDensityReading).where(
            CrowdDensityReading.zone_id == volunteer_zone_id,
            CrowdDensityReading.timestamp >= shift.start_time,
            CrowdDensityReading.timestamp <= shift.end_time,
        ).order_by(CrowdDensityReading.timestamp.asc())
    ).scalars().all())

    incident_count = len(incidents)
    peak_density = max(
        (r.density_level for r in crowd_readings if r.density_level),
        default=None,
    )

    user_text = (
        f"<shift>\n"
        f"  <volunteer_id>{shift.volunteer_id}</volunteer_id>\n"
        f"  <zone_id>{volunteer_zone_id}</zone_id>\n"
        f"  <start>{shift.start_time.isoformat()}</start>\n"
        f"  <end>{shift.end_time.isoformat()}</end>\n"
        f"  <status>{shift.status}</status>\n"
        f"  <incident_count>{incident_count}</incident_count>\n"
        f"  <peak_density>{peak_density or 'N/A'}</peak_density>\n"
        f"</shift>"
    )

    provider = model_router.for_task(TaskType.SHIFT_SUMMARY)
    log_cb: LogCallback = get_log_callback(request)

    result = await complete_with_fallback(
        provider=provider,
        task_type=TaskType.SHIFT_SUMMARY,
        system_prompt=SHIFT_SUMMARY_SYSTEM_PROMPT,
        user_text=user_text,
        schema=ShiftSummary,
        log_callback=log_cb,
        timeout_s=20.0,
        fallback_kwargs={},
    )

    return {
        "shift_id": shift_id,
        "volunteer_id": shift.volunteer_id,
        "zone_id": volunteer_zone_id,
        "incident_count": incident_count,
        "peak_density": peak_density,
        **result.data,
    }
