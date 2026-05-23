"""HTTP routes for /api/storage-locations. Phase 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/storage-locations", tags=["StorageLocations"])


@router.get("")
async def list_storage_locations() -> dict:
    return {
        "items": [],
        "total": 0,
        "message": "Phase 2 — storage locations not yet implemented",
    }
