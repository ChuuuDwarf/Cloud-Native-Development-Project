"""Pydantic schemas for the supervisor dashboard.

Single endpoint ``GET /api/dashboard`` returns one snapshot DTO so the
frontend can paint every widget from one round-trip — no waterfall of
small calls. Lab scope is applied server-side per the caller's role.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.enums import Severity


class IssuesSummary(BaseModel):
    total_open: int = Field(alias="totalOpen")
    by_severity: dict[str, int] = Field(alias="bySeverity")
    created_today: int = Field(alias="createdToday")
    escalated_today: int = Field(alias="escalatedToday")

    model_config = {"populate_by_name": True}


class LabBreakdown(BaseModel):
    lab_id: UUID = Field(alias="labId")
    lab_code: str = Field(alias="labCode")
    lab_name: str = Field(alias="labName")
    open_issues: int = Field(alias="openIssues")
    escalated_issues: int = Field(alias="escalatedIssues")

    model_config = {"populate_by_name": True}


class RecentEscalation(BaseModel):
    id: UUID
    title: str
    severity: Severity
    escalation_level: int = Field(alias="escalationLevel")
    lab_id: UUID = Field(alias="labId")
    updated_at: datetime = Field(alias="updatedAt")

    model_config = {"populate_by_name": True}


class DashboardSnapshot(BaseModel):
    """All widgets in one DTO. Scoped to the caller's lab visibility."""

    issues: IssuesSummary
    unread_notifications: int = Field(alias="unreadNotifications")
    # Always populated. For non-admins it's a single-element list (their own lab);
    # for admin it contains every lab — that's the only role that needs the
    # cross-lab leaderboard.
    by_lab: list[LabBreakdown] = Field(alias="byLab")
    recent_escalations: list[RecentEscalation] = Field(alias="recentEscalations")

    model_config = {"populate_by_name": True}
