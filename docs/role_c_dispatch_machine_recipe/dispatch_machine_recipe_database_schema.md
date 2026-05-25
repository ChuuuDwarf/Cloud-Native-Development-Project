## 派工排程與機台 Recipe 資料庫架構

本文件同步目前後端實作：[backend/database.py](../../backend/database.py)。

後端啟動時會透過 `init_db()` 建立與初始化 4 張資料表：

| 資料表 | 用途 |
|--------|------|
| `users` | 使用者、角色、部門與 LAB 權限範圍 |
| `machines` | 機台主檔、狀態、支援實驗項目與稼動率 |
| `recipes` | Recipe 主檔、版本、可用機台與參數 |
| `dispatches` | WIP 派工單、排程建議、實際派工與重排紀錄 |

### 資料庫物件摘要

| 項目 | 目前實作 |
|------|----------|
| 資料表數量 | 4 |
| Primary key | 每張表各 1 個文字型主鍵 |
| Foreign key | 目前未在資料庫層宣告，關聯由 FastAPI 應用層檢查 |
| Check constraint | 目前未在資料庫層宣告，枚舉值與數值範圍由 Pydantic schema 檢查 |
| 額外 index | 目前未建立額外 index |
| Migration | 目前沒有獨立 migration 檔，啟動時由 `init_db()` 執行 `CREATE TABLE IF NOT EXISTS` 與部分 `ALTER TABLE` 補欄位 |

### LAB 對照

| LAB 代碼 | 實驗室名稱 |
|----------|------------|
| `LAB A` | 材料分析實驗室 |
| `LAB B` | 結構分析實驗室 |
| `LAB C` | 光學量測實驗室 |

---

## users（使用者與角色）

### DDL

```sql
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    department TEXT NOT NULL,
    lab TEXT
);
```

### 欄位

| 欄位名稱 | 型態 | Null | Default | 說明 |
|----------|------|------|---------|------|
| `user_id` | `TEXT` | No | - | 使用者 ID，例如 `u-lab-a`、`u-supervisor-a`、`u-chief` |
| `name` | `TEXT` | No | - | 使用者姓名 |
| `role` | `TEXT` | No | - | 使用者角色 |
| `department` | `TEXT` | No | - | 所屬部門，例如 `實驗室`、`資訊部`、`F12 廠` |
| `lab` | `TEXT` | Yes | - | 所屬實驗室。LAB 人員與小主管通常為 `LAB A/B/C`；大主管與系統管理者可為 `NULL` |

### 目前使用角色

| 角色 | 說明 |
|------|------|
| `廠區使用者` | 建立委託/WIP 的廠區端角色 |
| `實驗室人員` | 可操作自己 LAB 的機台、Recipe、派工 |
| `實驗室小主管` | 可操作自己 LAB 的機台、Recipe、派工 |
| `實驗室大主管` | 可查看全部 LAB |
| `系統管理者` | 可查看與管理全部 LAB |

---

## machines（機台主檔）

### DDL

```sql
CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    lab TEXT NOT NULL,
    status TEXT NOT NULL,
    supported_items TEXT[] NOT NULL,
    utilization INTEGER NOT NULL DEFAULT 0,
    owner TEXT NOT NULL,
    last_maintenance TEXT NOT NULL
);
```

### 欄位

| 欄位名稱 | 型態 | Null | Default | 說明 |
|----------|------|------|---------|------|
| `machine_id` | `TEXT` | No | - | 機台 ID，例如 `TEM-001`、`XRD-002` |
| `name` | `TEXT` | No | - | 機台名稱 |
| `lab` | `TEXT` | No | - | 機台所在實驗室：`LAB A` / `LAB B` / `LAB C` |
| `status` | `TEXT` | No | - | 機台狀態 |
| `supported_items` | `TEXT[]` | No | - | 支援的實驗項目清單 |
| `utilization` | `INTEGER` | No | `0` | 稼動率，API schema 限制為 0 到 100 |
| `owner` | `TEXT` | No | - | 機台負責人 |
| `last_maintenance` | `TEXT` | No | - | 最近保養時間或保養紀錄文字 |

### 目前使用狀態

| 狀態 | 說明 |
|------|------|
| `閒置` | 可被排程與派工 |
| `使用中` | 使用中 |
| `保養中` | 不可派工 |
| `故障中` | 不可派工 |
| `停用` | 不可派工 |

---

## recipes（Recipe 設定）

### DDL

```sql
CREATE TABLE IF NOT EXISTS recipes (
    recipe_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    experiment_item TEXT NOT NULL,
    machine_ids TEXT[] NOT NULL,
    method TEXT NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);
```

### 欄位

