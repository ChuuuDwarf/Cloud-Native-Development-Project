## 系統設定

**模組目標：** 供系統管理者調整系統全域參數與規則。

| 可設定項目 | 系統管理者 |
|-----------|-----------|
| 實驗室數量 / 每室人數 | ✅ |
| 實驗室可執行實驗項目 | ✅ |
| 送測配額規則 | ✅ |
| 委託單 / WIP 編碼規則 | ✅ |
| 通知規則 | ✅ |
| 告警升級時間 | ✅ |
| 自動結單條件 | ✅ |
| 排程策略與最佳化權重參數 | ✅ |
| 假資料開關 / 筆數 / 更新頻率 | ✅ |
| 報告發布規則 | ✅ |

---

# 系統設定 API

## API 總表

| Method | API | 用途 |
|---|---|---|
| GET | `/api/master-data` | 取得前端共用下拉選單與狀態資料 |
| GET | `/api/system-settings` | 取得所有系統設定 |
| GET | `/api/system-settings/:key` | 取得單一系統設定 |
| PATCH | `/api/system-settings/:key` | 修改單一系統設定 |
| POST | `/api/system-settings/:key/reset` | 重設單一系統設定為預設值 |
| GET | `/api/system-settings/history` | 查看系統設定異動紀錄 |
| GET | `/api/labs` | 取得實驗室清單 |
| POST | `/api/labs` | 新增實驗室 |
| PATCH | `/api/labs/:id` | 修改實驗室設定 |
| DELETE | `/api/labs/:id` | 停用實驗室 |
| GET | `/api/labs/:id/capabilities` | 取得實驗室可執行實驗項目 |
| PATCH | `/api/labs/:id/capabilities` | 修改實驗室可執行實驗項目 |
| GET | `/api/departments` | 查詢部門 / 廠區清單 |
| POST | `/api/departments` | 新增部門 / 廠區 |
| GET | `/api/departments/:id` | 查看部門 / 廠區 |
| PATCH | `/api/departments/:id` | 修改部門 / 廠區 |
| DELETE | `/api/departments/:id` | 停用部門 / 廠區 |
| GET | `/api/storage-locations` | 查詢儲位清單 |
| POST | `/api/storage-locations` | 新增儲位 |
| PATCH | `/api/storage-locations/:id` | 修改儲位 |
| DELETE | `/api/storage-locations/:id` | 停用儲位 |
| POST | `/api/files` | 上傳原始數據、報告附件或其他檔案 |
| GET | `/api/files/:id` | 下載或預覽檔案 |
| DELETE | `/api/files/:id` | 刪除尚未正式綁定或草稿附件 |
| GET | `/api/audit-logs` | 查詢全域稽核紀錄 |


## System Settings Key

| key | 對應設定 |
|---|---|
| `labConfig` | 實驗室數量 / 每室人數 |
| `quotaRules` | 送測配額規則 |
| `codeRules` | 委託單 / WIP 編碼規則 |
| `notificationRules` | 通知規則 |
| `alertRules` | 告警升級時間 |
| `autoCloseRules` | 自動結單條件 |
| `schedulingPolicy` | 排程策略與最佳化權重參數 |
| `mockData` | 假資料開關 / 筆數 / 更新頻率 |
| `reportRules` | 報告發布規則 |

## Master Data 回傳範圍

`GET /api/master-data` 只負責提供前端共用下拉資料，不負責新增、修改或刪除資料。

| 資料 | 來源 |
|---|---|
| `roles`、`permissions` | `role.md` |
| `labs`、`departments`、`storageLocations` | `system_setting.md` |
| `experimentItems` | 系統設定 / 實驗室能力 |
| `orderStatuses`、`wipStatuses`、`reportStatuses` | 狀態定義 |
| `machineStatuses` | 機台狀態定義 |

## 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `role.md` | `GET /api/me` | 判斷是否為系統管理者 |
| `role.md` | `GET /api/users` | 系統設定異動紀錄顯示修改者資訊 |
| `schedule.md` | `POST /api/schedules/suggest` | 排程策略變更後會影響排程建議結果 |
| `warn.md` | `GET /api/issues` | 告警升級時間與通知規則會影響 Issue 升級 |
| `experiment_execute.md` | `GET /api/reports` | 報告發布規則會影響報告流程 |
