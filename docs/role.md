## 系統角色定義

| 角色 | 簡稱 | seed key (DB role.name) | 說明 |
|------|------|---|------|
| 廠區使用者 | 使用者 | `plant_user` | 提出送測需求的廠區端人員 |
| 實驗室人員 | 實驗員 | `lab_engineer` | 執行收樣、派工、實驗的操作人員 |
| 實驗室主管 | 主管 | `lab_supervisor` | 負責審核、監控與決策的管理者 |
| 系統管理者 | 管理者 | `system_admin` | 維護系統設定與帳號的後台人員 |

> seed key 是 DB `roles.name` 欄位，也是 `scripts/seed_dev.py` 寫入的 key。後端 `require_permission(code)` dependency 透過 user→roles→permissions 關聯查表。

### 設計原則

1. **`system_admin` 用 `*` wildcard** 通過所有 permission 檢查。
2. **`lab_supervisor` 是 `lab_engineer` 的 superset** — 主管能做實驗員所有操作，再多出審核 / 結案 / 發佈報告 / 升級告警等管理權。`seed_dev.py` 用 `set(LAB_ENGINEER_PERMS + LAB_SUPERVISOR_EXTRA_PERMS)` 自動 union。
3. **`plant_user` 跨 lab，但綁定 owner**：可以看 / 建立委託單到任何 lab，但只看到自己開的單。
4. **`lab_engineer` / `lab_supervisor` 綁定單一 lab**：只看到自己 lab 的資料（multi-lab scoping 設計仍在討論，詳見本文末「Lab-scoped authorization」）。

---

## Permission 矩陣（截至 Phase 1）

> 真實來源為 `backend/scripts/seed_dev.py::ROLES`。本表追隨更新。

| Permission code | plant_user | lab_engineer | lab_supervisor | system_admin |
|---|:---:|:---:|:---:|:---:|
| `users:read` | | | ✅ | ✅ (*) |
| `users:create` | | | | ✅ (*) |
| `users:update` | | | | ✅ (*) |
| `orders:read` | ✅ | ✅ | ✅ | ✅ (*) |
| `orders:create` | ✅ | | | ✅ (*) |
| `orders:approve` | | | ✅ | ✅ (*) |
| `orders:close` | | | ✅ | ✅ (*) |
| `samples:read` | ✅ | ✅ | ✅ | ✅ (*) |
| `samples:create` | | ✅ | ✅ | ✅ (*) |
| `wips:read` | | ✅ | ✅ | ✅ (*) |
| `wips:create` | | ✅ | ✅ | ✅ (*) |
| `wips:dispatch` | | ✅ | ✅ | ✅ (*) |
| `machines:read` | | ✅ | ✅ | ✅ (*) |
| `machines:manage` | | | ✅ | ✅ (*) |
| `recipes:read` | | ✅ | ✅ | ✅ (*) |
| `recipes:manage` | | | ✅ | ✅ (*) |
| `schedules:read` | | ✅ | ✅ | ✅ (*) |
| `schedules:manage` | | | ✅ | ✅ (*) |
| `dispatches:read` | | ✅ | ✅ | ✅ (*) |
| `dispatches:manage` | | ✅ | ✅ | ✅ (*) |
| `experiment_runs:read` | | ✅ | ✅ | ✅ (*) |
| `experiment_runs:execute` | | ✅ | ✅ | ✅ (*) |
| `reports:read` | | ✅ | ✅ | ✅ (*) |
| `reports:create` | | ✅ | ✅ | ✅ (*) |
| `reports:publish` | | | ✅ | ✅ (*) |
| `issues:read` | | ✅ | ✅ | ✅ (*) |
| `issues:create` | | ✅ | ✅ | ✅ (*) |
| `issues:close` | | | ✅ | ✅ (*) |
| `issues:escalate` | | | ✅ | ✅ (*) |
| `notifications:read` | ✅ | ✅ | ✅ | ✅ (*) |
| `dashboard:read` | | | ✅ | ✅ (*) |
| `audit_logs:read` | | | ✅ | ✅ (*) |
| `system_settings:read` | | | | ✅ (*) |
| `system_settings:update` | | | | ✅ (*) |
| `labs:read` | ✅ | ✅ | ✅ | ✅ (*) |
| `labs:manage` | | | | ✅ (*) |
| `departments:read` | ✅ | | ✅ | ✅ (*) |
| `departments:manage` | | | | ✅ (*) |
| `storage_locations:read` | | ✅ | ✅ | ✅ (*) |
| `storage_locations:manage` | | | | ✅ (*) |

