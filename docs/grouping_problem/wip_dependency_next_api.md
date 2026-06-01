# WIP Dependency Next Experiment API

## API

隊友準備建立下一筆 WIP 時，呼叫：

```http
POST /api/wips/dependency/next
Content-Type: application/json
```

```json
{
  "sampleId": "11111111-1111-1111-1111-111111111111"
}
```

`sampleId` 是 `samples.id`，不是 `samples.sample_no`。

成功 claim 到下一個實驗時會立刻把對應的 `order_items.dependency_check`
寫成 `true`，避免下一次呼叫重複拿到同一筆。

```json
{
  "success": true,
  "data": {
    "orderItemId": 123,
    "orderNo": "ORD-2026-0001",
    "sampleId": "11111111-1111-1111-1111-111111111111",
    "sampleNo": "SMP-2026-0001",
    "labId": "aaaaaaaa-0000-0000-0000-000000000001",
    "labName": "材料分析實驗室",
    "experimentId": "capability-id",
    "experimentName": "SEM 觀察",
    "targetGroup": "G1",
    "target": 1,
    "check": true,
    "reason": "lowest_machine_utilization"
  }
}
```

如果該 sample 已經沒有未 claim 的相依項目：

```json
{
  "success": true,
  "data": null,
  "message": "No pending dependency item"
}
```

## Dependency Rules

API 會先用 `samples.id` 查出 `samples.order_no` 與 `samples.sample_no`，
再用下面關係找到委託單明細：

```text
orders.order_no = samples.order_no
order_items.sample_id = samples.sample_no
```

判斷規則：

- `target_group` 是相依鏈邊界，不同 group 互不等待。
- 同一個 `target_group` 內，`target` 數字越小越先 claim。
- 每個 group 只會拿目前最小且 `dependency_check = false` 的一筆當候選。
- claim 成功後會更新該筆 `dependency_check = true`。

範例：

```text
G1 target 1 -> G1 target 2
G2 target 1
G3 target 1 -> G3 target 2
```

第一次可被選的候選是 `G1 target 1`、`G2 target 1`、`G3 target 1`。
當 `G1 target 1` 被 claim 後，下次 `G1 target 2` 才會進入候選。

## Tie-Break Algorithm

當多個 group 同時有候選時，API 會使用機台利用率做排序：

1. 依候選的 `labId` 找到 lab code/name。
2. 查 `machines` 中同 lab 的機台。
3. 只看 `supported_items` 包含該 `experimentName` 的機台。
4. 用候選項支援機台的最低 `utilization` 當分數。
5. 分數越低越優先。
6. 沒有可用機台資料時，該候選排在有資料者後面。
7. 最後用 `target ASC, created_at ASC, id ASC` 固定排序，避免結果飄動。

## Manual Test

啟動環境：

```bash
make infra
cd backend
source .venv/bin/activate
cd ..
make migrate
make seed
make dev-backend
```

用 Swagger 測：

```text
http://localhost:8000/api-docs
```

或用 curl：

```bash
curl -X POST http://localhost:8000/api/wips/dependency/next \
  -H "Content-Type: application/json" \
  -d '{"sampleId":"11111111-1111-1111-1111-111111111111"}'
```

自動測試：

```bash
cd backend
source .venv/bin/activate
pytest tests/test_wip_service.py tests/test_route_integration.py
```
