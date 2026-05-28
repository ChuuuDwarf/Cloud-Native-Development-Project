# Supervisor Dashboard 重設計 — Design Spec

**Date:** 2026-05-29
**Owner:** Han (組員 E)
**Status:** Draft — for team review

## 背景

`/` 路由是目前 supervisor dashboard 的入口,使用者為 `lab_supervisor`(看自己 lab)與 Sprint 5 新增的 `general_supervisor`(看全廠)。

現況問題:
- 後端 `backend/app/modules/dashboard/` **整個是空的**(只有 `__pycache__`),`dashboardApi.getSnapshot()` 沒有對應 API。
- 現有 `frontend/app/page.tsx`(446 行)的 widget 以 issue 為主(4 個 KPI 有 3 個是 issue),遺漏 spec 規範的 `pendingApprovals` / `pendingSchedules` / `reportStatusCounts` 等。
- `frontend/app/_dashboard/` 下有 4 個未被引用的 panel 元件(`AttentionPanel`、`DispatchPanel`、`LabsPanel`、`MachineStatusPanel`),屬於上一輪殘留。
- `general_supervisor` 視角沒有專屬處理,跟 `lab_supervisor` 看到一樣的單一 lab 視野。

## 目標

主管打開 dashboard 的 primary use case 是「今天實驗室跑得怎麼樣」 — 屬於 **operational monitoring**。要做的事:

1. 用 5 KPI bar + 機台 heatmap + WIP pipeline + 3 欄底部 list 滿足 operational monitoring 的需求。
2. Role-aware:同一個 `/` 路由,後端依登入者 role(`lab_supervisor` vs `general_supervisor`)回傳 scoped 資料,前端 3 個 widget 依 role 切換內容。
3. 從零建後端 `dashboard` module,單 endpoint 一次回傳完整 snapshot。
4. 30s polling + SSE 推送(用 `/api/dashboard/stream`)的 hybrid 更新策略。

## Out of scope(這次不做)

- 單 widget API (`/api/dashboard/widgets/:key`)
- 插單影響分析 (`POST /api/dashboard/simulations`)
- 手機版優化
- 使用者自訂 widget 排序 / saved views
- 實驗室人員(`lab_engineer`)的 dashboard

---

## Layout 總覽

3-Zone Operational layout,desktop 一屏不滾動:

```
┌─────────────────────────────────────────────────────────────┐
│ Top: 5 KPI bar (等寬一列)                                    │
├─────────────────────────────┬───────────────────────────────┤
│ Mid Left: Machine Heatmap   │ Mid Right: WIP Pipeline       │
│ (per-lab stack)             │ (6-stage horizontal stacked)  │
├─────────────────────┬───────┴───────────┬───────────────────┤
│ Bottom Col 1        │ Bottom Col 2      │ Bottom Col 3      │
│ 待 triage           │ Recent Escalations│ (role-dependent)  │
└─────────────────────┴───────────────────┴───────────────────┘
```

| Zone | 高度 |
|---|---|
| Top KPI bar | 80px |
| Mid 雙欄 | 250px |
| Bottom 3 欄 | 200px |

## Section 1 · Top KPI Bar (5 KPI)

5 卡等寬 grid,卡內容:大數字(28px / weight 800)+ 標籤(12px)+ delta 箭頭(11px monospace)。手機 viewport 自動降成 2x3(但手機非本次目標,僅 graceful 處理)。

| KPI | 計算 | role-aware scope |
|---|---|---|
| **新單** | 今日 `orders.created_at >= today_start` 數量 | lab_sup: order 有 WIP 落在自己 lab;general_sup: 全部 |
| **完工** | 今日 `wips.status` 進入 `COMPLETED` 數量 | lab_sup: `lab_name = self`;general_sup: 全部 |
| **回傳** | 今日 `reports.status` 進入 `RETURNED` 數量 | 同 scope 規則 |
| **待簽** | 此刻 `orders.status = pending_approval` 數量 | lab_sup: 跟自己 lab 相關的待簽;general_sup: 全部 |
| **未結告警** | 此刻 `issues.status IN (open, in_progress, escalated)` 且 `severity IN (high, critical)` | lab-scoped |

**Delta 計算**:跟昨日同一時間點(rolling 24h)比較,正數顯示 `↑3`(綠),負數 `↓1`(紅),0 為 `→`(灰)。

**Threshold 顏色**:
- 預設 `var(--text2)` 中性
- `未結告警 > 0` → `var(--orange)`
- `待簽 > 5` → `var(--orange)`
- `完工 > 昨日同期` → 數字旁加綠色 ↑

