"""Pydantic schemas for the issues module.

Wire format is camelCase (per integration_contract.md §6.1), Python uses
snake_case. The translation lives in per-field ``Field(alias=...)`` calls,
matching the style used by ``app/schemas/order.py``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.common.enums import IssueStatus, IssueType, Severity


class IssueCreate(BaseModel):
    """Request body for ``POST /api/issues``.

    Server-controlled fields (``id``, ``status``, ``escalation_level``,
    ``handled_at``, ``closed_at``, timestamps) are deliberately absent —
    callers should not be able to set them.
    """

    type: IssueType
    target_type: str = Field(alias="targetType", min_length=1, max_length=40)
    target_id: str = Field(alias="targetId", min_length=1, max_length=80)
    lab_id: UUID = Field(alias="labId")
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    severity: Severity = Severity.MEDIUM
    assigned_to: UUID | None = Field(default=None, alias="assignedTo")

    model_config = {"populate_by_name": True}


class IssueUpdate(BaseModel):
    """
    PATCH body for issues
    """

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    severity: Severity | None = None
    assigned_to: UUID | None = Field(default=None, alias="assignedTo")

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def at_least_one_field(self) -> IssueUpdate:
        if not any(
            v is not None for v in (self.title, self.description, self.severity, self.assigned_to)
        ):
            raise ValueError("at least one update field is required")
        return self


class IssueRead(BaseModel):
    """
    Get body for issues
    """

    id: UUID
    status: IssueStatus
    escalation_level: int = Field(alias="escalationLevel")
    next_escalation_time: datetime | None = Field(alias="nextEscalationTime")
    handled_at: datetime | None = Field(alias="handledAt")
    closed_at: datetime | None = Field(alias="closedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    type: IssueType
    target_type: str = Field(alias="targetType")
    target_id: str = Field(alias="targetId")
    lab_id: UUID = Field(alias="labId")
    title: str
    description: str
    severity: Severity
    assigned_to: UUID | None = Field(alias="assignedTo")

    model_config = {"populate_by_name": True, "from_attributes": True}


class IssueListParams(BaseModel):
    """Query parameters for ``GET /api/issues``."""

    status: IssueStatus | None = Field(default=None)
    severity: Severity | None = Field(default=None)
    type: IssueType | None = Field(default=None)
    assigned_to: UUID | None = Field(default=None, alias="assignedTo")
    target_type: str | None = Field(default=None, alias="targetType")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize")

    model_config = {"populate_by_name": True}
