"""Authentication endpoints: login, refresh, ws-ticket.

Doc #5 §2.2 — ws-ticket for WebSocket upgrade.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.auth import (
    create_jwt_token,
    create_ws_ticket,
    verify_jwt_token,
)
from fastapi import APIRouter, Header

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(volunteer_id: str, role: str = "volunteer", zone_id: str | None = None) -> dict[str, Any]:
    token = create_jwt_token(volunteer_id, role, zone_id)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh")
def refresh(authorization: str = Header(...)) -> dict[str, Any]:
    ctx = verify_jwt_token(authorization)
    token = create_jwt_token(ctx.volunteer_id, ctx.role, ctx.zone_id)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/ws-ticket")
def ws_ticket(authorization: str = Header(...)) -> dict[str, Any]:
    ctx = verify_jwt_token(authorization)
    ticket = create_ws_ticket(ctx.volunteer_id)
    return {"ticket": ticket, "ttl_seconds": 30}
