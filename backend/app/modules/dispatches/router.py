"""HTTP routes for /api/dispatches. Owned by 組員 C."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/dispatches", tags=["Dispatches"])


@router.get("")
async def list_dispatches() -> dict:
    return {"items": [], "total": 0, "message": "組員 C: implement dispatches module"}
