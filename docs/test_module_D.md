# 組員 D 模組：實驗執行 / 報告 / 結單 / 倉儲

對應 `docs/team_work_split.md` 組員 D，與 `docs/development_standards.md` 交付標準。

## 0. 技術棧（v0.2）

| 層 | 技術 | 狀態 |
|----|------|------|
| 前端 | TypeScript + React 19 + Next.js 16 | ✅ |
| 後端 | Python + FastAPI | ✅ |
| 資料庫 | PostgreSQL 16 + SQLAlchemy 2.0 ORM | ✅（取代原記憶體 store） |
| Migration | Alembic（初始 migration `0001`） | ✅ |
| 背景任務 | Celery + Redis | ✅（機台自動數據蒐集） |
| 佈署 | docker-compose（db / redis / backend / worker / frontend） | ✅ |

## 1. 交付內容

| 類別 | 內容 |
|------|------|
| 前端頁面 | `/execution`、`/report`、`/closure`、`/storage`（已加入 Sidebar 導覽） |
| 後端 API | `/api/experiments`、`/api/reports`、`/api/closures`（含 `/api/closures/storage`、機台訊號 `machine-signal`） |
| 共用 enum | `backend/app/enums.py`（OrderStatus / WipStatus / ReportStatus / StorageStatus / Role） |
| ORM / 序列化 | `backend/app/models.py`（8 張表 + camelCase 序列化器，對前端透明） |
| 狀態轉換 | 集中於 `store/` 套件（依功能分檔：experiments / reports / closures / common / seed），接收 SQLAlchemy Session，路由層只驗權與呼叫 |
| 背景任務 | `backend/app/tasks.py`（Celery `machine_complete`） |
| 種子資料 | `store.seed_if_empty()`（DB 為空時寫入）；前端 `lib/mock.ts` 離線 fallback |
| 權限 | JWT 優先 / X-Role 過渡（`deps.current_role`）；**角色繼承：主管含實驗室人員權限**，主管專屬操作（中止審核、報告審核）仍只限主管；違規回 403 |

## 2. 啟動方式（docker-compose）

```bash
cd <專案根目錄>
docker compose up --build        # 起 db + redis + backend + worker + frontend
```

- 前端：http://localhost:3000
- 後端：http://localhost:8005（容器內 8000，對外映射 8005，避開本機既有服務）
- DB：host 5433 → 容器 5432；Redis：host 6380 → 容器 6379
- 後端啟動順序：`alembic upgrade head`（建表）→ uvicorn → lifespan 寫入種子資料

> 連線字串／broker 皆由 docker-compose 的環境變數注入（`DATABASE_URL`、`CELERY_BROKER_URL`）。
> 重置資料：`docker compose down -v`（清掉 `pgdata` volume）。

> 若只開前端、不開後端，前端會顯示「離線展示資料」橫幅並改用 `lib/mock.ts`，頁面仍可瀏覽但操作不會儲存。

## 3. 狀態流程（依 docs/flow.md）

- WIP：`待上機 → 執行中 → 已下機 → 待確認 → 已完成`；異常經主管核准 → `已終止`
- 委託單（D 階段）：`實驗中 → 待結果確認 → 已完成 → 待報告回傳 → 待取件 → 已結案`；中止申請 → `待主管判定`
- 報告：`草稿 → 待審核 → 已確認 → 已發布 → 已回傳`（退回 → `已改版`）

關鍵規則：上下貨履歷不可刪除；機台回報完成不直接結案，需進「待確認」；實驗室人員不可直接終止，須主管審核。

## 4. API Contract（節錄）

回應格式依 `development_standards.md` 6.2；JSON 欄位 camelCase；錯誤格式 `{ "error": { "code", "message" } }`。

