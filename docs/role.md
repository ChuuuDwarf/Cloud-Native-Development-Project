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
| `machines:manage` | | ✅ | ✅ | ✅ (*) |
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
| `reports:publish` | | ✅ | ✅ | ✅ (*) |
| `issues:read` | | ✅ | ✅ | ✅ (*) |
| `issues:create` | | ✅ | ✅ | ✅ (*) |
| `issues:close` | | ✅ | ✅ | ✅ (*) |
| `issues:escalate` | | ✅ | ✅ | ✅ (*) |
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
- **lab_engineer**：收樣 → 拆 WIP / 分貨 → 派工到機台跑 recipe → 上下機 → 回報 → 寫報告 → **管機台狀態** → **發佈報告** → **第一線處理告警**（close / escalate）。**不能** 簽核委託 (`orders:approve/close`)、不能改 recipe / 排程設定（`recipes:manage` / `schedules:manage` 是 supervisor 才有的「製程 IP + 規劃決策」）、不能看儀表板。
- **lab_supervisor**：實驗員的**所有**動作 + **委託簽核 / 結案** (`orders:approve`, `orders:close`)、**製程 IP** (`recipes:manage`, `schedules:manage`)、**監督視角**（儀表板、audit log、部門列表）。
  - **告警 escalation 設計**：機台異常 → 系統先通知**值班 engineer** → 一段時間（依 `alertRules` 設定）engineer 沒 close 就**自動升級**給 supervisor。因此 engineer 必須有 `issues:close` 跟 `issues:escalate` —— escalate 也包含 engineer 自己主動「我處理不來請主管支援」這個動作。
- **system_admin**：除了業務操作以外，**only role** 能管帳號、權限、系統設定、實驗室 / 部門 / 倉位 master data。

### 怎麼新增 / 修改 permission

1. 改 `backend/scripts/seed_dev.py::PERMISSIONS` 列表加新 code
2. 在 `ROLES` 內把 code 加進對應 role（或 `LAB_ENGINEER_PERMS` / `LAB_SUPERVISOR_EXTRA_PERMS` 群組）
3. 重灌 seed：`make seed`
4. 在用到該 code 的 endpoint 加 `Depends(require_permission("..."))`
5. **同步更新本文件的 permission 矩陣**

---

## Lab-scoped authorization（已 align，Phase 2+ 實作）

廠區有多個實驗室，每個實驗室有自己的主管 + 機台 + recipe + 排程 + 報告，**不跨 lab 共用**。Engineer / supervisor 嚴格綁定**單一 lab**，只看自己 lab 的資料；plant_user 跨 lab 但只看自己開的單；sysadmin 看全部。

> **目前 (Phase 0/1) 實作僅到 resource:verb 層**；row-level lab filter 還沒上。任何過了 permission 檢查的 user 都看得到全部 lab 的資料。**Phase 2 起每個新 module 必須吃 scope helper**。

### Authorization scope 對照

| 角色 | scope | 解讀 |
|---|---|---|
| `system_admin` | `all` | 全部 lab、全部 user 的資料 |
| `lab_supervisor` | `own_lab` | 只 `WHERE lab_id = user.lab_id` |
| `lab_engineer` | `own_lab` | 同上 |
| `plant_user` | `own_records` | 只 `WHERE created_by = user.id`（自己開的單、自己的樣品） |

### 已定案的 spec

1. **engineer / supervisor 綁單一 lab**（`users.lab_id` 是 single FK，不做 many-to-many）。
2. **plant_user 可開單到任意 active lab**，不限制部門對應。
3. **一張委託單 = 一個 lab**（`orders.lab_id` 必填，不允許跨 lab order_items）。跨 lab 工作流請開兩張單。
4. **主管不能簽核別 lab 來的單**（接續 3，本來就不會發生）。
5. **Audit log 也 scoped**：sysadmin 看全部、supervisor 只看 `audit_logs.lab_id == user.lab_id` 的紀錄。**重要副作用**：`lab_id IS NULL` 的全域動作（department / system_setting / file 之類沒掛 lab 的 entity）supervisor **看不到** —— `NULL = uuid` 在 SQL 結果是 NULL、被 WHERE 過濾掉。這是 by design：全域動作只屬於 sysadmin 的稽核領域。若以後要 supervisor 也看 lab-agnostic 動作，要改 `apply_lab_scope` 加 `OR lab_id IS NULL` 分支。
6. **`/api/master-data` 的 `labs` 永遠回全部 active labs**（plant_user 建單時要選、engineer 也需要知道自己在哪 lab）；但個別 endpoint（`/api/machines` / `/api/recipes` / `/api/wips` 等）才做 lab filter。
7. **plant_user 的 `samples:read` 是 scoped 讀**：只看到自己單對應的樣品；前端 sidebar 不該列「收樣管理」這個 engineer 工作頁入口（Sidebar 上 `/sample` 跟 `/transfer` 用 `samples:create` 把關，非 `samples:read`）。

