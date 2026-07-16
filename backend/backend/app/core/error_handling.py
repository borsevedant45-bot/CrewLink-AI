"""Error response envelope and exception handlers.

Doc #5 §1.4 — error envelope shape.
Doc #5 §5 — error matrix (401, 403, 404, 409, 422, 429, 503).
"""

from __future__ import annotations

import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("crewlink.error")


class CrewLinkError(Exception):
    """Base application error with structured envelope fields."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


def build_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body: dict[str, Any] = {
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    if details:
        body["error"]["details"] = details
    if request_id:
        body["request_id"] = request_id
    return JSONResponse(content=body, status_code=status_code)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CrewLinkError)
    async def crewlink_error_handler(request: Request, exc: CrewLinkError) -> JSONResponse:
        logger.warning(
            "CrewLinkError: %s [%s]", exc.message, exc.error_code,
            extra={"status_code": exc.status_code, "error_code": exc.error_code},
        )
        return build_error_response(
            request,
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        logger.warning("ValidationError: %s", exc)
        return build_error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message=str(exc) or "Validation error",
        )

    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
        logger.warning("PermissionError: %s", exc)
        return build_error_response(
            request,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
            message=str(exc) or "Permission denied",
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception: %s", exc,
            extra={"traceback": traceback.format_exc()},
        )
        return build_error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        )
