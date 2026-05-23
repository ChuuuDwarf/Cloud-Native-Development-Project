"""HTTP routes for /api/audit-logs. Phase 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/audit-logs", tags=["AuditLogs"])


@router.get("")
async def list_audit_logs() -> dict:
    return {"items": [], "total": 0, "message": "Phase 2 — audit logs not yet implemented"}
