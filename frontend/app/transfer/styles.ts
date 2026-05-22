import type { CSSProperties } from 'react'

export const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 16,
  alignItems: 'flex-start',
  marginBottom: 16,
}

export const headerActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
}

export const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: 24,
  fontWeight: 900,
}

export const subtitleStyle: CSSProperties = {
  marginTop: 6,
  color: 'var(--text3)',
  fontSize: 13,
  lineHeight: 1.6,
}

export const currentUserBoxStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
  marginBottom: 14,
}

export const currentUserTitleStyle: CSSProperties = {
  fontSize: 12,
  color: 'var(--text3)',
  marginBottom: 4,
}

export const currentUserTextStyle: CSSProperties = {
  fontSize: 13,
  color: 'var(--text)',
  fontWeight: 800,
}

export const summaryGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
  gap: 12,
  marginBottom: 14,
}

export const summaryCardStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
}

export const summaryValueStyle: CSSProperties = {
  fontSize: 24,
  fontWeight: 900,
}

export const summaryLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

export const twoColumnGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(360px, 1fr))',
  gap: 14,
  alignItems: 'start',
  marginBottom: 14,
}

export const panelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 16,
  marginBottom: 14,
}

export const panelHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 12,
}

export const panelTitleStyle: CSSProperties = {
  fontWeight: 900,
  fontSize: 15,
}

export const hintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
  lineHeight: 1.5,
}

export const countBadgeStyle: CSSProperties = {
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

export const errorStyle: CSSProperties = {
  background: 'rgba(247,129,102,0.12)',
  border: '1px solid rgba(247,129,102,0.25)',
  color: 'var(--orange)',
  borderRadius: 10,
  padding: 12,
  fontSize: 13,
  marginBottom: 12,
}

export const successStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.25)',
  color: 'var(--green)',
  borderRadius: 10,
  padding: 12,
  fontSize: 13,
  marginBottom: 12,
}

export const emptyStyle: CSSProperties = {
  textAlign: 'center',
  color: 'var(--text3)',
  padding: 28,
  fontSize: 13,
}

export const candidateListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

export const candidateCardStyle: CSSProperties = {
  width: '100%',
  textAlign: 'left',
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
  cursor: 'pointer',
  color: 'var(--text)',
}

export const selectedCandidateCardStyle: CSSProperties = {
  ...candidateCardStyle,
  border: '1px solid rgba(56,139,253,0.55)',
  background: 'rgba(56,139,253,0.1)',
}

export const candidateTopRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 12,
}

export const candidateTitleStyle: CSSProperties = {
  fontWeight: 900,
  fontSize: 14,
}

export const candidateSubtitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

export const candidateMetaGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: 8,
}

export const infoLineLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
}

export const infoLineValueStyle: CSSProperties = {
  color: 'var(--text2)',
  fontSize: 12,
  fontWeight: 700,
  marginTop: 3,
}

export const statusBadgeStyle: CSSProperties = {
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

export const readyBadgeStyle: CSSProperties = {
  ...statusBadgeStyle,
  background: 'rgba(63,185,80,0.12)',
  color: 'var(--green)',
  border: '1px solid rgba(63,185,80,0.25)',
}

export const warningBadgeStyle: CSSProperties = {
  ...statusBadgeStyle,
  background: 'rgba(210,153,34,0.14)',
  color: 'var(--yellow)',
  border: '1px solid rgba(210,153,34,0.35)',
}

export const detailBoxStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 14,
}

export const sectionTitleStyle: CSSProperties = {
  fontWeight: 900,
  fontSize: 14,
}

export const detailGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
  gap: 10,
}

export const infoBlockStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
}

export const infoBlockLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginBottom: 6,
}

export const infoBlockValueStyle: CSSProperties = {
  color: 'var(--text)',
  fontSize: 13,
  fontWeight: 700,
  wordBreak: 'break-word',
}

export const wipListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

export const wipCardStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
}

export const existingTransferBoxStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.08)',
  border: '1px solid rgba(56,139,253,0.25)',
  borderRadius: 12,
  padding: 12,
}

export const returnBoxStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.08)',
  border: '1px solid rgba(63,185,80,0.25)',
  borderRadius: 12,
  padding: 12,
}

export const existingTransferHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 12,
}

export const createTransferBoxStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

export const warningNoticeStyle: CSSProperties = {
  marginTop: 10,
  background: 'rgba(210,153,34,0.1)',
  border: '1px solid rgba(210,153,34,0.25)',
  color: 'var(--yellow)',
  borderRadius: 10,
  padding: 10,
  fontSize: 12,
  lineHeight: 1.6,
}

export const actionBarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
  marginTop: 12,
}

export const primaryButtonStyle: CSSProperties = {
  background: 'var(--blue)',
  border: '1px solid var(--blue)',
  color: '#fff',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 12,
}

export const secondaryButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 12,
}

export const dangerButtonStyle: CSSProperties = {
  background: 'rgba(247,129,102,0.14)',
  border: '1px solid rgba(247,129,102,0.35)',
  color: 'var(--orange)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 12,
}

export const tableStyle: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
}

export const thStyle: CSSProperties = {
  textAlign: 'left',
  color: 'var(--text3)',
  fontSize: 11,
  padding: '10px 12px',
  whiteSpace: 'nowrap',
}

export const tdStyle: CSSProperties = {
  padding: '11px 12px',
  fontSize: 12.5,
  color: 'var(--text2)',
  whiteSpace: 'nowrap',
}

export const monoTdStyle: CSSProperties = {
  ...tdStyle,
  fontFamily: 'monospace',
  color: 'var(--text)',
}

export const smallActionGroupStyle: CSSProperties = {
  display: 'flex',
  gap: 6,
  alignItems: 'center',
}

export const smallPrimaryButtonStyle: CSSProperties = {
  ...primaryButtonStyle,
  padding: '5px 8px',
  fontSize: 11,
}

export const smallSecondaryButtonStyle: CSSProperties = {
  ...secondaryButtonStyle,
  padding: '5px 8px',
  fontSize: 11,
}

export const smallDangerButtonStyle: CSSProperties = {
  ...dangerButtonStyle,
  padding: '5px 8px',
  fontSize: 11,
}
export const modalBackdropStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 50,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 20,
  background: 'rgba(0,0,0,0.55)',
}

export const modalBackdropButtonStyle: CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: -1,
  opacity: 0,
}

export const modalCardStyle: CSSProperties = {
  width: 'min(920px, 96vw)',
  maxHeight: '90vh',
  overflowY: 'auto',
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 18,
  boxShadow: '0 20px 70px rgba(0,0,0,0.35)',
}

export const modalHeaderStyle: CSSProperties = {
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

export const modalHeaderActionsStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
}

export const modalTitleStyle: CSSProperties = {
  fontSize: 20,
  fontWeight: 900,
}

export const modalSubtitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

export const modalBodyStyle: CSSProperties = {
  padding: 18,
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
}

export const iconButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 10,
  width: 34,
  height: 34,
  cursor: 'pointer',
}

export const modalNoticeStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  color: 'var(--text2)',
  borderRadius: 12,
  padding: 12,
  fontSize: 13,
  lineHeight: 1.6,
}
