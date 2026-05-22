'use client'

import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { useSearchParams } from 'next/navigation'
import { apiGet, apiPost } from '@/lib/api'

type CurrentUser = {
  id: string
  name: string
  role: string
  role_name?: string
  department: string
  lab_name?: string | null
  email?: string
}

type RequestedExperiment = {
  lab_name: string
  experiment_item: string
}

type SampleNote = {
  source?: string
  sample_quantity?: string
  priority?: string
  requested_experiments?: RequestedExperiment[]
}

type Sample = {
  id: string
  sample_no: string
  order_no: string
  sample_name: string | null
  experiment_item: string | null
  applicant_name: string | null
  applicant_department: string | null
  status: string
  current_location: string | null
  storage_location_id: string | null
  received_at: string | null
  received_by: string | null
  picked_up_at: string | null
  picked_up_by: string | null
  note: string | null
  created_at: string
  updated_at: string
}

type Wip = {
  id: string
  wip_no: string
  sample_id: string
  order_no: string
  lab_name: string | null
  experiment_item: string | null
  priority: string
  status: string
  progress: number
  current_location: string | null
  scheduled_at: string | null
  dispatched_at: string | null
  started_at: string | null
  completed_at: string | null
  terminated_at: string | null
  note: string | null
  created_at: string
  updated_at: string
}

type WipForm = {
  lab_name: string
  experiment_item: string
  priority: string
  note: string
  auto_generated: boolean
}

const fallbackUser: CurrentUser = {
  id: 'USER001',
  name: '實驗室人員A',
  role: 'lab_staff',
  role_name: '實驗室人員',
  department: 'Lab A',
  lab_name: 'Lab A',
  email: '',
}

const activeSampleStatuses = new Set(['received', 'split'])

const sampleStatusText: Record<string, string> = {
  pending_receive: '待收樣',
  received: '已收樣',
  split: '已分貨',
  transferring: '交接中',
  in_storage: '已入庫',
  outbound: '待取件',
  picked_up: '已取件',
  lost: '遺失',
  damaged: '破損',
  cancelled: '已取消',
}

const wipStatusText: Record<string, string> = {
  created: '已建立',
  waiting_schedule: '待排程',
  scheduled: '已排程',
  dispatched: '已派工',
  running: '實驗中',
  paused: '暫停',
  completed: '已完成',
  terminated: '已終止',
  cancelled: '已取消',
}

const priorityText: Record<string, string> = {
  low: '低',
  normal: '一般',
  high: '高',
  urgent: '急件',
}

const experimentOptions = [
  'SEM 觀察',
  '電性量測',
  '材料分析',
  '光學量測',
  '可靠度測試',
  '外觀檢查',
  '化學分析',
  '成分分析',
  '污染分析',
  '尺寸量測',
  '失效分析',
  '熱循環測試',
]

const operatorName = 'WIP管理／實驗室人員A'

function createEmptyWipForm(labName = ''): WipForm {
  return {
    lab_name: labName,
    experiment_item: '',
    priority: 'normal',
    note: '',
    auto_generated: false,
  }
}

function getCurrentLab(user: CurrentUser | null) {
  return user?.lab_name || user?.department || fallbackUser.lab_name || fallbackUser.department
}

function safeParseSampleNote(note: string | null): SampleNote | null {
  if (!note) return null

  try {
    const parsed = JSON.parse(note)

    if (!parsed || typeof parsed !== 'object') return null

    return parsed as SampleNote
  } catch {
    return null
  }
}

function parseExperimentsFromSummary(summary: string | null): RequestedExperiment[] {
  if (!summary) return []

  return summary
    .split('、')
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [labName, ...rest] = part.split(':')
      const experimentItem = rest.join(':').trim()

      if (!labName || !experimentItem) return null

      return {
        lab_name: labName.trim(),
        experiment_item: experimentItem,
      }
    })
    .filter((item): item is RequestedExperiment => Boolean(item))
}

function getRequestedExperiments(sample: Sample | null): RequestedExperiment[] {
  if (!sample) return []

  const note = safeParseSampleNote(sample.note)

  if (note?.requested_experiments && Array.isArray(note.requested_experiments)) {
    return note.requested_experiments.filter((item) => item.lab_name && item.experiment_item)
  }

  return parseExperimentsFromSummary(sample.experiment_item)
}

