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
  fontWeight: 800,
}

export const subtitleStyle: CSSProperties = {
  marginTop: 6,
  color: 'var(--text3)',
  fontSize: 13,
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
  fontSize: 22,
  fontWeight: 900,
}

export const summaryLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

export const currentUserBoxStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
  marginBottom: 14,
}

export const panelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 16,
  marginBottom: 16,
}

export const panelHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 12,
  gap: 12,
}

export const panelHintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

export const filterBarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  marginBottom: 12,
}

export const filterButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 999,
  padding: '7px 11px',
  cursor: 'pointer',
  fontSize: 12,
  fontWeight: 800,
}

export function getFilterButtonStyle(active: boolean): CSSProperties {
  return {
    ...filterButtonStyle,
    ...(active
      ? {
          background: 'rgba(56,139,253,0.16)',
          color: 'var(--blue)',
          border: '1px solid rgba(56,139,253,0.55)',
        }
      : {}),
  }
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

export const emptyStyle: CSSProperties = {
  textAlign: 'center',
  color: 'var(--text3)',
  padding: 28,
  fontSize: 13,
}

export const miniEmptyStyle: CSSProperties = {
  background: 'var(--s2)',
  color: 'var(--text3)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
  fontSize: 13,
}

export const readonlyHintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
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

export const iconButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 10,
  width: 34,
  height: 34,
  cursor: 'pointer',
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
  width: 'min(1080px, 96vw)',
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
  background: 'var(--s1)',
  borderBottom: '1px solid var(--border2)',
  padding: 18,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 16,
  zIndex: 1,
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

export const nextStepBoxStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  borderRadius: 12,
  padding: 14,
}

export const sectionTitleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 900,
  marginTop: 2,
}

export const detailGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 10,
}

export const infoItemStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
}

export const infoLabelStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginBottom: 6,
}

export const infoValueStyle: CSSProperties = {
  color: 'var(--text)',
  fontSize: 13,
  fontWeight: 700,
  wordBreak: 'break-word',
}

export const labListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
}

export const labGroupStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

export const labGroupHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  fontWeight: 900,
  marginBottom: 10,
}

export const wipListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

export const wipCardStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
}

export const timelineStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
}

export const timelineItemStyle: CSSProperties = {
  display: 'flex',
  gap: 10,
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

export const timelineDotStyle: CSSProperties = {
  width: 9,
  height: 9,
  borderRadius: 99,
  background: 'var(--blue)',
  marginTop: 4,
  flexShrink: 0,
}

export const timelineTopRowStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
}

export const timelineTimeStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  whiteSpace: 'nowrap',
}

export const timelineMetaStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
}

export const historyActionRowStyle: CSSProperties = {
  display: 'flex',
  gap: 10,
  flexWrap: 'wrap',
}

export const actionBarStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 10,
}