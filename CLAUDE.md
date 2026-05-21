# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LIMS (Laboratory Information Management System / 實驗室資訊管理系統) — a cloud-native web app for semiconductor fab lab management. It tracks work orders, WIP, machine status, approvals, alerts, and notifications.

Five-person student team, each owning a vertical slice of the business flow. See `docs/team_work_split.md` for the per-member split and `docs/development_standards.md` for shared conventions.

## Stack (locked in by the team, 2026-05-20)

- **Frontend**: TypeScript + React + **Next.js 16** (App Router) + Tailwind v4 plumbing
- **Backend**: **Python 3.12 + FastAPI** + uvicorn + Pydantic v2
- **DB**: **PostgreSQL** via docker-compose, SQLAlchemy 2.0 (async) + Alembic migrations
- **Background jobs**: **Celery 5 + Redis 7** (Celery Beat for scheduled tasks, e.g. alert escalation)
- **Realtime push**: SSE via `sse-starlette` (dashboard + notifications); Redis pub/sub as the bridge across workers
- **Auth**: JWT in httpOnly cookie, `python-jose` + `passlib[bcrypt]`

## Development Commands

```bash
# Frontend (port 3000)
cd frontend && npm run dev

# Backend (port 8000) — local dev (Postgres + Redis assumed already running)
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Celery worker (in another shell)
cd backend && source venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info

# Celery Beat scheduler (in another shell)
celery -A app.core.celery_app beat --loglevel=info

# Full stack via Docker
docker compose up         # backend + frontend + postgres + redis + celery
docker compose --profile tools up    # also brings up pgAdmin
docker compose down
docker compose build
```

## Lint / Test

```bash
# Backend
cd backend
ruff check .                # lint
ruff format --check .       # format check (use --write to fix)
mypy app                    # type check
pytest                      # run tests
pytest --cov=app            # with coverage

# Frontend
cd frontend
npm run lint
npm test                    # vitest
npx playwright test         # E2E (single demo-flow test)
```

## Architecture

### Frontend (`frontend/`)

Next.js 16 App Router, React 19, TypeScript.

> **IMPORTANT**: Next.js 16 has breaking API changes from earlier versions. Before writing Next.js-specific code, read the relevant guide in `frontend/node_modules/next/dist/docs/`. Do not assume behavior from Next.js 13/14/15 training data.

- `app/layout.tsx` — root layout: mounts persistent `<Sidebar>` and `<main>` content area
- `app/page.tsx` — default route (`/`), the supervisor dashboard
- `app/globals.css` — CSS custom properties for the dark theme; all color/surface tokens live here
- `components/Sidebar.tsx` — collapsible left nav; defines the full route tree
- `components/ui/KpiCard.tsx` — metric card with colored top-bar accent
- `components/ui/Chip.tsx` — status badge; accepts a `ChipType` union

**Styling convention**: Components use inline `style` props with CSS variable references (e.g. `var(--blue)`, `var(--s1)`), **not** Tailwind utility classes. Keep this consistent when adding new UI.

**Data layer**: TanStack Query (`useQuery`/`useMutation`) + an `axios` instance with `withCredentials: true` for cookie auth. API clients live in `src/services/*-api.ts`.

**Shared constants**: `src/constants/enums.ts` is auto-generated from `backend/app/common/enums/*.py` via `scripts/sync_enums.py` — do not edit by hand. Display labels live in `src/constants/status-labels.ts`.

### Backend (`backend/`)

FastAPI + Python 3.12, uvicorn ASGI, modular MVC under `app/modules/`. Entry: `app.main:app`. Runs on port 8000. Frontend expects it at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000/api`; baked at build time via Docker `build.args`).

```
backend/app/
  main.py              # FastAPI factory + lifespan + middleware
  core/
    config.py          # Pydantic BaseSettings (env-driven)
    database.py        # async engine + AsyncSession dependency
    security.py        # JWT + bcrypt
    celery_app.py      # Celery factory + beat schedule
  common/
    enums/             # All shared status enums (str+Enum)
    schemas/           # ApiResponse, PageResponse, ErrorResponse
    dependencies/      # get_current_user, require_permission(code)
    errors.py
    middleware/
  modules/
    auth/ users/ roles/ system_settings/ labs/ departments/
    storage_locations/ files/ audit_logs/ issues/ notifications/
    dashboard/ master_data/      # owned by 組員 E
    orders/                       # 組員 A
    samples/ wips/                # 組員 B
    machines/ recipes/ schedules/ dispatches/    # 組員 C
    experiment_runs/ reports/     # 組員 D
  db/
    base.py            # DeclarativeBase + TimestampMixin
    models/            # SQLAlchemy models per resource
  workers/             # Celery tasks (escalation, email_sender)
