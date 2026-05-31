import type { CSSProperties, ReactNode } from "react";
import { formatExperimentSummary } from "@/lib/experimentSummary";
import type { Transfer, TransferCandidate, ReturnCandidate, Wip } from "../types";
import { priorityText, sampleStatusText, transferStatusText, wipStatusText } from "../constants";
import { formatDateTime } from "../utils/transferFlow";
import {
  summaryCardStyle,
  summaryValueStyle,
  summaryLabelStyle,
  hintStyle,
  infoLineLabelStyle,
  infoLineValueStyle,
  statusBadgeStyle,
  readyBadgeStyle,
  warningBadgeStyle,
  detailBoxStyle,
  sectionTitleStyle,
  detailGridStyle,
  transferModalDetailGridStyle,
  infoBlockStyle,
  infoBlockLabelStyle,
  infoBlockValueStyle,
  wipListStyle,
  wipCardStyle,
  existingTransferBoxStyle,
  returnBoxStyle,
  existingTransferHeaderStyle,
  createTransferBoxStyle,
  warningNoticeStyle,
  actionBarStyle,
  primaryButtonStyle,
  secondaryButtonStyle,
  dangerButtonStyle,
  modalBackdropStyle,
  modalBackdropButtonStyle,
  modalCardStyle,
  modalHeaderStyle,
  modalHeaderActionsStyle,
  modalTitleStyle,
  modalSubtitleStyle,
  modalBodyStyle,
  iconButtonStyle,
  modalNoticeStyle,
} from "../styles";

