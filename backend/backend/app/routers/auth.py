"""Authentication endpoints: login, refresh, ws-ticket.

Doc #5 §2.2 — ws-ticket for WebSocket upgrade.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header
from pydantic import BaseModel

from backend.app.core.auth import (
    create_jwt_token,
    create_ws_ticket,
    verify_jwt_token,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    badge_code: str
    pin: str


DEMO_CREDENTIALS: dict[str, dict[str, str | None]] = {
    "MARIA": {"volunteer_id": "vol_maria_alvarez", "role": "volunteer", "zone_id": "zone_east_concourse"},
    "JOHN": {"volunteer_id": "vol_john_chen", "role": "volunteer", "zone_id": "zone_west_concourse"},
    "AMINA": {"volunteer_id": "vol_amina_walker", "role": "volunteer", "zone_id": "zone_north_concourse"},
    "CARLOS": {"volunteer_id": "vol_carlos_rodriguez", "role": "volunteer", "zone_id": "zone_south_concourse"},
    "SUPERVISOR": {"volunteer_id": "vol_devon_price", "role": "supervisor", "zone_id": None},
}


@router.post("/login")
def login(body: LoginRequest) -> dict[str, Any]:
    profile = DEMO_CREDENTIALS.get(body.badge_code.upper().strip())
    if profile is None or not body.pin.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid badge code or PIN")
    volunteer_id = profile["volunteer_id"]
    role = profile["role"]
    zone_id = profile["zone_id"]
    if not volunteer_id or not role:
        raise HTTPException(status_code=401, detail="Invalid profile data")
    access_token = create_jwt_token(volunteer_id, role, zone_id)
    refresh_token = create_jwt_token(volunteer_id, role, zone_id, expiry_seconds=86400)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "volunteer_id": volunteer_id,
        "role": role,
        "zone_id": zone_id,
    }


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh(body: RefreshRequest) -> dict[str, Any]:
    ctx = verify_jwt_token(f"Bearer {body.refresh_token}")
    access_token = create_jwt_token(ctx.volunteer_id, ctx.role, ctx.zone_id)
    refresh_token = create_jwt_token(ctx.volunteer_id, ctx.role, ctx.zone_id, expiry_seconds=86400)
    return {"access_token": access_token, "refresh_token": refresh_token}


@router.post("/ws-ticket")
def ws_ticket(authorization: str = Header(...)) -> dict[str, Any]:
    ctx = verify_jwt_token(authorization)
    ticket = create_ws_ticket(ctx.volunteer_id)
    return {"ticket": ticket, "ttl_seconds": 30}
