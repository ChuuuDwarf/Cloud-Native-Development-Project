import type { CurrentUser, WipForm } from './types'

export const fallbackUser: CurrentUser = {
  id: 'USER001',
  name: '實驗室人員A',
  role: 'lab_engineer',
  role_name: '實驗室人員',
  department: 'Lab A',
  lab_name: 'Lab A',
  email: '',
}

export const activeSampleStatuses = new Set(['received', 'split', 'pending_transfer'])

export const sampleStatusText: Record<string, string> = {
  pending_receive: '待收樣',
  received: '已收樣',
  split: '已分貨',
  pending_transfer: '待交接',
  transferring: '交接中',
  in_storage: '已入庫',
  outbound: '待取件',
  picked_up: '已取件',
  lost: '遺失',
  damaged: '破損',
  cancelled: '已取消',
}

export const wipStatusText: Record<string, string> = {
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

export const priorityText: Record<string, string> = {
  low: '低',
  normal: '一般',
  high: '高',
  urgent: '急件',
}

export const experimentOptions = [
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

export const operatorName = 'WIP管理／實驗室人員A'
