'use client'

// TODO(integration): 這個頁面是暫時替代頁。專案合併後請改接 sample_management.md 內列出的正式模組 API：/api/me、/api/orders、/api/storage-locations、/api/labs、/api/master-data、/api/schedules、/api/dispatches、/api/issues。
import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '@/lib/api'
import type { CurrentUser, OthersData, PayloadValue } from './types'
import { tabs, defaultForms, sampleStatusText, wipStatusText, priorityText, orderStatusText } from './constants'
import type { TabKey } from './constants'
import { formatRequestedExperiments } from './utils/format'
import { CreateForm, SimpleTable } from './components/OthersWidgets'
import { pageStyle, headerStyle, headerActionsStyle, titleStyle, subtitleStyle, cardStyle, cardHeaderStyle, sectionTitleStyle, mutedStyle, currentUserGridStyle, profileBoxStyle, avatarStyle, selectStyle, codeBlockStyle, pillStyle, statusPillStyle, tabHeaderStyle, tabBarStyle, tabStyle, activeTabStyle, primaryButtonStyle, secondaryButtonStyle, errorStyle, successStyle, noticeStyle, tableTitleStyle, tableWrapStyle, tableStyle, thStyle, tdStyle, monoTdStyle, emptyTdStyle, trStyle, successMiniTextStyle, masterGridStyle, miniCardStyle, chipWrapStyle, outlinePillStyle, mutedMonoStyle } from './styles'

