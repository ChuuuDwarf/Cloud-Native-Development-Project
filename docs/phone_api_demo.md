# 電話通知 Demo 設定（中華電信 TAS）

Sprint 3d 整合中華電信 TAS (Telephony API Service) — 當 issue 建立 或
escalation worker 升級時，系統會打電話通知對應的實驗室人員 / 主管。

本文件涵蓋：
1. CHT TAS 帳號跟 API 的事前準備
2. 本機 / 容器內的 env var 設定
3. 換成自己手機的 demo 流程
4. 觸發條件 + 完整 demo path
5. 已知限制 + production 注意事項

---

## 1. CHT TAS 帳號

帳號由 SA 申請，目前團隊共用一組（細節在私聊不公開）：

| 項目 | 來源 |
|---|---|
| `API-KEY` | CHT 給的 (32 字串) |
| `出帳電話號碼` | CHT 給的固定電話 |
| `服務電話號碼 (serviceNumber)` | 自己 reg 出來 (一個 API key 最多 3 個) |

> ⚠️ **API key 不要 commit 進 git**。`backend/.env` 已在 `.gitignore` 內，
> 只放在你本機。

---

## 2. 取得 serviceNumber（**一次性 setup**）

如果 `.env` 已經有 `CHT_SERVICE_NUMBER` 就跳過這步。

### 看現有已 reg 的號碼
```bash
curl https://tasapi.cht.com.tw/apis/CHTIoT/phone-conn/v1/reg \
  -H "x-api-key: <YOUR_API_KEY>"
```

回傳一個 array，每個 element 有 `serviceNumber` 跟 `SNKey`。

### 沒任何號碼 → reg 一個新的
```bash
curl -X POST https://tasapi.cht.com.tw/apis/CHTIoT/phone-conn/v1/reg \
  -H "x-api-key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"appName":"LIMS","appDesc":"NYCU cloud-native LIMS demo"}'
```

回傳 JSON：
```json
{
  "serviceNumber": "0281920072",
  "SNKey": "...",
  "start": "2026-05-26T..."
}
```

把 `serviceNumber` 抄下來。

---

## 3. 設定 `backend/.env`

打開 `backend/.env`（沒有就 `cp backend/.env.example backend/.env`），加：

```bash
# CHT TAS phone callout (Sprint 3d)
CHT_API_KEY=<上面拿到的 32 字串>
CHT_SERVICE_NUMBER=<上面 reg 出來的號碼>
CHT_BASE_URL=https://tasapi.cht.com.tw/apis/CHTIoT

# Demo 用：所有 seed users 的電話都會被設成這個。
# 沒設 → 不撥電話，但其他通知 (站內) 還是正常。
DEMO_PHONE=09XXXXXXXX
```

把 `09XXXXXXXX` 換成**你自己手機**（demo 時你會接到電話）。

---

## 4. 重新 seed 把 phone 寫進 DB

```bash
make seed
```

驗證：
```bash
PGPASSWORD=lims psql -h localhost -U lims -d lims -c \
  "SELECT email, phone FROM users LIMIT 5;"
```
預期看到每個 user 的 phone 是你剛剛設的 `DEMO_PHONE`。

### 已經 seed 過、不想 re-seed？

直接 SQL 更新：
```bash
PGPASSWORD=lims psql -h localhost -U lims -d lims -c \
  "UPDATE users SET phone = '09XXXXXXXX';"
```

> 想分人不同 phone：
> ```sql
> UPDATE users SET phone = '09XXXXXXX1' WHERE email = 'engineer@example.com';
> UPDATE users SET phone = '09XXXXXXX2' WHERE email = 'supervisor@example.com';
> ```

---

## 5. 啟動服務 (3 個 terminal)

```bash
make dev-backend          # uvicorn :8000
make worker               # Celery worker — handle phone callout task
make beat                 # Celery beat — periodic escalation scan
```

⚠️ **worker 必須跑** — 沒 worker，phone callout 任務會卡在 Redis queue，
不會真的撥電話。

---

## 6. 觸發電話 demo

