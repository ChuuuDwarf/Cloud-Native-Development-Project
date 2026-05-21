 # 命名規範與類別宣告指南

> 本文件用來統一前端、後端、資料庫與 API 的命名方式，避免同一個概念在不同地方出現不同名稱。
>
> 適用範圍：Next.js 前端、FastAPI / Python 後端、資料庫 Schema、TypeScript 型別、Pydantic Schema、API Request / Response DTO。

---

## 1. 命名總原則

### 1.1 使用英文命名

程式碼內的變數、函式、類別、檔名、資料表與 API 欄位，統一使用英文。

✅ 建議：

```ts
orderId
sampleNo
experimentRunId
reportStatus
```

❌ 不建議：

```ts
委託單Id
樣品編號
實驗狀態
```

---

### 1.2 名稱要能看出用途

不要使用太短、太模糊的名稱。

✅ 建議：

```ts
getOrderById
createExperimentRun
updateReportStatus
assignedUserId
```

❌ 不建議：

```ts
getData
handleSubmit2
temp
obj
```

---

### 1.3 同一個概念只能有一種名稱

| 概念 | 統一命名 | 不要使用 |
|---|---|---|
| 委託單 | `Order` | `Request`, `Apply`, `Form` |
| 樣品 | `Sample` | `Specimen`, `Item` |
| WIP | `Wip` | `WorkItem`, `ProcessItem` |
| 實驗執行 | `ExperimentRun` | `Experiment`, `RunData` |
| 機台 | `Machine` | `Equipment`, `Tool` |
| 實驗方法 | `ExperimentMethod` | `Method` |
| Recipe | `Recipe` | `RecipeData` |
| 報告 | `Report` | `ExperimentReport` |
| 異常 / 告警 / 中止事件 | `Issue` | `AlertEvent`, `WarningEvent`, `AbnormalEvent` |
| 通知 | `Notification` | `Message`, `Notice` |
| 排程 | `Schedule` | `Plan` |
| 派工 | `Dispatch` | `Assignment` |
| 使用者 | `User` | `Account`, `Member` |
| 角色 | `Role` | `UserRole` |
| 系統設定 | `SystemSetting` | `Config`, `SettingData` |

---

## 2. 命名格式規則

### 2.1 TypeScript / JavaScript 命名

| 類型 | 命名格式 | 範例 |
|---|---|---|
| 變數 | camelCase | `orderId`, `reportStatus` |
| 函式 | camelCase | `getOrders`, `createReport` |
| 類別 | PascalCase | `OrderService`, `ReportController` |
| Interface | PascalCase | `Order`, `CreateOrderRequest` |
| Type | PascalCase | `OrderStatus`, `IssueType` |
| Enum | PascalCase | `OrderStatus`, `ReportAction` |
| 常數 | UPPER_SNAKE_CASE | `DEFAULT_PAGE_SIZE` |
| React Component | PascalCase | `OrderListPage` |
| React Hook | camelCase，開頭用 `use` | `useOrders`, `useReports` |

---

### 2.2 檔案命名

檔名統一使用 kebab-case。

✅ 建議：

```txt
order.service.ts
order.controller.ts
order.repository.ts
create-order.dto.ts
order-status.enum.ts
order-list-page.tsx
use-orders.ts
```

❌ 不建議：

```txt
OrderService.ts
orderService.ts
create_order_dto.ts
OrderListPage.tsx
```

---

### 2.3 API 路由命名

API 路由統一使用：

```txt
/api/{resource}
/api/{resource}/:id
/api/{resource}/:id/actions
```

規則：

| 項目 | 規則 | 範例 |
|---|---|---|
| Resource | 使用複數名詞 | `/api/orders` |
| ID | 使用 `:id` | `/api/orders/:id` |
| 流程動作 | 統一放在 `/actions` | `/api/orders/:id/actions` |
| 不用動詞當路由 | 動作用 HTTP Method 或 action 表示 | `POST /api/orders/:id/actions` |

✅ 建議：

```txt
GET    /api/orders
POST   /api/orders
GET    /api/orders/:id
PATCH  /api/orders/:id
POST   /api/orders/:id/actions
```

❌ 不建議：

```txt
POST /api/createOrder
POST /api/approveOrder
POST /api/orderSubmit
GET  /api/getOrderList
```