function getSampleDefaultPriority(sample: Sample | null) {
  const note = safeParseSampleNote(sample?.note ?? null)
  return note?.priority || 'normal'
}

function makeAutoFormsForSample(
  sample: Sample | null,
  currentLab: string,
  existingWips: Wip[],
) {
  if (!sample) return [createEmptyWipForm(currentLab)]

  const requestedExperiments = getRequestedExperiments(sample)
  const defaultPriority = getSampleDefaultPriority(sample)

  const currentLabExperiments = requestedExperiments.filter((item) => item.lab_name === currentLab)

  const existingItems = new Set(
    existingWips
      .filter((wip) => wip.sample_id === sample.id && wip.lab_name === currentLab)
      .map((wip) => wip.experiment_item)
      .filter(Boolean),
  )

  const notYetCreated = currentLabExperiments.filter(
    (item) => !existingItems.has(item.experiment_item),
  )

  if (notYetCreated.length === 0) {
    return [createEmptyWipForm(currentLab)]
  }

  return notYetCreated.map((item) => ({
    lab_name: item.lab_name,
    experiment_item: item.experiment_item,
    priority: defaultPriority,
    note: '由委託單實驗需求自動帶入',
    auto_generated: true,
  }))
}

function formatRequestedExperiments(sample: Sample | null) {
  const requestedExperiments = getRequestedExperiments(sample)

  if (requestedExperiments.length === 0) {
    return sample?.experiment_item ?? '-'
  }

  return requestedExperiments
    .map((item) => `${item.lab_name}:${item.experiment_item}`)
    .join('、')
}

function shouldOpenCreateWipByDefault(sample: Sample | null) {
  if (!sample) return true

  // 已分貨代表通常已經建立過 WIP，所以「建立 WIP」block 預設收合
  if (sample.status === 'split') return false

  return true
}

