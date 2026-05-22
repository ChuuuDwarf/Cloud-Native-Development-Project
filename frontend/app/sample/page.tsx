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

type Transfer = {
  id: string
  transfer_no: string
  target_type: 'sample' | 'wip'
  target_id: string
  order_no: string | null
  sample_no: string | null
  wip_no: string | null
  from_lab: string | null
  to_lab: string | null
  handed_by: string | null
  received_by: string | null
  status: string
  transferred_at: string | null
  received_at: string | null
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
  lab_name?: string | null
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

type SampleFilter = 'current' | 'active' | 'outbound' | 'picked_up' | 'all'

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
  approved: '已核准 / 未送樣',
  pending_receive: '待收樣',
  received: '已收樣',
  split: '已分貨',
  transferring: '交接中',
  transfer_pending: '交接待送出',
  transferred_waiting_receive: '已轉出 / 等待接收實驗室收樣',
  transferred_received: '已被接收實驗室收樣',
  transferred_out: '已轉出 / 後續由接收實驗室處理',
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

function isActiveSampleStatus(status: string) {
  return ['pending_receive', 'received', 'split', 'transferring', 'in_storage'].includes(status)
}

function isSampleInCurrentLab(sample: Sample | null, user: CurrentUser) {
  if (!sample) return false

  if (user.role === 'system_admin') return true

  if (user.role !== 'lab_staff' && user.role !== 'lab_supervisor') {
    return false
  }

  const currentLab = getUserLab(user)
  const currentLocation = sample.current_location ?? ''

  return Boolean(currentLab && currentLocation.startsWith(currentLab))
}

function shouldMaskSampleForLab(sample: Sample, user: CurrentUser) {
  if (user.role === 'factory_user' || user.role === 'system_admin') {
    return false
  }

  if (user.role !== 'lab_staff' && user.role !== 'lab_supervisor') {
    return false
  }

  return !isSampleInCurrentLab(sample, user)
}

function getDisplaySampleStatus(
  sample: Sample,
  user: CurrentUser,
  outgoingTransfer?: Transfer,
) {
  if (!shouldMaskSampleForLab(sample, user)) {
    return sample.status
  }

  if (outgoingTransfer?.status === 'pending') {
    return 'transfer_pending'
  }

  if (outgoingTransfer?.status === 'transferring') {
    return 'transferred_waiting_receive'
  }

  if (outgoingTransfer?.status === 'received') {
    return 'transferred_received'
  }

  if (outgoingTransfer?.status === 'cancelled') {
    return 'cancelled'
  }

  if (sample.status === 'cancelled') return 'cancelled'
  if (sample.status === 'lost') return 'lost'
  if (sample.status === 'damaged') return 'damaged'

  return 'transferred_out'
}

function getDisplaySampleLocation(
  sample: Sample,
  user: CurrentUser,
  outgoingTransfer?: Transfer,
) {
  if (!shouldMaskSampleForLab(sample, user)) {
    return sample.current_location ?? '-'
  }

  const receiverLabText = outgoingTransfer?.to_lab
    ? `接收實驗室（${outgoingTransfer.to_lab}）`
    : '接收實驗室'

  if (outgoingTransfer?.status === 'pending') {
    return '本實驗室交接待送區'
  }

  if (outgoingTransfer?.status === 'transferring') {
    return `已送出，等待${receiverLabText}收樣`
  }

  if (outgoingTransfer?.status === 'received') {
    return `已由${receiverLabText}收樣`
  }

  if (outgoingTransfer?.status === 'cancelled') {
    return '交接已取消'
  }

  if (sample.status === 'cancelled') return '流程已取消'
  if (sample.status === 'lost') return '樣品異常：遺失'
  if (sample.status === 'damaged') return '樣品異常：破損'

  return '已離開本實驗室'
}

function isSampleVisibleForUser(sample: Sample, user: CurrentUser) {
  if (user.role === 'system_admin') return true

  if (user.role === 'factory_user') {
    return sample.applicant_name === user.name
  }

  if (user.role === 'lab_staff' || user.role === 'lab_supervisor') {
    return true
  }

  return false
}

function filterSamplesByView(samples: Sample[], currentUser: CurrentUser, filter: SampleFilter) {
  const visibleBase = samples.filter((sample) => isSampleVisibleForUser(sample, currentUser))

  if (currentUser.role === 'factory_user') {
    if (filter === 'active' || filter === 'current') {
      return visibleBase.filter((sample) => isActiveSampleStatus(sample.status))
    }

    if (filter === 'outbound') {
      return visibleBase.filter((sample) => sample.status === 'outbound')
    }

    if (filter === 'picked_up') {
      return visibleBase.filter((sample) => sample.status === 'picked_up')
    }

    return visibleBase
  }

  if (currentUser.role === 'lab_staff' || currentUser.role === 'lab_supervisor') {
    const currentLab = getUserLab(currentUser)

    if (filter === 'current') {
      return visibleBase.filter((sample) => {
        const location = sample.current_location ?? ''
        return currentLab && location.startsWith(currentLab) && sample.status !== 'picked_up'
      })
    }

    if (filter === 'active') {
      return visibleBase.filter((sample) => isActiveSampleStatus(sample.status))
    }

    if (filter === 'outbound') {
      return visibleBase.filter((sample) => {
        if (sample.status !== 'outbound') return false

        const currentLabName = getUserLab(currentUser)
        const location = sample.current_location ?? ''

        return Boolean(currentLabName && location.startsWith(currentLabName))
      })
    }

    if (filter === 'picked_up') {
      return visibleBase.filter((sample) => sample.status === 'picked_up')
    }

    return visibleBase
  }

  return visibleBase
}

export default function SamplePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser>(fallbackUser)
  const [samples, setSamples] = useState<Sample[]>([])
  const [wips, setWips] = useState<Wip[]>([])
  const [transfers, setTransfers] = useState<Transfer[]>([])
  const [sampleHistories, setSampleHistories] = useState<SampleHistory[]>([])
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyVisibleCount, setHistoryVisibleCount] = useState(5)
  const [submitting, setSubmitting] = useState(false)
  const [sampleFilter, setSampleFilter] = useState<SampleFilter>('current')
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const isFactoryUser = currentUser.role === 'factory_user'
  const operatorName = currentUser.name || fallbackUser.name

  const outgoingTransfersBySampleId = useMemo(() => {
    const map = new Map<string, Transfer>()

    transfers
      .filter((transfer) => transfer.target_type === 'sample')
      .forEach((transfer) => {
        const existing = map.get(transfer.target_id)

        if (!existing) {
          map.set(transfer.target_id, transfer)
          return
        }

        const existingTime = new Date(existing.updated_at ?? existing.created_at).getTime()
        const nextTime = new Date(transfer.updated_at ?? transfer.created_at).getTime()

        if (nextTime > existingTime) {
          map.set(transfer.target_id, transfer)
        }
      })

    return map
  }, [transfers])

  const filterOptions = useMemo(() => {
    if (isFactoryUser) {
      return [
        { value: 'all', label: '全部' },
        { value: 'active', label: '進行中' },
        { value: 'outbound', label: '待取件' },
        { value: 'picked_up', label: '已取件' },
      ] as Array<{ value: SampleFilter; label: string }>
    }

    return [
      { value: 'current', label: '目前在本 Lab' },
      { value: 'outbound', label: '待取件' },
      { value: 'picked_up', label: '已取件紀錄' },
      { value: 'all', label: '全部紀錄' },
    ] as Array<{ value: SampleFilter; label: string }>
  }, [isFactoryUser])

  const visibleSamples = useMemo(() => {
    return filterSamplesByView(samples, currentUser, sampleFilter)
  }, [samples, currentUser, sampleFilter])

  const selectedSample = useMemo(() => {
    return visibleSamples.find((sample) => sample.id === selectedSampleId) ?? null
  }, [visibleSamples, selectedSampleId])

  const selectedSampleInCurrentLab = useMemo(() => {
    return isSampleInCurrentLab(selectedSample, currentUser)
  }, [selectedSample, currentUser])

  const selectedSampleOutgoingTransfer = useMemo(() => {
    if (!selectedSample) return undefined
    return outgoingTransfersBySampleId.get(selectedSample.id)
  }, [selectedSample, outgoingTransfersBySampleId])

  const selectedWips = useMemo(() => {
    if (!selectedSample) return []
    return wips.filter((wip) => wip.sample_id === selectedSample.id)
  }, [wips, selectedSample])

  const visibleSelectedWips = useMemo(() => {
    if (!selectedSample) return []

    if (currentUser.role === 'system_admin' || currentUser.role === 'factory_user') {
      return selectedWips
    }

    if (currentUser.role === 'lab_supervisor') {
      return selectedWips
    }

    if (currentUser.role === 'lab_staff') {
      const currentLab = getUserLab(currentUser)
      return selectedWips.filter((wip) => wip.lab_name === currentLab)
    }

    return []
  }, [selectedWips, selectedSample, currentUser])

  const wipsByLab = useMemo(() => {
    return visibleSelectedWips.reduce<Record<string, Wip[]>>((groups, wip) => {
      const labName = wip.lab_name ?? '未指定實驗室'

      if (!groups[labName]) {
        groups[labName] = []
      }

      groups[labName].push(wip)
      return groups
    }, {})
  }, [visibleSelectedWips])

  const allWipsCompleted =
    selectedWips.length > 0 &&
    selectedWips.every((wip) => wip.status === 'completed')

  const baseSamplesForCount = useMemo(() => {
    return samples.filter((sample) => isSampleVisibleForUser(sample, currentUser))
  }, [samples, currentUser])

  const pendingReceiveCount = baseSamplesForCount.filter(
    (sample) => sample.status === 'pending_receive',
  ).length

  const inLabCount = baseSamplesForCount.filter((sample) =>
    ['received', 'split', 'transferring', 'in_storage'].includes(sample.status),
  ).length

  const outboundCount = baseSamplesForCount.filter(
    (sample) => sample.status === 'outbound',
  ).length

  const pickedUpCount = baseSamplesForCount.filter(
    (sample) => sample.status === 'picked_up',
  ).length

  const visibleHistories = sampleHistories.slice(0, historyVisibleCount)

  const canFactoryConfirmPickup =
    Boolean(selectedSample) &&
    isFactoryUser &&
    selectedSample?.status === 'outbound' &&
    selectedSample?.applicant_name === currentUser.name

  const shouldShowFactoryAction = canFactoryConfirmPickup

  const shouldShowLabActions =
    Boolean(selectedSample) &&
    !isFactoryUser &&
    selectedSampleInCurrentLab &&
    (
      selectedSample?.status === 'pending_receive' ||
      selectedSample?.status === 'received' ||
      selectedSample?.status === 'transferring' ||
      selectedSample?.status === 'split'
    )

  const shouldShowActionSection = shouldShowFactoryAction || shouldShowLabActions

  async function loadCurrentUser() {
    try {
      const me = await apiGet<CurrentUser>('/api/me')
      setCurrentUser(me)

      if (me.role === 'factory_user') {
        setSampleFilter((prev) => (prev === 'current' ? 'all' : prev))
      } else {
        setSampleFilter((prev) => (prev === 'active' ? 'current' : prev))
      }

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

      const [sampleData, wipData, transferData] = await Promise.all([
        apiGet<Sample[]>('/api/samples?scope=all'),
        apiGet<Wip[]>('/api/wips?include_all_for_flow=true'),
        apiGet<Transfer[]>('/api/transfers'),
      ])

      const filteredSamples = filterSamplesByView(sampleData, meData, sampleFilter)

      setCurrentUser(meData)
      setSamples(sampleData)
      setWips(wipData)
      setTransfers(transferData)

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
    setHistoryVisibleCount(5)
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
    const targetSample = samples.find((sample) => sample.id === sampleId) ?? null

    const isFactoryPickup =
      isFactoryUser &&
      action === 'pickup_confirmed' &&
      targetSample?.status === 'outbound' &&
      targetSample.applicant_name === currentUser.name

    const isLabOperationAllowed =
      !isFactoryUser && isSampleInCurrentLab(targetSample, currentUser)

    if (!isLabOperationAllowed && !isFactoryPickup) {
      setError('只能操作目前位於自己 Lab 內的樣品；歷史紀錄只能查看，不能處理')
      return
    }

    if (isFactoryUser && action !== 'pickup_confirmed') {
      setError('廠區使用者不能執行收樣、分貨或通知取件')
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
        body.current_location = '已由使用者取回'
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
        return '實驗已完成，樣品等待取回。實際拿到樣品後，可以確認取件。'
      }

      if (sample.status === 'picked_up') {
        return '樣品已取回，流程完成。'
      }

      return '目前僅提供樣品狀態與歷程查詢。'
    }

    if (!isSampleInCurrentLab(sample, currentUser)) {
      const transfer = outgoingTransfersBySampleId.get(sample.id)

      if (transfer?.status === 'received') {
        return '此樣品已被接收實驗室收樣。你只能查看本實驗室的交接紀錄，不能查看接收實驗室後續處理狀態，也不能執行操作。'
      }

      if (transfer?.status === 'transferring') {
        return '此樣品已送出，等待接收實驗室確認收樣。'
      }

      if (transfer?.status === 'pending') {
        return '此樣品已有交接單，尚未送出。'
      }

      return '此樣品已離開你的實驗室。本畫面只保留你所屬 Lab 的歷程紀錄與交接確認結果，不能查看對方 Lab 的後續狀態，也不能執行操作。'
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
      return '樣品已由原使用者取回，流程完成。此筆會保留在已取件紀錄。'
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
            {isFactoryUser ? '我的樣品追蹤' : '收樣與樣品追蹤'}
          </h1>
          <p style={subtitleStyle}>
            {isFactoryUser
              ? 'SAMPLE TRACKING · 廠區使用者可查看自己已送樣後的樣品狀態、待取件與已取件紀錄'
              : 'SAMPLE TRACKING · 預設顯示目前仍在本 Lab 的樣品，也可切換查看待取件與歷史紀錄'}
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
                ? '可切換進行中、待取件、已取件與全部紀錄。'
                : '預設看目前仍在本 Lab 的樣品；轉交後只顯示交接狀態，不顯示接收實驗室後續細節。'}
            </div>
          </div>

          <span style={countBadgeStyle}>{visibleSamples.length} 筆</span>
        </div>

        <div style={filterBarStyle}>
          {filterOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                setSampleFilter(option.value)
                setSelectedSampleId(null)
                setDetailOpen(false)
                setSampleHistories([])
              }}
              style={sampleFilter === option.value ? activeFilterButtonStyle : filterButtonStyle}
            >
              {option.label}
            </button>
          ))}
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
                  const canCurrentUserOperateThisSample = isSampleInCurrentLab(sample, currentUser)
                  const outgoingTransfer = outgoingTransfersBySampleId.get(sample.id)
                  const displayStatus = getDisplaySampleStatus(sample, currentUser, outgoingTransfer)
                  const displayLocation = getDisplaySampleLocation(sample, currentUser, outgoingTransfer)

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
                        <StatusBadge status={displayStatus} />
                      </td>
                      <td style={tdStyle}>
                        <div>{displayLocation}</div>
                        {!isFactoryUser && !canCurrentUserOperateThisSample && (
                          <div style={readonlyHintStyle}>歷史紀錄 / 只可查看</div>
                        )}
                      </td>
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
              <StatusBadge
                status={getDisplaySampleStatus(
                  selectedSample,
                  currentUser,
                  selectedSampleOutgoingTransfer,
                )}
              />
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
              <InfoItem
                label="目前位置"
                value={getDisplaySampleLocation(
                  selectedSample,
                  currentUser,
                  selectedSampleOutgoingTransfer,
                )}
              />
              <InfoItem label="收樣人" value={selectedSample.received_by ?? '尚未收樣'} />
              <InfoItem label="收樣時間" value={formatDateTime(selectedSample.received_at)} />
              <InfoItem label="取件人" value={selectedSample.picked_up_by ?? '尚未取件'} />
              <InfoItem label="取件時間" value={formatDateTime(selectedSample.picked_up_at)} />
              <InfoItem label="備註" value={selectedSample.note ?? '-'} />
            </div>

            <div style={sectionTitleStyle}>此樣品的 WIP / 實驗子單</div>

            {visibleSelectedWips.length === 0 ? (
              <div style={miniEmptyStyle}>
                {shouldMaskSampleForLab(selectedSample, currentUser)
                  ? '此樣品已轉出，本畫面不顯示接收實驗室的 WIP / 實驗子單細節。'
                  : '目前尚未建立 WIP / 實驗子單。'}
              </div>
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
              <div style={miniEmptyStyle}>目前尚無可查看的歷程紀錄。</div>
            ) : (
              <>
                <div style={timelineStyle}>
                  {visibleHistories.map((history) => (
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
                          {history.lab_name ? ` · ${history.lab_name}` : ''}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div style={historyActionRowStyle}>
                  {sampleHistories.length > historyVisibleCount && (
                    <button
                      type="button"
                      onClick={() => setHistoryVisibleCount((count) => count + 5)}
                      style={secondaryButtonStyle}
                    >
                      查看更多歷程（還有 {sampleHistories.length - historyVisibleCount} 筆）
                    </button>
                  )}

                  {sampleHistories.length > 5 &&
                    historyVisibleCount >= sampleHistories.length && (
                      <button
                        type="button"
                        onClick={() => setHistoryVisibleCount(5)}
                        style={secondaryButtonStyle}
                      >
                        收合歷程
                      </button>
                    )}
                </div>
              </>
            )}

            {shouldShowActionSection && (
              <>
                <div style={sectionTitleStyle}>
                  {isFactoryUser ? '確認取件' : '可執行動作'}
                </div>

                <div style={actionBarStyle}>
                  {canFactoryConfirmPickup && (
                    <button
                      onClick={() => runSampleAction(selectedSample.id, 'pickup_confirmed')}
                      disabled={submitting}
                      style={primaryButtonStyle}
                    >
                      我已到待取件區取回樣品，確認取件
                    </button>
                  )}

                  {!isFactoryUser &&
                    selectedSampleInCurrentLab &&
                    selectedSample.status === 'pending_receive' && (
                      <button
                        onClick={() => runSampleAction(selectedSample.id, 'receive')}
                        disabled={submitting}
                        style={primaryButtonStyle}
                      >
                        確認收樣
                      </button>
                    )}

                  {!isFactoryUser &&
                    selectedSampleInCurrentLab &&
                    selectedSample.status === 'received' && (
                      <button
                        onClick={() => goToWipPage(selectedSample.id)}
                        disabled={submitting}
                        style={primaryButtonStyle}
                      >
                        前往 WIP / 分貨
                      </button>
                    )}

                  {!isFactoryUser &&
                    selectedSampleInCurrentLab &&
                    selectedSample.status === 'split' && (
                      <button
                        onClick={() => goToWipPage(selectedSample.id)}
                        disabled={submitting}
                        style={secondaryButtonStyle}
                      >
                        查看 / 管理 WIP
                      </button>
                    )}

                  {!isFactoryUser &&
                    selectedSampleInCurrentLab &&
                    selectedSample.status === 'split' &&
                    allWipsCompleted && (
                      <button
                        onClick={() => runSampleAction(selectedSample.id, 'outbound')}
                        disabled={submitting}
                        style={primaryButtonStyle}
                      >
                        通知取件 / 移至待取件區
                      </button>
                    )}

                  {!isFactoryUser &&
                    selectedSampleInCurrentLab &&
                    selectedSample.status === 'transferring' && (
                      <button
                        onClick={goToTransferPage}
                        disabled={submitting}
                        style={secondaryButtonStyle}
                      >
                        前往交接流轉
                      </button>
                    )}
                </div>
              </>
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

const filterBarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  marginBottom: 12,
}

const filterButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 999,
  padding: '7px 11px',
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 800,
}

const activeFilterButtonStyle: CSSProperties = {
  ...filterButtonStyle,
  background: 'rgba(56,139,253,0.16)',
  color: 'var(--blue)',
  borderColor: 'rgba(56,139,253,0.55)',
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

const readonlyHintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
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

const historyActionRowStyle: CSSProperties = {
  display: 'flex',
  gap: 10,
  flexWrap: 'wrap',
}

const actionBarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
}