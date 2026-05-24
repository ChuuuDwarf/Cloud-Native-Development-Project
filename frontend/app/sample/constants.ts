import type { CurrentUser } from './types'

export const fallbackUser: CurrentUser = {
  id: 'fallback',
  name: '實驗室人員A',
  role: 'lab_engineer',
  role_name: '實驗室人員',
  department: 'Lab A',
  lab_name: 'Lab A',
  email: '',
}

export const sampleStatusText: Record<string, string> = {
  approved: '已核准 / 未送樣',
  pending_receive: '待收樣',
  received: '已收樣',
  split: '已分貨',
  pending_transfer: '待交接',
  transferring: '交接中',
  transfer_pending: '交接待送出',
  transferred_waiting_receive: '已轉出 / 等待接收實驗室收樣',
  transferred_received: '已被接收實驗室收樣',
  transferred_out: '已轉出 / 後續由接收實驗室處理',
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
