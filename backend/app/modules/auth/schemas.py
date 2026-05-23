"""Pydantic DTOs for /api/auth and /api/me."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    """Returned in the response body for convenience; the auth cookie does the heavy lifting."""

    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID = Field(alias="userId")
    name: str
    email: EmailStr
    role: str
    permissions: list[str]


class MeResponse(BaseModel):
    """Shape consumed by the frontend AuthContext on `/api/me`."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    permissions: list[str]
    lab_id: uuid.UUID | None = Field(default=None, alias="labId")
    department_id: uuid.UUID | None = Field(default=None, alias="departmentId")
