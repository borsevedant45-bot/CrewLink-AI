"""App-level dependency providers.

These are injected into FastAPI route handlers via ``Depends()``.
Override in tests by setting ``app.dependency_overrides``.
"""

from __future__ import annotations

from fastapi import Request

from backend.orchestration.interfaces import ModelRouter
from backend.orchestration.logging_ import InvocationRecord, LogCallback


def get_model_router(request: Request) -> ModelRouter:
    router: ModelRouter | None = getattr(request.app.state, "model_router", None)
    if router is None:
        msg = "ModelRouter not configured on app.state.model_router"
        raise RuntimeError(msg)
    return router


def get_log_callback(request: Request) -> LogCallback:
    stored: LogCallback | None = getattr(request.app.state, "log_callback", None)
    if stored is not None:
        return stored

    async def _default_log_cb(record: InvocationRecord) -> None:
        pass

    return _default_log_cb
