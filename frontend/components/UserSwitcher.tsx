'use client'

import { useEffect, useState } from 'react'
import { formatLab } from '@/components/labDisplay'

export type AppUser = {
  userId: string
  name: string
  role: string
  department: string
  lab?: string | null
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'
const storageKey = 'lims-current-user-id'

export function getCurrentUserId() {
  if (typeof window === 'undefined') return 'u-lab-a'
  return window.localStorage.getItem(storageKey) ?? 'u-lab-a'
}

export function authHeaders(userId?: string) {
  return { 'X-User-Id': userId ?? getCurrentUserId() }
}

function userScopeLabel(user?: AppUser) {
  if (!user) return '未連線'
  if (user.lab) return formatLab(user.lab)
  return user.role === '實驗室大主管' || user.role === '系統管理者' ? '全 LAB' : user.department
}

export default function UserSwitcher({ onChange }: { onChange?: (user: AppUser) => void }) {
  const [users, setUsers] = useState<AppUser[]>([])
  const [currentUserId, setCurrentUserId] = useState(getCurrentUserId)

  useEffect(() => {
    fetch(`${apiUrl}/api/users`)
      .then(res => res.ok ? res.json() : Promise.reject(new Error('users failed')))
      .then((payload: { data: AppUser[] }) => {
        setUsers(payload.data)
        const selectedUser = payload.data.find(user => user.userId === currentUserId) ?? payload.data[0]
        if (selectedUser) onChange?.(selectedUser)
      })
      .catch(() => undefined)
  }, [currentUserId, onChange])

  function selectUser(userId: string) {
    window.localStorage.setItem(storageKey, userId)
    setCurrentUserId(userId)
    const selectedUser = users.find(user => user.userId === userId)
    if (selectedUser) onChange?.(selectedUser)
  }

  const currentUser = users.find(user => user.userId === currentUserId)

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <select value={currentUserId} onChange={event => selectUser(event.target.value)} style={selectStyle}>
        {users.map(user => (
          <option key={user.userId} value={user.userId}>{userScopeLabel(user)}｜{user.name}｜{user.role}</option>
        ))}
      </select>
      <span style={badgeStyle}>{userScopeLabel(currentUser)}</span>
    </div>
  )
}

const selectStyle = { background: 'var(--s2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '8px 12px', borderRadius: 8, fontSize: 12, minWidth: 230 }
const badgeStyle = { fontSize: 10, fontFamily: 'monospace', color: 'var(--text3)', background: 'var(--s3)', padding: '4px 7px', borderRadius: 4, whiteSpace: 'nowrap' as const }
