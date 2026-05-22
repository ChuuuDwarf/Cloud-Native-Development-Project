import type { ReactNode } from 'react'
import { modalBackdropButtonStyle, modalBackdropStyle, modalCardStyle } from '../styles'

export function Modal({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div style={modalBackdropStyle}>
      <div style={modalCardStyle}>{children}</div>
      <button style={modalBackdropButtonStyle} onClick={onClose} aria-label="close" />
    </div>
  )
}
