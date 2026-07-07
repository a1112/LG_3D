import { describe, expect, it } from 'vitest'

import {
  buildDefectClassConfigRows,
  buildDefectClassConfigPayload,
  getDefectClassColorPickerValue,
  updateDefectClassConfigRow,
} from './defectClassConfig'

describe('defect class config helpers', () => {
  it('builds QML DefectClassPop-compatible editable rows', () => {
    expect(
      buildDefectClassConfigRows({
        data: {
          压痕: { level: '3', show: 'true', color: '#ff0000' },
          夹杂: { level: 1, show: false, color: '#999999' },
        },
      }),
    ).toEqual([
      { name: '压痕', level: 3, show: true, color: '#ff0000' },
      { name: '夹杂', level: 1, show: false, color: '#999999' },
    ])
  })

  it('orders visible defect classes before masked classes like QML DefectClassProperty', () => {
    expect(
      buildDefectClassConfigRows({
        data: {
          屏蔽A: { level: 1, show: 'false', color: '#111111' },
          显示A: { level: 2, show: 'true', color: '#222222' },
          显示B: { level: 3, show: true, color: '#333333' },
          屏蔽B: { level: 4, show: false, color: '#444444' },
        },
      }).map((row) => row.name),
    ).toEqual(['显示A', '显示B', '屏蔽A', '屏蔽B'])
  })

  it('normalizes QML-style color objects and missing colors', () => {
    expect(
      buildDefectClassConfigRows({
        data: {
          RGB对象: { level: 1, show: true, color: { r: 255, g: 128, b: 0 } },
          嵌套颜色: { level: 2, show: true, color: { color: { r: 0, g: 64, b: 255 } } },
          缺省颜色: { level: 3, show: true },
        },
      }).map((row) => ({ name: row.name, color: row.color })),
    ).toEqual([
      { name: 'RGB对象', color: '#ff8000' },
      { name: '嵌套颜色', color: '#0040ff' },
      { name: '缺省颜色', color: '#FFA500' },
    ])
  })

  it('maps QML/CSS named colors to color-picker hex values without changing the row color text', () => {
    const rows = buildDefectClassConfigRows({
      data: {
        分层: { level: 5, show: true, color: 'red' },
        报警: { level: 2, show: true, color: 'yellow' },
        普通: { level: 1, show: true, color: 'gray' },
      },
    })

    expect(rows.map((row) => row.color)).toEqual(['red', 'yellow', 'gray'])
    expect(rows.map((row) => getDefectClassColorPickerValue(row.color))).toEqual(['#ff0000', '#ffff00', '#808080'])
  })

  it('builds the direct dictionary payload posted by QML setDefecctClassConfig', () => {
    const rows = [
      { name: '压痕', level: 4, show: true, color: '#00ff00' },
      { name: '夹杂', level: 1, show: false, color: '#999999' },
    ]

    expect(buildDefectClassConfigPayload(rows)).toEqual({
      压痕: { level: '4', show: 'true', color: '#00ff00' },
      夹杂: { level: '1', show: 'false', color: '#999999' },
    })
  })

  it('preserves original defect dictionary fields when building the save payload', () => {
    const rows = buildDefectClassConfigRows({
      data: {
        压痕: {
          name: '压痕',
          level: '3',
          show: 'true',
          color: '#ff0000',
          num: 7,
          vendorMeta: { source: 'qml' },
        },
      },
    })

    rows[0].level = 5
    rows[0].show = false
    rows[0].color = '#00ff00'

    expect(buildDefectClassConfigPayload(rows)).toEqual({
      压痕: {
        name: '压痕',
        level: '5',
        show: 'false',
        color: '#00ff00',
        num: 7,
        vendorMeta: { source: 'qml' },
      },
    })
  })

  it('preserves original defect dictionary fields after a React row edit', () => {
    const rows = buildDefectClassConfigRows({
      data: {
        压痕: {
          name: '压痕',
          level: '3',
          show: 'true',
          color: '#ff0000',
          num: 7,
        },
      },
    })

    const editedRow = updateDefectClassConfigRow(rows[0], { level: 2 })

    expect(buildDefectClassConfigPayload([editedRow])).toEqual({
      压痕: {
        name: '压痕',
        level: '2',
        show: 'true',
        color: '#ff0000',
        num: 7,
      },
    })
  })
})
