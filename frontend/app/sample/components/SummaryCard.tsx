import { summaryCardStyle, summaryLabelStyle, summaryValueStyle } from '../styles'

export function SummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div style={summaryCardStyle}>
      <div style={summaryValueStyle}>{value}</div>
      <div style={summaryLabelStyle}>{label}</div>
    </div>
  )
}
