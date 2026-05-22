import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("lims.error")


def _format_detail(detail: Any, fallback: str) -> str:
    if detail is None:
        return fallback

    if isinstance(detail, str):
        return detail

    if isinstance(detail, list):
        messages: list[str] = []
        for item in detail:
            if isinstance(item, dict):
                loc = item.get("loc") or []
                field = ".".join(str(part) for part in loc if part not in ("body", "query", "path"))
                msg = item.get("msg") or fallback
                messages.append(f"{field}: {msg}" if field else str(msg))
            else:
                messages.append(str(item))
        return "；".join(messages) if messages else fallback

    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("detail")
        return str(message) if message else fallback

    return str(detail)


def _error_payload(
    *,
    request: Request,
    status_code: int,
    detail: Any,
    code: str,
) -> dict[str, Any]:
    return {
        "detail": _format_detail(detail, "伺服器發生錯誤"),
        "code": code,
        "path": request.url.path,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                request=request,
                status_code=exc.status_code,
                detail=exc.detail,
                code="HTTP_ERROR",
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                request=request,
                status_code=exc.status_code,
                detail=exc.detail,
                code="HTTP_ERROR",
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                request=request,
                status_code=422,
                detail=exc.errors(),
                code="VALIDATION_ERROR",
            ),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        logger.exception("Database error on %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                request=request,
                status_code=500,
                detail="資料庫操作失敗，請稍後再試或聯絡系統管理員",
                code="DATABASE_ERROR",
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                request=request,
                status_code=500,
                detail="系統發生未預期錯誤，請稍後再試",
                code="INTERNAL_SERVER_ERROR",
            ),
        )
