"""HTTP routes for /api/auth and /api/me.

Cookie strategy
---------------
Two cookies — one short, one long — so a leaked access cookie expires fast
and a refresh cookie only rides the narrow ``/api/auth/refresh`` path:

- ``access_token``   httpOnly, samesite=lax, path=/,
                     max-age = ``jwt_access_expires_minutes`` (60 min default)
- ``refresh_token``  httpOnly, samesite=lax, path=/api/auth/refresh,
                     max-age = ``jwt_refresh_expires_days`` × 86400 (7 days default)

Both are ``secure=True`` only in production (cookies survive ``http://localhost``
in dev). Both are scoped so the refresh cookie isn't sent on every request,
shrinking the surface where it can leak via misbehaving server-side logging.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from jose import JWTError

from app.common.dependencies import CurrentUser, get_current_user
from app.common.errors import UnauthorizedError
from app.common.schemas import ApiResponse
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.services.auth import AuthService, get_auth_service, project_user

router = APIRouter(prefix="/api", tags=["Auth"])

settings = get_settings()
ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth/refresh"


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    """Single source of truth for cookie attributes — login + refresh both
    use this so the two endpoints can't drift on flags."""
    is_prod = settings.env == "production"
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access,
        max_age=settings.jwt_access_expires_minutes * 60,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        max_age=settings.jwt_refresh_expires_days * 86400,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        # Narrow path: browser only sends refresh on calls to the refresh
        # endpoint. Reduces leak surface vs. the broad access cookie.
        path=REFRESH_COOKIE_PATH,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.post("/auth/login", response_model=ApiResponse[LoginResponse])
async def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[LoginResponse]:
    user = await service.authenticate(str(payload.email), payload.password)
    access, refresh = service.issue_token_pair(user)
    role, permissions = project_user(user)
    _set_auth_cookies(response, access, refresh)
    return ApiResponse(
        data=LoginResponse(
            userId=user.id,
            name=user.name,
            email=user.email,
            role=role,
            permissions=permissions,
        ),
        message="logged in",
    )


@router.post("/auth/logout", response_model=ApiResponse[dict])
async def logout(response: Response) -> ApiResponse[dict]:
    _clear_auth_cookies(response)
    return ApiResponse(data={}, message="logged out")


@router.post("/auth/refresh", response_model=ApiResponse[dict])
async def refresh(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> ApiResponse[dict]:
    """Rotate the access token (and the refresh token) using a still-valid
    refresh cookie. Returns 401 on any failure; frontend interceptor treats
    that as "really logged out" and redirects to /login.

    Token rotation: each successful refresh issues a NEW refresh too. Tier 1
    does not invalidate the old one (Redis blacklist is Tier 2), so the
    rotation here just refreshes the 7-day clock — it doesn't yet detect a
    stolen-refresh replay. Tier 2 docs to follow.
    """
    if not refresh_token:
        raise UnauthorizedError("Missing refresh token")

    try:
        payload = decode_access_token(refresh_token)
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired refresh token") from exc

    # Reject an access token presented in the refresh slot — symmetrical
    # to the check in get_current_user. Stops a leaked access cookie from
    # being used to mint a fresh 7-day refresh.
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Wrong token type for this endpoint")

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Refresh token missing subject")
    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise UnauthorizedError("Refresh token subject is not a valid user id") from exc

    user = await service.find_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    access, new_refresh = service.issue_token_pair(user)
    _set_auth_cookies(response, access, new_refresh)
    return ApiResponse(data={}, message="refreshed")


@router.get("/me", response_model=ApiResponse[MeResponse])
async def get_me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[MeResponse]:
    return ApiResponse(
        data=MeResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            role=user.role,
            permissions=user.permissions,
            labId=user.lab_id,
            departmentId=user.department_id,
        ),
    )
