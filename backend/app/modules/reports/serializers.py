"""camelCase serializers for reports responses.

Ported from Role D's flat ``app/models.py`` (``report_dict``).
"""

from __future__ import annotations

from datetime import datetime

from app.db.models import Report, ReportAttachment, ReportTemplate, ReportVersion

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def fmt(dt: datetime | None) -> str | None:
    return dt.strftime(TIME_FMT) if dt else None


def version_dict(v: ReportVersion) -> dict:
    return {
        "version": v.version,
        "status": v.status,
        "at": fmt(v.at),
        "by": v.actor,
        "note": v.note,
    }


def attachment_dict(a: ReportAttachment) -> dict:
    return {"name": a.name, "at": fmt(a.at)}


def report_dict(r: Report) -> dict:
    return {
        "reportId": r.report_id,
        "orderId": r.order_id,
        "wipId": r.wip_id,
        "title": r.title,
        "summary": r.summary,
        "conclusion": r.conclusion,
        "status": r.status,
        "experimentData": r.experiment_data or {},
        "createdAt": fmt(r.created_at),
        "createdBy": r.created_by,
        "attachments": [attachment_dict(a) for a in r.attachments],
        "versions": [version_dict(v) for v in r.versions],
    }


def template_dict(t: ReportTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "orderId": t.order_id,
        "summary": t.summary,
        "conclusion": t.conclusion,
        "createdBy": t.created_by,
        "createdAt": fmt(t.created_at),
    }
