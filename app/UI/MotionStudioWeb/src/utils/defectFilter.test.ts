import { describe, expect, it } from 'vitest'

import type { CoilData, DefectData } from '@/types'
import {
  buildDefectClassFilterOptions,
  buildQmlLeftListDefectFilterOptions,
  countDefectsByClass,
  filterDataShowDefects,
  filterDefectsByClass,
  getDefaultSelectedDefectClasses,
  getQmlSelectAllDefectClasses,
  getQmlVisibleFilterOptions,
  getResetDefectClassSelection,
  hasQmlLeftListVisibleDefectOptions,
  reconcileQmlDefectClassSelection,
} from './defectFilter'
import * as defectFilterModule from './defectFilter'

const makeDefect = (id: number, defectType: string): DefectData => ({
  id,
  coilId: 193113,
  surface: 'S',
  defectType,
  position: { x: id * 10, y: id * 20 },
  size: { width: 30, height: 40 },
  confidence: 1,
})

const makeCoil = (id: number, raw: Record<string, unknown>): CoilData => ({
  id,
  coilNo: `coil-${id}`,
  dateTime: '2026-07-02 10:00:00',
  status: 2,
  surfaceKey: 'S',
  raw,
})

function requireFilterFunction<T extends (...args: never[]) => unknown>(name: string): T {
  const fn = (defectFilterModule as Record<string, unknown>)[name]
  expect(fn).toBeTypeOf('function')
  return fn as T
}

