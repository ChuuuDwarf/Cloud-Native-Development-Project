# LIMS Integration Contract

> Owner: **組員 E**. This is the single source of truth for the conventions every member must follow so the 5 modules stitch together cleanly at demo time.
>
> Stack is locked: **FastAPI · SQLAlchemy 2.0 (async) · Alembic · Celery + Redis · PostgreSQL · Next.js + TanStack Query**. See `CLAUDE.md` for commands.

---

## 1. Where things live

### Backend

```
backend/app/
  core/              # config, database, security, celery_app, logging
  common/
    enums/           # ALL shared status enums — add new ones here
    schemas/         # ApiResponse[T] / PageResponse[T] / ErrorResponse
    dependencies/    # get_current_user, require_permission(code), get_pagination
    middleware/      # request_id, request_logger
    errors.py        # AppError + ValidationError / NotFoundError / etc.
  modules/<name>/    # router.py, service.py, repository.py, schemas.py, dependencies.py
  db/
    base.py          # Base + TimestampMixin (import these in your models)
    models/          # one file per resource; re-export in __init__.py
  workers/           # Celery tasks
```

Reference module to copy: `app/modules/users/`.

### Frontend

```
frontend/
  src/
    api/             # httpClient.ts (axios + withCredentials)
    services/        # per-module API clients (auth-api.ts, user-api.ts, ...)
    contexts/        # AuthContext, NotificationContext
    constants/
      enums.ts       # AUTO-GENERATED — do not edit
      status-labels.ts  # hand-written Chinese display labels
    hooks/           # useUsers, useDashboard, ...
    components/<area>/   # per-module UI bits
  app/<route>/page.tsx   # Next.js App Router pages
  components/Sidebar.tsx, components/ui/{KpiCard,Chip,PlaceholderPage}.tsx
```

---

## 2. Response envelopes

Use the helpers from `app.common.schemas`:

```python
from app.common.schemas import ApiResponse, PageResponse, ErrorResponse

@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(...) -> ApiResponse[UserResponse]:
    return ApiResponse(data=UserResponse.model_validate(user))

@router.get("", response_model=PageResponse[UserResponse])
async def list_users(...) -> PageResponse[UserResponse]:
    return PageResponse(items=..., page=1, pageSize=20, total=...)
```

Errors propagate via `AppError` subclasses (`NotFoundError`, `ValidationError`, etc.) — the global exception handler in `app/main.py` wraps them into `{ "error": { "code": "...", "message": "..." } }`.

---

## 3. Auth & permissions

Every protected endpoint takes a permission dependency:

```python
from app.common.dependencies import CurrentUser, require_permission

@router.post("/orders", dependencies=[Depends(require_permission("orders:create"))])
async def create_order(
    payload: OrderCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    ...
): ...
```

Permission code convention: `<resource>:<verb>` — `users:create`, `orders:approve`, `system_settings:update`, etc. E maintains the canonical list in the `permissions` seed.

**Phase 0**: `get_current_user` returns a stub admin if no cookie present, so you can build modules without auth blocking you. **Phase 1** swaps this for the real JWT + DB lookup. Your code should not need to change.

---

## 4. Shared enums

If you need a status value, **never invent it inline** — add it under `app/common/enums/` and re-export in `app/common/enums/__init__.py`, then run:

```bash
python scripts/sync_enums.py
```

This regenerates `frontend/src/constants/enums.ts` so the FE has matching string-literal types. Add the Chinese display label to `frontend/src/constants/status-labels.ts`.

Naming: `PascalCase` class name, `snake_case` string values. E.g. `OrderStatus.PENDING_APPROVAL = "pending_approval"`.

---

## 5. Master data — single source of dropdowns

E owns `GET /api/master-data`. It returns every shared enum + lookup table (`roles`, `permissions`, `labs`, `departments`, `storageLocations`, `experimentItems`, all status enums) in one response. Frontend pages must call this on mount (cached by TanStack Query) rather than fetching individual endpoints for dropdown data.

If you need a new master-data field, **open a PR adding it to `app/modules/master_data/router.py` and notify E**.

---

## 6. Adding a new SQLAlchemy model

