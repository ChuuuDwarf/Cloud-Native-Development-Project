# 機台、Recipe 與實驗方法管理

## 模組目標

本模組負責實驗執行前所需的資源與方法資料管理，包含機台資料、機台狀態、支援實驗項目、保養維修狀態、Recipe、Recipe 版本、實驗方法與參數範本。

---

## 1. 機台管理

### 1.1 功能權限

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 機台新增 / 編輯 / 停用 | — | ✅ | — | ✅ |
| 機台狀態設定 | — | ✅ | — | — |
| 支援實驗項目設定 | — | ✅ | — | — |
| 保養 / 維修狀態管理 | — | ✅ | — | — |
| 查看機台使用率 / 稼動率 | — | ✅ | ✅ | — |
| 設定假資料顯示規則 | — | — | — | ✅ |

### 1.2 機台狀態

| 狀態 | 說明 |
|---|---|
| `idle` | 閒置，可被排程或派工 |
| `running` | 使用中，正在執行實驗 |
| `maintenance` | 保養中，暫不可派工 |
| `broken` | 故障中，需維修 |
| `disabled` | 停用，不可再被使用 |

### 1.3 說明

機台管理提供實驗室人員維護實驗機台資料，包含機台基本資訊、目前狀態、支援的實驗項目，以及保養或維修狀態。

實驗室主管主要查看機台使用率與稼動率，用來掌握實驗室資源負載情況。

系統管理者可協助維護機台資料，並設定假資料顯示規則，方便系統展示或測試使用。

---

## 2. Recipe 與實驗方法管理

### 2.1 功能權限

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立 Recipe | — | ✅ | — | — |
| 維護 Recipe 版本 | — | ✅ | — | — |
| 建立實驗方法 | — | ✅ | — | — |
| 設定機台對應 Recipe | — | ✅ | — | — |
| 管理參數範本 | — | ✅ | — | — |
| 查看修改歷程 | — | ✅ | ✅ | — |

### 2.2 說明

Recipe 與實驗方法管理主要用來定義實驗執行時所需的標準方法、機台參數與版本資料。

實驗室人員可建立與維護 Recipe、設定 Recipe 對應機台，並管理參數範本。

實驗室主管可查看修改歷程，用來追蹤方法或 Recipe 是否被調整過。

---

## 3. API 總表

| Method | API | 用途 |
|---|---|---|
| GET | `/api/machines` | 查詢機台列表 |
| POST | `/api/machines` | 新增機台 |
| GET | `/api/machines/:id` | 查看單一機台 |
| PATCH | `/api/machines/:id` | 修改機台資料、狀態、支援實驗項目 |
| DELETE | `/api/machines/:id` | 停用機台 |
| GET | `/api/machines/:id/history` | 查看機台異動歷程 |
| GET | `/api/machines/:id/usage` | 查看機台使用率 / 稼動率 |
| GET | `/api/experiment-methods` | 查詢實驗方法 |
| POST | `/api/experiment-methods` | 建立實驗方法 |
| GET | `/api/experiment-methods/:id` | 查看實驗方法 |
| PATCH | `/api/experiment-methods/:id` | 修改實驗方法 |
| DELETE | `/api/experiment-methods/:id` | 停用實驗方法 |
| GET | `/api/experiment-methods/:id/history` | 查看實驗方法修改歷程 |
| GET | `/api/recipes` | 查詢 Recipe |
| POST | `/api/recipes` | 建立 Recipe |
| GET | `/api/recipes/:id` | 查看 Recipe |
| PATCH | `/api/recipes/:id` | 修改 Recipe |
| DELETE | `/api/recipes/:id` | 停用 Recipe |
| GET | `/api/recipes/:id/versions` | 查詢 Recipe 版本 |
| POST | `/api/recipes/:id/versions` | 建立 Recipe 新版本 |

---

# 機台 API

## GET `/api/machines`

### 用途

查詢機台列表。

### 使用情境

| 使用者 | 使用情境 |
|---|---|
| 實驗室人員 | 查看目前可用機台、機台狀態、支援實驗項目 |
| 實驗室主管 | 查看機台使用率、稼動率與負載 |
| 系統管理者 | 檢查機台資料是否正確 |

### Query Params

| 參數 | 說明 |
|---|---|
| `status` | 機台狀態 |
| `labId` | 實驗室 ID |
| `experimentItemId` | 支援的實驗項目 ID |
| `keyword` | 關鍵字搜尋 |
| `page` | 頁碼 |
| `pageSize` | 每頁筆數 |