### Option A: 從前端建 issue
1. 瀏覽器 `http://localhost:3000/login`
2. 登入 `engineer@example.com` / `Engin1234`
3. 點 sidebar 「異常與告警」→ 目前無新增 form (Sprint 3a defer)
4. ⚠️ 所以走 Option B

### Option B: ⭐ Swagger UI 直接 POST
1. 瀏覽器另一頁 `http://localhost:8000/api-docs`
2. 找 `POST /api/issues` → Try it out
3. 貼 body（`labId` 用任一存在的 lab UUID）：

```json
{
  "type": "warning",
  "targetType": "machine",
  "targetId": "CMP-001",
  "labId": "<lab uuid>",
  "title": "CMP 機台異常 - 電話通知測試",
  "description": "Sprint 3d 電話 callout 測試",
  "severity": "high"
}
```

> 拿 lab UUID：`PGPASSWORD=lims psql -h localhost -U lims -d lims -c "SELECT id, code FROM labs;"`

4. Execute → **201 Created**

### 預期看到
- **Backend log**: `phone callout enqueued for source=... phones=1`
- **Worker log**: `Received task app.workers.phone_sender.send_callout[...]`
- **Worker log**: `cht callout queued: groupId=...`
- 📞 **手機響起來**，CHT 來電顯示 0281920072
  - Welcome: 「[新異常] CMP 機台異常 - 電話通知測試」
  - Body: 「Sprint 3d 電話 callout 測試」 (repeat 2 次)
  - Bye: 「謝謝」

### 看 Escalation 升級 (10 秒後)
- 不要 mark notification as read
- 10 秒後 + 下次 Beat tick (每分鐘) → escalation 升 level 1
- 📞 你手機**再響一次**，這次 welcome 是「[升級 Lv1] ...」（這是 supervisor 收到的）

---

## 7. Trouble shooting

| 症狀 | 原因 | 解 |
|---|---|---|
| Backend log 沒 `enqueued` | env var 沒讀到 | 確認 `backend/.env` 有 CHT_* 且 backend 重啟 |
| Worker log 沒 `Received task` | Worker 不知道 phone_sender task | Ctrl-C worker 重起 (新 task 要重 load registry) |
| Worker log `KeyError: send_callout` | 同上 | 同上 |
| Worker log 有 `Received` 但 `CHTTASError` | API key 錯 / serviceNumber 沒 reg / phone 格式錯 | 看 error message |
| 撥出 status=ok 但手機沒響 | CHT 那邊 callout 沒派到電信網路 / 手機關機 / 收訊差 | 等 1-2 分鐘，或換手機 |
| 撥出去打到別人 | `DEMO_PHONE` 沒改、忘了 re-seed | re-seed 或 SQL update |

---

## 8. Production 注意事項 (現況 vs. 真正上線)

| 項目 | 現況 (Sprint 3d) | 真正 production 該怎麼做 |
|---|---|---|
| Service number reg | 手動 curl 一次抄到 .env | 啟動時 auto-reg + persist |
| 確認接聽 / DTMF 按鍵 | **不知道** (只知道派送成功) | 接 MQTT broker，收 `calloutResult` topic |
| 每個 user 自己的 phone | 全部用 `DEMO_PHONE` 共用 | 加 `/account` 頁讓 user 自己編 |
| Rate limiting | 無 | per-user / per-issue 速率限制 |
| Critical 才打 | 全部 severity 都打 (per Q3 demo policy) | system_settings.alertRules 設定 |

---

## 9. 完整檔案 ref

- `backend/app/services/cht_tas.py` — CHT TAS HTTP client
- `backend/app/workers/phone_sender.py` — Celery task
- `backend/app/services/notifications.py` — `_dispatch_phone_callout` hook
- `backend/app/services/issues.py` — level-0 fan-out includes PHONE
- `backend/app/workers/escalation.py` — escalation fan-out includes PHONE
- `backend/scripts/seed_dev.py` — seed `User.phone` from `DEMO_PHONE` env
- `backend/.env.example` — env var template
