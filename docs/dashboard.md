## 監控儀表板

**模組目標：** 提供主管即時掌握實驗室整體營運狀況。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 查看待簽核委託單數 | — | — | ✅ | — |
| 查看各實驗室在製量 | — | — | ✅ | — |
| 查看機台使用率 / 稼動率 | — | — | ✅ | — |
| 查看告警未處理數 | — | — | ✅ | — |
| 查看逾期 / 異常案件數 | — | — | ✅ | — |
| 查看報告待確認 / 已回傳數 | — | — | ✅ | — |
| 查看待排程 WIP 數 | — | — | ✅ | — |
| 查看各機台未來負載 | — | — | ✅ | — |
| 插單影響分析 | — | — | ✅（選） | — |

---

# Dashboard API

## API 總表

| Method | API | 用途 |
|---|---|---|
| GET | `/api/dashboard` | 取得目前登入者 Dashboard 總覽 |
| GET | `/api/dashboard/widgets/:widgetKey` | 取得單一 widget 詳細資料 |
| POST | `/api/dashboard/simulations` | 插單影響分析，不直接修改排程 |


## Widget Key

### 實驗室人員

| widgetKey | 說明 |
|---|---|
| `myTasks` | 我的待辦 |
| `todaySchedule` | 今日排程 |
| `assignedWips` | 指派給我的 WIP |
| `pendingResultUploads` | 待上傳實驗數據 |
| `pendingReports` | 待處理報告 |
| `openIssues` | 未處理異常 / 告警 |

### 實驗室主管

| widgetKey | 說明 |
|---|---|
| `pendingApprovals` | 待簽核委託單 |
| `labWipCounts` | 各實驗室在製量 |
| `machineUtilization` | 機台使用率 |
| `openIssues` | 未處理異常 / 告警 |
| `overdueCases` | 逾期案件 |
| `reportStatusCounts` | 報告狀態統計 |
| `pendingSchedules` | 待排程 WIP |
| `machineFutureLoad` | 機台未來負載 |

## 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `role.md` | `GET /api/me` | 依登入者角色回傳不同 Dashboard |
| `order_management.md` | `GET /api/orders` | 統計待簽核、逾期、結案狀態 |
| `sample_management.md` | `GET /api/wips`<br>`GET /api/samples` | 統計在製量、待排程、待取件 |
| `schedule.md` | `GET /api/schedules`<br>`GET /api/dispatches`<br>`POST /api/schedules/conflict-check` | 今日排程、未來負載、插單影響分析 |
| `machine_recipe.md` | `GET /api/machines`<br>`GET /api/machines/:id/usage` | 機台狀態與稼動率 |
| `experiment_execute.md` | `GET /api/experiment-runs` | 實驗進度統計 |
| `warn.md` | `GET /api/issues` | 未處理異常 / 告警 / 中止申請數 |
| `experiment_execute.md` | `GET /api/reports` | 報告草稿、待確認、已回傳統計 |