**Drill-down**:
- 新單 → `/orders?created=today`
- 完工 → `/execution?status=completed`
- 回傳 → `/storage?status=returned`
- 待簽 → `/approve`
- 未結告警 → `/issues?severity=high,critical&status=open`

## Section 2 · Mid Left · Machine Heatmap

每個機台一格,顯示 `machine_no` 縮寫 + 狀態色塊。Per-lab stack 排列,lab 名稱 prefix 11px monospace。

| 狀態 | 色塊 |
|---|---|
| `in_use` | 飽和 `var(--blue)` |
| `idle` | 淺灰 `var(--text3)` |
| `maintenance` | `var(--orange)` |
| `faulty` | `var(--red)` 帶斜線 |
| `disabled` | 暗灰底,文字也暗 |

**Hover tooltip**:當前 recipe / 預估完成時間 / 操作員 / 今日累計使用 hr。

**Header 行**:
```
機台狀態          avg util 67%  •  in_use 5/12
```
- `avg util` = 今日 in_use 時數 / 8hr 加權平均(0-100%)
- `in_use 5/12` = 此刻使用中 / 總機台數

**Role-aware**:
- `lab_supervisor`:只顯示自己 lab 的機台(預期 4–6 個),不顯示 lab 前綴
- `general_supervisor`:依 lab 分組 stack(例 `LabA: ⬛⬛⬛⬛`、`LabB: ⬛⬛⬛`、...)

**Empty state**:`var(--text3)` 灰字「無機台資料」。

**Drill-down**:點機台格 → `/machine?id=<machine_id>`

## Section 3 · Mid Right · WIP Pipeline

橫向 100% 堆疊條,6 stage(對應 `WipStatus` + 報告狀態組合)。下方一行 stage 標籤 + 數字 + 同期 delta。

| Stage | 條件 | 顏色 | drill-down |
|---|---|---|---|
| **待排程** | WIP `pending` 且沒對應 dispatch | `var(--text3)` 灰 | `/dispatch` |
| **排程** | WIP `pending` 且已 dispatched / scheduled | `var(--cyan)` | `/dispatch` |
| **進行** | WIP `in_progress` | `var(--blue)` | `/execution` |
| **待傳** | WIP `completed` + report `RETURNED` + 下一步動作尚未觸發。語意:跨 lab 委託單時 = 「等轉交送件給下一個 lab」;單 lab 或最後 lab 時 = 「等送件結案」 | `var(--orange)` | `/execution` |
| **完** | 該 lab 對這個 WIP 已完成所有責任(sample 已 transferred 或 order 已 `CLOSED`) | `#3fb950` 綠 | `/storage` |
| **終止** | WIP `TERMINATED` | `var(--red)` 帶叉 | `/orders?status=terminated` |

**右上角總數**:`共 31 件`

**Role-aware**:
- `lab_supervisor`:只算自己 lab 的 WIP
- `general_supervisor`:全廠 WIP 加總(per-lab 對比放在 Bottom Col 3 的 leaderboard)

**Empty state**:條變空灰底,中央 `var(--text3)` 字「目前無 WIP」

**注意**:此 widget 的「待傳」stage 會直接視覺化 closure flow review 中 🟡#5 那段 `publish_report` → `WAITING_PICKUP` 灰色地帶 — 之後修 closure 時可用本 widget 確認 stage 轉移正確。

## Section 4 · Bottom Zone (3 欄)

3 等寬 column,各 200px 高,各 5 列 list。前 2 欄 role 共用,第 3 欄依 role 切換。

### Col 1 — 待 triage(我此刻該看的事)

5 列,按迫切性遞減排序,綜合 3 種來源:

| 來源 | 顯示格式 | 排序權重 |
|---|---|---|
| `pending_approval` orders | `[簽核] ORD-2025-0012 · 張工 · 2h ago` | 越久越優先 |
| 我未 ack 且 `escalated` 的 issues | `[告警] LabA #ISS-091 · critical · 升至 L2` | severity + 升級 level 越高越優先 |
| 我未 ack 且 `high+critical` open issues | `[告警] LabB #ISS-085 · high · 30min ago` | severity 為次 |

**Drill-down**:點列 → 對應頁。已 ack 的 escalated issue 不會在這欄出現。

### Col 2 — Recent Escalations(過去 24h 升級)

5 列,按升級時間遞減:

```
[critical L2] LabA · 真空泵故障 · 12 min ago
[high L1]    LabC · recipe 異常 · 38 min ago
```

**Drill-down**:點列 → `/issues/<id>`,自動觸發 ack(避免再回 Col 1)。

