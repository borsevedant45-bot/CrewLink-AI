"""Incident CRUD and dispatch endpoints.

Doc #5 — incidents resource.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthContext, verify_jwt_token
from backend.app.core.deps import get_log_callback, get_model_router
from backend.app.core.state_machine import IncidentStatus, apply_transition
from backend.app.db.session import get_db
from backend.app.models.incident import Incident as IncidentModel
from backend.app.services.classifier import classify_incident
from backend.app.services.dispatch_recommender import recommend_dispatch
from backend.app.services.emergency import broadcast_emergency
from backend.app.services.kb_retrieval import retrieve_chunks
from backend.app.services.ws_manager import manager as ws_manager
from backend.orchestration.interfaces import ModelRouter
from backend.orchestration.logging_ import InvocationRecord

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class CreateIncidentRequest(BaseModel):
    zone_id: str
    description: str
    source: str = "VOLUNTEER_REPORTED"
    reported_by_volunteer_id: str | None = None


class StatusUpdateRequest(BaseModel):
    status: str


class AssignRequest(BaseModel):
    volunteer_id: str


# ── Auth helper ───────────────────────────────────────────────────────────────


def _get_auth(request: Request) -> AuthContext:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return verify_jwt_token(auth_header)


# ── Zone-scoped query helper ──────────────────────────────────────────────────


def _zone_filter(auth: AuthContext) -> Any:
    if auth.is_supervisor:
        from sqlalchemy import true as sa_true
        return sa_true()
    return IncidentModel.zone_id == auth.zone_id


# ── Log callback helper ───────────────────────────────────────────────────────


def _log_callback(request: Request) -> Any:
    return get_log_callback(request)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/feed")
def incident_feed(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    auth = _get_auth(request)
    stmt = select(IncidentModel).where(_zone_filter(auth)).order_by(IncidentModel.created_at.desc()).limit(50)
    rows = list(db.execute(stmt).scalars().all())
    return {
        "items": [_incident_to_dict(r) for r in rows],
        "has_more": False,
    }


@router.get("")
def list_incidents(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    auth = _get_auth(request)
    stmt = select(IncidentModel).where(_zone_filter(auth)).order_by(IncidentModel.created_at.desc()).limit(50)
    rows = list(db.execute(stmt).scalars().all())
    return {
        "items": [_incident_to_dict(r) for r in rows],
        "has_more": False,
    }


@router.get("/{incident_id}")
def get_incident(
    incident_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    auth = _get_auth(request)
    stmt = select(IncidentModel).where(IncidentModel.incident_id == incident_id)
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not auth.is_supervisor and auth.zone_id != row.zone_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incident_to_dict(row)


@router.post("", status_code=201)
async def create_incident(
    body: CreateIncidentRequest,
    request: Request,
    db: Session = Depends(get_db),
    model_router: ModelRouter = Depends(get_model_router),
) -> Any:
    auth = _get_auth(request)

    source = body.source
    if not auth.is_supervisor and source == "SIMULATED":
        source = "VOLUNTEER_REPORTED"

    if not auth.is_supervisor and body.zone_id != auth.zone_id:
        raise HTTPException(status_code=403, detail="Cannot create incidents outside your zone")

    incident = IncidentModel(
        incident_id=str(uuid4()),
        category="general",
        raw_description=body.description,
        source=source,
        zone_id=body.zone_id,
        reported_by_volunteer_id=body.reported_by_volunteer_id,
        priority_score=50,
        status="Reported",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)

    log_cb = _log_callback(request)

    try:
        classification = await classify_incident(
            description=body.description,
            zone_id=body.zone_id,
            source=source,
            model_router=model_router,
            log_callback=log_cb,
        )
        data = classification.data
        incident.category = data.get("category", "general")
        incident.priority_score = _severity_to_score(data.get("severity_signal", "low"))

        if data.get("requires_emergency_escalation", False):
            broadcast_emergency(
                incident_id=incident.incident_id,
                category=incident.category,
                description=body.description,
                zone_id=body.zone_id,
            )
            apply_transition("Reported", "Escalated", emergency_bypass=True)
            incident.status = "Escalated"

        incident.classification_confidence = data.get("confidence")

        # FR-16: accessibility auto-surface via KB retrieval
        if incident.category == "accessibility":
            kb_chunks = await retrieve_chunks(
                f"accessibility procedures and accommodations for {body.description}",
                top_k=3,
            )
            if kb_chunks:
                incident.kb_lookup_performed = True
                incident.kb_reference_ids = [c["chunk_id"] for c in kb_chunks]

        db.commit()
        db.refresh(incident)
    except Exception:
        pass

    await ws_manager.broadcast("tasks", "incident.created", _incident_to_dict(incident))
    await ws_manager.broadcast("supervisor", "incident.created", _incident_to_dict(incident))

    return _incident_to_dict(incident)


@router.patch("/{incident_id}/status")
async def update_incident_status(
    incident_id: str,
    body: StatusUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    auth = _get_auth(request)
    stmt = select(IncidentModel).where(IncidentModel.incident_id == incident_id)
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not auth.is_supervisor and auth.zone_id != row.zone_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status: IncidentStatus = row.status  # type: ignore[assignment]
    new_status_str: IncidentStatus = body.status  # type: ignore[assignment]
    try:
        new_status = apply_transition(old_status, new_status_str)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    row.status = new_status
    timestamp = datetime.now(UTC)
    if new_status == "Triaged":
        row.triaged_at = timestamp
    elif new_status == "Dispatched":
        row.dispatched_at = timestamp
    elif new_status == "Resolved":
        row.resolved_at = timestamp

    db.commit()
    db.refresh(row)

    await ws_manager.broadcast("tasks", "incident.updated", _incident_to_dict(row))
    await ws_manager.broadcast("supervisor", "incident.updated", _incident_to_dict(row))

    # FR-9: log manual reclassification
    log_cb = _log_callback(request)
    rec = InvocationRecord.for_manual_override(
        override_type="HUMAN_RECLASSIFICATION",
        related_entity_type="INCIDENT",
        related_entity_id=incident_id,
        input_summary=f"Status change: {body.status}",
        output_text=f"Status changed from {old_status} to {new_status}",
    )
    await log_cb(rec)

    return _incident_to_dict(row)


@router.post("/{incident_id}/dispatch-recommendation")
async def get_dispatch_recommendation(
    incident_id: str,
    request: Request,
    db: Session = Depends(get_db),
    model_router: ModelRouter = Depends(get_model_router),
) -> Any:
    auth = _get_auth(request)
    stmt = select(IncidentModel).where(IncidentModel.incident_id == incident_id)
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    if not auth.is_supervisor and row.zone_id != auth.zone_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    candidates = _get_candidates_for_zone(db, row.zone_id)

    log_cb = _log_callback(request)

    result = await recommend_dispatch(
        incident_data={
            "incident_id": row.incident_id,
            "category": row.category,
            "severity_signal": _score_to_severity(row.priority_score),
            "zone_id": row.zone_id,
            "description": row.raw_description,
            "requires_emergency_escalation": row.status == "Escalated",
        },
        candidates=candidates,
        model_router=model_router,
        log_callback=log_cb,
    )

    row.dispatch_confidence = result.data.get("confidence")
    row.dispatch_rationale = str(result.data.get("recommended_volunteers", []))
    db.commit()

    return {
        **result.data,
        "fallback_used": result.fallback_used,
    }


@router.patch("/{incident_id}/assign")
async def assign_incident(
    incident_id: str,
    body: AssignRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    auth = _get_auth(request)
    if not auth.is_supervisor:
        raise HTTPException(status_code=403, detail="Only supervisors can assign incidents")

    stmt = select(IncidentModel).where(IncidentModel.incident_id == incident_id)
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_assignee = row.assigned_volunteer_id
    row.assigned_volunteer_id = body.volunteer_id
    db.commit()
    db.refresh(row)

    await ws_manager.broadcast("tasks", "incident.updated", _incident_to_dict(row))
    await ws_manager.broadcast("supervisor", "incident.updated", _incident_to_dict(row))

    # FR-9: log manual reassignment
    log_cb = _log_callback(request)
    rec = InvocationRecord.for_manual_override(
        override_type="HUMAN_REASSIGNMENT",
        related_entity_type="INCIDENT",
        related_entity_id=incident_id,
        input_summary=f"Reassign to: {body.volunteer_id}",
        output_text=f"Assignee changed from {old_assignee} to {body.volunteer_id}",
    )
    await log_cb(rec)

    return _incident_to_dict(row)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _incident_to_dict(inc: IncidentModel) -> dict[str, Any]:
    return {
        "incident_id": inc.incident_id,
        "category": inc.category,
        "description": inc.raw_description,
        "source": inc.source,
        "zone_id": inc.zone_id,
        "status": inc.status,
        "priority_score": inc.priority_score,
        "classification_confidence": inc.classification_confidence,
        "assigned_volunteer_id": inc.assigned_volunteer_id,
        "created_at": inc.created_at.isoformat() if inc.created_at else None,
        "triaged_at": inc.triaged_at.isoformat() if inc.triaged_at else None,
        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
    }


def _severity_to_score(severity: str) -> int:
    mapping = {"high": 90, "medium": 50, "low": 20}
    return mapping.get(severity, 50)


def _score_to_severity(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _get_candidates_for_zone(db: Session, zone_id: str) -> list[dict[str, Any]]:
    from backend.app.models.volunteer import Volunteer
    stmt = select(Volunteer).where(Volunteer.assigned_zone_id == zone_id)
    rows = list(db.execute(stmt).scalars().all())
    return [
        {
            "volunteer_id": v.volunteer_id,
            "zone_id": v.assigned_zone_id,
            "role": v.role,
            "certifications": v.skills_tags or [],
        }
        for v in rows
    ]
