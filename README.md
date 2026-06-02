# LIMS · 雲原生實驗室資訊管理系統

![Version](https://img.shields.io/badge/version-v0.1.0-blue.svg)
![Frontend](https://img.shields.io/badge/frontend-Next.js%2016%20%2B%20React%2019-111827.svg)
![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20Python%203.12-059669.svg)
![Deploy](https://img.shields.io/badge/deploy-Docker%20%7C%20K3s%20%7C%20Argo%20CD-f97316.svg)
![Tests](https://img.shields.io/badge/tests-pytest%20%7C%20Vitest%20%7C%20Playwright-7c3aed.svg)

> Cloud-Native Laboratory Information Management System，NYCU 雲原生課程學期專案。

本專案是一套以完整實驗室流程為核心的 LIMS：從委託單建立、主管簽核、收樣與 WIP 管理、派工排程、實驗執行、結果報告，到取件結案、主管儀表板、異常告警與通知中心。系統採前後端分離與容器化部署，後端提供 FastAPI/OpenAPI 文件，前端提供角色導向操作介面，並以 PostgreSQL、Redis、Celery、Docker Compose、K3s 與 Argo CD 串起本地開發到雲原生部署的路徑。

- Frontend README: [frontend/README.md](frontend/README.md)
- Backend README: [backend/README.md](backend/README.md)
- 團隊分工: [docs/team_work_split.md](docs/team_work_split.md)
- 整合規範: [docs/integration_contract.md](docs/integration_contract.md)
<img width="2559" height="1359" alt="image" src="https://github.com/user-attachments/assets/fef87f82-aaba-4b71-9450-61d331b5947b" />


## 系統架構

```text
Browser
  |
  v
Frontend: Next.js 16 + React 19
  |
  v
Backend API: FastAPI + JWT cookie auth + OpenAPI
  |
  +--> PostgreSQL 16: orders, samples, WIP, machines, reports, users...
  +--> Redis 7: Celery broker, cache, SSE pub/sub
  +--> Celery worker: notifications, escalation, async jobs
  +--> Celery beat: scheduled escalation checks
  +--> TAS MQTT listener: optional phone-alert acknowledgement pipeline
```

部署與開發支援三種情境：

| 情境           | 用途                       | 入口                                                     |
| -------------- | -------------------------- | -------------------------------------------------------- |
| Docker Compose | 快速跑完整 stack           | [docker-compose.yml](docker-compose.yml)                 |
| 本地開發       | 分別啟動前後端，方便 debug | [Makefile](Makefile)                                     |
| K3s / Argo CD  | 雲原生部署與環境推進       | [deploy/k3s](deploy/k3s), [deploy/argocd](deploy/argocd) |

## Tech Stack

| 層                      | 技術                                                                         |
| ----------------------- | ---------------------------------------------------------------------------- |
| Frontend                | TypeScript, React 19, Next.js 16 App Router, TanStack Query, axios, Recharts |
| Backend                 | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic               |
| Database                | PostgreSQL 16                                                                |
| Background jobs         | Celery 5, Redis 7, Celery Beat                                               |
| Auth                    | JWT access/refresh token, httpOnly cookie, bcrypt                            |
| Realtime / notification | SSE, Redis pub/sub, in-app notifications, optional email/TAS phone callout   |
| Tests                   | pytest, httpx, pytest-asyncio, Vitest, Testing Library, Playwright           |
| CI / Deploy             | GitHub Actions, Docker Compose, K3s manifests, Argo CD applications          |

## 專案結構

```text
Cloud-Native-Development-Project/
├── README.md                    # 專案總覽
├── Makefile                     # install/dev/test/lint/docker/ci 常用指令
├── docker-compose.yml           # 完整本地 stack
├── docker-compose.ci.yml        # CI compose overlay
├── backend/                     # FastAPI 後端服務
│   ├── README.md
│   ├── app/
│   ├── alembic/
│   ├── scripts/
│   └── tests/
├── frontend/                    # Next.js 前端應用
│   ├── README.md
│   ├── app/
│   ├── components/
│   ├── src/
│   └── tests/
├── docs/                        # 需求、流程、整合規範與模組文件
├── tests/e2e/                   # Playwright 端到端測試
├── deploy/k3s/                  # Kubernetes/K3s manifests
└── deploy/argocd/               # Argo CD Application manifests
```

## 快速啟動

### Mode A: Docker 完整堆疊

適合 reviewer 或組員快速看到完整系統。

```bash
# 第一次可先準備後端 env
cp backend/.env.example backend/.env

# 建置並啟動 frontend、backend、postgres、redis、worker、beat、seed
make build
make up
```

啟動後：

| Service    |                       URL / Port | 說明                    |
| ---------- | -------------------------------: | ----------------------- |
| Frontend   |          <http://localhost:3000> | Next.js 操作介面        |
| Backend    |          <http://localhost:8000> | FastAPI API             |
| API docs   | <http://localhost:8000/api-docs> | Swagger UI              |
| Health     |   <http://localhost:8000/health> | 後端健康檢查            |
| PostgreSQL |                 `localhost:5432` | 預設 `lims/lims`        |
| Redis      |                 `localhost:6379` | Celery broker + pub/sub |

需要 pgAdmin 時：

```bash
docker compose --profile tools up pgadmin
```

pgAdmin 預設在 <http://localhost:5050>，帳密由 [docker-compose.yml](docker-compose.yml) 定義。

### Mode B: 本地開發模式

適合修改程式碼、debug、看 hot reload。

```bash
# 1. 只啟動基礎設施
make infra

# 2. 安裝後端依賴、套 migration、灌 demo seed
python -m venv backend/.venv
cd backend
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python scripts/seed_dev.py

# 3. 另一個 shell 啟動 backend
make -C .. dev-backend

# 4. 另一個 shell 啟動 frontend
cd ../frontend
npm ci
make -C .. dev-frontend
```

### Mode C: CI / 部署重現

```bash
make ci-backend
make ci-frontend
make ci-build
make ci-e2e
```

K3s 與 Argo CD 文件入口：

- [deploy/k3s/provision.sh](deploy/k3s/provision.sh)
- [deploy/k3s/base](deploy/k3s/base)
- [deploy/k3s/overlays/staging](deploy/k3s/overlays/staging)
- [deploy/k3s/overlays/prod](deploy/k3s/overlays/prod)
- [deploy/argocd/applications](deploy/argocd/applications)

## 預設帳號

`backend/scripts/seed_dev.py` 會建立 demo 使用者，方便直接登入前端測試角色權限。

| Email                    | 密碼        | 角色       |
| ------------------------ | ----------- | ---------- |
| `admin@example.com`      | `Admin1234` | 系統管理者 |
| `supervisor@example.com` | `Super1234` | 實驗室主管 |
| `engineer@example.com`   | `Engin1234` | 實驗室人員 |
| `requester@example.com`  | `Reque1234` | 廠區使用者 |

## 環境變數與安全

後端環境變數範本在 [backend/.env.example](backend/.env.example)。

```bash
cp backend/.env.example backend/.env
```

重要設定：

| 變數                                | 用途                                |
| ----------------------------------- | ----------------------------------- |
| `DATABASE_URL`                      | PostgreSQL async SQLAlchemy 連線    |
| `REDIS_URL`                         | Celery broker、cache、SSE pub/sub   |
| `JWT_SECRET`                        | JWT 簽章金鑰，正式環境必須更換      |
| `CORS_ORIGINS`                      | 允許的前端來源                      |
| `EMAIL_BACKEND`                     | `file` 或 `smtp`                    |
| `UPLOADS_DIR`                       | 檔案與 email outbox 儲存位置        |
| `CHT_API_KEY`, `CHT_SERVICE_NUMBER` | 中華電信 TAS phone callout，可留空  |
| `TAS_ENABLED`, `TAS_SN_KEY`         | TAS MQTT listener，可留空或設 false |

請勿提交 `.env`、真實密碼、API key 或個人電話。開發環境未設定 TAS/CHT credential 時，電話通知流程會 no-op，不影響一般功能。

## 核心功能

| 模組                   | 功能                                                           |
| ---------------------- | -------------------------------------------------------------- |
| 帳號 / 角色            | 登入登出、目前使用者、帳號管理、角色權限、實驗室與 master data |
| 委託單 / 簽核          | 建立送測需求、草稿、送出、主管核准/退回/拒絕、配額檢核         |
| 收樣 / WIP / 轉送      | 樣品收樣、分貨、WIP 狀態、交接與流轉                           |
| 機台 / Recipe / 派工   | 機台狀態、Recipe 管理、派工指派、排程策略                      |
| 實驗執行 / 報告 / 結案 | 上下機、進度紀錄、結果上傳、報告管理、取件結案                 |
| 異常 / 通知 / 儀表板   | Issue 管理、通知中心、告警升級、主管 dashboard、SSE 即時更新   |

主要需求與流程文件：

- [docs/total.md](docs/total.md)
- [docs/flow.md](docs/flow.md)
- [docs/development_standards.md](docs/development_standards.md)
- [docs/frontend_backend_structure.md](docs/frontend_backend_structure.md)
- [docs/order_management.md](docs/order_management.md)
- [docs/sample_management.md](docs/sample_management.md)
- [docs/machine_recipe.md](docs/machine_recipe.md)
- [docs/experiment_execute.md](docs/experiment_execute.md)
- [docs/result_manage.md](docs/result_manage.md)
- [docs/dashboard.md](docs/dashboard.md)

## API 與測試

後端啟動後可使用：

- Swagger UI: <http://localhost:8000/api-docs>
- ReDoc: <http://localhost:8000/api-redoc>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Health check: <http://localhost:8000/health>

常用測試與品質檢查：

```bash
make test-backend      # pytest --cov=app
make test-frontend     # vitest
make lint-backend      # ruff + ruff format --check + mypy
make lint-frontend     # eslint + tsc --noEmit
make ci-e2e            # full stack + Playwright
```

更多細節請看：

- [backend/README.md](backend/README.md)
- [frontend/README.md](frontend/README.md)
- [tests/README.md](tests/README.md)
