"""HTTP routes for /api/samples. Owned by 組員 B."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/samples", tags=["Samples"])


@router.get("")
async def list_samples() -> dict:
    return {"items": [], "total": 0, "message": "組員 B: implement samples module"}
