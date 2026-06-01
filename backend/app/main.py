"""FastAPI application factory.

Run with:

    uvicorn app.main:app --reload --port 8000

Docker uses the same entry point — see docker-compose.yml.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.common.errors import AppError
from app.common.middleware import RequestIdMiddleware, RequestLoggerMiddleware
from app.common.schemas import ErrorResponse
from app.common.schemas.responses import ErrorDetail
from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.routes import ALL_ROUTERS

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(level="INFO" if settings.env == "production" else "DEBUG")
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="LIMS API",
        version="0.1.0",
        description="實驗室資訊管理系統 API 文件",
        lifespan=lifespan,
        docs_url="/api-docs",
        redoc_url="/api-redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestLoggerMiddleware)
    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        # AppError subclasses HTTPException, so this more-specific handler wins
        # over the global HTTPException handler registered below.
        code = getattr(exc, "code", "INTERNAL_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(code=code, message=str(exc.detail))
            ).model_dump(),
        )

    # Global handlers (HTTPException / StarletteHTTPException / validation /
    # SQLAlchemyError / catch-all) all emit the same nested ErrorResponse
    # envelope. The HTTPException handler covers route-not-found too, so there
    # is no separate status-404 handler.
    register_exception_handlers(app)

    @app.get("/health", tags=["Health"])
    async def health() -> dict:
        return {"status": "ok", "service": "lims-backend"}

    @app.get("/", tags=["Health"])
    async def root() -> dict:
        return {
            "service": "lims-backend",
            "docs": "/api-docs",
            "openapi": "/openapi.json",
            "health": "/health",
        }

    for router in ALL_ROUTERS:
        app.include_router(router)

    return app


app = create_app()


# Re-export for clarity
__all__ = ["app", "create_app"]