---

## 3. 後端分層命名

後端以 FastAPI 為主，建議每個主要模組都維持以下結構。若前端需要 TypeScript 型別，可另外放在前端 `types/` 或 `services/` 中。

```txt
backend/
  app/
    modules/
      orders/
        router.py
        service.py
        repository.py
        schemas.py
        enums.py
```

### 3.1 Router 命名

Router 負責接 API Request，不處理複雜商業邏輯。

```py
def get_orders():
    pass

def get_order_by_id(order_id: str):
    pass

def create_order(payload: CreateOrderDto):
    pass

def update_order(order_id: str, payload: UpdateOrderDto):
    pass

def delete_order(order_id: str):
    pass

def execute_order_action(order_id: str, payload: OrderActionDto):
    pass
```

命名規則：

| 行為 | 函式命名 | 範例 |
|---|---|---|
| 查詢列表 | `get{ResourcePlural}` | `getOrders()` |
| 查詢單筆 | `get{Resource}ById` | `getOrderById()` |
| 建立 | `create{Resource}` | `createOrder()` |
| 修改 | `update{Resource}` | `updateOrder()` |
| 刪除 / 停用 | `delete{Resource}` | `deleteOrder()` |
| 執行流程動作 | `execute{Resource}Action` | `executeOrderAction()` |

---

### 3.2 Service 命名

Service 負責商業邏輯、狀態檢查、權限判斷與跨模組流程。

```ts
export class OrderService {
  findOrders() {}
  findOrderById() {}
  createDraftOrder() {}
  updateDraftOrder() {}
  submitOrder() {}
  approveOrder() {}
  rejectOrder() {}
  closeOrder() {}
}
```

命名規則：

| 行為 | 函式命名 | 範例 |
|---|---|---|
| 查詢 | `find...` | `findOrders()` |
| 建立草稿 | `createDraft...` | `createDraftOrder()` |
| 狀態動作 | 直接用動詞 | `submitOrder()` |
| 驗證 | `validate...` | `validateOrderQuota()` |
| 檢查是否可做某事 | `can...` | `canCloseOrder()` |
| 同步狀態 | `sync...Status` | `syncOrderStatus()` |

---

### 3.3 Repository 命名

Repository 只負責資料庫存取，不寫商業規則。

```ts
export class OrderRepository {
  findMany() {}
  findById() {}
  create() {}
  updateById() {}
  softDeleteById() {}
}
```

---

## 4. DTO / Request / Response 宣告規則

### 4.1 DTO 命名

| 用途 | 命名格式 | 範例 |
|---|---|---|
| 建立資料 | `Create{Resource}Dto` | `CreateOrderDto` |
| 修改資料 | `Update{Resource}Dto` | `UpdateOrderDto` |
| 查詢條件 | `{Resource}QueryDto` | `OrderQueryDto` |
| 流程動作 | `{Resource}ActionDto` | `OrderActionDto` |
| 回傳資料 | `{Resource}ResponseDto` | `OrderResponseDto` |

範例：

```ts
export interface CreateOrderDto {
  applicantId: string;
  departmentId: string;
  sampleNo: string;
  experimentItems: CreateOrderItemDto[];
}

export interface OrderActionDto {
  action: OrderAction;
  reason?: string;
  comment?: string;
}
```

---

### 4.2 Request Body 欄位命名

API Request / Response 欄位統一使用 camelCase。

✅ 建議：

```json
{
  "orderId": "ORD001",
  "experimentRunId": "RUN001",
  "createdBy": "USER001",
  "createdAt": "2026-05-11T10:00:00+08:00"
}
```

❌ 不建議：

```json
{
  "order_id": "ORD001",
  "ExperimentRunID": "RUN001",
  "created_by": "USER001"
}
```

---

## 5. Type / Interface 宣告規則

### 5.1 Entity Interface

Entity 代表資料庫中的主要資料物件。

```ts
export interface Order {
  id: string;
  orderNo: string;
  applicantId: string;
  departmentId: string;
  status: OrderStatus;
  createdAt: string;
  updatedAt: string;
}
```

每個 Entity 建議都要有以下共用欄位：

```ts
export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
  updatedBy?: string;
}
```

---

### 5.2 List Response

列表 API 統一回傳分頁格式。

