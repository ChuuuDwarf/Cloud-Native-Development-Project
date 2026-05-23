"""HTTP routes for /api/dashboard. Phase 4."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("")
async def get_dashboard() -> dict:
    return {"data": {}, "message": "Phase 4 — dashboard not yet implemented"}