### Col 3a (lab_supervisor) — Recent Completions

5 列,按 RETURNED 時間遞減:

```
[完] WIP-A001 · ORD-2025-0012 · 5 min ago
[完] WIP-A003 · ORD-2025-0019 · 12 min ago
```

**Drill-down**:點列 → `/reports/<id>` 或對應 order 頁。

### Col 3b (general_supervisor) — Lab Leaderboard

5 列(5 labs),按「今日完工數」遞減:

```
LabA  完工 9   待傳 2   告警 1   util 78%   ↑
LabD  完工 7   待傳 1   告警 0   util 65%   →
```

每列 4 個指標 + 右側趨勢箭頭(今日完工 vs 昨日同期)。

**Drill-down**:點列 → `/orders?lab=<lab_name>`。

## Section 5 · 後端 API

### Endpoint

```
GET /api/dashboard
```

無 query param,scoping 全部從 `current_user` + `OrderScope` 推導(reuse 現有 `OrderScope.from_user(user)`)。

### Response shape(Pydantic v2)

```python
class DashboardSnapshot(BaseModel):
    viewer_role: Literal["lab_supervisor", "general_supervisor"]
    viewer_lab: str | None  # lab_supervisor 才有
    generated_at: datetime

    kpi: KpiBar
    machines: MachineHeatmap
    wip_pipeline: WipPipeline
    triage: list[TriageItem]
    recent_escalations: list[EscalationRow]
    recent_completions: list[CompletionRow] | None  # lab_sup 才有,否則 null
    lab_leaderboard: list[LabRow] | None  # general_sup 才有,否則 null


class KpiCard(BaseModel):
    value: int
    delta_24h: int  # 正↑ / 負↓ / 0→
    threshold_color: Literal["neutral", "orange", "red"] | None


class KpiBar(BaseModel):
    new_orders: KpiCard
    completed: KpiCard
    returned: KpiCard
    pending_approval: KpiCard
    open_critical_high_issues: KpiCard


class MachineGrid(BaseModel):
    machine_id: str
    machine_no: str
    lab_name: str
    status: MachineStatus  # 既有 enum
    today_hours: float
    current_recipe: str | None
    current_operator: str | None
    est_completion_at: datetime | None


class MachineHeatmap(BaseModel):
    by_lab: dict[str, list[MachineGrid]]  # key 為 lab_name
    avg_utilization_pct: int  # 0-100
    in_use_count: int
    total_count: int


class WipPipeline(BaseModel):
    total: int
    waiting_dispatch: tuple[int, int]  # (count, delta_24h)
    dispatched: tuple[int, int]
    in_progress: tuple[int, int]
    awaiting_handoff: tuple[int, int]  # 「待傳」
    done: tuple[int, int]
    terminated: tuple[int, int]


class TriageItem(BaseModel):
    type: Literal["pending_approval", "escalated_issue", "open_issue"]
    ref_id: str
    label: str
    lab_name: str | None
    severity: Severity | None
    created_at: datetime


class EscalationRow(BaseModel):
    issue_id: str
    lab_name: str
    severity: Severity
    escalation_level: int
    title: str
    escalated_at: datetime


class CompletionRow(BaseModel):
    wip_no: str
    order_no: str
    lab_name: str
    returned_at: datetime


class LabRow(BaseModel):
    lab_name: str
    completed_today: int
    awaiting_handoff: int
    open_high_critical_issues: int
    avg_utilization_pct: int
    trend_24h: Literal["up", "flat", "down"]
```

### Service 並行查詢

```python
async def compute_snapshot(self, user: CurrentUser) -> DashboardSnapshot:
    scope = OrderScope.from_user(user)

    kpi, machines, pipeline, triage, escalations, completions, leaderboard = (
        await asyncio.gather(
            self._compute_kpi(scope),
            self._compute_machines(scope),
            self._compute_pipeline(scope),
            self._compute_triage(scope, user),
            self._compute_escalations(scope, user),
            self._compute_completions(scope) if not scope.sees_all_labs else _none(),
            self._compute_leaderboard() if scope.sees_all_labs else _none(),
        )
    )
    return DashboardSnapshot(...)
```

每個 `_compute_*` 在 repository 各一個 method,測試獨立。

### 檔案結構

```
backend/app/modules/dashboard/
    __init__.py
    router.py        # GET /api/dashboard + GET /api/dashboard/stream
    service.py       # DashboardService.compute_snapshot()
    repository.py    # 一個 widget 一個 method
    schemas.py       # 上述 schema 集合
    dependencies.py
    publisher.py     # publish to Redis pub/sub
```

