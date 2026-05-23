# 實驗室資訊管理系統（LIMS）功能規格 — 依功能細分角色

---

## 系統角色定義 (role)

| 角色 | 簡稱 | 說明 |
|------|------|------|
| 廠區使用者 | 使用者 | 提出送測需求的廠區端人員 |
| 實驗室人員 | 實驗員 | 執行收樣、派工、實驗的操作人員 |
| 實驗室主管 | 主管 | 負責審核、監控與決策的管理者 |
| 系統管理者 | 管理者 | 維護系統設定與帳號的後台人員 |

---

## 一、使用者與帳號管理 (role)

**模組目標：** 管理系統帳號、角色指派、部門設定與實驗室歸屬。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 帳號建立 / 停用 | — | — | — | ✅ |
| 角色指派 | — | — | — | ✅ |
| 部門 / 廠區設定 | — | — | — | ✅ |
| 實驗室歸屬設定 | — | — | — | ✅ |
| 權限控管 | — | — | — | ✅ |

---

## 二、委託單管理 (order_management)

**模組目標：** 廠區使用者建立、送出與追蹤送測申請，主管進行簽核決策。

### 2.1 建立與送出

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立委託單 | ✅ | — | — | — |
| 儲存 / 編輯草稿 | ✅ | — | — | — |
| 編輯被退回單據 | ✅ | — | — | — |
| 送出委託單（送簽核） | ✅ | — | — | — |
| 取消委託單 | ✅ | — | — | — |
| 查詢委託單狀態 | ✅ | 查看（己所屬） | ✅ | ✅ |
| 查看退回 / 拒絕原因 | ✅ | — | — | — |

> **委託單欄位規則：**
> - 一張委託單可含多筆實驗明細，每筆對應一個實驗室
> - 必填欄位：委託單編號、申請人、部門/廠區、申請日期、樣品編號、實驗室、實驗項目
> - 可設定每單最大實驗項目數

### 2.2 簽核

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 查看待簽核單據 | — | — | ✅ | — |
| 核准委託單 | — | — | ✅ | — |
| 退回補件（填原因） | — | — | ✅ | — |
| 拒絕委託單（填原因） | — | — | ✅ | — |
| 特批超額送測 | — | — | ✅ | — |

> **簽核規則：**
> - 不同實驗室可由不同主管簽核
> - 建議採主單 + 子單簽核架構
> - 拒絕與退回必填原因

### 2.3 送測配額管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 送單時即時配額檢核 | 受限 | — | — | — |
| 設定個人 / 部門送測上限 | — | — | — | ✅ |
| 設定特急單上限 | — | — | — | ✅ |
| 超額申請特批流程 | 申請 | — | 審核 | 設定規則 |

---

## 三、收樣與樣品管理(sample_management)

**模組目標：** 追蹤樣品從送達、分貨、流轉到入庫取件的完整生命週期。

### 3.1 收樣

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 確認送樣（廠區端） | ✅ | — | — | — |
| 查看待收樣清單 | — | ✅ | — | — |
| 確認收樣 / 登記時間與人員 | — | ✅ | — | — |
| 記錄樣品狀態 | — | ✅ | — | — |
| 產生收樣紀錄 | — | ✅（系統自動） | — | — |

### 3.2 分貨與 WIP 管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 分貨（拆分樣品） | — | ✅ | — | — |
| 建立 WIP / WIP 編碼 | — | ✅ | — | — |
| WIP 狀態管理 | — | ✅ | 監看 | — |
| WIP 與實驗明細關聯 | — | ✅ | — | — |
| 設定 WIP 編碼規則 | — | — | — | ✅ |

### 3.3 樣品交接與流轉

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立交接單 | — | ✅ | — | — |
| 登記來源 / 目的實驗室 | — | ✅ | — | — |
| 登記交接人 / 簽收人 | — | ✅ | — | — |
| 查詢樣品目前位置 | ✅（己單） | ✅ | ✅ | — |
| 查看交接紀錄 | — | ✅ | ✅ | — |

