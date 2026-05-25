'use client'

import { useEffect, useState } from 'react'
import { apiGet, apiPost } from '@/lib/api'
import { getErrorMessage } from '@/lib/error'
import type { OthersData } from './types'
import { tabs, sampleStatusText, wipStatusText, priorityText, orderStatusText } from './constants'
import type { TabKey } from './constants'
import { formatRequestedExperiments } from './utils/format'
import { SimpleTable } from './components/OthersWidgets'
import { pageStyle, headerStyle, headerActionsStyle, titleStyle, subtitleStyle, cardStyle, cardHeaderStyle, sectionTitleStyle, mutedStyle, currentUserGridStyle, profileBoxStyle, avatarStyle, codeBlockStyle, pillStyle, statusPillStyle, tabHeaderStyle, tabBarStyle, tabStyle, activeTabStyle, primaryButtonStyle, secondaryButtonStyle, errorStyle, successStyle, noticeStyle, tableTitleStyle, tableWrapStyle, tableStyle, thStyle, tdStyle, monoTdStyle, emptyTdStyle, trStyle, successMiniTextStyle, masterGridStyle, miniCardStyle, chipWrapStyle, outlinePillStyle, mutedMonoStyle } from './styles'

export default function OthersPage() {
  const [data, setData] = useState<OthersData | null>(null)
  const [activeTab, setActiveTab] = useState<TabKey>('users')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const currentUserPayload = data?.current_user ? JSON.stringify(data.current_user, null, 2) : ''

  async function loadData() {
    try {
      setLoading(true)
      setError('')
      const result = await apiGet<OthersData>('/api/others')
      setData(result)
    } catch (err) {
      setError(getErrorMessage(err, '載入系統資料失敗'))
    } finally {
      setLoading(false)
    }
  }

  async function completeWip(wipId: string) {
    try {
      setSaving(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/others/wips/${wipId}/complete`, {})

      await loadData()
      setSuccessMessage('WIP 狀態已標記為 completed；系統會依實驗順序更新樣品狀態')
    } catch (err) {
      setError(getErrorMessage(err, '標記 WIP 完成失敗'))
    } finally {
      setSaving(false)
    }
  }

  async function confirmDelivery(orderId: string) {
    try {
      setSaving(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/others/orders/${orderId}/confirm-delivery`, {})

      await loadData()
      setSuccessMessage('已確認送樣，樣品已建立並送到對應 Lab 收樣區')
    } catch (err) {
      setError(getErrorMessage(err, '確認送樣失敗'))
    } finally {
      setSaving(false)
    }
  }

  function changeTab(tab: TabKey) {
    setActiveTab(tab)
    setError('')
    setSuccessMessage('')
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData()
  }, [])

  if (loading) return <div style={pageStyle}>載入系統資料中...</div>

  if (!data) {
    return (
      <div style={pageStyle}>
        <h1 style={titleStyle}>系統資料檢視</h1>
        <div style={errorStyle}>{error || '沒有資料'}</div>
      </div>
    )
  }

  const currentUser = data.current_user

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>系統資料檢視</h1>
          <p style={subtitleStyle}>
            這裡整合正式 users、labs、orders、samples、wips 資料；storage locations 暫時由 labs 自動產生。
          </p>
        </div>

        <div style={headerActionsStyle}>
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
            <div style={mutedStyle}>目前使用者由正式登入資訊或後端 /api/others current_user 決定，不再使用前端暫存的測試使用者。</div>
          </div>
          <span style={pillStyle}>{currentUser.role_name ?? currentUser.role ?? '-'}</span>
        </div>

        <div style={currentUserGridStyle}>
          <div style={profileBoxStyle}>
            <div style={avatarStyle}>{(currentUser.name ?? '系').slice(0, 1)}</div>
            <div>
              <div style={{ fontWeight: 800 }}>{currentUser.name ?? '系統'}</div>
              <div style={mutedStyle}>{currentUser.department ?? currentUser.lab_name ?? '-'}</div>
              <div style={mutedStyle}>{currentUser.email ?? '-'}</div>
            </div>
          </div>

          <div style={noticeStyle}>
            mock 使用者切換已移除。若要切換身分，請從正式登入流程或後端 auth / users 資料處理。
          </div>
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

          <button style={secondaryButtonStyle} onClick={loadData}>
            重新整理目前資料
          </button>
        </div>

        {activeTab === 'users' && (
          <SimpleTable
            headers={['身分', '姓名', '部門', 'Lab', 'Email']}
            rows={data.users.map((user) => [
              user.role_name ?? user.role,
              user.name,
              user.department ?? '-',
              user.lab_name ?? '-',
              user.email ?? '-', 
            ])}
          />
        )}

        {activeTab === 'labs' && (
          <SimpleTable
            headers={['代碼', '名稱', '說明']}
            rows={data.labs.map((lab) => [lab.code ?? lab.id, lab.name, lab.description ?? '-'])}
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
