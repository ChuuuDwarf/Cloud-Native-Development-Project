"use client";

import { ApprovalSettingsPanel } from "./components/ApprovalSettingsPanel";
import { HistoryTimeline } from "./components/HistoryTimeline";
import { Modal } from "./components/Modal";
import { OrderCard } from "./components/OrderCard";
import { OrderDetail } from "./components/OrderDetail";
import { Panel } from "./components/Panel";
import { ReasonModal } from "./components/ReasonModal";
import { useApprovePage } from "./hooks/useApprovePage";
import { emptyStyle } from "./styles";

export default function ApprovePage() {
  const {
    user,
    orders,
    masterData,
    usersById,
    quotaOverride,
    setQuotaOverride,
    loading,
    modal,
    setModal,
    reasonModal,
    setReasonModal,
    canApprove,
    actorLabIds,
    loadPendingOrders,
    getDetail,
    getHistory,
    openReasonModal,
    submitReasonModal,
  } = useApprovePage();

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>簽核管理</h1>
        <p style={{ color: "var(--text3)", fontSize: 12, marginTop: 4, fontFamily: "monospace" }}>
          APPROVAL MANAGEMENT · 查看待簽核單據、核准、退回補件、拒絕與特批超額送測
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <ApprovalSettingsPanel
            userLabel={user ? user.name : "尚未登入"}
            actorLabIds={actorLabIds}
            masterData={masterData}
            canApprove={canApprove}
            quotaOverride={quotaOverride}
            onQuotaOverrideChange={setQuotaOverride}
            onReload={() => void loadPendingOrders()}
          />
        </div>

        <div>
          <Panel title={`待簽核委託單（${orders.length} 筆）`}>
            <p style={{ color: "var(--text2)", fontSize: 12, marginBottom: 12 }}>
              只有狀態為「待簽核」的委託單會出現在這裡。主管可進行核准、退回補件或拒絕。
            </p>

            {loading ? (
              <div style={emptyStyle}>載入中...</div>
            ) : orders.length === 0 ? (
              <div style={emptyStyle}>
                目前沒有待簽核委託單。請先到「委託單管理」建立草稿並送出。
              </div>
            ) : (
              <div style={{ display: "grid", gap: 12 }}>
                {orders.map((order) => (
                  <OrderCard
                    key={order.id}
                    order={order}
                    actorLabIds={actorLabIds}
                    masterData={masterData}
                    usersById={usersById}
                    currentUser={user ? { id: user.id, name: user.name } : null}
                    onOpenDetail={(orderId) => void getDetail(orderId)}
                    onOpenHistory={(orderId) => void getHistory(orderId)}
                    onOpenReasonModal={openReasonModal}
                  />
                ))}
              </div>
            )}
          </Panel>
        </div>
      </div>

      {modal.type !== "none" && (
        <Modal title={modal.title} onClose={() => setModal({ type: "none" })}>
          {modal.type === "message" && (
            <p style={{ color: "var(--text2)", lineHeight: 1.8 }}>{modal.message}</p>
          )}
          {modal.type === "detail" && (
            <OrderDetail
              order={modal.order}
              masterData={masterData}
              usersById={usersById}
              currentUser={user ? { id: user.id, name: user.name } : null}
            />
          )}
          {modal.type === "history" && (
            <HistoryTimeline
              history={modal.history}
              usersById={usersById}
              currentUser={user ? { id: user.id, name: user.name } : null}
            />
          )}
        </Modal>
      )}

      {reasonModal.open && (
        <ReasonModal state={reasonModal} setState={setReasonModal} onSubmit={submitReasonModal} />
      )}
    </div>
  );
}