| Method | Path | 權限 | 說明 / 狀態轉換 |
|--------|------|------|------|
| GET | `/api/experiments` | 全部 | 列出 WIP（`?status=` 過濾） |
| GET | `/api/experiments/{wipId}` | 全部 | WIP 詳情含機台履歷 |
| POST | `/api/experiments/{wipId}/check-in` | 實驗室人員 | 待上機→執行中（operator/machineId/recipe 必填） |
| POST | `/api/experiments/{wipId}/check-out` | 實驗室人員 | 執行中→已下機 |
| PATCH | `/api/experiments/{wipId}/progress` | 實驗室人員 | 更新進度（0-100） |
| POST | `/api/experiments/{wipId}/result` | 實驗室人員 | →待確認（note 必填；dataVerified） |
| POST | `/api/experiments/{wipId}/confirm` | 實驗室人員 | 待確認→已完成（須 dataVerified） |
| POST | `/api/experiments/{wipId}/abort-request` | 實驗室人員 | 提出中止→委託單待主管判定 |
| POST | `/api/experiments/{wipId}/abort-review` | 實驗室主管 | approve=終止 / 否=恢復執行中 |
| POST | `/api/experiments/{wipId}/machine-signal` | 系統/機台 | 觸發 Celery 背景任務：自動寫入數據→待確認（broker 不可用時同步退回） |
| GET | `/api/reports` | 全部 | 列表（`?status=`、`?orderId=`） |
| POST | `/api/reports` | 實驗室人員 | 從 WIP 建立草稿（wipId） |
| PATCH | `/api/reports/{id}` | 實驗室人員 | 編輯摘要/結論/附件 |
| POST | `/api/reports/{id}/submit` | 實驗室人員 | 草稿→待審核 |
| POST | `/api/reports/{id}/review` | 實驗室主管 | approve=已確認 / 否=已改版 |
| POST | `/api/reports/{id}/publish` | 人員/主管 | 已確認→已回傳；委託單→待報告回傳 |
| GET | `/api/closures` | 全部 | 各委託單結單條件達成狀況 |
| GET | `/api/closures/storage` | 全部 | 倉儲清單（`?status=`） |
| GET | `/api/closures/{orderId}/check` | 全部 | 結單條件檢核 |
| POST | `/api/closures/{orderId}/to-pickup` | 實驗室人員 | 條件全滿足→待取件 |
| POST | `/api/closures/{orderId}/inbound` | 實驗室人員 | 入庫 |
| POST | `/api/closures/{orderId}/outbound` | 實驗室人員 | 待取件→出庫取件 |
| POST | `/api/closures/{orderId}/close` | 實驗室人員 | 待取件→已結案（須已取件） |

`X-Role` 代碼：`user` / `staff` / `chief` / `admin`（HTTP 標頭不可帶中文）。

## 5. 模組測試紀錄：實驗執行 / 報告 / 結單

| 項目 | 內容 |
|------|------|
| 負責人 | 組員 D |
| 測試日期 | 2026-05-21 |
| 對應文件 | experiment_execution.md / experiment_report.md / result_manage.md |
| 測試環境 | local（uvicorn + 直接呼叫 store 與 HTTP 端對端） |
| 前端頁面 | /execution, /report, /closure, /storage |
| API 範圍 | /api/experiments, /api/reports, /api/closures |

### 測試案例

| 編號 | 測試目標 | 角色 | 前置資料 | 操作步驟 | 預期結果 | 實際結果 | 狀態 |
|------|----------|------|----------|----------|----------|----------|------|
| T-001 | 上機登記 | 實驗室人員 | WIP-0892-01 待上機 | check-in 帶 operator/machine/recipe | WIP→執行中、委託單→實驗中、新增履歷 | 符合 | Pass |
| T-002 | 上機必填檢查 | 實驗室人員 | 待上機 WIP | check-in 只帶 operator | 回 422 VALIDATION_ERROR | 符合 | Pass |
| T-003 | 非人員上機 | 實驗室主管 | 待上機 WIP | 以 chief check-in | 回 403 FORBIDDEN | 符合 | Pass |
| T-004 | 上傳結果進待確認 | 實驗室人員 | 執行中 WIP | result note + dataVerified | WIP→待確認、progress=100 | 符合 | Pass |
| T-005 | 未驗證數據不可確認 | 實驗室人員 | 待確認且 dataVerified=false | confirm | 回 422，要求先驗證 | 符合 | Pass |
| T-006 | 狀態不合法確認 | 實驗室人員 | 執行中 WIP | confirm | 回 409 INVALID_STATE | 符合 | Pass |
| T-007 | 中止申請不可直接終止 | 實驗室人員 | 執行中 WIP | abort-request | WIP 仍在、委託單→待主管判定 | 符合 | Pass |
| T-008 | 主管核准終止 | 實驗室主管 | 待主管判定 WIP-0895-01 | abort-review approve | WIP→已終止 | 符合 | Pass |
| T-009 | 非主管審核中止 | 實驗室人員 | 待主管判定 WIP | abort-review | 回 403 FORBIDDEN | 符合 | Pass |
| T-010 | 報告完整流程 | 人員→主管→人員 | 已完成 WIP | create→submit→review(approve)→publish | 草稿→待審核→已確認→已回傳、委託單→待報告回傳 | 符合 | Pass |
| T-011 | 結單條件未滿足 | 實驗室人員 | WO-0894 待結果確認 | to-pickup | 回 409，列出未滿足條件 | 符合 | Pass |
| T-012 | 結單取件閉環 | 實驗室人員 | WO-0896 待取件 | outbound→close | 倉儲→已取件、委託單→已結案 | 符合 | Pass |
| T-013 | 查無資料 | 全部 | 無 | GET /api/experiments/WIP-XXXX | 回 404 NOT_FOUND | 符合 | Pass |
| T-014 | 前端離線 fallback | — | 後端未啟動 | 開啟各頁 | 顯示離線橫幅 + mock 資料，操作鈕禁用 | 符合 | Pass |
| T-015 | 機台訊號背景任務 | 系統 | 執行中 WIP | machine-signal → 等 worker | 回 202+taskId；約 5s 後 WIP→待確認、dataVerified=false、履歷有「機台自動數據蒐集」 | 符合 | Pass |
| T-016 | 資料持久化 | — | 已操作過的資料 | `docker compose restart backend` | total 仍 7（種子未重複）、先前狀態保留 | 符合 | Pass |
| T-017 | Alembic migration | — | 空 DB | `alembic upgrade head` | 建立 8 張表，App 正常啟動 | 符合 | Pass |

