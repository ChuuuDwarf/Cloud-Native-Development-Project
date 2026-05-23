# 實驗執行、結果與報告管理

## 模組目標

本模組負責 WIP 完成派工後，實際進入實驗執行階段的流程管理，包含上機、開始實驗、進度更新、下機、結果上傳、原始數據確認、異常中止申請、實驗完成、報告產出、報告審核、報告回傳與後續結單銜接。

本模組主要交付給 **組員 D：實驗執行、結果、報告、結單、倉儲取件** 使用。

---

## 1. 實驗執行

實驗執行主要負責樣品實際進入實驗室後的上下機、進度更新、數據蒐集與結果確認。

---

### 1.1 上下機履歷

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 上機登記（操作人 / 時間 / 機台 / Recipe） | — | ✅ | — | — |
| 下機登記 | — | ✅ | — | — |
| 查詢樣品完整機台履歷 | — | ✅ | ✅ | — |

> **規則：** 每次上下機紀錄不可刪除。

### 說明

上下機履歷用來記錄樣品在哪一台機台上執行、由誰操作、使用哪個 Recipe，以及上下機時間。

這些紀錄屬於實驗追溯資料，因此不可刪除。

實驗室人員可以登記上下機資料，實驗室主管可以查看樣品完整機台履歷。

---

### 1.2 實驗進度與結果

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 開始 / 更新實驗進度 | — | ✅ | — | — |
| 上傳結果 / 填寫備註 | — | ✅ | — | — |
| 關聯原始數據 | — | ✅ | — | — |
| 標記實驗完成 | — | ✅ | — | — |

### 說明

實驗進度與結果管理用來記錄實驗目前執行狀態、實驗結果、操作備註與原始數據。

實驗室人員可以開始實驗、更新進度、上傳結果、填寫備註，並將原始數據與實驗紀錄關聯。

當實驗完成後，實驗室人員可將實驗標記為完成，後續進入結果確認或報告產出流程。

---

### 1.3 機台自動化數據蒐集

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 接收機台開始 / 完成訊號 | — | 系統自動 | — | — |
| 自動抓取實驗數據並寫入 DB | — | 系統自動 | — | — |
| 驗證數據完整性 | — | ✅ | — | — |

> **規則：** 機台回報完成不直接結案，需進入「待結果確認」。

### 說明

機台自動化數據蒐集用來接收機台回傳的開始、完成訊號，並自動抓取實驗數據寫入資料庫。

系統雖然可以自動接收完成訊號，但不會直接將實驗結案。

實驗完成後需進入「待結果確認」狀態，由實驗室人員確認數據是否完整與正確。

---

## 2. 異常與中止管理

異常與中止管理用來處理實驗過程中發生的異常事件、停機、中止申請與主管審核。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立異常事件 | — | ✅ | — | — |
| 提出中止申請 | — | ✅ | — | — |
| 審核 / 決定是否終止實驗 | — | — | ✅ | — |
| 記錄中止原因與處理結果 | — | ✅ | ✅ | — |

> **規則：** 實驗室人員不可直接終止實驗，須由主管審核決定。

### 說明

當實驗過程中發生設備異常、樣品異常、數據異常或其他不可繼續執行的情況時，實驗室人員可建立異常事件。

若實驗需要中止，實驗室人員只能提出中止申請，不能直接終止實驗。

實驗室主管需審核中止申請，並決定是否終止實驗。

中止原因與後續處理結果都需要被記錄，方便後續追蹤與稽核。

---

## 3. 實驗報告管理

**模組目標：** 將實驗結果整理成正式報告，經主管確認後回傳廠區使用者。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立實驗報告草稿 | — | ✅ | — | — |
| 從實驗結果自動帶入內容 | — | 系統自動 | — | — |
| 編輯報告摘要 / 結論 / 附件 | — | ✅ | — | — |
| 上傳報告檔案 | — | ✅ | — | — |
| 報告版本管理 | — | ✅ | — | — |
| 提交報告審核 | — | ✅ | — | — |
| 審核 / 確認報告 | — | — | ✅ | — |
| 發布報告（回傳使用者） | — | ✅ | ✅（確認後） | — |
| 查閱 / 下載實驗報告 | ✅ | ✅ | ✅ | — |
| 設定報告發布規則 | — | — | — | ✅ |

