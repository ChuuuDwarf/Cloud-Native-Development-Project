import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.repos import wip_repo

fallback_user = {
    "id": "system",
    "name": "系統",
    "role": "system_admin",
    "role_name": "系統管理者",
    "department": None,
    "lab_name": None,
    "email": "",
}


WIP_ORDER_GUARD_MESSAGE = "目前尚未輪到此 WIP，請先完成前一站實驗或交接流程"
NO_PENDING_DEPENDENCY_MESSAGE = "No pending dependency item"
DEPENDENCY_REASON_LOWEST_MACHINE_UTILIZATION = "lowest_machine_utilization"
MISSING_MACHINE_UTILIZATION_SCORE = 1_000_000


async def get_active_user(
    db: AsyncSession,
    request: Request | None = None,
):
    try:
        from app.services.workflow_helpers import resolve_current_user

        return await resolve_current_user(db, request)
    except Exception:
        await db.rollback()
        return fallback_user


def get_user_lab(user: dict):
    return user.get("lab_name") or user.get("department")


def lab_location(lab_name: str | None, area: str):
    if not lab_name:
        return area

    lab_name = lab_name.strip()

    if lab_name.endswith(area):
        return lab_name

    return f"{lab_name} {area}"


def experiment_temp_location(lab_name: str | None):
    return lab_location(lab_name, "實驗暫存區")


def machine_location(lab_name: str | None):
    return lab_location(lab_name, "機台區")


def is_factory_role(role: str | None) -> bool:
    return role == "plant_user"


def is_lab_role(role: str | None) -> bool:
    return role in ("lab_engineer", "lab_supervisor")


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError) as err:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        ) from err


