# LIMS Frontend

![Version](https://img.shields.io/badge/version-v0.1.0-blue.svg)
![Next.js](https://img.shields.io/badge/Next.js-16.2.4-111827.svg)
![React](https://img.shields.io/badge/React-19.2.4-149eca.svg)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178c6.svg)
![Tests](https://img.shields.io/badge/tests-Vitest%20%2B%20Testing%20Library-7c3aed.svg)

LIMS 前端是以 Next.js App Router 建立的角色導向操作介面，負責登入、側邊欄權限控制、委託單、簽核、收樣、WIP、派工、實驗執行、報告、結案、通知與主管儀表板等頁面。後端 API 由 `NEXT_PUBLIC_API_URL` 指定，預設連到 `http://localhost:8000/api`。

- Repo README: [../README.md](../README.md)
- Backend README: [../backend/README.md](../backend/README.md)

## Tech Stack

| 類別          | 技術                                   |
| ------------- | -------------------------------------- |
| Framework     | Next.js 16 App Router                  |
| UI runtime    | React 19                               |
| Language      | TypeScript                             |
| Data fetching | TanStack Query, axios                  |
| Charts        | Recharts                               |
| Tests         | Vitest, Testing Library, jsdom         |
| Quality       | ESLint, TypeScript typecheck, Prettier |

## 快速啟動

```bash
cd frontend
npm ci
npm run dev
```

開啟 <http://localhost:3000>。若後端也在本機啟動，預設會呼叫 <http://localhost:8000/api>。

可選環境變數：

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Docker Compose 由根目錄控制：

```bash
cd ..
make up
```

## Scripts

| 指令                    | 用途                    |
| ----------------------- | ----------------------- |
| `npm run dev`           | 啟動 Next.js dev server |
| `npm run build`         | 建置 production bundle  |
| `npm run start`         | 啟動 production server  |
| `npm run lint`          | ESLint 檢查             |
| `npm run typecheck`     | TypeScript 型別檢查     |
| `npm run test`          | 執行 Vitest             |
| `npm run test:coverage` | 執行 Vitest coverage    |
| `npm run format`        | Prettier 格式化         |
| `npm run format:check`  | Prettier 檢查           |

根目錄 Makefile 也提供：

```bash
make dev-frontend
make lint-frontend
make test-frontend
```

## 路由與功能

| Route               | 功能                                          |
| ------------------- | --------------------------------------------- |
| `/`                 | 主管儀表板、KPI、WIP pipeline、告警與即時資料 |
| `/login`            | 登入頁                                        |
| `/account`          | 使用者與帳號管理                              |
| `/orders`           | 委託單建立、列表、明細與送出                  |
| `/orders/templates` | 委託單範本                                    |
| `/approve`          | 主管簽核、退回、拒絕與特批                    |
| `/sample`           | 收樣與樣品資訊                                |
| `/wip`              | WIP 建立、狀態與管理                          |
| `/transfer`         | 樣品轉送與交接                                |
| `/dispatch`         | 派工、機台/Recipe 指派                        |
| `/machine`          | 機台管理與狀態模擬                            |
| `/recipe`           | Recipe 管理                                   |
| `/execution`        | 實驗執行與進度紀錄                            |
| `/report`           | 報告建立、編輯、下載與狀態                    |
| `/closure`          | 取件結案與結案條件檢查                        |
| `/issues`           | 異常事件                                      |
| `/notifications`    | 通知中心                                      |
| `/others`           | 暫存、入庫或其他流程輔助頁                    |

## 專案結構

```text
frontend/
├── app/                         # Next.js App Router pages
│   ├── layout.tsx               # 根 layout，掛載 Providers/AuthGate
│   ├── page.tsx                 # Dashboard
│   ├── globals.css              # CSS variables 與全域樣式
│   ├── login/
│   ├── account/
│   ├── orders/
│   ├── approve/
│   ├── sample/
│   ├── wip/
│   ├── transfer/
│   ├── dispatch/
│   ├── machine/
│   ├── recipe/
│   ├── execution/
│   ├── report/
│   ├── closure/
│   ├── issues/
│   ├── notifications/
│   └── others/
├── components/                  # 全域共用元件
│   ├── AuthGate.tsx
│   ├── LoginForm.tsx
│   ├── Providers.tsx
│   ├── Sidebar.tsx
│   └── ui/
├── src/
│   ├── api/                     # axios/http client 與部分 API wrapper
│   ├── constants/               # enum、狀態 label、樣式常數
│   ├── contexts/                # AuthContext
│   ├── hooks/                   # 共用 hooks
│   ├── lib/                     # queryClient、錯誤處理、顯示名稱工具
│   ├── services/                # 模組化 typed API clients
│   └── types/                   # 前端共用型別
├── tests/                       # 前端測試
├── public/                      # 靜態資源
├── package.json
├── vitest.config.ts
├── tsconfig.json
└── next.config.ts
```

## API 與資料流

- `src/api/httpClient.ts` 建立 axios instance，預設使用 `NEXT_PUBLIC_API_URL`。
- `src/services/*-api.ts` 放各模組 typed API client，例如 auth、dashboard、dispatches、machines、reports、recipes、user。
- `src/types/` 放 API response 與 domain types。
- `src/contexts/AuthContext.tsx` 管理登入狀態、目前使用者、權限判斷、login/logout。
- `components/AuthGate.tsx` 負責未登入攔截與登入後 layout。
- `components/Sidebar.tsx` 依使用者權限顯示可用導覽項目。

## UI 與樣式慣例

- 全域色票與基礎樣式集中在 `app/globals.css`。
- 共用小元件放在 `components/ui/`，例如 `Btn`、`Chip`、`DataState`、`KpiCard`、`Modal`、`Panel`。
- 頁面邏輯優先拆到該頁 `hooks/`、`lib/`、`utils/` 或 `components/`，避免大型 page 元件難以測試。
- 前端 enum 顯示文字與 API enum 要保持一致；必要時參考後端 `backend/scripts/sync_enums.py`。

## 開發檢查

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

端到端測試在根目錄 [../tests/e2e](../tests/e2e)，需啟動完整 stack 後執行。