> **報告狀態流程：** 草稿 → 待審核 → 已確認 → 已發布 → 已回傳 → 已改版（如需）

### 說明

實驗報告管理負責將已完成的實驗結果整理成正式報告。

系統可從實驗結果自動帶入基本內容，實驗室人員再補充報告摘要、結論、附件或上傳正式報告檔案。

報告完成後，實驗室人員提交給實驗室主管審核。

主管確認後，報告才可以發布並回傳給廠區使用者。

廠區使用者只能查閱或下載已發布、已回傳的報告，不能看到草稿或審核中的報告。

若報告內容後續需要修改，則進入版本管理，保留舊版紀錄並產生新版報告。

---

## 4. API 總表

| Method | API | 用途 |
|---|---|---|
| GET | `/api/experiment-runs` | 查詢實驗執行紀錄 |
| POST | `/api/experiment-runs` | 建立實驗執行紀錄 |
| GET | `/api/experiment-runs/:id` | 查看實驗執行紀錄 |
| PATCH | `/api/experiment-runs/:id` | 更新實驗進度、備註、結果摘要 |
| POST | `/api/experiment-runs/:id/actions` | 執行上機、下機、開始、完成、暫停、恢復等實驗流程動作 |
| GET | `/api/experiment-runs/:id/history` | 查看實驗執行歷程 |
| GET | `/api/machine-events` | 查詢機台事件 |
| POST | `/api/machine-events` | 接收機台開始、完成、錯誤、資料上傳等事件 |
| POST | `/api/experiment-runs/:id/raw-data` | 上傳或關聯原始數據 |
| POST | `/api/experiment-runs/:id/validate-data` | 驗證實驗數據完整性 |
| GET | `/api/reports` | 查詢實驗報告 |
| POST | `/api/reports` | 建立報告草稿 |
| GET | `/api/reports/:id` | 查看報告 |
| PATCH | `/api/reports/:id` | 編輯報告摘要、結論、附件 |
| POST | `/api/reports/:id/actions` | 提交審核、確認、發布、退回、回傳、建立新版 |
| GET | `/api/reports/:id/versions` | 查詢報告版本 |

---

# 實驗執行 API

## GET `/api/experiment-runs`

### 用途

查詢實驗執行紀錄。

### 使用情境

| 使用者 | 使用情境 |
|---|---|
| 實驗室人員 | 查看自己負責的執行中、待確認、已完成實驗 |
| 實驗室主管 | 查看實驗進度、異常、中止與結果確認狀態 |
| 廠區使用者 | 通常不直接查詢實驗執行細節，只看委託單或報告狀態 |

### Query Params

| 參數 | 說明 |
|---|---|
| `status` | 實驗執行狀態 |
| `wipId` | WIP ID |
| `orderId` | 委託單 ID |
| `machineId` | 機台 ID |
| `operatorId` | 操作人 ID |
| `page` | 頁碼 |
| `pageSize` | 每頁筆數 |

---

## POST `/api/experiment-runs`

### 用途

建立實驗執行紀錄。

通常由派工轉入實驗執行時建立，或由實驗室人員針對已派工 WIP 建立。

### Request Body 範例

```json
{
  "wipId": "WIP001",
  "dispatchId": "DSP001",
  "machineId": "M001",
  "recipeId": "RCP001",
  "operatorId": "USER003",
  "plannedStartTime": "2026-05-12T09:00:00+08:00",
  "plannedEndTime": "2026-05-12T12:00:00+08:00"
}
```

### 主要處理內容

