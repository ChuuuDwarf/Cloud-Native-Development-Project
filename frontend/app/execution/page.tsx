'use client'
import { useMemo, useState } from 'react'
import Chip from '@/components/ui/Chip'
import KpiCard from '@/components/ui/KpiCard'
import Panel from '@/components/ui/Panel'
import Btn from '@/components/ui/Btn'
import DataState, { OfflineBanner } from '@/components/ui/DataState'
import RoleSwitcher from '@/components/ui/RoleSwitcher'
import { useQueryClient } from '@tanstack/react-query'
import { useResourceQuery } from '@/hooks/useResourceQuery'
import { errorMessage } from '@/lib/errorMessage'
import { experimentsApi } from '@/services/experiments-api'
import { MOCK_WIPS } from '@/mocks/lab'
import { chipOf, type Role, type Wip } from '@/types/lab'
import { th, td, tdMono, linkBtn } from '@/constants/styles'
import { CheckinModal, ResultModal, AbortModal, ReviewModal, DetailModal, type RunFn } from './modals'

type ModalKind = 'checkin' | 'result' | 'abort' | 'review' | 'detail' | null

const EXPERIMENTS_KEY = ['experiments'] as const

export default function ExecutionPage() {
  const queryClient = useQueryClient()
  const { data: wips, loading, offline, reload } = useResourceQuery<Wip[]>(EXPERIMENTS_KEY, experimentsApi.list, MOCK_WIPS)
  const [role, setRole] = useState<Role>('實驗室人員')
  const [modal, setModal] = useState<ModalKind>(null)
  const [target, setTarget] = useState<Wip | null>(null)
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null)

  const isStaff = role === '實驗室人員'
  const isChief = role === '實驗室主管'

  const kpi = useMemo(() => {
    const c = (s: string) => wips.filter((w) => w.status === s).length
    return { checkin: c('待上機'), running: c('執行中'), out: c('已下機'), confirm: c('待確認'), done: c('已完成') }
  }, [wips])

  const run: RunFn = async (fn, okText) => {
    try {
      await fn()
      setMsg({ text: okText, ok: true })
      setModal(null)
      await queryClient.invalidateQueries({ queryKey: EXPERIMENTS_KEY })
      reload()
    } catch (e) {
      setMsg({ text: errorMessage(e), ok: false })
    }
  }

  const open = (kind: ModalKind, w: Wip) => { setTarget(w); setModal(kind); setMsg(null) }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>實驗執行</h1>
          <p style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4, fontFamily: 'monospace' }}>EXPERIMENT EXECUTION · 上下機 / 進度 / 結果 / 中止</p>
        </div>
        <RoleSwitcher role={role} onChange={setRole} />
      </div>

      {offline && <OfflineBanner />}
      {msg && (
        <div style={{ marginBottom: 16, padding: '8px 14px', borderRadius: 8, fontSize: 12.5,
          background: msg.ok ? 'rgba(63,185,80,0.1)' : 'rgba(255,68,68,0.1)',
          border: `1px solid ${msg.ok ? 'rgba(63,185,80,0.3)' : 'rgba(255,68,68,0.3)'}`,
          color: msg.ok ? 'var(--green)' : 'var(--red)' }}>
          {msg.ok ? '✅ ' : '⚠️ '}{msg.text}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 14, marginBottom: 22 }}>
        <KpiCard label="待上機" value={kpi.checkin} color="var(--yellow)" icon="⏱️" />
        <KpiCard label="執行中" value={kpi.running} color="var(--cyan)" icon="🔬" />
        <KpiCard label="已下機" value={kpi.out} color="var(--orange)" icon="📤" />
        <KpiCard label="待確認" value={kpi.confirm} color="var(--purple)" icon="🔍" />
        <KpiCard label="已完成" value={kpi.done} color="var(--green)" icon="✅" />
      </div>

      <Panel title="實驗執行清單" tag={`${wips.length} 筆`}>
        <DataState loading={loading} empty={wips.length === 0}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--s2)' }}>
                  {['WIP 編號', '委託單', '樣品 / 項目', '機台', '操作人', '狀態', '進度', '操作'].map((h) => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {wips.map((w) => (
                  <tr key={w.wipId} style={{ borderBottom: '1px solid rgba(56,139,253,0.05)' }}>
                    <td style={tdMono}>
                      <button onClick={() => open('detail', w)} style={linkBtn}>{w.wipId}</button>
                    </td>
                    <td style={tdMono}>{w.orderId}</td>
                    <td style={td}>{w.sample}<div style={{ fontSize: 10, color: 'var(--text3)' }}>{w.experimentItem}</div></td>
                    <td style={td}>{w.machineId ?? '—'}</td>
                    <td style={td}>{w.operator ?? '—'}</td>
                    <td style={td}>
                      <Chip type={chipOf(w.status)} label={w.status} />
                      {w.abort?.status === '待主管判定' && <div style={{ fontSize: 10, color: 'var(--orange)', marginTop: 3 }}>⚠️ 中止待判定</div>}
                    </td>
                    <td style={td}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div style={{ background: 'var(--s3)', borderRadius: 3, height: 5, width: 70 }}>
                          <div style={{ width: `${w.progress}%`, height: '100%', borderRadius: 3, background: w.status === '已完成' ? 'var(--green)' : 'linear-gradient(90deg,var(--blue),var(--cyan))' }} />
                        </div>
                        <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--text3)' }}>{w.progress}%</span>
                      </div>
                    </td>
                    <td style={td}><div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>{actions(w)}</div></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DataState>
      </Panel>

      {renderModal()}
    </div>
  )

  function actions(w: Wip) {
    const disabled = offline
    const abortPending = w.abort?.status === '待主管判定'
    if (abortPending) {
      return isChief
        ? <Btn small variant="danger" disabled={disabled} onClick={() => open('review', w)}>審核中止</Btn>
        : <span style={{ fontSize: 10, color: 'var(--text3)' }}>待主管判定</span>
    }
    if (!isStaff) return <span style={{ fontSize: 10, color: 'var(--text3)' }}>僅實驗室人員可操作</span>
    switch (w.status) {
      case '待上機':
        return <Btn small variant="primary" disabled={disabled} onClick={() => open('checkin', w)}>上機</Btn>
      case '執行中':
        return <>
          <Btn small disabled={disabled} onClick={() => promptProgress(w)}>更新進度</Btn>
          <Btn small disabled={disabled} onClick={() => run(() => experimentsApi.checkOut(w.wipId, { operator: w.operator ?? '實驗室人員' }), '下機登記完成')}>下機</Btn>
          <Btn small variant="primary" disabled={disabled} onClick={() => open('result', w)}>上傳結果</Btn>
          <Btn small variant="danger" disabled={disabled} onClick={() => open('abort', w)}>中止申請</Btn>
        </>
      case '已下機':
        return <>
          <Btn small variant="primary" disabled={disabled} onClick={() => open('result', w)}>上傳結果</Btn>
          <Btn small variant="danger" disabled={disabled} onClick={() => open('abort', w)}>中止申請</Btn>
        </>
      case '待確認':
        return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          {!w.dataVerified && <span style={{ fontSize: 10, color: 'var(--orange)' }}>⚠️ 數據尚未驗證</span>}
          <Btn small variant="primary" disabled={disabled || !w.dataVerified} onClick={() => run(() => experimentsApi.confirm(w.wipId, { operator: '實驗室人員' }), '結果已確認')}>確認結果</Btn>
        </span>
      default:
        return <span style={{ fontSize: 10, color: 'var(--text3)' }}>—</span>
    }
  }

  function promptProgress(w: Wip) {
    const v = window.prompt(`更新 ${w.wipId} 進度（0-100）`, String(w.progress))
    if (v === null) return
    const n = Number(v)
    if (Number.isNaN(n) || n < 0 || n > 100) { setMsg({ text: '進度需為 0-100 的數字', ok: false }); return }
    run(() => experimentsApi.updateProgress(w.wipId, n), '進度已更新')
  }

  function renderModal() {
    if (!target) return null
    if (modal === 'checkin') return <CheckinModal w={target} run={run} onClose={() => setModal(null)} />
    if (modal === 'result') return <ResultModal w={target} run={run} onClose={() => setModal(null)} />
    if (modal === 'abort') return <AbortModal w={target} run={run} onClose={() => setModal(null)} />
    if (modal === 'review') return <ReviewModal w={target} run={run} onClose={() => setModal(null)} />
    if (modal === 'detail') return <DetailModal w={target} onClose={() => setModal(null)} />
    return null
  }
}
