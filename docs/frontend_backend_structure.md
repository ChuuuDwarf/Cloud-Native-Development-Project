# Frontend 與 Backend 專案結構說明

本文件整理本專案目前的 `frontend` 與 `backend` 目錄結構，方便組員了解各資料夾用途、後續開發位置，以及前後端分工方式。

---

## 一、專案整體建議結構

建議專案根目錄整理如下：

```txt
Cloud-Native-Development-Project/
├── README.md
├── docs/
│   ├── dashboard.md
│   ├── development_standards.md
│   ├── experiment_execute.md
│   ├── flow.md
│   ├── machine_recipe.md
│   ├── naming_and_class_conventions.md
│   ├── order_management.md
│   ├── result_manage.md
│   ├── role.md
│   ├── sample_management.md
│   ├── schedule.md
│   ├── system_setting.md
│   ├── team_work_split.md
│   ├── total.md
│   └── warn.md
│
├── frontend/
│   └── 前端 Next.js 專案
│
└── backend/
    └── 後端 Node.js / TypeScript 專案
```

---

# 二、Frontend 結構

Frontend 使用 Next.js App Router 架構，主要負責使用者畫面、頁面路由、UI 元件與呼叫後端 API。

---

## 2.1 Frontend 目錄結構

```txt
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   ├── globals.css
│   ├── favicon.ico
│   │
│   ├── orders/
│   │   └── page.tsx
│   ├── approve/
│   │   └── page.tsx
│   ├── sample/
│   │   └── page.tsx
│   ├── wip/
│   │   └── page.tsx
│   ├── dispatch/
│   │   └── page.tsx
│   ├── machine/
│   │   └── page.tsx
│   ├── recipe/
│   │   └── page.tsx
│   ├── transfer/
│   │   └── page.tsx
│   ├── storage/
│   │   └── page.tsx
│   ├── exception/
│   │   └── page.tsx
│   ├── alert/
│   │   └── page.tsx
│   ├── account/
│   │   └── page.tsx
│   └── config/
│       └── page.tsx
│
├── components/
│   ├── Sidebar.tsx
│   └── ui/
│       ├── Chip.tsx
│       └── KpiCard.tsx
│
├── public/
│
├── src/
│   ├── api/
│   │   ├── httpClient.ts
│   │   └── orderApi.ts
│   └── layouts/
│       └── MainLayout.tsx
│
├── package.json
├── package-lock.json
├── tsconfig.json
├── next.config.ts
├── eslint.config.mjs
└── Dockerfile
```

---

## 2.2 Frontend 主要資料夾說明

| 路徑 | 用途 |
|---|---|
| `app/` | Next.js App Router 頁面路由目錄 |
| `app/page.tsx` | 首頁或 Dashboard 入口 |
| `app/layout.tsx` | 全站共用版型設定 |
| `app/globals.css` | 全域樣式 |
| `components/` | 共用元件，例如側邊欄、卡片、標籤 |
| `components/ui/` | 小型 UI 元件 |
| `src/api/` | 前端呼叫後端 API 的封裝 |
| `src/api/httpClient.ts` | Axios instance 與 API base URL 設定 |
| `src/api/orderApi.ts` | 委託單相關 API 呼叫 |
| `src/layouts/` | 共用頁面排版 |
| `public/` | 靜態資源，例如圖片、icon |
| `Dockerfile` | 前端容器化設定 |

---

## 2.3 Frontend 路由對應

| 頁面路徑 | 功能說明 |
|---|---|
| `/` | 首頁 / Dashboard |
| `/orders` | 委託單管理 |
| `/approve` | 委託單簽核 |
| `/sample` | 收樣管理 |
| `/wip` | 樣品 / WIP 管理 |
| `/dispatch` | 派工管理 |
| `/machine` | 機台管理 |
| `/recipe` | Recipe 管理 |
| `/transfer` | 分貨 / 轉送管理 |
| `/storage` | 暫存 / 入庫管理 |
| `/exception` | 異常 / 中止管理 |
| `/alert` | 告警中心 |
| `/account` | 帳號管理 |
| `/config` | 系統設定 |

