"""HTTP routes for /api/labs. Phase 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/labs", tags=["Labs"])


@router.get("")
async def list_labs() -> dict:
    return {"items": [], "total": 0, "message": "Phase 2 — labs not yet implemented"}
