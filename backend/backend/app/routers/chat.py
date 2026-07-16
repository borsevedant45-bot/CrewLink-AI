"""Doc #5 §2.7 — Chat Session CRUD + message translation endpoints.

Emergencies: when a translation message's ``emergency_flag`` is true, the
SAME ``broadcast_emergency()`` path used by incidents is called (Doc #5 §3.5),
and an Incident is auto-created with status ``escalated``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.auth import AuthContext, verify_jwt_token
from backend.app.core.deps import get_log_callback, get_model_router
from backend.app.db.session import get_db
from backend.app.models.chat_message import ChatMessage as ChatMessageModel
from backend.app.models.chat_session import ChatSession as ChatSessionModel
from backend.app.models.incident import Incident as IncidentModel
from backend.app.services.emergency import broadcast_emergency
from backend.app.services.translation import translate_message
from backend.app.services.ws_manager import manager as ws_manager
from backend.orchestration.interfaces import ModelRouter

logger = logging.getLogger("crewlink.chat")

router = APIRouter(prefix="/api/v1/chat-sessions", tags=["chat"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────


class CreateSessionRequest(BaseModel):
    zone_id: str
    fan_language: str
    volunteer_language: str = "en"
    fan_display_name: str | None = None


class SendMessageRequest(BaseModel):
    sender: str  # "volunteer" | "fan"
    original_text: str
    original_language: str


class CloseSessionRequest(BaseModel):
    pass


# ── Auth helper ───────────────────────────────────────────────────────────────


def _get_auth(request: Request) -> AuthContext:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header required")
    return verify_jwt_token(auth_header)


def _session_to_dict(session: ChatSessionModel) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "volunteer_id": session.volunteer_id,
        "zone_id": session.zone_id,
        "fan_display_name": session.fan_display_name,
        "volunteer_language": session.volunteer_language,
        "fan_language": session.fan_detected_language,
        "status": "active" if session.status == "ACTIVE" else "closed",
        "created_at": session.started_at.isoformat() if session.started_at else None,
        "closed_at": session.ended_at.isoformat() if session.ended_at else None,
    }


def _message_to_dict(msg: ChatMessageModel) -> dict[str, Any]:
    return {
        "message_id": msg.message_id,
        "session_id": msg.session_id,
        "sender": msg.sender.lower(),
        "original_text": msg.original_text,
        "original_language": msg.original_language,
        "translated_text": msg.translated_text,
        "translated_language": msg.translated_language,
        "confidence": msg.confidence,
        "emergency_flag": msg.emergency_flag,
        "fallback_used": msg.fallback_used,
        "back_translation": msg.back_translation,
        "high_stakes": msg.high_stakes,
        "model_tier": msg.model_tier_used,
        "tool_call": "translate_message",
        "created_at": msg.sent_at.isoformat() if msg.sent_at else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("", status_code=201)
def create_session(
    body: CreateSessionRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Doc #5 §2.7 — Open a translation-bridge session."""
    auth = _get_auth(request)

    session = ChatSessionModel(
        session_id=f"chat_{uuid4().hex[:12]}",
        volunteer_id=auth.volunteer_id,
        zone_id=body.zone_id,
        fan_display_name=body.fan_display_name or f"Fan ({body.fan_language})",
        volunteer_language=body.volunteer_language,
        fan_detected_language=body.fan_language,
        status="ACTIVE",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return _session_to_dict(session)


@router.get("")
def list_sessions(
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Doc #5 §2.7 — List own sessions."""
    auth = _get_auth(request)
    stmt = (
        select(ChatSessionModel)
        .where(ChatSessionModel.volunteer_id == auth.volunteer_id)
        .order_by(ChatSessionModel.started_at.desc())
        .limit(50)
    )
    rows = list(db.execute(stmt).scalars().all())
    return {
        "items": [_session_to_dict(r) for r in rows],
        "has_more": False,
    }


@router.get("/{session_id}")
def get_session(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Doc #5 §2.7 — Session detail."""
    auth = _get_auth(request)
    stmt = select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not auth.is_supervisor and row.volunteer_id != auth.volunteer_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_dict(row)


@router.get("/{session_id}/messages")
def get_messages(
    session_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Doc #5 §2.7 — Paginated history (WS polling fallback)."""
    auth = _get_auth(request)
    # First verify session access
    sess_stmt = select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
    session_row = db.execute(sess_stmt).scalar_one_or_none()
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not auth.is_supervisor and session_row.volunteer_id != auth.volunteer_id:
        raise HTTPException(status_code=404, detail="Session not found")

    stmt = (
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .order_by(ChatMessageModel.sent_at.asc())
        .limit(100)
    )
    rows = list(db.execute(stmt).scalars().all())
    return {
        "items": [_message_to_dict(r) for r in rows],
        "has_more": False,
    }


@router.post("/{session_id}/messages", status_code=201)
async def send_message(
    session_id: str,
    body: SendMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
    model_router: ModelRouter = Depends(get_model_router),
) -> Any:
    """Doc #5 §2.7 / §4.3 — Send + translate a message.

    If ``emergency_flag`` is true, fires ``broadcast_emergency()`` and
    auto-creates an escalated Incident — the SAME code path incidents use.
    """
    auth = _get_auth(request)

    # Verify session exists and caller is participant
    stmt = select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
    session_row = db.execute(stmt).scalar_one_or_none()
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not auth.is_supervisor and session_row.volunteer_id != auth.volunteer_id:
        raise HTTPException(status_code=404, detail="Session not found")

    # Determine target language
    if body.sender == "volunteer":
        source_lang = session_row.volunteer_language
        target_lang = session_row.fan_detected_language
    else:
        source_lang = body.original_language
        target_lang = session_row.volunteer_language

    log_cb = get_log_callback(request)

    # Translate
    translation_result = await translate_message(
        original_text=body.original_text,
        source_language=source_lang,
        target_language=target_lang,
        model_router=model_router,
        log_callback=log_cb,
    )

    data = translation_result.data

    # Build message
    message = ChatMessageModel(
        message_id=f"msg_{uuid4().hex[:12]}",
        session_id=session_id,
        sender=body.sender.upper(),
        original_text=body.original_text,
        original_language=source_lang,
        translated_text=data.get("translated_text", body.original_text),
        translated_language=target_lang,
        confidence=data.get("confidence"),
        emergency_flag=bool(data.get("emergency_flag", False)),
        fallback_used=translation_result.fallback_used,
        back_translation=data.get("back_translation"),
        high_stakes=bool(data.get("high_stakes", False)),
        model_tier_used="fast_cheap",
    )
    db.add(message)

    # ── Emergency: auto-create Incident + broadcast ──────────────
    # Doc #5 §3.5: emergency_flag fires the identical broadcast path
    # as requires_emergency_escalation.
    if message.emergency_flag:
        incident_id = f"inc_{uuid4().hex[:12]}"
        incident = IncidentModel(
            incident_id=incident_id,
            category="medical",
            raw_description=body.original_text,
            source="VOLUNTEER_REPORTED",
            zone_id=session_row.zone_id,
            reported_by_volunteer_id=auth.volunteer_id,
            priority_score=95,
            status="Escalated",
        )
        db.add(incident)

        # Link session to incident
        session_row.linked_incident_id = incident_id

        # Same broadcast_emergency() the incident router uses
        broadcast_emergency(
            incident_id=incident_id,
            category="medical",
            description=body.original_text,
            zone_id=session_row.zone_id,
        )

        await ws_manager.broadcast(
            "tasks",
            "incident.created",
            {
                "incident_id": incident_id,
                "category": "medical",
                "description": body.original_text,
                "source": "VOLUNTEER_REPORTED",
                "zone_id": session_row.zone_id,
                "status": "Escalated",
                "priority_score": 95,
            },
        )

    db.commit()
    db.refresh(message)

    # Broadcast to chat channel
    msg_dict = _message_to_dict(message)
    await ws_manager.broadcast(f"chat/{session_id}", "message.sent", msg_dict)

    return msg_dict


@router.patch("/{session_id}/close")
def close_session(
    session_id: str,
    body: CloseSessionRequest,  # noqa: ARG001
    request: Request,
    db: Session = Depends(get_db),
) -> Any:
    """Doc #5 §2.7 — Close session."""
    auth = _get_auth(request)
    stmt = select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not auth.is_supervisor and row.volunteer_id != auth.volunteer_id:
        raise HTTPException(status_code=404, detail="Session not found")

    row.status = "ENDED"
    row.ended_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)

    return _session_to_dict(row)
