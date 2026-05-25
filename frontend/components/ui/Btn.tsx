import type { CSSProperties, ReactNode } from 'react'

type Variant = 'default' | 'primary' | 'danger'

const base: CSSProperties = {
  border: '1px solid var(--border)', borderRadius: 8, fontSize: 12,
  cursor: 'pointer', fontFamily: 'inherit', whiteSpace: 'nowrap',
  padding: '7px 14px', transition: 'all .15s',
}

const variants: Record<Variant, CSSProperties> = {
  default: { background: 'var(--s2)', color: 'var(--text2)' },
  primary: { background: 'var(--blue)', color: '#fff', borderColor: 'var(--blue)', fontWeight: 600 },
  danger: { background: 'var(--s2)', color: 'var(--red)', borderColor: 'var(--red)' },
}

export default function Btn({
  children, onClick, variant = 'default', small, disabled, title,
}: {
  children: ReactNode
  onClick?: () => void
  variant?: Variant
  small?: boolean
  disabled?: boolean
  title?: string
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      style={{
        ...base, ...variants[variant],
        ...(small ? { padding: '4px 10px', fontSize: 11 } : {}),
        ...(disabled ? { opacity: 0.4, cursor: 'not-allowed' } : {}),
      }}
    >
      {children}
    </button>
  )
}
