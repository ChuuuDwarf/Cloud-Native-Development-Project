import { describe, expect, it, vi } from 'vitest'

import type { Candidate, Sample, Wip } from '../types'
import {
  findMatchingWipForExperiment,
  formatDateTime,
  getCandidateKey,
  getRequestedExperiments,
  isExperimentCompleted,
  normalizeExperiment,
  normalizeLab,
  parseExperimentsFromSummary,
} from './transferFlow'

const sample: Sample = {
  id: 'sample-1',
  sample_no: 'SMP-2026-0001',
  order_no: 'ORD-2026-0001',
  sample_name: '測試樣品',
  experiment_item: 'Lab A:SEM 觀察、Lab B:光學量測、Lab C:Recipe:條件確認',
  applicant_name: '王小明',
  applicant_department: '廠區一課',
  status: 'split',
  current_location: 'Lab A 實驗暫存區',
  note: '備註不應被解析',
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
}

const wips: Wip[] = [
  {
    id: 'wip-a',
    wip_no: 'WIP-2026-0001-A-01',
    sample_id: 'sample-1',
    order_no: 'ORD-2026-0001',
    lab_name: 'Lab A',
    experiment_item: 'SEM 觀察',
    priority: 'normal',
    status: 'completed',
    progress: 100,
    current_location: 'Lab A 實驗暫存區',
    note: null,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
  },
  {
    id: 'wip-b',
    wip_no: 'WIP-2026-0001-B-01',
    sample_id: 'sample-1',
    order_no: 'ORD-2026-0001',
    lab_name: 'Lab B',
    experiment_item: '光學量測',
    priority: 'normal',
    status: 'created',
    progress: 0,
    current_location: 'Lab A 交接待送區',
    note: null,
    created_at: '2026-01-01T00:00:00',
    updated_at: '2026-01-01T00:00:00',
  },
]

describe('transferFlow 功能測試', () => {
  it('Lab 與實驗名稱比對會忽略 null、undefined、前後空白與大小寫', () => {
    expect(normalizeLab(' Lab A ')).toBe('lab a')
    expect(normalizeLab(null)).toBe('')
    expect(normalizeLab(undefined)).toBe('')

    expect(normalizeExperiment(' SEM 觀察 ')).toBe('sem 觀察')
    expect(normalizeExperiment(null)).toBe('')
    expect(normalizeExperiment(undefined)).toBe('')
  })

  it('從 sample.experiment_item 解析跨 Lab 實驗順序，支援實驗名稱內含冒號', () => {
    expect(parseExperimentsFromSummary(sample.experiment_item)).toEqual([
      { lab_name: 'Lab A', experiment_item: 'SEM 觀察' },
      { lab_name: 'Lab B', experiment_item: '光學量測' },
      { lab_name: 'Lab C', experiment_item: 'Recipe:條件確認' },
    ])

    expect(getRequestedExperiments(sample)).toHaveLength(3)
  })

  it('解析實驗需求時會忽略空白片段與缺少 Lab 或實驗項目的片段', () => {
    expect(parseExperimentsFromSummary(null)).toEqual([])
    expect(parseExperimentsFromSummary('')).toEqual([])

    expect(parseExperimentsFromSummary('Lab A:SEM、、Lab B:、:XRD、Lab C:FTIR')).toEqual([
      { lab_name: 'Lab A', experiment_item: 'SEM' },
      { lab_name: 'Lab C', experiment_item: 'FTIR' },
    ])

    expect(getRequestedExperiments(null)).toEqual([])
  })

  it('getRequestedExperiments 只解析 experiment_item，不解析 note', () => {
    expect(getRequestedExperiments({ ...sample, experiment_item: null, note: 'Lab Z:不該被解析' })).toEqual([])
  })

  it('依 Lab 與實驗項目找出對應 WIP，並處理 null 欄位', () => {
    expect(findMatchingWipForExperiment(wips, { lab_name: 'lab b', experiment_item: ' 光學量測 ' })).toMatchObject({
      id: 'wip-b',
    })

    expect(findMatchingWipForExperiment(wips, { lab_name: 'Lab C', experiment_item: 'XRD' })).toBeNull()

    expect(
      findMatchingWipForExperiment(
        [{ ...wips[0], id: 'wip-null', lab_name: null, experiment_item: null }],
        { lab_name: '', experiment_item: '' },
      ),
    ).toMatchObject({ id: 'wip-null' })
  })

  it('只有狀態 completed 的 WIP 視為實驗完成', () => {
    expect(isExperimentCompleted(wips, { lab_name: 'Lab A', experiment_item: 'SEM 觀察' })).toBe(true)
    expect(isExperimentCompleted(wips, { lab_name: 'Lab B', experiment_item: '光學量測' })).toBe(false)
    expect(isExperimentCompleted(wips, { lab_name: 'Lab C', experiment_item: 'XRD' })).toBe(false)
  })

  it('交接候選與歸還候選產生穩定 key，避免列表重繪錯亂', () => {
    const transferCandidate: Candidate = {
      kind: 'transfer',
      sample,
      currentLabCompletedWips: [wips[0]],
      remainingWips: [wips[1]],
      remainingExperiments: [{ lab_name: 'Lab B', experiment_item: '光學量測' }],
      nextLab: 'Lab B',
      nextExperiment: { lab_name: 'Lab B', experiment_item: '光學量測' },
      nextWip: wips[1],
      existingTransfer: null,
    }

    const returnCandidate: Candidate = {
      kind: 'return',
      sample,
      currentLabCompletedWips: wips,
      allWips: wips,
    }

    expect(getCandidateKey(transferCandidate)).toBe('transfer-sample-1-wip-b')
    expect(getCandidateKey(returnCandidate)).toBe('return-sample-1')
  })

  it('交接候選沒有 nextWip 時，使用 nextLab 與 nextExperiment 當 fallback key', () => {
    const transferCandidateWithoutWip: Candidate = {
      kind: 'transfer',
      sample,
      currentLabCompletedWips: [wips[0]],
      remainingWips: [],
      remainingExperiments: [{ lab_name: 'Lab C', experiment_item: 'FTIR' }],
      nextLab: 'Lab C',
      nextExperiment: { lab_name: 'Lab C', experiment_item: 'FTIR' },
      nextWip: null,
      existingTransfer: null,
    }

    expect(getCandidateKey(transferCandidateWithoutWip)).toBe('transfer-sample-1-Lab C-FTIR')
  })

  it('格式化日期時間，空值顯示 -，toLocaleString 失敗時回傳原字串', () => {
    expect(formatDateTime(null)).toBe('-')
    expect(formatDateTime(undefined)).toBe('-')

    const spy = vi.spyOn(Date.prototype, 'toLocaleString').mockImplementation(() => {
      throw new Error('format error')
    })

    expect(formatDateTime('not-a-date')).toBe('not-a-date')

    spy.mockRestore()
  })
})