| 欄位名稱 | 型態 | Null | Default | 說明 |
|----------|------|------|---------|------|
| `recipe_id` | `TEXT` | No | - | Recipe ID，例如 `RCP-TEM-001` |
| `name` | `TEXT` | No | - | Recipe 名稱 |
| `version` | `TEXT` | No | - | Recipe 版本，例如 `v1.0` |
| `experiment_item` | `TEXT` | No | - | 對應實驗項目，需與 WIP 的 `experiment_item` 相同 |
| `machine_ids` | `TEXT[]` | No | - | 可使用此 Recipe 的機台 ID 清單 |
| `method` | `TEXT` | No | - | 實驗方法或操作方法 |
| `parameters` | `JSONB` | No | `'{}'::jsonb` | Recipe 參數，例如電壓、時間、掃描範圍 |
| `updated_by` | `TEXT` | No | - | 最後更新者。建立時後端會使用目前登入使用者姓名 |
| `updated_at` | `TIMESTAMPTZ` | No | - | 最後更新時間。建立時後端寫入 `datetime.now()` |

---

## dispatches（WIP 派工與排程）

### DDL

```sql
CREATE TABLE IF NOT EXISTS dispatches (
    dispatch_id TEXT PRIMARY KEY,
    wip_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    experiment_item TEXT NOT NULL,
    priority TEXT NOT NULL,
    lab TEXT NOT NULL DEFAULT 'LAB A',
    due_at TEXT NOT NULL,
    status TEXT NOT NULL,
    suggested_machine_id TEXT,
    assigned_machine_id TEXT,
    assigned_recipe_id TEXT,
    scheduled_start TEXT,
    scheduled_end TEXT,
    created_by TEXT,
    assigned_by TEXT,
    strategy TEXT,
    replan_reason TEXT
);
```

### 欄位

| 欄位名稱 | 型態 | Null | Default | 說明 |
|----------|------|------|---------|------|
| `dispatch_id` | `TEXT` | No | - | 派工單 ID，例如 `DSP-001` |
| `wip_id` | `TEXT` | No | - | WIP ID，例如 `WIP-001` |
| `order_id` | `TEXT` | No | - | 委託單 ID，例如 `WO-001` |
| `experiment_item` | `TEXT` | No | - | 實驗項目，需對應機台支援項目與 Recipe 實驗項目 |
| `priority` | `TEXT` | No | - | 優先級 |
| `lab` | `TEXT` | No | `'LAB A'` | WIP 所屬實驗室：`LAB A` / `LAB B` / `LAB C` |
| `due_at` | `TEXT` | No | - | 交期，格式建議 `YYYY-MM-DD HH:mm` |
| `status` | `TEXT` | No | - | WIP 派工狀態 |
| `suggested_machine_id` | `TEXT` | Yes | - | 系統建議機台 ID |
| `assigned_machine_id` | `TEXT` | Yes | - | 實際確認派工的機台 ID |
| `assigned_recipe_id` | `TEXT` | Yes | - | 實際確認派工的 Recipe ID |
| `scheduled_start` | `TEXT` | Yes | - | 系統預估或最終派工開始時間，格式建議 `YYYY-MM-DD HH:mm` |
| `scheduled_end` | `TEXT` | Yes | - | 系統預估或最終派工結束時間，格式建議 `YYYY-MM-DD HH:mm` |
| `created_by` | `TEXT` | Yes | - | 建立 WIP 的使用者名稱 |
| `assigned_by` | `TEXT` | Yes | - | 確認派工的使用者名稱 |
| `strategy` | `TEXT` | Yes | - | 產生建議或重排使用的排程策略 |
| `replan_reason` | `TEXT` | Yes | - | 重排原因 |

### 目前使用優先級

| 優先級 | 排序權重 |
|--------|----------|
| `特急` | 最高 |
| `高` | 中 |
| `一般` | 一般 |

### 目前使用派工狀態

| 狀態 | 說明 |
|------|------|
| `待派工` | 尚未排程或尚未確認 |
| `排程中` | 已產生系統建議排程 |
| `待上機` | 已人工確認機台與 Recipe，等待上機 |

### 目前使用排程策略

| 策略 | 說明 |
|------|------|
| `FIFO` | 依 `dispatch_id` 排序 |
| `Priority First` | 依優先級，再依交期排序 |
| `Earliest Due Date` | 依交期，再依優先級排序 |
| `Least Setup Change` | 依實驗項目集中排序，減少換機或換設定 |
| `Hybrid` | 依優先級、交期、實驗項目綜合排序 |

### 目前使用重排原因