export default function WipPage() {
  const searchParams = useSearchParams()
  const sampleIdFromUrl = searchParams.get('sampleId')

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)
  const [samples, setSamples] = useState<Sample[]>([])
  const [wips, setWips] = useState<Wip[]>([])
  const [selectedSampleId, setSelectedSampleId] = useState<string>(sampleIdFromUrl ?? '')
  const [forms, setForms] = useState<WipForm[]>([
    createEmptyWipForm(fallbackUser.lab_name ?? fallbackUser.department),
  ])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [openSections, setOpenSections] = useState({
    sampleInfo: true,
    createWip: true,
    currentWips: true,
  })

  const currentLab = getCurrentLab(currentUser)
  const currentOperatorName = currentUser?.name ?? operatorName

  const activeSamples = useMemo(() => {
    return samples.filter((sample) => activeSampleStatuses.has(sample.status))
  }, [samples])

  const selectedSample = useMemo(() => {
    return activeSamples.find((sample) => sample.id === selectedSampleId) ?? null
  }, [activeSamples, selectedSampleId])

  const requestedExperiments = useMemo(() => {
    return getRequestedExperiments(selectedSample)
  }, [selectedSample])

  const currentLabRequestedExperiments = useMemo(() => {
    return requestedExperiments.filter((item) => item.lab_name === currentLab)
  }, [requestedExperiments, currentLab])

  const selectedWips = useMemo(() => {
    if (!selectedSampleId) return []

    return wips.filter((wip) => {
      return wip.sample_id === selectedSampleId && wip.lab_name === currentLab
    })
  }, [wips, selectedSampleId, currentLab])

  const wipsByLab = useMemo(() => {
    return selectedWips.reduce<Record<string, Wip[]>>((groups, wip) => {
      const labName = wip.lab_name ?? '未指定實驗室'

      if (!groups[labName]) {
        groups[labName] = []
      }

      groups[labName].push(wip)
      return groups
    }, {})
  }, [selectedWips])

  const canCreateWip = selectedSample?.status === 'received' || selectedSample?.status === 'split'

  const hasAutoGeneratedForms = forms.some((form) => form.auto_generated)

  function toggleSection(section: keyof typeof openSections) {
    setOpenSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  async function loadCurrentUser() {
    try {
      const meData = await apiGet<CurrentUser>('/api/me')
      return meData
    } catch {
      return fallbackUser
    }
  }

  function resetFormsForSample(sample: Sample | null, lab: string, wipData: Wip[]) {
    setForms(makeAutoFormsForSample(sample, lab, wipData))

    setOpenSections((prev) => ({
      ...prev,
      sampleInfo: true,
      createWip: shouldOpenCreateWipByDefault(sample),
      currentWips: true,
    }))
  }

  async function loadData() {
    try {
      setLoading(true)
      setError('')
      setSuccessMessage('')

      const [meData, sampleData, wipData] = await Promise.all([
        loadCurrentUser(),
        apiGet<Sample[]>('/api/samples'),
        apiGet<Wip[]>('/api/wips'),
      ])

      const lab = getCurrentLab(meData)

      setCurrentUser(meData)
      setSamples(sampleData)
      setWips(wipData)

      const activeSampleData = sampleData.filter((sample) =>
        activeSampleStatuses.has(sample.status),
      )

      if (sampleIdFromUrl) {
        const target = sampleData.find((sample) => sample.id === sampleIdFromUrl)

        if (target && activeSampleStatuses.has(target.status)) {
          setSelectedSampleId(target.id)
          resetFormsForSample(target, lab, wipData)
          return
        }

        setSelectedSampleId('')
        setForms([createEmptyWipForm(lab)])
        setOpenSections({
          sampleInfo: true,
          createWip: true,
          currentWips: true,
        })
        setError('這筆樣品目前不可分貨，只有「已收樣」或「已分貨」的樣品能在此頁操作')
        return
      }

      const currentSelected = activeSampleData.find((sample) => sample.id === selectedSampleId)

      if (currentSelected) {
        resetFormsForSample(currentSelected, lab, wipData)
        return
      }

      const firstTargetSample =
        activeSampleData.find((sample) => sample.status === 'received') ?? activeSampleData[0]

      if (firstTargetSample) {
        setSelectedSampleId(firstTargetSample.id)
        resetFormsForSample(firstTargetSample, lab, wipData)
      } else {
        setSelectedSampleId('')
        setForms([createEmptyWipForm(lab)])
        setOpenSections({
          sampleInfo: true,
          createWip: true,
          currentWips: true,
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '載入資料失敗')
    } finally {
      setLoading(false)
    }
  }

  function handleSelectSample(sampleId: string) {
    const targetSample = activeSamples.find((sample) => sample.id === sampleId) ?? null

    setSelectedSampleId(sampleId)
    resetFormsForSample(targetSample, currentLab, wips)
    setError('')
    setSuccessMessage('')
  }

  function updateForm(index: number, field: keyof WipForm, value: string | boolean) {
    setForms((prev) => {
      return prev.map((form, formIndex) => {
        if (formIndex !== index) return form

        return {
          ...form,
          [field]: value,
          auto_generated: field === 'experiment_item' ? false : form.auto_generated,
        }
      })
    })
  }

  function addForm() {
    setForms((prev) => [...prev, createEmptyWipForm(currentLab)])

    setOpenSections((prev) => ({
      ...prev,
      createWip: true,
    }))
  }

  function regenerateFormsFromOrder() {
    if (!selectedSample) return

    setForms(makeAutoFormsForSample(selectedSample, currentLab, wips))
    setOpenSections((prev) => ({
      ...prev,
      createWip: true,
    }))
    setSuccessMessage('已重新依照委託單實驗需求產生 WIP 項目')
  }

  function duplicateForm(index: number) {
    setForms((prev) => {
      const target = prev[index]
      if (!target) return prev

      return [
        ...prev.slice(0, index + 1),
        {
          ...target,
          experiment_item: '',
          note: '',
          auto_generated: false,
        },
        ...prev.slice(index + 1),
      ]
    })

    setOpenSections((prev) => ({
      ...prev,
      createWip: true,
    }))
  }

  function removeForm(index: number) {
    setForms((prev) => {
      if (prev.length === 1) return prev
      return prev.filter((_, formIndex) => formIndex !== index)
    })
  }

  function validateForms() {
    if (!selectedSample) {
      return '請先選擇樣品'
    }

    if (!canCreateWip) {
      return '目前樣品狀態不可分貨，需為「已收樣」或「已分貨」'
    }

    for (let index = 0; index < forms.length; index += 1) {
      const form = forms[index]

      if (!form.experiment_item.trim()) {
        return `第 ${index + 1} 筆 WIP 尚未填寫實驗項目`
      }

      if (!form.priority.trim()) {
        return `第 ${index + 1} 筆 WIP 尚未選擇優先級`
      }

      if (!form.lab_name.trim()) {
        return `第 ${index + 1} 筆 WIP 尚未指定實驗室`
      }
    }

    const duplicated = new Set<string>()

    for (const form of forms) {
      const key = `${form.lab_name}::${form.experiment_item}`

      if (duplicated.has(key)) {
        return `WIP 項目重複：${form.lab_name} / ${form.experiment_item}`
      }

      duplicated.add(key)
    }

    return ''
  }

  function buildWipNo(index: number) {
    const sampleNo = selectedSample?.sample_no ?? 'SAMPLE'
    const cleanSampleNo = sampleNo.replace('SMP', 'WIP')
    const suffix = String(index + 1).padStart(2, '0')

    return `${cleanSampleNo}-${suffix}`
  }

  async function submitSplit() {
    try {
      setSubmitting(true)
      setError('')
      setSuccessMessage('')

      const validationMessage = validateForms()

      if (validationMessage) {
        setError(validationMessage)
        return
      }

      if (!selectedSample) {
        setError('找不到指定樣品')
        return
      }

      await apiPost(`/api/samples/${selectedSample.id}/actions`, {
        action: 'split',
        operator_name: currentOperatorName,
        wips: forms.map((form, index) => ({
          wip_no: buildWipNo(index),
          lab_name: form.lab_name || currentLab,
          experiment_item: form.experiment_item,
          priority: form.priority,
          // 不送 current_location。
          // 後端會用 sample.current_location，避免 Lab B 的 WIP 在交接前被 Lab B 看到。
          note: form.note,
        })),
      })

      setSuccessMessage('WIP / 實驗子單建立成功')
      setOpenSections({
        sampleInfo: true,
        createWip: false,
        currentWips: true,
      })

      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : '建立 WIP 失敗')
    } finally {
      setSubmitting(false)
    }
  }

  function goBackToSamplePage() {
    window.location.href = '/sample'
  }

  function goToSchedulePage() {
    window.location.href = '/schedule'
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>WIP / 分貨管理</h1>
          <p style={subtitleStyle}>
            WIP MANAGEMENT · 依委託單實驗需求自動產生 WIP 項目
          </p>
        </div>

        <div style={headerActionsStyle}>
          <button onClick={goBackToSamplePage} style={secondaryButtonStyle}>
            回樣品追蹤
          </button>
          <button onClick={loadData} style={secondaryButtonStyle}>
            重新整理
          </button>
        </div>
      </div>

      {error && <div style={errorStyle}>{error}</div>}
      {successMessage && <div style={successStyle}>{successMessage}</div>}

      {loading ? (
        <section style={panelStyle}>
          <div style={emptyStyle}>載入中...</div>
        </section>
      ) : (
        <div style={layoutStyle}>
          <section style={leftPanelStyle}>
            <div style={panelHeaderStyle}>
              <div>
                <div style={{ fontWeight: 800 }}>可分貨樣品</div>
                <div style={panelHintStyle}>只顯示已收樣或已分貨、可建立 WIP 的樣品</div>
              </div>

              <span style={countBadgeStyle}>{activeSamples.length} 筆</span>
            </div>

            <div style={sampleListStyle}>
              {activeSamples.map((sample) => {
                const active = sample.id === selectedSampleId
                const sampleRequestedExperiments = getRequestedExperiments(sample)
                const currentLabCount = sampleRequestedExperiments.filter(
                  (item) => item.lab_name === currentLab,
                ).length

                return (
                  <button
                    key={sample.id}
                    onClick={() => handleSelectSample(sample.id)}
                    style={{
                      ...sampleCardStyle,
                      borderColor: active ? 'rgba(56,139,253,0.75)' : 'var(--border2)',
                      background: active ? 'rgba(56,139,253,0.1)' : 'var(--s1)',
                    }}
                  >
                    <div style={sampleCardTopStyle}>
                      <span style={monoTextStyle}>{sample.sample_no}</span>
                      <StatusBadge status={sample.status} />
                    </div>

                    <div style={sampleNameStyle}>{sample.sample_name ?? '未命名樣品'}</div>

                    <div style={sampleMetaStyle}>
                      {sample.order_no} ·{' '}
                      {currentLabCount > 0
                        ? `${currentLabCount} 個本 Lab 實驗需求`
                        : '本 Lab 無未建立需求'}
                    </div>

                    <div style={sampleMetaStyle}>位置：{sample.current_location ?? '-'}</div>
                  </button>
                )
              })}

              {activeSamples.length === 0 && (
                <div style={emptyStyle}>目前沒有可分貨的樣品</div>
              )}
            </div>
          </section>

          <main style={mainPanelStyle}>
            {!selectedSample ? (
              <section style={panelStyle}>
                <div style={emptyStyle}>請先選擇一筆可分貨樣品</div>
              </section>
            ) : (
              <>
                <CollapsibleSection
                  title="樣品資訊"
                  hint="目前選擇的樣品與委託單資料"
                  open={openSections.sampleInfo}
                  onToggle={() => toggleSection('sampleInfo')}
                  right={<StatusBadge status={selectedSample.status} />}
                >
                  <div style={detailGridStyle}>
                    <InfoItem label="樣品編號" value={selectedSample.sample_no} />
                    <InfoItem label="委託單號" value={selectedSample.order_no} />
                    <InfoItem label="樣品名稱" value={selectedSample.sample_name ?? '-'} />
                    <InfoItem label="全部實驗需求" value={formatRequestedExperiments(selectedSample)} />
                    <InfoItem label="本 Lab" value={currentLab} />
                    <InfoItem
                      label="本 Lab 實驗需求"
                      value={
                        currentLabRequestedExperiments.length > 0
                          ? currentLabRequestedExperiments
                              .map((item) => item.experiment_item)
                              .join('、')
                          : '無'
                      }
                    />
                    <InfoItem label="申請人" value={selectedSample.applicant_name ?? '-'} />
                    <InfoItem label="申請部門" value={selectedSample.applicant_department ?? '-'} />
                    <InfoItem label="目前位置" value={selectedSample.current_location ?? '-'} />
                    <InfoItem label="備註" value={selectedSample.note ?? '-'} />
                  </div>
                </CollapsibleSection>

                <CollapsibleSection
                  title="建立 WIP / 實驗子單"
                  hint={
                    selectedSample.status === 'split'
                      ? '此樣品已分貨，因此此區塊預設收合；若需要補建 WIP 可以展開'
                      : '系統會依照委託單實驗需求預先產生 WIP；必要時仍可新增或修改'
                  }
                  open={openSections.createWip}
                  onToggle={() => toggleSection('createWip')}
                  right={
                    <div style={sectionButtonGroupStyle}>
                      <button
                        onClick={(event) => {
                          event.stopPropagation()
                          regenerateFormsFromOrder()
                        }}
                        style={secondaryButtonStyle}
                        type="button"
                      >
                        重新依單產生
                      </button>

                      <button
                        onClick={(event) => {
                          event.stopPropagation()
                          addForm()
                        }}
                        style={secondaryButtonStyle}
                        type="button"
                      >
                        新增一筆
                      </button>
                    </div>
                  }
                >
                  {hasAutoGeneratedForms && (
                    <div style={autoGenerateNoticeStyle}>
                      已根據委託單實驗需求自動產生 WIP 項目，你可以直接確認建立。
                    </div>
                  )}

                  {!hasAutoGeneratedForms && currentLabRequestedExperiments.length === 0 && (
                    <div style={warningNoticeStyle}>
                      這張單子目前沒有指定 {currentLab} 的實驗需求。若確定要在本 Lab 建立 WIP，可以手動新增。
                    </div>
                  )}

                  <div style={formListStyle}>
                    {forms.map((form, index) => (
                      <div key={`${index}-${form.priority}-${form.experiment_item}`} style={formCardStyle}>
                        <div style={formCardHeaderStyle}>
                          <div>
                            <div style={{ fontWeight: 800 }}>
                              WIP #{index + 1}
                              {form.auto_generated && (
                                <span style={autoTagStyle}>自動帶入</span>
                              )}
                            </div>
                            <div style={panelHintStyle}>
                              {buildWipNo(index)} · {form.lab_name || currentLab}
                            </div>
                          </div>

                          <div style={formActionsStyle}>
                            <button
                              onClick={() => duplicateForm(index)}
                              type="button"
                              style={smallSecondaryButtonStyle}
                            >
                              複製
                            </button>

                            <button
                              onClick={() => removeForm(index)}
                              type="button"
                              disabled={forms.length === 1}
                              style={{
                                ...smallDangerButtonStyle,
                                opacity: forms.length === 1 ? 0.45 : 1,
                                cursor: forms.length === 1 ? 'not-allowed' : 'pointer',
                              }}
                            >
                              刪除
                            </button>
                          </div>
                        </div>

                        <div style={formGridStyle}>
                          <Field label="負責實驗室">
                            <input
                              value={form.lab_name}
                              readOnly
                              style={{
                                ...inputStyle,
                                opacity: 0.75,
                                cursor: 'not-allowed',
                              }}
                            />
                          </Field>

                          <Field label="實驗項目">
                            <input
                              value={form.experiment_item}
                              onChange={(event) =>
                                updateForm(index, 'experiment_item', event.target.value)
                              }
                              list={`experiment-options-${index}`}
                              placeholder="請選擇或輸入實驗項目"
                              style={inputStyle}
                            />

                            <datalist id={`experiment-options-${index}`}>
                              {experimentOptions.map((item) => (
                                <option key={item} value={item} />
                              ))}
                            </datalist>
                          </Field>

                          <Field label="優先級">
                            <select
                              value={form.priority}
                              onChange={(event) =>
                                updateForm(index, 'priority', event.target.value)
                              }
                              style={inputStyle}
                            >
                              <option value="low">低</option>
                              <option value="normal">一般</option>
                              <option value="high">高</option>
                              <option value="urgent">急件</option>
                            </select>
                          </Field>
                        </div>

                        <Field label="備註">
                          <textarea
                            value={form.note}
                            onChange={(event) => updateForm(index, 'note', event.target.value)}
                            placeholder="可填寫特殊需求、檢測條件或注意事項"
                            style={textareaStyle}
                          />
                        </Field>
                      </div>
                    ))}
                  </div>

                  <div style={submitBarStyle}>
                    <button
                      onClick={submitSplit}
                      disabled={submitting || !canCreateWip}
                      style={{
                        ...primaryButtonStyle,
                        opacity: submitting || !canCreateWip ? 0.55 : 1,
                        cursor: submitting || !canCreateWip ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {submitting ? '建立中...' : '建立 WIP / 完成分貨'}
                    </button>
                  </div>
                </CollapsibleSection>

                <CollapsibleSection
                  title="目前已建立的 WIP"
                  hint="只顯示目前實驗室的 WIP / 實驗子單"
                  open={openSections.currentWips}
                  onToggle={() => toggleSection('currentWips')}
                  right={<span style={countBadgeStyle}>{selectedWips.length} 筆</span>}
                >
                  {selectedWips.length === 0 ? (
                    <div style={emptyStyle}>此樣品目前尚未建立本實驗室的 WIP</div>
                  ) : (
                    <div style={labListStyle}>
                      {Object.entries(wipsByLab).map(([labName, labWips]) => (
                        <div key={labName} style={labGroupStyle}>
                          <div style={labGroupHeaderStyle}>
                            <span>{labName}</span>
                            <span style={countBadgeStyle}>{labWips.length} 個實驗</span>
                          </div>

                          <div style={wipListStyle}>
                            {labWips.map((wip) => (
                              <div key={wip.id} style={wipCardStyle}>
                                <div>
                                  <div style={wipTitleStyle}>
                                    {wip.experiment_item ?? '未命名實驗'}
                                  </div>

                                  <div style={wipMetaStyle}>
                                    {wip.wip_no} · 優先級：
                                    {priorityText[wip.priority] ?? wip.priority}
                                  </div>

                                  <div style={wipMetaStyle}>位置：{wip.current_location ?? '-'}</div>
                                </div>

                                <div style={{ textAlign: 'right' }}>
                                  <div style={{ fontSize: 12, fontWeight: 800 }}>
                                    {wipStatusText[wip.status] ?? wip.status}
                                  </div>

                                  <div style={wipMetaStyle}>進度 {wip.progress}%</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedWips.length > 0 && (
                    <div style={submitBarStyle}>
                      <button onClick={goToSchedulePage} style={primaryButtonStyle}>
                        前往排程 / 派工
                      </button>
                    </div>
                  )}
                </CollapsibleSection>
              </>
            )}
          </main>
        </div>
      )}
    </div>
  )
}

function CollapsibleSection({
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
  return (
    <section style={panelStyle}>
      <button onClick={onToggle} type="button" style={sectionToggleHeaderStyle}>
        <div>
          <div style={{ fontWeight: 800 }}>{title}</div>
          {hint && <div style={panelHintStyle}>{hint}</div>}
        </div>

        <div style={sectionHeaderRightStyle}>
          {right}
          <span style={collapseIconStyle}>{open ? '收合 ▲' : '展開 ▼'}</span>
        </div>
      </button>

      {open && children}
    </section>
  )
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div style={infoItemStyle}>
      <div style={infoLabelStyle}>{label}</div>
      <div style={infoValueStyle}>{value}</div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label style={fieldStyle}>
      <span style={fieldLabelStyle}>{label}</span>
      {children}
    </label>
  )
}

function StatusBadge({ status }: { status: string }) {
  return <span style={statusBadgeStyle}>{sampleStatusText[status] ?? status}</span>
}

const titleStyle: CSSProperties = {
  fontSize: 24,
  fontWeight: 900,
  letterSpacing: -0.5,
}

const headerStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 16,
  marginBottom: 24,
}

const headerActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
}

const subtitleStyle: CSSProperties = {
  fontSize: 12,
  color: 'var(--text3)',
  marginTop: 4,
  fontFamily: 'monospace',
}

const layoutStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '320px minmax(0, 1fr)',
  gap: 18,
  alignItems: 'start',
}

const leftPanelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  overflow: 'hidden',
  position: 'sticky',
  top: 18,
}

const mainPanelStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 18,
  minWidth: 0,
}

const panelStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border2)',
  borderRadius: 14,
  overflow: 'hidden',
}

const panelHeaderStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 18px',
  borderBottom: '1px solid var(--border2)',
  gap: 10,
}

const sectionToggleHeaderStyle: CSSProperties = {
  width: '100%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 18px',
  border: 'none',
  borderBottom: '1px solid var(--border2)',
  background: 'var(--s1)',
  color: 'var(--text2)',
  textAlign: 'left',
  cursor: 'pointer',
  gap: 10,
}

const sectionHeaderRightStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  flexShrink: 0,
}

const sectionButtonGroupStyle: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  flexWrap: 'wrap',
  justifyContent: 'flex-end',
}

const collapseIconStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  fontFamily: 'monospace',
  whiteSpace: 'nowrap',
}

const panelHintStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 12,
  marginTop: 4,
}

const countBadgeStyle: CSSProperties = {
  fontSize: 10,
  fontFamily: 'monospace',
  color: 'var(--text3)',
  background: 'var(--s3)',
  padding: '3px 8px',
  borderRadius: 999,
  whiteSpace: 'nowrap',
}

const sampleListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 10,
  padding: 12,
  maxHeight: 'calc(100vh - 210px)',
  overflowY: 'auto',
}

const sampleCardStyle: CSSProperties = {
  display: 'block',
  width: '100%',
  textAlign: 'left',
  border: '1px solid var(--border2)',
  borderRadius: 12,
  padding: 12,
  color: 'var(--text2)',
  cursor: 'pointer',
}

const sampleCardTopStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 10,
  alignItems: 'center',
  marginBottom: 8,
}

const sampleNameStyle: CSSProperties = {
  fontWeight: 800,
  fontSize: 13,
  marginBottom: 5,
}

const sampleMetaStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
}

const monoTextStyle: CSSProperties = {
  fontFamily: 'monospace',
  fontSize: 11,
  color: 'var(--text2)',
}

const detailGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
  gap: 10,
  padding: 18,
}

const infoItemStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
  borderRadius: 10,
  padding: 12,
}

const infoLabelStyle: CSSProperties = {
  fontSize: 10,
  color: 'var(--text3)',
  fontFamily: 'monospace',
  marginBottom: 6,
}

const infoValueStyle: CSSProperties = {
  fontSize: 13,
  color: 'var(--text2)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
}

const labNoticeStyle: CSSProperties = {
  margin: '0 18px 18px',
  padding: 12,
  borderRadius: 10,
  background: 'rgba(56,139,253,0.1)',
  border: '1px solid rgba(56,139,253,0.25)',
  color: 'var(--text2)',
  fontSize: 13,
  lineHeight: 1.7,
}

const autoGenerateNoticeStyle: CSSProperties = {
  margin: '18px 18px 0',
  padding: 12,
  borderRadius: 10,
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.28)',
  color: 'var(--green)',
  fontSize: 13,
}

const warningNoticeStyle: CSSProperties = {
  margin: '18px 18px 0',
  padding: 12,
  borderRadius: 10,
  background: 'rgba(210,153,34,0.12)',
  border: '1px solid rgba(210,153,34,0.28)',
  color: 'var(--yellow)',
  fontSize: 13,
}

const formListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  padding: 18,
}

const formCardStyle: CSSProperties = {
  border: '1px solid var(--border2)',
  borderRadius: 12,
  background: 'var(--s2)',
  padding: 14,
}

const formCardHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start',
  gap: 12,
  marginBottom: 14,
}

const formActionsStyle: CSSProperties = {
  display: 'flex',
  gap: 8,
}

const formGridStyle: CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
  gap: 12,
  marginBottom: 12,
}

const fieldStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  fontSize: 12,
  color: 'var(--text3)',
}

const fieldLabelStyle: CSSProperties = {
  fontSize: 11,
  color: 'var(--text3)',
  fontWeight: 700,
}

const inputStyle: CSSProperties = {
  width: '100%',
  background: 'var(--s1)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  borderRadius: 9,
  padding: '9px 10px',
  outline: 'none',
  fontSize: 13,
}

const textareaStyle: CSSProperties = {
  ...inputStyle,
  minHeight: 76,
  resize: 'vertical',
}

const submitBarStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'flex-end',
  gap: 8,
  flexWrap: 'wrap',
  padding: '0 18px 18px',
}

const labListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  padding: 18,
}

const labGroupStyle: CSSProperties = {
  border: '1px solid var(--border2)',
  borderRadius: 12,
  background: 'rgba(56,139,253,0.04)',
  padding: 10,
}

const labGroupHeaderStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 10,
  fontSize: 13,
  fontWeight: 800,
}

const wipListStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
}

const wipCardStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 12,
  padding: 12,
  borderRadius: 10,
  background: 'var(--s2)',
  border: '1px solid var(--border2)',
}

