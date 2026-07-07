import { describe, expect, it } from 'vitest'

const DEPRECATED_MODAL_PROP = 'destroy' + 'OnClose'
const sourceModules = import.meta.glob('/src/**/*.{ts,tsx}', {
  eager: true,
  import: 'default',
  query: '?raw',
}) as Record<string, string>

describe('Ant Design modal props', () => {
  it('uses destroyOnHidden instead of the deprecated destroyOnClose prop', () => {
    const offenders = Object.entries(sourceModules)
      .filter(([file]) => !file.includes('.test.'))
      .filter(([, source]) => source.includes(DEPRECATED_MODAL_PROP))
      .map(([file]) => file)

    expect(offenders).toEqual([])
  })
})