describe('defect class filter helpers', () => {
  it('builds QML-style defect options with visible classes first', () => {
    const dict = {
      data: {
        夹杂: { show: false, color: '#999999', level: 1 },
        压痕: { show: 'true', color: '#ff0000', level: 3 },
        划伤: { show: true, color: { r: 0, g: 128, b: 255, a: 1 }, level: 2 },
      },
    }

    expect(buildDefectClassFilterOptions(dict)).toEqual([
      { name: '压痕', color: '#ff0000', level: 3, show: true },
      { name: '划伤', color: 'rgba(0, 128, 255, 1)', level: 2, show: true },
      { name: '夹杂', color: '#999999', level: 1, show: false },
    ])
  })

  it('uses the QML default defect color when dictionary rows omit color', () => {
    expect(
      buildDefectClassFilterOptions({
        data: {
          缺省颜色: { level: 1, show: true },
          空颜色: { level: 2, show: true, color: null },
        },
      }),
    ).toEqual([
      { name: '缺省颜色', color: '#FFA500', level: 1, show: true },
      { name: '空颜色', color: '#FFA500', level: 2, show: true },
    ])
  })

  it('maps defect levels to QML DefectClassProperty getColorByLevel colors', () => {
    const getQmlDefectClassLevelColor =
      requireFilterFunction<(level: unknown) => string>('getQmlDefectClassLevelColor')

    expect(getQmlDefectClassLevelColor(4)).toBe('red')
    expect(getQmlDefectClassLevelColor(3)).toBe('red')
    expect(getQmlDefectClassLevelColor('2')).toBe('yellow')
    expect(getQmlDefectClassLevelColor(1)).toBe('gray')
    expect(getQmlDefectClassLevelColor(0)).toBe('#00000000')
    expect(getQmlDefectClassLevelColor(undefined)).toBe('#00000000')
  })

  it('uses current defect types when no dictionary has been loaded', () => {
    const defects = [makeDefect(1, '压痕'), makeDefect(2, '划伤'), makeDefect(3, '压痕')]

    expect(buildDefectClassFilterOptions(undefined, defects)).toEqual([
      { name: '压痕', show: true },
      { name: '划伤', show: true },
    ])
  })

  it('adds QML area defect classes from live defects when a dictionary is loaded', () => {
    const dict = {
      data: {
        压痕: { show: true, color: '#ff0000', level: 3 },
      },
      default: {
        defectLevel: 2,
        defectColor: { r: 0, g: 128, b: 255, a: 1 },
      },
    }
    const defects = [makeDefect(1, '压痕'), makeDefect(2, '2D_边裂'), makeDefect(3, '未知缺陷')]

    expect(buildDefectClassFilterOptions(dict, defects)).toEqual([
      { name: '压痕', color: '#ff0000', level: 3, show: true },
      { name: '2D_边裂', color: 'rgba(0, 128, 255, 1)', level: 2, show: true },
    ])
  })

  it('filters defects by selected class names', () => {
    const defects = [makeDefect(1, '压痕'), makeDefect(2, '划伤'), makeDefect(3, '夹杂')]

    expect(filterDefectsByClass(defects, ['压痕', '夹杂'])).toEqual([defects[0], defects[2]])
    expect(filterDefectsByClass(defects, [])).toEqual([])
  })

  it('selects visible classes by default', () => {
    const options = [
      { name: '压痕', show: true },
      { name: '夹杂', show: false },
      { name: '划伤', show: true },
    ]

    expect(getDefaultSelectedDefectClasses(options)).toEqual(['压痕', '划伤'])
  })

  it('selects hidden alarm classes when requested', () => {
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '划伤', show: true },
    ]

    expect(getDefaultSelectedDefectClasses(options, { includeHidden: true })).toEqual(['压痕', '背景_塔形', '划伤'])
  })

  it('resets class filters to the QML dictionary show defaults', () => {
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '划伤', show: true },
    ]

    expect(getResetDefectClassSelection(options)).toEqual(['压痕', '划伤'])
  })

  it('selects all defect classes like QML showAll with include-background disabled or enabled', () => {
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '划伤', show: true },
    ]

    expect(getQmlSelectAllDefectClasses(options, { includeHidden: false })).toEqual(['压痕', '划伤'])
    expect(getQmlSelectAllDefectClasses(options, { includeHidden: true })).toEqual(['压痕', '背景_塔形', '划伤'])
  })

  it('hides background filter rows like QML when include-background is disabled', () => {
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '划伤', show: true },
    ]

    expect(getQmlVisibleFilterOptions(options, { includeHidden: false }).map((option) => option.name)).toEqual([
      '压痕',
      '划伤',
    ])
    expect(getQmlVisibleFilterOptions(options, { includeHidden: true }).map((option) => option.name)).toEqual([
      '压痕',
      '背景_塔形',
      '划伤',
    ])
  })

  it('builds QML left-list filter options with the extra no-defect item visible and unchecked', () => {
    const options = buildQmlLeftListDefectFilterOptions({
      data: {
        压痕: { show: true, color: '#ff0000', level: 3 },
        背景_塔形: { show: false, color: '#999999', level: 1 },
        划伤: { show: true, color: '#00ff00', level: 2 },
      },
    })

    expect(options.map((option) => option.name)).toEqual(['压痕', '划伤', '无缺陷'])
    expect(options[2]).toMatchObject({ name: '无缺陷', show: false, level: 0 })
    expect(getDefaultSelectedDefectClasses(options)).toEqual(['压痕', '划伤'])
  })

  it('does not treat the QML no-defect item as loaded visible defect options', () => {
    expect(hasQmlLeftListVisibleDefectOptions([{ name: '无缺陷', show: false, level: 0 }])).toBe(false)
    expect(
      hasQmlLeftListVisibleDefectOptions([
        { name: '压痕', show: true },
        { name: '无缺陷', show: false, level: 0 },
      ]),
    ).toBe(true)
  })

  it('preserves selected classes when the QML include-background toggle only changes row visibility', () => {
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '划伤', show: true },
    ]

    expect(reconcileQmlDefectClassSelection(options, ['压痕', '划伤'], { includeHidden: true })).toEqual([
      '压痕',
      '划伤',
    ])
    expect(reconcileQmlDefectClassSelection(options, ['压痕', '背景_塔形'], { includeHidden: false })).toEqual([
      '压痕',
      '背景_塔形',
    ])
    expect(reconcileQmlDefectClassSelection(options, ['已删除类别'], { includeHidden: true })).toEqual(['压痕', '划伤'])
  })

  it('preserves an intentionally empty selection when QML include-background only changes row visibility', () => {
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '划伤', show: true },
    ]

    expect(reconcileQmlDefectClassSelection(options, [], { preserveEmpty: true })).toEqual([])
  })

  it('counts defects by class name for QML-style category badges', () => {
    const defects = [makeDefect(1, '压痕'), makeDefect(2, '划伤'), makeDefect(3, '压痕')]
    const options = [
      { name: '压痕', show: true },
      { name: '夹杂', show: true },
      { name: '划伤', show: false },
    ]

    expect(countDefectsByClass(options, defects)).toEqual({
      压痕: 2,
      夹杂: 0,
      划伤: 1,
    })
  })

  it('filters DataShow defects like QML show tools', () => {
    const defects = [makeDefect(1, '压痕'), makeDefect(2, '背景_塔形'), makeDefect(3, '2D_边裂')]
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '2D_边裂', show: true },
    ]

    expect(filterDataShowDefects(defects, options)).toEqual([defects[0]])
    expect(filterDataShowDefects(defects, options, { showHidden: true })).toEqual([defects[0], defects[1]])
    expect(filterDataShowDefects(defects, options, { showArea: true })).toEqual([defects[0], defects[2]])
    expect(filterDataShowDefects(defects, options, { showHidden: true, showArea: true })).toEqual(defects)
  })

  it('uses QML DataShow configDefectName as the 2D class identity for display tools', () => {
    const getDataShowDefectClassName =
      requireFilterFunction<(defect: DefectData) => string>('getDataShowDefectClassName')
    const buildDataShowDefectClassFilterOptions =
      requireFilterFunction<(defectDict: unknown, defects: DefectData[]) => Array<{ name: string; show: boolean }>>(
        'buildDataShowDefectClassFilterOptions',
      )
    const countDataShowDefectsByClass =
      requireFilterFunction<(options: Array<{ name: string }>, defects: DefectData[]) => Record<string, number>>(
        'countDataShowDefectsByClass',
      )
    const areaDefect = {
      ...makeDefect(1, '边裂'),
      raw: {
        defectName: '边裂',
        configDefectName: '2D_边裂',
      },
    }
    const dict = {
      data: {
        压痕: { show: true, color: '#ff0000', level: 3 },
      },
      default: {
        defectLevel: 2,
        defectColor: '#00ff00',
      },
    }

    expect(getDataShowDefectClassName(areaDefect)).toBe('2D_边裂')
    const options = buildDataShowDefectClassFilterOptions(dict, [areaDefect])

    expect(options.map((option) => option.name)).toEqual(['压痕', '2D_边裂'])
    expect(countDataShowDefectsByClass(options, [areaDefect])).toMatchObject({ 压痕: 0, '2D_边裂': 1 })
    expect(filterDataShowDefects([areaDefect], options)).toEqual([])
    expect(filterDataShowDefects([areaDefect], options, { showArea: true })).toEqual([areaDefect])
    expect(
      filterDataShowDefects([areaDefect], options, {
        selectedClassNames: ['边裂'],
        showArea: true,
      }),
    ).toEqual([])
    expect(
      filterDataShowDefects([areaDefect], options, {
        selectedClassNames: ['2D_边裂'],
        showArea: true,
      }),
    ).toEqual([areaDefect])
  })

  it('filters DataShow defects by per-class selection before broad show tools', () => {
    const defects = [makeDefect(1, '压痕'), makeDefect(2, '背景_塔形'), makeDefect(3, '2D_边裂')]
    const options = [
      { name: '压痕', show: true },
      { name: '背景_塔形', show: false },
      { name: '2D_边裂', show: true },
    ]

    expect(
      filterDataShowDefects(defects, options, {
        selectedClassNames: ['压痕'],
        showArea: true,
        showHidden: true,
      }),
    ).toEqual([defects[0]])
    expect(
      filterDataShowDefects(defects, options, {
        selectedClassNames: [],
        showArea: true,
        showHidden: true,
      }),
    ).toEqual([])
    expect(
      filterDataShowDefects(defects, options, {
        selectedClassNames: ['压痕', '背景_塔形', '2D_边裂'],
        showArea: true,
        showHidden: true,
      }),
    ).toEqual(defects)
  })

  it('extracts QML left-list defect names from coil children before fallback defects', () => {
    const getQmlCoilDefectNames =
      requireFilterFunction<(coil: CoilData) => string[]>('getQmlCoilDefectNames')

    expect(
      getQmlCoilDefectNames(
        makeCoil(1, {
          childrenCoilDefect: [
            { defectName: '压痕', configDefectName: '配置压痕' },
            { DefectName: '划伤' },
            { ConfigDefectName: '夹杂' },
            { Name: '辊印' },
            { defectName: '' },
          ],
          defects: [{ defectName: '不应读取' }],
        }),
      ),
    ).toEqual(['压痕', '划伤', '夹杂', '辊印'])

    expect(
      getQmlCoilDefectNames(
        makeCoil(2, {
          childrenCoilDefect: [],
          defects: [{ defectName: '被 children 空数组遮蔽' }],
        }),
      ),
    ).toEqual([])
  })

  it('filters the QML left coil list when defect-class filtering is enabled', () => {
    const filterQmlCoilsByDefectClasses =
      requireFilterFunction<(coils: CoilData[], selectedClassNames: string[], enabled: boolean) => CoilData[]>(
        'filterQmlCoilsByDefectClasses',
      )
    const coils = [
      makeCoil(1, { childrenCoilDefect: [{ defectName: '压痕' }] }),
      makeCoil(2, { childrenCoilDefect: [{ defectName: '划伤' }] }),
      makeCoil(3, { childrenCoilDefect: [] }),
    ]

    expect(filterQmlCoilsByDefectClasses(coils, ['划伤'], true).map((coil) => coil.id)).toEqual([2])
    expect(filterQmlCoilsByDefectClasses(coils, [], true)).toEqual([])
    expect(filterQmlCoilsByDefectClasses(coils, ['划伤'], false)).toBe(coils)
  })
})
