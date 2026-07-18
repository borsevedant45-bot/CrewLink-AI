"""Doc #5 §2.8 — Knowledge Base endpoints.

POST /api/v1/knowledge-base/ask  — Ask CrewLink retrieval-grounded Q&A.

All other KB endpoints (GET /documents, GET /documents/{id}) are stubs
that return 501 Not Implemented — they are out of Phase 8 scope.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.core.auth import AuthContext, verify_jwt_token
from backend.app.core.deps import get_log_callback, get_model_router
from backend.app.services.ask_crewlink import (
    AskCrewLinkResult,
    handle_ask_crewlink,
)
from backend.orchestration.interfaces import ModelRouter
from backend.orchestration.logging_ import LogCallback

router = APIRouter(prefix="/api/v1/knowledge-base", tags=["knowledge-base"])


# ── Auth helper ─────────────────────────────────────────────────────────


def _get_auth(request: Request) -> AuthContext:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authorization header required")
    return verify_jwt_token(auth_header)


# ── Request schema ──────────────────────────────────────────────────────


class AskQuestionRequest(BaseModel):
    question: str
    zone_id: str | None = None


# ── Endpoints ──────────────────────────────────────────────────────────


@router.post("/ask")
async def ask_crewlink(
    body: AskQuestionRequest,
    request: Request,
    model_router: ModelRouter = Depends(get_model_router),
    log_callback: LogCallback = Depends(get_log_callback),
) -> AskCrewLinkResult:
    """Ask CrewLink — retrieval-grounded Q&A (Reasoning tier).

    Per Doc #4's grounding boundary: generation never runs without a
    non-empty, above-threshold Chroma retrieval.  If retrieval comes back
    empty or below threshold, the response is still 200 OK with
    ``grounded: false``, ``answer: null``, and a ``fallback_message`` —
    never a hallucinated guess.

    Per Doc #5 §5: this endpoint never returns 5xx for AI failures — the
    fallback path handles them and returns 200 with ``fallback_used: true``.
    """
    auth = _get_auth(request)
    volunteer_language = "en"

    result = await handle_ask_crewlink(
        question=body.question,
        volunteer_id=auth.volunteer_id,
        volunteer_language=volunteer_language,
        model_router=model_router,
        log_callback=log_callback,
    )
    return result


@router.get("/documents")
def list_documents() -> dict[str, Any]:
    """List KB documents (metadata).  Stub — returns empty list."""
    return {"items": [], "pagination": {"next_cursor": None, "has_more": False, "limit": 20}}


@router.get("/documents/{doc_id}")
def get_document(doc_id: str) -> JSONResponse:
    """Full document content.  Stub — returns not-implemented."""
    return JSONResponse(
        status_code=501,
        content={"error": {"code": "NOT_IMPLEMENTED", "message": f"Document {doc_id} retrieval not yet implemented"}},
    )
