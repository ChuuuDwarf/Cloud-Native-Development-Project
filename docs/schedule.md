## 派工與排程管理

**模組目標：** 依 WIP 狀態、機台可用性、優先級與交期，產生排程並執行派工。

### 1 排程建議與最佳化

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 查看待派工 / 待排程清單 | — | ✅ | ✅ | — |
| 自動 / 半自動排程建議 | — | 參考 | 參考（選） | — |
| 查看預估開始 / 完成時間 | — | ✅ | ✅ | — |
| 排程衝突檢查 | — | 系統自動 | — | — |
| 設定排程策略參數 | — | — | 調整接單規則 | ✅ |

> **排程策略：** FIFO / Priority First / Earliest Due Date / Least Setup Change / Hybrid

### 2 派工執行

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 指派機台 / Recipe / 時段 | — | ✅ | — | — |
| 確認 / 手動調整派工 | — | ✅ | — | — |
| 手動覆寫系統建議 | — | ✅ | — | — |
| 建立派工紀錄 | — | ✅（系統自動） | — | — |

### 3 動態重排

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 機台故障重排 | — | ✅ | — | — |
| 特急單插單重排 | — | ✅ | 決策 | — |
| 前站延誤 / 樣品未到重排 | — | ✅ | — | — |
| 人員不足重排 | — | ✅ | 協調 | — |

---

# 派工與排程管理 API

## API 總表

| Method | API | 用途 |
|---|---|---|
| GET | `/api/schedules` | 查詢排程資料 |
| POST | `/api/schedules/suggest` | 產生排程建議 |
| POST | `/api/schedules/conflict-check` | 檢查排程衝突 |
| POST | `/api/schedules/reschedule` | 依原因動態重排 |
| PATCH | `/api/schedules/:id` | 手動調整單一排程 |
| GET | `/api/dispatches` | 查詢派工清單 |
| POST | `/api/dispatches` | 建立派工 |
| GET | `/api/dispatches/:id` | 查看派工詳細資料 |
| PATCH | `/api/dispatches/:id` | 修改派工內容 |
| POST | `/api/dispatches/:id/actions` | 執行派工確認、開始、暫停、恢復、完成、取消 |


## Reschedule Reason

`POST /api/schedules/reschedule` 統一處理所有重排情境，不要拆成多支 API。

| reason | 說明 |
|---|---|
| `machine_failure` | 機台故障 |
| `urgent_order` | 特急單插單 |
| `previous_step_delay` | 前站延誤 |
| `sample_not_arrived` | 樣品未到 |
| `staff_shortage` | 人員不足 |
| `manual_adjustment` | 人工調整 |

## Dispatch Actions

| action | 說明 |
|---|---|
| `confirm` | 確認派工 |
| `start` | 開始執行 |
| `pause` | 暫停 |
| `resume` | 恢復執行 |
| `complete` | 完成派工 |
| `cancel` | 取消派工 |

## 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `role.md` | `GET /api/me`<br>`GET /api/users` | 判斷排程權限並取得可派工人員 |
| `sample_management.md` | `GET /api/wips`<br>`GET /api/wips/:id`<br>`POST /api/wips/:id/actions` | 取得待排程 WIP，排程後同步 WIP 狀態 |
| `machine_recipe.md` | `GET /api/machines`<br>`GET /api/machines/:id`<br>`GET /api/recipes` | 排程與派工需要機台狀態與 Recipe |
| `system_setting.md` | `GET /api/system-settings/schedulingPolicy` | 取得排程策略與最佳化權重 |
| `warn.md` | `POST /api/issues` | 排程衝突或重排失敗可建立告警 |

