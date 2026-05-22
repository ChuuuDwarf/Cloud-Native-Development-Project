import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'

import Chip from './Chip'

describe('Chip', () => {
  it('會渲染 label', () => {
    const html = renderToStaticMarkup(<Chip type="running" label="執行中" />)

    expect(html).toContain('執行中')
    expect(html).toContain('inline-flex')
    expect(html).toContain('monospace')
  })

  it('支援所有 chip type', () => {
    const types = [
      'draft',
      'pending',
      'review',
      'approved',
      'running',
      'done',
      'rejected',
      'paused',
      'idle',
    ] as const

    for (const type of types) {
      const html = renderToStaticMarkup(<Chip type={type} label={type} />)
      expect(html).toContain(type)
    }
  })
})