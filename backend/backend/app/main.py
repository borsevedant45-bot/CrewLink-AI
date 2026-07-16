from __future__ import annotations

import json
import logging
import uuid

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.auth import verify_ws_ticket
from backend.app.core.config import settings
from backend.app.core.error_handling import register_exception_handlers
from backend.app.core.logging_config import configure_logging, set_request_id
from backend.app.routers import auth, chat, incidents, internal, knowledge_base, shifts, supervisor
from backend.app.services.ws_manager import manager as ws_manager

logger = logging.getLogger("crewlink.ws")
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
)


@app.on_event("startup")
def on_startup() -> None:
    from backend.orchestration.interfaces import ModelRouter, ModelTier
    router = ModelRouter({})
    app.state.model_router = router

    from backend.orchestration.logging_ import LogCallback, InvocationRecord
    from sqlalchemy.orm import sessionmaker
    from backend.app.db.session import engine

    _SessionLocal = sessionmaker(bind=engine)

    async def _log_cb(record: InvocationRecord) -> None:
        try:
            from backend.app.models.ai_invocation_log import AIInvocationLog
            session = _SessionLocal()
            log_entry = AIInvocationLog(
                invocation_id=record.invocation_id,
                related_entity_type=record.related_entity_type,
                related_entity_id=record.related_entity_id,
                tier_used=record.tier_used or "NONE",
                purpose=record.purpose,
                input_summary=record.input_summary,
                output_text=record.output_text,
                confidence=record.confidence,
                latency_ms=record.latency_ms,
                model_provider=record.model_provider,
                model_name=record.model_name,
                override_type=record.override_type,
            )
            session.add(log_entry)
            session.commit()
        except Exception:
            logger.exception("Failed to persist AIInvocationLog")
        finally:
            session.close()

    app.state.log_callback = _log_cb
    app.state.db_session_factory = _SessionLocal


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate request_id through logging context per Doc #5 §1.4."""

    async def dispatch(self, request: Request, call: Any) -> Any:
        rid = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"
        set_request_id(rid)
        try:
            response = await call(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            set_request_id(None)


app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(internal.router)
app.include_router(incidents.router)
app.include_router(chat.router)
app.include_router(knowledge_base.router)
app.include_router(shifts.router)
app.include_router(supervisor.router)


@app.websocket("/api/v1/ws/supervisor")
async def supervisor_ws(websocket: WebSocket, ticket: str = Query(...)) -> None:
    """Supervisor dashboard WebSocket — real-time rollup events.

    Per Doc #5 §3.4: receives ``incident.*``, ``volunteer.status_changed``,
    ``zone.crowd_density_updated``, and ``emergency.broadcast`` events.
    """
    try:
        volunteer_id = verify_ws_ticket(ticket)
    except Exception:
        await websocket.close(code=4001, reason="invalid_ticket")
        return

    channel = "supervisor"
    await websocket.accept()
    ws_manager.connect(channel, websocket)
    logger.info("Supervisor WS connected: volunteer=%s", volunteer_id)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            if data.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Supervisor WS error")
    finally:
        ws_manager.disconnect(channel, websocket)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