### 5.1 自動化測試（pytest）

測試碼位於 `backend/tests/`，對應 CI 的 `backend` job（`pytest --cov`）：

| 檔案 | 涵蓋 |
|------|------|
| `tests/conftest.py` | 測試用 SQLite（免 Postgres）、每測試重建 schema、Celery 設為 eager（免 Redis）、TestClient fixture |
| `tests/test_experiments.py` | 上機/結果/確認/中止/權限/404/機台訊號（12 例） |
| `tests/test_reports.py` | 報告全流程、退回改版、權限、404（7 例） |
| `tests/test_closures.py` | 結單條件、轉待取件、出庫結案、權限、404（8 例） |

執行（本機需 `pip install -r requirements-dev.txt`）：

```bash
cd backend
pytest --cov=. --cov-report=term-missing
```

結果：**27 passed，覆蓋率 90%**（app 套件）。

### 5.2 驗證指令與結果（全部實際跑過）

- 後端品質（對應 CI `backend-quality` job）：`ruff check .`、`ruff format --check .`、`mypy .` 全數通過
- 後端測試（對應 CI `backend` job）：`pytest --cov` → 27 passed / 90%
- 後端 **Docker 端對端**（`docker compose up`）：
  - Alembic `0001` migration 在 Postgres 16 建表成功
  - Celery：`machine-signal` 回 202 + taskId，worker log `Task machine_complete[...] succeeded in 5.08s`，WIP 正確轉「待確認」
  - 持久化：restart backend 後資料保留、種子未重複
- 前端：`npm run lint`、`npm run build`（standalone，4 頁 prerender）通過

> CI 注意：`backend` 與 `backend-quality` 兩個 job 的安裝步驟已改為 `pip install -r requirements-dev.txt`（pytest/ruff/mypy 在 dev 依賴，不進 runtime image）。

## 6. 已知限制

- 權限解析集中在 `deps.current_role`：優先 `Authorization: Bearer <JWT>`，未帶時退回展示用 `X-Role`（已在 deps.py 標記為「JWT 上線後可整段刪除」）。JWT 密鑰、演算法、角色 claim 名稱待與組員 E 對齊（環境變數 `JWT_SECRET` / `JWT_ALG` / `JWT_ROLE_CLAIM`）。
- 報告/原始數據「上傳」僅記錄檔名與連結字串，未實作真實檔案上傳與儲存。
- 機台自動化數據蒐集以 `machine-signal` 端點 + Celery 任務模擬（含 `time.sleep`），尚未接真實機台訊號來源；數據內容為產生的占位字串。
- 結單條件中「樣品已入庫或待返還」依賴收樣模組（組員 B）建立的倉儲紀錄；種子資料中部分委託單無倉儲紀錄，故結單條件會顯示未滿足（屬正確行為）。
- `enums.py`、`models.py` 為 D 範圍的最小共用版本；與組員 E 整合時應合併為單一權威 schema 來源。
- migration 目前只有初始版 `0001`（手寫）；後續 schema 變更建議改用 `alembic revision --autogenerate`。
- 種子資料寫在 `store.seed_if_empty()`，僅在 DB 為空時執行；要重新種子需 `docker compose down -v`。

## 7. 交接給下一模組

- 委託單最終狀態 `已結案`、報告 `已回傳`、倉儲 `已取件` 可供 **組員 E 儀表板** 聚合（待簽核/WIP/報告/逾期統計）。
- WIP 履歷、報告版本、倉儲履歷皆為可展示的操作紀錄，供整合測試 demo 一筆委託單從建立到結案使用。
