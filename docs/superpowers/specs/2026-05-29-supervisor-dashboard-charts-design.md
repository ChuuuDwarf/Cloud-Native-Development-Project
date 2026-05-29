# Supervisor Dashboard 圖表化 — Design Spec

**Date:** 2026-05-29
**Owner:** Han (組員 E)
**Status:** Draft — for team review
**Amends:** `docs/superpowers/specs/2026-05-29-supervisor-dashboard-redesign-design.md` (the original 3-Zone Operational layout)

## 背景

原 dashboard spec 已實作完成並 push 到 remote(commits `931ce90..94c1ab8`)。但實際使用後發現視覺資訊量偏低 — 大部分 widget 是純數字 + delta arrow + 簡單堆疊條,缺少趨勢與比較感。

## 目標

把「數字主、視覺輔」改成「圖表主、數字輔」。具體:5 個 widget 加 chart 元素或整個替換為 chart;新增 24h 時序資料 backend 支援。仍維持「desktop 一屏不滾動」、「role-aware」、「30s polling + SSE invalidation」的原架構。

## Chart 路線

**裝 Recharts 輕量 chart lib**(`npm install recharts`,~200 KB gzipped)。其他選項(純 inline SVG / hybrid)在 brainstorm 階段排除,理由是後續迭代成本。

單一例外:**WIP Pipeline 仍走 inline + CSS**(單條 100% 堆疊條,Recharts overkill)。

## Out of scope(這次仍不做)

- KPI 待簽 / 告警 兩個 state-type metric 不畫 sparkline(沒 hourly 歷史可算)
- per-lab 24h util 趨勢(只 current 值)
- Chart 上的點擊 drill-down(throughput chart 是 aggregate,不對應單一 item)
- 行動裝置優化

---

## Section 1 · KPI Bar with background sparkline

每張 KPI tile 在現有 80px 高度內疊加 24h 趨勢 line chart 作為背景:

- tile 主元素(數字 + delta arrow)保持不動,不挪位置不縮字
- Recharts `<LineChart>` 絕對定位填滿卡片下半部(`bottom: 0`, `left: 0`, `right: 0`, `height: 50%`)
- 單一 `<Line>`:`stroke` = 該 KPI 的 threshold color、`strokeOpacity: 0.15`、寬度 1.5px、`dot={false}`、`activeDot={false}`
- x-axis / y-axis / grid / tooltip / legend 全部隱藏
- Recharts `<ResponsiveContainer width="100%" height="100%">` 跟著卡片 resize

### 適用範圍

- **新單 / 完工 / 回傳** — 流量型,有 hourly 歷史 → 畫 sparkline
- **待簽 / 告警** — state-type,無 hourly 歷史 → `sparkline_24h: None`,前端條件 render(不畫 `<LineChart>`)

### Empty state(剛上線、24h 都 0)

不畫 — 卡片變回純平。前端判斷:`sparkline_24h == null || sparkline_24h.every(v => v === 0)` → 跳過 `<LineChart>` 渲染。

```
┌─────────────┐
│ 新單         │
│ 12  ↑3      │
│ ▁▂▃▄▆▅▃▂▁  │  ← 背景 line, opacity 0.15
└─────────────┘
```

## Section 2 · Machine Heatmap + Radial Util Gauge

Panel header 重組:把 `avg util` 從 monospace 小字升級為主視覺,並在每個 lab heatmap row 末端加 mini util bar。

### Header 大 radial gauge

- Recharts `<RadialBarChart>` 80x80px,半圓 (`startAngle=180`, `endAngle=0`)
- background track:`fill="var(--s2)"`,opacity 1
- active arc:顏色按 util 值動態
  - `< 40%` → `var(--text3)` 灰(用太少)
  - `40–79%` → `var(--blue)` 健康
  - `≥ 80%` → `var(--orange)` 偏高
  - `≥ 95%` → `var(--red)` 過載
- 中央 label:28px 大字 `67%`,下方 11px 小字 `avg util`

### Header 旁輔助數字

右側 monospace 一欄:
- 28px 同 threshold color `67%`(視覺上跟 gauge 中心 echo)
- 11px monospace `in_use 5/12`

### Per-lab mini util bar

每個 lab heatmap row 最右端加一條 20px 寬 × row 同高的迷你進度條:
- background `var(--s2)`
- fill 顏色按該 lab util 同 threshold 規則
- fill 寬度 = `(lab_util_pct / 100) * 20px`
- 上方顯示 11px monospace 該 lab `util` 數字(例:`78%`)

```
┌─ 機台狀態 ───────────────────────────────────────┐
│  ╭───────╮    avg util         in_use            │
│  │  67%  │      67%             5/12             │
│  ╰───────╯                                       │
│                                                  │
│  LabA  ⬛⬛⬛⬛                            78% ▓▓▓ │
│  LabB  ⬛⬛⬛                              65% ▓▓  │
│  LabC  ⬛⬛⬛⬛⬛                           72% ▓▓▓ │
└──────────────────────────────────────────────────┘
```

## Section 3 · WIP Pipeline 強化

