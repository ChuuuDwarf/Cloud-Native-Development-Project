'use client'

import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '@/lib/api'
import { fallbackUser } from './constants'
import type { CurrentUser, Sample, SampleAction, SampleFilter, SampleHistory, Transfer, Wip } from './types'
import { SampleDetailModal } from './components/SampleDetailModal'
import { SampleTable } from './components/SampleTable'
import { SummaryCard } from './components/SummaryCard'
import {
  getFilterButtonStyle,
  countBadgeStyle,
  currentUserBoxStyle,
  errorStyle,
  filterBarStyle,
  headerActionsStyle,
  headerStyle,
  panelHeaderStyle,
  panelHintStyle,
  panelStyle,
  secondaryButtonStyle,
  subtitleStyle,
  successStyle,
  summaryGridStyle,
  titleStyle,
} from './styles'
import {
  filterSamplesByView,
  getUserLab,
  isActiveSampleStatus,
  isSampleInCurrentLab,
  isSampleVisibleForUser,
} from './utils/sampleDisplay'

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

  const allWipsCompleted = selectedWips.length > 0 && selectedWips.every((wip) => wip.status === 'completed')

  const baseSamplesForCount = useMemo(() => {
    return samples.filter((sample) => isSampleVisibleForUser(sample, currentUser))
  }, [samples, currentUser])

  const pendingReceiveCount = baseSamplesForCount.filter((sample) => {
    if (sample.status !== 'pending_receive') return false

    if (currentUser.role === 'lab_staff' || currentUser.role === 'lab_supervisor') {
      return isSampleInCurrentLab(sample, currentUser)
    }

    return true
  }).length

  const inLabCount = baseSamplesForCount.filter((sample) => {
    if (!['received', 'split', 'transferring', 'in_storage'].includes(sample.status)) {
      return false
    }

    if (currentUser.role === 'lab_staff' || currentUser.role === 'lab_supervisor') {
      return isSampleInCurrentLab(sample, currentUser)
    }

    return true
  }).length

  const outboundCount = baseSamplesForCount.filter((sample) => {
    if (sample.status !== 'outbound') return false

    if (currentUser.role === 'lab_staff' || currentUser.role === 'lab_supervisor') {
      return isSampleInCurrentLab(sample, currentUser)
    }

    return true
  }).length

  const pickedUpCount = baseSamplesForCount.filter((sample) => sample.status === 'picked_up').length
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
    (selectedSample?.status === 'pending_receive' ||
      selectedSample?.status === 'received' ||
      selectedSample?.status === 'transferring' ||
      selectedSample?.status === 'split')

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

  async function runSampleAction(sampleId: string, action: SampleAction) {
    const targetSample = samples.find((sample) => sample.id === sampleId) ?? null

    const isFactoryPickup =
      isFactoryUser &&
      action === 'pickup_confirmed' &&
      targetSample?.status === 'outbound' &&
      targetSample.applicant_name === currentUser.name

    const isLabOperationAllowed = !isFactoryUser && isSampleInCurrentLab(targetSample, currentUser)

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
      if (sample.status === 'pending_receive') return '樣品已送出，等待實驗室確認收樣。'
      if (sample.status === 'received') return '實驗室已收樣，等待建立或執行實驗子單。'
      if (sample.status === 'split') return '樣品已進入實驗流程，可在此追蹤 WIP / 實驗子單進度。'
      if (sample.status === 'outbound') return '實驗已完成，樣品等待取回。實際拿到樣品後，可以確認取件。'
      if (sample.status === 'picked_up') return '樣品已取回，流程完成。'
      return '目前僅提供樣品狀態與歷程查詢。'
    }

    if (!isSampleInCurrentLab(sample, currentUser)) {
      const transfer = outgoingTransfersBySampleId.get(sample.id)

      if (transfer?.status === 'received') {
        return '此樣品已被接收實驗室收樣。你只能查看本實驗室的交接紀錄，不能查看接收實驗室後續處理狀態，也不能執行操作。'
      }

      if (transfer?.status === 'transferring') return '此樣品已送出，等待接收實驗室確認收樣。'
      if (transfer?.status === 'pending') return '此樣品已有交接單，尚未送出。'
      return '此樣品已離開你的實驗室。本畫面只保留你所屬 Lab 的歷程紀錄與交接確認結果，不能查看對方 Lab 的後續狀態，也不能執行操作。'
    }

    if (sample.status === 'pending_receive') return '樣品尚未完成收樣，下一步是確認收樣。'
    if (sample.status === 'received') return '樣品已完成收樣，下一步請前往 WIP / 分貨管理建立實驗子單。'
    if (sample.status === 'split' && selectedWips.length === 0) return '樣品已標記分貨，但目前沒有 WIP，請確認後端資料是否已建立實驗子單。'
    if (sample.status === 'split' && selectedWips.length > 0 && !allWipsCompleted) {
      return '樣品已有 WIP / 實驗子單，請依實驗室分組追蹤各實驗進度。若某實驗室完成且還有下一實驗室，請至交接流轉頁處理。'
    }
    if (sample.status === 'split' && allWipsCompleted) return '所有實驗已完成，可通知原使用者取件，並將樣品移至待取件區。'
    if (sample.status === 'transferring') return '樣品正在跨實驗室交接中，等待下一個實驗室簽收。'
    if (sample.status === 'outbound') return '已通知原使用者取件，樣品目前在待取件區。'
    if (sample.status === 'picked_up') return '樣品已由原使用者取回，流程完成。此筆會保留在已取件紀錄。'
    if (sample.status === 'in_storage') return '樣品目前已入庫保存。若不做倉儲流程，後續可改為直接通知取件。'

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
          <h1 style={titleStyle}>{isFactoryUser ? '我的樣品追蹤' : '收樣與樣品追蹤'}</h1>
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
            <div style={{ fontWeight: 800 }}>{isFactoryUser ? '我的樣品清單' : '樣品清單'}</div>
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
              style={getFilterButtonStyle(sampleFilter === option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>

        <SampleTable
          loading={loading}
          samples={visibleSamples}
          selectedSampleId={selectedSampleId}
          detailOpen={detailOpen}
          currentUser={currentUser}
          outgoingTransfersBySampleId={outgoingTransfersBySampleId}
          onOpenDetail={openDetail}
        />
      </section>

      {detailOpen && selectedSample && (
        <SampleDetailModal
          sample={selectedSample}
          currentUser={currentUser}
          selectedSampleOutgoingTransfer={selectedSampleOutgoingTransfer}
          visibleSelectedWips={visibleSelectedWips}
          wipsByLab={wipsByLab}
          sampleHistories={sampleHistories}
          visibleHistories={visibleHistories}
          historyLoading={historyLoading}
          historyVisibleCount={historyVisibleCount}
          submitting={submitting}
          canFactoryConfirmPickup={canFactoryConfirmPickup}
          selectedSampleInCurrentLab={selectedSampleInCurrentLab}
          allWipsCompleted={allWipsCompleted}
          shouldShowActionSection={shouldShowActionSection}
          isFactoryUser={isFactoryUser}
          nextStepText={getNextStep(selectedSample)}
          onClose={closeDetail}
          onShowMoreHistory={() => setHistoryVisibleCount((count) => count + 5)}
          onCollapseHistory={() => setHistoryVisibleCount(5)}
          onRunSampleAction={runSampleAction}
          onGoToWipPage={goToWipPage}
          onGoToTransferPage={goToTransferPage}
        />
      )}
    </div>
  )
}
