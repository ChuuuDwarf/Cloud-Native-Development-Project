import type { CurrentUser, Sample, SampleAction, SampleHistory, Transfer, Wip } from '../types'
import { priorityText, wipStatusText } from '../constants'
import { InfoItem } from './InfoItem'
import { Modal } from './Modal'
import { StatusBadge } from './StatusBadge'
import {
  actionBarStyle,
  countBadgeStyle,
  detailGridStyle,
  historyActionRowStyle,
  iconButtonStyle,
  labGroupHeaderStyle,
  labGroupStyle,
  labListStyle,
  miniEmptyStyle,
  modalBodyStyle,
  modalHeaderStyle,
  modalSubtitleStyle,
  modalTitleStyle,
  nextStepBoxStyle,
  primaryButtonStyle,
  secondaryButtonStyle,
  sectionTitleStyle,
  timelineDotStyle,
  timelineItemStyle,
  timelineMetaStyle,
  timelineStyle,
  timelineTimeStyle,
  timelineTopRowStyle,
  wipCardStyle,
  wipListStyle,
} from '../styles'
import {
  formatDateTime,
  formatStatusChange,
  getDisplaySampleLocation,
  getDisplaySampleStatus,
  getUserLab,
  isLabUser as checkIsLabUser,
  shouldMaskSampleForLab,
} from '../utils/sampleDisplay'

function formatExperimentRequirement(experimentItem: string | null) {
  if (!experimentItem) return '-'

  const items = experimentItem
    .split('、')
    .map((item) => item.trim())
    .filter(Boolean)

  if (items.length <= 1) return experimentItem

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {items.map((item, index) => (
        <div key={`${item}-${index}`}>{item}</div>
      ))}
    </div>
  )
}

type SampleDetailModalProps = {
  sample: Sample
  currentUser: CurrentUser
  selectedSampleOutgoingTransfer?: Transfer
  visibleSelectedWips: Wip[]
  wipsByLab: Record<string, Wip[]>
  sampleHistories: SampleHistory[]
  visibleHistories: SampleHistory[]
  historyLoading: boolean
  historyVisibleCount: number
  submitting: boolean
  canFactoryConfirmPickup: boolean
  selectedSampleInCurrentLab: boolean
  allWipsCompleted: boolean
  shouldShowTransferAction: boolean
  shouldShowActionSection: boolean
  isFactoryUser: boolean
  nextStepText: string
  onClose: () => void
  onShowMoreHistory: () => void
  onCollapseHistory: () => void
  onRunSampleAction: (sampleId: string, action: SampleAction) => void
  onGoToWipPage: (sampleId: string) => void
  onGoToTransferPage: () => void
}

