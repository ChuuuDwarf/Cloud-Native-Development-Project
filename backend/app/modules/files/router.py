"""HTTP routes for /api/files. Phase 2."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("/{file_id}")
async def get_file(file_id: str) -> dict:
    return {"data": {"id": file_id}, "message": "Phase 2 — files not yet implemented"}