const wipTitleStyle: CSSProperties = {
  fontWeight: 800,
  fontSize: 13,
}

const wipMetaStyle: CSSProperties = {
  color: 'var(--text3)',
  fontSize: 11,
  marginTop: 4,
}

const emptyStyle: CSSProperties = {
  padding: 28,
  color: 'var(--text3)',
  fontSize: 13,
  textAlign: 'center',
}

const errorStyle: CSSProperties = {
  background: 'rgba(248,81,73,0.12)',
  border: '1px solid rgba(248,81,73,0.3)',
  color: 'var(--red)',
  padding: '10px 14px',
  borderRadius: 10,
  marginBottom: 16,
  fontSize: 13,
}

const successStyle: CSSProperties = {
  background: 'rgba(63,185,80,0.12)',
  border: '1px solid rgba(63,185,80,0.3)',
  color: 'var(--green)',
  padding: '10px 14px',
  borderRadius: 10,
  marginBottom: 16,
  fontSize: 13,
}

const statusBadgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '4px 9px',
  borderRadius: 999,
  background: 'rgba(56,139,253,0.12)',
  border: '1px solid rgba(56,139,253,0.28)',
  color: 'var(--text2)',
  fontSize: 11,
  fontWeight: 700,
  whiteSpace: 'nowrap',
}

