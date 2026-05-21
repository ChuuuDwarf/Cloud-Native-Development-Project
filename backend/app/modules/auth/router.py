"""HTTP routes for /api/auth and /api/me.

Cookie strategy
---------------
- Name: ``access_token``
- httpOnly: True       (not JS-readable; mitigates XSS-stealable tokens)
- secure: True in prod, False in dev (driven by env)
- samesite: ``lax``    (lets the cookie ride normal cross-origin GETs)
- path: ``/``
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.common.dependencies import CurrentUser, get_current_user
from app.common.schemas import ApiResponse
from app.core.config import get_settings
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.schemas import LoginRequest, LoginResponse, MeResponse
from app.modules.auth.service import AuthService, project_user

router = APIRouter(prefix="/api", tags=["Auth"])

settings = get_settings()
COOKIE_NAME = "access_token"


@router.post("/auth/login", response_model=ApiResponse[LoginResponse])
async def login(
    payload: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> ApiResponse[LoginResponse]:
    user = await service.authenticate(str(payload.email), payload.password)
    token = service.issue_token(user)
    role, permissions = project_user(user)

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=settings.jwt_expires_minutes * 60,
        httponly=True,
        secure=settings.env == "production",
        samesite="lax",
        path="/",
    )

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
    response.delete_cookie(COOKIE_NAME, path="/")
    return ApiResponse(data={}, message="logged out")


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