function ExperimentRequirementLines({ value }: { value: string | null | undefined }) {
  const displayText = formatExperimentSummary(value);

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

export function TransferModal({
  transfer,
  currentLab,
  submitting,
  onClose,
  onSendTransfer,
  onCancelTransfer,
}: {
  transfer: Transfer;
  currentLab: string;
  submitting: boolean;
  onClose: () => void;
  onSendTransfer: (transfer: Transfer) => void;
  onCancelTransfer: (transfer: Transfer) => void;
}) {
  return (
    <div style={modalBackdropStyle}>
      <div style={modalCardStyle}>
        <div style={modalHeaderStyle}>
          <div>
            <div style={modalTitleStyle}>{transfer.transfer_no ?? transfer.id.slice(0, 8)}</div>
            <div style={modalSubtitleStyle}>
              {transfer.from_lab ?? "-"} → {transfer.to_lab ?? "-"}
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

          <div style={transferModalDetailGridStyle}>
            <InfoBlock label="交接單號" value={transfer.transfer_no ?? transfer.id} />
            <InfoBlock label="樣品" value={transfer.sample_no ?? "-"} />
            <InfoBlock label="委託單號" value={transfer.order_no ?? "-"} />
            <InfoBlock label="樣品編號" value={transfer.sample_no ?? "-"} />

            <InfoBlock label="來源實驗室" value={transfer.from_lab ?? "-"} />
            <InfoBlock label="目的實驗室" value={transfer.to_lab ?? "-"} />
            <InfoBlock label="交接人" value={transfer.handed_by ?? "-"} />
            <InfoBlock label="送出時間" value={formatDateTime(transfer.transferred_at)} />

            <InfoBlock label="簽收人" value={transfer.received_by ?? "-"} />
            <InfoBlock label="簽收時間" value={formatDateTime(transfer.received_at)} />
            <InfoBlock label="建立時間" value={formatDateTime(transfer.created_at)} />
            <InfoBlock label="更新時間" value={formatDateTime(transfer.updated_at)} />
            <InfoBlock label="備註" value={transfer.note ?? "-"} style={{ gridColumn: "1 / -1" }} />
          </div>

          <div style={modalNoticeStyle}>
            {transfer.status === "pending" && "這筆交接單尚未送出，只有來源實驗室可以送出或取消。"}
            {transfer.status === "transferring" &&
              "交接單已送出，樣品已移到目的實驗室收樣區，等待目的實驗室在收樣管理確認收樣。"}
            {transfer.status === "received" && "目的實驗室已確認收樣，交接流程完成。"}
            {transfer.status === "cancelled" && "這筆交接單已取消。"}
          </div>

          <div style={actionBarStyle}>
            {transfer.from_lab === currentLab && transfer.status === "pending" && (
              <button
                type="button"
                disabled={submitting}
                onClick={() => onSendTransfer(transfer)}
                style={primaryButtonStyle}
              >
                送出到對方待收樣區
              </button>
            )}

            {transfer.from_lab === currentLab && transfer.status === "pending" && (
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
      <button type="button" aria-label="close" style={modalBackdropButtonStyle} onClick={onClose} />
    </div>
  );
}

export function TransferDetail({
  candidate,
  currentLab,
  submitting,
  onCreateTransfer,
  onSendTransfer,
  onCancelTransfer,
}: {
  candidate: TransferCandidate;
  currentLab: string;
  submitting: boolean;
  onCreateTransfer: (candidate: TransferCandidate) => void;
  onSendTransfer: (transfer: Transfer) => void;
  onCancelTransfer: (transfer: Transfer) => void;
}) {
  return (
    <div style={detailBoxStyle}>
      <div style={sectionTitleStyle}>樣品資訊</div>

      <div style={detailGridStyle}>
        <InfoBlock label="樣品編號" value={candidate.sample.sample_no} />
        <InfoBlock label="委託單號" value={candidate.sample.order_no} />
        <InfoBlock label="樣品名稱" value={candidate.sample.sample_name ?? "-"} />
        <InfoBlock
          label="實驗需求"
          value={<ExperimentRequirementLines value={candidate.sample.experiment_item} />}
        />
        <InfoBlock label="目前位置" value={candidate.sample.current_location ?? "-"} />
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
            <div key={`${experiment.lab_name}-${experiment.experiment_item}`} style={wipCardStyle}>
              <div>
                <div style={{ fontWeight: 800, fontSize: 13 }}>{experiment.experiment_item}</div>
                <div style={hintStyle}>{experiment.lab_name} · 尚未建立 WIP</div>
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
            <InfoBlock label="交接人" value={candidate.existingTransfer.handed_by ?? "-"} />
            <InfoBlock label="備註" value={candidate.existingTransfer.note ?? "-"} />
          </div>

          <div style={actionBarStyle}>
            {candidate.existingTransfer.from_lab === currentLab &&
              candidate.existingTransfer.status === "pending" && (
                <button
                  onClick={() => onSendTransfer(candidate.existingTransfer as Transfer)}
                  disabled={submitting}
                  style={primaryButtonStyle}
                >
                  送出到對方待收樣區
                </button>
              )}

            {candidate.existingTransfer.from_lab === currentLab &&
              candidate.existingTransfer.status === "pending" && (
                <button
                  onClick={() => onCancelTransfer(candidate.existingTransfer as Transfer)}
                  disabled={submitting}
                  style={dangerButtonStyle}
                >
                  取消交接
                </button>
              )}

            {candidate.existingTransfer.status === "transferring" && (
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
              下一個 Lab 的 WIP 尚未建立。樣品送到對方待收樣區後，對方會在 /sample 收樣，再到 /wip
              建立自己的 WIP。
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
  );
}

export function ReturnDetail({
  candidate,
  submitting,
  onNotifyPickup,
}: {
  candidate: ReturnCandidate;
  submitting: boolean;
  onNotifyPickup: (candidate: ReturnCandidate) => void;
}) {
  const isOutbound = candidate.sample.status === "outbound";

  return (
    <div style={detailBoxStyle}>
      <div style={sectionTitleStyle}>樣品資訊</div>

      <div style={detailGridStyle}>
        <InfoBlock label="樣品編號" value={candidate.sample.sample_no} />
        <InfoBlock label="委託單號" value={candidate.sample.order_no} />
        <InfoBlock label="樣品名稱" value={candidate.sample.sample_name ?? "-"} />
        <InfoBlock
          label="實驗需求"
          value={<ExperimentRequirementLines value={candidate.sample.experiment_item} />}
          style={{ gridColumn: "1 / -1" }}
        />
        <InfoBlock label="目前位置" value={candidate.sample.current_location ?? "-"} />
        <InfoBlock
          label="樣品狀態"
          value={sampleStatusText[candidate.sample.status] ?? candidate.sample.status}
        />
        <InfoBlock label="申請人" value={candidate.sample.applicant_name ?? "-"} />
        <InfoBlock label="申請部門" value={candidate.sample.applicant_department ?? "-"} />
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
              {isOutbound ? "已通知使用者取件" : "尚未通知使用者取件"}
            </div>
            <div style={hintStyle}>
              {isOutbound
                ? "樣品目前在待取件區，等待廠區使用者取回。"
                : "所有 WIP 已完成，可以通知原使用者取件。"}
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
            // 'pickup_confirmed' is reserved for the original requester
            // (see backend _validate_sample_action_permission). Lab roles
            // no longer flip the sample on the requester's behalf — wait
            // for the user's own confirmation on /sample 我的樣品追蹤.
            <span style={{ ...hintStyle, fontStyle: "italic" }}>
              等待使用者本人於「我的樣品追蹤」確認取件
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={summaryCardStyle}>
      <div style={summaryValueStyle}>{value}</div>
      <div style={summaryLabelStyle}>{label}</div>
    </div>
  );
}

export function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={infoLineLabelStyle}>{label}</div>
      <div style={infoLineValueStyle}>{value}</div>
    </div>
  );
}

export function InfoBlock({
  label,
  value,
  style,
}: {
  label: string;
  value: ReactNode | null | undefined;
  style?: CSSProperties;
}) {
  return (
    <div style={{ ...infoBlockStyle, ...style }}>
      <div style={infoBlockLabelStyle}>{label}</div>
      <div style={infoBlockValueStyle}>{value ?? "-"}</div>
    </div>
  );
}

export function WipCard({ wip }: { wip: Wip }) {
  return (
    <div style={wipCardStyle}>
      <div>
        <div style={{ fontWeight: 800, fontSize: 13 }}>{wip.experiment_item ?? "未命名實驗"}</div>
        <div style={hintStyle}>
          {wip.wip_no} · {wip.lab_name ?? "未指定 Lab"} ·{" "}
          {priorityText[wip.priority] ?? wip.priority}
        </div>
      </div>

      <div style={{ textAlign: "right" }}>
        <StatusBadge status={wip.status} type="wip" />
        <div style={hintStyle}>進度 {wip.progress}%</div>
      </div>
    </div>
  );
}

export function StatusBadge({
  status,
  type = "transfer",
}: {
  status: string;
  type?: "transfer" | "wip" | "sample";
}) {
  let text = status;

  if (type === "wip") {
    text = wipStatusText[status] ?? status;
  } else if (type === "sample") {
    text = sampleStatusText[status] ?? status;
  } else {
    text = transferStatusText[status] ?? status;
  }

  return <span style={statusBadgeStyle}>{text}</span>;
}