### 3.4 倉儲與取件管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 樣品入庫 | — | ✅ | — | — |
| 樣品出庫 | — | ✅ | — | — |
| 儲位管理 | — | ✅ | — | — |
| 查看待取件清單 | ✅ | ✅ | — | — |
| 確認取件（廠區端） | ✅ | — | — | — |
| 逾期未領通知觸發 | — | 系統自動 | 接收通知 | 設定規則 |

---

## 四、機台與 Recipe 管理 (machine_recipe)

**模組目標：** 管理機台資料、狀態、Recipe 版本，為派工提供基礎資源。

### 4.1 機台管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 機台新增 / 編輯 / 停用 | — | ✅ | — | ✅ |
| 機台狀態設定 | — | ✅ | — | — |
| 支援實驗項目設定 | — | ✅ | — | — |
| 保養 / 維修狀態管理 | — | ✅ | — | — |
| 查看機台使用率 / 稼動率 | — | ✅ | ✅ | — |
| 設定假資料顯示規則 | — | — | — | ✅ |

> **機台狀態：** 閒置 / 使用中 / 保養中 / 故障中 / 停用

### 4.2 Recipe 與實驗方法管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立 Recipe | — | ✅ | — | — |
| 維護 Recipe 版本 | — | ✅ | — | — |
| 建立實驗方法 | — | ✅ | — | — |
| 設定機台對應 Recipe | — | ✅ | — | — |
| 管理參數範本 | — | ✅ | — | — |
| 查看修改歷程 | — | ✅ | ✅ | — |

---

## 五、派工與排程管理 (schedule)

**模組目標：** 依 WIP 狀態、機台可用性、優先級與交期，產生排程並執行派工。

### 5.1 排程建議與最佳化

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 查看待派工 / 待排程清單 | — | ✅ | ✅ | — |
| 自動 / 半自動排程建議 | — | 參考 | 參考（選） | — |
| 查看預估開始 / 完成時間 | — | ✅ | ✅ | — |
| 排程衝突檢查 | — | 系統自動 | — | — |
| 設定排程策略參數 | — | — | 調整接單規則 | ✅ |

> **排程策略：** FIFO / Priority First / Earliest Due Date / Least Setup Change / Hybrid

### 5.2 派工執行

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 指派機台 / Recipe / 時段 | — | ✅ | — | — |
| 確認 / 手動調整派工 | — | ✅ | — | — |
| 手動覆寫系統建議 | — | ✅ | — | — |
| 建立派工紀錄 | — | ✅（系統自動） | — | — |

### 5.3 動態重排

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 機台故障重排 | — | ✅ | — | — |
| 特急單插單重排 | — | ✅ | 決策 | — |
| 前站延誤 / 樣品未到重排 | — | ✅ | — | — |
| 人員不足重排 | — | ✅ | 協調 | — |

---

## 六、實驗執行與結果管理 (experiment_execute)

**模組目標：** 記錄實驗上下機、進度、數據收集與結果，為報告提供資料來源。

### 6.1 上下機履歷

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 上機登記（操作人 / 時間 / 機台 / Recipe） | — | ✅ | — | — |
| 下機登記 | — | ✅ | — | — |
| 查詢樣品完整機台履歷 | — | ✅ | ✅ | — |

> **規則：** 每次上下機紀錄不可刪除

### 6.2 實驗執行

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 開始 / 更新實驗進度 | — | ✅ | — | — |
| 上傳結果 / 填寫備註 | — | ✅ | — | — |
| 關聯原始數據 | — | ✅ | — | — |
| 標記實驗完成 | — | ✅ | — | — |

### 6.3 機台自動化數據蒐集

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 接收機台開始 / 完成訊號 | — | 系統自動 | — | — |
| 自動抓取實驗數據並寫入 DB | — | 系統自動 | — | — |
| 驗證數據完整性 | — | ✅ | — | — |

> **規則：** 機台回報完成不直接結案，需進入「待結果確認」

### 6.4 異常與中止管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立異常事件 | — | ✅ | — | — |
| 提出中止申請 | — | ✅ | — | — |
| 審核 / 決定是否終止實驗 | — | — | ✅ | — |
| 記錄中止原因與處理結果 | — | ✅ | ✅ | — |

