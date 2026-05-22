'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import UserSwitcher, { authHeaders } from '@/components/UserSwitcher'
import Chip from '@/components/ui/Chip'
import KpiCard from '@/components/ui/KpiCard'

type Recipe = {
  recipeId: string
  name: string
  version: string
  experimentItem: string
  machineIds: string[]
  method: string
  parameters: Record<string, string>
  updatedBy: string
  updatedAt: string
}

type Machine = {
  machineId: string
  name: string
  supportedItems: string[]
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'

const demoRecipeForm = {
  recipeId: 'RCP-AFM-001',
  name: 'AFM 表面形貌標準流程',
  version: 'v1.0',
  experimentItem: '表面形貌分析',
  machineId: 'AFM-004',
  method: '標準掃描模式，先做探針校正，再進行 5 點表面形貌量測。',
  parameters: 'scanSize:10um,resolution:512,duration:30min',
  updatedBy: '',
}

export default function RecipePage() {
  const [recipes, setRecipes] = useState<Recipe[]>([])
  const [machines, setMachines] = useState<Machine[]>([])
  const [form, setForm] = useState({
    recipeId: '',
    name: '',
    version: '',
    experimentItem: '',
    machineId: '',
    method: '',
    parameters: '',
    updatedBy: '',
  })
  const [message, setMessage] = useState('讀取資料庫中')

  const loadData = useCallback(() => {
    Promise.all([
      fetch(`${apiUrl}/api/recipes`).then(res => res.ok ? res.json() : Promise.reject(new Error('recipes failed'))),
      fetch(`${apiUrl}/api/machines`).then(res => res.ok ? res.json() : Promise.reject(new Error('machines failed'))),
    ])
      .then(([recipePayload, machinePayload]: [{ data: Recipe[] }, { data: Machine[] }]) => {
        setRecipes(recipePayload.data)
        setMachines(machinePayload.data)
        setMessage('已連線 PostgreSQL')
      })
      .catch(() => setMessage('後端或 PostgreSQL 尚未啟動'))
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const experimentItems = useMemo(() => Array.from(new Set(machines.flatMap(machine => machine.supportedItems))), [machines])
  const compatibleMachines = machines.filter(machine => machine.supportedItems.includes(form.experimentItem))

  function createRecipe() {
    const machineId = compatibleMachines.some(machine => machine.machineId === form.machineId)
      ? form.machineId
      : compatibleMachines[0]?.machineId ?? form.machineId
    fetch(`${apiUrl}/api/recipes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        recipeId: form.recipeId,
        name: form.name,
        version: form.version,
        experimentItem: form.experimentItem,
        machineIds: [machineId],
        method: form.method,
        parameters: Object.fromEntries(form.parameters.split(',').map(item => item.trim()).filter(Boolean).map(item => {
          const [key, value] = item.split(':')
          return [(key ?? '').trim(), (value ?? '').trim()]
        })),
        updatedBy: form.updatedBy,
      }),
    })
      .then(res => res.ok ? res.json() : Promise.reject(new Error('create failed')))
      .then(() => {
        setForm({ recipeId: '', name: '', version: '', experimentItem: '', machineId: '', method: '', parameters: '', updatedBy: '' })
        loadData()
      })
      .catch(() => setMessage('建立 Recipe 失敗，只有實驗室人員可建立，並請確認機台與 Recipe ID'))
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 22 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Recipe 管理</h1>
          <p style={{ fontSize: 12, color: 'var(--text3)', marginTop: 4, fontFamily: 'monospace' }}>ROLE C · POSTGRESQL · {message}</p>
        </div>
        <UserSwitcher />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 20 }}>
        <KpiCard label="Recipe 數" value={recipes.length} sub="含版本與方法" color="var(--blue)" icon="📐" />
        <KpiCard label="實驗項目" value={experimentItems.length} sub="由機台支援項目彙整" color="var(--cyan)" icon="🧪" />
        <KpiCard label="可用機台" value={machines.length} sub="可被 Recipe 綁定" color="var(--green)" icon="⚙️" />
        <KpiCard label="參數範本" value={recipes.reduce((sum, recipe) => sum + Object.keys(recipe.parameters).length, 0)} sub="Recipe parameters" color="var(--purple)" icon="📝" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 16 }}>
        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <span style={{ fontWeight: 700 }}>新增 Recipe</span>
            <button onClick={() => setForm(demoRecipeForm)} style={smallButtonStyle}>快速填入</button>
          </div>
          <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input placeholder="Recipe ID，例如 RCP-001" value={form.recipeId} onChange={event => setForm({ ...form, recipeId: event.target.value })} style={inputStyle} />
            <input placeholder="Recipe 名稱" value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} style={inputStyle} />
            <input placeholder="版本，例如 v1.0" value={form.version} onChange={event => setForm({ ...form, version: event.target.value })} style={inputStyle} />
            <select value={form.experimentItem} onChange={event => setForm({ ...form, experimentItem: event.target.value, machineId: '' })} style={inputStyle}>
              <option value="">選擇實驗項目</option>
              {experimentItems.map(item => <option key={item}>{item}</option>)}
            </select>
            <select value={form.machineId} onChange={event => setForm({ ...form, machineId: event.target.value })} style={inputStyle}>
              <option value="">選擇相容機台</option>
              {(compatibleMachines.length ? compatibleMachines : machines).map(machine => (
                <option key={machine.machineId} value={machine.machineId}>{machine.machineId} · {machine.name}</option>
              ))}
            </select>
            <textarea placeholder="實驗方法" value={form.method} onChange={event => setForm({ ...form, method: event.target.value })} style={{ ...inputStyle, minHeight: 90 }} />
            <input placeholder="參數 key:value，用逗號分隔" value={form.parameters} onChange={event => setForm({ ...form, parameters: event.target.value })} style={inputStyle} />
            <button onClick={createRecipe} style={buttonStyle}>建立 Recipe</button>
          </div>
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <span style={{ fontWeight: 700 }}>Recipe 版本清單</span>
            <span style={badgeStyle}>{recipes.length} 筆</span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--s2)' }}>
                {['Recipe', '實驗項目', '適用機台', '方法', '參數', '更新'].map(header => (
                  <th key={header} style={thStyle}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {recipes.map(recipe => (
                <tr key={recipe.recipeId} style={{ borderBottom: '1px solid var(--border2)' }}>
                  <td style={tdStyle}>
                    <div style={{ fontFamily: 'monospace', color: 'var(--text)' }}>{recipe.recipeId}</div>
                    <div style={{ color: 'var(--text3)', fontSize: 11 }}>{recipe.name} · {recipe.version}</div>
                  </td>
                  <td style={tdStyle}><Chip type="approved" label={recipe.experimentItem} /></td>
                  <td style={tdStyle}>{recipe.machineIds.join('、')}</td>
                  <td style={tdStyle}>{recipe.method}</td>
                  <td style={tdStyle}>{Object.entries(recipe.parameters).map(([key, value]) => `${key}:${value}`).join(' / ')}</td>
                  <td style={tdStyle}>{recipe.updatedBy}<br /><span style={{ color: 'var(--text3)', fontSize: 11 }}>{recipe.updatedAt}</span></td>
                </tr>
              ))}
              {!recipes.length && (
                <tr><td colSpan={6} style={{ ...tdStyle, textAlign: 'center', padding: 28 }}>尚無 Recipe，請先建立機台，再新增 Recipe。</td></tr>
              )}
            </tbody>
          </table>
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
