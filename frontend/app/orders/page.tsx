"use client";

import { HistoryTimeline } from "./components/HistoryTimeline";
import { Modal } from "./components/common";
import { OrderDetail } from "./components/OrderDetail";
import { OrderForm } from "./components/OrderForm";
import { OrderList } from "./components/OrderList";
import { QuotaSummary } from "./components/QuotaSummary";
import { useOrdersPage } from "./hooks/useOrdersPage";
import { orderWorkspaceGridStyle } from "./styles";

export default function OrdersPage() {
  const page = useOrdersPage();

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>委託單管理</h1>
        <p style={{ color: "var(--text3)", fontSize: 12, marginTop: 4, fontFamily: "monospace" }}>
          ORDER MANAGEMENT · 建立、送出、修改補件與追蹤送測申請
        </p>
      </div>

      <div style={{ display: "grid", gap: 16 }}>
        <div style={orderWorkspaceGridStyle}>
          <QuotaSummary
            quotaSettings={page.quotaSettings}
            masterData={page.masterData}
            usersById={page.usersById}
            currentUser={{ id: page.currentUserId, name: page.currentUserName }}
            onRefresh={() => void page.loadQuotas()}
          />
          <OrderList
            orders={page.orders}
            filteredOrders={page.filteredOrders}
            masterData={page.masterData}
            currentUser={{ id: page.currentUserId, name: page.currentUserName }}
            usersById={page.usersById}
            loading={page.loading}
            activeStatusFilter={page.activeStatusFilter}
            statusCounts={page.statusCounts}
            onFilterChange={page.setActiveStatusFilter}
            onCreate={page.openCreateOrder}
            onRefresh={() => void page.loadOrders()}
            onDetail={(orderId) => void page.getDetail(orderId)}
            onHistory={(orderId) => void page.getHistory(orderId)}
            onEdit={page.startEditOrder}
            onAction={(order, action) => void page.doAction(order, action)}
            onDelete={(order) => void page.deleteOrder(order)}
          />
        </div>
      </div>

      {page.formModalOpen && (
        <Modal title={page.editingOrderId ? "修改委託單 " + (page.editingOrderNo || "") : "新增委託單"} onClose={page.closeFormModal}>
          <OrderForm
            currentUserName={page.currentUserName}
            applicantId={page.applicantId}
            currentUser={{ id: page.currentUserId, name: page.currentUserName }}
            usersById={page.usersById}
            departmentId={page.departmentId}
            setDepartmentId={page.setDepartmentId}
            priority={page.priority}
            setPriority={page.setPriority}
            masterData={page.masterData}
            quotaCheck={page.quotaCheck}
            templates={page.templates}
            selectedTemplateId={page.selectedTemplateId}
            templateName={page.templateName}
            setTemplateName={page.setTemplateName}
            items={page.items}
            sampleGroups={page.sampleGroups}
            editingOrderId={page.editingOrderId}
            editingOrderNo={page.editingOrderNo}
            submitting={page.submitting}
            onCheckQuota={() => void page.checkQuotaForForm()}
            onSaveTemplate={page.saveCurrentTemplate}
            onApplyTemplate={page.applyTemplate}
            onAddSample={page.addSample}
            onSampleChange={page.updateSampleGroup}
            onToggleExperiment={page.toggleExperimentForSample}
            onMoveExperiment={page.moveExperiment}
            onRemoveItem={page.removeItem}
            onClose={page.closeFormModal}
            onCreate={(submitAfterCreate) => void page.createOrder(submitAfterCreate)}
            onUpdate={() => void page.updateOrder()}
          />
        </Modal>
      )}

      {page.modal.type !== "none" && (
        <Modal title={page.modal.title} onClose={() => page.setModal({ type: "none" })}>
          {page.modal.type === "message" && <p style={{ color: "var(--text2)", lineHeight: 1.8 }}>{page.modal.message}</p>}
          {page.modal.type === "detail" && (
            <OrderDetail
              order={page.modal.order}
              masterData={page.masterData}
              currentUser={{ id: page.currentUserId, name: page.currentUserName }}
              usersById={page.usersById}
            />
          )}
          {page.modal.type === "history" && (
            <HistoryTimeline
              history={page.modal.history}
              currentUser={{ id: page.currentUserId, name: page.currentUserName }}
              usersById={page.usersById}
            />
          )}
        </Modal>
      )}
    </div>
  );
}