### Permission

`router.py` 上的 endpoint 用 `require_permission("dashboard:read")`。

## Section 6 · Refresh 策略 + Visual Tokens + Migration

### Refresh — Hybrid (polling + SSE invalidation)

**Primary**:TanStack Query `refetchInterval: 30_000`(沿用現有模式)。

**Bonus SSE**:`GET /api/dashboard/stream` 推送下列事件,前端統一 `queryClient.invalidateQueries(["dashboard"])`:

| 事件 | trigger 點 |
|---|---|
| `dashboard.new_escalation` | `workers/escalation.py` 升級時 |
| `dashboard.new_pending_approval` | `orders/service.py::submit_for_approval` |
| `dashboard.report_returned` | `reports/service.py::publish_report`(report → RETURNED) |

每個事件不帶 payload,前端統一 refetch(整 snapshot 取得便宜)。Redis pub/sub channel:`dashboard:events:{lab_name}`(lab_sup 訂閱對應 lab)或 `dashboard:events:*`(general_sup 訂閱 wildcard)。

```typescript
// frontend useDashboardStream hook
useEffect(() => {
  const es = new EventSource("/api/dashboard/stream");
  es.onmessage = () => queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  return () => es.close();
}, [queryClient]);
```

### Visual Tokens(全部沿用 globals.css 既有 token)

| 元素 | 規則 |
|---|---|
| Panel 容器 | `background: var(--s1)` / `border: 1px solid var(--border)` / `border-radius: 8` / `padding: 16` |
| KPI 大數字 | 28px / weight 800 / `var(--text1)` |
| KPI 標籤 | 12px / `var(--text2)` |
| Delta arrow | 11px monospace,顏色 ↑綠 / ↓紅 / →灰 |
| Stage colors | 灰 (`--text3`) / cyan / blue / orange / 綠 (`#3fb950`) / 紅 (`--red`) |
| Severity colors | critical `var(--red)` / high `var(--orange)` / medium `#d4a300` / low `var(--cyan)` |
| Zone 間距 | 16px gap |
| Card 間距 | 14px gap |

字體:`--font-display`(文字)+ Roboto Mono(數字 / delta / timestamp)。

### Migration

**前端清理(刪除)**:
- `frontend/app/_dashboard/AttentionPanel.tsx`
- `frontend/app/_dashboard/DispatchPanel.tsx`
- `frontend/app/_dashboard/LabsPanel.tsx`
- `frontend/app/_dashboard/MachineStatusPanel.tsx`

**前端重寫**:
- `frontend/app/page.tsx`(只剩 layout orchestration)
- `frontend/src/types/dashboard.ts`
- `frontend/src/services/dashboard-api.ts`

**前端新增**:
```
frontend/app/_dashboard/
    KpiBar.tsx
    MachineHeatmap.tsx
    WipPipeline.tsx
    TriageList.tsx
    EscalationsList.tsx
    CompletionsList.tsx       # lab_sup only
    LabLeaderboard.tsx        # general_sup only
    useDashboardStream.ts     # SSE hook
```

**後端新增**:見 Section 5 檔案結構。

**對其他 service 的最小改動**(各 1–2 行):
- `workers/escalation.py` → 升級時呼叫 `publisher.publish_new_escalation(lab_name)`
- `modules/orders/service.py::submit_for_approval` → `publisher.publish_new_pending_approval(lab_name)`
- `modules/reports/service.py::publish_report` → `publisher.publish_report_returned(lab_name)`

### Testing

| 層級 | 涵蓋 |
|---|---|
| Backend pytest | 各 widget repository method 單元測試;Role scope unit tests(lab_sup vs general_sup);`DashboardService.compute_snapshot` happy path 並行;permission guard |
| Frontend vitest | 各 panel 元件 mock data render;`KpiCard` 顏色 threshold;`WipPipeline` 空 state;role 切換 Col 3 |
| Playwright | dashboard 載入;lab_sup 與 general_sup fixture 看到不同 Col 3 |

## Side effect

完成這個 dashboard 後,**WIP Pipeline 的「待傳」stage 會直接視覺化 closure flow review 🟡#5 那段 `publish_report` → `WAITING_PICKUP` 灰色地帶**,後續修 closure 時可用本 widget 即時確認 stage 轉移正確,等於把該 bug 從「藏在 backend」變成 dashboard 上 explicit 看得到。

## 後續步驟

1. 隊友 review 此 design.md
2. Approve 後進 writing-plans skill 寫實作計畫
3. 實作分階段:後端 module → 前端 panel components → SSE wiring → E2E