> **規則：** 實驗室人員不可直接終止實驗，須由主管審核決定

---

## 七、實驗報告管理 (experiment_execute)

**模組目標：** 將實驗結果整理成正式報告，經主管確認後回傳廠區使用者。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 建立實驗報告草稿 | — | ✅ | — | — |
| 從實驗結果自動帶入內容 | — | 系統自動 | — | — |
| 編輯報告摘要 / 結論 / 附件 | — | ✅ | — | — |
| 上傳報告檔案 | — | ✅ | — | — |
| 報告版本管理 | — | ✅ | — | — |
| 提交報告審核 | — | ✅ | — | — |
| 審核 / 確認報告 | — | — | ✅ | — |
| 發布報告（回傳使用者） | — | ✅ | ✅（確認後） | — |
| 查閱 / 下載實驗報告 | ✅ | ✅ | ✅ | — |
| 設定報告發布規則 | — | — | — | ✅ |

> **報告狀態流程：** 草稿 → 待審核 → 已確認 → 已發布 → 已回傳 → 已改版（如需）

---

## 八、結單管理 (result_manage)

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

## 九、告警與通知管理 (warn)

**模組目標：** 監控機台異常並依 SLA 升級通知，確保問題即時處理。

### 9.1 告警管理

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 接收 / 查看告警清單 | — | ✅ | ✅ | — |
| 指派告警處理人 | — | — | ✅ | — |
| 追蹤告警回應時間 | — | — | ✅ | — |
| 關閉告警 | — | ✅（處理完） | ✅ | — |
| 設定告警升級規則與時間 | — | — | — | ✅ |

> **升級機制範例：**
> - 0 分鐘：通知責任人員
> - 10 分鐘未處理：通知資深工程師
> - 20 分鐘未處理：通知實驗室主管
> - 30 分鐘未處理：通知上級主管

### 9.2 通知管理

| 通知情境 | 廠區使用者 | 實驗室人員 | 實驗室主管 |
|----------|-----------|-----------|-----------|
| 送單成功 | ✅ | — | — |
| 退回補件 | ✅ | — | — |
| 拒絕 | ✅ | — | — |
| 核准送樣 | ✅ | ✅ | — |
| 收樣成功 | ✅ | — | — |
| 異常通知 | — | ✅ | ✅ |
| 中止通知 | ✅ | ✅ | ✅ |
| 完成通知 | ✅ | — | — |
| 實驗報告已回傳 | ✅ | — | — |
| 取件通知 | ✅ | — | — |
| 告警升級通知 | — | ✅ | ✅ |

> **通知管道：** Email（必要）、系統內通知（必要）、可擴充簡訊 / Teams

---

## 十、監控儀表板 (dashboard)

**模組目標：** 提供主管即時掌握實驗室整體營運狀況。

| 功能項目 | 廠區使用者 | 實驗室人員 | 實驗室主管 | 系統管理者 |
|----------|-----------|-----------|-----------|-----------|
| 查看待簽核委託單數 | — | — | ✅ | — |
| 查看各實驗室在製量 | — | — | ✅ | — |
| 查看機台使用率 / 稼動率 | — | — | ✅ | — |
| 查看告警未處理數 | — | — | ✅ | — |
| 查看逾期 / 異常案件數 | — | — | ✅ | — |
| 查看報告待確認 / 已回傳數 | — | — | ✅ | — |
| 查看待排程 WIP 數 | — | — | ✅ | — |
| 查看各機台未來負載 | — | — | ✅ | — |
| 插單影響分析 | — | — | ✅（選） | — |

---

## 十一、系統設定 (system_setting)

**模組目標：** 供系統管理者調整系統全域參數與規則。

| 可設定項目 | 系統管理者 |
|-----------|-----------|
| 實驗室數量 / 每室人數 | ✅ |
| 實驗室可執行實驗項目 | ✅ |
| 送測配額規則 | ✅ |
| 委託單 / WIP 編碼規則 | ✅ |
| 通知規則 | ✅ |
| 告警升級時間 | ✅ |
| 自動結單條件 | ✅ |
| 排程策略與最佳化權重參數 | ✅ |
| 假資料開關 / 筆數 / 更新頻率 | ✅ |
| 報告發布規則 | ✅ |

