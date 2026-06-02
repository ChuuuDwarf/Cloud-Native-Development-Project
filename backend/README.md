# LIMS Backend

![Version](https://img.shields.io/badge/version-v0.1.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12-3776ab.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128.8-009688.svg)
![Database](https://img.shields.io/badge/PostgreSQL-16-4169e1.svg)
![Tests](https://img.shields.io/badge/tests-pytest%20%2B%20httpx-7c3aed.svg)

LIMS 後端是以 FastAPI 建立的 API 服務，負責驗證授權、委託單流程、樣品/WIP、派工、實驗執行、報告、結案、異常、通知、儀表板與背景任務。資料層使用 SQLAlchemy 2 async 與 Alembic，背景工作由 Redis + Celery + Celery Beat 處理，並支援可選的中華電信 TAS phone alert / MQTT acknowledgement pipeline。

- Repo README: [../README.md](../README.md)
- Frontend README: [../frontend/README.md](../frontend/README.md)
- Integration contract: [../docs/integration_contract.md](../docs/integration_contract.md)

## Tech Stack

| 類別 | 技術 |
|---|---|
| Runtime | Python 3.12 |
| API | FastAPI, Uvicorn, Pydantic v2 |
| DB | PostgreSQL 16, SQLAlchemy 2 async, asyncpg, Alembic |
| Auth | JWT access/refresh token, bcrypt, httpOnly cookie |
| Background jobs | Celery 5, Redis 7, Celery Beat |
| Realtime | SSE, Redis pub/sub |
| Notification | in-app notifications, file/SMTP email, optional TAS phone callout |
| Tests | pytest, pytest-asyncio, httpx |
| Quality | ruff, mypy |

## 快速啟動

從 repo 根目錄啟動 Postgres 與 Redis：

```bash
make infra
```

建立後端環境：

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_dev.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

其他 shell 可啟動背景任務：

```bash
cd backend
source .venv/bin/activate
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat --loglevel=info
```

根目錄 Makefile 等價指令：

```bash
make dev-backend
make worker
make beat
make migrate
make seed
```

## API 文件

啟動 `uvicorn app.main:app --reload --port 8000` 後：

| Endpoint | 用途 |
|---|---|
| <http://localhost:8000/api-docs> | Swagger UI |
| <http://localhost:8000/api-redoc> | ReDoc |
| <http://localhost:8000/openapi.json> | OpenAPI JSON |
| <http://localhost:8000/health> | Health check |
| <http://localhost:8000/> | API root summary |

FastAPI app version 為 `0.1.0`。

## API 路由總覽

| Prefix | 模組 |
|---|---|
| `/api/auth/login`, `/api/auth/logout`, `/api/auth/refresh`, `/api/me` | Auth |
| `/api/users` | 使用者管理 |
| `/api/roles` | 角色與權限 |
| `/api/master-data` | 前端下拉與共用主資料 |
| `/api/labs` | 實驗室 |
| `/api/orders` | 委託單與簽核流程 |
| `/api/quotas` | 配額 |
| `/api/samples` | 樣品 |
| `/api/wips` | WIP |
| `/api/transfers` | 樣品轉送 |
| `/api/machines` | 機台 |
| `/api/recipes` | Recipe |
| `/api/dispatches` | 派工 |
| `/api/experiment-runs` | 實驗執行 |
| `/api/reports` | 報告 |
| `/api/closures` | 取件與結案 |
| `/api/issues` | 異常與告警 |
| `/api/notifications` | 通知中心 |
| `/api/dashboard` | 主管儀表板與即時資料 |
| `/api/workflow-*` | 跨模組流程視圖 |

實際 route registry 位於 `backend/app/routes/registry.py`。

## 專案結構

```text
backend/
├── app/
│   ├── main.py                 # FastAPI app factory, middleware, error handlers, health
│   ├── routes/                 # API routers 與中央 registry
│   ├── services/               # 既有服務層
│   ├── repos/                  # DB repository / mapper
│   ├── schemas/                # 既有 Pydantic schemas
│   ├── modules/                # 模組化 domains: dashboard, machines, recipes...
│   ├── db/
│   │   ├── base.py             # DeclarativeBase / mixins
│   │   ├── session.py          # session factory
│   │   └── models/             # SQLAlchemy ORM models
│   ├── common/
│   │   ├── enums/              # 共用 enum
│   │   ├── schemas/            # ApiResponse / PageResponse / ErrorResponse
│   │   ├── dependencies/       # auth, scope, pagination, lab scope
│   │   ├── middleware/         # request id, request logger
│   │   └── errors.py           # AppError 與共用錯誤
│   ├── core/
│   │   ├── config.py           # Pydantic settings
│   │   ├── database.py         # async DB helpers
│   │   ├── security.py         # JWT / password hashing
│   │   ├── celery_app.py       # Celery app + beat schedule
│   │   └── error_handlers.py
│   └── workers/                # Celery tasks, TAS MQTT listener, email sender
├── alembic/                    # migration env 與 versions
├── scripts/                    # seed、enum sync、smoke scripts
├── sql/                        # schema / bootstrap SQL
├── tests/                      # pytest 測試
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── alembic.ini
└── .env.example
```

目前程式同時包含 `app/routes`、`app/services`、`app/repos` 與部分 `app/modules/<name>` 的分層；新增或調整模組時請優先參考 [../docs/integration_contract.md](../docs/integration_contract.md) 的約定，並與既有路由 registry 對齊。

## Environment Variables

複製範本：

```bash
cp .env.example .env
```

主要設定：

| 變數 | 預設 / 範例 | 說明 |
|---|---|---|
| `ENV` | `development` | 執行環境 |
| `DATABASE_URL` | `postgresql+asyncpg://lims:lims@localhost:5432/lims` | async SQLAlchemy DB URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker、cache、SSE pub/sub |
| `JWT_SECRET` | `change-me-in-prod-please` | JWT 簽章金鑰，正式環境必須更換 |
| `JWT_ALGORITHM` | `HS256` | JWT 演算法 |
| `JWT_ACCESS_EXPIRES_MINUTES` | `60` | access token 有效時間 |
| `JWT_REFRESH_EXPIRES_DAYS` | `7` | refresh token 有效天數 |
| `CORS_ORIGINS` | `http://localhost:3000` | 允許前端來源，逗號分隔 |
| `EMAIL_BACKEND` | `file` | `file` 或 `smtp` |
| `EMAIL_FROM` | `noreply@lims.local` | email 寄件人 |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | 空 / `587` | SMTP 設定 |
| `UPLOADS_DIR` | `./uploads` | 上傳檔案與 file email backend 位置 |
| `CHT_API_KEY`, `CHT_SERVICE_NUMBER` | 空 | TAS phone callout credential，可留空 |
| `CHT_BASE_URL` | `https://tasapi.cht.com.tw/apis/CHTIoT` | TAS REST API base URL |
| `TAS_ENABLED` | `false` | 是否啟用 TAS phone/MQTT pipeline |
| `TAS_SN_KEY` | 空 | MQTT topic key |
| `TAS_MQTT_BROKER_URL` | `tls://tasapi.cht.com.tw:2883` | TAS MQTT broker |
| `DEMO_PHONE` | 空 | seed users 共用 demo phone |

未設定 TAS/CHT 時，電話通知任務會記錄並跳過，不影響 API、通知中心或 email demo。

## Migration 與 Seed

```bash
alembic upgrade head
alembic revision --autogenerate -m "add foo"
alembic downgrade -1
python scripts/seed_dev.py
```

根目錄 Makefile：

```bash
make migrate
make revision msg="add foo"
make seed
```

`scripts/seed_dev.py` 會建立 demo 角色、使用者、部門與實驗室；Docker Compose 的 `seed` service 也會自動執行。

## 測試與品質檢查

```bash
ruff check .
ruff format --check .
mypy app
pytest
pytest --cov=app
```

根目錄 Makefile：

```bash
make lint-backend
make test-backend
make ci-backend
```

測試目錄依模組分組，例如：

```text
tests/
├── a_tests/        # order 相關
├── c_tests/        # machine / recipe / dispatch
├── d_tests/        # experiment / report
├── e_tests/        # auth / user / role / dashboard / notification
└── test_*.py       # 跨模組或 regression tests
```

## Docker Compose

根目錄 [../docker-compose.yml](../docker-compose.yml) 會啟動：

| Service | 用途 |
|---|---|
| `postgres` | PostgreSQL |
| `redis` | Redis |
| `migrate` | 一次性 Alembic migration |
| `seed` | 一次性 demo seed |
| `backend` | FastAPI API |
| `celery-worker` | 背景任務 |
| `celery-beat` | 排程任務 |
| `tas-mqtt-listener` | TAS MQTT listener，可選 |
| `frontend` | Next.js 前端 |
| `pgadmin` | DB 管理工具，需 `--profile tools` |

常用指令：

```bash
make build
make up
make logs
make down
```
