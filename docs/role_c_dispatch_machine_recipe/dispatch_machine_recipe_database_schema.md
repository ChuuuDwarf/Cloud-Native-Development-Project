## 派工排程與機台 Recipe 資料庫欄位需求

目前「派工排程、機台管理、Recipe 管理」後端會建立 4 張資料表：`users`、`machines`、`recipes`、`dispatches`。

### users（使用者與角色）

| 欄位名稱 | 型態 | 說明 |
|----------|------|------|
| user_id | TEXT PK | 使用者 ID，例如 `u-lab`、`u-supervisor` |
| name | TEXT NOT NULL | 使用者姓名 |
| role | TEXT NOT NULL | 使用者角色：`廠區使用者` / `實驗室人員` / `實驗室主管` / `系統管理者` |
| department | TEXT NOT NULL | 所屬部門，例如 `實驗室`、`資訊部`、`F12 廠` |
| lab | TEXT | 所屬實驗室，可為空；例如 `材料分析實驗室` |

### machines（機台主檔）

| 欄位名稱 | 型態 | 說明 |
|----------|------|------|
| machine_id | TEXT PK | 機台 ID，例如 `OPT-001` |
| name | TEXT NOT NULL | 機台名稱 |
| lab | TEXT NOT NULL | 機台所在實驗室 |
| status | TEXT NOT NULL | 機台狀態：`閒置` / `使用中` / `保養中` / `故障中` / `停用` |
| supported_items | TEXT[] NOT NULL | 支援的實驗項目清單 |
| utilization | INTEGER NOT NULL DEFAULT 0 | 稼動率，0 到 100 |
| owner | TEXT NOT NULL | 機台負責人 |
| last_maintenance | TEXT NOT NULL | 最近保養時間或保養紀錄文字 |

### recipes（Recipe 設定）

| 欄位名稱 | 型態 | 說明 |
|----------|------|------|
| recipe_id | TEXT PK | Recipe ID，例如 `RCP-SEM-001` |
| name | TEXT NOT NULL | Recipe 名稱 |
| version | TEXT NOT NULL | Recipe 版本 |
| experiment_item | TEXT NOT NULL | 對應實驗項目，需與 WIP 的 `experiment_item` 相同 |
| machine_ids | TEXT[] NOT NULL | 可使用此 Recipe 的機台 ID 清單 |
| method | TEXT NOT NULL | 實驗方法或操作方法 |
| parameters | JSONB NOT NULL DEFAULT '{}'::jsonb | Recipe 參數，例如倍率、溫度、時間等 |
| updated_by | TEXT NOT NULL | 最後更新者 |
| updated_at | TIMESTAMPTZ NOT NULL | 最後更新時間 |

### dispatches（WIP 派工與排程）

| 欄位名稱 | 型態 | 說明 |
|----------|------|------|
| dispatch_id | TEXT PK | 派工單 ID，例如 `DSP-001` |
| wip_id | TEXT NOT NULL | WIP ID，例如 `WIP-001` |
| order_id | TEXT NOT NULL | 委託單 ID，例如 `WO-001` |
| experiment_item | TEXT NOT NULL | 實驗項目，需對應機台支援項目與 Recipe 實驗項目 |
| priority | TEXT NOT NULL | 優先級：`一般` / `高` / `特急` |
| due_at | TEXT NOT NULL | 交期，目前以前端日期時間選擇器填入，格式建議 `YYYY-MM-DD HH:mm` |
| status | TEXT NOT NULL | WIP 派工狀態：`待派工` / `排程中` / `待上機` |
| suggested_machine_id | TEXT | 系統建議機台 ID |
| assigned_machine_id | TEXT | 實際確認派工的機台 ID |
| assigned_recipe_id | TEXT | 實際確認派工的 Recipe ID |
| scheduled_start | TEXT | 系統預估或最終派工開始時間，格式建議 `YYYY-MM-DD HH:mm` |
| scheduled_end | TEXT | 系統預估或最終派工結束時間，格式建議 `YYYY-MM-DD HH:mm` |
| created_by | TEXT | 建立 WIP 的使用者名稱 |
| assigned_by | TEXT | 確認派工的使用者名稱 |
| strategy | TEXT | 產生建議或重排使用的策略：`FIFO` / `Priority First` / `Earliest Due Date` / `Least Setup Change` / `Hybrid` |
| replan_reason | TEXT | 重排原因：`機台故障重排` / `特急單插單重排` / `前站延誤重排` / `人員不足重排` |

### 資料關係

| 關係 | 說明 |
|------|------|
| dispatches.experiment_item -> machines.supported_items | WIP 的實驗項目必須存在於機台支援項目清單 |
| dispatches.experiment_item -> recipes.experiment_item | WIP 的實驗項目必須等於 Recipe 實驗項目 |
| dispatches.assigned_machine_id -> recipes.machine_ids | 實際派工機台必須存在於 Recipe 可用機台清單 |
| dispatches.assigned_recipe_id -> recipes.recipe_id | 實際派工 Recipe 需存在於 Recipe 主檔 |