1. Create `app/db/models/<resource>.py`
2. Inherit `Base, TimestampMixin` from `app.db.base`
3. Use `UUID(as_uuid=True)` primary keys (`default=uuid.uuid4`)
4. FK columns reference `users.id`, `labs.id`, `departments.id` (all owned by E) — these tables exist after Alembic migration 0001
5. Re-export your model in `app/db/models/__init__.py`
6. Generate migration:
   ```bash
   alembic revision --autogenerate -m "0XXX <letter> <description>"
   ```
   where `<letter>` is your member letter (`a` for orders, `b` for samples/wips, `c` for machines/recipes/schedules/dispatches, `d` for experiment_runs/reports, `e` for E's modules)
7. Inspect the generated migration before running `alembic upgrade head`
8. PR with both the model + migration

---

## 7. Adding a new module

Copy `app/modules/users/` — it has the canonical 5-file shape:

```
modules/<name>/
  __init__.py
  router.py        # APIRouter, prefix="/api/<resource>", tags=["<Resource>"]
  schemas.py       # XCreate / XUpdate / XResponse / XQuery
  service.py       # business logic; orchestrates Repository + AuditLogService
  repository.py    # async DB queries; takes AsyncSession
  dependencies.py  # get_<resource>_service(session) factory
```

Then mount in `app/routes.py` by:
1. `from app.modules.<name>.router import router as <name>_router`
2. Append to `ALL_ROUTERS`

---

## 8. API path & field conventions

| Item | Rule |
|---|---|
| Resource path | plural, kebab-case: `/api/orders`, `/api/storage-locations` |
| ID path | `/api/{resource}/{id}` |
| Flow action | `/api/{resource}/{id}/actions` with `{ "action": "approve", "reason": "...", "comment": "..." }` |
| Request fields | `camelCase` (Pydantic `populate_by_name=True` + `alias`) |
| Response fields | `camelCase` |
| DB columns | `snake_case` |
| Enum values | `snake_case` strings |

Don't invent verb-routes (`POST /api/createOrder`) — use the flow-action pattern.

---

## 9. Audit log

Every state-changing Service must record an audit row:

```python
from app.db.models import AuditLog
from app.common.enums import AuditTargetType

audit = AuditLog(
    actor_id=current_user.id,
    action="approve",
    target_type=AuditTargetType.ORDER,
    target_id=str(order.id),
    before_data={"status": "pending_approval"},
    after_data={"status": "approved"},
)
session.add(audit)
```

A helper `AuditLogService.record(...)` will land in Phase 2.

---

## 10. Notifications + alerts

When your module detects something a user should know about:

```python
from app.modules.notifications.service import NotificationService

await NotificationService(session).notify(
    user_ids=[supervisor_id],
    title="新委託單待簽核",
    body=f"{order.order_no} 由 {applicant.name} 送出",
    target_type="order",
    target_id=str(order.id),
)
```

`NotificationService` decides per-channel delivery based on `system_settings.notificationRules` and enqueues `send_notification_email` Celery tasks for email channels. **Phase 3** implements this; for Phase 0/1 you can call it freely — it's a no-op stub.

For long-running anomalies (machine fault, overdue case) **create an Issue** instead — `POST /api/issues` — and the auto-escalation Celery Beat task will handle reminders per `system_settings.alertRules`.

---

## 11. Real-time (SSE)

Frontend opens `GET /api/notifications/stream` once per session via `NotificationContext`. Backend services that should trigger UI refresh just publish to Redis:

```python
await redis_client.publish("notifications", json.dumps({"user_id": ..., "kind": "..."}))
```

The SSE endpoint fans out to subscribed clients. **Phase 3** implements the Redis bridge; for Phase 0/1 publishes are no-ops.

---

## 12. Tests

Per `docs/development_standards.md` §4. Minimum per module:
- Service unit tests for happy path + 1 failure case per Service method
- API tests using `httpx.AsyncClient` for each endpoint (status code + envelope shape + a permission-denied case)
- One state-machine test covering an invalid transition

E owns `tests/e2e/full_flow.spec.ts` (Playwright) that drives the full Order → Closeout flow through every module. You don't have to write E2E tests — but your UI must support being driven by the data-attributes E uses in the spec.

---

## 13. Migration filename convention

Avoids collisions when multiple members generate migrations in the same week:

```
alembic/versions/<ordinal>_<member-letter>_<short_description>.py
```

Examples:
- `0001_e_initial_e_tables.py` (E's first migration)
- `0010_a_orders.py` (A's first migration)
- `0020_b_samples_wips.py` (B's first migration)

The `<ordinal>` keeps lexical order; if two PRs are open with the same ordinal, rebase and bump.

---

## 14. Open questions for cross-module sync

These need answers before Phase 1 ships. E will track on the team channel:

1. **A**: include `priority` and `due_date` on `Order` for `dashboard.overdueCases`?
2. **C**: time-bucketing granularity for `dashboard.machineFutureLoad`?
3. **D**: exact `ReportStatus` values used in your queries (so `dashboard.reportStatusCounts` filters correctly)?
4. **All**: confirm `users.id` FK can be enforced from your tables (E ships `users` table first)?
5. **All**: who creates the demo seed data? E proposes E does, with peers contributing module-specific fixtures.
