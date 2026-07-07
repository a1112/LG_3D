import { describe, expect, it } from 'vitest'

import { buildControlConfigRows, formatControlConfigValue } from './controlConfig'

describe('control config helpers', () => {
  it('returns no rows for an empty control config', () => {
    expect(buildControlConfigRows({})).toEqual([])
    expect(buildControlConfigRows(null)).toEqual([])
  })

  it('flattens scalar and nested control config values into editable rows', () => {
    expect(
      buildControlConfigRows({
        lower_limit: -64.5,
        enabled: true,
        render: {
          max_depth: 20,
          mode: 'dynamic',
        },
      }),
    ).toEqual([
      { key: 'enabled', value: 'true' },
      { key: 'lower_limit', value: '-64.5' },
      { key: 'render.max_depth', value: '20' },
      { key: 'render.mode', value: 'dynamic' },
    ])
  })

  it('formats object and array values as compact JSON for set_property input', () => {
    expect(formatControlConfigValue({ a: 1, b: 'x' })).toBe('{"a":1,"b":"x"}')
    expect(formatControlConfigValue([1, 'x'])).toBe('[1,"x"]')
    expect(formatControlConfigValue(undefined)).toBe('')
  })
})
