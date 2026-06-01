"""Global exception handlers that normalize every error response.

All handlers here emit the project's nested error envelope::

    {"error": {"code": "...", "message": "..."}}

built from :class:`app.common.schemas.responses.ErrorResponse` /
:class:`~app.common.schemas.responses.ErrorDetail` — the same construction
used by the ``AppError`` handler in ``app.main`` — so the whole API speaks one
shape regardless of whether an error originated from a domain ``AppError``, a
raw ``HTTPException``, request validation, the database, or an unhandled bug.

``register_exception_handlers(app)`` is called from ``app.main.create_app``.
The ``AppError`` handler registered inline in ``app.main`` is *more specific*
than the ``HTTPException`` handler below (``AppError`` subclasses
``HTTPException``), so FastAPI/Starlette dispatch ``AppError`` instances to it
and only raw ``HTTPException``s reach the handler here.
"""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.schemas import ErrorResponse
from app.common.schemas.responses import ErrorDetail

logger = logging.getLogger("lims.error")

# Map HTTP status codes to stable error codes the frontend can switch on.
_STATUS_CODE_MAP: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
}


def _code_for_status(status_code: int) -> str:
    return _STATUS_CODE_MAP.get(status_code, "HTTP_ERROR")


def _envelope(*, status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump(),
    )


def _summarize_validation_errors(errors: Sequence[Any]) -> str:
    """Flatten ``exc.errors()`` into a single readable message."""
    messages: list[str] = []
    for item in errors:
        if not isinstance(item, dict):
            messages.append(str(item))
            continue
        loc = item.get("loc") or []
        field = ".".join(str(part) for part in loc if part not in ("body", "query", "path"))
        msg = item.get("msg") or "輸入資料驗證失敗"
        messages.append(f"{field}: {msg}" if field else str(msg))
    return "；".join(messages) if messages else "輸入資料驗證失敗"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _envelope(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="VALIDATION_ERROR",
            message=_summarize_validation_errors(exc.errors()),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        _: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        code = _code_for_status(exc.status_code)
        message = str(exc.detail) if exc.detail is not None else code
        return _envelope(status_code=exc.status_code, code=code, message=message)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        _: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        code = _code_for_status(exc.status_code)
        message = str(exc.detail) if exc.detail is not None else code
        return _envelope(status_code=exc.status_code, code=code, message=message)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        logger.exception("Database error on %s", request.url.path, exc_info=exc)
        return _envelope(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
            message="資料庫操作失敗，請稍後再試或聯絡系統管理員",
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path, exc_info=exc)
        return _envelope(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INTERNAL_SERVER_ERROR",
            message="系統發生未預期錯誤，請稍後再試",
        )
