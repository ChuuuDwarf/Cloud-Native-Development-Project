'use client'

import { useEffect, useMemo, useState } from 'react'
import { apiGet, apiPost } from '@/lib/api'
import { getErrorMessage, logClientError } from '@/lib/error'
import type {
  CurrentUser,
  Sample,
  Wip,
  Transfer,
  TransferCandidate,
  ReturnCandidate,
  Candidate,
} from './types'
import { fallbackUser, sampleStatusText, blockingTransferStatuses } from './constants'
import {
  normalizeLab,
  getRequestedExperiments,
  findMatchingWipForExperiment,
  isExperimentCompleted,
  getCandidateKey,
} from './utils/transferFlow'
import {
  TransferModal,
  TransferDetail,
  ReturnDetail,
  SummaryCard,
  InfoLine,
  StatusBadge,
} from './components/TransferWidgets'
import {
  headerStyle,
  headerActionsStyle,
  titleStyle,
  subtitleStyle,
  currentUserBoxStyle,
  currentUserTitleStyle,
  currentUserTextStyle,
  summaryGridStyle,
  twoColumnGridStyle,
  panelStyle,
  panelHeaderStyle,
  panelTitleStyle,
  hintStyle,
  countBadgeStyle,
  errorStyle,
  successStyle,
  emptyStyle,
  candidateListStyle,
  candidateCardStyle,
  selectedCandidateCardStyle,
  candidateTopRowStyle,
  candidateTitleStyle,
  candidateSubtitleStyle,
  candidateMetaGridStyle,
  readyBadgeStyle,
  warningBadgeStyle,
  secondaryButtonStyle,
  tableStyle,
  thStyle,
  tdStyle,
  monoTdStyle,
  smallActionGroupStyle,
  smallPrimaryButtonStyle,
  smallSecondaryButtonStyle,
  smallDangerButtonStyle,
} from './styles'

export default function SampleTransferPage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser>(fallbackUser)
  const [samples, setSamples] = useState<Sample[]>([])
  const [wips, setWips] = useState<Wip[]>([])
  const [transfers, setTransfers] = useState<Transfer[]>([])
  const [selectedCandidateKey, setSelectedCandidateKey] = useState('')
  const [selectedTransferId, setSelectedTransferId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const currentLab = currentUser.lab_name || currentUser.department || 'Lab A'
  const operatorName = currentUser.name || fallbackUser.name

  const selectedTransfer = useMemo(() => {
    if (!selectedTransferId) return null

    return transfers.find((transfer) => transfer.id === selectedTransferId) ?? null
  }, [transfers, selectedTransferId])

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

      if (currentLabWips.length === 0) return

      const currentLabIncompleteWips = currentLabWips.filter(
        (wip) => wip.status !== 'completed',
      )

      // 重點：
      // 只要目前 Lab 還有任何 WIP 沒完成，就不能顯示可轉移。
      // 避免完成一個 WIP 後，又新增另一個 WIP，transfer 頁面仍然顯示可轉移。
      if (currentLabIncompleteWips.length > 0) return

      const currentLabCompletedWips = currentLabWips.filter(
        (wip) => wip.status === 'completed',
      )

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

      if (currentLabWips.length === 0) return

      const currentLabIncompleteWips = currentLabWips.filter(
        (wip) => wip.status !== 'completed',
      )

      if (currentLabIncompleteWips.length > 0) return

      const currentLabCompletedWips = currentLabWips.filter(
        (wip) => wip.status === 'completed',
      )

      const unfinishedAnyWips = sampleWips.filter(
        (wip) => wip.status !== 'completed',
      )

      // 不管是不是委託單原始實驗，只要這個 sample 底下還有 WIP 沒完成，
      // 就不能通知取件。
      if (unfinishedAnyWips.length > 0) return

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

  async function loadData(options?: { resetCandidate?: boolean }) {
    const resetCandidate = options?.resetCandidate ?? true

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

      if (resetCandidate) {
        setSelectedCandidateKey('')
      }

      if (
        selectedTransferId &&
        !transferData.some((transfer) => transfer.id === selectedTransferId)
      ) {
        setSelectedTransferId(null)
      }
    } catch (err) {
      setError(getErrorMessage(err, '載入樣品流轉資料失敗'))
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
      logClientError('createTransfer failed', err)
      setError(getErrorMessage(err, '建立交接申請失敗'))
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

      setSelectedTransferId(null)
      setSuccessMessage('已送出交接，樣品已移至下一個 Lab 的待收樣區')
      await loadData()
    } catch (err) {
      logClientError('sendTransfer failed', err)
      setError(getErrorMessage(err, '送出交接單失敗'))
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

      setSelectedTransferId(null)
      setSuccessMessage('交接單已取消')
      await loadData()
    } catch (err) {
      logClientError('cancelTransfer failed', err)
      setError(getErrorMessage(err, '取消交接單失敗'))
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

      setSelectedTransferId(null)
      setSuccessMessage('已通知原使用者取件，樣品已移至待取件區')
      await loadData()
    } catch (err) {
      logClientError('notifyPickup failed', err)
      setError(getErrorMessage(err, '通知取件失敗'))
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

      setSelectedTransferId(null)
      setSuccessMessage('已確認使用者取件，樣品流程完成')
      await loadData()
    } catch (err) {
      logClientError('confirmPickup failed', err)
      setError(getErrorMessage(err, '確認取件失敗'))
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
          <button onClick={() => loadData()} style={secondaryButtonStyle}>
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
                          onClick={() => setSelectedTransferId(transfer.id)}
                          style={smallSecondaryButtonStyle}
                        >
                          查看
                        </button>

                        {transfer.from_lab === currentLab && transfer.status === 'pending' && (
                          <button
                            type="button"
                            onClick={() => sendTransfer(transfer)}
                            disabled={submitting}
                            style={smallPrimaryButtonStyle}
                          >
                            送出
                          </button>
                        )}

                        {transfer.from_lab === currentLab && transfer.status === 'pending' && (
                          <button
                            type="button"
                            onClick={() => cancelTransfer(transfer)}
                            disabled={submitting}
                            style={smallDangerButtonStyle}
                          >
                            取消
                          </button>
                        )}

                        {transfer.status === 'transferring' && (
                          <span style={hintStyle}>已送至對方待收樣區</span>
                        )}
                        {transfer.status === 'received' && (
                          <span style={hintStyle}>對方已收樣</span>
                        )}
                        {transfer.status === 'cancelled' && (
                          <span style={hintStyle}>已取消</span>
                        )}
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
          onClose={() => setSelectedTransferId(null)}
          onSendTransfer={sendTransfer}
          onCancelTransfer={cancelTransfer}
        />
      )}
    </div>
  )
}