```

Each module follows the same shape: `router.py` (FastAPI APIRouter — thin), `service.py` (business logic), `repository.py` (async DB queries), `schemas.py` (Pydantic DTOs), `dependencies.py` (FastAPI `Depends`).

**Response convention** (`app/common/schemas/`):
- Success: `{ "data": ..., "message": "success" }`
- List: `{ "items": [...], "page": 1, "pageSize": 20, "total": 0 }`
- Error: `{ "error": { "code": "VALIDATION_ERROR", "message": "..." } }`

### Background jobs

Celery tasks live under `app/workers/`. Beat schedules are configured in `app/core/celery_app.py`. The escalation worker scans open issues every 60s, bumps `escalation_level` per `system_settings.alertRules`, and enqueues email + in-app notifications.

### Realtime push

SSE endpoints (`/api/dashboard/stream`, `/api/notifications/stream`) hold one connection per logged-in client and forward events from Redis pub/sub. Other Services publish to Redis on state changes; SSE handlers fan out.

### CI (`.github/workflows/ci.yml`) — runs on push/PR to `main`

- Backend: `ruff check && ruff format --check && mypy app && pytest`
- Frontend: `npm ci && npm run lint && npm run build && npm test`
- Docker compose build smoke test

## Routes

The Sidebar (`frontend/components/Sidebar.tsx`) defines these routes. Most pages exist as placeholder stubs (`components/ui/PlaceholderPage.tsx`) until each member fills them in.

| Section | Route | Owner | Purpose |
|---|---|---|---|
| Overview | `/` | E | Supervisor dashboard |
| 委託流程 | `/orders` | A | Work order CRUD |
| | `/approve` | A | Supervisor approval |
| | `/sample` | B | Sample receiving |
| | `/wip` | B | WIP / 分貨 |
| 執行與機台 | `/dispatch` | C | Dispatch + scheduling |
| | `/machine` | C | Machine management |
| | `/recipe` | C | Recipe management |
| | `/transfer` | B | Sample transfer |
| 結案與倉儲 | `/storage` | D | Storage / pickup |
| | `/issues` | E | 異常 / 告警 / 中止申請 |
| | `/notifications` | E | Notification center |
| 系統 | `/account` | E | Users / roles |
| | `/config` | E | System settings |
| | `/login` | E | Login page |

## Subagent delegation (do this by default)

Specialized subagents are registered under `.claude/agents/` (project-scoped) and `~/.claude/agents/` (user-scoped). **Default to delegating implementation work to them** rather than writing code inline — the agents are tuned for this project, they build their own per-agent memory, and the workflow naturally inserts a code-review checkpoint before "done".

| Trigger | Agent | Notes |
|---|---|---|
| FastAPI / Python / SQLAlchemy / pydantic / Celery work under `backend/` | `backend-developer` | New endpoints, services, migrations, workers, models. |
| Next.js / React / TS / styling work under `frontend/` | `frontend-developer` | New pages, components, hooks, contexts, API clients. |
| New tests, test fixtures, pytest/vitest/Playwright, or CI test wiring | `software-testing-engineer` | Tests live under `backend/tests/` and `frontend/` (vitest TBD). |
| `.github/workflows/*`, `Dockerfile`, `docker-compose.yml`, deployment | `devops-engineer` | Container plumbing + CI/CD. |
| Just finished a non-trivial change (proactive) | `lims-code-reviewer` | **Mandatory review checkpoint** before claiming work is done. |
| Need a second pass after `lims-code-reviewer` | `code-reviewer` | Project-agnostic deep review. |
| Need to understand architecture / trace a flow before changing it | `code-analyzer` | Especially for cross-module work or unfamiliar areas. |
| "Where is X defined / referenced?" | `Explore` | Faster than running 3+ greps yourself. |
| Multi-file change with non-obvious strategy | `Plan` | Before touching files. |

**Inline execution is only OK for:** 1–3 line edits, doc/config tweaks, reading files for context, replying to clarifying questions, or retrying classifier-blocked operations.

**Workflow:** delegate → review with `lims-code-reviewer` → only then mark the task complete.

## Docs

- `docs/total.md` — full cross-module overview
- `docs/flow.md` — canonical state machines (Order, WIP, Issue, etc.)
- `docs/team_work_split.md` — per-member ownership
- `docs/development_standards.md` — testing, PR, docs, integration standards
- `docs/naming_and_class_conventions.md` — naming rules for files, classes, APIs, DB
- `docs/frontend_backend_structure.md` — directory layout + dev notes
- `docs/integration_contract.md` — owned by E; the single source of truth for shared enums, response helpers, auth dependencies, and the "how to add your module" guide
- `docs/{role,system_setting,warn,dashboard}.md` — E's module specs
- `docs/{order_management,sample_management,machine_recipe,schedule,experiment_execute,result_manage}.md` — A/B/C/D module specs