### 需要 `lab_id` FK 的表（給 A/B/C/D 設計 model 時參考）

| 表 | 欄位 | 拿誰的 lab_id |
|---|---|---|
| `orders` | `lab_id NOT NULL` | plant_user 建單時挑 |
| `samples` | `lab_id NOT NULL` | 繼承自 `order.lab_id` |
| `wips` | `lab_id NOT NULL` | 繼承自 `sample.lab_id` |
| `machines` | `lab_id NOT NULL` | 註冊機台時指定 |
| `recipes` | `lab_id NOT NULL` | 註冊 recipe 時指定（或從 machine 繼承） |
| `schedules` | `lab_id NOT NULL` | 從 machine 推 |
| `dispatches` | `lab_id NOT NULL` | 從 wip / machine 推 |
| `experiment_runs` | `lab_id NOT NULL` | 從 dispatch 推 |
| `reports` | `lab_id NOT NULL` | 從 experiment_run 推 |
| `issues` | `lab_id NULLABLE` | 從 target 推（target 不一定有 lab，例如系統層 issue） |
| `audit_logs` | `lab_id NULLABLE` | 從 target 推（用於 supervisor scoped 讀） |

### Service-layer pattern（建議 helper）

E 在 Phase 2 會在 `app/common/dependencies/scope.py` 提供 helper，A/B/C/D 直接吃：

```python
from sqlalchemy import Select
from app.common.dependencies import CurrentUser

def apply_lab_scope(
    stmt: Select,
    user: CurrentUser,
    lab_id_column,
    created_by_column=None,  # optional, 只有 plant_user 會用
) -> Select:
    """加 lab 或 owner filter 到 SQLAlchemy select。

    - system_admin: 不加 filter
    - lab_supervisor / lab_engineer: stmt.where(lab_id_column == user.lab_id)
    - plant_user: 如果 created_by_column 給了，stmt.where(... == user.id)；
                  否則 raise（plant_user 不該看這資源）
    """
    ...
```

呼叫範例（Phase 2+ service 內部）：

```python
async def list_orders(self, user: CurrentUser) -> list[Order]:
    stmt = select(Order)
    stmt = apply_lab_scope(stmt, user, Order.lab_id, created_by_column=Order.created_by)
    return (await self._session.execute(stmt)).scalars().all()
```

### Edge case 對照

| 情境 | 預期行為 |
|---|---|
| plant_user 查不是自己開的單 (`GET /api/orders/<other-id>`) | 404 (不洩漏存在性) 或 403 |
| engineer 查別 lab 的機台 | 404 / 403 同上 |
| supervisor 簽核別 lab 的單（直接打 API） | 403 |
| 主管 promote 自己變成兩個 lab 的主管 | sysadmin 才能改 user.lab_id，supervisor 自己不能 |
| sysadmin 不綁 lab 也 OK | `users.lab_id = NULL` 對 sysadmin 合法 |

### Implementation 進度

- [x] permission code 設計（resource:verb）— Phase 1 完成
- [x] role → perm mapping — Phase 1 完成（本文上方矩陣）
- [ ] `lab_id` FK 加進每個 model — A/B/C/D 各自 Phase 1+
- [ ] `apply_lab_scope` helper — E Phase 2
- [ ] 所有 list/get/update service 改吃 helper — A/B/C/D Phase 2+
- [ ] 404-not-403 不洩漏存在性 — 統一規則待定
- [ ] audit log scoped 讀 — E Phase 2（audit_logs 模組）

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