### Response 範例

```json
{
  "items": [
    {
      "id": "M001",
      "machineNo": "SEM-001",
      "name": "SEM 掃描式電子顯微鏡",
      "labId": "LAB001",
      "status": "idle",
      "supportedExperimentItemIds": ["EXP_SEM"],
      "currentWipId": null,
      "updatedAt": "2026-05-12T10:00:00+08:00"
    }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 1
}
```

---

## POST `/api/machines`

### 用途

新增機台資料。

### Request Body 範例

```json
{
  "machineNo": "SEM-001",
  "name": "SEM 掃描式電子顯微鏡",
  "labId": "LAB001",
  "status": "idle",
  "supportedExperimentItemIds": ["EXP_SEM"],
  "description": "用於表面形貌分析"
}
```

### 主要處理內容

| 項目 | 說明 |
|---|---|
| 建立機台基本資料 | 建立機台編號、名稱、實驗室歸屬 |
| 設定支援項目 | 定義機台可以執行哪些實驗項目 |
| 設定初始狀態 | 預設可為 `idle` |
| 建立異動紀錄 | 保留新增紀錄供後續追蹤 |

---

## GET `/api/machines/:id`

### 用途

查看單一機台詳細資料。

### 回傳內容建議包含

| 欄位 | 說明 |
|---|---|
| `id` | 機台 ID |
| `machineNo` | 機台編號 |
| `name` | 機台名稱 |
| `labId` | 所屬實驗室 |
| `status` | 目前狀態 |
| `supportedExperimentItems` | 支援實驗項目 |
| `currentWipId` | 目前執行中的 WIP |
| `description` | 備註 |
| `createdAt` | 建立時間 |
| `updatedAt` | 更新時間 |

---

## PATCH `/api/machines/:id`

### 用途

修改機台資料、狀態、支援實驗項目。

### Request Body 範例

```json
{
  "name": "SEM 掃描式電子顯微鏡",
  "status": "maintenance",
  "supportedExperimentItemIds": ["EXP_SEM", "EXP_SURFACE"],
  "description": "例行保養中"
}
```

### 可修改內容

| 欄位 | 說明 |
|---|---|
| `name` | 機台名稱 |
| `status` | 機台狀態 |
| `supportedExperimentItemIds` | 支援實驗項目 |
| `description` | 備註 |

---

## DELETE `/api/machines/:id`

### 用途

停用機台。

### 說明

此 API 不建議真的刪除資料，而是將機台狀態改為 `disabled`，避免歷史派工與實驗紀錄找不到對應機台。

---

## GET `/api/machines/:id/history`

### 用途

查看機台異動歷程。

### 使用情境

| 使用情境 | 說明 |
|---|---|
| 狀態追蹤 | 查看機台何時從閒置變成故障或保養 |
| 稽核紀錄 | 追蹤誰修改過機台資料 |
| 問題排查 | 查詢某次實驗期間機台是否曾異常 |

---

## GET `/api/machines/:id/usage`

### 用途

查看機台使用率 / 稼動率。

### Query Params

| 參數 | 說明 |
|---|---|
| `startDate` | 查詢起始日期 |
| `endDate` | 查詢結束日期 |
| `groupBy` | 統計方式，例如 `day`、`week`、`month` |

### Response 範例

```json
{
  "machineId": "M001",
  "machineNo": "SEM-001",
  "startDate": "2026-05-01",
  "endDate": "2026-05-12",
  "usageRate": 0.76,
  "totalRunningHours": 82,
  "totalIdleHours": 26,
  "totalMaintenanceHours": 8
}
```

---

# 實驗方法 API

## GET `/api/experiment-methods`

### 用途

查詢實驗方法列表。

### Query Params

| 參數 | 說明 |
|---|---|
| `keyword` | 關鍵字 |
| `experimentItemId` | 實驗項目 ID |
| `status` | 狀態 |
| `page` | 頁碼 |
| `pageSize` | 每頁筆數 |

---

## POST `/api/experiment-methods`

### 用途

建立實驗方法。

### Request Body 範例

```json
{
  "methodNo": "METHOD-SEM-001",
  "name": "SEM 表面形貌分析標準方法",
  "experimentItemId": "EXP_SEM",
  "description": "用於 SEM 表面形貌觀察",
  "parameterTemplate": {
    "voltage": "15kV",
    "magnification": "5000x"
  }
}
```