---

## 2.4 Frontend API 設定

前端使用 Axios 呼叫後端 API。

```txt
src/api/httpClient.ts
```

建議使用 Next.js 的公開環境變數：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

範例：

```ts
const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";
```

---

## 2.5 Frontend 開發注意事項

1. 新增頁面時，請放在 `app/<route>/page.tsx`。
2. 共用元件請放在 `components/`。
3. API 呼叫邏輯請集中放在 `src/api/`，不要直接散落在各頁面。
4. 若新增後端 API，前端應建立對應的 API function。
5. 側邊欄有連結的頁面都應至少建立空白頁，避免 404。
6. 環境變數需使用 `NEXT_PUBLIC_` 開頭，前端才讀得到。

---

# 三、Backend 結構

Backend 使用 **Python 3.12 + FastAPI** 架構，負責 API、商業邏輯、資料存取（SQLAlchemy 2.0 async + Alembic）、背景任務（Celery + Redis）以及自動生成的 OpenAPI 文件。

> 框架定案於 2026-05-20。`docs/integration_contract.md` 是跨模組的單一規範文件。

---

## 3.1 Backend 目錄結構

```txt
backend/
├── app/
│   ├── main.py                # FastAPI factory + lifespan + middleware
│   ├── routes.py              # 中央 router registry（每個 module 都掛在這）
│   │
│   ├── core/
│   │   ├── config.py          # Pydantic BaseSettings（env vars）
│   │   ├── database.py        # async engine + AsyncSession dependency
│   │   ├── security.py        # JWT + bcrypt
│   │   ├── celery_app.py      # Celery factory + beat schedule
│   │   └── logging.py
│   │
│   ├── common/
│   │   ├── enums/             # 全專案共享的 status enums
│   │   ├── schemas/           # ApiResponse / PageResponse / ErrorResponse
│   │   ├── dependencies/      # get_current_user, require_permission(...)
│   │   ├── middleware/        # request_id, request_logger
│   │   └── errors.py          # AppError / ValidationError / NotFoundError / ...
│   │
│   ├── modules/
│   │   ├── auth/              # 登入、登出、目前使用者（組員 E）
│   │   ├── users/             # 使用者管理（組員 E）— 範本模組
│   │   ├── roles/             # 角色、權限（組員 E）
│   │   ├── master_data/       # 共用下拉資料（組員 E）
│   │   ├── system_settings/   # 系統設定 + 歷程（組員 E）
│   │   ├── labs/              # 實驗室（組員 E）
│   │   ├── departments/       # 部門（組員 E）
│   │   ├── storage_locations/ # 倉位（組員 E）
│   │   ├── files/             # 檔案上傳（組員 E）
│   │   ├── audit_logs/        # 稽核紀錄（組員 E）
│   │   ├── issues/            # 異常 / 告警 / 中止申請（組員 E）
│   │   ├── notifications/     # 通知中心（組員 E）
│   │   ├── dashboard/         # 主管儀表板聚合 + SSE（組員 E）
│   │   ├── orders/            # 委託單（組員 A）
│   │   ├── samples/           # 收樣（組員 B）
│   │   ├── wips/              # WIP 與分貨（組員 B）
│   │   ├── machines/          # 機台（組員 C）
│   │   ├── recipes/           # Recipe（組員 C）
│   │   ├── schedules/         # 排程（組員 C）
│   │   ├── dispatches/        # 派工（組員 C）
│   │   ├── experiment_runs/   # 實驗執行紀錄（組員 D）
│   │   └── reports/           # 實驗報告（組員 D）
│   │
│   ├── db/
│   │   ├── base.py            # DeclarativeBase + TimestampMixin
│   │   └── models/            # 每個資源一個檔案，於 __init__ re-export
│   │
│   └── workers/
│       ├── escalation.py      # Celery: 掃描未解決告警並升級
│       └── email_sender.py    # Celery: 寄送通知 email
│
├── alembic/                   # 遷移檔（async 設定）
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── scripts/
│   └── sync_enums.py          # 同步 enum 到 frontend/src/constants/enums.ts
│
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── e_tests/               # 組員 E 的單元 / 整合 / 整合性測試
│
├── uploads/                   # 檔案模組的儲存位置（Phase 6 stretch: MinIO）
│
├── requirements.txt           # runtime 依賴
├── requirements-dev.txt       # dev / test 依賴
├── pyproject.toml             # ruff / mypy / pytest 設定
├── alembic.ini
├── Dockerfile                 # multi-stage Python image
├── .env.example
└── README.md
```