| 項目 | 說明 |
|---|---|
| 關聯 WIP | 知道本次實驗來自哪一筆 WIP |
| 關聯派工 | 知道本次實驗來自哪一筆派工 |
| 關聯機台 | 記錄使用哪台機台 |
| 關聯 Recipe | 記錄使用哪個 Recipe |
| 建立初始狀態 | 初始可為 `waiting_load` 或 `ready` |

---

## GET `/api/experiment-runs/:id`

### 用途

查看單一實驗執行紀錄。

### 回傳內容建議包含

| 欄位 | 說明 |
|---|---|
| `id` | 實驗執行 ID |
| `runNo` | 實驗執行編號 |
| `wipId` | WIP ID |
| `dispatchId` | 派工 ID |
| `orderId` | 委託單 ID |
| `machineId` | 機台 ID |
| `recipeId` | Recipe ID |
| `operatorId` | 操作人 |
| `status` | 實驗狀態 |
| `progress` | 實驗進度百分比 |
| `loadedAt` | 上機時間 |
| `startedAt` | 開始時間 |
| `unloadedAt` | 下機時間 |
| `completedAt` | 完成時間 |
| `resultSummary` | 結果摘要 |
| `rawDataFiles` | 原始數據附件 |
| `remark` | 備註 |

---

## PATCH `/api/experiment-runs/:id`

### 用途

更新實驗進度、備註、結果摘要。

### Request Body 範例

```json
{
  "progress": 60,
  "resultSummary": "目前數據正常，等待最後量測完成",
  "remark": "樣品狀況穩定"
}
```

### 可修改內容

| 欄位 | 說明 |
|---|---|
| `progress` | 實驗進度 |
| `resultSummary` | 結果摘要 |
| `remark` | 備註 |

---

## POST `/api/experiment-runs/:id/actions`

### 用途

執行上機、下機、開始、完成、暫停、恢復等實驗流程動作。

## 實驗執行 Actions

| action | 用途 | 說明 |
|---|---|---|
| `load` | 上機 | 登記機台、Recipe、上機時間與操作人 |
| `start` | 開始實驗 | 狀態轉為 `running` |
| `pause` | 暫停實驗 | 因異常或等待處理暫停 |
| `resume` | 恢復實驗 | 暫停後繼續執行 |
| `unload` | 下機 | 記錄下機時間，機台可回到 idle |
| `complete` | 完成實驗 | 狀態轉為 `waiting_result_confirmation` |

> 中止申請不要在這裡獨立建立資料；前端可在實驗頁按「申請中止」，但後端應呼叫 `POST /api/issues` 建立 `type=termination_request`。

### Request Body 範例：上機

```json
{
  "action": "load",
  "machineId": "M001",
  "recipeId": "RCP001",
  "operatorId": "USER003",
  "comment": "樣品已上機"
}
```

### Request Body 範例：開始實驗

```json
{
  "action": "start",
  "comment": "開始執行 SEM 分析"
}
```

### Request Body 範例：完成實驗

```json
{
  "action": "complete",
  "comment": "機台執行完成，等待結果確認"
}
```

---

## GET `/api/experiment-runs/:id/history`

### 用途

查看實驗執行歷程。

### 使用情境

| 使用情境 | 說明 |
|---|---|
| 追蹤上下機紀錄 | 查看何時上機、下機、由誰操作 |
| 追蹤狀態變化 | 查看開始、暫停、恢復、完成等事件 |
| 稽核紀錄 | 保留完整實驗歷史 |

---

## POST `/api/experiment-runs/:id/raw-data`

### 用途

上傳或關聯原始數據。

### Request Body 範例

```json
{
  "fileIds": ["FILE001", "FILE002"],
  "dataSource": "machine_upload",
  "description": "SEM 原始影像與量測數據"
}
```

---

## POST `/api/experiment-runs/:id/validate-data`

### 用途

驗證實驗數據完整性。

### Request Body 範例

```json
{
  "checkItems": ["file_exists", "required_fields", "format_valid"]
}
```