```ts
export interface PageResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
}
```

範例：

```ts
export type OrderListResponse = PageResponse<Order>;
```

---

### 5.3 API Error Response

錯誤回傳格式統一。

```ts
export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: unknown;
}
```

範例：

```json
{
  "code": "ORDER_NOT_EDITABLE",
  "message": "只有草稿或退回補件狀態可以編輯委託單"
}
```

---

## 6. Enum 宣告規則

### 6.1 Enum 值使用 snake_case

TypeScript enum 名稱使用 PascalCase，enum value 使用 snake_case 字串。

```ts
export enum OrderStatus {
  Draft = "draft",
  PendingApproval = "pending_approval",
  Returned = "returned",
  Rejected = "rejected",
  Approved = "approved",
  WaitingSample = "waiting_sample",
  Received = "received",
  InProgress = "in_progress",
  Completed = "completed",
  Closed = "closed",
}
```

原因：

- 程式碼內好讀。
- API 傳輸值穩定。
- 前端顯示文字可以另外用 mapping 處理。

---

### 6.2 Action Enum

流程動作統一用 Action Enum 管理。

```ts
export enum OrderAction {
  Submit = "submit",
  Cancel = "cancel",
  Approve = "approve",
  Return = "return",
  Reject = "reject",
  ConfirmDelivery = "confirm_delivery",
  ConfirmReceived = "confirm_received",
  ReadyForPickup = "ready_for_pickup",
  Close = "close",
}
```

```ts
export enum ReportAction {
  SubmitReview = "submit_review",
  Approve = "approve",
  Reject = "reject",
  Publish = "publish",
  ReturnToUser = "return_to_user",
  CreateRevision = "create_revision",
}
```

---

## 7. 主要模組類別命名建議

### 7.1 使用者與權限模組

| 類別 | 用途 |
|---|---|
| `AuthController` | 登入、登出 |
| `AuthService` | 驗證帳密、建立登入狀態 |
| `UserController` | 使用者 CRUD |
| `UserService` | 使用者管理邏輯 |
| `RoleController` | 角色與權限查詢 |
| `PermissionService` | 權限檢查 |

---

### 7.2 委託單模組

| 類別 | 用途 |
|---|---|
| `OrderController` | 委託單 API |
| `OrderService` | 委託單流程邏輯 |
| `OrderRepository` | 委託單資料存取 |
| `OrderActionService` | 委託單狀態動作處理 |
| `OrderHistoryService` | 委託單歷程紀錄 |
| `QuotaService` | 送測配額檢查 |

---

### 7.3 樣品與 WIP 模組

| 類別 | 用途 |
|---|---|
| `SampleController` | 樣品 API |
| `SampleService` | 收樣、分貨、交接、入庫、出庫 |
| `SampleHistoryService` | 樣品歷程 |
| `WipController` | WIP API |
| `WipService` | WIP 狀態與流程 |
| `WipCodeService` | WIP 編碼產生 |

---

### 7.4 機台、Recipe、實驗執行模組

| 類別 | 用途 |
|---|---|
| `MachineController` | 機台 API |
| `MachineService` | 機台狀態與支援項目管理 |
| `RecipeController` | Recipe API |
| `RecipeService` | Recipe 與版本管理 |
| `ExperimentMethodController` | 實驗方法 API |
| `ExperimentMethodService` | 實驗方法管理 |
| `ExperimentRunController` | 實驗執行 API |
| `ExperimentRunService` | 上機、下機、開始、完成、數據確認 |
| `MachineEventController` | 機台事件接收 API |
| `MachineEventService` | 機台訊號與事件處理 |

---

### 7.5 排程與派工模組

| 類別 | 用途 |
|---|---|
| `ScheduleController` | 排程 API |
| `ScheduleService` | 排程查詢與人工調整 |
| `ScheduleSuggestionService` | 產生排程建議 |
| `ScheduleConflictService` | 排程衝突檢查 |
| `RescheduleService` | 動態重排 |
| `DispatchController` | 派工 API |
| `DispatchService` | 派工建立、確認、開始、完成 |

---

### 7.6 報告模組

| 類別 | 用途 |
|---|---|
| `ReportController` | 報告 API |
| `ReportService` | 報告建立、編輯、查詢 |
| `ReportActionService` | 報告送審、確認、發布、回傳 |
| `ReportVersionService` | 報告版本管理 |
| `ReportFileService` | 報告附件處理 |