---

## 3.2 Backend 主要資料夾說明

| 路徑 | 用途 |
|---|---|
| `app/main.py` | FastAPI 應用工廠 + lifespan + 中介層 |
| `app/routes.py` | 中央 router registry — 新增模組時，在這裡多加一行 |
| `app/core/` | 環境設定、async DB engine、安全（JWT + bcrypt）、Celery、logging |
| `app/common/` | 跨模組共用：enums、response schemas、dependencies、middleware、errors |
| `app/modules/` | 依功能切分；每個模組同一份檔案結構（見 §3.3） |
| `app/db/` | SQLAlchemy Base + 所有 ORM 模型 |
| `app/workers/` | Celery 背景任務 |
| `alembic/` | 資料庫遷移；async 設定，autogenerate 從 `app.db.base.Base.metadata` 拿 schema |
| `scripts/sync_enums.py` | 將 enum 同步到 frontend `enums.ts` |
| `tests/` | pytest + httpx；組員 E 的測試集中在 `tests/e_tests/` |
| `Dockerfile` | Multi-stage 容器；同一份 image 同時供 API、Celery worker、Celery beat 使用 |

---

## 3.3 Backend Module 分層說明

每一個 module 維持以下檔案：

```txt
modules/<name>/
├── __init__.py
├── router.py        # FastAPI APIRouter — thin、只負責路由與權限 deps
├── schemas.py       # Pydantic DTOs：XCreate / XUpdate / XResponse / XQuery
├── service.py       # 商業邏輯；協調 Repository、AuditLogService、NotificationService
├── repository.py    # 純 async DB 查詢；以 AsyncSession 為輸入
└── dependencies.py  # FastAPI Depends factory，例如 get_user_service(session)
```

| 檔案 | 負責內容 |
|---|---|
| `router.py` | 定義 API 路由、HTTP method、權限 dependencies |
| `schemas.py` | request / response 的 Pydantic 型別（含 alias 轉 camelCase） |
| `service.py` | 主要業務邏輯、狀態檢查、跨模組協調 |
| `repository.py` | SQLAlchemy 查詢，不放業務規則 |
| `dependencies.py` | FastAPI Depends() factory，例如 service 建構 |

> **範本模組**：`app/modules/users/`。開發新模組時請直接複製這個資料夾、改名後填內容。

---

## 3.4 Backend 模組規劃

詳見 `docs/team_work_split.md` 的責任歸屬。所有模組命名一律 `snake_case`，URL 一律 kebab-case（`/api/storage-locations` 對應 `modules/storage_locations/`）。

