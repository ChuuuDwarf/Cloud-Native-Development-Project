import type { ReactNode } from 'react'
import type { OthersData, PayloadValue, RequestedExperiment } from '../types'
import type { TabKey } from '../constants'
import { tabs, defaultForms, sampleStatusText, wipStatusText, priorityText, orderStatusText } from '../constants'
import { formatRequestedExperiments } from '../utils/format'
import { sectionTitleStyle, mutedStyle, primaryButtonStyle, ghostButtonStyle, formBoxStyle, formHeaderStyle, formGridStyle, fieldStyle, fieldTitleStyle, inputStyle, wideFieldStyle, experimentMatrixStyle, experimentLabBoxStyle, experimentLabTitleStyle, experimentItemGridStyle, checkboxLabelStyle, formActionStyle, tableTitleStyle, tableWrapStyle, tableStyle, thStyle, tdStyle, emptyTdStyle, trStyle } from '../styles'

export function CreateForm({
  activeTab,
  form,
  saving,
  onChange,
  onCancel,
  onSubmit,
  masterKeys,
}: {
  activeTab: TabKey
  form: Record<string, string>
  saving: boolean
  onChange: (key: string, value: string) => void
  onCancel: () => void
  onSubmit: () => void
  masterKeys: string[]
}) {
  const titleMap: Record<TabKey, string> = {
    users: '新增使用者',
    labs: '新增實驗室',
    storage: '新增儲位',
    orders: '新增委託單 / 待收樣資料',
    schedules: '新增排程',
    issues: '新增異常 / 告警',
    master: '新增狀態選項',
  }

  const labOptions = [
    { value: '', label: '無 / 不指定' },
    { value: 'Lab A', label: 'Lab A' },
    { value: 'Lab B', label: 'Lab B' },
    { value: 'Lab C', label: 'Lab C' },
  ]

  const departmentOptions = [
    { value: 'F12 廠', label: 'F12 廠' },
    { value: 'F6 廠', label: 'F6 廠' },
    { value: 'Lab A', label: 'Lab A' },
    { value: 'Lab B', label: 'Lab B' },
    { value: 'Lab C', label: 'Lab C' },
    { value: 'Lab 管理部', label: 'Lab 管理部' },
    { value: 'IT', label: 'IT' },
  ]

  const roleOptions = [
    { value: 'plant_user', label: '廠區使用者' },
    { value: 'lab_engineer', label: '實驗室人員' },
    { value: 'lab_supervisor', label: '實驗室主管' },
    { value: 'system_admin', label: '系統管理者' },
  ]

  const orderStatusOptions = [
    { value: 'approved', label: '已核准 / 未送樣 approved' },
    { value: 'pending_receive', label: '已確認送樣 / 待收樣 pending_receive' },
  ]

  const priorityOptions = [
    { value: 'low', label: '低 low' },
    { value: 'normal', label: '一般 normal' },
    { value: 'high', label: '高 high' },
    { value: 'urgent', label: '特急 urgent' },
  ]

  const labExperimentMatrix = [
    {
      labName: 'Lab A',
      items: ['SEM 觀察', '電性量測', '材料分析'],
    },
    {
      labName: 'Lab B',
      items: ['光學量測', '可靠度測試', '外觀檢查'],
    },
    {
      labName: 'Lab C',
      items: ['化學分析', '成分分析', '污染分析'],
    },
  ]

  const sampleQuantityOptions = [
    { value: '1', label: '1 件' },
    { value: '2', label: '2 件' },
    { value: '3', label: '3 件' },
    { value: '5', label: '5 件' },
    { value: '10', label: '10 件' },
  ]

  const scheduleStatusOptions = [
    { value: 'waiting_schedule', label: '待排程 waiting_schedule' },
    { value: 'scheduled', label: '已排程 scheduled' },
    { value: 'running', label: '執行中 running' },
    { value: 'completed', label: '已完成 completed' },
    { value: 'cancelled', label: '已取消 cancelled' },
  ]

  const issueTypeOptions = [
    { value: 'warning', label: '告警 warning' },
    { value: 'abnormal', label: '異常 abnormal' },
    { value: 'terminate', label: '中止 terminate' },
  ]

  const issueTargetTypeOptions = [
    { value: 'sample', label: '樣品 sample' },
    { value: 'wip', label: 'WIP wip' },
    { value: 'experiment_run', label: '實驗執行 experiment_run' },
    { value: 'machine', label: '機台 machine' },
    { value: 'order', label: '委託單 order' },
  ]

  const issueLevelOptions = [
    { value: 'low', label: '低 low' },
    { value: 'medium', label: '中 medium' },
    { value: 'high', label: '高 high' },
    { value: 'critical', label: '嚴重 critical' },
  ]

  const issueStatusOptions = [
    { value: 'open', label: '未處理 open' },
    { value: 'processing', label: '處理中 processing' },
    { value: 'resolved', label: '已解決 resolved' },
    { value: 'closed', label: '已關閉 closed' },
  ]

  const masterCategoryOptions = [
    { value: 'sample_statuses', label: '樣品狀態 sample_statuses' },
    { value: 'wip_statuses', label: 'WIP 狀態 wip_statuses' },
    { value: 'priorities', label: '優先度 priorities' },
    { value: 'experiment_items', label: '實驗項目 experiment_items' },
    { value: 'lab_experiment_matrix', label: '實驗室項目矩陣 lab_experiment_matrix' },
    ...masterKeys
      .filter(
        (key) =>
          ![
            'sample_statuses',
            'wip_statuses',
            'priorities',
            'experiment_items',
            'lab_experiment_matrix',
          ].includes(key),
      )
      .map((key) => ({ value: key, label: key })),
  ]

  function getRequestedExperimentKeys() {
    return form.requested_experiment_keys
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean)
  }

  function toggleRequestedExperiment(key: string) {
    const currentKeys = getRequestedExperimentKeys()

    const nextKeys = currentKeys.includes(key)
      ? currentKeys.filter((item) => item !== key)
      : [...currentKeys, key]

    onChange('requested_experiment_keys', nextKeys.join(','))
  }

  function isRequestedExperimentChecked(key: string) {
    return getRequestedExperimentKeys().includes(key)
  }

  function changeUserRole(role: string) {
    const roleNameMap: Record<string, string> = {
      plant_user: '廠區使用者',
      lab_engineer: '實驗室人員',
      lab_supervisor: '實驗室主管',
      system_admin: '系統管理者',
    }

    onChange('role', role)
    onChange('role_name', roleNameMap[role] ?? role)

    if (role === 'plant_user') {
      onChange('department', 'F12 廠')
      onChange('lab_name', '')
    }

    if (role === 'lab_engineer') {
      onChange('department', 'Lab A')
      onChange('lab_name', 'Lab A')
    }

    if (role === 'lab_supervisor') {
      onChange('department', 'Lab 管理部')
      onChange('lab_name', 'Lab A')
    }

    if (role === 'system_admin') {
      onChange('department', 'IT')
      onChange('lab_name', '')
    }
  }

  return (
    <div style={formBoxStyle}>
      <div style={formHeaderStyle}>
        <div>
          <div style={sectionTitleStyle}>{titleMap[activeTab]}</div>
          <div style={mutedStyle}>
            {activeTab === 'orders'
              ? '這裡新增 approved 時只會建立委託單，不會建立 sample；按確認送樣後才會進 Lab 收樣區。'
              : '這裡新增的是開發期假資料。'}
          </div>
        </div>

        <button style={ghostButtonStyle} onClick={onCancel}>
          關閉
        </button>
      </div>

      {activeTab === 'users' && (
        <div style={formGridStyle}>
          <TextInput label="姓名" value={form.name} onChange={(value) => onChange('name', value)} />
          <SelectInput label="角色" value={form.role} onChange={changeUserRole} options={roleOptions} />
          <SelectInput
            label="部門"
            value={form.department}
            onChange={(value) => onChange('department', value)}
            options={departmentOptions}
          />
          <SelectInput
            label="Lab"
            value={form.lab_name}
            onChange={(value) => onChange('lab_name', value)}
            options={labOptions}
          />
          <TextInput label="Email" value={form.email} onChange={(value) => onChange('email', value)} />
        </div>
      )}

      {activeTab === 'labs' && (
        <div style={formGridStyle}>
          <SelectInput
            label="實驗室名稱"
            value={form.name}
            onChange={(value) => onChange('name', value)}
            options={[
              { value: 'Lab A', label: 'Lab A' },
              { value: 'Lab B', label: 'Lab B' },
              { value: 'Lab C', label: 'Lab C' },
              { value: 'Lab D', label: 'Lab D' },
            ]}
          />

          <SelectInput
            label="說明"
            value={form.description}
            onChange={(value) => onChange('description', value)}
            options={[
              { value: '材料與電性測試', label: '材料與電性測試' },
              { value: '光學與可靠度測試', label: '光學與可靠度測試' },
              { value: '化學分析', label: '化學分析' },
              { value: '製程驗證', label: '製程驗證' },
            ]}
          />
        </div>
      )}

      {activeTab === 'storage' && (
        <div style={formGridStyle}>
          <SelectInput
            label="儲位代碼"
            value={form.code}
            onChange={(value) => onChange('code', value)}
            options={[
              { value: '', label: '系統自動產生' },
              { value: 'A-R01-S01', label: 'A-R01-S01' },
              { value: 'A-R01-S02', label: 'A-R01-S02' },
              { value: 'B-R01-S01', label: 'B-R01-S01' },
              { value: 'B-R01-S02', label: 'B-R01-S02' },
              { value: 'C-R01-S01', label: 'C-R01-S01' },
            ]}
          />

          <SelectInput
            label="儲位名稱"
            value={form.name}
            onChange={(value) => onChange('name', value)}
            options={[
              { value: '', label: '系統自動帶入未命名儲位' },
              { value: 'Lab A 待取件架 1', label: 'Lab A 待取件架 1' },
              { value: 'Lab A 暫存架 2', label: 'Lab A 暫存架 2' },
              { value: 'Lab B 待取件架 1', label: 'Lab B 待取件架 1' },
              { value: 'Lab B 暫存架 2', label: 'Lab B 暫存架 2' },
              { value: 'Lab C 待取件架 1', label: 'Lab C 待取件架 1' },
            ]}
          />

          <SelectInput
            label="所屬 Lab"
            value={form.lab_name}
            onChange={(value) => onChange('lab_name', value)}
            options={labOptions.filter((option) => option.value !== '')}
          />
        </div>
      )}

      {activeTab === 'orders' && (
        <div style={formGridStyle}>
          <TextInput
            label="委託單號"
            value={form.order_no}
            placeholder="不填就由後端產生"
            onChange={(value) => onChange('order_no', value)}
          />

          <SelectInput
            label="申請人"
            value={form.applicant_name}
            onChange={(value) => onChange('applicant_name', value)}
            options={[
              { value: '王建國', label: '王建國' },
              { value: '李美珍', label: '李美珍' },
              { value: '陳怡君', label: '陳怡君' },
              { value: '黃俊傑', label: '黃俊傑' },
            ]}
          />

          <SelectInput
            label="申請部門"
            value={form.applicant_department}
            onChange={(value) => onChange('applicant_department', value)}
            options={departmentOptions.filter((option) => option.value.includes('廠'))}
          />

          <TextInput
            label="樣品名稱"
            value={form.sample_name}
            placeholder="例如 晶圓切片"
            onChange={(value) => onChange('sample_name', value)}
          />

          <SelectInput
            label="樣品數量"
            value={form.sample_quantity}
            onChange={(value) => onChange('sample_quantity', value)}
            options={sampleQuantityOptions}
          />

          <SelectInput
            label="優先度"
            value={form.priority}
            onChange={(value) => onChange('priority', value)}
            options={priorityOptions}
          />

          <SelectInput
            label="委託單狀態"
            value={form.status}
            onChange={(value) => onChange('status', value)}
            options={orderStatusOptions}
          />

          <div style={wideFieldStyle}>
            <div style={fieldTitleStyle}>實驗室 / 實驗項目</div>
            <div style={mutedStyle}>可多選。不同實驗室可以負責不同實驗項目。</div>

            <div style={experimentMatrixStyle}>
              {labExperimentMatrix.map((lab) => (
                <div key={lab.labName} style={experimentLabBoxStyle}>
                  <div style={experimentLabTitleStyle}>{lab.labName}</div>

                  <div style={experimentItemGridStyle}>
                    {lab.items.map((item) => {
                      const key = `${lab.labName}::${item}`

                      return (
                        <label key={key} style={checkboxLabelStyle}>
                          <input
                            type="checkbox"
                            checked={isRequestedExperimentChecked(key)}
                            onChange={() => toggleRequestedExperiment(key)}
                          />
                          <span>{item}</span>
                        </label>
                      )
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'schedules' && (
        <div style={formGridStyle}>
          <TextInput
            label="WIP 編號"
            value={form.wip_no}
            placeholder="例如 WIP-2026-0001-A"
            onChange={(value) => onChange('wip_no', value)}
          />

          <SelectInput
            label="機台名稱"
            value={form.machine_name}
            onChange={(value) => onChange('machine_name', value)}
            options={[
              { value: '', label: '未指定機台' },
              { value: 'SEM-001', label: 'SEM-001' },
              { value: 'OPT-002', label: 'OPT-002' },
              { value: 'XRD-003', label: 'XRD-003' },
              { value: 'FTIR-004', label: 'FTIR-004' },
            ]}
          />

          <SelectInput
            label="狀態"
            value={form.status}
            onChange={(value) => onChange('status', value)}
            options={scheduleStatusOptions}
          />

          <SelectInput
            label="開始時間"
            value={form.start_time}
            onChange={(value) => onChange('start_time', value)}
            options={[
              { value: '', label: '未排定' },
              { value: '2026-05-22T10:00:00', label: '2026-05-22 10:00' },
              { value: '2026-05-22T14:00:00', label: '2026-05-22 14:00' },
              { value: '2026-05-23T09:00:00', label: '2026-05-23 09:00' },
              { value: '2026-05-23T15:00:00', label: '2026-05-23 15:00' },
            ]}
          />
        </div>
      )}

      {activeTab === 'issues' && (
        <div style={formGridStyle}>
          <SelectInput
            label="類型"
            value={form.type}
            onChange={(value) => onChange('type', value)}
            options={issueTypeOptions}
          />

          <SelectInput
            label="目標類型"
            value={form.target_type}
            onChange={(value) => onChange('target_type', value)}
            options={issueTargetTypeOptions}
          />

          <TextInput
            label="目標編號"
            value={form.target_no}
            placeholder="例如 SMP-2026-0001 或 WIP-2026-0001-A"
            onChange={(value) => onChange('target_no', value)}
          />

          <SelectInput
            label="等級"
            value={form.level}
            onChange={(value) => onChange('level', value)}
            options={issueLevelOptions}
          />

          <SelectInput
            label="訊息"
            value={form.message}
            onChange={(value) => onChange('message', value)}
            options={[
              { value: '', label: '未填寫訊息' },
              { value: '樣品待取件超過 2 天', label: '樣品待取件超過 2 天' },
              { value: '機台故障', label: '機台故障' },
              { value: '實驗數據異常', label: '實驗數據異常' },
              { value: 'WIP 超過預計完成時間', label: 'WIP 超過預計完成時間' },
              { value: '樣品交接逾時', label: '樣品交接逾時' },
            ]}
          />

          <SelectInput
            label="狀態"
            value={form.status}
            onChange={(value) => onChange('status', value)}
            options={issueStatusOptions}
          />
        </div>
      )}

      {activeTab === 'master' && (
        <div style={formGridStyle}>
          <SelectInput
            label="分類"
            value={form.category}
            onChange={(value) => onChange('category', value)}
            options={masterCategoryOptions}
          />

          <TextInput
            label="值 value"
            value={form.value}
            placeholder="例如 pending_receive"
            onChange={(value) => onChange('value', value)}
          />

          <TextInput
            label="顯示名稱 label"
            value={form.label}
            placeholder="例如 待收樣"
            onChange={(value) => onChange('label', value)}
          />
        </div>
      )}

      <div style={formActionStyle}>
        <button
          style={{
            ...primaryButtonStyle,
            opacity: saving ? 0.55 : 1,
            cursor: saving ? 'not-allowed' : 'pointer',
          }}
          disabled={saving}
          onClick={onSubmit}
        >
          {saving ? '儲存中...' : '新增'}
        </button>
      </div>
    </div>
  )
}

export function SimpleTable({
  title,
  headers,
  rows,
}: {
  title?: string
  headers: string[]
  rows: Array<Array<string | number | null | undefined>>
}) {
  return (
    <div style={{ marginTop: 14 }}>
      {title && <div style={tableTitleStyle}>{title}</div>}

      <div style={tableWrapStyle}>
        <table style={tableStyle}>
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header} style={thStyle}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td style={emptyTdStyle} colSpan={headers.length}>
                  目前沒有資料
                </td>
              </tr>
            ) : (
              rows.map((row, rowIndex) => (
                <tr key={rowIndex} style={trStyle}>
                  {row.map((cell, cellIndex) => (
                    <td key={`${rowIndex}-${cellIndex}`} style={tdStyle}>
                      {cell ?? '-'}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function TextInput({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string
  value: string
  placeholder?: string
  onChange: (value: string) => void
}) {
  return (
    <label style={fieldStyle}>
      <span style={fieldTitleStyle}>{label}</span>
      <input
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        style={inputStyle}
      />
    </label>
  )
}

export function SelectInput({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: Array<{ value: string; label: string }>
  onChange: (value: string) => void
}) {
  return (
    <label style={fieldStyle}>
      <span style={fieldTitleStyle}>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} style={inputStyle}>
        {options.map((option, index) => (
          <option key={`${option.value}-${index}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}

