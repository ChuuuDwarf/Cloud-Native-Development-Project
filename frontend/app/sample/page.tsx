'use client'

import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { apiGet, apiPost } from '@/lib/api'

type Sample = {
  id: string
  sample_no: string
  order_no: string
  sample_name: string | null
  experiment_item: string | null
  applicant_name: string | null
  applicant_department: string | null
  status: string
  current_location: string | null
  storage_location_id: string | null
  received_at: string | null
  received_by: string | null
  picked_up_at: string | null
  picked_up_by: string | null
  note: string | null
  created_at: string
  updated_at: string
}

type Wip = {
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
  scheduled_at: string | null
  dispatched_at: string | null
  started_at: string | null
  completed_at: string | null
  terminated_at: string | null
  note: string | null
  created_at: string
  updated_at: string
}

type SampleHistory = {
  id: string
  sample_id: string
  action: string
  from_status: string | null
  to_status: string | null
  description: string | null
  operator_name: string | null
  created_at: string
}

type CurrentUser = {
  id: string
  name: string
  role: string
  role_name?: string
  department: string
  lab_name?: string | null
  email?: string
}

const fallbackUser: CurrentUser = {
  id: 'fallback',
  name: '實驗室人員A',
  role: 'lab_staff',
  role_name: '實驗室人員',
  department: 'Lab A',
  lab_name: 'Lab A',
  email: '',
}

const sampleStatusText: Record<string, string> = {
  pending_receive: '待收樣',
  received: '已收樣',
  split: '已分貨',
  transferring: '交接中',
  in_storage: '已入庫',
  outbound: '待取件',
  picked_up: '已取件',
  lost: '遺失',
  damaged: '破損',
  cancelled: '已取消',
}

