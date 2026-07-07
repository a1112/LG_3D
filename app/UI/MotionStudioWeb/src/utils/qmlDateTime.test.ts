import { describe, expect, it } from 'vitest'

import * as qmlDateTime from './qmlDateTime'
import { formatQmlDateTimeMinute, getQmlCurrentDayRange, resolveQmlDateRangeSearch } from './qmlDateTime'

describe('QML date time helpers', () => {
  it('formats local dates with the same minute precision as QML DateTime.dateTimeString', () => {
    expect(formatQmlDateTimeMinute(new Date(2026, 5, 28, 3, 4, 59))).toBe('202606280304')
  })

  it('formats the QML TimeText header clock with second precision', () => {
    const formatQmlTimeText = (
      qmlDateTime as unknown as {
        formatQmlTimeText?: (value: Date) => string
      }
    ).formatQmlTimeText

    expect(formatQmlTimeText).toBeTypeOf('function')
    expect(formatQmlTimeText?.(new Date(2026, 6, 3, 4, 5, 6))).toBe('2026-07-03 04:05:06')
    expect(formatQmlTimeText?.(new Date(2026, 11, 31, 23, 59, 59))).toBe('2026-12-31 23:59:59')
  })

  it('defaults date searches to current-day midnight through now like the QML time search panel', () => {
    const [start, end] = getQmlCurrentDayRange(new Date(2026, 5, 28, 14, 37, 10))

    expect(formatQmlDateTimeMinute(start)).toBe('202606280000')
    expect(formatQmlDateTimeMinute(end)).toBe('202606281437')
  })

  it('requires a complete range before building a backend date search request', () => {
    expect(resolveQmlDateRangeSearch(null)).toEqual({ kind: 'none' })
    expect(resolveQmlDateRangeSearch([new Date(2026, 5, 28, 0, 0), null])).toEqual({ kind: 'none' })

    expect(
      resolveQmlDateRangeSearch([
        new Date(2026, 5, 28, 0, 0),
        new Date(2026, 5, 28, 23, 59),
      ]),
    ).toEqual({
      kind: 'range',
      start: '202606280000',
      end: '202606282359',
    })
  })
})
