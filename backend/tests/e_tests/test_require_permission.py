"""Direct tests for the ``require_permission`` dependency factory.

We exercise it via a tiny throwaway FastAPI app that mounts a route guarded
by the dependency. Going through the FastAPI machinery means cookie-handling,
JWT decode, and session injection all behave identically to production.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from app.common.dependencies import CurrentUser, require_permission
from app.common.errors import AppError
from app.common.schemas import ErrorResponse
from app.common.schemas.responses import ErrorDetail
from app.core.database import get_db
from app.main import app as real_app


def _build_probe_app(code: str) -> FastAPI:
    """A standalone app exposing a single route gated by ``require_permission``.

    Sharing the production ``get_db`` keeps the AsyncSession aligned with the
    test DB. ``require_permission`` is wired by reference.

    The production app's AppError -> ErrorResponse handler is re-registered
    here so 401/403 bodies match what the frontend actually sees.
    """
    probe = FastAPI()

    @probe.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        code_ = getattr(exc, "code", "INTERNAL_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetail(code=code_, message=str(exc.detail))
            ).model_dump(),
        )

    @probe.get("/probe")
    async def probe_route(  # noqa: D401 — test helper
        user: CurrentUser = Depends(require_permission(code)),
    ) -> dict:
        return {"id": str(user.id), "code": code}

    # Reuse production DB session
    probe.dependency_overrides[get_db] = real_app.dependency_overrides.get(get_db, get_db)
    return probe


async def _login_and_get_cookie(email: str, password: str) -> str:
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        assert res.status_code == 200, res.text
        return res.cookies["access_token"]


@pytest.mark.asyncio
async def test_admin_wildcard_passes_any_permission_check() -> None:
    token = await _login_and_get_cookie("admin@example.com", "Admin1234")
    probe = _build_probe_app("orders:approve")
    transport = ASGITransport(app=probe)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"access_token": token},
    ) as ac:
        res = await ac.get("/probe")
    assert res.status_code == 200
    assert res.json()["code"] == "orders:approve"


@pytest.mark.asyncio
async def test_exact_permission_match_passes() -> None:
    token = await _login_and_get_cookie("requester@example.com", "Reque1234")
    probe = _build_probe_app("orders:create")
    transport = ASGITransport(app=probe)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"access_token": token},
    ) as ac:
        res = await ac.get("/probe")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_missing_permission_returns_403() -> None:
    token = await _login_and_get_cookie("requester@example.com", "Reque1234")
    probe = _build_probe_app("users:create")
    transport = ASGITransport(app=probe)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"access_token": token},
    ) as ac:
        res = await ac.get("/probe")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_no_cookie_returns_401() -> None:
    probe = _build_probe_app("orders:read")
    transport = ASGITransport(app=probe)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/probe")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_malformed_token_returns_401() -> None:
    probe = _build_probe_app("orders:read")
    transport = ASGITransport(app=probe)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"access_token": "not-a-real-jwt"},
    ) as ac:
        res = await ac.get("/probe")
    assert res.status_code == 401