export default function OthersPage() {
  const [data, setData] = useState<OthersData | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('users')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [form, setForm] = useState<Record<string, string>>(defaultForms.users)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const currentUserPayload = useMemo(() => {
    if (!data?.current_user) return ''
    return JSON.stringify(data.current_user, null, 2)
  }, [data?.current_user])

  async function loadData() {
    try {
      setLoading(true)
      setError('')
      const result = await apiGet<OthersData>('/api/others') // TODO(integration): 改接正式 role/order/system_setting/schedule/warn 模組 API 後移除 /api/others 聚合資料
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : '載入替代資料失敗')
    } finally {
      setLoading(false)
    }
  }

  async function switchUser(userId: string) {
    try {
      setSaving(true)
      setError('')
      setSuccessMessage('')

      sessionStorage.setItem('mockUserId', userId)

      // TODO(integration): 改接 role.md 的正式使用者/身分 API
      await apiPost<CurrentUser>('/api/others/current-user', {
        user_id: userId,
      })

      await loadData()
      window.dispatchEvent(new Event('lims-current-user-changed'))
      setSuccessMessage('目前分頁操作身分已切換，不會影響其他分頁')
    } catch (err) {
      setError(err instanceof Error ? err.message : '切換使用者失敗')
    } finally {
      setSaving(false)
    }
  }

  async function completeWip(wipId: string) {
    try {
      setSaving(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/others/wips/${wipId}/complete`, {}) // TODO(integration): 改接 /api/wips/:id/actions complete

      await loadData()
      setSuccessMessage('WIP 已標記完成，樣品位置已同步更新')
    } catch (err) {
      setError(err instanceof Error ? err.message : '標記 WIP 完成失敗')
    } finally {
      setSaving(false)
    }
  }

  async function confirmDelivery(orderId: string) {
    try {
      setSaving(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/others/orders/${orderId}/confirm-delivery`, {}) // TODO(integration): 改接 order_management.md 的 /api/orders/:id/actions

      await loadData()
      setSuccessMessage('已確認送樣，樣品已建立並送到對應 Lab 收樣區')
    } catch (err) {
      setError(err instanceof Error ? err.message : '確認送樣失敗')
    } finally {
      setSaving(false)
    }
  }

  function openCreateForm() {
    setForm(defaultForms[activeTab])
    setShowCreateForm(true)
    setError('')
    setSuccessMessage('')
  }

  function closeCreateForm() {
    setShowCreateForm(false)
    setForm(defaultForms[activeTab])
  }

  function updateForm(key: string, value: string) {
    setForm((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  function getCreateEndpoint(tab: TabKey) {
    if (tab === 'storage') return '/api/others/storage-locations' // TODO(integration): 改接 system_setting.md 的 /api/storage-locations
    if (tab === 'master') return '/api/others/master-data' // TODO(integration): 改接 system_setting.md 的 /api/master-data
    return `/api/others/${tab}` // TODO(integration): 依 tab 改接正式模組 API，不要再依賴 /api/others
  }

  function normalizePayload(payload: Record<string, string>) {
    const result: Record<string, string | null> = {}

    Object.entries(payload).forEach(([key, value]) => {
      result[key] = value.trim() === '' ? null : value
    })

    return result
  }

  function buildCreatePayload() {
    let payload: Record<string, PayloadValue> = normalizePayload(form)

    if (activeTab === 'orders') {
      const keys = form.requested_experiment_keys
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)

      const requestedExperiments = keys.map((key) => {
        const [labName, experimentItem] = key.split('::')

        return {
          lab_name: labName,
          experiment_item: experimentItem,
        }
      })

      payload = {
        ...payload,
        requested_experiments: requestedExperiments,
      }

      delete payload.requested_experiment_keys
    }

    return payload
  }

  async function createData() {
    try {
      setSaving(true)
      setError('')
      setSuccessMessage('')

      if (activeTab === 'orders') {
        const selectedKeys = form.requested_experiment_keys
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean)

        if (selectedKeys.length === 0) {
          setError('請至少選擇一個實驗室 / 實驗項目')
          return
        }
      }

      await apiPost(getCreateEndpoint(activeTab), buildCreatePayload())
      await loadData()

      setShowCreateForm(false)
      setForm(defaultForms[activeTab])

      if (activeTab === 'orders') {
        if (form.status === 'approved') {
          setSuccessMessage('委託單新增成功，狀態為已核准 / 未送樣，請在委託單表格按「確認送樣」後才會建立 sample')
        } else {
          setSuccessMessage('委託單新增成功，並已同步建立一筆 /sample 可看到的待收樣資料')
        }
      } else {
        setSuccessMessage('新增成功，資料已更新')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '新增資料失敗')
    } finally {
      setSaving(false)
    }
  }

  function changeTab(tab: TabKey) {
    setActiveTab(tab)
    setShowCreateForm(false)
    setForm(defaultForms[tab])
    setError('')
    setSuccessMessage('')
  }

  useEffect(() => {
    loadData()
  }, [])

  if (loading) return <div style={pageStyle}>載入替代資料中...</div>

  if (!data) {
    return (
      <div style={pageStyle}>
        <h1 style={titleStyle}>替代資料切換</h1>
        <div style={errorStyle}>{error || '沒有資料'}</div>
      </div>
    )
  }

  const currentUser = data.current_user

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>替代資料切換</h1>
          <p style={subtitleStyle}>
            先用 /api/others 補 sample_management.md 會用到、但其他模組尚未完成的資料。
            這裡可以切換目前操作身分，也可以直接新增開發期假資料。
          </p>
        </div>

        <div style={headerActionsStyle}>
          <button style={primaryButtonStyle} onClick={openCreateForm}>
            新增資料
          </button>
          <button style={secondaryButtonStyle} onClick={loadData}>
            重新整理
          </button>
        </div>
      </div>

      {error && <div style={errorStyle}>{error}</div>}
      {successMessage && <div style={successStyle}>{successMessage}</div>}

      <section style={cardStyle}>
        <div style={cardHeaderStyle}>
          <div>
            <div style={sectionTitleStyle}>目前操作身分</div>
            <div style={mutedStyle}>用來模擬廠區使用者、實驗室 A/B 人員、主管、系統管理者。</div>
          </div>
          <span style={pillStyle}>{currentUser.role_name}</span>
        </div>

        <div style={currentUserGridStyle}>
          <div style={profileBoxStyle}>
            <div style={avatarStyle}>{currentUser.name.slice(0, 1)}</div>
            <div>
              <div style={{ fontWeight: 800 }}>{currentUser.name}</div>
              <div style={mutedStyle}>{currentUser.department}</div>
              <div style={mutedStyle}>{currentUser.email}</div>
            </div>
          </div>

          <select
            value={currentUser.id}
            onChange={(event) => switchUser(event.target.value)}
            disabled={saving}
            style={selectStyle}
          >
            {data.users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.role_name} / {user.name} / {user.department}
              </option>
            ))}
          </select>
        </div>

        <pre style={codeBlockStyle}>{currentUserPayload}</pre>
      </section>

      <section style={cardStyle}>
        <div style={tabHeaderStyle}>
          <div style={tabBarStyle}>
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => changeTab(tab.key)}
                style={activeTab === tab.key ? activeTabStyle : tabStyle}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <button style={primaryButtonStyle} onClick={openCreateForm}>
            新增目前分類資料
          </button>
        </div>

        {showCreateForm && (
          <CreateForm
            activeTab={activeTab}
            form={form}
            saving={saving}
            onChange={updateForm}
            onCancel={closeCreateForm}
            onSubmit={createData}
            masterKeys={Object.keys(data.master_data)}
          />
        )}

        {activeTab === 'users' && (
          <SimpleTable
            headers={['身分', '姓名', '部門', 'Lab', 'Email']}
            rows={data.users.map((user) => [
              user.role_name,
              user.name,
              user.department,
              user.lab_name ?? '-',
              user.email,
            ])}
          />
        )}

        {activeTab === 'labs' && (
          <SimpleTable
            headers={['代碼', '名稱', '說明']}
            rows={data.labs.map((lab) => [lab.id, lab.name, lab.description])}
          />
        )}

        {activeTab === 'storage' && (
          <SimpleTable
            headers={['代碼', '名稱', '所屬實驗室']}
            rows={data.storage_locations.map((item) => [item.code, item.name, item.lab_name])}
          />
        )}

        {activeTab === 'orders' && (
          <>
            <div style={noticeStyle}>
              approved 代表委託單已核准但尚未送樣，不會出現在 /sample。
              廠區使用者按「確認送樣」後，才會建立 sample 並進入 Lab 收樣區。
            </div>

            <div style={{ marginTop: 14 }}>
              <div style={tableTitleStyle}>委託單資料</div>

              <div style={tableWrapStyle}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>委託單號</th>
                      <th style={thStyle}>申請人</th>
                      <th style={thStyle}>部門</th>
                      <th style={thStyle}>樣品</th>
                      <th style={thStyle}>實驗需求</th>
                      <th style={thStyle}>優先度</th>
                      <th style={thStyle}>狀態</th>
                      <th style={thStyle}>操作</th>
                    </tr>
                  </thead>

                  <tbody>
                    {data.orders.length === 0 ? (
                      <tr>
                        <td style={emptyTdStyle} colSpan={8}>
                          目前沒有委託單資料
                        </td>
                      </tr>
                    ) : (
                      data.orders.map((order) => {
                        const relatedSample = (data.samples ?? []).find(
                          (sample) => sample.order_no === order.order_no,
                        )

                        return (
                          <tr key={order.id} style={trStyle}>
                            <td style={monoTdStyle}>{order.order_no}</td>
                            <td style={tdStyle}>{order.applicant_name}</td>
                            <td style={tdStyle}>{order.applicant_department}</td>
                            <td style={tdStyle}>{order.sample_name ?? '-'}</td>
                            <td style={tdStyle}>{formatRequestedExperiments(order)}</td>
                            <td style={tdStyle}>{priorityText[order.priority ?? ''] ?? order.priority ?? '-'}</td>
                            <td style={tdStyle}>
                              <span style={statusPillStyle}>
                                {orderStatusText[order.status] ?? order.status}
                              </span>
                            </td>
                            <td style={tdStyle}>
                              {order.status === 'approved' && !relatedSample ? (
                                <button
                                  type="button"
                                  disabled={saving}
                                  onClick={() => confirmDelivery(order.id)}
                                  style={{
                                    ...primaryButtonStyle,
                                    opacity: saving ? 0.55 : 1,
                                    cursor: saving ? 'not-allowed' : 'pointer',
                                  }}
                                >
                                  確認送樣
                                </button>
                              ) : relatedSample ? (
                                <span style={successMiniTextStyle}>
                                  已建立樣品 {relatedSample.sample_no}
                                </span>
                              ) : (
                                <span style={mutedStyle}>無可執行動作</span>
                              )}
                            </td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <SimpleTable
              title="/sample 可看到的待收樣資料"
              headers={['樣品編號', '委託單號', '樣品名稱', '實驗項目', '申請人', '部門', '狀態', '目前位置']}
              rows={(data.samples ?? []).map((sample) => [
                sample.sample_no,
                sample.order_no,
                sample.sample_name,
                sample.experiment_item,
                sample.applicant_name,
                sample.applicant_department,
                sampleStatusText[sample.status] ?? sample.status,
                sample.current_location,
              ])}
            />
          </>
        )}

        {activeTab === 'schedules' && (
          <>
            <SimpleTable
              title="排程"
              headers={['WIP', '機台', '狀態', '開始時間']}
              rows={data.schedules.map((schedule) => [
                schedule.wip_no,
                schedule.machine_name,
                schedule.status,
                schedule.start_time ?? '-',
              ])}
            />

            <SimpleTable
              title="派工"
              headers={['WIP', '負責人', '狀態']}
              rows={data.dispatches.map((dispatch) => [
                dispatch.wip_no,
                dispatch.assignee_name,
                dispatch.status,
              ])}
            />

            <div style={{ marginTop: 18 }}>
              <div style={sectionTitleStyle}>WIP 測試操作</div>
              <div style={mutedStyle}>
                這裡是開發測試用，可以直接把 WIP 標記完成，用來測交接與通知取件流程。
              </div>

              <div style={tableWrapStyle}>
                <table style={tableStyle}>
                  <thead>
                    <tr>
                      <th style={thStyle}>WIP 編號</th>
                      <th style={thStyle}>樣品</th>
                      <th style={thStyle}>實驗室</th>
                      <th style={thStyle}>實驗項目</th>
                      <th style={thStyle}>狀態</th>
                      <th style={thStyle}>進度</th>
                      <th style={thStyle}>目前位置</th>
                      <th style={thStyle}>操作</th>
                    </tr>
                  </thead>

                  <tbody>
                    {(data.wips ?? []).length === 0 ? (
                      <tr>
                        <td style={emptyTdStyle} colSpan={8}>
                          目前沒有 WIP 資料
                        </td>
                      </tr>
                    ) : (
                      (data.wips ?? []).map((wip) => (
                        <tr key={wip.id} style={trStyle}>
                          <td style={monoTdStyle}>{wip.wip_no}</td>
                          <td style={tdStyle}>
                            {wip.sample_no ?? '-'}
                            {wip.sample_name ? ` / ${wip.sample_name}` : ''}
                          </td>
                          <td style={tdStyle}>{wip.lab_name ?? '-'}</td>
                          <td style={tdStyle}>{wip.experiment_item ?? '-'}</td>
                          <td style={tdStyle}>{wipStatusText[wip.status] ?? wip.status}</td>
                          <td style={tdStyle}>{wip.progress}%</td>
                          <td style={tdStyle}>{wip.current_location ?? '-'}</td>
                          <td style={tdStyle}>
                            {wip.status === 'completed' ? (
                              <span style={successMiniTextStyle}>已完成</span>
                            ) : (
                              <button
                                type="button"
                                disabled={saving}
                                onClick={() => completeWip(wip.id)}
                                style={{
                                  ...primaryButtonStyle,
                                  opacity: saving ? 0.55 : 1,
                                  cursor: saving ? 'not-allowed' : 'pointer',
                                }}
                              >
                                標記完成
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {activeTab === 'issues' && (
          <SimpleTable
            headers={['類型', '目標', '等級', '訊息', '狀態']}
            rows={data.issues.map((issue) => [
              issue.type,
              `${issue.target_type} / ${issue.target_no}`,
              issue.level,
              issue.message,
              issue.status,
            ])}
          />
        )}

        {activeTab === 'master' && (
          <div style={masterGridStyle}>
            {Object.entries(data.master_data).map(([key, values]) => (
              <div key={key} style={miniCardStyle}>
                <div style={sectionTitleStyle}>{key}</div>

                <div style={chipWrapStyle}>
                  {values.map((item, index) => {
                    if (item.lab_name && item.items) {
                      return (
                        <span key={`${key}-${item.lab_name}`} style={outlinePillStyle}>
                          {item.lab_name}
                          <span style={mutedMonoStyle}>{item.items.join('、')}</span>
                        </span>
                      )
                    }

                    return (
                      <span key={`${key}-${item.value ?? index}`} style={outlinePillStyle}>
                        {item.label ?? item.value ?? '-'}
                        <span style={mutedMonoStyle}>{item.value ?? ''}</span>
                      </span>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
