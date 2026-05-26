# C / D 模組全功能參考（合併後現況）

> 對象：組員 C（機台 / Recipe / 派工）與組員 D（實驗執行 / 報告 / 結案倉儲）的後端 API。
> 每個端點列出：**路由函式 / Service 方法名稱、權限、功能、資料庫串接、逐步流程**。


---

## 0. 資料模型與跨模組串接總覽

| 資料表 | 擁有者 | 主鍵 | 業務碼 | 備註 |
|---|---|---|---|---|
| `orders` | **A** | `id` (int) | `order_no` | `OrderModel`；status 存英文 `OrderStatus` |
| `samples` | **B** | `id` (UUID) | `sample_no` | 無 ORM model（raw SQL） |
| `wips` | **B** | `id` (UUID) | `wip_no` | `Wip`；status 英文 + CHECK |
| `wip_histories` | **B** | `id` (UUID) | — | `WipHistory`（action/operator_name/description）|
| `wip_execution` | **D 側表** | `wip_no` | `wip_no` | `WipExecution`：D 執行細節，1:1 對應 `wips` |
| `machines` / `recipes` / `dispatches` | **C** | `id` (UUID) | `machine_id`/`recipe_id`/`dispatch_id` | status 存中文 |
| `reports` / `report_versions` / `report_attachments` | **D** | `report_id` / `id` | — | status 存中文 |
| `storage` / `storage_history` | **D** | `storage_id` / `id` | — | status 存中文 |

**橋接重點（D）**
- WIP 狀態雙層：D 細粒度狀態存在 `wip_execution.exec_status`（英文 `WipStatus`），同步寫一個粗粒度合法值到 B 的 `wips.status`（`WIP_EXEC_TO_B` 對應）。
- 委託單狀態：D 寫入 A 的 `orders.status` 用英文；closures 回應時用 `_order_zh` 轉回中文。
- ID 一律用業務碼 `order_no` / `wip_no` 串接（A/B 用代理鍵，無跨表 FK）。
- 回應信封：list = `{items,page,pageSize,total}`，單筆 = `{data,message}`。

**WIP 流程鏈（A→B→C→D 全程串接）**
- canonical（flow.md）：`created`→`waiting_schedule`→`scheduled`→`dispatched`→`running`→…→`completed`（中文：已建立→待派工→排程中→待上機→執行中→…→已完成）。
- 由 **C 驅動**（不碰 A/B 程式）：建立派工 → `waiting_schedule`；排程 suggest/replan → `scheduled`；指派 assign → `dispatched`（皆 `DispatchService._sync_wip_status`，前進式、不回退、寫 `wip_histories`）。
- **D 入口關卡**：`check_in` 要求 `wips.status == 'dispatched'`，沒派工不能上機 → 中間流程強制不可跳。

**Lab / 廠區 scoping（D 三模組共用，`app/common/dependencies/lab_scope.py` 的 `LabScope`）**
- 規則：`system_admin` → 全部 lab；`lab_supervisor` / `lab_engineer` → 只看 / 操作自己 lab；非 admin 且無 lab → 看不到任何資料。Celery 等系統情境用 `LabScope.system()`（不受限）。
- 解析：`CurrentUser` 只帶 `lab_id`(UUID)，`build_lab_scope` 由 `lab_id` → `labs.name`，再比對 `wips.lab_name`（存中文 `labs.name`）。
- 落點：三模組 `dependencies.py` 的 service factory 改 async，注入 `get_current_user` 並把 `LabScope` 傳進 service 建構式。
  - experiment_runs：`_require_wip` 集中做 per-row 檢查（涵蓋 get + 所有操作）；`list_wips` 在 repo 用 `lab_name` 過濾。
  - reports：報告的 lab = 來源 WIP 的 lab（`reports.wip_id == wips.wip_no`）；`_require_report` / `create_report` 檢查，list 用 join 過濾。
  - closures：order 可見 lab = 其底下 wips 的 lab（`order_labs()`）；`_enforce_order_access` 加在 check / to_pickup / inbound / outbound / close，list 用 join 過濾。
