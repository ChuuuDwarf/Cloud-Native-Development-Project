# 四功能合併整合報告（four-functions-merge）

> 狀態快照：`feature/four-functions-merge` 分支，merge commit `b0a153a` 之上的整合工作。
> 本文件供 review 確認用。所有後端 CI 關卡（ruff / mypy / pytest）已綠。

---

## 1. 背景與核心決策

合併時發現團隊有**兩套後端架構在打架**，決定如下：

- **main（A/B/E）是正確基準**；merge 進來的 C/D 架構需向 main 對齊。
- **路由**：採 main 的集中式 `app/routes/` 套件 + `registry.py`，而非 C/D 原本的 `app/modules/<name>/router.py`。
- **資料模型衝突一律以 A/B 為準**（[[cd-yields-to-ab-models]]）：
  - `orders` → A 的 `OrderModel`（代理鍵 `id`，業務碼 `order_no`）
  - `wips` / `wip_histories` → B 的 schema（UUID 主鍵，業務碼 `wip_no`）
- **D 的執行流程資料**（B 的 wips 沒有的欄位）→ 放進 **D 自有側表 `wip_execution`**（以 `wip_no` 關聯），不動 A/B 的表。
- **狀態 / ID 橋接層放在 D 內部**：不放寬 B 的 CHECK、不改 A/B 主鍵。

---

## 2. 各階段改動

### Phase 0 — 資料庫地基
- 刪除 D 的 `app/db/models/orders.py`（`Order`）。
- `app/db/models/wips.py` 改寫為 **B 的正規 ORM model**（`Wip` / `WipHistory`，UUID 主鍵、英文 status + CHECK）。B 原本只有 migration 沒 ORM，此為照 migration 補的。
- 新增 `app/db/models/wip_execution.py`（D 側表）：`exec_status`（D 細粒度英文狀態）、`machine_id`、`recipe`、`operator`、`check_in_at`/`check_out_at`、`result_note`、`raw_data_url`、`data_verified`、`abort_*`。
- `app/db/models/__init__.py`：補註冊 `Report*`（原本漏掉，是 ImportError 主因）、`WipExecution`、`Recipe`。
- Migration 改為**單一線性鏈**：`a14aa7269a7f (E) → fea80b716b10 (A) → c65036646f0b (B) → 0001 (D 表) → 0002_c_machines (C 表)`。
  - `0001_initial.py` 重接到 B 的 head、只留 D 自有表（`reports*`/`storage*`/`wip_execution`），不再建 `orders`/`wips`/`wip_history`。
  - `0002` 的 `down_revision` 改為單一 `"0001"`（原本是 tuple merge）。

### Phase 1 — 橋接層
- `app/common/enums/role_d_zh.py` 新增 `WIP_EXEC_TO_B`：D 細粒度 `WipStatus` → B CHECK 合法的粗粒度 `wips.status`。
- 訂單狀態：D 寫入 A 的 `orders.status` 用英文 `OrderStatus.value`；closures 回應時轉回中文顯示。
- reports / storage 為 D 自有表，狀態維持中文。

### Phase 2 — D 三模組改寫
`experiment_runs` / `reports` / `closures` 的 repository / service / serializers：
- 改用 A 的 `OrderModel`（by `order_no`）+ B 的 `Wip`（by `wip_no`）+ `WipExecution` 側表。
- 狀態閘判 `exec_status`；履歷寫入 B 的 `wip_histories`（action / operator_name / description）。
- 中止申請（abort）移到側表。
- closures 的 applicant→email 改用 `applicant_id`（UUID）解析。

### Phase 3 — 路由換線
- 新增 6 個控制器：`app/routes/{experiment_runs,reports,closures,dispatches,machines,recipes}.py`，並註冊進 `registry.py`。
- 刪除 `app/modules/closures/router.py`（移到 `routes/`）。
- 移除衝突 stub：`others.py` 的 `GET /api/dispatches`、`workflow_views.py` 的 `GET /api/reports`。