---

## 附錄 A：委託單完整狀態機

```
草稿
  └─► 待簽核
        ├─► 退回補件 ──► (修改後) 待簽核
        ├─► 已拒絕
        ├─► 已取消
        └─► 已核准
              └─► 待送樣
                    └─► 已收樣
                          └─► 已分貨
                                └─► 排程中
                                      └─► 實驗中
                                            ├─► 暫停中
                                            │     └─► 待主管判定
                                            │           ├─► 已終止
                                            │           └─► 實驗中（繼續）
                                            └─► 待結果確認
                                                  └─► 已完成
                                                        └─► 待報告回傳
                                                              └─► 待取件
                                                                    └─► 已結案
```

## 附錄 B：WIP 狀態機

```
已建立 → 待派工 → 排程中 → 待上機 → 執行中 → 已下機 → 待確認 → 已完成
                                                                ↓（異常）
                                                              已終止
```

## 附錄 C：非功能性需求摘要

| 面向 | 要求 |
|------|------|
| 稽核追蹤 | 所有關鍵操作保留 Audit Log（誰、何時、做什麼、修改前後差異） |
| 權限安全 | 角色分權、畫面與 API 權限控管、報告下載權限控管 |
| 使用者規模 | 最多 200 人（8 個實驗室），需支援同時在線 |
| RWD | 需支援桌機主要操作，可擴充平板 / 手機 |
| 整合性 | 可與機台系統、Email、AD/SSO、報表匯出整合 |
| 擴充性 | 可新增實驗室、機台、實驗項目；假資料模式可切換為正式串接 |

---

# 專案 API 覆蓋總整理

## API 所屬文件總表

