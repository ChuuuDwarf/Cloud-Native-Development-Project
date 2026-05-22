'use client'

import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { apiGet, apiPost } from '@/lib/api'

type CurrentUser = {
  id: string
  name: string
  role: string
  role_name: string
  department: string
  lab_name: string | null
  email: string
}

type RequestedExperiment = {
  lab_name: string
  experiment_item: string
}

type SampleData = {
  id: string
  sample_no: string
  order_no: string
  sample_name: string
  experiment_item: string
  applicant_name: string
  applicant_department: string
  status: string
  current_location: string
  note: string | null
}

type WipData = {
  id: string
  wip_no: string
  sample_id: string
  order_no: string
  lab_name: string | null
  experiment_item: string | null
  priority: string
  status: string
  progress: number
  current_location: string | null
  completed_at: string | null
  note: string | null
  sample_no?: string | null
  sample_name?: string | null
}

type MasterDataItem = {
  value?: string
  label?: string
  lab_name?: string
  items?: string[]
}

type OthersData = {
  current_user: CurrentUser
  users: CurrentUser[]
  labs: Array<{ id: string; name: string; description: string }>
  storage_locations: Array<{ id: string; code: string; name: string; lab_name: string }>
  orders: Array<{
    id: string
    order_no: string
    applicant_name: string
    applicant_department: string
    sample_name?: string
    sample_quantity?: string
    target_lab?: string
    test_item?: string
    priority?: string
    status: string
    requested_experiments?: RequestedExperiment[]
  }>
  samples?: SampleData[]
  wips?: WipData[]
  schedules: Array<{
    id: string
    wip_no: string
    machine_name: string
    status: string
    start_time: string | null
  }>
  dispatches: Array<{ id: string; wip_no: string; assignee_name: string; status: string }>
  issues: Array<{
    id: string
    type: string
    target_type: string
    target_no: string
    level: string
    message: string
    status: string
  }>
  master_data: Record<string, MasterDataItem[]>
}

type PayloadValue = string | null | RequestedExperiment[]

const tabs = [
  { key: 'users', label: '使用者 / 權限' },
  { key: 'labs', label: '實驗室' },
  { key: 'storage', label: '儲位' },
  { key: 'orders', label: '委託單 / 待收樣' },
  { key: 'schedules', label: '排程 / 派工' },
  { key: 'issues', label: '異常 / 告警' },
  { key: 'master', label: '狀態選項' },
] as const

type TabKey = (typeof tabs)[number]['key']

const defaultForms: Record<TabKey, Record<string, string>> = {
  users: {
    name: '',
    role: 'lab_staff',
    role_name: '實驗室人員',
    department: 'Lab A',
    lab_name: 'Lab A',
    email: '',
  },
  labs: {
    name: 'Lab A',
    description: '材料與電性測試',
  },
  storage: {
    code: '',
    name: '',
    lab_name: 'Lab A',
  },
  orders: {
    order_no: '',
    applicant_name: '王建國',
    applicant_department: 'F12 廠',
    sample_name: '晶圓切片',
    sample_quantity: '1',
    requested_experiment_keys: 'Lab A::SEM 觀察',
    priority: 'normal',
    status: 'approved',
  },
  schedules: {
    wip_no: '',
    machine_name: '',
    status: 'waiting_schedule',
    start_time: '',
  },
  issues: {
    type: 'warning',
    target_type: 'sample',
    target_no: '',
    level: 'medium',
    message: '',
    status: 'open',
  },
  master: {
    category: 'sample_statuses',
    value: '',
    label: '',
  },
}

const sampleStatusText: Record<string, string> = {
  approved: '已核准 / 未送樣',
  pending_receive: '待收樣',
  received: '已收樣',
  split: '已分貨',
  transferring: '交接中',
  in_storage: '已入庫',
  outbound: '待取件',
  picked_up: '已取件',
}

const wipStatusText: Record<string, string> = {
  created: '已建立',
  waiting_schedule: '待排程',
  scheduled: '已排程',
  dispatched: '已派工',
  running: '執行中',
  paused: '暫停',
  completed: '已完成',
  terminated: '已終止',
  cancelled: '已取消',
}

