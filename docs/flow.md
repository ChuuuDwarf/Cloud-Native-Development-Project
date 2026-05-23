## 委託單完整狀態流程

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

## WIP 狀態機

```
已建立 → 待派工 → 排程中 → 待上機 → 執行中 → 已下機 → 待確認 → 已完成
                                                                ↓（異常）
                                                              已終止
```

---

# 狀態流程對應 API

本檔不定義新的 API，只負責說明狀態如何由其他 md 的 API 推進。

## 委託單狀態與 API 對應

| 狀態變化 | 使用 API | 所屬 md |
|---|---|---|
| 草稿 → 待簽核 | `POST /api/orders/:id/actions`，action=`submit` | `order_management.md` |
| 待簽核 → 已核准 / 退回補件 / 已拒絕 | `POST /api/orders/:id/actions`，action=`approve` / `return` / `reject` | `order_management.md` |
| 已核准 → 待送樣 | `POST /api/orders/:id/actions`，action=`approve` | `order_management.md` |
| 待送樣 → 已收樣 | `POST /api/samples/:id/actions`，action=`receive`，並同步 `POST /api/orders/:id/actions` | `sample_management.md`、`order_management.md` |
| 已收樣 → 已分貨 | `POST /api/samples/:id/actions`，action=`split` | `sample_management.md` |
| 已分貨 → 排程中 | `POST /api/wips/:id/actions`，action=`send_to_schedule`，搭配 `POST /api/schedules/suggest` | `sample_management.md`、`schedule.md` |
| 排程中 → 實驗中 | `POST /api/dispatches/:id/actions`，action=`start`，搭配 `POST /api/experiment-runs/:id/actions` | `schedule.md`、`experiment_execute.md` |
| 實驗中 → 待結果確認 | `POST /api/experiment-runs/:id/actions`，action=`complete` | `experiment_execute.md` |
| 待結果確認 → 已完成 | `POST /api/experiment-runs/:id/validate-data` | `experiment_execute.md` |
| 已完成 → 待報告回傳 | `POST /api/reports/:id/actions`，action=`submit_review` / `approve` / `publish` | `experiment_execute.md` |
| 待報告回傳 → 待取件 | `POST /api/reports/:id/actions`，action=`return_to_user`，並同步 `POST /api/orders/:id/actions` | `experiment_execute.md`、`order_management.md` |
| 待取件 → 已結案 | `GET /api/orders/:id/close-check` 後 `POST /api/orders/:id/actions`，action=`close` | `result_manage.md`、`order_management.md` |

## 異常 / 中止流程

| 情境 | 使用 API | 所屬 md |
|---|---|---|
| 建立異常 | `POST /api/issues`，type=`abnormal` | `warn.md` |
| 建立告警 | `POST /api/issues`，type=`warning` | `warn.md` |
| 申請中止 | `POST /api/issues`，type=`termination_request` | `warn.md` |
| 核准 / 拒絕中止 | `POST /api/issues/:id/actions`，action=`approve` / `reject` | `warn.md` |
| 中止後同步實驗與 WIP | `PATCH /api/experiment-runs/:id`、`POST /api/wips/:id/actions` | `experiment_execute.md`、`sample_management.md` |

## 會使用到其他 md 的 API

| 來源 md | 會使用到的 API | 使用目的 |
|---|---|---|
| `order_management.md` | `POST /api/orders/:id/actions` | 推進委託單主流程 |
| `sample_management.md` | `POST /api/samples/:id/actions`<br>`POST /api/wips/:id/actions` | 推進樣品與 WIP 流程 |
| `schedule.md` | `POST /api/schedules/suggest`<br>`POST /api/dispatches/:id/actions` | 排程與派工流程 |
| `experiment_execute.md` | `POST /api/experiment-runs/:id/actions`<br>`POST /api/experiment-runs/:id/validate-data` | 實驗執行與結果確認流程 |
| `experiment_execute.md` | `POST /api/reports/:id/actions` | 報告審核與回傳流程 |
| `warn.md` | `POST /api/issues`<br>`POST /api/issues/:id/actions` | 異常、告警、中止流程 |
| `result_manage.md` | `GET /api/orders/:id/close-check` | 結案前條件檢查 |