### Response 範例

```json
{
  "experimentRunId": "RUN001",
  "isValid": true,
  "errors": [],
  "warnings": [
    "缺少非必要欄位 operatorNote"
  ]
}
```

---

# 機台事件 API

## GET `/api/machine-events`

### 用途

查詢機台事件。

### 使用情境

| 使用情境 | 說明 |
|---|---|
| 自動化紀錄查詢 | 查看機台回報開始、完成、錯誤、資料上傳等事件 |
| 異常排查 | 查看某次實驗期間是否有錯誤訊號 |
| 實驗同步 | 確認機台事件是否已轉成實驗狀態 |

---

## POST `/api/machine-events`

### 用途

接收機台開始、完成、錯誤、資料上傳等事件。

### Request Body 範例

```json
{
  "machineId": "M001",
  "experimentRunId": "RUN001",
  "eventType": "completed",
  "eventTime": "2026-05-12T12:00:00+08:00",
  "payload": {
    "rawDataFileIds": ["FILE001"],
    "message": "Machine completed successfully"
  }
}
```

### 主要處理內容

| 項目 | 說明 |
|---|---|
| 記錄機台事件 | 保留機台回報原始事件 |
| 關聯實驗紀錄 | 若有 `experimentRunId`，綁定到對應實驗 |
| 更新實驗狀態 | 完成訊號只更新為待結果確認，不直接結案 |
| 建立告警 | 錯誤事件可呼叫 `POST /api/issues` 建立異常事件 |

---

# 實驗報告 API

## GET `/api/reports`

### 用途

查詢實驗報告列表。

### 使用情境

| 使用者 | 使用情境 |
|---|---|
| 廠區使用者 | 查看自己委託單已發布或已回傳的報告 |
| 實驗室人員 | 查看自己負責編輯的報告草稿或退回報告 |
| 實驗室主管 | 查看待審核報告 |
| 系統管理者 | 通常不直接操作報告，只設定報告發布規則 |

### Query Params

| 參數 | 說明 |
|---|---|
| `status` | 報告狀態 |
| `orderId` | 委託單 ID |
| `experimentRunId` | 實驗執行 ID |
| `createdBy` | 建立者 |
| `page` | 頁碼 |
| `pageSize` | 每頁筆數 |

---

## POST `/api/reports`

### 用途

建立報告草稿。

通常在實驗數據確認完成後，由系統自動建立，或由實驗室人員手動建立。

### Request Body 範例

```json
{
  "orderId": "ORD001",
  "experimentRunId": "RUN001",
  "title": "SEM 表面分析報告",
  "summary": "系統由實驗結果自動帶入摘要",
  "conclusion": "",
  "attachmentFileIds": ["FILE001"]
}
```

### 主要處理內容

| 項目 | 說明 |
|---|---|
| 關聯委託單 | 知道報告屬於哪一張委託單 |
| 關聯實驗紀錄 | 從實驗執行結果帶入資料 |
| 建立報告草稿 | 初始狀態為 `draft` |
| 關聯附件 | 可綁定報告檔案或補充資料 |

---

## GET `/api/reports/:id`

### 用途

查看單一報告詳細資料。

### 回傳內容建議包含

| 欄位 | 說明 |
|---|---|
| `id` | 報告 ID |
| `reportNo` | 報告編號 |
| `orderId` | 委託單 ID |
| `experimentRunId` | 實驗執行 ID |
| `title` | 報告標題 |
| `summary` | 報告摘要 |
| `conclusion` | 結論 |
| `status` | 報告狀態 |
| `version` | 目前版本 |
| `attachments` | 附件 |
| `reviewer` | 審核主管 |
| `publishedAt` | 發布時間 |
| `returnedAt` | 回傳時間 |
| `createdAt` | 建立時間 |
| `updatedAt` | 更新時間 |

---

## PATCH `/api/reports/:id`

### 用途

編輯報告摘要、結論、附件。

### 可修改內容