const priorityText: Record<string, string> = {
  low: '低',
  normal: '一般',
  high: '高',
  urgent: '急件',
}

const orderStatusText: Record<string, string> = {
  approved: '已核准 / 未送樣',
  pending_receive: '已確認送樣 / 待收樣',
  received: '已收樣',
  split: '已分貨',
  testing: '實驗中',
  completed: '已完成',
  cancelled: '已取消',
}

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
      const result = await apiGet<OthersData>('/api/others')
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

      await apiPost(`/api/others/wips/${wipId}/complete`, {})

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

      await apiPost(`/api/others/orders/${orderId}/confirm-delivery`, {})

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
    if (tab === 'storage') return '/api/others/storage-locations'
    if (tab === 'master') return '/api/others/master-data'
    return `/api/others/${tab}`
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

function formatRequestedExperiments(order: OthersData['orders'][number]) {
  if (order.requested_experiments && order.requested_experiments.length > 0) {
    return order.requested_experiments
      .map((item) => `${item.lab_name}:${item.experiment_item}`)
      .join('、')
  }

  if (order.target_lab || order.test_item) {
    return `${order.target_lab ?? '-'}:${order.test_item ?? '-'}`
  }

  return '-'
}

function CreateForm({
  activeTab,
  form,
  saving,
  onChange,
  onCancel,
  onSubmit,
  masterKeys,
}: {
  activeTab: TabKey
  form: Record<string, string>
  saving: boolean
  onChange: (key: string, value: string) => void
  onCancel: () => void
  onSubmit: () => void
  masterKeys: string[]
}) {
  const titleMap: Record<TabKey, string> = {
    users: '新增使用者',
    labs: '新增實驗室',
    storage: '新增儲位',
    orders: '新增委託單 / 待收樣資料',
    schedules: '新增排程',
    issues: '新增異常 / 告警',
    master: '新增狀態選項',
  }

  const labOptions = [
    { value: '', label: '無 / 不指定' },
    { value: 'Lab A', label: 'Lab A' },
    { value: 'Lab B', label: 'Lab B' },
    { value: 'Lab C', label: 'Lab C' },
  ]

  const departmentOptions = [
    { value: 'F12 廠', label: 'F12 廠' },
    { value: 'F6 廠', label: 'F6 廠' },
    { value: 'Lab A', label: 'Lab A' },
    { value: 'Lab B', label: 'Lab B' },
    { value: 'Lab C', label: 'Lab C' },
    { value: 'Lab 管理部', label: 'Lab 管理部' },
    { value: 'IT', label: 'IT' },
  ]

  const roleOptions = [
    { value: 'factory_user', label: '廠區使用者' },
    { value: 'lab_staff', label: '實驗室人員' },
    { value: 'lab_supervisor', label: '實驗室主管' },
    { value: 'system_admin', label: '系統管理者' },
  ]

  const orderStatusOptions = [
    { value: 'approved', label: '已核准 / 未送樣 approved' },
    { value: 'pending_receive', label: '已確認送樣 / 待收樣 pending_receive' },
  ]

  const priorityOptions = [
    { value: 'low', label: '低 low' },
    { value: 'normal', label: '一般 normal' },
    { value: 'high', label: '高 high' },
    { value: 'urgent', label: '特急 urgent' },
  ]

  const labExperimentMatrix = [
    {
      labName: 'Lab A',
      items: ['SEM 觀察', '電性量測', '材料分析'],
    },
    {
      labName: 'Lab B',
      items: ['光學量測', '可靠度測試', '外觀檢查'],
    },
    {
      labName: 'Lab C',
      items: ['化學分析', '成分分析', '污染分析'],
    },
  ]

  const sampleQuantityOptions = [
    { value: '1', label: '1 件' },
    { value: '2', label: '2 件' },
    { value: '3', label: '3 件' },
    { value: '5', label: '5 件' },
    { value: '10', label: '10 件' },
  ]

  const scheduleStatusOptions = [
    { value: 'waiting_schedule', label: '待排程 waiting_schedule' },
    { value: 'scheduled', label: '已排程 scheduled' },
    { value: 'running', label: '執行中 running' },
    { value: 'completed', label: '已完成 completed' },
    { value: 'cancelled', label: '已取消 cancelled' },
  ]

  const issueTypeOptions = [
    { value: 'warning', label: '告警 warning' },
    { value: 'abnormal', label: '異常 abnormal' },
    { value: 'terminate', label: '中止 terminate' },
  ]

  const issueTargetTypeOptions = [
    { value: 'sample', label: '樣品 sample' },
    { value: 'wip', label: 'WIP wip' },
    { value: 'experiment_run', label: '實驗執行 experiment_run' },
    { value: 'machine', label: '機台 machine' },
    { value: 'order', label: '委託單 order' },
  ]

  const issueLevelOptions = [
    { value: 'low', label: '低 low' },
    { value: 'medium', label: '中 medium' },
    { value: 'high', label: '高 high' },
    { value: 'critical', label: '嚴重 critical' },
  ]

  const issueStatusOptions = [
    { value: 'open', label: '未處理 open' },
    { value: 'processing', label: '處理中 processing' },
    { value: 'resolved', label: '已解決 resolved' },
    { value: 'closed', label: '已關閉 closed' },
  ]

  const masterCategoryOptions = [
    { value: 'sample_statuses', label: '樣品狀態 sample_statuses' },
    { value: 'wip_statuses', label: 'WIP 狀態 wip_statuses' },
    { value: 'priorities', label: '優先度 priorities' },
    { value: 'experiment_items', label: '實驗項目 experiment_items' },
    { value: 'lab_experiment_matrix', label: '實驗室項目矩陣 lab_experiment_matrix' },
    ...masterKeys
      .filter(
        (key) =>
          ![
            'sample_statuses',
            'wip_statuses',
            'priorities',
            'experiment_items',
            'lab_experiment_matrix',
          ].includes(key),
      )
      .map((key) => ({ value: key, label: key })),
  ]

  function getRequestedExperimentKeys() {
    return form.requested_experiment_keys
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }

  function toggleRequestedExperiment(key: string) {
    const currentKeys = getRequestedExperimentKeys()

    const nextKeys = currentKeys.includes(key)
      ? currentKeys.filter((item) => item !== key)
      : [...currentKeys, key]

    onChange('requested_experiment_keys', nextKeys.join(','))
  }

  function isRequestedExperimentChecked(key: string) {
    return getRequestedExperimentKeys().includes(key)
  }

  function changeUserRole(role: string) {
    const roleNameMap: Record<string, string> = {
      factory_user: '廠區使用者',
      lab_staff: '實驗室人員',
      lab_supervisor: '實驗室主管',
      system_admin: '系統管理者',
    }

    onChange('role', role)
    onChange('role_name', roleNameMap[role] ?? role)

    if (role === 'factory_user') {
      onChange('department', 'F12 廠')
      onChange('lab_name', '')
    }

    if (role === 'lab_staff') {
      onChange('department', 'Lab A')
      onChange('lab_name', 'Lab A')
    }

    if (role === 'lab_supervisor') {
      onChange('department', 'Lab 管理部')
      onChange('lab_name', 'Lab A')
    }

    if (role === 'system_admin') {
      onChange('department', 'IT')
      onChange('lab_name', '')
    }
  }

  return (
    <div style={formBoxStyle}>
      <div style={formHeaderStyle}>
        <div>
          <div style={sectionTitleStyle}>{titleMap[activeTab]}</div>
          <div style={mutedStyle}>
            {activeTab === 'orders'
              ? '這裡新增 approved 時只會建立委託單，不會建立 sample；按確認送樣後才會進 Lab 收樣區。'
              : '這裡新增的是開發期假資料。'}
          </div>
        </div>

        <button style={ghostButtonStyle} onClick={onCancel}>
          關閉
        </button>
      </div>

      {activeTab === 'users' && (
        <div style={formGridStyle}>
          <TextInput label="姓名" value={form.name} onChange={(value) => onChange('name', value)} />
          <SelectInput label="角色" value={form.role} onChange={changeUserRole} options={roleOptions} />
          <SelectInput
            label="部門"
            value={form.department}
            onChange={(value) => onChange('department', value)}
            options={departmentOptions}
          />
          <SelectInput
            label="Lab"
            value={form.lab_name}
            onChange={(value) => onChange('lab_name', value)}
            options={labOptions}
          />
          <TextInput label="Email" value={form.email} onChange={(value) => onChange('email', value)} />
        </div>
      )}

      {activeTab === 'labs' && (
        <div style={formGridStyle}>
          <SelectInput
            label="實驗室名稱"
            value={form.name}
            onChange={(value) => onChange('name', value)}
            options={[
              { value: 'Lab A', label: 'Lab A' },
              { value: 'Lab B', label: 'Lab B' },
              { value: 'Lab C', label: 'Lab C' },
              { value: 'Lab D', label: 'Lab D' },
            ]}
          />

          <SelectInput
            label="說明"
            value={form.description}
            onChange={(value) => onChange('description', value)}
            options={[
              { value: '材料與電性測試', label: '材料與電性測試' },
              { value: '光學與可靠度測試', label: '光學與可靠度測試' },
              { value: '化學分析', label: '化學分析' },
              { value: '製程驗證', label: '製程驗證' },
            ]}
          />
        </div>
      )}

      {activeTab === 'storage' && (
        <div style={formGridStyle}>
          <SelectInput
            label="儲位代碼"
            value={form.code}
            onChange={(value) => onChange('code', value)}
            options={[
              { value: '', label: '系統自動產生' },
              { value: 'A-R01-S01', label: 'A-R01-S01' },
              { value: 'A-R01-S02', label: 'A-R01-S02' },
              { value: 'B-R01-S01', label: 'B-R01-S01' },
              { value: 'B-R01-S02', label: 'B-R01-S02' },
              { value: 'C-R01-S01', label: 'C-R01-S01' },
            ]}
          />

          <SelectInput
            label="儲位名稱"
            value={form.name}
            onChange={(value) => onChange('name', value)}
            options={[
              { value: '', label: '系統自動帶入未命名儲位' },
              { value: 'Lab A 待取件架 1', label: 'Lab A 待取件架 1' },
              { value: 'Lab A 暫存架 2', label: 'Lab A 暫存架 2' },
              { value: 'Lab B 待取件架 1', label: 'Lab B 待取件架 1' },
              { value: 'Lab B 暫存架 2', label: 'Lab B 暫存架 2' },
              { value: 'Lab C 待取件架 1', label: 'Lab C 待取件架 1' },
            ]}
          />

          <SelectInput
            label="所屬 Lab"
            value={form.lab_name}
            onChange={(value) => onChange('lab_name', value)}
            options={labOptions.filter((option) => option.value !== '')}
          />
        </div>
      )}

      {activeTab === 'orders' && (
        <div style={formGridStyle}>
          <TextInput
            label="委託單號"
            value={form.order_no}
            placeholder="不填就由後端產生"
            onChange={(value) => onChange('order_no', value)}
          />

          <SelectInput
            label="申請人"
            value={form.applicant_name}
            onChange={(value) => onChange('applicant_name', value)}
            options={[
              { value: '王建國', label: '王建國' },
              { value: '李美珍', label: '李美珍' },
              { value: '陳怡君', label: '陳怡君' },
              { value: '黃俊傑', label: '黃俊傑' },
            ]}
          />

          <SelectInput
            label="申請部門"
            value={form.applicant_department}
            onChange={(value) => onChange('applicant_department', value)}
            options={departmentOptions.filter((option) => option.value.includes('廠'))}
          />

          <TextInput
            label="樣品名稱"
            value={form.sample_name}
            placeholder="例如 晶圓切片"
            onChange={(value) => onChange('sample_name', value)}
          />

          <SelectInput
            label="樣品數量"
            value={form.sample_quantity}
            onChange={(value) => onChange('sample_quantity', value)}
            options={sampleQuantityOptions}
          />

          <SelectInput
            label="優先度"
            value={form.priority}
            onChange={(value) => onChange('priority', value)}
            options={priorityOptions}
          />

          <SelectInput
            label="委託單狀態"
            value={form.status}
            onChange={(value) => onChange('status', value)}
            options={orderStatusOptions}
          />

          <div style={wideFieldStyle}>
            <div style={fieldTitleStyle}>實驗室 / 實驗項目</div>
            <div style={mutedStyle}>可多選。不同實驗室可以負責不同實驗項目。</div>

            <div style={experimentMatrixStyle}>
              {labExperimentMatrix.map((lab) => (
                <div key={lab.labName} style={experimentLabBoxStyle}>
                  <div style={experimentLabTitleStyle}>{lab.labName}</div>

                  <div style={experimentItemGridStyle}>
                    {lab.items.map((item) => {
                      const key = `${lab.labName}::${item}`

                      return (
                        <label key={key} style={checkboxLabelStyle}>
                          <input
                            type="checkbox"
                            checked={isRequestedExperimentChecked(key)}
                            onChange={() => toggleRequestedExperiment(key)}
                          />
                          <span>{item}</span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'schedules' && (
        <div style={formGridStyle}>
          <TextInput
            label="WIP 編號"
            value={form.wip_no}
            placeholder="例如 WIP-2026-0001-A"
            onChange={(value) => onChange('wip_no', value)}
          />

          <SelectInput
            label="機台名稱"
            value={form.machine_name}
            onChange={(value) => onChange('machine_name', value)}
            options={[
              { value: '', label: '未指定機台' },
              { value: 'SEM-001', label: 'SEM-001' },
              { value: 'OPT-002', label: 'OPT-002' },
              { value: 'XRD-003', label: 'XRD-003' },
              { value: 'FTIR-004', label: 'FTIR-004' },
            ]}
          />

          <SelectInput
            label="狀態"
            value={form.status}
            onChange={(value) => onChange('status', value)}
            options={scheduleStatusOptions}
          />

          <SelectInput
            label="開始時間"
            value={form.start_time}
            onChange={(value) => onChange('start_time', value)}
            options={[
              { value: '', label: '未排定' },
              { value: '2026-05-22T10:00:00', label: '2026-05-22 10:00' },
              { value: '2026-05-22T14:00:00', label: '2026-05-22 14:00' },
              { value: '2026-05-23T09:00:00', label: '2026-05-23 09:00' },
              { value: '2026-05-23T15:00:00', label: '2026-05-23 15:00' },
            ]}
          />
        </div>
      )}

      {activeTab === 'issues' && (
        <div style={formGridStyle}>
          <SelectInput
            label="類型"
            value={form.type}
            onChange={(value) => onChange('type', value)}
            options={issueTypeOptions}
          />

          <SelectInput
            label="目標類型"
            value={form.target_type}
            onChange={(value) => onChange('target_type', value)}
            options={issueTargetTypeOptions}
          />

          <TextInput
            label="目標編號"
            value={form.target_no}
            placeholder="例如 SMP-2026-0001 或 WIP-2026-0001-A"
            onChange={(value) => onChange('target_no', value)}
          />

          <SelectInput
            label="等級"
            value={form.level}
            onChange={(value) => onChange('level', value)}
            options={issueLevelOptions}
          />

          <SelectInput
            label="訊息"
            value={form.message}
            onChange={(value) => onChange('message', value)}
            options={[
              { value: '', label: '未填寫訊息' },
              { value: '樣品待取件超過 2 天', label: '樣品待取件超過 2 天' },
              { value: '機台故障', label: '機台故障' },
              { value: '實驗數據異常', label: '實驗數據異常' },
              { value: 'WIP 超過預計完成時間', label: 'WIP 超過預計完成時間' },
              { value: '樣品交接逾時', label: '樣品交接逾時' },
            ]}
          />

          <SelectInput
            label="狀態"
            value={form.status}
            onChange={(value) => onChange('status', value)}
            options={issueStatusOptions}
          />
        </div>
      )}

      {activeTab === 'master' && (
        <div style={formGridStyle}>
          <SelectInput
            label="分類"
            value={form.category}
            onChange={(value) => onChange('category', value)}
            options={masterCategoryOptions}
          />

          <TextInput
            label="值 value"
            value={form.value}
            placeholder="例如 pending_receive"
            onChange={(value) => onChange('value', value)}
          />

          <TextInput
            label="顯示名稱 label"
            value={form.label}
            placeholder="例如 待收樣"
            onChange={(value) => onChange('label', value)}
          />
        </div>
      )}

      <div style={formActionStyle}>
        <button
          style={{
            ...primaryButtonStyle,
            opacity: saving ? 0.55 : 1,
            cursor: saving ? 'not-allowed' : 'pointer',
          }}
          disabled={saving}
          onClick={onSubmit}
        >
          {saving ? '儲存中...' : '新增'}
        </button>
      </div>
    </div>
  )
}

function SimpleTable({
  title,
  headers,
  rows,
}: {
  title?: string
  headers: string[]
  rows: Array<Array<string | number | null | undefined>>
}) {
  return (
    <div style={{ marginTop: 14 }}>
      {title && <div style={tableTitleStyle}>{title}</div>}

      <div style={tableWrapStyle}>
        <table style={tableStyle}>
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header} style={thStyle}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td style={emptyTdStyle} colSpan={headers.length}>
                  目前沒有資料
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={rowIndex} style={trStyle}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${rowIndex}-${cellIndex}`} style={tdStyle}>
                      {cell ?? '-'}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TextInput({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  onChange: (value: string) => void
}) {
  return (
    <label style={fieldStyle}>
      <span style={fieldTitleStyle}>{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        style={inputStyle}
      />
    </label>
  )
}

function SelectInput({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: Array<{ value: string; label: string }>
  onChange: (value: string) => void
}) {
  return (
    <label style={fieldStyle}>
      <span style={fieldTitleStyle}>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle}>
        {options.map((option, index) => (
          <option key={`${option.value}-${index}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

const pageStyle: CSSProperties = {
  padding: 24,
  color: 'var(--text)',
}

const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 16,
  alignItems: 'flex-start',
  marginBottom: 18,
}

const headerActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 10,
}

const titleStyle: CSSProperties = {
  fontSize: 26,
  fontWeight: 900,
  margin: 0,
}

const subtitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 13,
  marginTop: 8,
  lineHeight: 1.6,
}

const cardStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 16,
  padding: 18,
  marginBottom: 18,
}

const cardHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 14,
  alignItems: 'center',
  marginBottom: 14,
}

const sectionTitleStyle: CSSProperties = {
  fontSize: 15,
  fontWeight: 900,
}

const mutedStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  lineHeight: 1.5,
}

const currentUserGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr minmax(280px, 420px)',
  gap: 14,
  alignItems: 'center',
}

const profileBoxStyle: CSSProperties = {
  display: 'flex',
  gap: 12,
  alignItems: 'center',
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

const avatarStyle: CSSProperties = {
  width: 42,
  height: 42,
  borderRadius: 999,
  background: 'rgba(56,139,253,0.18)',
  color: 'var(--blue)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 900,
}

const selectStyle: CSSProperties = {
  width: '100%',
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  borderRadius: 10,
  padding: '10px 12px',
}

const codeBlockStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
  overflowX: 'auto',
  color: 'var(--text2)',
  fontSize: 12,
  marginTop: 12,
}

const pillStyle: CSSProperties = {
  display: 'inline-flex',
  borderRadius: 999,
  padding: '5px 10px',
  color: 'var(--blue)',
  background: 'rgba(56,139,253,0.14)',
  border: '1px solid rgba(56,139,253,0.32)',
  fontSize: 12,
  fontWeight: 800,
}

const statusPillStyle: CSSProperties = {
  display: 'inline-flex',
  borderRadius: 999,
  padding: '4px 9px',
  color: 'var(--blue)',
  background: 'rgba(56,139,253,0.14)',
  border: '1px solid rgba(56,139,253,0.32)',
  fontSize: 11,
  fontWeight: 800,
  whiteSpace: 'nowrap',
}

const tabHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  alignItems: 'center',
  flexWrap: 'wrap',
  marginBottom: 14,
}

const tabBarStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
}

