# LIMS · 雲原生實驗室資訊管理系統

> Cloud-Native Laboratory Information Management System — NYCU 雲原生課程學期專案。
> 涵蓋委託單建立 → 主管簽核 → 收樣分貨 → WIP/派工排程 → 實驗執行 → 結果與報告 → 取件結案 → 主管儀表板 / 告警 / 通知 的完整流程。

5 人分工請看 [`docs/team_work_split.md`](docs/team_work_split.md)，跨組整合規範請看 [`docs/integration_contract.md`](docs/integration_contract.md)。Claude Code 操作慣例與 subagent 對應請看 [`CLAUDE.md`](CLAUDE.md)。

---

## Quick start

從零到「在 browser 看到 dashboard」的 5 個步驟。

```bash
# 1. 啟動 Postgres + Redis (docker)
make infra

# 2. 安裝 backend Python 依賴 + 跑 migration + seed
cd backend
python -m venv venv && source venv/bin/activate
make -C .. install-backend           # = pip install -r requirements.txt -r requirements-dev.txt
make -C .. revision msg="0001 e initial e tables"   # 第一次才需要
make -C .. migrate
make -C .. seed                                       # 灌入 4 個示範帳號

# 3. 啟動 backend (port 8000)
make -C .. dev-backend

# 4. 另一個 shell：啟動 frontend (port 3000)
cd ../frontend && make -C .. install-frontend && make -C .. dev-frontend

# 5. 打開 http://localhost:3000
```

預設帳號（`scripts/seed_dev.py` 內定義）：

| Email | 密碼 | 角色 |
|---|---|---|
| `admin@example.com` | `Admin1234` | 系統管理者 (`*` 全權限) |
| `supervisor@example.com` | `Super1234` | 實驗室主管 |
| `engineer@example.com` | `Engin1234` | 實驗室人員 |
| `requester@example.com` | `Reque1234` | 廠區使用者 |

