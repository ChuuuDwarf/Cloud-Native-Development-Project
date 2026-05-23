"""HTTP routes for /api/issues. Phase 3."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/issues", tags=["Issues"])


@router.get("")
async def list_issues() -> dict:
    return {"items": [], "total": 0, "message": "Phase 3 — issues not yet implemented"}