| 重排原因 | 預設對應策略 |
|----------|--------------|
| `機台故障重排` | `Least Setup Change` |
| `特急單插單重排` | `Priority First` |
| `前站延誤重排` | `Earliest Due Date` |
| `人員不足重排` | `Hybrid` |

---

## 啟動時補欄位與資料校正

`init_db()` 建表後，會額外對 `dispatches` 執行以下相容舊資料的更新：

```sql
ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS created_by TEXT;
ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS assigned_by TEXT;
ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS strategy TEXT;
ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS replan_reason TEXT;
ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS lab TEXT DEFAULT 'LAB A';
UPDATE dispatches SET lab = 'LAB A' WHERE lab IS NULL;
ALTER TABLE dispatches ALTER COLUMN lab SET NOT NULL;
```

另外，`seed_db()` 會把舊版中文實驗室名稱校正為 LAB 代碼：

| 舊值 | 新值 |
|------|------|
| `材料分析實驗室` | `LAB A` |
| `結構分析實驗室` | `LAB B` |
| `光學實驗室` | `LAB C` |

`dispatches.lab` 也會依照 `experiment_item` 自動校正：

| 實驗項目 | LAB |
|----------|-----|
| `材料成份分析`、`晶格缺陷觀察`、`表面形貌分析` | `LAB A` |
| `晶體結構分析`、`薄膜應力分析` | `LAB B` |
| `光學量測`、`膜厚量測` | `LAB C` |

---

## 初始 Seed 資料

### users

啟動時會確保以下角色存在，並使用 upsert 更新最新資料：

| user_id | name | role | department | lab |
|---------|------|------|------------|-----|
| `u-lab` | 林育誠 | 實驗室人員 | 實驗室 | `LAB A` |
| `u-supervisor` | 陳雅婷 | 實驗室小主管 | 實驗室 | `LAB A` |
| `u-lab-a` | 林育誠 | 實驗室人員 | 實驗室 | `LAB A` |
| `u-supervisor-a` | 陳雅婷 | 實驗室小主管 | 實驗室 | `LAB A` |
| `u-lab-b` | 吳佳穎 | 實驗室人員 | 實驗室 | `LAB B` |
| `u-supervisor-b` | 黃柏翰 | 實驗室小主管 | 實驗室 | `LAB B` |
| `u-lab-c` | 周品妤 | 實驗室人員 | 實驗室 | `LAB C` |
| `u-supervisor-c` | 許冠廷 | 實驗室小主管 | 實驗室 | `LAB C` |
| `u-chief` | 謝雅雯 | 實驗室大主管 | 實驗室 | `NULL` |
| `u-admin` | 張志明 | 系統管理者 | 資訊部 | `NULL` |

如果 `users` 原本完全沒有資料，會額外建立：

| user_id | name | role | department | lab |
|---------|------|------|------------|-----|
| `u-factory` | 王建國 | 廠區使用者 | F12 廠 | `NULL` |

### machines

當 `machines` 為空時會建立：

| machine_id | name | lab | status | supported_items | utilization | owner | last_maintenance |
|------------|------|-----|--------|-----------------|-------------|-------|------------------|
| `TEM-001` | 穿透式電子顯微鏡 | `LAB A` | `閒置` | `材料成份分析`、`晶格缺陷觀察` | 48 | 林育誠 | `2026-05-10` |
| `XRD-002` | X 光繞射儀 | `LAB B` | `閒置` | `晶體結構分析`、`薄膜應力分析` | 35 | 陳雅婷 | `2026-05-14` |
| `SEM-001` | 掃描式電子顯微鏡 | `LAB A` | `故障中` | `表面形貌分析`、`材料成份分析` | 72 | 林育誠 | `2026-05-02` |
| `OPT-001` | 光學量測平台 | `LAB C` | `閒置` | `光學量測`、`膜厚量測` | 22 | 林育誠 | `2026-05-12` |

### recipes

當 `recipes` 為空時會建立：

| recipe_id | name | version | experiment_item | machine_ids | method | parameters | updated_by |
|-----------|------|---------|-----------------|-------------|--------|------------|------------|
| `RCP-TEM-001` | TEM 材料成份標準流程 | `v1.0` | `材料成份分析` | `TEM-001` | 低劑量成像與 EDS mapping | `{"voltage": "200kV", "duration": "45min"}` | 林育誠 |
| `RCP-XRD-001` | XRD 薄膜應力標準流程 | `v1.0` | `薄膜應力分析` | `XRD-002` | Omega-2Theta scan | `{"range": "20-80deg", "step": "0.02deg"}` | 陳雅婷 |
| `RCP-OPT-001` | 光學量測標準流程 | `v1.0` | `光學量測` | `OPT-001` | 多點反射率快速量測 | `{"points": "9", "duration": "20min"}` | 林育誠 |

