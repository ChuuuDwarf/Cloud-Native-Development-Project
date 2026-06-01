"""Pydantic DTOs for /api/users."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.common.enums import UserStatus


class _UserConfig(BaseModel):
    """Common config block: accept camelCase aliases, allow ORM conversion."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RoleSummary(_UserConfig):
    id: uuid.UUID
    name: str


class UserBase(_UserConfig):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    department_id: uuid.UUID | None = Field(default=None, alias="departmentId")
    lab_id: uuid.UUID | None = Field(default=None, alias="labId")
    # Local phone number for the CHT TAS callout pipeline. Optional; an empty
    # / None value disables phone alerts for the account.
    phone: str | None = Field(default=None, alias="phoneNumber", max_length=20)


class UserCreate(UserBase):
    # 72-byte cap matches bcrypt's hard limit; longer inputs are silently
    # truncated by the hasher but rejecting at the boundary is friendlier.
    password: str = Field(min_length=8, max_length=72)
    role_ids: list[uuid.UUID] = Field(default_factory=list, alias="roleIds")


class UserUpdate(BaseModel):
    """PATCH /api/users/:id — every field is optional.

    A non-None ``password`` resets the user's password (admin path).
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    department_id: uuid.UUID | None = Field(default=None, alias="departmentId")
    lab_id: uuid.UUID | None = Field(default=None, alias="labId")
    status: UserStatus | None = None
    role_ids: list[uuid.UUID] | None = Field(default=None, alias="roleIds")
    password: str | None = Field(default=None, min_length=8, max_length=72)
    # Phone update path. Use empty string or None to clear; otherwise
    # overwrites with the provided value.
    phone: str | None = Field(default=None, alias="phoneNumber", max_length=20)


class UserResponse(UserBase):
    id: uuid.UUID
    status: UserStatus
    is_active: bool = Field(alias="isActive")
    roles: list[RoleSummary] = Field(default_factory=list)
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class UserQuery(BaseModel):
    keyword: str | None = None
    role: str | None = None
    department_id: uuid.UUID | None = Field(default=None, alias="departmentId")
    lab_id: uuid.UUID | None = Field(default=None, alias="labId")
    status: UserStatus | None = None