export function SampleDetailModal({
  sample,
  currentUser,
  selectedSampleOutgoingTransfer,
  visibleSelectedWips,
  wipsByLab,
  sampleHistories,
  visibleHistories,
  historyLoading,
  historyVisibleCount,
  submitting,
  canFactoryConfirmPickup,
  selectedSampleInCurrentLab,
  allWipsCompleted,
  shouldShowTransferAction,
  shouldShowActionSection,
  isFactoryUser,
  nextStepText,
  onClose,
  onShowMoreHistory,
  onCollapseHistory,
  onRunSampleAction,
  onGoToWipPage,
  onGoToTransferPage,
}: SampleDetailModalProps) {
  const currentLab = getUserLab(currentUser)
  const shouldMaskForCurrentLab = shouldMaskSampleForLab(sample, currentUser)
  const isLabUser = checkIsLabUser(currentUser)

  const ownLabReceiveHistory = sampleHistories.find((history) => {
    if (history.action !== 'receive') return false
    if (!isLabUser) return true
    return history.lab_name === currentLab
  })

  const isIncomingTransferWaitingReceive = Boolean(
    isLabUser &&
      selectedSampleInCurrentLab &&
      selectedSampleOutgoingTransfer &&
      selectedSampleOutgoingTransfer.to_lab === currentLab &&
      selectedSampleOutgoingTransfer.status === 'transferring' &&
      sample.status === 'pending_receive',
  )

  const displayReceivedBy =
    ownLabReceiveHistory?.operator_name ??
    (shouldMaskForCurrentLab
      ? selectedSampleOutgoingTransfer?.handed_by ?? sample.received_by ?? '尚未收樣'
      : sample.received_by ?? '尚未收樣')

  const displayReceivedAt = ownLabReceiveHistory?.created_at ?? sample.received_at

  const transferReceiverText =
    selectedSampleOutgoingTransfer?.received_by ??
    (selectedSampleOutgoingTransfer?.to_lab
      ? `${selectedSampleOutgoingTransfer.to_lab} 尚未確認接收`
      : '接收實驗室尚未確認接收')

  const transferredOutStatusText = (() => {
    if (!selectedSampleOutgoingTransfer) return '已離開本實驗室'

    if (selectedSampleOutgoingTransfer.status === 'pending') {
      return `交接單已建立，尚未送出至 ${selectedSampleOutgoingTransfer.to_lab ?? '接收實驗室'}`
    }

    if (selectedSampleOutgoingTransfer.status === 'transferring') {
      return `等待 ${selectedSampleOutgoingTransfer.to_lab ?? '接收實驗室'} 確認接收`
    }

    if (selectedSampleOutgoingTransfer.status === 'received') {
      return '接收實驗室已確認接收'
    }

    if (selectedSampleOutgoingTransfer.status === 'cancelled') {
      return '交接已取消'
    }

    return selectedSampleOutgoingTransfer.status
  })()

  const shouldShowPickupInfo =
    !shouldMaskForCurrentLab &&
    !isIncomingTransferWaitingReceive &&
    (sample.status === 'outbound' || sample.status === 'picked_up')

  return (
    <Modal onClose={onClose}>
      <div style={modalHeaderStyle}>
        <div>
          <div style={modalTitleStyle}>{sample.sample_no}</div>
          <div style={modalSubtitleStyle}>委託單編號 {sample.order_no}</div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <StatusBadge
            status={getDisplaySampleStatus(sample, currentUser, selectedSampleOutgoingTransfer)}
          />
          <button onClick={onClose} style={iconButtonStyle}>
            ✕
          </button>
        </div>
      </div>

      <div style={modalBodyStyle}>
        <div style={nextStepBoxStyle}>
          <div style={{ fontWeight: 800, marginBottom: 6 }}>下一步判斷</div>
          <div style={{ color: 'var(--text2)', fontSize: 13 }}>{nextStepText}</div>
        </div>

        <div style={sectionTitleStyle}>樣品詳細資料</div>

        <div style={detailGridStyle}>
          <InfoItem label="樣品編號" value={sample.sample_no} />
          <InfoItem label="委託單編號" value={sample.order_no} />
          <InfoItem label="樣品名稱" value={sample.sample_name ?? '-'} />
          <InfoItem label="實驗需求" value={formatExperimentRequirement(sample.experiment_item)} />
          <InfoItem label="申請人" value={sample.applicant_name ?? '-'} />
          <InfoItem label="申請部門" value={sample.applicant_department ?? '-'} />
          <InfoItem
            label="目前位置"
            value={getDisplaySampleLocation(sample, currentUser, selectedSampleOutgoingTransfer)}
          />

          {isIncomingTransferWaitingReceive ? (
            <>
              <InfoItem label="來源實驗室" value={selectedSampleOutgoingTransfer?.from_lab ?? '-'} />
              <InfoItem label="交接人" value={selectedSampleOutgoingTransfer?.handed_by ?? '-'} />
              <InfoItem
                label="交接時間"
                value={formatDateTime(selectedSampleOutgoingTransfer?.transferred_at ?? null)}
              />
              <InfoItem label="收件人" value="尚未接收" />
              <InfoItem label="收件時間" value="-" />
            </>
          ) : (
            <>
              <InfoItem label="收樣人" value={displayReceivedBy} />
              <InfoItem label="收樣時間" value={formatDateTime(displayReceivedAt)} />

              {shouldMaskForCurrentLab && selectedSampleOutgoingTransfer && (
                <>
                  {selectedSampleOutgoingTransfer.status === 'received' ? (
                    <>
                      <InfoItem label="取走人" value={transferReceiverText} />
                      <InfoItem
                        label="取走時間"
                        value={formatDateTime(selectedSampleOutgoingTransfer.received_at)}
                      />
                    </>
                  ) : (
                    <>
                      <InfoItem label="接收狀態" value={transferredOutStatusText} />
                      <InfoItem
                        label={
                          selectedSampleOutgoingTransfer.status === 'pending'
                            ? '建立交接時間'
                            : '交接時間'
                        }
                        value={formatDateTime(
                          selectedSampleOutgoingTransfer.status === 'pending'
                            ? selectedSampleOutgoingTransfer.created_at
                            : selectedSampleOutgoingTransfer.transferred_at,
                        )}
                      />
                    </>
                  )}
                </>
              )}

              {shouldShowPickupInfo && (
                <>
                  <InfoItem label="取件人" value={sample.picked_up_by ?? '尚未取件'} />
                  <InfoItem label="取件時間" value={formatDateTime(sample.picked_up_at)} />
                </>
              )}
            </>
          )}

        </div>

        <div style={sectionTitleStyle}>此樣品的 WIP / 實驗子單</div>

        {visibleSelectedWips.length === 0 ? (
          <div style={miniEmptyStyle}>
            {shouldMaskSampleForLab(sample, currentUser)
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
                          {wip.wip_no} · 優先級：{priorityText[wip.priority] ?? wip.priority}
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

                      <div style={timelineTimeStyle}>{formatDateTime(history.created_at)}</div>
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
                <button type="button" onClick={onShowMoreHistory} style={secondaryButtonStyle}>
                  查看更多歷程（還有 {sampleHistories.length - historyVisibleCount} 筆）
                </button>
              )}

              {sampleHistories.length > 5 && historyVisibleCount >= sampleHistories.length && (
                <button type="button" onClick={onCollapseHistory} style={secondaryButtonStyle}>
                  收合歷程
                </button>
              )}
            </div>
          </>
        )}

        {shouldShowActionSection && (
          <>
            <div style={sectionTitleStyle}>{isFactoryUser ? '確認取件' : '可執行動作'}</div>

            <div style={actionBarStyle}>
              {canFactoryConfirmPickup && (
                <button
                  onClick={() => onRunSampleAction(sample.id, 'pickup_confirmed')}
                  disabled={submitting}
                  style={primaryButtonStyle}
                >
                  我已到待取件區取回樣品，確認取件
                </button>
              )}

              {!isFactoryUser && selectedSampleInCurrentLab && sample.status === 'pending_receive' && (
                <button
                  onClick={() => onRunSampleAction(sample.id, 'receive')}
                  disabled={submitting}
                  style={primaryButtonStyle}
                >
                  確認收樣
                </button>
              )}

              {!isFactoryUser && selectedSampleInCurrentLab && sample.status === 'received' && (
                <button
                  onClick={() => onGoToWipPage(sample.id)}
                  disabled={submitting}
                  style={primaryButtonStyle}
                >
                  前往 WIP / 分貨
                </button>
              )}

              {!isFactoryUser && selectedSampleInCurrentLab && sample.status === 'split' && (
                <button
                  onClick={() => onGoToWipPage(sample.id)}
                  disabled={submitting}
                  style={secondaryButtonStyle}
                >
                  查看 / 管理 WIP
                </button>
              )}

              {!isFactoryUser &&
                selectedSampleInCurrentLab &&
                sample.status === 'split' &&
                allWipsCompleted && (
                  <button
                    onClick={() => onRunSampleAction(sample.id, 'outbound')}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    通知取件 / 移至待取件區
                  </button>
                )}

              {!isFactoryUser &&
                selectedSampleInCurrentLab &&
                sample.status === 'split' &&
                shouldShowTransferAction && (
                  <button
                    onClick={onGoToTransferPage}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    本 Lab 已完成，前往交接流轉
                  </button>
                )}

              {!isFactoryUser && selectedSampleInCurrentLab && sample.status === 'transferring' && (
                <button onClick={onGoToTransferPage} disabled={submitting} style={secondaryButtonStyle}>
                  前往交接流轉
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </Modal>
  )
}
