'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import UserSwitcher, { authHeaders } from '@/components/UserSwitcher'
import Chip from '@/components/ui/Chip'
import KpiCard from '@/components/ui/KpiCard'

type MachineStatus = '閒置' | '使用中' | '保養中' | '故障中' | '停用'
type WipStatus = '待派工' | '排程中' | '待上機'
type Strategy = 'FIFO' | 'Priority First' | 'Earliest Due Date' | 'Least Setup Change' | 'Hybrid'

type Machine = {
  machineId: string
  name: string
  status: MachineStatus
  supportedItems: string[]
}

type Recipe = {
  recipeId: string
  name: string
  experimentItem: string
  machineIds: string[]
}

type Dispatch = {
  dispatchId: string
  wipId: string
  orderId: string
  experimentItem: string
  priority: string
  dueAt: string
  status: WipStatus
  suggestedMachineId?: string | null
  assignedMachineId?: string | null
  assignedRecipeId?: string | null
  scheduledStart?: string | null
  scheduledEnd?: string | null
  createdBy?: string | null
  assignedBy?: string | null
  strategy?: string | null
  replanReason?: string | null
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'
const strategies: Strategy[] = ['FIFO', 'Priority First', 'Earliest Due Date', 'Least Setup Change', 'Hybrid']
const strategyDescriptions: Record<Strategy, string> = {
  FIFO: '依 Dispatch ID 代表的進件順序排序',
  'Priority First': '特急、高、一般優先序排序',
  'Earliest Due Date': '交期最早的 WIP 優先',
  'Least Setup Change': '相同實驗項目集中，減少換機/換設定',
  Hybrid: '先看優先級，再看交期與實驗項目',
}
const replanPolicies: { reason: string; label: string; strategy: Strategy; hint: string }[] = [
  { reason: '機台故障重排', label: '機台故障', strategy: 'Least Setup Change', hint: '集中相同項目，降低換機與換設定' },
  { reason: '特急單插單重排', label: '特急插單', strategy: 'Priority First', hint: '特急與高優先級先排' },
  { reason: '前站延誤重排', label: '前站延誤', strategy: 'Earliest Due Date', hint: '先救交期最近的項目' },
  { reason: '人員不足重排', label: '人員不足', strategy: 'Hybrid', hint: '兼顧優先級、交期與同類項目' },
]
const statusTypes: Record<WipStatus, 'pending' | 'review' | 'approved'> = {
  待派工: 'pending',
  排程中: 'review',
  待上機: 'approved',
}

const demoDispatchForm = {
  dispatchId: 'DSP-004',
  wipId: 'WIP-004',
  orderId: 'WO-004',
  experimentItem: '表面形貌分析',
  priority: '高',
  dueAt: '2026-05-24T12:00',
}

function toDateTimeLocal(value?: string | null) {
  if (!value) return ''
  return value.replace(' ', 'T').slice(0, 16)
}

function toApiDateTime(value: string) {
  return value.replace('T', ' ')
}

export default function DispatchPage() {
  const [machines, setMachines] = useState<Machine[]>([])
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [dispatches, setDispatches] = useState<Dispatch[]>([])
  const [strategy, setStrategy] = useState<Strategy>('FIFO')
  const [activeDispatchId, setActiveDispatchId] = useState('')
  const [scheduledStart, setScheduledStart] = useState('')
  const [scheduledEnd, setScheduledEnd] = useState('')
  const [message, setMessage] = useState('讀取資料庫中')
  const [form, setForm] = useState({
    dispatchId: '',
    wipId: '',
    orderId: '',
    experimentItem: '',
    priority: '一般',
    dueAt: '',
  })

  const loadData = useCallback(() => {
    Promise.all([
      fetch(`${apiUrl}/api/machines`).then(res => res.ok ? res.json() : Promise.reject(new Error('machines failed'))),
      fetch(`${apiUrl}/api/recipes`).then(res => res.ok ? res.json() : Promise.reject(new Error('recipes failed'))),
      fetch(`${apiUrl}/api/dispatches`).then(res => res.ok ? res.json() : Promise.reject(new Error('dispatches failed'))),
    ])
      .then(([machinePayload, recipePayload, dispatchPayload]: [{ data: Machine[] }, { data: Recipe[] }, { data: Dispatch[] }]) => {
        setMachines(machinePayload.data)
        setRecipes(recipePayload.data)
        setDispatches(dispatchPayload.data)
        setActiveDispatchId(current => current || dispatchPayload.data[0]?.dispatchId || '')
        setMessage('已連線 PostgreSQL')
      })
      .catch(() => setMessage('後端或 PostgreSQL 尚未啟動'))
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const experimentItems = useMemo(
    () => Array.from(new Set(machines.flatMap(machine => machine.supportedItems))),
    [machines],
  )
  const activeDispatch = dispatches.find(dispatch => dispatch.dispatchId === activeDispatchId) ?? dispatches[0]
  useEffect(() => {
    setScheduledStart(toDateTimeLocal(activeDispatch?.scheduledStart))
    setScheduledEnd(toDateTimeLocal(activeDispatch?.scheduledEnd))
  }, [activeDispatch?.dispatchId, activeDispatch?.scheduledStart, activeDispatch?.scheduledEnd])

  const assignableMachines = useMemo(() => {
    if (!activeDispatch) return []
    return machines.filter(machine => machine.supportedItems.includes(activeDispatch.experimentItem) && !['故障中', '保養中', '停用'].includes(machine.status))
  }, [activeDispatch, machines])
  const selectedMachineId = activeDispatch?.suggestedMachineId && assignableMachines.some(machine => machine.machineId === activeDispatch.suggestedMachineId)
    ? activeDispatch.suggestedMachineId
    : assignableMachines[0]?.machineId
  const assignableRecipes = useMemo(() => {
    if (!activeDispatch || !selectedMachineId) return []
    return recipes.filter(recipe => recipe.experimentItem === activeDispatch.experimentItem && recipe.machineIds.includes(selectedMachineId))
  }, [activeDispatch, recipes, selectedMachineId])

  const summary = useMemo(() => ({
    pending: dispatches.filter(dispatch => dispatch.status === '待派工').length,
    scheduling: dispatches.filter(dispatch => dispatch.status === '排程中').length,
    ready: dispatches.filter(dispatch => dispatch.status === '待上機').length,
    blockedMachines: machines.filter(machine => ['故障中', '保養中', '停用'].includes(machine.status)).length,
  }), [dispatches, machines])

  function createDispatch() {
    fetch(`${apiUrl}/api/dispatches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ ...form, dueAt: toApiDateTime(form.dueAt) }),
    })
      .then(res => res.ok ? res.json() : Promise.reject(new Error('create failed')))
      .then(() => {
        setForm({ dispatchId: '', wipId: '', orderId: '', experimentItem: '', priority: '一般', dueAt: '' })
        loadData()
      })
      .catch(() => setMessage('新增待派工 WIP 失敗，只有實驗室人員可新增，並請確認 dispatch ID 不重複'))
  }

  function suggestSchedule() {
    fetch(`${apiUrl}/api/dispatches/suggest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ strategy }),
    })
      .then(res => res.ok ? res.json() : Promise.reject(new Error('suggest failed')))
      .then(() => loadData())
      .catch(() => setMessage('產生建議失敗，廠區使用者不可操作，或機台與 WIP 無法對應'))
  }

  function replan(reason: string, recommendedStrategy: Strategy) {
    setStrategy(recommendedStrategy)
    fetch(`${apiUrl}/api/dispatches/replan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ reason, strategy: recommendedStrategy }),
    })
      .then(res => res.ok ? res.json() : Promise.reject(new Error('replan failed')))
      .then(() => loadData())
      .catch(() => setMessage('重排失敗，請確認使用者權限'))
  }

  function assignDispatch() {
    if (!activeDispatch || !selectedMachineId || !assignableRecipes[0]) return
    fetch(`${apiUrl}/api/dispatches/${activeDispatch.dispatchId}/assign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        machineId: selectedMachineId,
        recipeId: assignableRecipes[0].recipeId,
        scheduledStart: toApiDateTime(scheduledStart),
        scheduledEnd: toApiDateTime(scheduledEnd),
      }),
    })
      .then(res => res.ok ? res.json() : Promise.reject(new Error('assign failed')))
      .then(() => loadData())
      .catch(() => setMessage('確認派工失敗，只有實驗室人員可派工，並請確認機台狀態與 Recipe 相容'))
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 22 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>派工排程</h1>
          <p style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4, fontFamily: 'monospace' }}>ROLE C · POSTGRESQL · {message}</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <UserSwitcher />
          <select value={strategy} onChange={event => setStrategy(event.target.value as Strategy)} style={inputStyle}>
            {strategies.map(item => <option key={item}>{item}</option>)}
          </select>
          <button onClick={suggestSchedule} style={buttonStyle}>產生建議</button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 20 }}>
        <KpiCard label="待派工 WIP" value={summary.pending} sub="由使用者建立" color="var(--yellow)" icon="🗂️" />
        <KpiCard label="排程中" value={summary.scheduling} sub={`策略 ${strategy}`} color="var(--purple)" icon="📌" />
        <KpiCard label="待上機" value={summary.ready} sub="已完成派工" color="var(--green)" icon="✅" />
        <KpiCard label="不可用機台" value={summary.blockedMachines} sub="派工時自動排除" color="var(--red)" icon="⚠️" />
      </div>

      <div style={{ ...panelStyle, padding: 12, marginBottom: 16, display: 'flex', gap: 10, alignItems: 'center' }}>
        <span style={{ color: 'var(--text2)', fontSize: 12, flex: 1 }}>{strategyDescriptions[strategy]}</span>
        {replanPolicies.map(policy => (
          <button key={policy.reason} title={`${policy.strategy}：${policy.hint}`} onClick={() => replan(policy.reason, policy.strategy)} style={smallButtonStyle}>
            {policy.label}
            <span style={{ display: 'block', color: 'var(--text3)', fontSize: 9 }}>{policy.strategy}</span>
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr 340px', gap: 16 }}>
        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <span style={{ fontWeight: 700 }}>新增待派工 WIP</span>
            <button onClick={() => setForm(demoDispatchForm)} style={smallButtonStyle}>快速填入</button>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input placeholder="Dispatch ID，例如 DSP-001" value={form.dispatchId} onChange={event => setForm({ ...form, dispatchId: event.target.value })} style={inputStyle} />
            <input placeholder="WIP ID，例如 WIP-001" value={form.wipId} onChange={event => setForm({ ...form, wipId: event.target.value })} style={inputStyle} />
            <input placeholder="委託單 ID，例如 WO-001" value={form.orderId} onChange={event => setForm({ ...form, orderId: event.target.value })} style={inputStyle} />
            <select value={form.experimentItem} onChange={event => setForm({ ...form, experimentItem: event.target.value })} style={inputStyle}>
              <option value="">選擇實驗項目</option>
              {experimentItems.map(item => <option key={item}>{item}</option>)}
            </select>
            <select value={form.priority} onChange={event => setForm({ ...form, priority: event.target.value })} style={inputStyle}>
              {['一般', '高', '特急'].map(item => <option key={item}>{item}</option>)}
            </select>
            <input type="datetime-local" value={form.dueAt} onChange={event => setForm({ ...form, dueAt: event.target.value })} style={inputStyle} />
            <button onClick={createDispatch} style={buttonStyle}>新增 WIP</button>
          </div>
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <span style={{ fontWeight: 700 }}>待派工 / 待排程清單</span>
            <span style={badgeStyle}>{dispatches.length} 筆</span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--s2)' }}>
                {['WIP', '實驗項目', '優先', '交期', '狀態', '建議 / 指派', '系統預估', '重排 / 策略'].map(header => (
                  <th key={header} style={thStyle}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dispatches.map(dispatch => (
                <tr key={dispatch.dispatchId} onClick={() => setActiveDispatchId(dispatch.dispatchId)} style={{ borderBottom: '1px solid var(--border2)', background: activeDispatchId === dispatch.dispatchId ? 'rgba(56,139,253,0.08)' : 'transparent', cursor: 'pointer' }}>
                  <td style={tdStyle}>{dispatch.wipId}<br /><span style={{ color: 'var(--text3)' }}>{dispatch.orderId}</span></td>
                  <td style={tdStyle}>{dispatch.experimentItem}</td>
                  <td style={tdStyle}>{dispatch.priority}</td>
                  <td style={tdStyle}>{dispatch.dueAt}</td>
                  <td style={tdStyle}><Chip type={statusTypes[dispatch.status]} label={dispatch.status} /></td>
                  <td style={tdStyle}>{dispatch.assignedMachineId ?? dispatch.suggestedMachineId ?? '尚未產生'}</td>
                  <td style={tdStyle}>{dispatch.scheduledStart ?? '-'}<br /><span style={{ color: 'var(--text3)' }}>{dispatch.scheduledEnd ?? ''}</span></td>
                  <td style={tdStyle}>
                    {dispatch.replanReason ?? '-'}
                    <br />
                    <span style={{ color: 'var(--text3)' }}>{dispatch.strategy ?? ''}</span>
                  </td>
                </tr>
              ))}
              {!dispatches.length && (
                <tr><td colSpan={8} style={{ ...tdStyle, textAlign: 'center', padding: 28 }}>尚無 WIP，請從左側新增。</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <span style={{ fontWeight: 700 }}>手動確認派工</span>
            <span style={badgeStyle}>{activeDispatch?.wipId ?? 'N/A'}</span>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={fieldLabelStyle}>實驗項目</div>
            <div style={summaryBoxStyle}>{activeDispatch?.experimentItem ?? '未選擇 WIP'}</div>
            <div style={fieldLabelStyle}>可派工機台</div>
            <div style={summaryBoxStyle}>{assignableMachines.map(machine => `${machine.machineId} ${machine.name}`).join('、') || '無可用機台'}</div>
            <div style={fieldLabelStyle}>相容 Recipe</div>
            <div style={summaryBoxStyle}>{assignableRecipes.map(recipe => `${recipe.recipeId} ${recipe.name}`).join('、') || '無相容 Recipe'}</div>
            <div style={fieldLabelStyle}>最終派工時間</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <input type="datetime-local" value={scheduledStart} onChange={event => setScheduledStart(event.target.value)} style={inputStyle} />
              <input type="datetime-local" value={scheduledEnd} onChange={event => setScheduledEnd(event.target.value)} style={inputStyle} />
            </div>
            <button
              disabled={!activeDispatch?.scheduledStart || !activeDispatch?.scheduledEnd}
              onClick={() => {
                setScheduledStart(toDateTimeLocal(activeDispatch?.scheduledStart))
                setScheduledEnd(toDateTimeLocal(activeDispatch?.scheduledEnd))
              }}
              style={{ ...smallButtonStyle, opacity: activeDispatch?.scheduledStart && activeDispatch?.scheduledEnd ? 1 : 0.45 }}
            >
              套用系統預估時間
            </button>
            <button disabled={!selectedMachineId || !assignableRecipes[0]} onClick={assignDispatch} style={{ ...buttonStyle, opacity: selectedMachineId && assignableRecipes[0] ? 1 : 0.45, cursor: selectedMachineId && assignableRecipes[0] ? 'pointer' : 'not-allowed' }}>
              確認派工
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

const panelStyle = { background: 'var(--s1)', border: '1px solid var(--border2)', borderRadius: 12, overflow: 'hidden' }
const panelHeaderStyle = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px', borderBottom: '1px solid var(--border2)' }
const badgeStyle = { fontSize: 10, fontFamily: 'monospace', color: 'var(--text3)', background: 'var(--s3)', padding: '2px 7px', borderRadius: 4 }
const thStyle = { fontSize: 10, letterSpacing: 1.5, color: 'var(--text3)', padding: '10px 16px', textAlign: 'left' as const, fontFamily: 'monospace', borderBottom: '1px solid var(--border2)' }
const tdStyle = { padding: '12px 16px', fontSize: 12.5, color: 'var(--text2)', verticalAlign: 'middle' as const }
const inputStyle = { background: 'var(--s2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '9px 10px', borderRadius: 8, fontSize: 12, width: '100%' }
const buttonStyle = { background: 'var(--blue)', border: '1px solid var(--border)', color: '#fff', padding: '9px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }
const smallButtonStyle = { background: 'var(--s2)', border: '1px solid var(--border)', color: 'var(--text2)', padding: '4px 8px', borderRadius: 6, fontSize: 10, cursor: 'pointer' }
const fieldLabelStyle = { fontSize: 10, letterSpacing: 1.5, color: 'var(--text3)', fontFamily: 'monospace' }
const summaryBoxStyle = { background: 'var(--s2)', border: '1px solid var(--border2)', color: 'var(--text2)', padding: 10, borderRadius: 8, fontSize: 12, minHeight: 38 }
