import { sampleStatusText } from '../constants'
import { statusBadgeStyle } from '../styles'

export function StatusBadge({ status }: { status: string }) {
  return <span style={statusBadgeStyle}>{sampleStatusText[status] ?? status}</span>
}