- 違反範圍 → `ForbiddenError`（403）。

**取件流程（`/storage` 畫面已移除）**
- 前端不再有獨立倉儲畫面；「待通知使用者取件 / 待取件」併入 **`/transfer`**（B 的 sample-action API：`POST /api/samples/{id}/actions` action `outbound` → `pickup_confirmed`）。
- D 的 `confirm_result` 完成 WIP 後會觸發 B 的 sample-flow（見 D-1 confirm），讓樣品自動進入 `/transfer` 的待交接 / 待通知取件。`/api/closures/*`（含 `/close` 結單、`/storage` 清單）後端仍保留供結單流程使用。

---

# C 模組

## C-1 機台管理 `/api/machines`（`app/routes/machines.py` → `MachineService`）

資料庫串接：僅 C 自有 `machines` 表。

### `GET /api/machines` — 列出機台
- 路由 `list_machines` → `MachineService.list_machines`
- 權限：登入即可。
- 流程：
  1. `MachineRepository.list_machines()` 查全部 `machines`。
  2. 每筆經 `machine_dict` 序列化為 camelCase 回傳。

### `POST /api/machines` — 新增機台
- 路由 `create_machine` → `MachineService.create`（權限 `machines:manage`）
- 流程：
  1. 以 `machine_id` 查重，已存在 → `ConflictError`。
  2. 建立 `Machine`（status 預設「閒置」、`supported_items` 存 JSONB 陣列）。
  3. `add` + `commit`，回傳序列化結果。

### `PATCH /api/machines/{machine_id}` — 更新機台
- 路由 `update_machine` → `MachineService.update`（`machines:manage`）
- 流程：
  1. `_require` 查機台，不存在 → `NotFoundError`。
  2. 覆寫 name / lab / supported_items / owner / utilization / last_maintenance（**不改 status**）。
  3. `commit` 回傳。

### `PATCH /api/machines/{machine_id}/status` — 切換機台狀態
- 路由 `update_machine_status` → `MachineService.update_status`（`machines:manage`）
- 流程：
  1. 驗證 status ∈ {閒置, 使用中, 保養中, 故障中, 停用}，否則 `ValidationError`。
  2. `_require` 取機台 → 設定 `status` → `commit`。

---

## C-2 Recipe 管理 `/api/recipes`（`app/routes/recipes.py` → `RecipeService`）

資料庫串接：僅 C 自有 `recipes` 表（`updated_at` 由 `TimestampMixin` 自動維護）。

### `GET /api/recipes` — 列出 Recipe
- 路由 `list_recipes` → `RecipeService.list_recipes`（登入即可）
- 流程：`RecipeRepository.list_recipes()` 查全部 → `recipe_dict` 序列化。

### `POST /api/recipes` — 新增 Recipe
- 路由 `create_recipe` → `RecipeService.create`（`recipes:manage`）
- 流程：
  1. 以 `recipe_id` 查重 → `ConflictError`。
  2. 建立 `Recipe`（`machine_ids` 存 JSONB 陣列、`parameters` 存 JSONB 物件）。
  3. `add` + `commit`。

### `PATCH /api/recipes/{recipe_id}` — 更新 Recipe
- 路由 `update_recipe` → `RecipeService.update`（`recipes:manage`）
- 流程：`_require` 取 Recipe → 覆寫 name/version/experiment_item/machine_ids/method/parameters/updated_by → `commit`。

---

## C-3 派工 / 排程 `/api/dispatches`（`app/routes/dispatches.py` → `DispatchService`）

資料庫串接：C 自有 `dispatches`（status 中文：待派工 / 排程中 / 待上機）；**讀** `machines`（媒合 / 驗證）、`recipes`（指派驗證）。`wip_id` / `order_id` 為業務碼字串，無 FK。

### `GET /api/dispatches` — 列出派工單
- 路由 `list_dispatches` → `DispatchService.list_dispatches`（登入即可）
- 流程：查全部 `dispatches` → `dispatch_dict` 序列化。

