"""HTTP routes for /api/system-settings. Phase 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/system-settings", tags=["SystemSettings"])


@router.get("")
async def get_settings() -> dict:
    return {"data": {}, "message": "Phase 2 — system settings not yet implemented"}
