import type { CSSProperties } from 'react'

export const titleStyle: CSSProperties = {
  fontSize: 24,
  fontWeight: 900,
  letterSpacing: -0.5,
}

export const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 16,
  marginBottom: 24,
}

export const headerActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
}

export const subtitleStyle: CSSProperties = {
  fontSize: 12,
  color: 'var(--text3)',
  marginTop: 4,
  fontFamily: 'monospace',
}

export const layoutStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '320px minmax(0, 1fr)',
  gap: 18,
  alignItems: 'start',
}

export const leftPanelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  overflow: 'hidden',
  position: 'sticky',
  top: 18,
}

export const mainPanelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
  minWidth: 0,
}

export const panelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  overflow: 'hidden',
}

export const panelHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 18px',
  borderBottom: '1px solid var(--border2)',
  gap: 10,
}

export const sectionToggleHeaderStyle: CSSProperties = {
  width: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 18px',
  border: 'none',
  borderBottom: '1px solid var(--border2)',
  background: 'var(--s1)',
  color: 'var(--text2)',
  textAlign: 'left',
  cursor: 'pointer',
  gap: 10,
}

export const sectionHeaderRightStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexShrink: 0,
}

export const sectionButtonGroupStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
}

export const collapseIconStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  fontFamily: 'monospace',
  whiteSpace: 'nowrap',
}

export const panelHintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

export const countBadgeStyle: CSSProperties = {
  fontSize: 10,
  fontFamily: 'monospace',
  color: 'var(--text3)',
  background: 'var(--s3)',
  padding: '3px 8px',
  borderRadius: 999,
  whiteSpace: 'nowrap',
}

export const sampleListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  padding: 12,
  maxHeight: 'calc(100vh - 210px)',
  overflowY: 'auto',
}

export const sampleCardStyle: CSSProperties = {
  display: 'block',
  width: '100%',
  textAlign: 'left',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
  color: 'var(--text2)',
  cursor: 'pointer',
}

export const sampleCardTopStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 10,
  alignItems: 'center',
  marginBottom: 8,
}

export const sampleNameStyle: CSSProperties = {
  fontWeight: 800,
  fontSize: 13,
  marginBottom: 5,
}

export const sampleMetaStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
}

export const monoTextStyle: CSSProperties = {
  fontFamily: 'monospace',
  fontSize: 11,
  color: 'var(--text2)',
}

export const detailGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: 10,
  padding: 18,
}

export const infoItemStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
}

export const infoLabelStyle: CSSProperties = {
  fontSize: 10,
  color: 'var(--text3)',
  fontFamily: 'monospace',
  marginBottom: 6,
}

export const infoValueStyle: CSSProperties = {
  fontSize: 13,
  color: 'var(--text2)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
}

export const labNoticeStyle: CSSProperties = {
  margin: '0 18px 18px',
  padding: 12,
  borderRadius: 10,
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  color: 'var(--text2)',
  fontSize: 13,
  lineHeight: 1.7,
}

export const autoGenerateNoticeStyle: CSSProperties = {
  margin: '18px 18px 0',
  padding: 12,
  borderRadius: 10,
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.28)',
  color: 'var(--green)',
  fontSize: 13,
}

export const warningNoticeStyle: CSSProperties = {
  margin: '18px 18px 0',
  padding: 12,
  borderRadius: 10,
  background: 'rgba(210,153,34,0.12)',
  border: '1px solid rgba(210,153,34,0.28)',
  color: 'var(--yellow)',
  fontSize: 13,
}

export const formListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  padding: 18,
}

export const formCardStyle: CSSProperties = {
  border: '1px solid var(--border2)',
  borderRadius: 12,
  background: 'var(--s2)',
  padding: 14,
}

export const formCardHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 14,
}

export const formActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
}

export const formGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: 12,
  marginBottom: 12,
}

export const fieldStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  fontSize: 12,
  color: 'var(--text3)',
}

export const fieldLabelStyle: CSSProperties = {
  fontSize: 11,
  color: 'var(--text3)',
  fontWeight: 700,
}

export const inputStyle: CSSProperties = {
  width: '100%',
  background: 'var(--s1)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 9,
  padding: '9px 10px',
  outline: 'none',
  fontSize: 13,
}

export const textareaStyle: CSSProperties = {
  ...inputStyle,
  minHeight: 76,
  resize: 'vertical',
}

export const submitBarStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  flexWrap: 'wrap',
  padding: '0 18px 18px',
}

export const labListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  padding: 18,
}

export const labGroupStyle: CSSProperties = {
  border: '1px solid var(--border2)',
  borderRadius: 12,
  background: 'rgba(56,139,253,0.04)',
  padding: 10,
}

export const labGroupHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 10,
  fontSize: 13,
  fontWeight: 800,
}

export const wipListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

export const wipCardStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  padding: 12,
  borderRadius: 10,
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
}

export const wipTitleStyle: CSSProperties = {
  fontWeight: 800,
  fontSize: 13,
}

export const wipMetaStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
}

export const emptyStyle: CSSProperties = {
  padding: 28,
  color: 'var(--text3)',
  fontSize: 13,
  textAlign: 'center',
}

export const errorStyle: CSSProperties = {
  background: 'rgba(248,81,73,0.12)',
  border: '1px solid rgba(248,81,73,0.3)',
  color: 'var(--red)',
  padding: '10px 14px',
  borderRadius: 10,
  marginBottom: 16,
  fontSize: 13,
}

export const successStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.3)',
  color: 'var(--green)',
  padding: '10px 14px',
  borderRadius: 10,
  marginBottom: 16,
  fontSize: 13,
}

export const statusBadgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '4px 9px',
  borderRadius: 999,
  background: 'rgba(56,139,253,0.12)',
  border: '1px solid rgba(56,139,253,0.28)',
  color: 'var(--text2)',
  fontSize: 11,
  fontWeight: 700,
  whiteSpace: 'nowrap',
}

export const autoTagStyle: CSSProperties = {
  display: 'inline-flex',
  marginLeft: 8,
  padding: '2px 7px',
  borderRadius: 999,
  background: 'rgba(63,185,80,0.14)',
  color: 'var(--green)',
  border: '1px solid rgba(63,185,80,0.28)',
  fontSize: 10,
  verticalAlign: 'middle',
}

export const primaryButtonStyle: CSSProperties = {
  background: 'var(--blue)',
  border: '1px solid var(--blue)',
  color: '#fff',
  padding: '8px 14px',
  borderRadius: 8,
  fontSize: 12,
  cursor: 'pointer',
}

export const secondaryButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  padding: '8px 14px',
  borderRadius: 8,
  fontSize: 12,
  cursor: 'pointer',
}

export const smallSecondaryButtonStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  padding: '6px 10px',
  borderRadius: 8,
  fontSize: 11,
  cursor: 'pointer',
}

export const smallDangerButtonStyle: CSSProperties = {
  background: 'rgba(248,81,73,0.1)',
  border: '1px solid rgba(248,81,73,0.28)',
  color: 'var(--red)',
  padding: '6px 10px',
  borderRadius: 8,
  fontSize: 11,
  cursor: 'pointer',
}
