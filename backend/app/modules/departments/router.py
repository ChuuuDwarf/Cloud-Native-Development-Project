"""HTTP routes for /api/departments. Phase 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/departments", tags=["Departments"])


@router.get("")
async def list_departments() -> dict:
    return {"items": [], "total": 0, "message": "Phase 2 — departments not yet implemented"}
