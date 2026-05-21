## 結單管理

**模組目標：** 確認所有實驗完成後執行結案流程。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 系統自動判斷是否可結單 | — | 系統自動 | — | 設定條件 |
| 人員確認實驗結果 | — | ✅ | — | — |
| 轉待取件狀態 | — | ✅ | — | — |
| 完成結案 | — | ✅（使用者取件後） | — | — |

> **結單條件（需全部滿足）：**
> 所有實驗明細完成或終止 / 所有 WIP 已結束 / 數據已收集 / 無未結異常 / 樣品已入庫或待返還 / 報告已建立或已回傳

---

# 結單管理 API

## API 總表

| Method | API | 用途 |
|---|---|---|
| GET | `/api/orders/:id/close-check` | 檢查委託單是否符合結案條件 |


> 結單管理不另外建立大量 CRUD。它主要是檢查跨模組條件，真正狀態變更仍使用 `order_management.md` 的 `POST /api/orders/:id/actions`。

## Close Check 條件

`GET /api/orders/:id/close-check` 回傳該委託單是否可結案，以及不能結案的原因。

| 條件 | 來源 |
|---|---|
| 所有實驗明細完成或終止 | `experiment_execute.md` |
| 所有 WIP 已完成或終止 | `sample_management.md` |
| 數據已收集並確認 | `experiment_execute.md` |
| 無未結異常 / 告警 / 中止申請 | `warn.md` |
| 樣品已入庫或待返還 | `sample_management.md` |
| 報告已建立或已回傳 | `experiment_execute.md` |

## 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `role.md` | `GET /api/me` | 判斷是否能執行結案 |
| `order_management.md` | `GET /api/orders/:id`<br>`POST /api/orders/:id/actions` | 取得委託單狀態並執行 `close` |
| `sample_management.md` | `GET /api/samples`<br>`GET /api/wips` | 確認樣品與 WIP 是否都已結束 |
| `experiment_execute.md` | `GET /api/experiment-runs` | 確認實驗是否完成、數據是否已確認 |
| `experiment_execute.md` | `GET /api/reports` | 確認報告是否已建立、發布或回傳 |
| `warn.md` | `GET /api/issues` | 確認沒有未結事件 |
| `system_setting.md` | `GET /api/system-settings/autoCloseRules` | 取得自動結單條件 |