import { describe, expect, it } from 'vitest'

import { headerActionsStyle, layoutStyle, sectionButtonGroupStyle } from './styles'

describe('wip RWD style contract', () => {
  it('WIP 主版面採用左側清單加右側內容的 grid 架構', () => {
    expect(layoutStyle.display).toBe('grid')
    expect(String(layoutStyle.gridTemplateColumns)).toContain('320px')
    expect(String(layoutStyle.gridTemplateColumns)).toContain('minmax(0, 1fr)')
  })

  it('header 與區塊按鈕可換行，降低小螢幕溢出風險', () => {
    expect(headerActionsStyle.flexWrap).toBe('wrap')
    expect(sectionButtonGroupStyle.flexWrap).toBe('wrap')
  })
})