| 所屬 md | Method | API | 用途 |
|---|---|---|---|
| `role.md` | POST | `/api/auth/login` | 使用者登入 |
| `role.md` | POST | `/api/auth/logout` | 使用者登出 |
| `role.md` | GET | `/api/me` | 取得目前登入者資料、角色與權限 |
| `role.md` | GET | `/api/users` | 查詢使用者列表 |
| `role.md` | POST | `/api/users` | 建立使用者 |
| `role.md` | GET | `/api/users/:id` | 查看單一使用者 |
| `role.md` | PATCH | `/api/users/:id` | 修改使用者資料、角色、部門、實驗室歸屬或啟用狀態 |
| `role.md` | GET | `/api/roles` | 取得角色清單 |
| `role.md` | GET | `/api/permissions` | 取得系統權限清單 |
| `order_management.md` | GET | `/api/orders` | 查詢委託單列表 |
| `order_management.md` | POST | `/api/orders` | 建立委託單草稿 |
| `order_management.md` | GET | `/api/orders/:id` | 查看委託單詳細資料 |
| `order_management.md` | PATCH | `/api/orders/:id` | 編輯草稿或退回補件的委託單 |
| `order_management.md` | DELETE | `/api/orders/:id` | 刪除草稿委託單 |
| `order_management.md` | POST | `/api/orders/:id/actions` | 執行送出、取消、核准、退回、拒絕、確認送樣、待取件、結案等流程動作 |
| `order_management.md` | GET | `/api/orders/:id/history` | 查看委託單流程歷程 |
| `sample_management.md` | GET | `/api/samples` | 查詢樣品列表 |
| `sample_management.md` | GET | `/api/samples/:id` | 查看樣品詳細資料 |
| `sample_management.md` | PATCH | `/api/samples/:id` | 更新樣品基本資料、目前位置、儲位、備註 |
| `sample_management.md` | POST | `/api/samples/:id/actions` | 執行收樣、分貨、交接、入庫、出庫、確認取件等流程動作 |
| `sample_management.md` | GET | `/api/samples/:id/history` | 查看樣品歷程 |
| `sample_management.md` | GET | `/api/wips` | 查詢 WIP 清單 |
| `sample_management.md` | POST | `/api/wips` | 建立 WIP，通常由樣品分貨流程觸發 |
| `sample_management.md` | GET | `/api/wips/:id` | 查看單一 WIP 詳細資料 |
| `sample_management.md` | PATCH | `/api/wips/:id` | 更新 WIP 非流程欄位，例如備註、優先級、負責實驗室 |
| `sample_management.md` | POST | `/api/wips/:id/actions` | 執行 WIP 狀態動作，例如送排程、暫停、恢復、標記完成、終止 |
| `sample_management.md` | GET | `/api/wips/:id/history` | 查看 WIP 歷程 |
| `machine_recipe.md` | GET | `/api/machines` | 查詢機台列表 |
| `machine_recipe.md` | POST | `/api/machines` | 新增機台 |
| `machine_recipe.md` | GET | `/api/machines/:id` | 查看單一機台 |
| `machine_recipe.md` | PATCH | `/api/machines/:id` | 修改機台資料、狀態、支援實驗項目 |
| `machine_recipe.md` | DELETE | `/api/machines/:id` | 停用機台 |
| `machine_recipe.md` | GET | `/api/machines/:id/history` | 查看機台異動歷程 |
| `machine_recipe.md` | GET | `/api/machines/:id/usage` | 查看機台使用率 / 稼動率 |
| `machine_recipe.md` | GET | `/api/experiment-methods` | 查詢實驗方法 |
| `machine_recipe.md` | POST | `/api/experiment-methods` | 建立實驗方法 |
| `machine_recipe.md` | GET | `/api/experiment-methods/:id` | 查看實驗方法 |
| `machine_recipe.md` | PATCH | `/api/experiment-methods/:id` | 修改實驗方法 |
| `machine_recipe.md` | DELETE | `/api/experiment-methods/:id` | 停用實驗方法 |
| `machine_recipe.md` | GET | `/api/experiment-methods/:id/history` | 查看實驗方法修改歷程 |
| `machine_recipe.md` | GET | `/api/recipes` | 查詢 Recipe |
| `machine_recipe.md` | POST | `/api/recipes` | 建立 Recipe |
| `machine_recipe.md` | GET | `/api/recipes/:id` | 查看 Recipe |
| `machine_recipe.md` | PATCH | `/api/recipes/:id` | 修改 Recipe |
| `machine_recipe.md` | DELETE | `/api/recipes/:id` | 停用 Recipe |
| `machine_recipe.md` | GET | `/api/recipes/:id/versions` | 查詢 Recipe 版本 |
| `machine_recipe.md` | POST | `/api/recipes/:id/versions` | 建立 Recipe 新版本 |
| `experiment_execute.md` | GET | `/api/experiment-runs` | 查詢實驗執行紀錄 |
| `experiment_execute.md` | POST | `/api/experiment-runs` | 建立實驗執行紀錄 |
| `experiment_execute.md` | GET | `/api/experiment-runs/:id` | 查看實驗執行紀錄 |
| `experiment_execute.md` | PATCH | `/api/experiment-runs/:id` | 更新實驗進度、備註、結果摘要 |
| `experiment_execute.md` | POST | `/api/experiment-runs/:id/actions` | 執行上機、下機、開始、完成、暫停、恢復等實驗流程動作 |
| `experiment_execute.md` | GET | `/api/experiment-runs/:id/history` | 查看實驗執行歷程 |
| `experiment_execute.md` | GET | `/api/machine-events` | 查詢機台事件 |
| `experiment_execute.md` | POST | `/api/machine-events` | 接收機台開始、完成、錯誤、資料上傳等事件 |
| `experiment_execute.md` | POST | `/api/experiment-runs/:id/raw-data` | 上傳或關聯原始數據 |
| `experiment_execute.md` | POST | `/api/experiment-runs/:id/validate-data` | 驗證實驗數據完整性 |
| `schedule.md` | GET | `/api/schedules` | 查詢排程資料 |
| `schedule.md` | POST | `/api/schedules/suggest` | 產生排程建議 |
| `schedule.md` | POST | `/api/schedules/conflict-check` | 檢查排程衝突 |
| `schedule.md` | POST | `/api/schedules/reschedule` | 依原因動態重排 |
| `schedule.md` | PATCH | `/api/schedules/:id` | 手動調整單一排程 |
| `schedule.md` | GET | `/api/dispatches` | 查詢派工清單 |
| `schedule.md` | POST | `/api/dispatches` | 建立派工 |
| `schedule.md` | GET | `/api/dispatches/:id` | 查看派工詳細資料 |
| `schedule.md` | PATCH | `/api/dispatches/:id` | 修改派工內容 |
| `schedule.md` | POST | `/api/dispatches/:id/actions` | 執行派工確認、開始、暫停、恢復、完成、取消 |
| `experiment_execute.md` | GET | `/api/reports` | 查詢實驗報告 |
| `experiment_execute.md` | POST | `/api/reports` | 建立報告草稿 |
| `experiment_execute.md` | GET | `/api/reports/:id` | 查看報告 |
| `experiment_execute.md` | PATCH | `/api/reports/:id` | 編輯報告摘要、結論、附件 |
| `experiment_execute.md` | POST | `/api/reports/:id/actions` | 提交審核、確認、發布、退回、回傳、建立新版 |
| `experiment_execute.md` | GET | `/api/reports/:id/versions` | 查詢報告版本 |
| `warn.md` | GET | `/api/issues` | 查詢異常 / 告警 / 中止申請列表 |
| `warn.md` | POST | `/api/issues` | 建立異常、告警或中止申請 |
| `warn.md` | GET | `/api/issues/:id` | 查看單一事件詳細資料 |
| `warn.md` | PATCH | `/api/issues/:id` | 更新事件處理資訊 |
| `warn.md` | POST | `/api/issues/:id/actions` | 執行審核、關閉、升級、指派、重開 |
| `warn.md` | GET | `/api/notifications` | 查詢通知列表 |
| `warn.md` | POST | `/api/notifications` | 建立通知，通常由後端流程自動觸發 |
| `warn.md` | PATCH | `/api/notifications/:id` | 更新單筆通知狀態 |
| `warn.md` | POST | `/api/notifications/actions` | 批次已讀或批次刪除通知 |
| `dashboard.md` | GET | `/api/dashboard` | 取得目前登入者 Dashboard 總覽 |
| `dashboard.md` | GET | `/api/dashboard/widgets/:widgetKey` | 取得單一 widget 詳細資料 |
| `dashboard.md` | POST | `/api/dashboard/simulations` | 插單影響分析，不直接修改排程 |
| `system_setting.md` | GET | `/api/master-data` | 取得前端共用下拉選單與狀態資料 |
| `system_setting.md` | GET | `/api/system-settings` | 取得所有系統設定 |
| `system_setting.md` | GET | `/api/system-settings/:key` | 取得單一系統設定 |
| `system_setting.md` | PATCH | `/api/system-settings/:key` | 修改單一系統設定 |
| `system_setting.md` | POST | `/api/system-settings/:key/reset` | 重設單一系統設定為預設值 |
| `system_setting.md` | GET | `/api/system-settings/history` | 查看系統設定異動紀錄 |
| `system_setting.md` | GET | `/api/labs` | 取得實驗室清單 |
| `system_setting.md` | POST | `/api/labs` | 新增實驗室 |
| `system_setting.md` | PATCH | `/api/labs/:id` | 修改實驗室設定 |
| `system_setting.md` | DELETE | `/api/labs/:id` | 停用實驗室 |
| `system_setting.md` | GET | `/api/labs/:id/capabilities` | 取得實驗室可執行實驗項目 |
| `system_setting.md` | PATCH | `/api/labs/:id/capabilities` | 修改實驗室可執行實驗項目 |
| `system_setting.md` | GET | `/api/departments` | 查詢部門 / 廠區清單 |
| `system_setting.md` | POST | `/api/departments` | 新增部門 / 廠區 |
| `system_setting.md` | GET | `/api/departments/:id` | 查看部門 / 廠區 |
| `system_setting.md` | PATCH | `/api/departments/:id` | 修改部門 / 廠區 |
| `system_setting.md` | DELETE | `/api/departments/:id` | 停用部門 / 廠區 |
| `system_setting.md` | GET | `/api/storage-locations` | 查詢儲位清單 |
| `system_setting.md` | POST | `/api/storage-locations` | 新增儲位 |
| `system_setting.md` | PATCH | `/api/storage-locations/:id` | 修改儲位 |
| `system_setting.md` | DELETE | `/api/storage-locations/:id` | 停用儲位 |
| `system_setting.md` | POST | `/api/files` | 上傳原始數據、報告附件或其他檔案 |
| `system_setting.md` | GET | `/api/files/:id` | 下載或預覽檔案 |
| `system_setting.md` | DELETE | `/api/files/:id` | 刪除尚未正式綁定或草稿附件 |
| `system_setting.md` | GET | `/api/audit-logs` | 查詢全域稽核紀錄 |
| `result_manage.md` | GET | `/api/orders/:id/close-check` | 檢查委託單是否符合結案條件 |


