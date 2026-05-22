import { describe, expect, it } from 'vitest'

import { detailGridStyle, filterBarStyle, summaryGridStyle } from './styles'

describe('sample RWD style contract', () => {
  it('摘要區使用 auto-fit grid，能依裝置寬度自動換欄', () => {
    expect(summaryGridStyle.display).toBe('grid')
    expect(String(summaryGridStyle.gridTemplateColumns)).toContain('auto-fit')
    expect(String(summaryGridStyle.gridTemplateColumns)).toContain('minmax')
  })

  it('篩選列允許換行，避免小螢幕按鈕溢出', () => {
    expect(filterBarStyle.display).toBe('flex')
    expect(filterBarStyle.flexWrap).toBe('wrap')
  })

  it('詳細資料區使用 grid 排版，維持資訊可讀性', () => {
    expect(detailGridStyle.display).toBe('grid')
    expect(String(detailGridStyle.gridTemplateColumns)).toContain('auto-fit')
  })
})
