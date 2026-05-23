from __future__ import annotations

from fastapi import APIRouter, Query

from app.data.master_data import DEPARTMENTS, EXPERIMENTS, LABS
from app.schemas.order import ApiResponse

router = APIRouter(prefix="/api", tags=["Master Data"])


# @router.get("/master-data")
# def get_master_data() -> ApiResponse:
#     return ApiResponse(
#         data={
#             "departments": DEPARTMENTS,
#             "labs": LABS,
#             "experiments": EXPERIMENTS,
#             "statuses": [{"value": item.value, "label": item.value} for item in OrderStatus],
#             "priorities": [{"value": item.value, "label": item.value} for item in PriorityLevel],
#         }
#     )


@router.get("/labs")
def get_labs() -> ApiResponse:
    return ApiResponse(data=LABS)


@router.get("/departments")
def get_departments() -> ApiResponse:
    return ApiResponse(data=DEPARTMENTS)


@router.get("/experiments")
def get_experiments(lab_id: str | None = Query(default=None, alias="labId")) -> ApiResponse:
    experiments = EXPERIMENTS
    if lab_id:
        experiments = [item for item in experiments if item["labId"] == lab_id]
    return ApiResponse(data=experiments)