## 模組覆蓋確認

| 專案模組 | 對應 md | 覆蓋狀態 |
|---|---|---|
| 使用者與帳號管理 | `role.md` | ✅ 完整覆蓋 |
| 委託單管理 | `order_management.md` | ✅ 完整覆蓋 |
| 收樣與樣品管理 | `sample_management.md` | ✅ 完整覆蓋，已補 WIP API |
| 機台與 Recipe 管理 | `machine_recipe.md` | ✅ 完整覆蓋 |
| 派工與排程管理 | `schedule.md` | ✅ 完整覆蓋 |
| 實驗執行與結果管理 | `experiment_execute.md` | ✅ 完整覆蓋 |
| 實驗報告管理 | `experiment_execute.md` | ✅ 完整覆蓋，報告 API 統一在 `experiment_execute.md` 的 `/api/reports` |
| 結單管理 | `result_manage.md` | ✅ 使用 close-check + orders actions 覆蓋 |
| 告警與通知管理 | `warn.md` | ✅ 完整覆蓋，統一 `/api/issues` |
| 監控儀表板 | `dashboard.md` | ✅ 完整覆蓋 |
| 系統設定 | `system_setting.md` | ✅ 完整覆蓋，含 Master Data、Files、Audit Logs |
| 狀態流程 | `flow.md` | ✅ 以 API 對應狀態機 |