---

## GET `/api/experiment-methods/:id`

### 用途

查看單一實驗方法。

---

## PATCH `/api/experiment-methods/:id`

### 用途

修改實驗方法。

### 可修改內容

| 欄位 | 說明 |
|---|---|
| `name` | 方法名稱 |
| `description` | 方法說明 |
| `parameterTemplate` | 參數範本 |
| `status` | 狀態 |

---

## DELETE `/api/experiment-methods/:id`

### 用途

停用實驗方法。

### 說明

不建議實體刪除，建議將狀態改為 `disabled`。

---

## GET `/api/experiment-methods/:id/history`

### 用途

查看實驗方法修改歷程。

---

# Recipe API

## GET `/api/recipes`

### 用途

查詢 Recipe 列表。

### Query Params

| 參數 | 說明 |
|---|---|
| `machineId` | 機台 ID |
| `experimentMethodId` | 實驗方法 ID |
| `status` | 狀態 |
| `keyword` | 關鍵字 |
| `page` | 頁碼 |
| `pageSize` | 每頁筆數 |

---

## POST `/api/recipes`

### 用途

建立 Recipe。

### Request Body 範例

```json
{
  "recipeNo": "RCP-SEM-001",
  "name": "SEM 標準觀察 Recipe",
  "machineId": "M001",
  "experimentMethodId": "METHOD001",
  "version": "1.0.0",
  "parameters": {
    "voltage": "15kV",
    "workingDistance": "10mm",
    "magnification": "5000x"
  },
  "status": "active"
}
```

### 主要處理內容

| 項目 | 說明 |
|---|---|
| 關聯機台 | 指定 Recipe 適用哪台機台 |
| 關聯實驗方法 | 指定 Recipe 對應的方法 |
| 記錄版本 | 初始版本通常為 `1.0.0` |
| 保存參數 | 保存機台執行所需參數 |

---

## GET `/api/recipes/:id`

### 用途

查看單一 Recipe。

### 回傳內容建議包含

| 欄位 | 說明 |
|---|---|
| `id` | Recipe ID |
| `recipeNo` | Recipe 編號 |
| `name` | Recipe 名稱 |
| `machineId` | 機台 ID |
| `experimentMethodId` | 實驗方法 ID |
| `version` | 版本 |
| `parameters` | Recipe 參數 |
| `status` | 狀態 |
| `createdAt` | 建立時間 |
| `updatedAt` | 更新時間 |

---

## PATCH `/api/recipes/:id`

### 用途

修改 Recipe 基本資料。

### 說明

若修改的是重要執行參數，建議不要直接覆蓋原版本，而是建立新版本。

---

## DELETE `/api/recipes/:id`

### 用途

停用 Recipe。

---

## GET `/api/recipes/:id/versions`

### 用途

查詢 Recipe 版本。

### 使用情境

| 使用情境 | 說明 |
|---|---|
| 版本追蹤 | 查看 Recipe 曾經調整過哪些參數 |
| 實驗追溯 | 查詢某次實驗使用的 Recipe 版本 |
| 主管檢查 | 確認方法變更歷程 |

---

## POST `/api/recipes/:id/versions`

### 用途

建立 Recipe 新版本。

### Request Body 範例

```json
{
  "version": "1.1.0",
  "parameters": {
    "voltage": "20kV",
    "workingDistance": "10mm",
    "magnification": "5000x"
  },
  "changeReason": "提升影像解析度"
}
```

---

## 4. 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `role.md` | `GET /api/me` | 判斷實驗室人員、主管、系統管理者的操作權限 |
| `sample_management.md` | `GET /api/wips` | 取得待派工 WIP，確認需要的實驗項目 |
| `schedule.md` | `GET /api/dispatches`<br>`POST /api/dispatches` | 派工時需要使用機台與 Recipe |
| `experiment_execute.md` | `POST /api/experiment-runs` | 實驗開始時會引用機台與 Recipe |
| `system_setting.md` | `GET /api/system-settings/mockDataRules` | 讀取假資料顯示規則 |

---

## 5. 驗收標準

- 可新增、查詢、修改、停用機台。
- 可設定機台狀態與支援實驗項目。
- 可查詢機台使用率 / 稼動率。
- 可建立實驗方法與參數範本。
- 可建立 Recipe 並關聯機台與實驗方法。
- 可建立 Recipe 新版本並保留歷史紀錄。
- 待派工 WIP 能選擇可用機台與對應 Recipe。
