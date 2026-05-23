## 告警與通知管理

**模組目標：** 監控機台異常並依 SLA 升級通知，確保問題即時處理。

### 1 告警管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 接收 / 查看告警清單 | — | ✅ | ✅ | — |
| 指派告警處理人 | — | — | ✅ | — |
| 追蹤告警回應時間 | — | — | ✅ | — |
| 關閉告警 | — | ✅（處理完） | ✅ | — |
| 設定告警升級規則與時間 | — | — | — | ✅ |

> **升級機制範例：**
> - 0 分鐘：通知責任人員
> - 10 分鐘未處理：通知資深工程師
> - 20 分鐘未處理：通知實驗室主管
> - 30 分鐘未處理：通知上級主管

### 2 通知管理

| 通知情境 | 廠區使用者 | 實驗室人員 | 實驗室主管 |
|----------|-----------|-----------|-----------|
| 送單成功 | ✅ | — | — |
| 退回補件 | ✅ | — | — |
| 拒絕 | ✅ | — | — |
| 核准送樣 | ✅ | ✅ | — |
| 收樣成功 | ✅ | — | — |
| 異常通知 | — | ✅ | ✅ |
| 中止通知 | ✅ | ✅ | ✅ |
| 完成通知 | ✅ | — | — |
| 實驗報告已回傳 | ✅ | — | — |
| 取件通知 | ✅ | — | — |
| 告警升級通知 | — | ✅ | ✅ |

> **通知管道選項：** Email（必要）、系統內通知（必要）、可擴充簡訊 / Teams 、 打電話API

---

# Issues / Notifications API

## API 總表

| Method | API | 用途 |
|---|---|---|
| GET | `/api/issues` | 查詢異常 / 告警 / 中止申請列表 |
| POST | `/api/issues` | 建立異常、告警或中止申請 |
| GET | `/api/issues/:id` | 查看單一事件詳細資料 |
| PATCH | `/api/issues/:id` | 更新事件處理資訊 |
| POST | `/api/issues/:id/actions` | 執行審核、關閉、升級、指派、重開 |
| GET | `/api/notifications` | 查詢通知列表 |
| POST | `/api/notifications` | 建立通知，通常由後端流程自動觸發 |
| PATCH | `/api/notifications/:id` | 更新單筆通知狀態 |
| POST | `/api/notifications/actions` | 批次已讀或批次刪除通知 |


## Issue Type

| type | 說明 |
|---|---|
| `abnormal` | 實驗數據、樣品、流程異常 |
| `warning` | 機台故障、SLA 超時、系統警示 |
| `termination_request` | 實驗中止申請 |

## Issue Actions

| action | 用途 |
|---|---|
| `approve` | 核准中止申請 |
| `reject` | 拒絕中止申請 |
| `close` | 關閉異常或告警 |
| `escalate` | 升級告警 |
| `assign` | 指派處理人 |
| `reopen` | 重新開啟事件 |

## targetType 建議值

| targetType | 對應模組 |
|---|---|
| `machine` | 機台 |
| `experiment_run` | 實驗執行 |
| `order` | 委託單 |
| `sample` | 樣品 |
| `wip` | WIP |
| `report` | 報告 |
| `schedule` | 排程 |
| `dispatch` | 派工 |

## 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `role.md` | `GET /api/me`<br>`GET /api/users`<br>`GET /api/roles` | 判斷權限、指派處理人、告警升級通知角色 |
| `machine_recipe.md` | `GET /api/machines/:id`<br>`PATCH /api/machines/:id` | 機台告警時查詢或同步機台狀態 |
| `experiment_execute.md` | `GET /api/experiment-runs/:id`<br>`PATCH /api/experiment-runs/:id` | 實驗異常或中止核准後同步實驗狀態 |
| `order_management.md` | `GET /api/orders/:id`<br>`POST /api/orders/:id/actions` | 中止或補件情境同步委託單狀態 |
| `sample_management.md` | `GET /api/samples/:id`<br>`PATCH /api/samples/:id`<br>`GET /api/wips/:id`<br>`PATCH /api/wips/:id` | 樣品異常或 WIP 卡關時同步狀態 |
| `schedule.md` | `GET /api/schedules`<br>`POST /api/schedules/reschedule`<br>`GET /api/dispatches` | 機台故障或中止後重新排程與查詢派工 |
| `experiment_execute.md` | `GET /api/reports/:id`<br>`POST /api/reports/:id/actions` | 報告退回、回傳或補件通知 |
