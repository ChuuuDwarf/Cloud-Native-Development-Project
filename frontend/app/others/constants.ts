import type { RequestedExperiment } from './types'

export const tabs = [
  { key: 'users', label: '使用者 / 權限' },
  { key: 'labs', label: '實驗室' },
  { key: 'storage', label: '儲位' },
  { key: 'orders', label: '委託單 / 待收樣' },
  { key: 'schedules', label: '排程 / 派工' },
  { key: 'issues', label: '異常 / 告警' },
  { key: 'master', label: '狀態選項' },
] as const

export type TabKey = (typeof tabs)[number]['key']

export const defaultForms: Record<TabKey, Record<string, string>> = {
  users: {
    name: '',
    role: 'lab_engineer',
    role_name: '實驗室人員',
    department: '',
    lab_name: '',
    email: '',
  },
  labs: {
    name: '',
    description: '材料與電性測試',
  },
  storage: {
    code: '',
    name: '',
    lab_name: '',
  },
  orders: {
    order_no: '',
    applicant_name: '王建國',
    applicant_department: 'F12 廠',
    sample_name: '晶圓切片',
    sample_quantity: '1',
    requested_experiment_keys: '',
    priority: 'normal',
    status: 'approved',
  },
  schedules: {
    wip_no: '',
    machine_name: '',
    status: 'waiting_schedule',
    start_time: '',
  },
  issues: {
    type: 'warning',
    target_type: 'sample',
    target_no: '',
    level: 'medium',
    message: '',
    status: 'open',
  },
  master: {
    category: 'sample_statuses',
    value: '',
    label: '',
  },
}

export const sampleStatusText: Record<string, string> = {
  approved: '已核准 / 未送樣',
  pending_receive: '待收樣',
  received: '已收樣',
  split: '已分貨',
  pending_transfer: '可交接',
  in_storage: '已入庫',
  outbound: '待取件',
  picked_up: '已取件',
}

export const wipStatusText: Record<string, string> = {
  created: '已建立',
  waiting_schedule: '待排程',
  scheduled: '已排程',
  dispatched: '已派工',
  running: '執行中',
  paused: '暫停',
  completed: '已完成',
  terminated: '已終止',
  cancelled: '已取消',
}

export const priorityText: Record<string, string> = {
  low: '低',
  normal: '一般',
  high: '高',
  urgent: '急件',
}

export const orderStatusText: Record<string, string> = {
  approved: '已核准 / 未送樣',
  pending_receive: '已確認送樣 / 待收樣',
  received: '已收樣',
  split: '已分貨',
  testing: '實驗中',
  completed: '已完成',
  cancelled: '已取消',
}