### Phase 4 — 收尾
- `scripts/seed_dev.py`：補權限碼 `experiments:operate/review`、`reports:operate/review`、`closures:operate`；engineer 取得 operate 類、supervisor 取得 review 類。
- `scripts/seed_experiments.py`：全改寫，建立完整 chain（samples → orders → wips → wip_execution → histories → reports → storage），中文 demo 狀態於寫入時橋接成英文。

### 額外修正 — mypy 設定（解決「A 壞掉」假象）
- merge 把 `pyproject.toml` 改成 `plugins = ["pydantic.mypy"]`，導致 A（與 main 一字不差）的 order 程式碼被誤判 20 個錯誤。
- 已照 main 還原 `plugins = []`，並把 `auth.py`（`userId`）與 6 個新 route（`pageSize`）改回別名慣例。**A 完全未動。**

---

## 3. 驗證結果（真實 Postgres，非單純編譯）

| 項目 | 結果 |
|---|---|
| `alembic upgrade head` | ✅ 從零乾淨套用，單一 head `0002_c_machines` |
| schema 歸屬 | ✅ `orders`=A、`wips`=B（UUID）、`wip_execution`=D 側表、`wip_histories`(B) |
| ORM mapper 設定 | ✅ `configure_mappers()` 通過 |
| App import / 路由掛載 | ✅ 104 routes，`/api/reports`、`/api/dispatches` 各單一正確 controller |
| `seed_dev` + `seed_experiments` | ✅ 6 orders / 7 wips(+samples+execution) / 3 reports / 3 storage |
| D 業務邏輯 smoke | ✅ list/get/update_progress/check_closure 皆正確（狀態中文渲染、側表 join、跨表結單檢核） |
| **ruff check** | ✅ All checks passed |
| **ruff format** | ✅ 167 files formatted |
| **mypy** | ✅ 0 issues（145 files） |
| **pytest** | ✅ 96 passed |

---

## 4. 仍待處理（已記錄，非阻斷）

1. **樣品顯示名 = `None`**：`experiment_runs` serializer 的 `sample` 欄暫填 None（B 的 wips 只有 `sample_id` UUID）。若 UI 需要，需 join `samples` 取 `sample_name`。
2. **C 模組業務邏輯未 smoke**：machines/recipes/dispatches 只驗證了路由掛載與 import（本來就無 A/B 衝突）。
3. **無新增 C/D 正式 pytest**：現有 96 個測試涵蓋 B/E；C/D 以 runtime smoke 驗證取代。
4. **A 既有 order 程式碼**：未動（main 即如此）；mypy 在 `plugins=[]` 下通過。

---

## 5. 如何用 Docker 驗證

```bash
# 1. 起 DB 與快取
docker compose up -d postgres redis

# 2. 跑 migration（單一 head）
docker compose run --rm backend alembic upgrade head

# 3. 灌種子資料（先 seed_dev 再 seed_experiments）
docker compose run --rm backend python -m scripts.seed_dev
docker compose run --rm backend python -m scripts.seed_experiments

# 4. 起後端 + 前端
docker compose up -d backend frontend

# 後端 API 文件：http://localhost:8001/api-docs   （本機 .env: BACKEND_PORT=8001）
# 前端：        http://localhost:3000
# 預設帳號：    admin@example.com / Admin1234（其他見 scripts/seed_dev.py）
```

> ⚠️ 若既有的 `pgdata` volume 是舊 migration 圖譜灌的，`upgrade head` 可能不相容。
> 乾淨驗證可重置：`docker compose down -v`（**會清掉本機 DB 資料**）後再跑上面步驟。

可驗證的頁面：`/dispatch`、`/machine`、`/recipe`、`/execution`、`/report`、`/closure`、`/storage`。

---

## 6. 待 commit

所有變更在 `b0a153a` 之上、**尚未 commit**（約 30 檔）。建議切分：
1. 地基（models + migrations）
2. D 三模組改寫（含橋接 enum）
3. 路由換線（routes/ + registry + 移除衝突 stub）
4. 權限 + seed
5. mypy 設定還原（pyproject + auth + route 別名）
