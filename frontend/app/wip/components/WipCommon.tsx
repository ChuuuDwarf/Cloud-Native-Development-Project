import type { KeyboardEvent, ReactNode } from 'react'
import { sampleStatusText, wipStatusText } from '../constants'
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
        role="button"
        tabIndex={0}
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        style={sectionToggleHeaderStyle}
      >
        <div>
          <div style={{ fontWeight: 800 }}>{title}</div>
          {hint && <div style={panelHintStyle}>{hint}</div>}
        </div>

        <div style={sectionHeaderRightStyle}>
          {right}
          <span style={collapseIconStyle}>{open ? '⌃' : '⌄'}</span>
        </div>
      </div>

      {open && <div>{children}</div>}
    </section>
  )
}

export function InfoItem({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div style={infoItemStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value ?? '-'}</div>
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
  const text = sampleStatusText[status] ?? wipStatusText[status] ?? status

  return <span style={statusBadgeStyle}>{text}</span>
}