const wipStatusText: Record<string, string> = {
  created: '已建立',
  waiting_schedule: '待排程',
  scheduled: '已排程',
  dispatched: '已派工',
  running: '實驗中',
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

function getUserLab(user: CurrentUser) {
  return user.lab_name || user.department
}

function isSampleVisibleForUser(sample: Sample, user: CurrentUser) {
  if (user.role === 'system_admin') return true

  if (user.role === 'factory_user') {
    return sample.applicant_name === user.name
  }

  if (user.role === 'lab_staff' || user.role === 'lab_supervisor') {
    const labName = getUserLab(user)

    if (!labName) return false

    return sample.current_location?.startsWith(labName) ?? false
  }

  return false
}

export default function SamplePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser>(fallbackUser)
  const [samples, setSamples] = useState<Sample[]>([])
  const [wips, setWips] = useState<Wip[]>([])
  const [sampleHistories, setSampleHistories] = useState<SampleHistory[]>([])
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const isFactoryUser = currentUser.role === 'factory_user'
  const canOperateSample =
    currentUser.role === 'lab_staff' ||
    currentUser.role === 'lab_supervisor' ||
    currentUser.role === 'system_admin'

  const operatorName = currentUser.name || fallbackUser.name

  const visibleSamples = useMemo(() => {
    return samples.filter((sample) => isSampleVisibleForUser(sample, currentUser))
  }, [samples, currentUser])

  const selectedSample = useMemo(() => {
    return visibleSamples.find((sample) => sample.id === selectedSampleId) ?? null
  }, [visibleSamples, selectedSampleId])

  const selectedWips = useMemo(() => {
    if (!selectedSample) return []
    return wips.filter((wip) => wip.sample_id === selectedSample.id)
  }, [wips, selectedSample])

  const wipsByLab = useMemo(() => {
    return selectedWips.reduce<Record<string, Wip[]>>((groups, wip) => {
      const labName = wip.lab_name ?? '未指定實驗室'

      if (!groups[labName]) {
        groups[labName] = []
      }

      groups[labName].push(wip)
      return groups
    }, {})
  }, [selectedWips])

  const allWipsCompleted =
    selectedWips.length > 0 &&
    selectedWips.every((wip) => wip.status === 'completed')

  const pendingReceiveCount = visibleSamples.filter(
    (sample) => sample.status === 'pending_receive',
  ).length

  const inLabCount = visibleSamples.filter((sample) =>
    ['received', 'split', 'transferring', 'in_storage'].includes(sample.status),
  ).length

  const outboundCount = visibleSamples.filter(
    (sample) => sample.status === 'outbound',
  ).length

  const pickedUpCount = visibleSamples.filter(
    (sample) => sample.status === 'picked_up',
  ).length

  async function loadCurrentUser() {
    try {
      const me = await apiGet<CurrentUser>('/api/me')
      setCurrentUser(me)
      return me
    } catch {
      setCurrentUser(fallbackUser)
      return fallbackUser
    }
  }

  async function loadData() {
    try {
      setLoading(true)
      setError('')
      setSuccessMessage('')

      const meData = await loadCurrentUser()

      const [sampleData, wipData] = await Promise.all([
        apiGet<Sample[]>('/api/samples'),
        apiGet<Wip[]>('/api/wips'),
      ])

      const filteredSamples = sampleData.filter((sample) =>
        isSampleVisibleForUser(sample, meData),
      )

      setCurrentUser(meData)
      setSamples(sampleData)
      setWips(wipData)

      if (selectedSampleId) {
        const stillVisible = filteredSamples.some((item) => item.id === selectedSampleId)

        if (!stillVisible) {
          setSelectedSampleId(null)
          setSampleHistories([])
          setDetailOpen(false)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '載入資料失敗')
    } finally {
      setLoading(false)
    }
  }

  async function loadSampleHistory(sampleId: string) {
    try {
      setHistoryLoading(true)
      const data = await apiGet<SampleHistory[]>(`/api/samples/${sampleId}/history`)
      setSampleHistories(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : '載入樣品歷程失敗')
    } finally {
      setHistoryLoading(false)
    }
  }

  async function openDetail(sampleId: string) {
    setSelectedSampleId(sampleId)
    setDetailOpen(true)
    setSampleHistories([])
    setError('')
    setSuccessMessage('')
    await loadSampleHistory(sampleId)
  }

  function closeDetail() {
    setDetailOpen(false)
  }

  async function runSampleAction(
    sampleId: string,
    action: 'receive' | 'outbound' | 'pickup_confirmed',
  ) {
    if (!canOperateSample) {
      setError('廠區使用者只能查看樣品資料，不能執行收樣或取件操作')
      return
    }

    try {
      setSubmitting(true)
      setError('')
      setSuccessMessage('')

      const body: Record<string, string> = {
        action,
        operator_name: operatorName,
      }

      if (action === 'outbound') {
        body.note = '所有實驗已完成，已通知原使用者取件'
      }

      if (action === 'pickup_confirmed') {
        body.current_location = '已取件'
      }

      await apiPost(`/api/samples/${sampleId}/actions`, body)

      if (action === 'receive') {
        setSuccessMessage('已完成收樣，樣品仍會保留在目前實驗室的收樣管理清單中')
      }

      if (action === 'outbound') {
        setSuccessMessage('已通知取件，樣品已移至目前實驗室的待取件區')
      }

      if (action === 'pickup_confirmed') {
        setSuccessMessage('已確認廠區取件')
      }

      await loadData()
      await loadSampleHistory(sampleId)
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失敗')
    } finally {
      setSubmitting(false)
    }
  }

  function getNextStep(sample: Sample | null) {
    if (!sample) return '請先選擇樣品'

    if (isFactoryUser) {
      if (sample.status === 'pending_receive') {
        return '樣品已送出，等待實驗室確認收樣。'
      }

      if (sample.status === 'received') {
        return '實驗室已收樣，等待建立或執行實驗子單。'
      }

      if (sample.status === 'split') {
        return '樣品已進入實驗流程，可在此追蹤 WIP / 實驗子單進度。'
      }

      if (sample.status === 'outbound') {
        return '實驗已完成，樣品等待取回。'
      }

      if (sample.status === 'picked_up') {
        return '樣品已取回，流程完成。'
      }

      return '目前僅提供樣品狀態與歷程查詢。'
    }

    if (sample.status === 'pending_receive') {
      return '樣品尚未完成收樣，下一步是確認收樣。'
    }

    if (sample.status === 'received') {
      return '樣品已完成收樣，下一步請前往 WIP / 分貨管理建立實驗子單。'
    }

    if (sample.status === 'split' && selectedWips.length === 0) {
      return '樣品已標記分貨，但目前沒有 WIP，請確認後端資料是否已建立實驗子單。'
    }

    if (sample.status === 'split' && selectedWips.length > 0 && !allWipsCompleted) {
      return '樣品已有 WIP / 實驗子單，請依實驗室分組追蹤各實驗進度。若某實驗室完成且還有下一實驗室，請至交接流轉頁處理。'
    }

    if (sample.status === 'split' && allWipsCompleted) {
      return '所有實驗已完成，可通知原使用者取件，並將樣品移至待取件區。'
    }

    if (sample.status === 'transferring') {
      return '樣品正在跨實驗室交接中，等待下一個實驗室簽收。'
    }

    if (sample.status === 'outbound') {
      return '已通知原使用者取件，樣品目前在待取件區。'
    }

    if (sample.status === 'picked_up') {
      return '樣品已由原使用者取回，流程完成。'
    }

    if (sample.status === 'in_storage') {
      return '樣品目前已入庫保存。若不做倉儲流程，後續可改為直接通知取件。'
    }

    return '請依樣品狀態判斷下一步。'
  }

  function goToWipPage(sampleId: string) {
    window.location.href = `/wip?sampleId=${sampleId}`
  }

  function goToTransferPage() {
    window.location.href = '/sample/transfer'
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>
            {isFactoryUser ? '我的送樣追蹤' : '收樣與樣品追蹤'}
          </h1>
          <p style={subtitleStyle}>
            {isFactoryUser
              ? 'SAMPLE TRACKING · 廠區使用者只能查看自己送出的樣品狀態與歷程'
              : 'SAMPLE TRACKING · 目前顯示的是仍在此實驗室內的樣品，不只限待收樣'}
          </p>
        </div>

        <div style={headerActionsStyle}>
          {!isFactoryUser && (
            <button onClick={goToTransferPage} style={secondaryButtonStyle}>
              交接流轉
            </button>
          )}
          <button onClick={loadData} style={secondaryButtonStyle}>
            重新整理
          </button>
        </div>
      </div>

      <section style={summaryGridStyle}>
        <SummaryCard label="待收樣" value={pendingReceiveCount} />
        <SummaryCard label="實驗室內" value={inLabCount} />
        <SummaryCard label="待取件" value={outboundCount} />
        <SummaryCard label="已取件" value={pickedUpCount} />
      </section>

      <section style={currentUserBoxStyle}>
        <div style={{ fontWeight: 800 }}>目前操作身分</div>
        <div style={panelHintStyle}>
          {currentUser.role_name ?? currentUser.role} · {currentUser.name} ·{' '}
          {currentUser.lab_name ?? currentUser.department}
        </div>
      </section>

      {error && <div style={errorStyle}>{error}</div>}
      {successMessage && <div style={successStyle}>{successMessage}</div>}

      <section style={panelStyle}>
        <div style={panelHeaderStyle}>
          <div>
            <div style={{ fontWeight: 800 }}>
              {isFactoryUser ? '我的樣品清單' : '樣品清單'}
            </div>
            <div style={panelHintStyle}>
              {isFactoryUser
                ? '只顯示目前使用者送出的樣品。'
                : '只要樣品 current_location 還在目前 Lab，就會顯示在這裡。'}
            </div>
          </div>

          <span style={countBadgeStyle}>{visibleSamples.length} 筆</span>
        </div>

        {loading ? (
          <div style={emptyStyle}>載入中...</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
              <thead>
                <tr style={{ background: 'var(--s2)' }}>
                  {[
                    '樣品編號',
                    '委託單號',
                    '樣品名稱',
                    '實驗需求',
                    '狀態',
                    '目前位置',
                    '操作',
                  ].map((header) => (
                    <th key={header} style={thStyle}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {visibleSamples.map((sample) => {
                  const active = sample.id === selectedSampleId && detailOpen

                  return (
                    <tr
                      key={sample.id}
                      style={{
                        borderBottom: '1px solid rgba(56,139,253,0.08)',
                        background: active ? 'rgba(56,139,253,0.08)' : 'transparent',
                      }}
                    >
                      <td style={monoTdStyle}>{sample.sample_no}</td>
                      <td style={monoTdStyle}>{sample.order_no}</td>
                      <td style={tdStyle}>{sample.sample_name ?? '-'}</td>
                      <td style={tdStyle}>{sample.experiment_item ?? '-'}</td>
                      <td style={tdStyle}>
                        <StatusBadge status={sample.status} />
                      </td>
                      <td style={tdStyle}>{sample.current_location ?? '-'}</td>
                      <td style={tdStyle}>
                        <button onClick={() => openDetail(sample.id)} style={primaryButtonStyle}>
                          查看
                        </button>
                      </td>
                    </tr>
                  )
                })}

                {visibleSamples.length === 0 && (
                  <tr>
                    <td colSpan={7} style={emptyStyle}>
                      目前沒有樣品資料
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {detailOpen && selectedSample && (
        <Modal onClose={closeDetail}>
          <div style={modalHeaderStyle}>
            <div>
              <div style={modalTitleStyle}>{selectedSample.sample_no}</div>
              <div style={modalSubtitleStyle}>
                {selectedSample.order_no} · {selectedSample.sample_name ?? '未命名樣品'}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <StatusBadge status={selectedSample.status} />
              <button onClick={closeDetail} style={iconButtonStyle}>
                ✕
              </button>
            </div>
          </div>

          <div style={modalBodyStyle}>
            <div style={nextStepBoxStyle}>
              <div style={{ fontWeight: 800, marginBottom: 6 }}>下一步判斷</div>
              <div style={{ color: 'var(--text2)', fontSize: 13 }}>
                {getNextStep(selectedSample)}
              </div>
            </div>

            <div style={sectionTitleStyle}>樣品詳細資料</div>

            <div style={detailGridStyle}>
              <InfoItem label="樣品編號" value={selectedSample.sample_no} />
              <InfoItem label="委託單號" value={selectedSample.order_no} />
              <InfoItem label="樣品名稱" value={selectedSample.sample_name ?? '-'} />
              <InfoItem label="實驗需求" value={selectedSample.experiment_item ?? '-'} />
              <InfoItem label="申請人" value={selectedSample.applicant_name ?? '-'} />
              <InfoItem label="申請部門" value={selectedSample.applicant_department ?? '-'} />
              <InfoItem label="目前位置" value={selectedSample.current_location ?? '-'} />
              <InfoItem label="收樣人" value={selectedSample.received_by ?? '尚未收樣'} />
              <InfoItem label="收樣時間" value={formatDateTime(selectedSample.received_at)} />
              <InfoItem label="取件人" value={selectedSample.picked_up_by ?? '尚未取件'} />
              <InfoItem label="取件時間" value={formatDateTime(selectedSample.picked_up_at)} />
              <InfoItem label="備註" value={selectedSample.note ?? '-'} />
            </div>

            <div style={sectionTitleStyle}>此樣品的 WIP / 實驗子單</div>

            {selectedWips.length === 0 ? (
              <div style={miniEmptyStyle}>目前尚未建立 WIP / 實驗子單。</div>
            ) : (
              <div style={labListStyle}>
                {Object.entries(wipsByLab).map(([labName, labWips]) => (
                  <div key={labName} style={labGroupStyle}>
                    <div style={labGroupHeaderStyle}>
                      <span>{labName}</span>
                      <span style={countBadgeStyle}>{labWips.length} 個實驗</span>
                    </div>

                    <div style={wipListStyle}>
                      {labWips.map((wip) => (
                        <div key={wip.id} style={wipCardStyle}>
                          <div>
                            <div style={{ fontWeight: 800, fontSize: 13 }}>
                              {wip.experiment_item ?? '未命名實驗'}
                            </div>
                            <div style={{ color: 'var(--text3)', fontSize: 11, marginTop: 4 }}>
                              {wip.wip_no} · 優先級：
                              {priorityText[wip.priority] ?? wip.priority}
                            </div>
                          </div>

                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: 12, fontWeight: 700 }}>
                              {wipStatusText[wip.status] ?? wip.status}
                            </div>
                            <div style={{ color: 'var(--text3)', fontSize: 11, marginTop: 4 }}>
                              進度 {wip.progress}% · {wip.current_location ?? '-'}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div style={sectionTitleStyle}>樣品歷程紀錄</div>

            {historyLoading ? (
              <div style={miniEmptyStyle}>歷程載入中...</div>
            ) : sampleHistories.length === 0 ? (
              <div style={miniEmptyStyle}>目前尚無歷程紀錄。</div>
            ) : (
              <div style={timelineStyle}>
                {sampleHistories.map((history) => (
                  <div key={history.id} style={timelineItemStyle}>
                    <div style={timelineDotStyle} />

                    <div style={{ flex: 1 }}>
                      <div style={timelineTopRowStyle}>
                        <div style={{ fontWeight: 800, fontSize: 13 }}>
                          {history.description ?? history.action}
                        </div>

                        <div style={timelineTimeStyle}>
                          {formatDateTime(history.created_at)}
                        </div>
                      </div>

                      <div style={timelineMetaStyle}>
                        {formatStatusChange(history.from_status, history.to_status)}
                        {' · '}
                        {history.operator_name ?? '系統'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div style={sectionTitleStyle}>
              {isFactoryUser ? '查看權限' : '可執行動作'}
            </div>

            {isFactoryUser ? (
              <div style={miniEmptyStyle}>
                廠區使用者只能查看自己送出的樣品詳細資料、WIP 進度與歷程紀錄，不能在收樣管理執行收樣、分貨、通知取件或確認取件。
              </div>
            ) : (
              <div style={actionBarStyle}>
                {selectedSample.status === 'pending_receive' && (
                  <button
                    onClick={() => runSampleAction(selectedSample.id, 'receive')}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    確認收樣
                  </button>
                )}

                {selectedSample.status === 'received' && (
                  <button
                    onClick={() => goToWipPage(selectedSample.id)}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    前往 WIP / 分貨
                  </button>
                )}

                {selectedSample.status === 'split' && (
                  <button
                    onClick={() => goToWipPage(selectedSample.id)}
                    disabled={submitting}
                    style={secondaryButtonStyle}
                  >
                    查看 / 管理 WIP
                  </button>
                )}

                {selectedSample.status === 'split' && allWipsCompleted && (
                  <button
                    onClick={() => runSampleAction(selectedSample.id, 'outbound')}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    通知取件 / 移至待取件區
                  </button>
                )}

                {selectedSample.status === 'outbound' && (
                  <button
                    onClick={() => runSampleAction(selectedSample.id, 'pickup_confirmed')}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    確認廠區已取件
                  </button>
                )}

                {selectedSample.status === 'transferring' && (
                  <button
                    onClick={goToTransferPage}
                    disabled={submitting}
                    style={secondaryButtonStyle}
                  >
                    前往交接流轉
                  </button>
                )}

                {!['pending_receive', 'received', 'split', 'outbound', 'transferring'].includes(
                  selectedSample.status,
                ) && <div style={miniEmptyStyle}>目前沒有可執行動作。</div>}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={summaryCardStyle}>
      <div style={summaryValueStyle}>{value}</div>
      <div style={summaryLabelStyle}>{label}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  return <span style={statusBadgeStyle}>{sampleStatusText[status] ?? status}</span>
}

function InfoItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div style={infoItemStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value}</div>
    </div>
  )
}

function Modal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div style={modalBackdropStyle}>
      <div style={modalCardStyle}>{children}</div>
      <button style={modalBackdropButtonStyle} onClick={onClose} aria-label="close" />
    </div>
  )
}

function formatDateTime(value: string | null) {
  if (!value) return '-'

  try {
    return new Date(value).toLocaleString('zh-TW', {
      hour12: false,
    })
  } catch {
    return value
  }
}

function formatStatusChange(fromStatus: string | null, toStatus: string | null) {
  if (!fromStatus && !toStatus) return '狀態未變更'

  const fromText = fromStatus ? sampleStatusText[fromStatus] ?? fromStatus : '無'
  const toText = toStatus ? sampleStatusText[toStatus] ?? toStatus : '無'

  return `${fromText} → ${toText}`
}

const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 16,
  alignItems: 'flex-start',
  marginBottom: 16,
}

const headerActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
}

const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
  fontWeight: 800,
}

const subtitleStyle: CSSProperties = {
  marginTop: 6,
  color: 'var(--text3)',
  fontSize: 13,
}

const summaryGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 12,
  marginBottom: 14,
}

const summaryCardStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
}

const summaryValueStyle: CSSProperties = {
  fontSize: 22,
  fontWeight: 900,
}

const summaryLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

const currentUserBoxStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
  marginBottom: 14,
}

const panelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 16,
  marginBottom: 16,
}

const panelHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 12,
  gap: 12,
}

const panelHintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

const countBadgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'rgba(56,139,253,0.14)',
  color: 'var(--blue)',
  border: '1px solid rgba(56,139,253,0.35)',
  borderRadius: 999,
  padding: '3px 8px',
  fontSize: 11,
  fontWeight: 800,
}

const tableStyle: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
}

const thStyle: CSSProperties = {
  textAlign: 'left',
  color: 'var(--text3)',
  fontSize: 11,
  padding: '10px 12px',
  whiteSpace: 'nowrap',
}

const tdStyle: CSSProperties = {
  padding: '11px 12px',
  fontSize: 12.5,
  color: 'var(--text2)',
  whiteSpace: 'nowrap',
}

const monoTdStyle: CSSProperties = {
  ...tdStyle,
  fontFamily: 'monospace',
  color: 'var(--text)',
}

const emptyStyle: CSSProperties = {
  textAlign: 'center',
  color: 'var(--text3)',
  padding: 28,
  fontSize: 13,
}

const miniEmptyStyle: CSSProperties = {
  background: 'var(--s2)',
  color: 'var(--text3)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
  fontSize: 13,
}

const primaryButtonStyle: CSSProperties = {
  background: 'var(--blue)',
  border: '1px solid var(--blue)',
  color: '#fff',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 12,
}

const secondaryButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 12,
}

const iconButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 10,
  width: 34,
  height: 34,
  cursor: 'pointer',
}

const errorStyle: CSSProperties = {
  background: 'rgba(247,129,102,0.12)',
  border: '1px solid rgba(247,129,102,0.25)',
  color: 'var(--orange)',
  borderRadius: 10,
  padding: 12,
  fontSize: 13,
  marginBottom: 12,
}

const successStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.25)',
  color: 'var(--green)',
  borderRadius: 10,
  padding: 12,
  fontSize: 13,
  marginBottom: 12,
}

const statusBadgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  borderRadius: 999,
  padding: '4px 9px',
  fontSize: 11,
  fontWeight: 800,
  background: 'rgba(56,139,253,0.14)',
  color: 'var(--blue)',
  border: '1px solid rgba(56,139,253,0.35)',
  whiteSpace: 'nowrap',
}

const modalBackdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 50,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 20,
  background: 'rgba(0,0,0,0.55)',
}

const modalBackdropButtonStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: -1,
  opacity: 0,
}

const modalCardStyle: CSSProperties = {
  width: 'min(1080px, 96vw)',
  maxHeight: '90vh',
  overflowY: 'auto',
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 18,
  boxShadow: '0 20px 70px rgba(0,0,0,0.35)',
}

const modalHeaderStyle: CSSProperties = {
  position: 'sticky',
  top: 0,
  background: 'var(--s1)',
  borderBottom: '1px solid var(--border2)',
  padding: 18,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 16,
  zIndex: 1,
}

const modalTitleStyle: CSSProperties = {
  fontSize: 20,
  fontWeight: 900,
}

const modalSubtitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

const modalBodyStyle: CSSProperties = {
  padding: 18,
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
}

const nextStepBoxStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  borderRadius: 12,
  padding: 14,
}

const sectionTitleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 900,
  marginTop: 2,
}

const detailGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 10,
}

const infoItemStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
}

const infoLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginBottom: 6,
}

const infoValueStyle: CSSProperties = {
  color: 'var(--text)',
  fontSize: 13,
  fontWeight: 700,
  wordBreak: 'break-word',
}

const labListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

const labGroupStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

const labGroupHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  fontWeight: 900,
  marginBottom: 10,
}

const wipListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const wipCardStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
}

const timelineStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const timelineItemStyle: CSSProperties = {
  display: 'flex',
  gap: 10,
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

const timelineDotStyle: CSSProperties = {
  width: 9,
  height: 9,
  borderRadius: 99,
  background: 'var(--blue)',
  marginTop: 4,
  flexShrink: 0,
}

const timelineTopRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
}

const timelineTimeStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  whiteSpace: 'nowrap',
}

const timelineMetaStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
}

const actionBarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
}