const tabStyle: CSSProperties = {
  border: '1px solid var(--border)',
  background: 'var(--s2)',
  color: 'var(--text2)',
  borderRadius: 999,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 12,
}

const activeTabStyle: CSSProperties = {
  ...tabStyle,
  background: 'rgba(56,139,253,0.16)',
  color: 'var(--blue)',
  borderColor: 'rgba(56,139,253,0.55)',
}

const primaryButtonStyle: CSSProperties = {
  border: '1px solid var(--blue)',
  background: 'var(--blue)',
  color: '#fff',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 800,
  fontSize: 12,
}

const secondaryButtonStyle: CSSProperties = {
  border: '1px solid var(--border)',
  background: 'var(--s2)',
  color: 'var(--text2)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 800,
  fontSize: 12,
}

const ghostButtonStyle: CSSProperties = {
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text2)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 800,
  fontSize: 12,
}

const errorStyle: CSSProperties = {
  background: 'rgba(247,129,102,0.12)',
  border: '1px solid rgba(247,129,102,0.25)',
  color: 'var(--orange)',
  borderRadius: 12,
  padding: 12,
  marginBottom: 12,
  fontSize: 13,
}

const successStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.25)',
  color: 'var(--green)',
  borderRadius: 12,
  padding: 12,
  marginBottom: 12,
  fontSize: 13,
}

const noticeStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  color: 'var(--text2)',
  borderRadius: 12,
  padding: 12,
  marginBottom: 12,
  fontSize: 13,
}

const formBoxStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
  marginBottom: 16,
}

const formHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 14,
  marginBottom: 14,
}

const formGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 12,
}

const fieldStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

const fieldTitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  fontWeight: 800,
}

const inputStyle: CSSProperties = {
  width: '100%',
  background: 'var(--s1)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  borderRadius: 10,
  padding: '10px 12px',
  outline: 'none',
}

const wideFieldStyle: CSSProperties = {
  gridColumn: '1 / -1',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const experimentMatrixStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 10,
}

const experimentLabBoxStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

const experimentLabTitleStyle: CSSProperties = {
  fontWeight: 900,
  marginBottom: 8,
}

const experimentItemGridStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
}

const checkboxLabelStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  alignItems: 'center',
  color: 'var(--text2)',
  fontSize: 13,
}

const formActionStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  marginTop: 14,
}

const tableTitleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 900,
  marginBottom: 8,
}

const tableWrapStyle: CSSProperties = {
  overflowX: 'auto',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  marginTop: 10,
}

const tableStyle: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
}

const thStyle: CSSProperties = {
  textAlign: 'left',
  background: 'var(--s2)',
  color: 'var(--text3)',
  fontSize: 11,
  padding: '10px 12px',
  whiteSpace: 'nowrap',
}

const tdStyle: CSSProperties = {
  borderTop: '1px solid var(--border2)',
  color: 'var(--text2)',
  fontSize: 12,
  padding: '10px 12px',
  whiteSpace: 'nowrap',
}

const monoTdStyle: CSSProperties = {
  ...tdStyle,
  fontFamily: 'monospace',
  color: 'var(--text)',
}

const emptyTdStyle: CSSProperties = {
  ...tdStyle,
  textAlign: 'center',
  color: 'var(--text3)',
  padding: 24,
}

const trStyle: CSSProperties = {
  verticalAlign: 'top',
}

const successMiniTextStyle: CSSProperties = {
  color: 'var(--green)',
  fontWeight: 800,
  fontSize: 12,
}

const masterGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
  gap: 12,
}

const miniCardStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

const chipWrapStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  marginTop: 10,
}

const outlinePillStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  border: '1px solid var(--border)',
  borderRadius: 999,
  padding: '5px 9px',
  color: 'var(--text2)',
  fontSize: 12,
}

const mutedMonoStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  fontFamily: 'monospace',
}