### `POST /api/dispatches` — 建立派工單（連動 WIP 進待派工）
- 路由 `create_dispatch` → `DispatchService.create`（`dispatches:manage`）
- 流程：
  1. 以 `dispatch_id` 查重 → `ConflictError`。
  2. 建立 `Dispatch`，狀態「待派工」、記錄 `created_by`。
  3. **`_sync_wip_status`**：把對應 WIP（`wip_id`==`wips.wip_no`）前進到 `waiting_schedule`（待派工）+ 履歷「送入待派工」。
  4. `commit`。

### `POST /api/dispatches/suggest` — 產生排程建議
- 路由 `suggest_dispatches` → `DispatchService.suggest`（`dispatches:manage`）
- 流程：
  1. 驗證策略 ∈ {FIFO, Priority First, Earliest Due Date, Least Setup Change, Hybrid}。
  2. 取所有「待派工」`dispatches` 與全部 `machines`。
  3. 依策略 `_order_by_strategy` 排序；逐筆 `_match_machine`（找 `supported_items` 含該實驗項目的機台）設 `suggested_machine_id`、狀態轉「排程中」、記 `strategy`。
  4. **逐筆 `_sync_wip_status`**：對應 WIP 前進到 `scheduled`（排程中）+ 履歷「排程」。
  5. `commit`，回傳受影響清單。

### `POST /api/dispatches/replan` — 重新排程
- 路由 `replan_dispatches` → `DispatchService.replan`（`dispatches:manage`）
- 流程：同 suggest（WIP 也連動前進到 `scheduled`），但範圍是「待派工 + 排程中」，並額外記錄 `replan_reason`。

### `POST /api/dispatches/{dispatch_id}/assign` — 指派機台 / Recipe（含 C→B 連動）
- 路由 `assign_dispatch` → `DispatchService.assign`（`dispatches:manage`）
- 流程：
  1. `_require` 取派工單，狀態須為「排程中」否則 `ConflictError`。
  2. 取 `machine`（不存在→404）；驗證機台 `supported_items` 含該實驗項目。
  3. 取 `recipe`（不存在→404）；驗證 recipe `experiment_item` 相符、且 `machine_ids` 含該機台。
  4. 寫入 `assigned_machine_id` / `assigned_recipe_id` / `scheduled_start` / `scheduled_end` / `assigned_by`，派工單狀態轉「待上機」。
  5. **`_sync_wip_status`（C→B 連動，打通派工→上機）**：以 `dispatch.wip_id`（= `wips.wip_no`）取 B 的 WIP，前進到 `dispatched`（待上機）+ 設 `dispatched_at` + 寫 `wip_histories`（action「派工指派」）。此處 `strict=True`：WIP 已在執行 / 結束 → `ConflictError`；查無對應 WIP（demo placeholder）→ 記 log 不阻擋。
  6. `commit`。

---

# D 模組

> D 的 WIP 操作同時牽動三張表：**B 的 `wips`**（粗粒度狀態 + 進度 + 時間戳）、**D 的 `wip_execution`**（細粒度 `exec_status` + 機台/結果/中止）、**B 的 `wip_histories`**（履歷）；訂單狀態則寫 **A 的 `orders`**。

## D-1 實驗執行 `/api/experiment-runs`（`app/routes/experiment_runs.py` → `ExperimentRunService`）

### `GET /api/experiment-runs` — 列出 WIP
- 路由 `list_experiment_runs` → `ExperimentRunService.list_wips`（登入即可，可帶 `status` 中文過濾；**套用 lab scoping，見 §0**）
- 流程：
  1. `list_wips()` 查 B 的 `wips`（eager-load `history`）。
  2. `get_execs_map()` 批次取對應 `wip_execution`。
  3. 每筆 `wip_dict(wip, exec)` 合併序列化（`exec_status` 經 `WIP_ZH` 渲染為中文 status；機台/結果欄位取自側表）。
  4. 有 `status` 參數則用渲染後中文過濾。