| 模組資料夾 | URL 前綴 | 負責人 |
|---|---|---|
| `auth/` | `/api/auth/*`, `/api/me` | 組員 E |
| `users/` | `/api/users` | 組員 E |
| `roles/` | `/api/roles`, `/api/permissions` | 組員 E |
| `master_data/` | `/api/master-data` | 組員 E |
| `system_settings/` | `/api/system-settings` | 組員 E |
| `labs/` | `/api/labs` | 組員 E |
| `departments/` | `/api/departments` | 組員 E |
| `storage_locations/` | `/api/storage-locations` | 組員 E |
| `files/` | `/api/files` | 組員 E |
| `audit_logs/` | `/api/audit-logs` | 組員 E |
| `issues/` | `/api/issues` | 組員 E |
| `notifications/` | `/api/notifications` | 組員 E |
| `dashboard/` | `/api/dashboard` | 組員 E |
| `orders/` | `/api/orders` | 組員 A |
| `samples/` | `/api/samples` | 組員 B |
| `wips/` | `/api/wips` | 組員 B |
| `machines/` | `/api/machines` | 組員 C |
| `recipes/` | `/api/recipes` | 組員 C |
| `schedules/` | `/api/schedules` | 組員 C |
| `dispatches/` | `/api/dispatches` | 組員 C |
| `experiment_runs/` | `/api/experiment-runs` | 組員 D |
| `reports/` | `/api/reports` | 組員 D |

---

## 3.5 Backend API 文件

FastAPI 自動產生 OpenAPI，啟動後可用以下路徑：

| 路徑 | 用途 |
|---|---|
| `/api-docs` | Swagger UI |
| `/api-redoc` | ReDoc |
| `/openapi.json` | OpenAPI JSON spec |
| `/health` | 健康檢查 |

---

## 3.6 Backend 開發注意事項

1. 新增 API 前，先決定屬於哪個 module；不確定就問 E。
2. 嚴格維持 `router → service → repository` 分層，不在 router 寫業務邏輯。
3. Response 一律走 `ApiResponse[T]` / `PageResponse[T]` / `ErrorResponse` 三種包裝。
4. Enum 一律放 `app/common/enums/`；新增後執行 `python scripts/sync_enums.py` 同步到前端。
5. 新增 SQLAlchemy 模型後：在 `app/db/models/__init__.py` re-export，再執行 `alembic revision --autogenerate -m "..."`。
6. 遷移檔命名：`<ordinal>_<member-letter>_<short_description>.py`，避免多人撞檔名。
7. 狀態變更請寫入 `AuditLog`；需要通知使用者時呼叫 `NotificationService.notify(...)`。
8. 背景任務放 `app/workers/`，註冊到 `app.core.celery_app.celery_app.conf.include`。
9. 假資料集中在 `scripts/seed_demo.py`（Phase 5 建立），不要散在各 service。
10. API contract / DTO 名稱遵循 `docs/naming_and_class_conventions.md`。

---

# 四、Frontend 與 Backend 對應關係

| Frontend 頁面 | Backend API 模組 |
|---|---|
| `/orders` | `orders/` |
| `/approve` | `orders/` |
| `/sample` | `samples/` |
| `/wip` | `samples/` |
| `/dispatch` | `dispatches/` |
| `/machine` | `machines/` |
| `/recipe` | `recipes/` |
| `/exception` | `issues/` |
| `/alert` | `issues/` |
| `/account` | `users/` |
| `/config` | `system-settings/` |
| `/` | `dashboard/` |

---

# 五、建議分工方式

## Frontend

| 工作 | 負責內容 |
|---|---|
| 頁面開發 | 建立各功能頁面與表單 |
| UI 元件 | 建立共用元件，例如卡片、表格、彈窗 |
| API 串接 | 在 `src/api/` 中建立 API function |
| 版面整合 | 整合 Sidebar、Layout 與頁面內容 |

---

## Backend

| 工作 | 負責內容 |
|---|---|
| API Routes | 建立各模組 API 路由 |
| Controller | 處理 request / response |
| Service | 撰寫商業邏輯 |
| Repository | 處理資料存取或假資料 |
| Swagger | 更新 API 文件 |
| Middleware | 錯誤處理、驗證、權限檢查 |

---

# 六、總結

本專案建議採用前後端分離架構：

```txt
frontend/
```

負責畫面、路由、UI 元件與呼叫 API。

```txt
backend/
```

負責 API、商業邏輯、資料處理與 Swagger 文件。

前端新增頁面時，應同步確認是否需要後端 API。  
後端新增 API 時，也應同步更新 Swagger 文件與前端 API 呼叫封裝。