| 欄位 | 說明 |
|---|---|
| `title` | 報告標題 |
| `summary` | 報告摘要 |
| `conclusion` | 報告結論 |
| `attachmentFileIds` | 報告附件 |
| `remark` | 備註 |

> 只有 `draft` 或 `rejected` 狀態可編輯。

---

## POST `/api/reports/:id/actions`

### 用途

執行報告流程動作，例如送審、主管確認、退回、發布、回傳、建立新版。

## Report Actions

| action | 用途 | 使用角色 |
|---|---|---|
| `submit_review` | 草稿送主管審核 | 實驗室人員 |
| `approve` | 主管確認報告 | 實驗室主管 |
| `reject` | 退回修改 | 實驗室主管 |
| `publish` | 發布報告 | 實驗室人員 / 主管 |
| `return_to_user` | 回傳廠區使用者 | 系統 / 實驗室人員 |
| `create_revision` | 建立新版報告 | 實驗室人員 |

### Request Body 範例：送審

```json
{
  "action": "submit_review",
  "comment": "報告已完成，送主管審核"
}
```

### Request Body 範例：主管確認

```json
{
  "action": "approve",
  "comment": "確認報告內容無誤"
}
```

### Request Body 範例：退回修改

```json
{
  "action": "reject",
  "reason": "請補充測試條件與數據說明"
}
```

### Request Body 範例：發布報告

```json
{
  "action": "publish"
}
```

### Request Body 範例：回傳廠區使用者

```json
{
  "action": "return_to_user",
  "notifyUser": true
}
```

### Request Body 範例：建立新版

```json
{
  "action": "create_revision",
  "reason": "補充附件與更新結論"
}
```

---

## GET `/api/reports/:id/versions`

### 用途

查詢報告版本紀錄。

### 使用情境

| 使用情境 | 說明 |
|---|---|
| 報告改版 | 查看舊版與新版差異 |
| 稽核追蹤 | 保留每次報告發布紀錄 |
| 主管確認 | 查看報告是否曾被修改 |

---

## 5. 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `role.md` | `GET /api/me` | 判斷實驗室人員、主管、廠區使用者的操作與下載權限 |
| `order_management.md` | `GET /api/orders/:id`<br>`POST /api/orders/:id/actions` | 報告發布或回傳後同步委託單狀態 |
| `sample_management.md` | `GET /api/wips/:id`<br>`PATCH /api/wips/:id`<br>`POST /api/wips/:id/actions` | 實驗開始、完成、終止時同步 WIP 狀態 |
| `schedule.md` | `GET /api/dispatches/:id`<br>`POST /api/dispatches/:id/actions` | 實驗由派工轉入執行，完成後同步派工狀態 |
| `warn.md` | `POST /api/issues`<br>`GET /api/issues`<br>`POST /api/notifications` | 實驗異常、機台錯誤、中止申請建立 Issue；報告送審、退回、發布、回傳時發送通知 |
| `system_setting.md` | `POST /api/files`<br>`GET /api/files/:id`<br>`GET /api/system-settings/reportRules` | 上傳 / 下載原始數據與報告附件，讀取報告發布規則 |
| `machine_recipe.md` | `GET /api/machines/:id`<br>`GET /api/recipes/:id` | 實驗執行時取得機台與 Recipe 資訊 |

---

## 6. 驗收標準

- 已派工 WIP 可以建立實驗執行紀錄。
- 可登記上機、開始、暫停、恢復、下機、完成。
- 上下機紀錄不可刪除，並可查看歷程。
- 機台回報完成後，實驗狀態進入待結果確認，不直接結案。
- 可上傳或關聯原始數據。
- 可驗證實驗數據完整性。
- 發生異常或中止申請時，會透過 `POST /api/issues` 建立事件。
- 實驗完成後可建立報告草稿。
- 報告可送審、退回、確認、發布、回傳與建立新版。
- 報告發布或回傳後，可以同步委託單 / WIP / 結單流程。