---

### 7.7 Issue / Notification 模組

| 類別 | 用途 |
|---|---|
| `IssueController` | 異常、告警、中止申請 API |
| `IssueService` | Issue 建立與處理 |
| `IssueActionService` | 核准、拒絕、關閉、升級、指派 |
| `NotificationController` | 通知 API |
| `NotificationService` | 通知建立、查詢、已讀 |
| `AlertEscalationService` | 告警升級處理 |

---

### 7.8 Dashboard / 系統設定模組

| 類別 | 用途 |
|---|---|
| `DashboardController` | Dashboard API |
| `DashboardService` | Dashboard 總覽統計 |
| `DashboardWidgetService` | 單一 Widget 資料 |
| `SimulationService` | 插單影響分析 |
| `SystemSettingController` | 系統設定 API |
| `SystemSettingService` | 系統設定查詢與修改 |
| `MasterDataController` | 共用下拉資料 API |
| `FileController` | 檔案上傳下載 API |
| `AuditLogService` | 稽核紀錄 |

---

## 8. 前端命名規則

### 8.1 頁面與元件命名

React Component 使用 PascalCase。

```tsx
export function OrderListPage() {}
export function OrderDetailPage() {}
export function OrderForm() {}
export function ReportStatusBadge() {}
```

檔案使用 kebab-case。

```txt
order-list-page.tsx
order-detail-page.tsx
order-form.tsx
report-status-badge.tsx
```

---

### 8.2 Hook 命名

Hook 統一使用 `use` 開頭。

```ts
useOrders()
useOrderDetail(orderId)
useCreateOrder()
useUpdateOrder()
useOrderActions()
```

---

### 8.3 API Client 命名

前端呼叫 API 的檔案建議集中在 `services` 或 `api` 資料夾。

```txt
src/services/order-api.ts
src/services/sample-api.ts
src/services/report-api.ts
```

```ts
export const orderApi = {
  getOrders,
  getOrderById,
  createOrder,
  updateOrder,
  executeOrderAction,
};
```

---

## 9. 資料庫命名規則

### 9.1 資料表命名

資料表統一使用 snake_case 複數名詞。

| Entity | Table Name |
|---|---|
| `User` | `users` |
| `Order` | `orders` |
| `OrderItem` | `order_items` |
| `Sample` | `samples` |
| `Wip` | `wips` |
| `Machine` | `machines` |
| `ExperimentRun` | `experiment_runs` |
| `Report` | `reports` |
| `Issue` | `issues` |
| `Notification` | `notifications` |
| `SystemSetting` | `system_settings` |
| `AuditLog` | `audit_logs` |

---

### 9.2 欄位命名

資料庫欄位使用 snake_case。

```sql
id
order_no
applicant_id
created_at
updated_at
created_by
updated_by
```

API 回傳時轉成 camelCase。

| DB 欄位 | API 欄位 |
|---|---|
| `order_no` | `orderNo` |
| `applicant_id` | `applicantId` |
| `created_at` | `createdAt` |
| `updated_at` | `updatedAt` |

---

## 10. ID 與編號命名

### 10.1 ID 欄位

系統內部關聯 ID 使用 `{resource}Id`。

```ts
orderId
sampleId
wipId
machineId
reportId
issueId
createdBy
updatedBy
```

---

### 10.2 顯示用編號

給使用者看的單號使用 `{resource}No`。

```ts
orderNo
sampleNo
wipNo
reportNo
```

差異：

| 欄位 | 用途 | 範例 |
|---|---|---|
| `id` | 系統內部唯一識別 | `550e8400-e29b-41d4-a716-446655440000` |
| `orderNo` | 使用者看的委託單編號 | `ORD-20260511-001` |

---

## 11. 狀態與顯示文字分離

狀態值不要直接拿來當畫面顯示文字。

```ts
export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  [OrderStatus.Draft]: "草稿",
  [OrderStatus.PendingApproval]: "待簽核",
  [OrderStatus.Returned]: "退回補件",
  [OrderStatus.Rejected]: "已拒絕",
  [OrderStatus.Approved]: "已核准",
  [OrderStatus.WaitingSample]: "待送樣",
  [OrderStatus.Received]: "已收樣",
  [OrderStatus.InProgress]: "實驗中",
  [OrderStatus.Completed]: "已完成",
  [OrderStatus.Closed]: "已結案",
};
```

