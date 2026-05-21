"""HTTP routes for /api/notifications. Phase 3."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("")
async def list_notifications() -> dict:
    return {
        "items": [],
        "total": 0,
        "message": "Phase 3 — notifications not yet implemented",
    }