`updated_at` 由 seed 執行時寫入 `datetime.now()`，因此會依初始化時間而不同。

### dispatches

當 `dispatches` 為空時會建立：

| dispatch_id | wip_id | order_id | experiment_item | priority | lab | due_at | status | created_by |
|-------------|--------|----------|-----------------|----------|-----|--------|--------|------------|
| `DSP-001` | `WIP-001` | `WO-001` | `材料成份分析` | `特急` | `LAB A` | `2026-05-22 18:00` | `待派工` | 王建國 |
| `DSP-002` | `WIP-002` | `WO-002` | `薄膜應力分析` | `高` | `LAB B` | `2026-05-23 10:00` | `待派工` | 王建國 |
| `DSP-003` | `WIP-003` | `WO-003` | `表面形貌分析` | `一般` | `LAB A` | `2026-05-23 17:00` | `待派工` | 王建國 |
| `DSP-004` | `WIP-004` | `WO-004` | `光學量測` | `一般` | `LAB C` | `2026-05-22 09:00` | `待派工` | 王建國 |
| `DSP-005` | `WIP-005` | `WO-005` | `薄膜應力分析` | `特急` | `LAB B` | `2026-05-24 16:00` | `待派工` | 王建國 |

---

## 資料關係與應用層規則

目前資料庫沒有宣告 foreign key，以下關係由 FastAPI router 與 service 在應用層檢查：

| 關係 | 說明 |
|------|------|
| `users.lab` -> `machines.lab` / `dispatches.lab` | LAB scoped user 只能查看與操作自己 LAB 的資料 |
| `dispatches.experiment_item` -> `machines.supported_items` | WIP 的實驗項目必須存在於機台支援項目清單 |
| `dispatches.experiment_item` -> `recipes.experiment_item` | WIP 的實驗項目必須等於 Recipe 實驗項目 |
| `dispatches.lab` -> `machines.lab` | WIP 只能派到同一個 LAB 的機台 |
| `dispatches.assigned_machine_id` -> `recipes.machine_ids` | 實際派工機台必須存在於 Recipe 可用機台清單 |
| `dispatches.assigned_recipe_id` -> `recipes.recipe_id` | 實際派工 Recipe 需存在於 Recipe 主檔 |

---

## API 與資料庫欄位命名對照

後端回傳 API 時會透過 [backend/serializers.py](../../backend/serializers.py) 將資料庫的 snake_case 欄位轉為前端使用的 camelCase 欄位：

| 資料表 | 資料庫欄位 | API 欄位 |
|--------|------------|----------|
| `users` | `user_id` | `userId` |
| `machines` | `machine_id` | `machineId` |
| `machines` | `supported_items` | `supportedItems` |
| `machines` | `last_maintenance` | `lastMaintenance` |
| `recipes` | `recipe_id` | `recipeId` |
| `recipes` | `experiment_item` | `experimentItem` |
| `recipes` | `machine_ids` | `machineIds` |
| `recipes` | `updated_by` | `updatedBy` |
| `recipes` | `updated_at` | `updatedAt`，格式化為 `YYYY-MM-DD HH:mm` |
| `dispatches` | `dispatch_id` | `dispatchId` |
| `dispatches` | `wip_id` | `wipId` |
| `dispatches` | `order_id` | `orderId` |
| `dispatches` | `experiment_item` | `experimentItem` |
| `dispatches` | `due_at` | `dueAt` |
| `dispatches` | `suggested_machine_id` | `suggestedMachineId` |
| `dispatches` | `assigned_machine_id` | `assignedMachineId` |
| `dispatches` | `assigned_recipe_id` | `assignedRecipeId` |
| `dispatches` | `scheduled_start` | `scheduledStart` |
| `dispatches` | `scheduled_end` | `scheduledEnd` |
| `dispatches` | `created_by` | `createdBy` |
| `dispatches` | `assigned_by` | `assignedBy` |
| `dispatches` | `replan_reason` | `replanReason` |

---

## 權限與資料範圍

| 角色 | 可見資料範圍 | 可操作範圍 |
|------|--------------|------------|
| `廠區使用者` | 目前不屬於 Role C 操作角色 | 不可操作機台、Recipe、派工 |
| `實驗室人員` | 自己所屬 LAB | 可維護自己 LAB 的機台、Recipe、WIP 與派工 |
| `實驗室小主管` | 自己所屬 LAB | 可維護自己 LAB 的機台、Recipe、WIP 與派工 |
| `實驗室大主管` | 全部 LAB | 以查看全部 LAB 儀表板與資料為主 |
| `系統管理者` | 全部 LAB | 可跨 LAB 查看與管理資料；部分建立操作仍依 router 規則限制 |