這樣之後如果畫面文字要改，不會影響 API 與資料庫。

---

## 12. 共用欄位規範

### 12.1 建議每張主要資料表都有的欄位

| 欄位 | 說明 |
|---|---|
| `id` | 系統唯一 ID |
| `createdAt` | 建立時間 |
| `updatedAt` | 更新時間 |
| `createdBy` | 建立者 |
| `updatedBy` | 最後修改者 |
| `status` | 狀態 |
| `remark` | 備註，可選 |

---

### 12.2 軟刪除欄位

重要資料不建議真的刪除，建議使用軟刪除或停用。

```ts
isActive: boolean;
deletedAt?: string;
deletedBy?: string;
```

例如：

- 使用者停用
- 機台停用
- Recipe 停用
- 實驗方法停用
- 實驗室停用
- 部門停用

---

## 13. Action API 統一格式

所有 `/actions` API 建議使用相同格式。

```ts
export interface ActionRequest<TAction extends string> {
  action: TAction;
  reason?: string;
  comment?: string;
  payload?: Record<string, unknown>;
}
```

範例：

```json
{
  "action": "approve",
  "reason": "主管確認可執行",
  "comment": "核准送測"
}
```

如果該 action 需要額外資料，放在 `payload`。

```json
{
  "action": "load",
  "payload": {
    "machineId": "M001",
    "recipeId": "R001",
    "operatorId": "USER001"
  }
}
```

---

## 14. Audit Log 命名規則

所有關鍵操作都要寫入 Audit Log。

```ts
export interface AuditLog {
  id: string;
  actorId: string;
  action: string;
  targetType: AuditTargetType;
  targetId: string;
  beforeData?: unknown;
  afterData?: unknown;
  createdAt: string;
}
```

`targetType` 建議值：

```ts
export enum AuditTargetType {
  Order = "order",
  Sample = "sample",
  Wip = "wip",
  Machine = "machine",
  ExperimentRun = "experiment_run",
  Report = "report",
  Issue = "issue",
  User = "user",
  SystemSetting = "system_setting",
}
```

---

## 15. 建議資料夾結構

### 15.1 後端

```txt
backend/
  app/
    modules/
      auth/
      users/
      orders/
      samples/
      wips/
      machines/
      recipes/
      experiment_methods/
      experiment_runs/
      schedules/
      dispatches/
      reports/
      issues/
      notifications/
      dashboard/
      system_settings/
      files/
      audit_logs/
    common/
      schemas/
      enums/
      errors/
      middleware/
      utils/
```

---

### 15.2 前端

```txt
frontend/
  src/
    app/
      login/
      dashboard/
      orders/
      samples/
      wips/
      schedules/
      dispatches/
      experiment-runs/
      reports/
      issues/
      system-settings/
    components/
      common/
      orders/
      samples/
      reports/
    hooks/
    services/
    types/
    constants/
    utils/
```

---

## 16. 新增功能時的檢查清單

每次新增一個模組或 API，先確認以下項目：

- [ ] Resource 名稱是否已經存在？
- [ ] API 路由是否使用複數名詞？
- [ ] 是否真的需要新 API？還是可以用既有 `/actions`？
- [ ] Request / Response 欄位是否使用 camelCase？
- [ ] DTO 是否有建立？
- [ ] Status / Action 是否有 enum？
- [ ] 是否需要 Audit Log？
- [ ] 是否需要權限檢查？
- [ ] 是否需要同步其他模組狀態？
- [ ] 是否需要通知？

---

## 17. 最小實作建議

如果時間不夠，至少先做到以下規範：

1. API 路由統一使用 `/api/{resources}`。
2. 狀態變更統一使用 `POST /api/{resources}/:id/actions`。
3. Request / Response 欄位統一 camelCase。
4. 後端類別統一用 `Controller`、`Service`、`Repository`。
5. TypeScript enum value 統一 snake_case。
6. 檔案名稱統一 kebab-case。
7. 資料庫欄位統一 snake_case。
8. 畫面顯示文字不要直接綁死狀態值。
