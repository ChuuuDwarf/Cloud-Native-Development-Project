import type { CSSProperties } from 'react'

export const pageStyle: CSSProperties = {
  padding: 24,
  color: 'var(--text)',
}

export const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 16,
  alignItems: 'flex-start',
  marginBottom: 18,
}

export const headerActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 10,
}

export const titleStyle: CSSProperties = {
  fontSize: 26,
  fontWeight: 900,
  margin: 0,
}

export const subtitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 13,
  marginTop: 8,
  lineHeight: 1.6,
}

export const cardStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 16,
  padding: 18,
  marginBottom: 18,
}

export const cardHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 14,
  alignItems: 'center',
  marginBottom: 14,
}

export const sectionTitleStyle: CSSProperties = {
  fontSize: 15,
  fontWeight: 900,
}

export const mutedStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  lineHeight: 1.5,
}

export const currentUserGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr minmax(280px, 420px)',
  gap: 14,
  alignItems: 'center',
}

export const profileBoxStyle: CSSProperties = {
  display: 'flex',
  gap: 12,
  alignItems: 'center',
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

export const avatarStyle: CSSProperties = {
  width: 42,
  height: 42,
  borderRadius: 999,
  background: 'rgba(56,139,253,0.18)',
  color: 'var(--blue)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 900,
}

export const selectStyle: CSSProperties = {
  width: '100%',
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  borderRadius: 10,
  padding: '10px 12px',
}

export const codeBlockStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
  overflowX: 'auto',
  color: 'var(--text2)',
  fontSize: 12,
  marginTop: 12,
}

export const pillStyle: CSSProperties = {
  display: 'inline-flex',
  borderRadius: 999,
  padding: '5px 10px',
  color: 'var(--blue)',
  background: 'rgba(56,139,253,0.14)',
  border: '1px solid rgba(56,139,253,0.32)',
  fontSize: 12,
  fontWeight: 800,
}

export const statusPillStyle: CSSProperties = {
  display: 'inline-flex',
  borderRadius: 999,
  padding: '4px 9px',
  color: 'var(--blue)',
  background: 'rgba(56,139,253,0.14)',
  border: '1px solid rgba(56,139,253,0.32)',
  fontSize: 11,
  fontWeight: 800,
  whiteSpace: 'nowrap',
}

export const tabHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  alignItems: 'center',
  flexWrap: 'wrap',
  marginBottom: 14,
}

export const tabBarStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
}

export const tabStyle: CSSProperties = {
  padding: '10px 14px',
  borderWidth: 1,
  borderStyle: 'solid',
  borderRadius: 12,
  background:  'var(--s2)',
  color: 'var(--text2)',
  fontWeight: 700,
  cursor: 'pointer',
}

export const activeTabStyle: CSSProperties = {
  ...tabStyle,
  borderColor:  'rgba(56,139,253,0.55)',
  background: 'rgba(56,139,253,0.16)',
  color: 'var(--blue)',
}

export const primaryButtonStyle: CSSProperties = {
  border: '1px solid var(--blue)',
  background: 'var(--blue)',
  color: '#fff',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 800,
  fontSize: 12,
}

export const secondaryButtonStyle: CSSProperties = {
  border: '1px solid var(--border)',
  background: 'var(--s2)',
  color: 'var(--text2)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 800,
  fontSize: 12,
}

export const ghostButtonStyle: CSSProperties = {
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text2)',
  borderRadius: 10,
  padding: '8px 12px',
  cursor: 'pointer',
  fontWeight: 800,
  fontSize: 12,
}

export const errorStyle: CSSProperties = {
  background: 'rgba(247,129,102,0.12)',
  border: '1px solid rgba(247,129,102,0.25)',
  color: 'var(--orange)',
  borderRadius: 12,
  padding: 12,
  marginBottom: 12,
  fontSize: 13,
}

export const successStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.25)',
  color: 'var(--green)',
  borderRadius: 12,
  padding: 12,
  marginBottom: 12,
  fontSize: 13,
}

export const noticeStyle: CSSProperties = {
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  color: 'var(--text2)',
  borderRadius: 12,
  padding: 12,
  marginBottom: 12,
  fontSize: 13,
}

export const formBoxStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  padding: 14,
  marginBottom: 16,
}

export const formHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 14,
  marginBottom: 14,
}

export const formGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 12,
}

export const fieldStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
}

export const fieldTitleStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  fontWeight: 800,
}

export const inputStyle: CSSProperties = {
  width: '100%',
  background: 'var(--s1)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  borderRadius: 10,
  padding: '10px 12px',
  outline: 'none',
}

export const wideFieldStyle: CSSProperties = {
  gridColumn: '1 / -1',
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

export const experimentMatrixStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: 10,
}

export const experimentLabBoxStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

export const experimentLabTitleStyle: CSSProperties = {
  fontWeight: 900,
  marginBottom: 8,
}

export const experimentItemGridStyle: CSSProperties = {
  display: 'grid',
  gap: 8,
}

export const checkboxLabelStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  alignItems: 'center',
  color: 'var(--text2)',
  fontSize: 13,
}

export const formActionStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  marginTop: 14,
}

export const tableTitleStyle: CSSProperties = {
  fontSize: 14,
  fontWeight: 900,
  marginBottom: 8,
}

export const tableWrapStyle: CSSProperties = {
  overflowX: 'auto',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  marginTop: 10,
}

export const tableStyle: CSSProperties = {
  width: '100%',
  borderCollapse: 'collapse',
}

export const thStyle: CSSProperties = {
  textAlign: 'left',
  background: 'var(--s2)',
  color: 'var(--text3)',
  fontSize: 11,
  padding: '10px 12px',
  whiteSpace: 'nowrap',
}

export const tdStyle: CSSProperties = {
  borderTop: '1px solid var(--border2)',
  color: 'var(--text2)',
  fontSize: 12,
  padding: '10px 12px',
  whiteSpace: 'nowrap',
}

export const monoTdStyle: CSSProperties = {
  ...tdStyle,
  fontFamily: 'monospace',
  color: 'var(--text)',
}

export const emptyTdStyle: CSSProperties = {
  ...tdStyle,
  textAlign: 'center',
  color: 'var(--text3)',
  padding: 24,
}

export const trStyle: CSSProperties = {
  verticalAlign: 'top',
}

export const successMiniTextStyle: CSSProperties = {
  color: 'var(--green)',
  fontWeight: 800,
  fontSize: 12,
}

export const masterGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
  gap: 12,
}

export const miniCardStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
}

export const chipWrapStyle: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 8,
  marginTop: 10,
}

export const outlinePillStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  border: '1px solid var(--border)',
  borderRadius: 999,
  padding: '5px 9px',
  color: 'var(--text2)',
  fontSize: 12,
}

export const mutedMonoStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  fontFamily: 'monospace',
}