## 已消除的重複 API

| 原本重複 / 雷同設計 | 最終保留 | 說明 |
|---|---|---|
| `/api/auth/me`、`/api/me` | `GET /api/me` | 目前登入者只保留一支 |
| `/api/experiment-reports`、`/api/reports` | `/api/reports` | 報告模組統一命名 |
| `/api/experiment-abnormal-events`、`/api/issues` | `/api/issues` | 異常、告警、中止統一為 Issue |
| `/api/scheduling-policies`、`/api/system-settings/schedulingPolicy` | `/api/system-settings/schedulingPolicy` | 排程策略屬於系統設定 |
| 各種重排細分 API | `POST /api/schedules/reschedule` | 用 `reason` 區分情境 |
| 各種流程狀態 API | `POST .../actions` | 用 action 區分狀態動作 |

## 跨 md 使用規則

- 每支 API 只在一個 md 裡正式定義。
- 其他 md 如果需要使用，只放在「會使用到其他 md 的 API」表格。
- 共用下拉資料由 `system_setting.md` 的 `GET /api/master-data` 提供。
- 共用檔案上傳由 `system_setting.md` 的 Files API 提供。
- 異常、告警、中止都由 `warn.md` 的 Issues API 提供。


## 統一規則

- 目前登入者 API 統一使用 `GET /api/me`，不再使用 `/api/auth/me`。
- 報告 API 統一使用 `/api/reports`，不再使用 `/api/experiment-reports`。
- 異常、告警、中止申請統一使用 `/api/issues`，不再使用 `/api/experiment-abnormal-events`。
- 排程策略統一由 `system_setting.md` 的 `/api/system-settings/schedulingPolicy` 管理，不再另開 `/api/scheduling-policies`。
- 流程狀態變更一律用 `POST .../actions`，一般欄位修改才用 `PATCH`。



## 報告 API 唯一來源

實驗報告 API 統一由 `experiment_execute.md` 定義，避免與其他文件重複維護。