> 想看完整 docker-compose 版本（含 celery worker / beat），跳到 [Docker](#docker-完整堆疊) 一節。

---

## Tech stack

| 層 | 技術 |
|---|---|
| 前端 | TypeScript + React 19 + **Next.js 16** (App Router) · TanStack Query · axios · inline-style + CSS variables (不用 Tailwind utility class) |
| 後端 | **Python 3.12 + FastAPI** · uvicorn · pydantic v2 |
| DB | **PostgreSQL 16** + SQLAlchemy 2.0 (async) + Alembic 遷移 |
| 背景任務 | **Celery 5 + Redis 7** (Celery Beat 排程告警升級) |
| Auth | JWT (httpOnly cookie) + bcrypt |
| Realtime | SSE (`sse-starlette`) + Redis pub/sub |
| Email | `fastapi-mail` (file backend for demo, SMTP for prod) |
| 測試 | pytest + httpx + pytest-asyncio (BE) · vitest + Playwright (FE) |
| Lint | ruff + mypy (BE) · eslint + tsc (FE) |
| CI | GitHub Actions (`.github/workflows/ci.yml`) |
| 部署 | docker-compose（含 postgres / redis / celery worker / celery beat） |

---

## Repo 結構

```
Cloud-Native-Development-Project/
├── README.md                    ← 你正在看
├── CLAUDE.md                    ← Claude Code 操作慣例 + subagent 對應表
├── Makefile                     ← `make help` 看所有指令
├── docker-compose.yml           ← 全套服務拓樸（FE + BE + Postgres + Redis + Celery + pgAdmin）
├── .github/workflows/ci.yml     ← CI：lint + test + docker build
├── docs/                        ← 規範與需求文件
├── backend/                     ← FastAPI 應用
└── frontend/                    ← Next.js 應用
```

`docs/` 內的關鍵文件：

| 文件 | 內容 |
|---|---|
| `total.md` | 跨模組總覽 |
| `flow.md` | 委託單 / WIP / Issue 的官方狀態機 |
| `team_work_split.md` | 5 人分工 (A: 委託單；B: 樣品/WIP；C: 機台/Recipe/排程；D: 實驗執行/報告；E: 帳號/設定/告警/儀表板/整合品質) |
| `integration_contract.md` | E 主導的跨模組規範：enum、response 包裝、auth、master-data、新增 module/model/migration 流程 |
| `development_standards.md` | 測試、PR、Definition of Done |
| `naming_and_class_conventions.md` | 檔名、類別、API、DB 命名規則 |
| `frontend_backend_structure.md` | 前後端目錄詳解 |
| `role.md`, `system_setting.md`, `warn.md`, `dashboard.md` | E 模組的需求文件 |
| `order_management.md`, `sample_management.md`, `machine_recipe.md`, `schedule.md`, `experiment_execute.md`, `result_manage.md` | A/B/C/D 模組的需求文件 |

---

## Backend (`backend/`)

### 啟動

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                          # 預設指向 localhost postgres / redis

# DB
alembic revision --autogenerate -m "0001 e initial e tables"   # 第一次
alembic upgrade head
python scripts/seed_dev.py                    # 灌示範帳號 + 角色 + 部門 + 實驗室

# API
uvicorn app.main:app --reload --port 8000     # http://localhost:8000

# 背景任務（其他 shell）
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat   --loglevel=info
```

打開 <http://localhost:8000/api-docs> 看 Swagger，<http://localhost:8000/health> 看健康檢查。

### 檔案夾用途

```
backend/
├── app/
│   ├── main.py              ← FastAPI factory + CORS + middleware + 例外處理 + /health
│   ├── routes.py            ← 中央 router registry；新增 module 在這加一行
│   │
│   ├── core/
│   │   ├── config.py        ← Pydantic Settings — 讀 .env / 環境變數
│   │   ├── database.py      ← async SQLAlchemy engine + `get_db()` dependency
│   │   ├── security.py      ← bcrypt 雜湊 + JWT 編解碼
│   │   ├── celery_app.py    ← Celery 實例 + beat 排程表
│   │   └── logging.py
│   │
│   ├── common/              ← 跨模組共用
│   │   ├── enums/           ← 全部 status enum（OrderStatus, IssueStatus, ...）
│   │   ├── schemas/         ← ApiResponse / PageResponse / ErrorResponse 三種回傳包裝
│   │   ├── dependencies/    ← get_current_user, require_permission(code), get_pagination
│   │   ├── middleware/      ← X-Request-ID, request logger
│   │   └── errors.py        ← AppError + NotFoundError / ValidationError 等
│   │
│   ├── modules/             ← 22 個業務模組（每個都用 5 檔案結構）
│   │   ├── auth/            ← E：login / logout / /api/me
│   │   ├── users/           ← E：使用者 CRUD（這是範本模組）
│   │   ├── roles/           ← E：角色 + 權限
│   │   ├── master_data/     ← E：給前端下拉的共用資料
│   │   ├── system_settings/ ← E：系統設定（Phase 2）
│   │   ├── labs/            ← E
│   │   ├── departments/     ← E
│   │   ├── storage_locations/ ← E
│   │   ├── files/           ← E：檔案上傳
│   │   ├── audit_logs/      ← E：稽核紀錄
│   │   ├── issues/          ← E：異常 / 告警 / 中止申請（Phase 3）
│   │   ├── notifications/   ← E：通知中心（Phase 3）
│   │   ├── dashboard/       ← E：儀表板聚合 + SSE（Phase 4）
│   │   ├── orders/          ← A：委託單（placeholder）
│   │   ├── samples/, wips/  ← B
│   │   ├── machines/, recipes/, schedules/, dispatches/  ← C
│   │   └── experiment_runs/, reports/  ← D
│   │
│   ├── db/
│   │   ├── base.py          ← DeclarativeBase + TimestampMixin
│   │   └── models/          ← SQLAlchemy ORM 模型；每個資源一個檔，於 __init__.py re-export
│   │
│   └── workers/             ← Celery 背景任務
│       ├── escalation.py    ← 每 60s 掃描 open issue 並升級
│       └── email_sender.py  ← 寄送通知 email（file backend / SMTP）
│
├── alembic/                 ← async 遷移；版本檔放 versions/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── scripts/
│   ├── seed_dev.py          ← 示範資料（角色 / 使用者 / 部門 / 實驗室）
│   └── sync_enums.py        ← 把 app/common/enums/*.py 轉成 frontend enums.ts
│
├── tests/
│   ├── conftest.py          ← session-scope DB 重建 + seed；提供 client / admin_client / plant_user_client
│   ├── test_health.py
│   └── e_tests/             ← E 的測試（test_auth, test_users, test_roles_master_data）
│
├── uploads/                 ← /api/files 的儲存位置（Phase 6 stretch: MinIO）
├── requirements.txt         ← runtime deps
├── requirements-dev.txt     ← pytest / ruff / mypy
├── pyproject.toml           ← ruff / mypy / pytest 設定
├── alembic.ini
├── dockerfile               ← multi-stage Python image（給 API、worker、beat 共用）
├── .env.example
└── README.md
```

**Module pattern** — 每個 `modules/<name>/` 都用同樣 5 檔案結構：

| 檔案 | 職責 |
|---|---|
| `router.py` | FastAPI APIRouter — 只放路由、權限 deps |
| `schemas.py` | Pydantic DTO (`Create` / `Update` / `Response` / `Query`) |
| `service.py` | 商業邏輯 — 協調 repository + audit + notification |
| `repository.py` | 純 DB 查詢，不寫業務規則 |
| `dependencies.py` | FastAPI `Depends()` factory（建構 service 等） |

開新模組請參考 `app/modules/users/` 範本。

### 測試 / Lint

```bash
make test-backend           # = pytest --cov=app
make lint-backend           # = ruff check + ruff format --check + mypy app
make format                 # 自動修正
```

`backend/tests/conftest.py` 會在 session 開始時 drop+recreate schema 並重跑 seed。所以測試需要 Postgres 在跑（`make infra`）。

### Alembic / migration

```bash
make revision msg="add foo"      # = alembic revision --autogenerate -m "..."
make migrate                     # = alembic upgrade head
cd backend && alembic downgrade -1
cd backend && alembic history
```

遷移檔命名規則：`<順序>_<成員字母>_<簡述>.py`，例如 `0010_a_orders.py`（A 的第一個遷移）。詳見 `docs/integration_contract.md` §13。

---

## Frontend (`frontend/`)

### 啟動

```bash
cd frontend
npm install                 # 第一次
npm run dev                 # http://localhost:3000
```

未登入會看到登入畫面（AuthGate 攔截）。用上面的示範帳號登入即可。

環境變數（可選）：

```bash
export NEXT_PUBLIC_API_URL=http://localhost:8000/api   # 預設值即此（Docker build 也用同名 build-arg）
```

### 檔案夾用途

```
frontend/
├── app/                        ← Next.js 16 App Router 頁面
│   ├── layout.tsx              ← 全站根 layout — mount Providers + AuthGate
│   ├── page.tsx                ← /  主管儀表板（Phase 4 改成 API-driven）
│   ├── globals.css             ← CSS 變數（--bg, --s1, --blue, ...）— 設計系統的單一來源
│   ├── login/page.tsx          ← /login  登入頁（已登入會自動跳 /）
│   ├── account/page.tsx        ← /account  使用者管理（含建立 modal）
│   ├── config/page.tsx         ← /config  系統設定（Phase 2）
│   ├── orders/, approve/       ← A 模組頁面
│   ├── sample/, wip/, transfer/ ← B
│   ├── dispatch/, machine/, recipe/ ← C
│   ├── storage/, exception/, alert/ ← D / E
│   └── 其餘為 placeholder stub（components/PlaceholderPage.tsx）
│
├── components/                 ← 根層級的 React 元件
│   ├── Sidebar.tsx             ← 左側導覽，依 permission 過濾 nav，footer 顯示登入者
│   ├── AuthGate.tsx            ← 根據 useAuth() 狀態渲染 loading / 登入表單 / Sidebar+主畫面
│   ├── Providers.tsx           ← QueryClientProvider + AuthProvider（mounted from layout）
│   ├── LoginForm.tsx           ← 登入表單元件（被 AuthGate / /login 共用）
│   ├── PlaceholderPage.tsx     ← 未實作頁面的「🚧 施工中」樣板
│   └── ui/                     ← 小型 UI 原件
│       ├── KpiCard.tsx         ← 儀表板 KPI 卡片
│       └── Chip.tsx            ← 狀態標籤
│
├── src/
│   ├── api/
│   │   └── httpClient.ts       ← axios 實例（withCredentials: true 才能帶 cookie）
│   ├── lib/
│   │   └── queryClient.ts      ← TanStack Query client（4xx 不重試等預設）
│   ├── contexts/
│   │   └── AuthContext.tsx     ← useAuth() → { user, login, logout, hasPermission, refresh }
│   ├── services/               ← 每個模組一支型別化的 API client
│   │   ├── auth-api.ts
│   │   ├── user-api.ts
│   │   └── master-data-api.ts
│   ├── types/
│   │   ├── api.ts              ← ApiResponse / PageResponse / ApiErrorBody
│   │   └── user.ts             ← User / Role / MeResponse / 等
│   ├── constants/
│   │   ├── enums.ts            ← 由 backend/scripts/sync_enums.py 自動生成 — 不要手改
│   │   └── status-labels.ts    ← 手寫的中文顯示對照
│   └── layouts/MainLayout.tsx  ← (legacy, 目前未使用)
│
├── public/                     ← 靜態資源
├── node_modules/
├── package.json                ← Next.js 16, React 19, axios, @tanstack/react-query
├── tsconfig.json               ← `@/*` 同時解析 ./src/* 與 ./*
├── eslint.config.mjs
├── postcss.config.mjs
├── next.config.ts
├── next-env.d.ts
├── dockerfile                  ← (待補 — 目前用 docker-compose build 即可)
├── CLAUDE.md → AGENTS.md       ← 「This is NOT the Next.js you know」提醒
└── README.md
```

**Styling 慣例**：用 `style={{ color: 'var(--blue)' }}` 形式的 inline style + CSS 變數，**不要**用 Tailwind utility class。色票全部在 `app/globals.css` 統一管。

**路徑別名**：`@/*` 同時解析 `./src/*` 和 `./*`，所以 `@/components/Sidebar`（在根 components/）和 `@/contexts/AuthContext`（在 src/contexts/）都能用。

### 測試 / Lint

```bash
make test-frontend          # vitest（vitest config 待補）
make lint-frontend          # eslint + tsc --noEmit
```

---

## Docker 完整堆疊

```bash
make build                  # 第一次或 Dockerfile 改後
make up                     # 起 FE + BE + postgres + redis + celery worker + celery beat
make up profile=tools       # 加上 pgAdmin (port 5050)
make down
make logs                   # 跟看所有 service log
```

服務拓樸：

| Service | Port | 用途 |
|---|---|---|
| `frontend` | 3000 | Next.js |
| `backend` | 8000 | FastAPI |
| `postgres` | 5432 | DB（`pgdata` volume 持久化） |
| `redis` | 6379 | Celery broker + cache + SSE pub/sub（AOF 持久化） |
| `celery-worker` | — | 跑 Celery 任務 |
| `celery-beat` | — | 排程器（每分鐘觸發告警升級掃描） |
| `pgadmin` | 5050 | 只有 `--profile tools` 才會啟動 |

預設帳號 / 密碼 / DB 名稱由 docker-compose 的環境變數控制（見 `docker-compose.yml`）。

---

## CI

`.github/workflows/ci.yml` 在每個 push / PR 跑：

- **backend** — ruff check + ruff format --check + mypy + alembic upgrade head + pytest（使用 postgres + redis service container）
- **frontend** — eslint + tsc --noEmit + next build + vitest (如果有)
- **docker** — `docker compose build` smoke test

---

## 給組員的 onboarding 指引

第一次 clone 之後：

1. 讀 [`docs/team_work_split.md`](docs/team_work_split.md) 確認自己負責哪幾個模組。
2. 讀 [`docs/integration_contract.md`](docs/integration_contract.md) — enum / API / DB / migration 命名規範都在這。
3. 讀 [`docs/flow.md`](docs/flow.md) 確認自己模組的狀態機。
4. 用 Quick start 把 stack 起起來，登入 4 個角色看看 sidebar 差異。
5. 看 `backend/app/modules/users/` 當作 backend module 範本；複製後改名實作自己的模組。
6. 看 `frontend/app/account/page.tsx` 當作 frontend 頁面範本（TanStack Query + master-data + 權限判斷）。
7. 開新 SQLAlchemy 模型時，記得在 `backend/app/db/models/__init__.py` re-export，然後 `make revision msg="0XYY_<letter>_<short_desc>"`。
8. 新增 enum 後，跑 `python backend/scripts/sync_enums.py` 把前端 `enums.ts` 重新生成。

有問題優先看 `CLAUDE.md` 和 `docs/integration_contract.md`，或丟到組內群組讓 E 同步。
