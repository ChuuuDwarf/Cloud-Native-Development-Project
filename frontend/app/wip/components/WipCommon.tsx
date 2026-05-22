import type { KeyboardEvent, ReactNode } from 'react'
import { wipStatusText } from '../constants'
import {
  panelStyle,
  panelHintStyle,
  infoItemStyle,
  infoLabelStyle,
  infoValueStyle,
  sectionToggleHeaderStyle,
  sectionHeaderRightStyle,
  collapseIconStyle,
  fieldStyle,
  fieldLabelStyle,
  statusBadgeStyle,
} from '../styles'

export function CollapsibleSection({
  title,
  hint,
  right,
  open,
  onToggle,
  children,
}: {
  title: string
  hint?: string
  right?: ReactNode
  open: boolean
  onToggle: () => void
  children: ReactNode
}) {
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      onToggle()
    }
  }

  return (
    <section style={panelStyle}>
      <div
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        role="button"
        tabIndex={0}
        style={sectionToggleHeaderStyle}
      >
        <div>
          <div style={{ fontWeight: 800 }}>{title}</div>
          {hint && <div style={panelHintStyle}>{hint}</div>}
        </div>

        <div style={sectionHeaderRightStyle}>
          {right}
          <span style={collapseIconStyle}>{open ? '收合 ▲' : '展開 ▼'}</span>
        </div>
      </div>

      {open && children}
    </section>
  )
}

export function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div style={infoItemStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value}</div>
    </div>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label style={fieldStyle}>
      <span style={fieldLabelStyle}>{label}</span>
      {children}
    </label>
  )
}

export function StatusBadge({ status }: { status: string }) {
  return <span style={statusBadgeStyle}>{wipStatusText[status] ?? status}</span>
}