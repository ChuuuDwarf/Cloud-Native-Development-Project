"""HTTP routes for /api/schedules. Owned by 組員 C."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/schedules", tags=["Schedules"])


@router.get("")
async def list_schedules() -> dict:
    return {"items": [], "total": 0, "message": "組員 C: implement schedules module"}
