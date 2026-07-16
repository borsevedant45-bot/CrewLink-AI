"""Auth context, JWT dependency, and ws-ticket management.

Doc #5 §1.3 — JWT in Authorization header
Doc #6 §3 — role/zone claims checked server-side on every REST/WS call
ADDENDUM G13 — internal auth uses separate static credential
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, TypeVar

import jwt

from backend.app.core.config import settings

F = TypeVar("F", bound=Callable[..., Any])
JWT_ALGORITHM = "HS256"
WS_TICKET_TTL = 30


@dataclass
class AuthContext:
    volunteer_id: str
    role: str
    zone_id: str | None

    @property
    def is_supervisor(self) -> bool:
        return self.role == "supervisor"

    def can_access_zone(self, target_zone_id: str) -> bool:
        if self.is_supervisor:
            return True
        return self.zone_id == target_zone_id


def create_jwt_token(
    volunteer_id: str,
    role: str,
    zone_id: str | None,
    *,
    expiry_seconds: int = 3600,
) -> str:
    payload: dict[str, Any] = {
        "sub": volunteer_id,
        "role": role,
        "zone_id": zone_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + expiry_seconds,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict[str, Any]:
    result: dict[str, Any] = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    return result


def verify_jwt_token(authorization: str) -> AuthContext:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        raise ValueError("Invalid authorization scheme")
    payload = decode_jwt_token(token)
    return AuthContext(
        volunteer_id=payload["sub"],
        role=payload["role"],
        zone_id=payload.get("zone_id"),
    )


def create_ws_ticket(volunteer_id: str) -> str:
    payload: dict[str, Any] = {
        "sub": volunteer_id,
        "purpose": "ws_upgrade",
        "iat": int(time.time()),
        "exp": int(time.time()) + WS_TICKET_TTL,
        "jti": str(uuid.uuid4()),
    }
    result: str = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    return result


def verify_ws_ticket(token: str) -> str:
    payload: dict[str, Any] = jwt.decode(token, settings.jwt_secret_key, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "ws_upgrade":
        raise ValueError("Token is not a ws-ticket")
    return str(payload["sub"])


@lru_cache
def _get_internal_credential() -> str:
    return str(settings.simulator_auth_token)


def verify_internal_auth(authorization: str) -> bool:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return False
    return token == _get_internal_credential()


def require_role(required_role: str) -> Callable[[F], F]:
    """Decorator factory: require specific role on route."""
    def decorator(func: F) -> F:
        def wrapper(auth_context: AuthContext, *args: Any, **kwargs: Any) -> Any:
            if auth_context.role != required_role:
                raise PermissionError(
                    f"Requires role '{required_role}', got '{auth_context.role}'"
                )
            return func(auth_context, *args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator


def _check_role(required_role: str, auth_context: AuthContext) -> None:
    """Dependency-style check: raise if role doesn't match."""
    if auth_context.role != required_role:
        raise PermissionError(
            f"Requires role '{required_role}', got '{auth_context.role}'"
        )
