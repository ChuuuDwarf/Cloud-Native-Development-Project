import { describe, expect, it } from 'vitest'

import type { OthersData } from '../types'
import { formatRequestedExperiments } from './format'

type Order = OthersData['orders'][number]

const makeOrder = (overrides: Partial<Order> = {}): Order =>
  ({
    id: 'order-1',
    order_no: 'ORD-2026-0001',
    applicant_name: '王建國',
    applicant_department: 'F12 廠',
    status: 'approved',
    target_lab: 'Lab A',
    test_item: 'SEM 觀察',
    requested_experiments: [],
    created_at: '2026-05-23T00:00:00',
    updated_at: '2026-05-23T00:00:00',
    ...overrides,
  }) as Order

describe('formatRequestedExperiments', () => {
  it('有 requested_experiments 時，優先格式化多 Lab 實驗項目', () => {
    const order = makeOrder({
      requested_experiments: [
        {
          lab_name: 'Lab A',
          experiment_item: 'SEM 觀察',
        },
        {
          lab_name: 'Lab B',
          experiment_item: '光學量測',
        },
      ],
      target_lab: 'Lab C',
      test_item: 'FTIR',
    })

    expect(formatRequestedExperiments(order)).toBe(
      'Lab A:SEM 觀察、Lab B:光學量測',
    )
  })

  it('requested_experiments 為空時，使用 target_lab 與 test_item', () => {
    const order = makeOrder({
      requested_experiments: [],
      target_lab: 'Lab A',
      test_item: 'SEM 觀察',
    })

    expect(formatRequestedExperiments(order)).toBe('Lab A:SEM 觀察')
  })

  it('只有 target_lab 時，test_item 顯示 -', () => {
    const order = makeOrder({
      requested_experiments: [],
      target_lab: 'Lab A',
    })

    delete (order as Partial<Order>).test_item

    expect(formatRequestedExperiments(order)).toBe('Lab A:-')
  })

  it('只有 test_item 時，target_lab 顯示 -', () => {
    const order = makeOrder({
      requested_experiments: [],
      test_item: 'SEM 觀察',
    })

    delete (order as Partial<Order>).target_lab

    expect(formatRequestedExperiments(order)).toBe('-:SEM 觀察')
  })

  it('沒有 requested_experiments、target_lab、test_item 時顯示 -', () => {
    const order = makeOrder({
      requested_experiments: [],
    })

    delete (order as Partial<Order>).target_lab
    delete (order as Partial<Order>).test_item

    expect(formatRequestedExperiments(order)).toBe('-')
  })

  it('requested_experiments 為 undefined 時也能 fallback', () => {
    const order = makeOrder({
      target_lab: 'Lab B',
      test_item: '光學量測',
    })

    delete (order as Partial<Order>).requested_experiments

    expect(formatRequestedExperiments(order)).toBe('Lab B:光學量測')
  })
})