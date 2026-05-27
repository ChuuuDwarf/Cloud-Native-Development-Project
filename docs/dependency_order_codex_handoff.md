# 委託單相依 / 獨立子單功能：Codex 修改指令與隊友銜接文件

## 0. 任務摘要

本次只要在「委託單 order_items」加入相依 / 獨立子單描述能力。

核心欄位：

| API 欄位 | DB 欄位建議 | 型別 | 預設 | 用途 |
|---|---|---|---|---|
| `targetGroup` | `target_group` | string | `G1` | 相依群組。同一組內才互相影響。 |
| `target` | `target` | integer | `1` | 同一個 `targetGroup` 內的執行順序，數字越小越先做。 |
| `check` | `dependency_check` | boolean | `false` | 先開給後續排程組員使用，目前建立時預設 false。 |

核心規則：

```text
Group 是相依鏈的邊界。
Target 只在同一個 Group 裡比較，不是整張委託單的全域排序。
不同 Group 彼此獨立，不互相等待。
check 目前只預設 false，不參與目前 order_item 的相依判斷。
```

範例：

```text
A -> B -> C    D    E -> F    H
```

應填成：

| item | targetGroup | target | check |
|---|---|---:|---|
| A | G1 | 1 | false |
| B | G1 | 2 | false |
| C | G1 | 3 | false |
| D | G2 | 1 | false |
| E | G3 | 1 | false |
| F | G3 | 2 | false |
| H | G4 | 1 | false |

可一開始執行：A、D、E、H。
B 只等 A；C 只等 B；F 只等 E。
D、H 自己一組，不等也不卡其他 group。

---

## 1. 給 Codex 的最高優先級限制

請嚴格遵守以下限制。

### 1.1 絕對禁止修改的檔案 / 目錄

不要修改任何環境、部署、容器、CI、套件管理、金鑰、設定檔，包含但不限於：

```text
.env
.env.*
*.env
backend/.env
backend/.env.example
frontend/.env
frontend/.env.local
frontend/.env.example
.devcontainer/**
Dockerfile
**/Dockerfile
docker-compose.yml
docker-compose.*.yml
.github/**
.git/**
.gitignore
backend/.dockerignore
backend/alembic.ini
backend/alembic/env.py
package.json
package-lock.json
pnpm-lock.yaml
yarn.lock
requirements.txt
pyproject.toml
poetry.lock
```

除非本文件明確要求，否則不要修改任何環境與依賴設定。

### 1.2 禁止做的事情

- 不要重構整個專案。
- 不要改登入、權限、角色、lab scope、master data、quota 等無關功能。
- 不要改既有 API route path。
- 不要改 docker / devcontainer / CI。
- 不要新增外部套件。
- 不要更名既有資料表。
- 不要刪除既有欄位。
- 不要把 `group` 或 `check` 當 DB 欄位名稱，避免撞 SQL 語意。
- 不要把 `target` 當成全域排序；它只在同一個 `target_group` 裡比較。
- 不要在本次實作 WIP 排程引擎，只需讓 order_items 能保存並回傳相依資料。

### 1.3 允許修改的範圍

只允許針對本功能必要修改下列檔案：

```text
backend/app/db/models/order_management.py
backend/app/schemas/order.py
backend/app/repos/order_mappers.py
backend/app/repos/order_repo.py
backend/alembic/versions/<新增一個 migration 檔案>
frontend/app/orders/types.ts
frontend/app/orders/constants.ts
frontend/app/orders/lib/formItems.ts
frontend/app/orders/hooks/useOrdersPage.ts
frontend/app/orders/components/OrderForm.tsx
frontend/app/orders/components/SampleExperimentEditor.tsx
frontend/app/orders/components/OrderDetail.tsx
frontend/app/orders/lib/templates.ts
frontend/app/orders/templates/useOrderTemplatesPage.ts
frontend/app/orders/templates/page.tsx
```

其中 templates 相關檔案只有在型別或模板儲存流程需要補 `targetGroup / target / check` 時才修改。

---

## 2. 後端修改需求

### 2.1 SQLAlchemy Model

檔案：

```text
backend/app/db/models/order_management.py
```

在 `OrderItemModel` 中新增三個欄位：

