import { useState } from "react";
import type {
  CurrentUser,
  Sample,
  SampleAction,
  SampleHistory,
  Transfer,
  Wip,
  WipExecutionDetail,
} from "../types";
import { priorityText, wipStatusText } from "../constants";
import { InfoItem } from "./InfoItem";
import { Modal } from "./Modal";
import { StatusBadge } from "./StatusBadge";
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
} from "../styles";
import {
  formatDateTime,
  formatStatusChange,
  formatSampleExperimentRequirement,
  getDisplaySampleLocation,
  getDisplaySampleStatus,
  getUserLab,
  isLabUser as checkIsLabUser,
  shouldMaskSampleForLab,
} from "../utils/sampleDisplay";

function formatExperimentRequirement(experimentItem: string | null) {
  const displayText = formatSampleExperimentRequirement(experimentItem);
  if (displayText === "-") return "-";

  const items = displayText
    .split("、")
    .map((item) => item.trim())
    .filter(Boolean);

  if (items.length <= 1) return displayText;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {items.map((item, index) => (
        <div key={`${item}-${index}`}>{item}</div>
      ))}
    </div>
  );
}

function formatExecutionAction(action: string) {
  if (action === "created_from_split") return "分貨建立";
  if (action === "send_to_schedule") return "送入排程";
  return action;
}

function WipExecutionSummary({
  detail,
  loading,
}: {
  detail?: WipExecutionDetail;
  loading: boolean;
}) {
  if (loading && !detail) {
    return <span style={{ color: "var(--text3)" }}>機台履歷載入中...</span>;
  }

  if (!detail) {
    return <span style={{ color: "var(--text3)" }}>尚無上機紀錄</span>;
  }

  const machineText = detail.machineId ? `機台 ${detail.machineId}` : "未指定機台";
  const recipeText = detail.recipe ? ` · ${detail.recipe}` : "";
  const operatorText = detail.operator ? ` · ${detail.operator}` : "";

  return (
    <span style={{ color: "var(--text3)" }}>
      {machineText}
      {recipeText}
      {operatorText}
    </span>
  );
}