`(*)` = 透過 `*` wildcard 自動通過，不需要逐條 grant。

### 業務 intent 對照（給隊友快速建構心智模型）

- **plant_user**：開單 → 看自己單的進度 → 取件結案。**不能** 簽核、看 WIP / 機台 / 實驗、看儀表板。
- **lab_engineer**：收樣 → 拆 WIP / 分貨 → 派工到機台跑 recipe → 上下機 → 回報 → 寫報告草稿。**不能** 簽核 / 結案 / 發佈報告 / 處理告警 / 看儀表板。
- **lab_supervisor**：實驗員的所有動作 +**審核** (`orders:approve`, `orders:close`, `reports:publish`)、**告警處理** (`issues:close`, `issues:escalate`)、**監督**（看儀表板、看 audit log、機台/Recipe/排程**管理權**）。
- **system_admin**：除了業務操作以外，**only role** 能管帳號、權限、系統設定、實驗室 / 部門 / 倉位 master data。

### 怎麼新增 / 修改 permission

1. 改 `backend/scripts/seed_dev.py::PERMISSIONS` 列表加新 code
2. 在 `ROLES` 內把 code 加進對應 role（或 `LAB_ENGINEER_PERMS` / `LAB_SUPERVISOR_EXTRA_PERMS` 群組）
3. 重灌 seed：`make seed`
4. 在用到該 code 的 endpoint 加 `Depends(require_permission("..."))`
5. **同步更新本文件的 permission 矩陣**

---

## Lab-scoped authorization（討論中，尚未實作）

廠區有多個實驗室；engineer / supervisor 只看自己 lab 的資料。設計細節整理中，待 team align 後落地。**目前實作僅做到 resource:verb 層**，沒有 row-level lab filter，任何過了 permission 檢查的 user 都看得到全部 lab 的資料。

待定問題：
- engineer 是否可同時隸屬多個 lab？
- plant_user 是否限制只能開單給「自己部門」配合的某些 lab？
- 跨 lab 委託（樣品從 LAB-A 送 LAB-B 加測）的權限怎麼算？
- audit log 是否 lab-scoped（supervisor 只看自己 lab 的稽核）？

---
## 使用者與帳號管理

**模組目標：** 管理系統帳號、角色指派、部門設定與實驗室歸屬。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 帳號建立 / 停用 | — | — | — | ✅ |
| 角色指派 | — | — | — | ✅ |
| 部門 / 廠區設定 | — | — | — | ✅ |
| 實驗室歸屬設定 | — | — | — | ✅ |
| 權限控管 | — | — | — | ✅ |

---

# 使用者與帳號管理 API

## API 總表

| Method | API | 用途 |
|---|---|---|
| POST | `/api/auth/login` | 使用者登入 |
| POST | `/api/auth/logout` | 使用者登出 |
| GET | `/api/me` | 取得目前登入者資料、角色與權限 |
| GET | `/api/users` | 查詢使用者列表 |
| POST | `/api/users` | 建立使用者 |
| GET | `/api/users/:id` | 查看單一使用者 |
| PATCH | `/api/users/:id` | 修改使用者資料、角色、部門、實驗室歸屬或啟用狀態 |
| GET | `/api/roles` | 取得角色清單 |
| GET | `/api/permissions` | 取得系統權限清單 |


## 主要流程

### 1. 登入

`POST /api/auth/login` 驗證帳號密碼、檢查帳號啟用狀態，成功後建立登入狀態並回傳 token 或 session 資訊。

### 2. 取得目前登入者

`GET /api/me` 是所有頁面權限判斷的核心 API，前端登入後、重新整理頁面、Route Guard、顯示功能選單時都要使用。

### 3. 使用者管理

`GET /api/users` 支援依關鍵字、角色、部門、實驗室、啟用狀態查詢。`POST /api/users` 建立帳號，`PATCH /api/users/:id` 負責修改角色、部門、實驗室歸屬、啟用狀態與重設密碼。

## 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `system_setting.md` | `GET /api/labs`<br>`GET /api/departments` | 建立或編輯使用者時選擇實驗室與部門 |
| `system_setting.md` | `GET /api/master-data` | 載入角色、部門、實驗室等下拉選單 |