仍走 inline + CSS(Recharts 對單條堆疊條 overkill),但**升級**:

- bar 高度 14px → **40px**
- 每段內若寬度 ≥ 8% → 顯示 % 數字(白色 11px,居中)
- **`終止` 段**用 45° 紅斜紋 pattern(`background-image: repeating-linear-gradient(45deg, var(--red) 0 4px, transparent 4px 6px)`),保留紅底為主色
- **hover tooltip**:任一段 mouseover 顯示黑底白字氣泡 `stage 名稱 · count · % · ↑ delta`,position 用 `onMouseEnter` 算座標 + portal
- **完工 baseline marker**:在「完」段右側加一根 2px 白色細直線 + 上方 11px 小字 `本日完工 baseline`
- 段下方標籤列保持現狀(stage 名 + count + delta arrow + drill-down)

### Empty state 不變

灰底 + `目前無 WIP` 文字(沒有 stage segment 可 hover)。

```
┌─ WIP pipeline ────────────────────────── 共 31 件 ─┐
│                                                     │
│ ┃▓▓▓▓▓▓│░░░│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│░░░░░░░░░│⫝⫝│  │
│  16%    10%        39%(進行)         26%(待傳) 10%(完)│
│                                                     │
│  待排程5↑1  排程3→  進行12↓2  待傳8↑3  完3↑1  終止0│
└─────────────────────────────────────────────────────┘
```

## Section 4 · Lab Leaderboard 4 small multiples

只 general_supervisor 看的 Bottom Col 3 — 從 5 列文字 table 改成 4 個 small multiples horizontal bar chart 並排。

### 4 個 sub-chart

每個 sub-chart 200px 高、grid `repeat(4, 1fr)` gap 12,Recharts `<BarChart layout="vertical">`:

| Sub-chart | metric | bar fill | 排序 |
|---|---|---|---|
| 完工 | `completed_today` | `#3fb950` 綠 | desc(產出最多在頂) |
| 待傳 | `awaiting_handoff` | `var(--orange)` | desc(默認) |
| 告警 | `open_high_critical_issues` | `var(--red)` | **asc**(告警最少在頂) |
| util% | `avg_utilization_pct` | `var(--blue)` | desc |

### Bar 細節

- bar height 自動填滿 sub-chart(5 labs)
- bar 旁顯示數字:11px monospace,util 帶 `%`
- bar 內 normalize 到該 sub-chart 的最大值 → 用該 sub-chart 寬度的 100% 表達 leader 位置
- bar 右端到 sub-chart 右邊界的空白填淺灰底(`var(--s2)` opacity 0.3)
- 點 bar → drill `/orders?lab=<lab_name>`(保持 spec 原 behavior)

### Empty state

5 個 lab 都 0 → mini chart 顯示 `—` 灰字置中。

```
┌─ Lab Leaderboard ────────────────────────────────────┐
│ 完工(綠)      待傳(橙)      告警(紅)      util%(藍) │
│ LabA ████ 9   LabC ████ 3   LabE ███ 3   LabA ████ 78%│
│ LabD ███  7   LabA ██   2   LabC ██  2   LabE ████ 81%│
│ LabC ██   5   LabB █    1   LabA █   1   LabC ███  72%│
│ LabB █    4   LabD █    1   LabB     0   LabD ██   65%│
│ LabE      2   LabE ██   2   LabD     0   LabB █    58%│
└──────────────────────────────────────────────────────┘
```

## Section 5 · 24h Throughput chart (lab_supervisor)

只 lab_supervisor 看,**取代 Recent Completions** 那一欄。

### LineChart 細節

- Recharts `<LineChart data={throughput_24h}>` 200px 高,寬填滿 Bottom Col 3
- x-axis:24 個 hourly bucket(now-24h ~ now),label 每 **1 hr** 顯示一個(`HH:00`)、10px monospace,可能需要 `angle={-45}` 避免擠
- y-axis:auto-scale 整數,從 0 起
- 兩條 `<Line>`:
  - **完工**:`stroke="var(--blue)"` 2px **實線**,`dot={false}`,`activeDot={{ r: 3 }}`
  - **回傳**:`stroke="#3fb950"` 2px **虛線**(`strokeDasharray="4 3"`),同上
- `<Tooltip>`:hover 顯示 `HH:00 · 完工 X · 回傳 Y` 黑底白字
- `<CartesianGrid strokeDasharray="2 4" opacity={0.15} />` 淡網格
- 右上角小字 `完工 22 · 回傳 14`(本日 24h 累計)
- 點圖不 drill — chart 表達 aggregate

### Empty state

24h 都 0 → chart 區塊變淺灰底,中央 `var(--text3)` 字「近 24h 無產出」

## Section 6 · Backend 時序資料 + Recharts 安裝

### Backend schema 改動

