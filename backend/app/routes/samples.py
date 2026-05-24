from __future__ import annotations

from fastapi import APIRouter

from app.core.order_errors import not_found
from app.data.master_data import SAMPLES
from app.schemas.order import ApiResponse

router = APIRouter(prefix="/api/samples", tags=["Samples"])


@router.get("")
def list_samples() -> ApiResponse:
    return ApiResponse(data=SAMPLES)


@router.get("/{sample_id}")
def get_sample(sample_id: str) -> ApiResponse:
    sample = next((item for item in SAMPLES if item["id"] == sample_id), None)
    if sample is None:
        raise not_found("Sample not found")
    return ApiResponse(data=sample)