### `GET /api/experiment-runs/{wip_id}` — WIP 詳情
- 路由 `get_experiment_run` → `ExperimentRunService.get_wip`
- 流程：取 `wips`（含 history）+ `wip_execution` → `wip_dict` 合併回傳。

### `POST /api/experiment-runs/{wip_id}/check-in` — 上機登記
- 路由 `check_in` → `ExperimentRunService.check_in`（`experiments:operate`）
- 流程：
  1. `_require_wip` 取 B 的 wip。
  2. **入口關卡（中間流程強制）**：`wips.status` 須為 `dispatched`（待上機，由 C 的派工 assign 推進）否則 `ConflictError`「WIP 尚未派工…」——沒派工不能上機。
  3. `ensure_exec` 取/建側表列；閘 `exec_status` 須為 `waiting_load`，否則 `ConflictError`。
  4. `_set_status(RUNNING)`：側表 `exec_status=running`、同步 B `wips.status=running`。
  5. 側表寫 operator / machine_id / recipe / check_in_at。
  6. `_event`：新增 B `wip_histories`（action「上機」）。
  7. 查 A 的 `orders`（by `order_no`），若為 `scheduled` → 轉 `in_progress`。
  8. `commit`。

### `POST /api/experiment-runs/{wip_id}/check-out` — 下機登記
- 路由 `check_out` → `ExperimentRunService.check_out`（`experiments:operate`）
- 流程：閘 `exec_status=running` → `_set_status(UNLOADED)`、側表寫 check_out_at、履歷「下機」→ `commit`。

### `PATCH /api/experiment-runs/{wip_id}/progress` — 更新進度
- 路由 `update_progress` → `ExperimentRunService.update_progress`（`experiments:operate`）
- 流程：閘 `exec_status=running` → 寫 B `wips.progress`、履歷「更新進度」→ `commit`。

### `POST /api/experiment-runs/{wip_id}/result` — 上傳結果
- 路由 `upload_result` → `ExperimentRunService.upload_result`（`experiments:operate`）
- 流程：
  1. 閘 `exec_status` ∈ {running, unloaded}。
  2. 若仍 running → 自動補 check_out_at + 履歷「下機」。
  3. `_set_status(WAITING_CONFIRM)`；側表寫 result_note / raw_data_url / data_verified；B `wips.progress=100`；履歷「上傳結果」。
  4. `commit` → `_refresh_order_after_result`（該訂單所有 WIP 的 `exec_status` 皆達待確認/完成/終止時，A `orders` → `waiting_result_confirm`）→ 再 `commit`。

### `POST /api/experiment-runs/{wip_id}/confirm` — 確認結果（含 sample 推進）
- 路由 `confirm_result` → `ExperimentRunService.confirm_result`（`experiments:operate`）
- 流程：
  1. 閘 `exec_status=waiting_confirm` 且 `data_verified=True`（否則 `ValidationError`）→ `_set_status(COMPLETED)`、履歷「確認結果」→ `commit`。
  2. `_refresh_order_after_confirm`（全 WIP 結束 → A `orders=completed`）→ `commit`。
  3. **`_advance_sample_flow`（Point 2，串接 `/transfer`）**：呼叫 B 的 `wip_service.update_sample_to_pending_transfer_if_ready`，依該 sample 的實驗序列推進 B 的 `samples`：
     - 中間站完成 → sample `pending_transfer` + 位置「{lab} 實驗暫存區」+ 履歷「…可交接至 {下一 lab}」（出現在 `/transfer` 可交接清單）。
     - 最後一站完成（後續無實驗）→ sample `split` + 履歷「…可通知使用者取件」（出現在 `/transfer` 待通知使用者取件）。
     - best-effort：確認本身已 commit，sample-flow 失敗只記 log，不讓請求失敗。`wip.sample_id` 為空則略過。

### `POST /api/experiment-runs/{wip_id}/abort-request` — 提出中止申請
- 路由 `abort_request` → `ExperimentRunService.request_abort`（`experiments:operate`）
- 流程：`ensure_exec`；閘 未結束且無 pending 申請 → 側表寫 abort_reason/by/status=「待主管判定」/requested_at、履歷「提出中止申請」→ `commit`。