```python
# backend/app/modules/dashboard/schemas.py

class KpiCard(BaseModel):
    value: int
    delta_24h: int
    threshold_color: ThresholdColor = "neutral"
    sparkline_24h: list[int] | None = None  # 新增,長度固定 24 或 None

class MachineHeatmap(BaseModel):
    by_lab: dict[str, list[MachineGrid]]
    avg_utilization_pct: int
    in_use_count: int
    total_count: int
    per_lab_util_pct: dict[str, int]  # 新增,lab_name → 0-100

class ThroughputPoint(BaseModel):  # 新增
    hour_offset: int  # 0..23,0 = (now-24h) 的小時,23 = 最近完整小時
    completed: int
    returned: int

class DashboardSnapshot(BaseModel):
    # ...原欄位
    throughput_24h: list[ThroughputPoint] | None  # 新增 lab_supervisor 才有
    recent_completions: list[CompletionRow] | None  # ❌ 移除
```

### Backend repository 加方法

```python
async def hourly_buckets_new_orders(self, lab_codes: list[str] | None) -> list[int]:
    """Return 24 hourly counts (now-24h .. now). Buckets without rows = 0."""
async def hourly_buckets_completed(self, lab_names: list[str] | None) -> list[int]:
async def hourly_buckets_returned(self, lab_names: list[str] | None) -> list[int]:
async def throughput_24h(self, lab_names: list[str] | None) -> list[tuple[int, int, int]]:
    """Return 24 (hour_offset, completed_count, returned_count) tuples."""
async def per_lab_util(self) -> dict[str, int]:
    """For machine heatmap mini bar: lab_name → util_pct (0..100)."""
```

每個查詢用 `date_trunc('hour', col) WHERE col >= now()-INTERVAL '24h' GROUP BY 1`,Python 端把缺失桶補 0 → 固定 24 個元素。

### Backend service 改動

`compute_snapshot` 多 fire 3 個 hourly queries + 1 throughput + 1 per_lab_util,放進 `asyncio.gather`。把結果塞進對應 KpiCard.sparkline_24h、MachineHeatmap.per_lab_util_pct、Snapshot.throughput_24h。

`recent_completions` 對應的 query / build / fixture 全部刪掉(被 throughput_24h 取代)。

### Frontend 改動

```
frontend/app/_dashboard/
    KpiBar.tsx          # 改:在 tile 內加 background <LineChart>
    MachineHeatmap.tsx  # 改:header 加 <RadialBarChart>,row 末端加 mini util bar
    WipPipeline.tsx     # 改:加高 + tooltip + baseline marker(inline,不引 Recharts)
    LabLeaderboard.tsx  # 改:5 列文字 → 4 個 small multiples <BarChart>
    ThroughputChart.tsx # 新增:雙線 LineChart
    CompletionsList.tsx # ❌ 刪除
    page.tsx            # 改:lab_supervisor → ThroughputChart,刪掉 CompletionsList import
```

對應 type 變動(`frontend/src/types/dashboard.ts`):
- `KpiCardData` 加 `sparkline_24h: number[] | null`
- `MachineHeatmap` 加 `per_lab_util_pct: Record<string, number>`
- 新 type `ThroughputPoint`
- `DashboardSnapshot` 加 `throughput_24h: ThroughputPoint[] | null`,移除 `recent_completions`
- `CompletionRow` 移除

### Recharts 安裝

```bash
cd frontend && npm install recharts
```

確認跟 Next.js 16 + React 19 相容(2025+ 版本支援)。

### 視覺 tokens 補充

| 元素 | rule |
|---|---|
| Chart background | 透明(panel 已有 `var(--s1)`) |
| Line stroke | 1.5px (KPI sparkline),2px (throughput) |
| Bar fill | metric color(見 Section 4) |
| Tooltip | 黑底 `#0a0a0a`,白字 11px,4px radius,8px padding |
| Grid | `strokeDasharray="2 4"`, opacity 0.15 |
| Axis tick | 10px monospace `var(--text3)` |
| Legend | 11px,top-right,間距 12px |

### Testing

- **Backend pytest**:加 `test_hourly_buckets_new_orders` / `test_hourly_buckets_completed` / `test_hourly_buckets_returned`(各驗證固定 24 元素 + 補零)、`test_throughput_24h`(驗證 lab_sup 拿到 24 點、general_sup 拿到 None)、`test_per_lab_util`(各 lab 0..100)
- **Frontend vitest**:`KpiBar.test.tsx` 加「sparkline_24h null 時不 render LineChart」、`MachineHeatmap.test.tsx` 加「RadialGauge 顏色 threshold」+「per_lab mini util bar 寬度比例」、`LabLeaderboard.test.tsx` 改成 4 個 sub-chart render + 排序方向驗證、新增 `ThroughputChart.test.tsx`、`CompletionsList.test.tsx` ❌ 刪除
- **Playwright**:`tests/e2e/tests/dashboard.spec.ts` 改 — lab_supervisor 那個 case 把 `data-testid="completions-list"` 改成 `data-testid="throughput-chart"`,general_sup 那個保持 `lab-leaderboard`

## 後續步驟

1. 隊友 review 此 design spec
2. Approve 後進 writing-plans skill 寫實作計畫(預計 6-8 個 task)
3. 實作分階段:backend schema + repo + service + tests → recharts install → 5 個 FE 元件改動 → page.tsx + 刪 CompletionsList → 改 Playwright spec
