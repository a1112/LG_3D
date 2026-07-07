import { describe, expect, it } from 'vitest'

import {
  buildManualDefectAddPayload,
  buildManualDefectExportPayload,
  buildManualDefectUpdatePayload,
  canEditManualDefect,
  formatManualDefectExportError,
  formatManualDefectExportResult,
  getExportableDefects,
  getManualDefectExportCounts,
  getManualDefectFormValues,
} from './manualDefect'
import type { DefectData } from '@/types'

function defect(overrides: Partial<DefectData> = {}): DefectData {
  return {
    id: 51,
    coilId: 42,
    surface: 'S',
    defectType: '边裂',
    position: { x: 12, y: 34 },
    size: { width: 56, height: 78 },
    confidence: 1,
    raw: { type: 'manual', remark: 'old', annotator: 'operator' },
    ...overrides,
  }
}

describe('manualDefect', () => {
  it('allows editing only QML manual defect rows', () => {
    expect(canEditManualDefect(defect())).toBe(true)
    expect(canEditManualDefect(defect({ raw: {} }))).toBe(true)
    expect(canEditManualDefect(defect({ raw: { type: 'auto' } }))).toBe(false)
    expect(canEditManualDefect(null)).toBe(false)
  })

  it('builds QML-compatible manual defect update payload with form defaults', () => {
    expect(
      buildManualDefectUpdatePayload({
        defectName: '',
        defectX: Number.NaN,
        defectY: Number.NaN,
        defectW: 0,
        defectH: 0,
        remark: 'checked',
      }),
    ).toEqual({
      defectName: '未知缺陷',
      defectX: 0,
      defectY: 0,
      defectW: 100,
      defectH: 100,
      remark: 'checked',
    })
  })

  it('builds QML-compatible manual defect add payload from a selected rectangle', () => {
    expect(
      buildManualDefectAddPayload({
        coilId: 193113,
        surfaceKey: 'L',
        rect: { x: 12, y: 34, width: 56, height: 78 },
        defectName: '',
        remark: 'new mark',
      }),
    ).toEqual({
      secondaryCoilId: 193113,
      surface: 'L',
      defectName: '未知缺陷',
      defectX: 12,
      defectY: 34,
      defectW: 56,
      defectH: 78,
      remark: 'new mark',
      annotator: '系统用户',
    })
  })

  it('initializes the edit form from a defect row like QML openForDefect', () => {
    expect(getManualDefectFormValues(defect())).toEqual({
      defectName: '边裂',
      defectX: 12,
      defectY: 34,
      defectW: 56,
      defectH: 78,
      remark: 'old',
    })
  })

  it('selects all, manual-only, or selected defects for export', () => {
    const manual = defect({ id: 1 })
    const auto = defect({ id: 2, raw: { type: 'auto' } })
    const selected = defect({ id: 3, raw: { type: 'manual', selected: true } })
    const defects = [manual, auto, selected]

    expect(getExportableDefects(defects, 'all')).toEqual(defects)
    expect(getExportableDefects(defects, 'manual')).toEqual([manual, selected])
    expect(getExportableDefects(defects, 'selected')).toEqual([selected])
  })

  it('counts manual and selected defects for the QML export dialog labels', () => {
    const defects = [
      defect({ id: 1 }),
      defect({ id: 2, raw: { type: 'auto' } }),
      defect({ id: 3, raw: { type: 'manual', selected: true } }),
    ]

    expect(getManualDefectExportCounts(defects)).toEqual({
      total: 3,
      manual: 2,
      selected: 1,
    })
  })

  it('exports defects with the QML HeadToolBox payload shape and defaults', () => {
    const sparse = defect({
      id: 52,
      coilId: 0,
      surface: '' as DefectData['surface'],
      defectType: '',
      position: { x: Number.NaN, y: Number.NaN },
      size: { width: 0, height: 0 },
      raw: { type: 'manual' },
    })

    expect(buildManualDefectExportPayload([defect(), sparse], 'D:\\exports', 'manual')).toEqual({
      defects: [
        {
          secondaryCoilId: 42,
          surface: 'S',
          defectName: '边裂',
          defectX: 12,
          defectY: 34,
          defectW: 56,
          defectH: 78,
        },
        {
          secondaryCoilId: 52,
          surface: 'S',
          defectName: 'Unknown',
          defectX: 0,
          defectY: 0,
          defectW: 100,
          defectH: 100,
        },
      ],
      folder_path: 'D:\\exports',
      group_by_category: true,
      include_info: true,
      high_quality: false,
    })
  })

  it('formats QML-compatible export result text', () => {
    expect(formatManualDefectExportResult({ exported: 2, total: 3, categories: 1 })).toBe(
      '成功导出 2 个缺陷图像\n共 3 个缺陷\n分类: 1 个',
    )
  })

  it('formats QML-compatible export error text', () => {
    expect(formatManualDefectExportError({ message: 'export failed' })).toBe(
      '导出过程中发生错误:\n{"message":"export failed"}',
    )
    expect(formatManualDefectExportError('network')).toBe('导出过程中发生错误:\n"network"')
  })
})
