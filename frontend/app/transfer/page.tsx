'use client'

import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties } from 'react'
import { apiGet, apiPost } from '@/lib/api'

type CurrentUser = {
  id: string
  name: string
  role: string
  role_name?: string
  department: string
  lab_name?: string | null
  email?: string
}

type RequestedExperiment = {
  lab_name: string
  experiment_item: string
}

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
  storage_location_id?: string | null
  received_at?: string | null
  received_by?: string | null
  picked_up_at?: string | null
  picked_up_by?: string | null
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
  scheduled_at?: string | null
  dispatched_at?: string | null
  started_at?: string | null
  completed_at?: string | null
  terminated_at?: string | null
  note: string | null
  created_at: string
  updated_at: string
}

type Transfer = {
  id: string
  transfer_no: string | null
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

type TransferCandidate = {
  kind: 'transfer'
  sample: Sample
  currentLabCompletedWips: Wip[]
  remainingWips: Wip[]
  remainingExperiments: RequestedExperiment[]
  nextLab: string
  nextExperiment: RequestedExperiment
  nextWip: Wip | null
  existingTransfer: Transfer | null
}

type ReturnCandidate = {
  kind: 'return'
  sample: Sample
  currentLabCompletedWips: Wip[]
  allWips: Wip[]
}

type Candidate = TransferCandidate | ReturnCandidate

const fallbackUser: CurrentUser = {
  id: 'fallback',
  name: '張志明',
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

const transferStatusText: Record<string, string> = {
  pending: '待送出',
  transferring: '已送出 / 待對方收樣',
  received: '已簽收',
  cancelled: '已取消',
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

const blockingTransferStatuses = ['pending', 'transferring']

function normalizeLab(value: string | null | undefined) {
  return (value ?? '').trim().toLowerCase()
}

function normalizeExperiment(value: string | null | undefined) {
  return (value ?? '').trim().toLowerCase()
}

function safeParseSampleNote(note: string | null) {
  if (!note) return null

  try {
    const parsed = JSON.parse(note)

    if (!parsed || typeof parsed !== 'object') return null

    return parsed as {
      requested_experiments?: RequestedExperiment[]
      priority?: string
      sample_quantity?: string
      source?: string
    }
  } catch {
    return null
  }
}

function parseExperimentsFromSummary(summary: string | null): RequestedExperiment[] {
  if (!summary) return []

  return summary
    .split('、')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [labName, ...rest] = part.split(':')
      const experimentItem = rest.join(':').trim()

      if (!labName || !experimentItem) return null

      return {
        lab_name: labName.trim(),
        experiment_item: experimentItem,
      }
    })
    .filter((item): item is RequestedExperiment => Boolean(item))
}

function getRequestedExperiments(sample: Sample | null): RequestedExperiment[] {
  if (!sample) return []

  const parsedNote = safeParseSampleNote(sample.note)

  if (
    parsedNote?.requested_experiments &&
    Array.isArray(parsedNote.requested_experiments)
  ) {
    return parsedNote.requested_experiments.filter(
      (item) => item.lab_name && item.experiment_item,
    )
  }

  return parseExperimentsFromSummary(sample.experiment_item)
}

function findMatchingWipForExperiment(
  sampleWips: Wip[],
  experiment: RequestedExperiment,
) {
  return (
    sampleWips.find(
      (wip) =>
        normalizeLab(wip.lab_name) === normalizeLab(experiment.lab_name) &&
        normalizeExperiment(wip.experiment_item) ===
          normalizeExperiment(experiment.experiment_item),
    ) ?? null
  )
}

function isExperimentCompleted(
  sampleWips: Wip[],
  experiment: RequestedExperiment,
) {
  return sampleWips.some(
    (wip) =>
      normalizeLab(wip.lab_name) === normalizeLab(experiment.lab_name) &&
      normalizeExperiment(wip.experiment_item) ===
        normalizeExperiment(experiment.experiment_item) &&
      wip.status === 'completed',
  )
}

export default function SampleTransferPage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser>(fallbackUser)
  const [samples, setSamples] = useState<Sample[]>([])
  const [wips, setWips] = useState<Wip[]>([])
  const [transfers, setTransfers] = useState<Transfer[]>([])
  const [selectedCandidateKey, setSelectedCandidateKey] = useState('')
  const [selectedTransfer, setSelectedTransfer] = useState<Transfer | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const currentLab = currentUser.lab_name || currentUser.department || 'Lab A'
  const operatorName = currentUser.name || fallbackUser.name

  const wipsBySampleId = useMemo(() => {
    return wips.reduce<Record<string, Wip[]>>((groups, wip) => {
      if (!groups[wip.sample_id]) {
        groups[wip.sample_id] = []
      }

      groups[wip.sample_id].push(wip)
      return groups
    }, {})
  }, [wips])

  const transfersByTargetId = useMemo(() => {
    return transfers.reduce<Record<string, Transfer[]>>((groups, transfer) => {
      if (!groups[transfer.target_id]) {
        groups[transfer.target_id] = []
      }

      groups[transfer.target_id].push(transfer)
      return groups
    }, {})
  }, [transfers])

  const transferCandidates = useMemo<TransferCandidate[]>(() => {
    const result: TransferCandidate[] = []

    samples.forEach((sample) => {
      const sampleWips = wipsBySampleId[sample.id] ?? []

      if (sample.status === 'picked_up') return
      if (sample.status === 'outbound') return
      if (sample.status === 'pending_receive') return

      const requestedExperiments = getRequestedExperiments(sample)

      const currentLabWips = sampleWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab),
      )

      const currentLabCompletedWips = currentLabWips.filter(
        (wip) => wip.status === 'completed',
      )

      if (currentLabCompletedWips.length === 0) return

      const remainingExperiments =
        requestedExperiments.length > 0
          ? requestedExperiments.filter((experiment) => {
              const isOtherLab =
                normalizeLab(experiment.lab_name) !== normalizeLab(currentLab)

              const completed = isExperimentCompleted(sampleWips, experiment)

              return isOtherLab && !completed
            })
          : []

      const remainingWips = sampleWips.filter(
        (wip) =>
          normalizeLab(wip.lab_name) !== normalizeLab(currentLab) &&
          wip.status !== 'completed',
      )

      if (requestedExperiments.length > 0) {
        if (remainingExperiments.length === 0) return

        const nextExperiment = remainingExperiments[0]
        const nextWip = findMatchingWipForExperiment(sampleWips, nextExperiment)

        const relatedTransfers = [
          ...(transfersByTargetId[sample.id] ?? []),
          ...(nextWip ? transfersByTargetId[nextWip.id] ?? [] : []),
        ]

        const existingTransfer =
          relatedTransfers.find((transfer) =>
            blockingTransferStatuses.includes(transfer.status),
          ) ?? null

        result.push({
          kind: 'transfer',
          sample,
          currentLabCompletedWips,
          remainingWips,
          remainingExperiments,
          nextLab: nextExperiment.lab_name,
          nextExperiment,
          nextWip,
          existingTransfer,
        })

        return
      }

      if (sampleWips.length === 0) return
      if (remainingWips.length === 0) return

      const nextWip = remainingWips[0]

      if (!nextWip.lab_name) return

      const nextExperiment = {
        lab_name: nextWip.lab_name,
        experiment_item: nextWip.experiment_item ?? '未命名實驗',
      }

      const relatedTransfers = [
        ...(transfersByTargetId[sample.id] ?? []),
        ...(transfersByTargetId[nextWip.id] ?? []),
      ]

      const existingTransfer =
        relatedTransfers.find((transfer) =>
          blockingTransferStatuses.includes(transfer.status),
        ) ?? null

      result.push({
        kind: 'transfer',
        sample,
        currentLabCompletedWips,
        remainingWips,
        remainingExperiments: [nextExperiment],
        nextLab: nextWip.lab_name,
        nextExperiment,
        nextWip,
        existingTransfer,
      })
    })

    return result
  }, [samples, wipsBySampleId, transfersByTargetId, currentLab])

  const returnCandidates = useMemo<ReturnCandidate[]>(() => {
    const result: ReturnCandidate[] = []

    samples.forEach((sample) => {
      const sampleWips = wipsBySampleId[sample.id] ?? []

      if (sample.status === 'picked_up') return
      if (sample.status === 'pending_receive') return

      const requestedExperiments = getRequestedExperiments(sample)

      const currentLabWips = sampleWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab),
      )

      const currentLabCompletedWips = currentLabWips.filter(
        (wip) => wip.status === 'completed',
      )

      const hasCurrentLabCompletedWip = currentLabCompletedWips.length > 0

      if (!hasCurrentLabCompletedWip) return

      if (requestedExperiments.length > 0) {
        const unfinishedExperiments = requestedExperiments.filter(
          (experiment) => !isExperimentCompleted(sampleWips, experiment),
        )

        if (unfinishedExperiments.length > 0) return

        result.push({
          kind: 'return',
          sample,
          currentLabCompletedWips,
          allWips: sampleWips,
        })

        return
      }

      if (sampleWips.length === 0) return

      const unfinishedAnyWips = sampleWips.filter(
        (wip) => wip.status !== 'completed',
      )

      if (unfinishedAnyWips.length > 0) return

      result.push({
        kind: 'return',
        sample,
        currentLabCompletedWips,
        allWips: sampleWips,
      })
    })

    return result
  }, [samples, wipsBySampleId, currentLab])

  const candidates = useMemo<Candidate[]>(() => {
    return [...transferCandidates, ...returnCandidates]
  }, [transferCandidates, returnCandidates])

  const selectedCandidate = useMemo(() => {
    return (
      candidates.find((candidate) => getCandidateKey(candidate) === selectedCandidateKey) ??
      null
    )
  }, [candidates, selectedCandidateKey])

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

      const [sampleData, wipData, transferData] = await Promise.all([
        apiGet<Sample[]>('/api/samples'),
        apiGet<Wip[]>('/api/wips?include_all_for_flow=true'),
        apiGet<Transfer[]>('/api/transfers'),
      ])

      setCurrentUser(meData)
      setSamples(sampleData)
      setWips(wipData)
      setTransfers(transferData)
      setSelectedCandidateKey('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '載入樣品流轉資料失敗')
    } finally {
      setLoading(false)
    }
  }

  async function createTransfer(candidate: TransferCandidate) {
    try {
      setSubmitting(true)
      setError('')
      setSuccessMessage('')

      await apiPost('/api/transfers', {
        target_type: 'sample',
        target_id: candidate.sample.id,
        order_no: candidate.sample.order_no,
        sample_no: candidate.sample.sample_no,
        wip_no: candidate.nextWip?.wip_no ?? null,
        from_lab: currentLab,
        to_lab: candidate.nextLab,
        handed_by: operatorName,
        note: candidate.nextWip
          ? `目前 ${currentLab} 的 WIP 已完成，交接至 ${candidate.nextLab} 收樣區。下一個 WIP：${candidate.nextWip.wip_no}`
          : `目前 ${currentLab} 的 WIP 已完成，交接至 ${candidate.nextLab} 收樣區。下一個測驗：${candidate.nextExperiment.experiment_item}。`,
      })

      setSuccessMessage('交接申請已建立')
      await loadData()
    } catch (err) {
      console.error('createTransfer failed:', err)
      setError(err instanceof Error ? err.message : '建立交接申請失敗')
    } finally {
      setSubmitting(false)
    }
  }

  async function sendTransfer(transfer: Transfer) {
    try {
      setSubmitting(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/transfers/${transfer.id}/actions`, {
        action: 'send',
        operator_name: operatorName,
      })

      setSuccessMessage('已送出交接，樣品已移至下一個 Lab 的待收樣區')
      await loadData()
    } catch (err) {
      console.error('sendTransfer failed:', err)
      setError(err instanceof Error ? err.message : '送出交接單失敗')
    } finally {
      setSubmitting(false)
    }
  }

  async function cancelTransfer(transfer: Transfer) {
    try {
      setSubmitting(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/transfers/${transfer.id}/actions`, {
        action: 'cancel',
        operator_name: operatorName,
      })

      setSuccessMessage('交接單已取消')
      await loadData()
    } catch (err) {
      console.error('cancelTransfer failed:', err)
      setError(err instanceof Error ? err.message : '取消交接單失敗')
    } finally {
      setSubmitting(false)
    }
  }

  async function notifyPickup(candidate: ReturnCandidate) {
    try {
      setSubmitting(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/samples/${candidate.sample.id}/actions`, {
        action: 'outbound',
        operator_name: operatorName,
        current_location: `${currentLab} 待取件區`,
        note: candidate.sample.note,
      })

      setSuccessMessage('已通知原使用者取件，樣品已移至待取件區')
      await loadData()
    } catch (err) {
      console.error('notifyPickup failed:', err)
      setError(err instanceof Error ? err.message : '通知取件失敗')
    } finally {
      setSubmitting(false)
    }
  }

  async function confirmPickup(candidate: ReturnCandidate) {
    try {
      setSubmitting(true)
      setError('')
      setSuccessMessage('')

      await apiPost(`/api/samples/${candidate.sample.id}/actions`, {
        action: 'pickup_confirmed',
        operator_name: operatorName,
        current_location: '已由使用者取回',
      })

      setSuccessMessage('已確認使用者取件，樣品流程完成')
      await loadData()
    } catch (err) {
      console.error('confirmPickup failed:', err)
      setError(err instanceof Error ? err.message : '確認取件失敗')
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>樣品交接管理</h1>
          <p style={subtitleStyle}>
            TRANSFER OUT · 目前 Lab：{currentLab} · 這裡只負責把樣品送出到下一個 Lab 的待收樣區。
          </p>
        </div>

        <div style={headerActionsStyle}>
          <button onClick={() => (window.location.href = '/sample')} style={secondaryButtonStyle}>
            回樣品管理
          </button>
          <button onClick={loadData} style={secondaryButtonStyle}>
            重新整理
          </button>
        </div>
      </div>

      <div style={currentUserBoxStyle}>
        <div style={currentUserTitleStyle}>目前登入者</div>
        <div style={currentUserTextStyle}>
          {currentUser.name} · {currentUser.role_name ?? currentUser.role} · {currentLab}
        </div>
      </div>

      {error && <div style={errorStyle}>{error}</div>}
      {successMessage && <div style={successStyle}>{successMessage}</div>}

      <section style={summaryGridStyle}>
        <SummaryCard label="待建立交接" value={transferCandidates.length} />
        <SummaryCard
          label="我方待送出"
          value={
            transfers.filter(
              (transfer) =>
                transfer.from_lab === currentLab && transfer.status === 'pending',
            ).length
          }
        />
        <SummaryCard
          label="我方已送出"
          value={
            transfers.filter(
              (transfer) =>
                transfer.from_lab === currentLab && transfer.status === 'transferring',
            ).length
          }
        />
        <SummaryCard label="待通知 / 取件" value={returnCandidates.length} />
      </section>

      <section style={twoColumnGridStyle}>
        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <div>
              <div style={panelTitleStyle}>待送出至下一個 Lab</div>
              <div style={hintStyle}>
                條件：目前 Lab 有 completed WIP，且同一樣品仍有其他 Lab 測驗未完成。
              </div>
            </div>

            <span style={countBadgeStyle}>{transferCandidates.length} 筆</span>
          </div>

          {loading ? (
            <div style={emptyStyle}>載入中...</div>
          ) : transferCandidates.length === 0 ? (
            <div style={emptyStyle}>目前沒有需要送出到其他實驗室的樣品。</div>
          ) : (
            <div style={candidateListStyle}>
              {transferCandidates.map((candidate) => {
                const candidateKey = getCandidateKey(candidate)
                const selected = selectedCandidateKey === candidateKey

                return (
                  <button
                    key={candidateKey}
                    type="button"
                    onClick={() => setSelectedCandidateKey(candidateKey)}
                    style={selected ? selectedCandidateCardStyle : candidateCardStyle}
                  >
                    <div style={candidateTopRowStyle}>
                      <div>
                        <div style={candidateTitleStyle}>{candidate.sample.sample_no}</div>
                        <div style={candidateSubtitleStyle}>
                          {candidate.sample.sample_name ?? '未命名樣品'} ·{' '}
                          {candidate.sample.order_no}
                        </div>
                      </div>

                      {candidate.existingTransfer ? (
                        <StatusBadge status={candidate.existingTransfer.status} />
                      ) : (
                        <span style={readyBadgeStyle}>可建立</span>
                      )}
                    </div>

                    <div style={candidateMetaGridStyle}>
                      <InfoLine label="目前位置" value={candidate.sample.current_location ?? '-'} />
                      <InfoLine
                        label="目前完成"
                        value={`${currentLab} · ${candidate.currentLabCompletedWips.length} 個 WIP`}
                      />
                      <InfoLine label="送往" value={`${candidate.nextLab} 收樣區`} />
                      <InfoLine
                        label="下一 WIP"
                        value={candidate.nextWip?.wip_no ?? '尚未建立 WIP'}
                      />
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <div>
              <div style={panelTitleStyle}>待通知使用者取件</div>
              <div style={hintStyle}>
                條件：全部測驗都 completed，才可以通知原使用者取件。
              </div>
            </div>

            <span style={countBadgeStyle}>{returnCandidates.length} 筆</span>
          </div>

          {loading ? (
            <div style={emptyStyle}>載入中...</div>
          ) : returnCandidates.length === 0 ? (
            <div style={emptyStyle}>目前沒有待通知或待取件的樣品。</div>
          ) : (
            <div style={candidateListStyle}>
              {returnCandidates.map((candidate) => {
                const candidateKey = getCandidateKey(candidate)
                const selected = selectedCandidateKey === candidateKey
                const isOutbound = candidate.sample.status === 'outbound'

                return (
                  <button
                    key={candidateKey}
                    type="button"
                    onClick={() => setSelectedCandidateKey(candidateKey)}
                    style={selected ? selectedCandidateCardStyle : candidateCardStyle}
                  >
                    <div style={candidateTopRowStyle}>
                      <div>
                        <div style={candidateTitleStyle}>{candidate.sample.sample_no}</div>
                        <div style={candidateSubtitleStyle}>
                          {candidate.sample.sample_name ?? '未命名樣品'} ·{' '}
                          {candidate.sample.order_no}
                        </div>
                      </div>

                      {isOutbound ? (
                        <span style={warningBadgeStyle}>待取件</span>
                      ) : (
                        <span style={readyBadgeStyle}>可通知</span>
                      )}
                    </div>

                    <div style={candidateMetaGridStyle}>
                      <InfoLine label="目前位置" value={candidate.sample.current_location ?? '-'} />
                      <InfoLine
                        label="樣品狀態"
                        value={sampleStatusText[candidate.sample.status] ?? candidate.sample.status}
                      />
                      <InfoLine label="申請人" value={candidate.sample.applicant_name ?? '-'} />
                      <InfoLine
                        label="完成 WIP"
                        value={`${candidate.allWips.filter((wip) => wip.status === 'completed').length} / ${candidate.allWips.length}`}
                      />
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </section>

      <section style={panelStyle}>
        <div style={panelHeaderStyle}>
          <div>
            <div style={panelTitleStyle}>交接 / 取件操作</div>
            <div style={hintStyle}>
              選擇上方樣品後，建立交接、送出到下一個 Lab 待收樣區，或通知使用者取件。
            </div>
          </div>
        </div>

        {!selectedCandidate ? (
          <div style={emptyStyle}>請先選擇上方任一樣品。</div>
        ) : selectedCandidate.kind === 'transfer' ? (
          <TransferDetail
            candidate={selectedCandidate}
            currentLab={currentLab}
            submitting={submitting}
            onCreateTransfer={createTransfer}
            onSendTransfer={sendTransfer}
            onCancelTransfer={cancelTransfer}
          />
        ) : (
          <ReturnDetail
            candidate={selectedCandidate}
            submitting={submitting}
            onNotifyPickup={notifyPickup}
            onConfirmPickup={confirmPickup}
          />
        )}
      </section>

      <section style={panelStyle}>
        <div style={panelHeaderStyle}>
          <div>
            <div style={panelTitleStyle}>我方交接單列表</div>
            <div style={hintStyle}>
              只顯示目前 Lab 送出的交接單。對方收到後會出現在對方的 /sample 待收樣。
            </div>
          </div>

          <span style={countBadgeStyle}>{transfers.length} 筆</span>
        </div>

        {transfers.length === 0 ? (
          <div style={emptyStyle}>目前沒有交接單。</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={tableStyle}>
              <thead>
                <tr style={{ background: 'var(--s2)' }}>
                  {[
                    '交接單',
                    '樣品',
                    'WIP',
                    'From',
                    'To',
                    '狀態',
                    '交接人',
                    '簽收人',
                    '操作',
                  ].map((header) => (
                    <th key={header} style={thStyle}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {transfers.map((transfer) => (
                  <tr key={transfer.id} style={{ borderBottom: '1px solid var(--border2)' }}>
                    <td style={monoTdStyle}>{transfer.transfer_no ?? transfer.id.slice(0, 8)}</td>
                    <td style={monoTdStyle}>{transfer.sample_no ?? '-'}</td>
                    <td style={monoTdStyle}>{transfer.wip_no ?? '-'}</td>
                    <td style={tdStyle}>{transfer.from_lab ?? '-'}</td>
                    <td style={tdStyle}>{transfer.to_lab ?? '-'}</td>
                    <td style={tdStyle}>
                      <StatusBadge status={transfer.status} />
                    </td>
                    <td style={tdStyle}>{transfer.handed_by ?? '-'}</td>
                    <td style={tdStyle}>{transfer.received_by ?? '-'}</td>
                    <td style={tdStyle}>
                      <div style={smallActionGroupStyle}>
                        <button
                          type="button"
                          onClick={() => setSelectedTransfer(transfer)}
                          style={smallSecondaryButtonStyle}
                        >
                          查看
                        </button>

                        {transfer.from_lab === currentLab && transfer.status === 'pending' && (
                          <button
                            onClick={() => sendTransfer(transfer)}
                            disabled={submitting}
                            style={smallPrimaryButtonStyle}
                          >
                            送出
                          </button>
                        )}

                        {transfer.from_lab === currentLab && transfer.status === 'pending' && (
                          <button
                            onClick={() => cancelTransfer(transfer)}
                            disabled={submitting}
                            style={smallDangerButtonStyle}
                          >
                            取消
                          </button>
                        )}

                        {transfer.status === 'transferring' && <span style={hintStyle}>已送至對方待收樣區</span>}
                        {transfer.status === 'received' && <span style={hintStyle}>對方已收樣</span>}
                        {transfer.status === 'cancelled' && <span style={hintStyle}>已取消</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selectedTransfer && (
        <TransferModal
          transfer={selectedTransfer}
          currentLab={currentLab}
          submitting={submitting}
          onClose={() => setSelectedTransfer(null)}
          onSendTransfer={sendTransfer}
          onCancelTransfer={cancelTransfer}
        />
      )}
    </div>
  )
}

function TransferModal({
  transfer,
  currentLab,
  submitting,
  onClose,
  onSendTransfer,
  onCancelTransfer,
}: {
  transfer: Transfer
  currentLab: string
  submitting: boolean
  onClose: () => void
  onSendTransfer: (transfer: Transfer) => void
  onCancelTransfer: (transfer: Transfer) => void
}) {
  return (
    <div style={modalBackdropStyle}>
      <div style={modalCardStyle}>
        <div style={modalHeaderStyle}>
          <div>
            <div style={modalTitleStyle}>
              {transfer.transfer_no ?? transfer.id.slice(0, 8)}
            </div>
            <div style={modalSubtitleStyle}>
              {transfer.from_lab ?? '-'} → {transfer.to_lab ?? '-'}
            </div>
          </div>

          <div style={modalHeaderActionsStyle}>
            <StatusBadge status={transfer.status} />
            <button type="button" onClick={onClose} style={iconButtonStyle}>
              ✕
            </button>
          </div>
        </div>

        <div style={modalBodyStyle}>
          <div style={sectionTitleStyle}>交接單詳細資訊</div>

          <div style={detailGridStyle}>
            <InfoBlock label="交接單號" value={transfer.transfer_no ?? transfer.id} />
            <InfoBlock label="交接類型" value={transfer.target_type} />
            <InfoBlock label="委託單號" value={transfer.order_no ?? '-'} />
            <InfoBlock label="樣品編號" value={transfer.sample_no ?? '-'} />
            <InfoBlock label="WIP 編號" value={transfer.wip_no ?? '-'} />
            <InfoBlock label="來源實驗室" value={transfer.from_lab ?? '-'} />
            <InfoBlock label="目的實驗室" value={transfer.to_lab ?? '-'} />
            <InfoBlock label="交接人" value={transfer.handed_by ?? '-'} />
            <InfoBlock label="送出時間" value={formatDateTime(transfer.transferred_at)} />
            <InfoBlock label="簽收人" value={transfer.received_by ?? '-'} />
            <InfoBlock label="簽收時間" value={formatDateTime(transfer.received_at)} />
            <InfoBlock
              label="狀態"
              value={transferStatusText[transfer.status] ?? transfer.status}
            />
            <InfoBlock label="建立時間" value={formatDateTime(transfer.created_at)} />
            <InfoBlock label="更新時間" value={formatDateTime(transfer.updated_at)} />
            <InfoBlock label="備註" value={transfer.note ?? '-'} />
          </div>

          <div style={modalNoticeStyle}>
            {transfer.status === 'pending' &&
              '這筆交接單尚未送出，只有來源實驗室可以送出或取消。'}
            {transfer.status === 'transferring' &&
              '交接單已送出，樣品已移到目的實驗室收樣區，等待目的實驗室在收樣管理確認收樣。'}
            {transfer.status === 'received' &&
              '目的實驗室已確認收樣，交接流程完成。'}
            {transfer.status === 'cancelled' && '這筆交接單已取消。'}
          </div>

          <div style={actionBarStyle}>
            {transfer.from_lab === currentLab && transfer.status === 'pending' && (
              <button
                type="button"
                disabled={submitting}
                onClick={() => onSendTransfer(transfer)}
                style={primaryButtonStyle}
              >
                送出到對方待收樣區
              </button>
            )}

            {transfer.from_lab === currentLab && transfer.status === 'pending' && (
              <button
                type="button"
                disabled={submitting}
                onClick={() => onCancelTransfer(transfer)}
                style={dangerButtonStyle}
              >
                取消交接
              </button>
            )}

            <button type="button" onClick={onClose} style={secondaryButtonStyle}>
              關閉
            </button>
          </div>
        </div>
      </div>
      <button
        type="button"
        aria-label="close"
        style={modalBackdropButtonStyle}
        onClick={onClose}
      />
    </div>
  )
}

function TransferDetail({
  candidate,
  currentLab,
  submitting,
  onCreateTransfer,
  onSendTransfer,
  onCancelTransfer,
}: {
  candidate: TransferCandidate
  currentLab: string
  submitting: boolean
  onCreateTransfer: (candidate: TransferCandidate) => void
  onSendTransfer: (transfer: Transfer) => void
  onCancelTransfer: (transfer: Transfer) => void
}) {
  return (
    <div style={detailBoxStyle}>
      <div style={sectionTitleStyle}>樣品資訊</div>

      <div style={detailGridStyle}>
        <InfoBlock label="樣品編號" value={candidate.sample.sample_no} />
        <InfoBlock label="委託單號" value={candidate.sample.order_no} />
        <InfoBlock label="樣品名稱" value={candidate.sample.sample_name ?? '-'} />
        <InfoBlock label="實驗需求" value={candidate.sample.experiment_item ?? '-'} />
        <InfoBlock label="目前位置" value={candidate.sample.current_location ?? '-'} />
        <InfoBlock label="送往" value={`${candidate.nextLab} 收樣區`} />
      </div>

      <div style={sectionTitleStyle}>目前 Lab 已完成 WIP</div>
      <div style={wipListStyle}>
        {candidate.currentLabCompletedWips.map((wip) => (
          <WipCard key={wip.id} wip={wip} />
        ))}
      </div>

      <div style={sectionTitleStyle}>後續待做測驗</div>

      {candidate.remainingWips.length > 0 ? (
        <div style={wipListStyle}>
          {candidate.remainingWips.map((wip) => (
            <WipCard key={wip.id} wip={wip} />
          ))}
        </div>
      ) : (
        <div style={wipListStyle}>
          {candidate.remainingExperiments.map((experiment) => (
            <div
              key={`${experiment.lab_name}-${experiment.experiment_item}`}
              style={wipCardStyle}
            >
              <div>
                <div style={{ fontWeight: 800, fontSize: 13 }}>
                  {experiment.experiment_item}
                </div>
                <div style={hintStyle}>
                  {experiment.lab_name} · 尚未建立 WIP
                </div>
              </div>

              <span style={warningBadgeStyle}>待對方收樣後建立</span>
            </div>
          ))}
        </div>
      )}

      <div style={sectionTitleStyle}>交接狀態</div>

      {candidate.existingTransfer ? (
        <div style={existingTransferBoxStyle}>
          <div style={existingTransferHeaderStyle}>
            <div>
              <div style={{ fontWeight: 800 }}>交接申請已建立</div>
              <div style={hintStyle}>
                {candidate.existingTransfer.from_lab} → {candidate.existingTransfer.to_lab} 收樣區
              </div>
            </div>

            <StatusBadge status={candidate.existingTransfer.status} />
          </div>

          <div style={detailGridStyle}>
            <InfoBlock
              label="交接單號"
              value={candidate.existingTransfer.transfer_no ?? candidate.existingTransfer.id}
            />
            <InfoBlock label="交接人" value={candidate.existingTransfer.handed_by ?? '-'} />
            <InfoBlock label="備註" value={candidate.existingTransfer.note ?? '-'} />
          </div>

          <div style={actionBarStyle}>
            {candidate.existingTransfer.from_lab === currentLab &&
              candidate.existingTransfer.status === 'pending' && (
                <button
                  onClick={() => onSendTransfer(candidate.existingTransfer as Transfer)}
                  disabled={submitting}
                  style={primaryButtonStyle}
                >
                  送出到對方待收樣區
                </button>
              )}

            {candidate.existingTransfer.from_lab === currentLab &&
              candidate.existingTransfer.status === 'pending' && (
                <button
                  onClick={() => onCancelTransfer(candidate.existingTransfer as Transfer)}
                  disabled={submitting}
                  style={dangerButtonStyle}
                >
                  取消交接
                </button>
              )}

            {candidate.existingTransfer.status === 'transferring' && (
              <span style={hintStyle}>已送出，樣品會出現在對方 /sample 待收樣。</span>
            )}
          </div>
        </div>
      ) : (
        <div style={createTransferBoxStyle}>
          <div style={{ fontWeight: 800, marginBottom: 6 }}>尚未建立交接申請</div>
          <div style={hintStyle}>
            建立後可以送出，送出後樣品會直接移到 {candidate.nextLab} 收樣區。
          </div>

          {!candidate.nextWip && (
            <div style={warningNoticeStyle}>
              下一個 Lab 的 WIP 尚未建立。樣品送到對方待收樣區後，對方會在 /sample 收樣，再到 /wip 建立自己的 WIP。
            </div>
          )}

          <div style={actionBarStyle}>
            <button
              onClick={() => onCreateTransfer(candidate)}
              disabled={submitting}
              style={primaryButtonStyle}
            >
              建立交接申請
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ReturnDetail({
  candidate,
  submitting,
  onNotifyPickup,
  onConfirmPickup,
}: {
  candidate: ReturnCandidate
  submitting: boolean
  onNotifyPickup: (candidate: ReturnCandidate) => void
  onConfirmPickup: (candidate: ReturnCandidate) => void
}) {
  const isOutbound = candidate.sample.status === 'outbound'

  return (
    <div style={detailBoxStyle}>
      <div style={sectionTitleStyle}>樣品資訊</div>

      <div style={detailGridStyle}>
        <InfoBlock label="樣品編號" value={candidate.sample.sample_no} />
        <InfoBlock label="委託單號" value={candidate.sample.order_no} />
        <InfoBlock label="樣品名稱" value={candidate.sample.sample_name ?? '-'} />
        <InfoBlock label="實驗需求" value={candidate.sample.experiment_item ?? '-'} />
        <InfoBlock label="目前位置" value={candidate.sample.current_location ?? '-'} />
        <InfoBlock
          label="樣品狀態"
          value={sampleStatusText[candidate.sample.status] ?? candidate.sample.status}
        />
        <InfoBlock label="申請人" value={candidate.sample.applicant_name ?? '-'} />
        <InfoBlock label="申請部門" value={candidate.sample.applicant_department ?? '-'} />
      </div>

      <div style={sectionTitleStyle}>全部 WIP 已完成</div>
      <div style={wipListStyle}>
        {candidate.allWips.map((wip) => (
          <WipCard key={wip.id} wip={wip} />
        ))}
      </div>

      <div style={sectionTitleStyle}>取件狀態</div>

      <div style={returnBoxStyle}>
        <div style={existingTransferHeaderStyle}>
          <div>
            <div style={{ fontWeight: 800 }}>
              {isOutbound ? '已通知使用者取件' : '尚未通知使用者取件'}
            </div>
            <div style={hintStyle}>
              {isOutbound
                ? '樣品目前在待取件區，等待廠區使用者取回。'
                : '所有 WIP 已完成，可以通知原使用者取件。'}
            </div>
          </div>

          {isOutbound ? (
            <span style={warningBadgeStyle}>待取件</span>
          ) : (
            <span style={readyBadgeStyle}>可通知</span>
          )}
        </div>

        <div style={actionBarStyle}>
          {!isOutbound && (
            <button
              onClick={() => onNotifyPickup(candidate)}
              disabled={submitting}
              style={primaryButtonStyle}
            >
              通知原使用者取件
            </button>
          )}

          {isOutbound && (
            <button
              onClick={() => onConfirmPickup(candidate)}
              disabled={submitting}
              style={primaryButtonStyle}
            >
              確認使用者已取件
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return '-'

  try {
    return new Date(value).toLocaleString('zh-TW', {
      hour12: false,
    })
  } catch {
    return value
  }
}

function getCandidateKey(candidate: Candidate) {
  if (candidate.kind === 'transfer') {
    return `transfer-${candidate.sample.id}-${candidate.nextWip?.id ?? `${candidate.nextLab}-${candidate.nextExperiment.experiment_item}`}`
  }

  return `return-${candidate.sample.id}`
}

function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={summaryCardStyle}>
      <div style={summaryValueStyle}>{value}</div>
      <div style={summaryLabelStyle}>{label}</div>
    </div>
  )
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={infoLineLabelStyle}>{label}</div>
      <div style={infoLineValueStyle}>{value}</div>
    </div>
  )
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div style={infoBlockStyle}>
      <div style={infoBlockLabelStyle}>{label}</div>
      <div style={infoBlockValueStyle}>{value}</div>
    </div>
  )
}

function WipCard({ wip }: { wip: Wip }) {
  return (
    <div style={wipCardStyle}>
      <div>
        <div style={{ fontWeight: 800, fontSize: 13 }}>
          {wip.experiment_item ?? '未命名實驗'}
        </div>
        <div style={hintStyle}>
          {wip.wip_no} · {wip.lab_name ?? '未指定 Lab'} ·{' '}
          {priorityText[wip.priority] ?? wip.priority}
        </div>
      </div>

      <div style={{ textAlign: 'right' }}>
        <StatusBadge status={wip.status} type="wip" />
        <div style={hintStyle}>進度 {wip.progress}%</div>
      </div>
    </div>
  )
}

function StatusBadge({
  status,
  type = 'transfer',
}: {
  status: string
  type?: 'transfer' | 'wip' | 'sample'
}) {
  let text = status

  if (type === 'wip') {
    text = wipStatusText[status] ?? status
  } else if (type === 'sample') {
    text = sampleStatusText[status] ?? status
  } else {
    text = transferStatusText[status] ?? status
  }

  return <span style={statusBadgeStyle}>{text}</span>
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
  fontWeight: 900,
}

const subtitleStyle: CSSProperties = {
  marginTop: 6,
  color: 'var(--text3)',
  fontSize: 13,
  lineHeight: 1.6,
}

const currentUserBoxStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
  marginBottom: 14,
}

const currentUserTitleStyle: CSSProperties = {
  fontSize: 12,
  color: 'var(--text3)',
  marginBottom: 4,
}

const currentUserTextStyle: CSSProperties = {
  fontSize: 13,
  color: 'var(--text)',
  fontWeight: 800,
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
  fontSize: 24,
  fontWeight: 900,
}

const summaryLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

const twoColumnGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(360px, 1fr))',
  gap: 14,
  alignItems: 'start',
  marginBottom: 14,
}

const panelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 16,
  marginBottom: 14,
}

const panelHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 12,
}

const panelTitleStyle: CSSProperties = {
  fontWeight: 900,
  fontSize: 15,
}

const hintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
  lineHeight: 1.5,
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
  whiteSpace: 'nowrap',
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

const emptyStyle: CSSProperties = {
  textAlign: 'center',
  color: 'var(--text3)',
  padding: 28,
  fontSize: 13,
}

const candidateListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

const candidateCardStyle: CSSProperties = {
  width: '100%',
  textAlign: 'left',
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
  cursor: 'pointer',
  color: 'var(--text)',
}

const selectedCandidateCardStyle: CSSProperties = {
  ...candidateCardStyle,
  border: '1px solid rgba(56,139,253,0.55)',
  background: 'rgba(56,139,253,0.1)',
}

const candidateTopRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 12,
}

const candidateTitleStyle: CSSProperties = {
  fontWeight: 900,
  fontSize: 14,
}

const candidateSubtitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

const candidateMetaGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: 8,
}

const infoLineLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
}

const infoLineValueStyle: CSSProperties = {
  color: 'var(--text2)',
  fontSize: 12,
  fontWeight: 700,
  marginTop: 3,
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

const readyBadgeStyle: CSSProperties = {
  ...statusBadgeStyle,
  background: 'rgba(63,185,80,0.12)',
  color: 'var(--green)',
  border: '1px solid rgba(63,185,80,0.25)',
}

const warningBadgeStyle: CSSProperties = {
  ...statusBadgeStyle,
  background: 'rgba(210,153,34,0.14)',
  color: 'var(--yellow)',
  border: '1px solid rgba(210,153,34,0.35)',
}

const detailBoxStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
}

const sectionTitleStyle: CSSProperties = {
  fontWeight: 900,
  fontSize: 14,
}

const detailGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 10,
}

const infoBlockStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
}

const infoBlockLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginBottom: 6,
}

const infoBlockValueStyle: CSSProperties = {
  color: 'var(--text)',
  fontSize: 13,
  fontWeight: 700,
  wordBreak: 'break-word',
}

const wipListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const wipCardStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
}

const existingTransferBoxStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.08)',
  border: '1px solid rgba(56,139,253,0.25)',
  borderRadius: 12,
  padding: 12,
}

const returnBoxStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.08)',
  border: '1px solid rgba(63,185,80,0.25)',
  borderRadius: 12,
  padding: 12,
}

const existingTransferHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 12,
}

const createTransferBoxStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

const warningNoticeStyle: CSSProperties = {
  marginTop: 10,
  background: 'rgba(210,153,34,0.1)',
  border: '1px solid rgba(210,153,34,0.25)',
  color: 'var(--yellow)',
  borderRadius: 10,
  padding: 10,
  fontSize: 12,
  lineHeight: 1.6,
}

const actionBarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
  marginTop: 12,
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

const dangerButtonStyle: CSSProperties = {
  background: 'rgba(247,129,102,0.14)',
  border: '1px solid rgba(247,129,102,0.35)',
  color: 'var(--orange)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 12,
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

const smallActionGroupStyle: CSSProperties = {
  display: 'flex',
  gap: 6,
  alignItems: 'center',
}

const smallPrimaryButtonStyle: CSSProperties = {
  ...primaryButtonStyle,
  padding: '5px 8px',
  fontSize: 11,
}

const smallSecondaryButtonStyle: CSSProperties = {
  ...secondaryButtonStyle,
  padding: '5px 8px',
  fontSize: 11,
}

const smallDangerButtonStyle: CSSProperties = {
  ...dangerButtonStyle,
  padding: '5px 8px',
  fontSize: 11,
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
  width: 'min(920px, 96vw)',
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
  zIndex: 1,
  background: 'var(--s1)',
  borderBottom: '1px solid var(--border2)',
  padding: 18,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: 16,
}

const modalHeaderActionsStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
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

const iconButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 10,
  width: 34,
  height: 34,
  cursor: 'pointer',
}

const modalNoticeStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  color: 'var(--text2)',
  borderRadius: 12,
  padding: 12,
  fontSize: 13,
  lineHeight: 1.6,
}
