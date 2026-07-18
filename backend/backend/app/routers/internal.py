"""Internal-only route family for simulator/automated ingestion.

ADDENDUM G13: Authenticated by static service credential (Header),
distinct from user JWTs. Rejects user JWTs with 403.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status

from backend.app.core.auth import verify_internal_auth
from backend.app.core.error_handling import CrewLinkError

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_internal_auth(authorization: str | None = Header(default=None)) -> None:
    if authorization is None:
        raise CrewLinkError(
            message="Internal auth required",
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )
    if not verify_internal_auth(authorization):
        raise CrewLinkError(
            message="Invalid internal credential",
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )


@router.post("/ingest/incidents")
def ingest_incident(
    _auth: None = Depends(_require_internal_auth),
) -> dict[str, str]:
    return {"status": "accepted"}


@router.post("/ingest/crowd-density")
def ingest_crowd_density(
    _auth: None = Depends(_require_internal_auth),
) -> dict[str, str]:
    return {"status": "accepted"}


@router.post("/ingest/position-pings")
def ingest_position_pings(
    _auth: None = Depends(_require_internal_auth),
) -> dict[str, str]:
    return {"status": "accepted"}
