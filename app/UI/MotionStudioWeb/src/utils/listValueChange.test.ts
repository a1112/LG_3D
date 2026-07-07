import { describe, expect, it } from 'vitest'

import {
  buildListValueChangeInitialRange,
  buildListValueChangePoints,
  chooseListValueChangeKey,
  normalizeListValueChangeKeys,
} from './listValueChange'

describe('list value change helpers', () => {
  it('uses the last visible coil as start and the first visible coil as end like QML', () => {
    const range = buildListValueChangeInitialRange([
      { id: 193113, coilNo: 'A', dateTime: '', status: 0, surfaceKey: 'S' },
      { id: 193112, coilNo: 'B', dateTime: '', status: 0, surfaceKey: 'S' },
      { id: 193110, coilNo: 'C', dateTime: '', status: 0, surfaceKey: 'S' },
    ])

    expect(range).toEqual({ startId: '193110', endId: '193113' })
  })

  it('returns empty inputs when the visible coil list is empty', () => {
    expect(buildListValueChangeInitialRange([])).toEqual({ startId: '', endId: '' })
  })

  it('normalizes backend key arrays into non-empty strings', () => {
    expect(normalizeListValueChangeKeys(['Grade', '', 123, null, 'ActWidth'])).toEqual(['Grade', 'ActWidth'])
  })

  it('builds numeric trend points from Python raw fields in ascending coil order', () => {
    const points = buildListValueChangePoints(
      [
        {
          id: 193113,
          coilNo: 'LG-A',
          dateTime: '',
          status: 0,
          surfaceKey: 'S',
          raw: { ActWidth: '1248.5' },
        },
        {
          id: 193110,
          coilNo: 'LG-C',
          dateTime: '',
          status: 0,
          surfaceKey: 'S',
          raw: { ActWidth: 1251 },
        },
        {
          id: 193112,
          coilNo: 'LG-B',
          dateTime: '',
          status: 0,
          surfaceKey: 'S',
          raw: { ActWidth: null },
        },
      ],
      'ActWidth',
    )

    expect(points).toEqual([
      { coilId: 193110, coilNo: 'LG-C', label: '193110', value: 1251 },
      { coilId: 193113, coilNo: 'LG-A', label: '193113', value: 1248.5 },
    ])
  })

  it('filters trend points by the inclusive start and end coil id inputs', () => {
    const coils = [
      { id: 105, coilNo: 'E', dateTime: '', status: 0, surfaceKey: 'S' as const, raw: { Grade: 5 } },
      { id: 101, coilNo: 'A', dateTime: '', status: 0, surfaceKey: 'S' as const, raw: { Grade: 1 } },
      { id: 103, coilNo: 'C', dateTime: '', status: 0, surfaceKey: 'S' as const, raw: { Grade: 3 } },
      { id: 102, coilNo: 'B', dateTime: '', status: 0, surfaceKey: 'S' as const, raw: { Grade: 2 } },
    ]

    expect(buildListValueChangePoints(coils, 'Grade', { startId: '102', endId: '104' })).toEqual([
      { coilId: 102, coilNo: 'B', label: '102', value: 2 },
      { coilId: 103, coilNo: 'C', label: '103', value: 3 },
    ])

    expect(buildListValueChangePoints(coils, 'Grade', { startId: '104', endId: '102' })).toEqual([
      { coilId: 102, coilNo: 'B', label: '102', value: 2 },
      { coilId: 103, coilNo: 'C', label: '103', value: 3 },
    ])
  })

  it('falls back to normalized React fields for QML key names', () => {
    expect(
      buildListValueChangePoints(
        [
          { id: 1, coilNo: 'A', dateTime: '', status: 0, surfaceKey: 'S', grade: 2 },
          { id: 2, coilNo: 'B', dateTime: '', status: 0, surfaceKey: 'S', defectCountS: 4 },
        ],
        'Grade',
      ),
    ).toEqual([{ coilId: 1, coilNo: 'A', label: '1', value: 2 }])
  })

  it('maps QML display labels to the matching backend fields', () => {
    expect(
      buildListValueChangePoints(
        [
          {
            id: 1,
            coilNo: 'A',
            dateTime: '',
            status: 0,
            surfaceKey: 'S',
            raw: { Thickness: '2.4', DefectCountS: 3, DefectCountL: 2 },
          },
        ],
        '二级厚度',
      ),
    ).toEqual([{ coilId: 1, coilNo: 'A', label: '1', value: 2.4 }])

    expect(
      buildListValueChangePoints(
        [
          {
            id: 1,
            coilNo: 'A',
            dateTime: '',
            status: 0,
            surfaceKey: 'S',
            raw: { DefectCountS: 3, DefectCountL: 2 },
          },
        ],
        '缺陷',
      ),
    ).toEqual([{ coilId: 1, coilNo: 'A', label: '1', value: 5 }])
  })

  it('reads QML display labels from camelCase coil raw aliases', () => {
    const coils = [
      {
        id: 301,
        coilNo: 'A',
        dateTime: '',
        status: 0,
        surfaceKey: 'S' as const,
        raw: { coilInside: '610', coilDia: 1810, coilThickness: '2.8', coilWidth: 1255 },
      },
    ]

    expect(buildListValueChangePoints(coils, '二级内径')).toEqual([
      { coilId: 301, coilNo: 'A', label: '301', value: 610 },
    ])
    expect(buildListValueChangePoints(coils, '二级卷径')).toEqual([
      { coilId: 301, coilNo: 'A', label: '301', value: 1810 },
    ])
    expect(buildListValueChangePoints(coils, '二级厚度')).toEqual([
      { coilId: 301, coilNo: 'A', label: '301', value: 2.8 },
    ])
    expect(buildListValueChangePoints(coils, '宽度')).toEqual([
      { coilId: 301, coilNo: 'A', label: '301', value: 1255 },
    ])
  })

  it('chooses the first backend key like the QML ComboBox default selection', () => {
    const coils = [
      {
        id: 1,
        coilNo: 'A',
        dateTime: '',
        status: 0,
        surfaceKey: 'S' as const,
        raw: { Thickness: '', DefectCountS: 0, DefectCountL: 0 },
      },
    ]

    expect(chooseListValueChangeKey(['二级厚度', '缺陷'], coils)).toBe('二级厚度')
    expect(chooseListValueChangeKey(['距离平均'], coils)).toBe('距离平均')
    expect(chooseListValueChangeKey([], coils)).toBeUndefined()
  })
})