### `POST /api/experiment-runs/{wip_id}/abort-review` — 主管審核中止
- 路由 `abort_review` → `ExperimentRunService.review_abort`（`experiments:review`）
- 流程：閘 `abort_status=待主管判定`。
  - 核准：`_set_status(TERMINATED)`、abort_status=「已終止」、履歷「主管核准終止」→ commit → 全 WIP 結束則 A `orders=completed`。
  - 駁回：`_set_status(RUNNING)`、abort_status=「已駁回」、履歷「主管駁回」、A `orders=in_progress`。

### `POST /api/experiment-runs/{wip_id}/machine-signal` — 機台完成訊號（202）
- 路由 `machine_signal` → Celery `app.workers.experiment_tasks.machine_complete` →（背景）`ExperimentRunService.apply_machine_completion`
- 流程：
  1. 先 `get_wip` 確認存在。
  2. 丟 `machine_complete.delay(wip_id)` 給 Celery；broker 不可用則同步 `apply_machine_completion` 退回。
  3. `apply_machine_completion`：閘 `exec_status` ∈ {running, unloaded} → 自動下機 + `_set_status(WAITING_CONFIRM)`、進度 100、補 result_note/raw_data_url、履歷「機台自動數據蒐集」→ 刷新訂單狀態。

---

## D-2 實驗報告 `/api/reports`（`app/routes/reports.py` → `ReportService`）

資料庫串接：D 自有 `reports` / `report_versions` / `report_attachments`（狀態中文）；**讀** B 的 `wips`、D 的 `wip_execution`（建立時取 result_note 與結果閘）、A 的 `orders`（發布時改狀態）。

### `GET /api/reports` — 列出報告
- 路由 `list_reports` → `ReportService.list_reports`（登入即可，可帶 `status` / `order_id`；**套用 lab scoping，見 §0**）
- 流程：查 `reports`（eager-load versions/attachments，依條件過濾；非 admin 以來源 WIP 的 lab join 過濾）→ `report_dict`。

### `GET /api/reports/{report_id}` — 報告詳情
- 路由 `get_report` → `ReportService.get_report` → 含版本紀錄與附件。

### `POST /api/reports` — 建立報告草稿
- 路由 `create_report` → `ReportService.create_report`（`reports:operate`，body 帶 `wip_id`）
- 流程：
  1. 取 B 的 wip（不存在→404）+ D 的 `wip_execution`。
  2. 閘：`exec_status` ∈ {waiting_confirm, completed} 否則 `ConflictError`。
  3. 以 `count_reports_for_order(order_no)` 產生報告編號 `RPT-{order尾碼}-{序號}`。
  4. 標題用 `wip.order_no` + `wip.experiment_item`；摘要用 `wip_no` + 實驗項目；結論取側表 `result_note`。
  5. 建 `Report`（狀態「草稿」）+ 第 1 版 `ReportVersion` → `add` + `commit`。

### `PATCH /api/reports/{report_id}` — 編輯報告
- 路由 `edit_report` → `ReportService.edit_report`（`reports:operate`）
- 流程：閘 狀態 ∈ {草稿, 已改版} → 更新 summary/conclusion、（可選）新增 `ReportAttachment` → `commit`。

### `POST /api/reports/{report_id}/submit` — 送審
- 路由 `submit_report` → `ReportService.submit_report`（`reports:operate`）
- 流程：閘 {草稿, 已改版} → 狀態轉「待審核」、加版本 → `commit`。

### `POST /api/reports/{report_id}/review` — 主管審核
- 路由 `review_report` → `ReportService.review_report`（`reports:review`）
- 流程：閘 「待審核」 → 核准轉「已確認」/ 退回轉「已改版」、加版本（記評語）→ `commit`。

### `POST /api/reports/{report_id}/publish` — 發布並回傳
- 路由 `publish_report` → `ReportService.publish_report`（`reports:operate`）
- 流程：閘 「已確認」 → 狀態轉「已回傳」、加版本；查 A 的 `orders`，若為 `completed` → 轉 `waiting_report_return`；`commit`。