def build_wip_visibility_filter(current_user: dict):
    role = current_user.get("role")
    where_clauses: list[str] = []
    params: dict[str, object] = {}

    if role in ("system_admin", "lab_supervisor"):
        return where_clauses, params

    if is_factory_role(role):
        where_clauses.append("s.applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if is_lab_role(role):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        params["current_lab"] = current_lab

        where_clauses.append(
            """
            (
                w.lab_name = :current_lab
                OR EXISTS (
                    SELECT 1
                    FROM transfers t
                    WHERE t.target_type = 'sample'
                      AND t.target_id = w.sample_id
                      AND t.to_lab = :current_lab
                )
            )
            """
        )

        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


def build_wip_flow_visibility_filter(current_user: dict):
    """給 transfer flow 使用的 WIP 查詢範圍。

    一般 WIP 管理頁只看自己 Lab 的 WIP。
    但 transfer flow 需要判斷同一個 sample 底下所有 Lab 的 WIP 是否完成。
    """

    role = current_user.get("role")
    where_clauses: list[str] = []
    params: dict[str, object] = {}

    if role == "system_admin":
        return where_clauses, params

    if is_factory_role(role):
        where_clauses.append("s.applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if is_lab_role(role):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        params["current_lab"] = current_lab
        params["current_lab_prefix"] = f"{current_lab}%"

        where_clauses.append(
            """
            (
                s.current_location LIKE :current_lab_prefix
                OR EXISTS (
                    SELECT 1
                    FROM wips related_wips
                    WHERE related_wips.sample_id = w.sample_id
                      AND related_wips.lab_name = :current_lab
                )
                OR EXISTS (
                    SELECT 1
                    FROM transfers sample_transfers
                    WHERE sample_transfers.target_type = 'sample'
                      AND sample_transfers.target_id = s.id
                      AND (
                          sample_transfers.from_lab = :current_lab
                          OR sample_transfers.to_lab = :current_lab
                      )
                )
                OR EXISTS (
                    SELECT 1
                    FROM transfers wip_transfers
                    WHERE wip_transfers.target_type = 'wip'
                      AND wip_transfers.target_id = w.id
                      AND (
                          wip_transfers.from_lab = :current_lab
                          OR wip_transfers.to_lab = :current_lab
                      )
                )
            )
            """
        )

        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


async def can_view_wip(
    current_user: dict,
    wip: dict,
    sample: dict | None = None,
    db: AsyncSession | None = None,
) -> bool:
    role = current_user.get("role")

    if role in ("system_admin", "lab_supervisor"):
        return True

    if is_factory_role(role):
        return bool(sample and sample.get("applicant_name") == current_user.get("name"))

    if is_lab_role(role):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            return False

        if wip.get("lab_name") == current_lab:
            return True

        if db is None:
            return False

        sample_id = wip.get("sample_id")
        if sample_id is None:
            return False

        return await wip_repo.has_transfer_to_lab_for_sample(
            db,
            sample_id=str(sample_id),
            current_lab=current_lab,
        )

    return False


def can_manage_wip(current_user: dict, wip: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if not is_lab_role(role):
        return False

    current_lab = get_user_lab(current_user)

    # 操作 WIP 以 WIP 歸屬 Lab 為準，不用 current_location。
    return bool(current_lab and wip.get("lab_name") == current_lab)


async def get_wip_or_404(wip_id: str, db: AsyncSession):
    validate_uuid(wip_id, "wip_id")

    wip = await wip_repo.get_wip_by_id(db, wip_id=wip_id)

    if wip is None:
        raise HTTPException(status_code=404, detail="WIP not found")

    return wip


async def get_sample_by_id(sample_id: str, db: AsyncSession):
    validate_uuid(sample_id, "sample_id")

    return await wip_repo.get_sample_by_id(db, sample_id=sample_id)


def parse_requested_experiments(experiment_item: str | None) -> list[dict[str, str]]:
    if not experiment_item:
        return []

    experiments: list[dict[str, str]] = []

    for part in experiment_item.split("、"):
        part = part.strip()

        if ":" not in part:
            continue

        lab_name, item_name = part.split(":", 1)
        lab_name = lab_name.strip()
        item_name = item_name.strip()

        if lab_name and item_name:
            experiments.append({"lab_name": lab_name, "experiment_item": item_name})

    return experiments


def normalize_flow_value(value: str | None) -> str:
    return (value or "").strip().lower()


def parse_supported_items(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [part.strip() for part in stripped.split(",") if part.strip()]

        if isinstance(parsed, list):
            return [str(item) for item in parsed]

    return []


def normalize_dependency_item(item: dict) -> dict:
    return {
        **item,
        "target_group": item.get("target_group") or "G1",
        "target": int(item.get("target") or 1),
        "dependency_check": bool(item.get("dependency_check")),
    }


def select_pending_dependency_candidates(order_items: list[dict]) -> list[dict]:
    pending_by_group: dict[str, dict] = {}

    for raw_item in order_items:
        item = normalize_dependency_item(raw_item)
        if item["dependency_check"]:
            continue

        group = item["target_group"]
        current = pending_by_group.get(group)

        if current is None or (
            item["target"],
            str(item.get("created_at") or ""),
            int(item["id"]),
        ) < (
            current["target"],
            str(current.get("created_at") or ""),
            int(current["id"]),
        ):
            pending_by_group[group] = item

    return list(pending_by_group.values())


def machine_utilization_score(candidate: dict, machines: list[dict]) -> int:
    lab_values = {
        normalize_flow_value(candidate.get("lab_name")),
        normalize_flow_value(candidate.get("lab_code")),
        normalize_flow_value(candidate.get("lab_id")),
    }
    experiment_name = normalize_flow_value(candidate.get("experiment_name"))

    scores: list[int] = []
    for machine in machines:
        if normalize_flow_value(machine.get("lab")) not in lab_values:
            continue

        supported_items = {
            normalize_flow_value(item)
            for item in parse_supported_items(machine.get("supported_items"))
        }
        if experiment_name not in supported_items:
            continue

        try:
            scores.append(int(machine.get("utilization") or 0))
        except (TypeError, ValueError):
            scores.append(MISSING_MACHINE_UTILIZATION_SCORE)

    return min(scores) if scores else MISSING_MACHINE_UTILIZATION_SCORE


def select_dependency_candidate(candidates: list[dict], machines: list[dict]) -> dict:
    return sorted(
        candidates,
        key=lambda item: (
            machine_utilization_score(item, machines),
            item["target"],
            str(item.get("created_at") or ""),
            int(item["id"]),
        ),
    )[0]


async def claim_next_dependency_experiment(
    db: AsyncSession,
    sample_id: str,
    order_no: str | None = None,
) -> dict:
    # sample_id intentionally maps to order_items.sample_id (sample number) so the
    # next destination can be resolved before samples.id exists.
    sample_no = sample_id.strip()
    if not sample_no:
        raise HTTPException(status_code=400, detail="sampleId is required")

    normalized_order_no = order_no.strip() if order_no else None

    order_items = await wip_repo.list_dependency_order_items_for_sample(
        db,
        sample_no=sample_no,
        order_no=normalized_order_no,
    )
    if not order_items:
        raise HTTPException(status_code=404, detail="Dependency order items not found")

    candidates = select_pending_dependency_candidates(order_items)
    if not candidates:
        return {
            "success": True,
            "data": None,
            "message": NO_PENDING_DEPENDENCY_MESSAGE,
        }

    lab_names = sorted(
        {str(candidate.get("lab_name")) for candidate in candidates if candidate.get("lab_name")}
    )
    lab_codes = sorted(
        {
            str(candidate.get("lab_code") or candidate.get("lab_id"))
            for candidate in candidates
            if candidate.get("lab_code") or candidate.get("lab_id")
        }
    )
    machines = await wip_repo.list_machines_for_dependency_candidates(
        db,
        lab_names=lab_names,
        lab_codes=lab_codes,
    )

    for candidate in sorted(
        candidates,
        key=lambda item: (
            machine_utilization_score(item, machines),
            item["target"],
            str(item.get("created_at") or ""),
            int(item["id"]),
        ),
    ):
        claimed = await wip_repo.claim_order_item_dependency_check(
            db,
            order_item_id=int(candidate["id"]),
        )
        if claimed is None:
            continue

        await db.commit()
        return {
            "success": True,
            "data": {
                "orderItemId": candidate["id"],
                "orderNo": candidate.get("order_no") or normalized_order_no,
                "sampleId": sample_no,
                "sampleNo": sample_no,
                "labId": candidate.get("lab_id"),
                "labName": candidate.get("lab_name"),
                "experimentId": candidate.get("experiment_id"),
                "experimentName": candidate.get("experiment_name"),
                "targetGroup": candidate.get("target_group") or "G1",
                "target": candidate.get("target") or 1,
                "check": True,
                "reason": DEPENDENCY_REASON_LOWEST_MACHINE_UTILIZATION,
            },
        }

    await db.rollback()
    return {
        "success": True,
        "data": None,
        "message": NO_PENDING_DEPENDENCY_MESSAGE,
    }


def find_current_experiment_index(
    experiments: list[dict[str, str]],
    wip: dict,
) -> int | None:
    wip_lab = normalize_flow_value(wip.get("lab_name"))
    wip_experiment = normalize_flow_value(wip.get("experiment_item"))

    for index, experiment in enumerate(experiments):
        if (
            normalize_flow_value(experiment.get("lab_name")) == wip_lab
            and normalize_flow_value(experiment.get("experiment_item")) == wip_experiment
        ):
            return index

    return None


def is_same_experiment_wip(experiment: dict, wip: dict) -> bool:
    return normalize_flow_value(experiment.get("lab_name")) == normalize_flow_value(
        wip.get("lab_name")
    ) and normalize_flow_value(experiment.get("experiment_item")) == normalize_flow_value(
        wip.get("experiment_item")
    )


def build_ordered_wip_slots(
    experiments: list[dict[str, str]],
    wips: list[dict],
) -> list[dict]:
    unused_wips = list(wips)
    slots: list[dict] = []

    for experiment in experiments:
        matched_wip = None

        for index, candidate in enumerate(unused_wips):
            if is_same_experiment_wip(experiment, candidate):
                matched_wip = candidate
                unused_wips.pop(index)
                break

        slots.append(
            {
                "experiment": experiment,
                "wip": matched_wip,
            }
        )

    return slots


async def get_sample_wips_in_flow_order(sample_id: str, db: AsyncSession) -> list[dict]:
    return await wip_repo.list_sample_wips_in_flow_order(
        db,
        sample_id=sample_id,
    )


def find_wip_experiment_index_from_slots(
    slots: list[dict],
    wip_id: str | None,
) -> int | None:
    if not wip_id:
        return None

    for index, slot in enumerate(slots):
        slot_wip = slot.get("wip")

        if slot_wip and str(slot_wip.get("id")) == str(wip_id):
            return index

    return None


def find_first_incomplete_wip_slot(slots: list[dict]) -> dict | None:
    for slot in slots:
        slot_wip = slot.get("wip")

        if slot_wip and slot_wip.get("status") != "completed":
            return slot

    return None


def get_completable_wip_slots_for_current_segment(slots: list[dict]) -> list[dict]:
    completable_slots: list[dict] = []
    segment_lab = None
    segment_started = False

    for slot in slots:
        experiment = slot["experiment"]
        slot_lab = normalize_flow_value(experiment.get("lab_name"))
        slot_wip = slot.get("wip")

        if not segment_started:
            if slot_wip and slot_wip.get("status") == "completed":
                continue

            if slot_wip is None:
                return []

            segment_started = True
            segment_lab = slot_lab

        if slot_lab != segment_lab:
            break

        if slot_wip and slot_wip.get("status") != "completed":
            completable_slots.append(slot)

    return completable_slots


def get_creatable_wip_slots_for_current_segment(slots: list[dict]) -> list[dict]:
    creatable_slots: list[dict] = []
    segment_lab = None
    segment_started = False

    for slot in slots:
        experiment = slot["experiment"]
        slot_lab = normalize_flow_value(experiment.get("lab_name"))
        slot_wip = slot.get("wip")

        if not segment_started:
            if slot_wip and slot_wip.get("status") == "completed":
                continue

            segment_started = True
            segment_lab = slot_lab

        if slot_lab != segment_lab:
            break

        if slot_wip is None:
            creatable_slots.append(slot)

    return creatable_slots


def validate_wip_create_items_in_order(
    sample: dict,
    existing_wips: list[dict],
    requested_items: list[dict],
) -> None:
    experiments = parse_requested_experiments(sample.get("experiment_item"))

    if not experiments:
        return

    slots = build_ordered_wip_slots(experiments, existing_wips)
    creatable_slots = get_creatable_wip_slots_for_current_segment(slots)
    creatable_experiments = [slot["experiment"] for slot in creatable_slots]

    if len(requested_items) > len(creatable_experiments):
        raise HTTPException(
            status_code=400,
            detail=WIP_ORDER_GUARD_MESSAGE,
        )

    for index, item in enumerate(requested_items):
        if not is_same_experiment_wip(creatable_experiments[index], item):
            raise HTTPException(
                status_code=400,
                detail=WIP_ORDER_GUARD_MESSAGE,
            )


async def validate_wip_can_complete_in_order(
    db: AsyncSession,
    wip: dict,
) -> int | None:
    sample_id = wip.get("sample_id")
    if sample_id is None:
        return None

    sample = await get_sample_by_id(str(sample_id), db)
    if sample is None:
        return None

    experiments = parse_requested_experiments(sample.get("experiment_item"))
    if not experiments:
        return None

    sample_wips = await get_sample_wips_in_flow_order(sample["id"], db)
    slots = build_ordered_wip_slots(experiments, sample_wips)
    current_index = find_wip_experiment_index_from_slots(slots, wip.get("id"))

    if current_index is None:
        return find_current_experiment_index(experiments, wip)

    if wip.get("status") == "completed":
        return current_index

    completable_wip_ids = {
        str(slot["wip"]["id"])
        for slot in get_completable_wip_slots_for_current_segment(slots)
        if slot.get("wip")
    }

    if str(wip.get("id")) not in completable_wip_ids:
        raise HTTPException(
            status_code=400,
            detail=WIP_ORDER_GUARD_MESSAGE,
        )

    return current_index


async def complete_wip_sample_flow(
    db: AsyncSession,
    wip: dict,
    current_lab: str | None,
    operator_name: str,
    current_index: int | None = None,
) -> None:
    if not current_lab:
        return

    sample_id = wip.get("sample_id")
    if sample_id is None:
        return

    sample = await get_sample_by_id(str(sample_id), db)
    if sample is None:
        return

    experiments = parse_requested_experiments(sample.get("experiment_item"))
    if current_index is None:
        sample_wips = await get_sample_wips_in_flow_order(sample["id"], db)
        slots = build_ordered_wip_slots(experiments, sample_wips)
        current_index = find_wip_experiment_index_from_slots(slots, wip.get("id"))

    if current_index is None:
        current_index = find_current_experiment_index(experiments, wip)

    current_lab_temp_location = experiment_temp_location(current_lab)

    if current_index is None:
        await wip_repo.update_sample_status_and_location(
            db,
            sample_id=sample["id"],
            status="split",
            current_location=current_lab_temp_location,
        )
        return

    next_experiment = (
        experiments[current_index + 1] if current_index + 1 < len(experiments) else None
    )

    if next_experiment is None:
        await wip_repo.update_sample_status_and_location(
            db,
            sample_id=sample["id"],
            status="split",
            current_location=current_lab_temp_location,
        )

        await wip_repo.create_sample_history(
            db,
            sample_id=sample["id"],
            action="wip_completed_ready_to_notify_pickup",
            from_status=sample.get("status"),
            to_status="split",
            description=f"{current_lab} 完成 {wip.get('experiment_item')}，可通知使用者取件",
            operator_name=operator_name,
            lab_name=current_lab,
        )
        return

    next_lab = next_experiment["lab_name"]
    if normalize_flow_value(next_lab) == normalize_flow_value(current_lab):
        await wip_repo.update_sample_status_and_location(
            db,
            sample_id=sample["id"],
            status="split",
            current_location=current_lab_temp_location,
        )
        return

    await wip_repo.update_sample_status_and_location(
        db,
        sample_id=sample["id"],
        status="pending_transfer",
        current_location=current_lab_temp_location,
    )

    note = f"{current_lab} 完成 {wip.get('experiment_item')}，可交接至 {next_lab}"

    await wip_repo.create_sample_history(
        db,
        sample_id=sample["id"],
        action="wip_completed_pending_transfer",
        from_status=sample.get("status"),
        to_status="pending_transfer",
        description=note,
        operator_name=operator_name,
        lab_name=current_lab,
    )


async def update_sample_to_pending_transfer_if_ready(
    db: AsyncSession,
    sample_id: str,
    current_lab: str | None,
    next_location: str | None,
    operator_name: str,
    completed_wip: dict | None = None,
    completed_wip_index: int | None = None,
) -> None:
    if completed_wip is not None:
        await complete_wip_sample_flow(
            db=db,
            wip=completed_wip,
            current_lab=current_lab,
            operator_name=operator_name,
            current_index=completed_wip_index,
        )
        return

    completed_wip = await wip_repo.get_latest_completed_wip_for_lab(
        db,
        sample_id=sample_id,
        current_lab=current_lab,
    )

    if completed_wip is not None:
        await complete_wip_sample_flow(
            db=db,
            wip=completed_wip,
            current_lab=current_lab,
            operator_name=operator_name,
        )


async def list_wips(
    db: AsyncSession,
    current_user: dict,
    status: str | None = None,
    include_all_for_flow: bool = False,
):
    if include_all_for_flow:
        where_clauses, params = build_wip_flow_visibility_filter(current_user)
    else:
        where_clauses, params = build_wip_visibility_filter(current_user)

    if status:
        where_clauses.append("w.status = :status")
        params["status"] = status

    return await wip_repo.list_wips(
        db,
        where_clauses=where_clauses,
        params=params,
    )


async def get_wip_detail(
    db: AsyncSession,
    current_user: dict,
    wip_id: str,
):
    wip = await get_wip_or_404(wip_id, db)
    sample = await get_sample_by_id(wip["sample_id"], db)

    if not await can_view_wip(current_user, wip, sample, db):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this WIP",
        )

    return wip


async def list_wip_history(
    db: AsyncSession,
    current_user: dict,
    wip_id: str,
):
    wip = await get_wip_or_404(wip_id, db)
    sample = await get_sample_by_id(wip["sample_id"], db)

    if not await can_view_wip(current_user, wip, sample, db):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this WIP",
        )

    return await wip_repo.list_wip_history(db, wip_id=wip_id)


async def update_wip(
    db: AsyncSession,
    current_user: dict,
    wip_id: str,
    payload: dict,
):
    wip = await get_wip_or_404(wip_id, db)

    if not can_manage_wip(current_user, wip):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this WIP",
        )

    updated_wip = await wip_repo.update_wip_fields(
        db,
        wip_id=wip_id,
        lab_name=payload.get("lab_name"),
        experiment_item=payload.get("experiment_item"),
        priority=payload.get("priority"),
        current_location=payload.get("current_location"),
        note=payload.get("note"),
    )

    await db.commit()
    return updated_wip


def _get_wip_action_maps():
    status_map = {
        "send_to_schedule": "waiting_schedule",
        "mark_scheduled": "scheduled",
        "mark_dispatched": "dispatched",
        "start": "running",
        "pause": "paused",
        "resume": "running",
        "complete": "completed",
        "terminate": "terminated",
    }

    description_map = {
        "send_to_schedule": "WIP 送入待排程",
        "mark_scheduled": "WIP 標記為已排程",
        "mark_dispatched": "WIP 標記為已派工",
        "start": "WIP 開始執行，樣品移至機台區",
        "pause": "WIP 暫停",
        "resume": "WIP 恢復執行",
        "complete": "WIP 完成，樣品回到實驗暫存區",
        "terminate": "WIP 終止",
    }

    return status_map, description_map


def _build_wip_action_update_options(
    action: str,
    payload: dict,
    current_lab: str | None,
) -> dict:
    options: dict[str, object] = {
        "scheduled_at": False,
        "dispatched_at": False,
        "started_at": False,
        "completed_at": False,
        "terminated_at": False,
        "progress": None,
        "next_location": None,
    }

    if action == "mark_scheduled":
        options["scheduled_at"] = True

    if action == "mark_dispatched":
        options["dispatched_at"] = True

    if action == "start":
        options["started_at"] = True
        options["next_location"] = payload.get("current_location") or machine_location(current_lab)

    if action == "resume":
        options["next_location"] = payload.get("current_location") or machine_location(current_lab)

    if action == "complete":
        options["completed_at"] = True
        options["progress"] = 100
        options["next_location"] = payload.get("current_location") or experiment_temp_location(
            current_lab
        )

    if action == "terminate":
        options["terminated_at"] = True

    return options


async def handle_wip_action(
    db: AsyncSession,
    current_user: dict,
    wip_id: str,
    payload: dict,
):
    wip = await get_wip_or_404(wip_id, db)

    if not can_manage_wip(current_user, wip):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to operate this WIP",
        )

    current_lab = get_user_lab(current_user)
    action = payload.get("action")

    status_map, description_map = _get_wip_action_maps()

    if action not in status_map:
        raise HTTPException(
            status_code=400,
            detail=(
                "action must be one of: send_to_schedule, mark_scheduled, "
                "mark_dispatched, start, pause, resume, complete, terminate"
            ),
        )

    action = str(action)

    operator_name = payload.get("operator_name") or current_user.get("name")

    if not operator_name:
        raise HTTPException(
            status_code=400,
            detail="operator_name is required",
        )

    new_status = status_map[action]
    description = payload.get("description") or description_map[action]
    wip_flow_index = None

    if action == "complete":
        wip_flow_index = await validate_wip_can_complete_in_order(db, wip)

    update_options = _build_wip_action_update_options(
        action=action,
        payload=payload,
        current_lab=current_lab,
    )

    progress = update_options["progress"]
    next_location = update_options["next_location"]

    updated_wip = await wip_repo.update_wip_status(
        db,
        wip_id=wip_id,
        new_status=new_status,
        scheduled_at=bool(update_options["scheduled_at"]),
        dispatched_at=bool(update_options["dispatched_at"]),
        started_at=bool(update_options["started_at"]),
        completed_at=bool(update_options["completed_at"]),
        terminated_at=bool(update_options["terminated_at"]),
        progress=progress if isinstance(progress, int) else None,
        next_location=next_location if isinstance(next_location, str) else None,
    )

    if action in ("start", "resume", "complete"):
        next_location = update_options["next_location"]

        sample_id = wip.get("sample_id")
        if sample_id is None:
            raise HTTPException(status_code=400, detail="sample_id is required")

        sample_id = str(sample_id)

        if isinstance(next_location, str) and next_location:
            await wip_repo.update_sample_location(
                db,
                sample_id=sample_id,
                next_location=next_location,
            )

            await wip_repo.update_current_lab_wips_location(
                db,
                sample_id=sample_id,
                current_lab=current_lab,
                next_location=next_location,
            )

            if action == "complete":
                await update_sample_to_pending_transfer_if_ready(
                    db=db,
                    sample_id=sample_id,
                    current_lab=current_lab,
                    next_location=next_location,
                    operator_name=operator_name,
                    completed_wip=updated_wip,
                    completed_wip_index=wip_flow_index,
                )

    await wip_repo.create_wip_history(
        db,
        wip_id=wip_id,
        action=action,
        from_status=wip["status"],
        to_status=new_status,
        description=description,
        operator_name=operator_name,
    )

    await db.commit()
    return updated_wip
