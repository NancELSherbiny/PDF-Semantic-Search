"""
Application error types and centralized exception handling.

Services raise framework-agnostic `AppError` subclasses. The handlers turn those
— plus FastAPI's own errors — into the contract's {"error": ...} shape, and
convert anything unexpected into a logged 500 without leaking internals.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base for expected errors that map to an HTTP response."""

    status_code = 500
    message = "Internal server error."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message


class BadRequestError(AppError):
    status_code = 400
    message = "Bad request."


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status_code >= 500:
            logger.error("Application error: %s", exc.message)
        return JSONResponse(status_code=exc.status_code, content={"error": exc.message})

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"error": "Invalid request body."})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(status_code=500, content={"error": "Internal server error."})