```python
target_group: Mapped[str] = mapped_column(String(50), nullable=False, default="G1")
target: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
dependency_check: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

建議放在 `experiment_id` 後面、`status` 前面。

不要使用欄位名稱 `group` 或 `check`。

---

### 2.2 Alembic Migration

新增一個 migration 檔案到：

```text
backend/alembic/versions/
```

檔名可類似：

```text
0005_add_order_item_dependency_fields.py
```

注意：

- 不要修改舊 migration。
- `down_revision` 要接目前最新 migration。若目前最新是 `0004_d_wip_execution_experiment_data`，就接它。
- 若實際最新不同，請以專案當下 `alembic/versions` 的最新 revision 為準。

範例內容：

```python
"""add order item dependency fields

Revision ID: 0005_add_order_item_dependency_fields
Revises: 0004_d_wip_execution_experiment_data
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_order_item_dependency_fields"
down_revision = "0004_d_wip_execution_experiment_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("target_group", sa.String(length=50), nullable=False, server_default="G1"),
    )
    op.add_column(
        "order_items",
        sa.Column("target", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "order_items",
        sa.Column("dependency_check", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_check_constraint(
        "order_items_target_positive_check",
        "order_items",
        "target >= 1",
    )

    op.create_index(
        "ix_order_items_dependency",
        "order_items",
        ["order_id", "sample_id", "target_group", "target"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_items_dependency", table_name="order_items")
    op.drop_constraint("order_items_target_positive_check", "order_items", type_="check")
    op.drop_column("order_items", "dependency_check")
    op.drop_column("order_items", "target")
    op.drop_column("order_items", "target_group")
```

若資料庫或 Alembic 實際使用的 revision 命名不同，請保留相同功能但調整 revision metadata。

---

### 2.3 Pydantic Schema

檔案：

```text
backend/app/schemas/order.py
```

在 `OrderItemCreate` 加入：

```python
target_group: str = Field(default="G1", alias="targetGroup", min_length=1)
target: int = Field(default=1, ge=1)
dependency_check: bool = Field(default=False, alias="check")
```

也請加入 normalize validator：

```python
@field_validator("target_group")
@classmethod
def normalize_target_group(cls, value: str) -> str:
    stripped = value.strip()
    return stripped or "G1"
```

`OrderItem` 繼承 `OrderItemCreate`，所以回傳也會帶這三個欄位。

API 對外欄位必須是：

```json
{
  "targetGroup": "G1",
  "target": 1,
  "check": false
}
```

---

### 2.4 Mapper

檔案：

```text
backend/app/repos/order_mappers.py
```

在 `item_to_schema()` 裡補：

```python
targetGroup=item.target_group,
target=item.target,
check=item.dependency_check,
```

不要移除既有欄位。

---

### 2.5 Repository 建立 item

檔案：

```text
backend/app/repos/order_repo.py
```

在 `_make_item()` 建立 `OrderItemModel` 時補：

```python
target_group=payload.target_group,
target=payload.target,
dependency_check=payload.dependency_check,
```

也要檢查更新委託單時是否會重建或 patch item：

- 如果更新時是刪掉重建 items：`_make_item()` 補完就足夠。
- 如果更新時會沿用舊 item 並逐欄位更新，請同步更新：

```python
item.target_group = payload.target_group
item.target = payload.target
item.dependency_check = payload.dependency_check
```

---

## 3. 前端修改需求

### 3.1 TypeScript 型別

檔案：

```text
frontend/app/orders/types.ts
```

修改 `FormItem`：

```ts
export type FormItem = {
  sampleId: string;
  sampleName: string;
  labId: string;
  experimentId: string;
  targetGroup: string;
  target: number;
  check: boolean;
};
```

修改 `OrderItem`：

```ts
export type OrderItem = {
  id: number;
  sampleId: string;
  sampleName?: string | null;
  labId: string;
  experimentId: string;
  targetGroup: string;
  target: number;
  check: boolean;
  status?: OrderStatus;
  approvedBy?: string | null;
  approvedAt?: string | null;
  returnReason?: string | null;
  rejectReason?: string | null;
  quotaExceeded?: boolean;
  quotaOverride?: boolean;
};
```

若模板型別使用 `FormItem[]`，會自動一起支援。

---

### 3.2 空白預設 item

檔案：

```text
frontend/app/orders/constants.ts
```

修改 `emptyFormItem`：

```ts
export const emptyFormItem = {
  sampleId: "",
  sampleName: "",
  labId: "",
  experimentId: "",
  targetGroup: "G1",
  target: 1,
  check: false,
};
```

---

### 3.3 建立預設 item / 勾選新增實驗

檔案：

```text
frontend/app/orders/lib/formItems.ts
```

`createDefaultItem()` 回傳補：

```ts
targetGroup: "G1",
target: 1,
check: false,
```

`toggleExperimentInGroup()` 新增 item 時補：

```ts
targetGroup: `G${group.items.length + 1}`,
target: 1,
check: false,
```

說明：新增實驗預設先當獨立子單，使用者可手動調整 targetGroup 與 target。

---

### 3.4 編輯舊委託單時保留欄位

檔案：

```text
frontend/app/orders/hooks/useOrdersPage.ts
```

`startEditOrder()` 裡 `setItems(orderItems.map(...))` 要保留 dependency 欄位：

```ts
orderItems.map(({ sampleId, sampleName, labId, experimentId, targetGroup, target, check }) => ({
  sampleId,
  sampleName: sampleName ?? "",
  labId,
  experimentId,
  targetGroup: targetGroup || "G1",
  target: target || 1,
  check: check ?? false,
}))
```

否則編輯一次會把相依設定洗掉。

---

### 3.5 加入更新 dependency 欄位的 handler

檔案：

```text
frontend/app/orders/hooks/useOrdersPage.ts
```

新增 function：

```ts
function updateDependencyField(
  index: number,
  field: "targetGroup" | "target",
  value: string | number
) {
  setItems((current) =>
    current.map((item, itemIndex) => {
      if (itemIndex !== index) return item;

      if (field === "target") {
        return {
          ...item,
          target: Math.max(1, Number(value) || 1),
        };
      }

      return {
        ...item,
        targetGroup: String(value).trim() || "G1",
      };
    })
  );
}
```

並在 return object 中加入：

```ts
updateDependencyField,
```

---

### 3.6 表單驗證

檔案：

```text
frontend/app/orders/hooks/useOrdersPage.ts
```

在 `validateForm()` 裡補：

```ts
const invalidDependencyIndex = items.findIndex(
  (item) => !item.targetGroup.trim() || item.target < 1
);

if (invalidDependencyIndex >= 0) {
  return `明細 ${invalidDependencyIndex + 1} 的相依群組不可為空，Target 必須大於等於 1`;
}
```

目前不要強制同 group target 不可重複，除非 PM / 組員確認同 group 不支援並行。這次只做欄位支援與基本驗證。

---

### 3.7 OrderForm 傳遞 handler

檔案：

```text
frontend/app/orders/components/OrderForm.tsx
```

確認 props 加入：

```ts
onDependencyChange: (
  index: number,
  field: "targetGroup" | "target",
  value: string | number
) => void;
```

並傳給 `SampleExperimentEditor`：

```tsx
<SampleExperimentEditor
  ...
  onDependencyChange={onDependencyChange}
/>
```

呼叫 `OrderForm` 的地方也要把 `page.updateDependencyField` 傳入。

---

### 3.8 SampleExperimentEditor 顯示欄位

檔案：

```text
frontend/app/orders/components/SampleExperimentEditor.tsx
```

Props 加入：

```ts
onDependencyChange: (
  index: number,
  field: "targetGroup" | "target",
  value: string | number
) => void;
```

在每個實驗明細卡片中顯示兩個輸入欄位：

```tsx
<div style={{ display: "grid", gridTemplateColumns: "1fr 120px", gap: 8, marginTop: 8 }}>
  <label style={{ display: "grid", gap: 4 }}>
    <span style={{ fontSize: 12, color: "var(--text3)" }}>相依群組</span>
    <input
      value={item.targetGroup}
      onChange={(event) => onDependencyChange(index, "targetGroup", event.target.value)}
      placeholder="G1"
      style={inputStyle}
    />
  </label>

  <label style={{ display: "grid", gap: 4 }}>
    <span style={{ fontSize: 12, color: "var(--text3)" }}>Target</span>
    <input
      type="number"
      min={1}
      value={item.target}
      onChange={(event) => onDependencyChange(index, "target", Number(event.target.value) || 1)}
      style={inputStyle}
    />
  </label>
</div>
```

`check` 不需要讓使用者填，目前 hidden 固定由前端送 false 或沿用既有值。

---

### 3.9 詳細頁顯示

檔案：

```text
frontend/app/orders/components/OrderDetail.tsx
```

在 order item 顯示區加入：

```tsx
<span>相依群組：{item.targetGroup || "G1"}</span>
<span>Target：{item.target || 1}</span>
<span>Check：{item.check ? "true" : "false"}</span>
```

不要大改 UI，只要能讓使用者確認資料有存回來即可。

---

## 4. 不要本次實作的 WIP 判斷，但請保留給隊友

本次可以不改 WIP。後續 WIP 組員判斷某筆 WIP 能不能開始時，邏輯應該是：

```sql
SELECT COUNT(*)
FROM wips
WHERE order_no = :orderNo
  AND sample_id = :sampleId
  AND target_group = :targetGroup
  AND target < :currentTarget
  AND status != 'completed';
```

如果 count = 0，代表可以開始。

注意：

```text
一定要限制同一個 target_group。
不能只看 target < currentTarget。
不同 group 彼此獨立。
```

---

## 5. 驗收測試情境

### 5.1 建立委託單

建立一張委託單，items 如下：

```json
[
  { "sampleId": "S001", "sampleName": "樣品1", "labId": "LAB_A", "experimentId": "A", "targetGroup": "G1", "target": 1, "check": false },
  { "sampleId": "S001", "sampleName": "樣品1", "labId": "LAB_B", "experimentId": "B", "targetGroup": "G1", "target": 2, "check": false },
  { "sampleId": "S001", "sampleName": "樣品1", "labId": "LAB_C", "experimentId": "C", "targetGroup": "G1", "target": 3, "check": false },
  { "sampleId": "S001", "sampleName": "樣品1", "labId": "LAB_D", "experimentId": "D", "targetGroup": "G2", "target": 1, "check": false },
  { "sampleId": "S001", "sampleName": "樣品1", "labId": "LAB_E", "experimentId": "E", "targetGroup": "G3", "target": 1, "check": false },
  { "sampleId": "S001", "sampleName": "樣品1", "labId": "LAB_F", "experimentId": "F", "targetGroup": "G3", "target": 2, "check": false },
  { "sampleId": "S001", "sampleName": "樣品1", "labId": "LAB_H", "experimentId": "H", "targetGroup": "G4", "target": 1, "check": false }
]
```

API 回傳與 DB 應保留：

```text
G1: A target 1, B target 2, C target 3
G2: D target 1
G3: E target 1, F target 2
G4: H target 1
```

### 5.2 編輯委託單

1. 建立後重新打開編輯。
2. 確認每筆 item 的 `targetGroup / target / check` 都沒有消失。
3. 修改其中一筆，例如 F target 從 2 改 3。
4. 儲存後重新讀取，確認 API 回傳 target = 3。

### 5.3 前端基本驗證

- targetGroup 空白時應擋下。
- target 小於 1 時應擋下或自動修正為 1。
- check 預設 false。

---

## 6. 完成後請回報

完成後請列出：

1. 修改過的檔案清單。
2. 新增的 migration 檔案名稱與 revision。
3. 手動測試結果。
4. 確認沒有修改任何環境、Docker、CI、依賴、lock file。

---

## 7. 給隊友的銜接說明

這次 A 組 / 委託單端只負責讓 order_items 能存相依資訊。

實際語意如下：

```text
targetGroup：相依鏈 ID。
target：同一條相依鏈內的執行順序。
check：目前預設 false，保留給排程 / WIP 模組使用。
```

重要規則：

```text
Target 只在同一個 targetGroup 裡比較。
不同 targetGroup 是獨立流程。
```

例如：

```text
A -> B -> C    D    E -> F    H
```

資料為：

```text
G1: A(1) -> B(2) -> C(3)
G2: D(1)
G3: E(1) -> F(2)
G4: H(1)
```

WIP 端未來建立資料時，建議從 order_items 複製：

```text
order_items.id               -> wips.order_item_id
order_items.sample_id        -> wips.sample_id
order_items.lab_id           -> wips.lab_id
order_items.experiment_id    -> wips.experiment_id
order_items.target_group     -> wips.target_group
order_items.target           -> wips.target
order_items.dependency_check -> wips.dependency_check
```

WIP 判斷能不能開始時，只看同一張委託單、同一個樣品、同一個 target_group 中，有沒有 target 比自己小且尚未完成的項目。