---

## D-3 結案與倉儲 `/api/closures`（`app/routes/closures.py` → `ClosureService`）

資料庫串接：**讀** A `orders`、B `wips`、D `wip_execution`、D `reports`、D `storage`；**寫** A `orders.status`（英文，回應轉中文）、D `storage`/`storage_history`；email 解析查 E `users`。

### `GET /api/closures` — 各委託單結單狀態
- 路由 `list_closures` → `ClosureService.list_closures`（登入即可；**套用 lab scoping，見 §0**）
- 流程：取（非 admin 以 wips lab join 過濾後的）`orders`，對每張 `order_no` 計算結單條件（`_compute_closure`）。

### `GET /api/closures/storage` — 倉儲取件清單
- 路由 `list_storage` → `ClosureService.list_storage`（可帶 `status`；**套用 lab scoping，見 §0**）
- 流程：查 D `storage`（eager-load history；非 admin 以 order→wips lab join 過濾）→ `storage_dict`。

### `GET /api/closures/{order_id}/check` — 結單條件檢查
- 路由 `check_closure` → `ClosureService.check_closure`（**先 `_enforce_order_access` 做 lab 授權，見 §0**，再 `_compute_closure`）
- 流程（六條件，全滿足才 `canClose`）：
  1. 取 A `orders`（by order_no）、該訂單的 B `wips`、對應 `wip_execution`。
  2. 報告：`count_reports_in_status`（已發布/已回傳）> 0。
  3. 樣品：D `storage` 全在 已入庫/待返還/已取件。
  4. 無未結中止：所有 `wip_execution.abort_status` ≠「待主管判定」。
  5. 全 WIP 結束：每筆 `exec_status` ∈ {completed, terminated}。
  6. 數據已收集：completed 的 WIP 其側表 `result_note` 非空。
  7. 回傳 `orderId` / `status`（英文經 `_order_zh` 轉中文）/ `canClose` / 各條件。

### `POST /api/closures/{order_id}/to-pickup` — 轉待取件
- 路由 `to_pickup` → `ClosureService.to_pickup`（`closures:operate`）
- 流程：
  1. 先 `check_closure`，未達 `canClose` → `ConflictError`（列出未滿足條件）。
  2. 閘 訂單狀態 ∈ {completed, waiting_report_return} → 設 A `orders=waiting_pickup`、`commit`。
  3. `_send_pickup_reminder`：用 `applicant_id`（UUID）查 E `users.email`；查不到則退回 placeholder。透過 Celery `send_pickup_reminder_email.delay`，broker 不可用則同步 `.run`。

### `POST /api/closures/{order_id}/inbound` — 入庫
- 路由 `inbound` → `ClosureService.storage_inbound`（`closures:operate`）
- 流程：取該訂單 D `storage` 列，將「實驗室」狀態者轉「已入庫」並寫 `storage_history`（入庫）→ `commit`。

### `POST /api/closures/{order_id}/outbound` — 出庫取件
- 路由 `outbound` → `ClosureService.storage_outbound`（`closures:operate`）
- 流程：閘 訂單 `waiting_pickup` → 所有 `storage` 轉「已取件」+ 寫 `storage_history`（出庫取件）→ `commit`。

### `POST /api/closures/{order_id}/close` — 結案
- 路由 `close_order` → `ClosureService.close_order`（`closures:operate`）
- 流程：閘 訂單 `waiting_pickup`、且 `storage` 全為「已取件」否則 `ConflictError` → 設 A `orders=closed` → `commit`。

---

## 附：權限碼（`scripts/seed_dev.py`）

| 權限碼 | 授予角色 |
|---|---|
| `machines:manage` / `recipes:manage` / `dispatches:manage` | lab_engineer（+ supervisor 繼承）|
| `experiments:operate` / `reports:operate` / `closures:operate` | lab_engineer（+ supervisor）|
| `experiments:review` / `reports:review` | lab_supervisor 專屬 |

讀取類端點僅需登入（`get_current_user`）。
