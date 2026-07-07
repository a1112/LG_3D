import { describe, expect, it } from 'vitest'

import * as coilCheckModule from './coilCheck'
import {
  buildCoilCheckPayload,
  getCoilCheckOption,
  getQmlCoilCheckStatusClass,
  resolveQmlCoilCheckStatus,
  normalizeCoilCheck,
  resolveCoilCheck,
} from './coilCheck'

describe('coilCheck', () => {
  it('normalizes Python/QML coil check rows and defaults to unconfirmed', () => {
    expect(normalizeCoilCheck({ secondaryCoilId: 42, status: 2, msg: 'needs review' })).toEqual({
      coilId: 42,
      status: 2,
      msg: 'needs review',
    })
    expect(normalizeCoilCheck(null, 99)).toEqual({ coilId: 99, status: 0, msg: '' })
  })

  it('maps QML status choices to labels and colors', () => {
    expect(getCoilCheckOption(2)).toEqual({ status: 2, label: '返修', color: 'red' })
    expect(getCoilCheckOption(0)).toEqual({ status: 0, label: '未确认', color: 'yellow' })
    expect(getCoilCheckOption(1)).toEqual({ status: 1, label: '通过', color: 'green' })
  })

  it('builds the QML set status payload shape', () => {
    expect(buildCoilCheckPayload(193113, 1, 'ok')).toEqual({
      coilId: 193113,
      status: 1,
      msg: 'ok',
    })
  })

  it('prefers the locally confirmed QML-style status for the active coil', () => {
    expect(
      resolveCoilCheck(
        { secondaryCoilId: 193113, status: 0, msg: '' },
        193113,
        { coilId: 193113, status: 2, msg: 'needs review' },
      ),
    ).toEqual({
      coilId: 193113,
      status: 2,
      msg: 'needs review',
    })

    expect(
      resolveCoilCheck(
        { secondaryCoilId: 193114, status: 1, msg: 'ok' },
        193114,
        { coilId: 193113, status: 2, msg: 'needs review' },
      ),
    ).toEqual({
      coilId: 193114,
      status: 1,
      msg: 'ok',
    })
  })

  it('resolves the QML list-row status underline from childrenCoilCheck instead of CheckStatus', () => {
    expect(
      resolveQmlCoilCheckStatus({
        CheckStatus: 2,
        childrenCoilCheck: [],
      }),
    ).toBe(0)
    expect(
      resolveQmlCoilCheckStatus({
        childrenCoilCheck: [
          { secondaryCoilId: 193113, status: 1, msg: 'ok' },
          { secondaryCoilId: 193113, status: 2, msg: 'rework' },
        ],
      }),
    ).toBe(2)
  })

  it('maps QML list-row status underline classes', () => {
    expect(getQmlCoilCheckStatusClass({ childrenCoilCheck: [] })).toBe('coil-check-none')
    expect(getQmlCoilCheckStatusClass({ childrenCoilCheck: [{ status: 1 }] })).toBe('coil-check-pass')
    expect(getQmlCoilCheckStatusClass({ childrenCoilCheck: [{ status: 2 }] })).toBe('coil-check-rework')
  })

  it('maps QML SelectMenuItem foreground colors for judgment menu status', () => {
    expect(coilCheckModule).toHaveProperty('getQmlCoilCheckSelectColor')
    expect(coilCheckModule.getQmlCoilCheckSelectColor?.(2)).toBe('#f44336')
    expect(coilCheckModule.getQmlCoilCheckSelectColor?.(0)).toBe('#ffeb3b')
    expect(coilCheckModule.getQmlCoilCheckSelectColor?.(1)).toBe('#4caf50')
  })
})