function WipExecutionHistoryModal({
  wipNo,
  detail,
  loading,
  onClose,
}: {
  wipNo: string;
  detail?: WipExecutionDetail;
  loading: boolean;
  onClose: () => void;
}) {
  return (
    <Modal onClose={onClose}>
      <div style={modalHeaderStyle}>
        <div>
          <div style={modalTitleStyle}>機台履歷</div>
          <div style={modalSubtitleStyle}>{wipNo}</div>
        </div>

        <button type="button" onClick={onClose} style={iconButtonStyle}>
          ✕
        </button>
      </div>

      <div style={modalBodyStyle}>
        {loading && !detail ? (
          <div style={miniEmptyStyle}>機台履歷載入中...</div>
        ) : !detail ? (
          <div style={miniEmptyStyle}>尚無上機 / 下機履歷。</div>
        ) : (
          <>
            <div style={sectionTitleStyle}>執行資訊</div>

            <div style={detailGridStyle}>
              <InfoItem label="機台" value={detail.machineId ?? "-"} />
              <InfoItem label="Recipe" value={detail.recipe ?? "-"} />
              <InfoItem label="操作人" value={detail.operator ?? "-"} />
              <InfoItem label="執行狀態" value={detail.status} />
              <InfoItem label="進度" value={`${detail.progress}%`} />
              <InfoItem label="數據驗證" value={detail.dataVerified ? "已驗證" : "尚未驗證"} />
              <InfoItem label="上機時間" value={formatDateTime(detail.checkInAt)} />
              <InfoItem label="下機時間" value={formatDateTime(detail.checkOutAt)} />
              <InfoItem label="原始數據" value={detail.rawDataUrl ?? "-"} />
            </div>

            {detail.resultNote && (
              <>
                <div style={sectionTitleStyle}>結果備註</div>
                <div
                  style={{
                    padding: 12,
                    borderRadius: 12,
                    border: "1px solid var(--line)",
                    background: "var(--bg2)",
                    fontSize: 13,
                    color: "var(--text2)",
                    lineHeight: 1.7,
                  }}
                >
                  {detail.resultNote}
                </div>
              </>
            )}

            <div style={sectionTitleStyle}>執行歷程</div>

            {detail.history.length === 0 ? (
              <div style={miniEmptyStyle}>尚無執行履歷。</div>
            ) : (
              <div style={timelineStyle}>
                {detail.history.map((event, index) => (
                  <div key={`${event.action}-${event.time}-${index}`} style={timelineItemStyle}>
                    <div style={timelineDotStyle} />

                    <div style={{ flex: 1 }}>
                      <div style={timelineTopRowStyle}>
                        <div style={{ fontWeight: 800, fontSize: 13 }}>
                          {formatExecutionAction(event.action)}
                        </div>
                        <div style={timelineTimeStyle}>{formatDateTime(event.time)}</div>
                      </div>

                      <div style={timelineMetaStyle}>
                        {event.by ?? "系統"}
                        {event.note ? ` · ${event.note}` : ""}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}

type SampleDetailModalProps = {
  sample: Sample;
  currentUser: CurrentUser;
  selectedSampleOutgoingTransfer?: Transfer;
  visibleSelectedWips: Wip[];
  wipsByLab: Record<string, Wip[]>;
  wipExecutionDetails: Record<string, WipExecutionDetail>;
  wipExecutionLoading: boolean;
  sampleHistories: SampleHistory[];
  visibleHistories: SampleHistory[];
  historyLoading: boolean;
  historyVisibleCount: number;
  submitting: boolean;
  canFactoryConfirmPickup: boolean;
  selectedSampleInCurrentLab: boolean;
  allWipsCompleted: boolean;
  shouldShowTransferAction: boolean;
  shouldShowActionSection: boolean;
  isFactoryUser: boolean;
  nextStepText: string;
  onClose: () => void;
  onShowMoreHistory: () => void;
  onCollapseHistory: () => void;
  onRunSampleAction: (sampleId: string, action: SampleAction) => void;
  onGoToWipPage: (sampleId: string) => void;
  onGoToTransferPage: () => void;
};

export function SampleDetailModal({
  sample,
  currentUser,
  selectedSampleOutgoingTransfer,
  visibleSelectedWips,
  wipsByLab,
  wipExecutionDetails,
  wipExecutionLoading,
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
  const [historyTargetWipNo, setHistoryTargetWipNo] = useState<string | null>(null);

  const currentLab = getUserLab(currentUser);
  const shouldMaskForCurrentLab = shouldMaskSampleForLab(sample, currentUser);
  const isLabUser = checkIsLabUser(currentUser);

  const ownLabReceiveHistory = sampleHistories.find((history) => {
    if (history.action !== "receive") return false;
    if (!isLabUser) return true;
    return history.lab_name === currentLab;
  });

  const isIncomingTransferWaitingReceive = Boolean(
    isLabUser &&
      selectedSampleInCurrentLab &&
      selectedSampleOutgoingTransfer &&
      selectedSampleOutgoingTransfer.to_lab === currentLab &&
      selectedSampleOutgoingTransfer.status === "transferring" &&
      sample.status === "pending_receive"
  );

  const displayReceivedBy =
    ownLabReceiveHistory?.operator_name ??
    (shouldMaskForCurrentLab
      ? selectedSampleOutgoingTransfer?.handed_by ?? sample.received_by ?? "尚未收樣"
      : sample.received_by ?? "尚未收樣");

  const displayReceivedAt = ownLabReceiveHistory?.created_at ?? sample.received_at;

  const transferReceiverText =
    selectedSampleOutgoingTransfer?.received_by ??
    (selectedSampleOutgoingTransfer?.to_lab
      ? `${selectedSampleOutgoingTransfer.to_lab} 尚未確認接收`
      : "接收實驗室尚未確認接收");

  const transferredOutStatusText = (() => {
    if (!selectedSampleOutgoingTransfer) return "已離開本實驗室";

    if (selectedSampleOutgoingTransfer.status === "pending") {
      return `交接單已建立，尚未送出至 ${
        selectedSampleOutgoingTransfer.to_lab ?? "接收實驗室"
      }`;
    }

    if (selectedSampleOutgoingTransfer.status === "transferring") {
      return `等待 ${selectedSampleOutgoingTransfer.to_lab ?? "接收實驗室"} 確認接收`;
    }

    if (selectedSampleOutgoingTransfer.status === "received") {
      return "接收實驗室已確認接收";
    }

    if (selectedSampleOutgoingTransfer.status === "cancelled") {
      return "交接已取消";
    }

    return selectedSampleOutgoingTransfer.status;
  })();

  const shouldShowPickupInfo =
    !shouldMaskForCurrentLab &&
    !isIncomingTransferWaitingReceive &&
    (sample.status === "outbound" || sample.status === "picked_up");

  return (
    <>
      <Modal onClose={onClose}>
        <div style={modalHeaderStyle}>
          <div>
            <div style={modalTitleStyle}>{sample.sample_no}</div>
            <div style={modalSubtitleStyle}>委託單編號 {sample.order_no}</div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <StatusBadge
              status={getDisplaySampleStatus(sample, currentUser, selectedSampleOutgoingTransfer)}
            />
            <button type="button" onClick={onClose} style={iconButtonStyle}>
              ✕
            </button>
          </div>
        </div>

        <div style={modalBodyStyle}>
          <div style={nextStepBoxStyle}>
            <div style={{ fontWeight: 800, marginBottom: 6 }}>下一步判斷</div>
            <div style={{ color: "var(--text2)", fontSize: 13 }}>{nextStepText}</div>
          </div>

          <div style={sectionTitleStyle}>樣品詳細資料</div>

          <div style={detailGridStyle}>
            <InfoItem label="樣品編號" value={sample.sample_no} />
            <InfoItem label="委託單編號" value={sample.order_no} />
            <InfoItem label="樣品名稱" value={sample.sample_name ?? "-"} />
            <InfoItem label="實驗需求" value={formatExperimentRequirement(sample.experiment_item)} />
            <InfoItem label="申請人" value={sample.applicant_name ?? "-"} />
            <InfoItem label="申請部門" value={sample.applicant_department ?? "-"} />
            <InfoItem
              label="目前位置"
              value={getDisplaySampleLocation(sample, currentUser, selectedSampleOutgoingTransfer)}
            />

            {isIncomingTransferWaitingReceive ? (
              <>
                <InfoItem
                  label="來源實驗室"
                  value={selectedSampleOutgoingTransfer?.from_lab ?? "-"}
                />
                <InfoItem label="交接人" value={selectedSampleOutgoingTransfer?.handed_by ?? "-"} />
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
                    {selectedSampleOutgoingTransfer.status === "received" ? (
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
                            selectedSampleOutgoingTransfer.status === "pending"
                              ? "建立交接時間"
                              : "交接時間"
                          }
                          value={formatDateTime(
                            selectedSampleOutgoingTransfer.status === "pending"
                              ? selectedSampleOutgoingTransfer.created_at
                              : selectedSampleOutgoingTransfer.transferred_at
                          )}
                        />
                      </>
                    )}
                  </>
                )}

                {shouldShowPickupInfo && (
                  <>
                    <InfoItem label="取件人" value={sample.picked_up_by ?? "尚未取件"} />
                    <InfoItem label="取件時間" value={formatDateTime(sample.picked_up_at)} />
                  </>
                )}
              </>
            )}
          </div>

          <div style={sectionTitleStyle}>WIP / 實驗子單</div>

          {visibleSelectedWips.length === 0 ? (
            <div style={miniEmptyStyle}>
              {shouldMaskSampleForLab(sample, currentUser)
                ? "此樣品已轉出，本畫面不顯示接收實驗室的 WIP / 實驗子單細節。"
                : "目前尚未建立 WIP / 實驗子單。"}
            </div>
          ) : (
            <div style={labListStyle}>
              {Object.entries(wipsByLab).map(([labName, labWips]) => (
                <div key={labName} style={labGroupStyle}>
                  <div style={labGroupHeaderStyle}>
                    <span>{labName}</span>
                    <span style={countBadgeStyle}>{labWips.length} 個實驗</span>
                  </div>

                  {labWips.map((wip) => {
                    const executionDetail = wipExecutionDetails[wip.wip_no];

                    return (
                      <div key={wip.id} style={wipCardStyle}>
                        <div>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 8,
                              fontWeight: 800,
                              fontSize: 13,
                            }}
                          >
                            <span>{wip.experiment_item ?? "未命名實驗"}</span>

                            <button
                              type="button"
                              title="查看機台履歷"
                              aria-label="查看機台履歷"
                              onClick={() => setHistoryTargetWipNo(wip.wip_no)}
                              style={{
                                width: 22,
                                height: 22,
                                borderRadius: 999,
                                border: "1px solid var(--line)",
                                background: "var(--bg)",
                                color: "var(--text2)",
                                cursor: "pointer",
                                display: "grid",
                                placeItems: "center",
                                fontSize: 12,
                                lineHeight: 1,
                                padding: 0,
                                flex: "0 0 auto",
                              }}
                            >
                              📜
                            </button>
                          </div>

                          <div style={{ color: "var(--text3)", fontSize: 11, marginTop: 4 }}>
                            {wip.wip_no} · 優先級：{priorityText[wip.priority] ?? wip.priority}
                          </div>

                          <div style={{ color: "var(--text3)", fontSize: 11, marginTop: 4 }}>
                            <WipExecutionSummary
                              detail={executionDetail}
                              loading={wipExecutionLoading}
                            />
                          </div>
                        </div>

                        <div
                          style={{
                            textAlign: "right",
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "flex-end",
                            gap: 4,
                          }}
                        >
                          <div style={{ fontSize: 12, fontWeight: 700 }}>
                            {executionDetail?.status ?? wipStatusText[wip.status] ?? wip.status}
                          </div>

                          <div style={{ color: "var(--text3)", fontSize: 11 }}>
                            進度 {executionDetail?.progress ?? wip.progress}% ·{" "}
                            {wip.current_location ?? "-"}
                          </div>
                        </div>
                      </div>
                    );
                  })}
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
                        {" · "}
                        {history.operator_name ?? "系統"}
                        {history.lab_name ? ` · ${history.lab_name}` : ""}
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
              <div style={sectionTitleStyle}>{isFactoryUser ? "確認取件" : "可執行動作"}</div>

              <div style={actionBarStyle}>
                {canFactoryConfirmPickup && (
                  <button
                    type="button"
                    onClick={() => onRunSampleAction(sample.id, "pickup_confirmed")}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    我已到待取件區取回樣品，確認取件
                  </button>
                )}

                {!isFactoryUser &&
                  selectedSampleInCurrentLab &&
                  sample.status === "pending_receive" && (
                    <button
                      type="button"
                      onClick={() => onRunSampleAction(sample.id, "receive")}
                      disabled={submitting}
                      style={primaryButtonStyle}
                    >
                      確認收樣
                    </button>
                  )}

                {!isFactoryUser && selectedSampleInCurrentLab && sample.status === "received" && (
                  <button
                    type="button"
                    onClick={() => onGoToWipPage(sample.id)}
                    disabled={submitting}
                    style={primaryButtonStyle}
                  >
                    前往 WIP / 分貨
                  </button>
                )}

                {!isFactoryUser &&
                  selectedSampleInCurrentLab &&
                  (sample.status === "split" || sample.status === "pending_transfer") && (
                    <button
                      type="button"
                      onClick={() => onGoToWipPage(sample.id)}
                      disabled={submitting}
                      style={secondaryButtonStyle}
                    >
                      查看 / 管理 WIP / 分貨
                    </button>
                  )}

                {!isFactoryUser &&
                  selectedSampleInCurrentLab &&
                  (sample.status === "split" || sample.status === "pending_transfer") &&
                  allWipsCompleted && (
                    <button
                      type="button"
                      onClick={() => onRunSampleAction(sample.id, "outbound")}
                      disabled={submitting}
                      style={primaryButtonStyle}
                    >
                      通知取件 / 移至待取件區
                    </button>
                  )}

                {!isFactoryUser &&
                  selectedSampleInCurrentLab &&
                  (sample.status === "split" || sample.status === "pending_transfer") &&
                  shouldShowTransferAction && (
                    <button
                      type="button"
                      onClick={onGoToTransferPage}
                      disabled={submitting}
                      style={primaryButtonStyle}
                    >
                      本 Lab 已完成，前往交接流轉
                    </button>
                  )}

                {!isFactoryUser &&
                  selectedSampleInCurrentLab &&
                  sample.status === "transferring" && (
                    <button
                      type="button"
                      onClick={onGoToTransferPage}
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

      {historyTargetWipNo && (
        <WipExecutionHistoryModal
          wipNo={historyTargetWipNo}
          detail={wipExecutionDetails[historyTargetWipNo]}
          loading={wipExecutionLoading}
          onClose={() => setHistoryTargetWipNo(null)}
        />
      )}
    </>
  );
}