const autoTagStyle: CSSProperties = {
  display: 'inline-flex',
  marginLeft: 8,
  padding: '2px 7px',
  borderRadius: 999,
  background: 'rgba(63,185,80,0.14)',
  color: 'var(--green)',
  border: '1px solid rgba(63,185,80,0.28)',
  fontSize: 10,
  verticalAlign: 'middle',
}

const primaryButtonStyle: CSSProperties = {
  background: 'var(--blue)',
  border: '1px solid var(--blue)',
  color: '#fff',
  padding: '8px 14px',
  borderRadius: 8,
  fontSize: 12,
  cursor: 'pointer',
}

const secondaryButtonStyle: CSSProperties = {
  background: 'var(--s2)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  padding: '8px 14px',
  borderRadius: 8,
  fontSize: 12,
  cursor: 'pointer',
}

const smallSecondaryButtonStyle: CSSProperties = {
  background: 'var(--s1)',
  border: '1px solid var(--border)',
  color: 'var(--text2)',
  padding: '6px 10px',
  borderRadius: 8,
  fontSize: 11,
  cursor: 'pointer',
}

const smallDangerButtonStyle: CSSProperties = {
  background: 'rgba(248,81,73,0.1)',
  border: '1px solid rgba(248,81,73,0.28)',
  color: 'var(--red)',
  padding: '6px 10px',
  borderRadius: 8,
  fontSize: 11,
  cursor: 'pointer',
}