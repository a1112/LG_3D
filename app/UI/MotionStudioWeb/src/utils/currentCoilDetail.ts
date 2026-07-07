import type { CoilData } from '@/types'

export interface DetailRow {
  key: string
  value: string
}

export interface CoilStateSections {
  S: { title: 'S端'; rows: DetailRow[] }
  L: { title: 'L端'; rows: DetailRow[] }
}

export interface CoilAlarmSection {
  title: '扁卷检测' | '塔形检测' | '松卷检测'
  level: number
  rows: DetailRow[]
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readValue(record: Record<string, unknown>, keys: string[], fallback: unknown = ''): unknown {
  for (const key of keys) {
    if (record[key] !== undefined && record[key] !== null) return record[key]
  }
  return fallback
}

function asText(value: unknown): string {
  if (value === undefined || value === null) return ''
  return String(value)
}

function fixedText(value: unknown, digits: number): string {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return ''
  return numberValue.toFixed(digits)
}

function numberValue(value: unknown, fallback = 0): number {
  const nextValue = Number(value)
  return Number.isFinite(nextValue) ? nextValue : fallback
}

function sideLabel(side: 'S' | 'L'): string {
  return `${side}端`
}

function formatMm(value: number | null | undefined): string {
  return value !== null && value !== undefined && Number.isFinite(value) ? `${value.toFixed(2)} mm` : '--'
}

function formatOneDecimal(value: unknown): string {
  return numberValue(value).toFixed(1)
}

function maybeRow(record: Record<string, unknown>, key: string, label: string): DetailRow[] {
  const value = record[key]
  if (value === undefined || value === null) return []
  return [{ key: label, value: asText(value) }]
}

function stateRows(state: Record<string, unknown>): DetailRow[] {
  return [
    { key: '标定X', value: fixedText(state.scan3dCoordinateScaleX, 4) },
    { key: '标定Y', value: fixedText(state.scan3dCoordinateScaleY, 4) },
    { key: '标定Z', value: fixedText(state.scan3dCoordinateScaleZ, 4) },
    { key: ' ', value: '' },
    { key: '下报警mm', value: fixedText(state.colorFromValue_mm, 4) },
    { key: '上报警mm', value: fixedText(state.colorToValue_mm, 4) },
    { key: '下报警int', value: asText(state.lowerLimit) },
    { key: '上报警int', value: asText(state.upperLimit) },
    { key: '报警int', value: asText(state.start) },
    { key: '报警范围int', value: asText(state.step) },
    { key: 'rotate', value: asText(state.rotate) },
    { key: 'x_rotate', value: asText(state.x_rotate) },
    { key: '3d平均', value: asText(state.median_3d) },
    { key: '3d平均mm', value: asText(state.median_3d_mm) },
    { key: '宽度px', value: asText(state.width) },
    { key: '高度px', value: asText(state.height) },
    { key: '卷像素面积', value: asText(state.mask_area) },
    { key: '卷面积', value: '' },
    { key: '下报警面积', value: asText(state.lowerArea) },
    { key: '上报警面积', value: asText(state.upperArea) },
    { key: '下报警%', value: fixedText(Number(state.lowerArea_percent) * 100, 2) },
    { key: '上报警%', value: fixedText(Number(state.upperArea_percent) * 100, 2) },
  ]
}

export function buildCurrentCoilBaseRows(coil: CoilData | null | undefined): DetailRow[] {
  if (!coil) return []

  const raw = asRecord(coil.raw)
  return [
    { key: '流水号', value: asText(coil.id) },
    { key: '卷号', value: asText(coil.coilNo) },
    { key: '钢种', value: asText(readValue(raw, ['coilType', 'CoilType'])) },
    { key: '内径', value: asText(readValue(raw, ['coilInside', 'CoilInside'])) },
    { key: '外径', value: asText(readValue(raw, ['coilDia', 'CoilDia'])) },
    { key: '厚度', value: asText(readValue(raw, ['coilThickness', 'CoilThickness', 'thickness', 'Thickness'])) },
    { key: '生产宽度', value: asText(readValue(raw, ['coilWidth', 'CoilWidth', 'width', 'Width'])) },
    { key: '实际宽度', value: asText(readValue(raw, ['coilActWidth', 'CoilActWidth', 'actWidth', 'ActWidth'])) },
    { key: '去向', value: asText(readValue(raw, ['nextInfo', 'NextInfo'])) },
  ]
}

export function buildCurrentCoilPlcRows(plcData: unknown): DetailRow[] {
  const record = asRecord(plcData)
  return [
    ...maybeRow(record, 'location_S', '设备位置_S'),
    ...maybeRow(record, 'location_L', '设备位置_L'),
    ...maybeRow(record, 'location_laser', '激光'),
  ]
}

export function buildCurrentCoilStateSections(states: unknown): CoilStateSections {
  const sections: CoilStateSections = {
    S: { title: 'S端', rows: [] },
    L: { title: 'L端', rows: [] },
  }

  if (!Array.isArray(states)) return sections

  for (const item of states) {
    const record = asRecord(item)
    const target = String(record.surface ?? '').toUpperCase() === 'S' ? 'S' : 'L'
    sections[target].rows = stateRows(record)
  }

  return sections
}

function flatRollSideDiameterMm(item: Record<string, unknown>): number | null {
  const innerWidth = numberValue(item.inner_circle_width, -1)
  const accuracyX = numberValue(item.accuracy_x, 1)
  if (innerWidth <= 0) return null
  return innerWidth * accuracyX
}

function flatRollRows(flatRoll: Record<string, unknown>): { level: number; rows: DetailRow[] } {
  const sides = (['S', 'L'] as const).map((side) => {
    const item = asRecord(flatRoll[side])
    const innerDiameterMm = flatRollSideDiameterMm(item)
    return { side, item, innerDiameterMm, hasData: Object.keys(item).length > 0 }
  })
  const diameters = sides.map((side) => side.innerDiameterMm).filter((value): value is number => value !== null)
  const averageDiameter = diameters.length > 0 ? diameters.reduce((sum, value) => sum + value, 0) / diameters.length : null
  const level = averageDiameter === null ? 0 : averageDiameter < 680 ? 2 : 1
  const rows: DetailRow[] = [{ key: '内径测量', value: formatMm(averageDiameter) }]

  for (const side of sides) {
    if (!side.hasData) {
      rows.push({ key: `${sideLabel(side.side)}数据`, value: '无数据' })
      continue
    }
    rows.push(
      { key: `${sideLabel(side.side)}内径`, value: formatMm(side.innerDiameterMm) },
      { key: `${sideLabel(side.side)}外径`, value: formatMm(numberValue(side.item.out_circle_width, 0)) },
      { key: `${sideLabel(side.side)}等级`, value: asText(numberValue(side.item.level, 0)) },
    )
  }

  return { level, rows }
}

function recordsArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(asRecord).filter((item) => Object.keys(item).length > 0) : []
}

function taperScore(item: Record<string, unknown>, keys: string[]): number {
  return keys.reduce((score, key) => Math.max(score, Math.abs(numberValue(item[key], 0))), 0)
}

function selectTaperItems(items: Record<string, unknown>[]) {
  let outItem = items[0] ?? {}
  let inItem = items[0] ?? {}
  let metaItem = items[0] ?? {}
  let outScore = -1
  let inScore = -1
  let metaScore = -1

  for (const item of items) {
    const currentOutScore = taperScore(item, ['out_taper_max_value', 'out_taper_min_value'])
    const currentInScore = taperScore(item, ['in_taper_max_value', 'in_taper_min_value'])
    const currentMetaScore = Math.max(currentOutScore, currentInScore)
    if (currentOutScore > outScore) {
      outScore = currentOutScore
      outItem = item
    }
    if (currentInScore > inScore) {
      inScore = currentInScore
      inItem = item
    }
    if (currentMetaScore > metaScore) {
      metaScore = currentMetaScore
      metaItem = item
    }
  }

  return { outItem, inItem, metaItem }
}

function taperRows(taperShape: Record<string, unknown>): { level: number; rows: DetailRow[] } {
  let outTaper = 0
  let innerTaper = 0
  let sideLevel = 0
  let hasData = false
  const rows: DetailRow[] = []

  for (const side of ['S', 'L'] as const) {
    const items = recordsArray(taperShape[side])
    if (items.length === 0) {
      rows.push({ key: `${sideLabel(side)}塔形`, value: '无数据' })
      continue
    }

    hasData = true
    const { outItem, inItem, metaItem } = selectTaperItems(items)
    outTaper = Math.max(
      outTaper,
      Math.abs(numberValue(outItem.out_taper_max_value, 0)),
      Math.abs(numberValue(outItem.out_taper_min_value, 0)),
    )
    innerTaper = Math.max(
      innerTaper,
      Math.abs(numberValue(inItem.in_taper_max_value, 0)),
      Math.abs(numberValue(inItem.in_taper_min_value, 0)),
    )
    sideLevel = Math.max(sideLevel, numberValue(metaItem.level, 0))
    rows.push(
      { key: `${sideLabel(side)}外塔形最高`, value: formatOneDecimal(outItem.out_taper_max_value) },
      { key: `${sideLabel(side)}外塔形最低`, value: formatOneDecimal(outItem.out_taper_min_value) },
      { key: `${sideLabel(side)}内塔形最高`, value: formatOneDecimal(inItem.in_taper_max_value) },
      { key: `${sideLabel(side)}内塔形最低`, value: formatOneDecimal(inItem.in_taper_min_value) },
      { key: `${sideLabel(side)}旋转角`, value: formatOneDecimal(metaItem.rotation_angle) },
    )
  }

  const computedLevel = outTaper > 75 || innerTaper > 10 ? 3 : hasData ? 1 : 0
  return { level: Math.max(sideLevel, computedLevel), rows }
}

function parseLooseDetail(data: unknown): Record<string, unknown> {
  if (typeof data !== 'string' || !data.trim()) return {}
  try {
    return asRecord(JSON.parse(data))
  } catch {
    return {}
  }
}

function looseWidthMm(item: Record<string, unknown>): number {
  const rawWidth = numberValue(item.max_width, 0)
  const detail = parseLooseDetail(item.data)
  const pixelWidth = numberValue(detail.max_width_px, 0)
  if (detail.max_width_unit === 'px') return pixelWidth > 0 ? pixelWidth : rawWidth
  if (detail.max_width_mm !== undefined && detail.max_width_mm !== null) return numberValue(detail.max_width_mm, rawWidth)
  return rawWidth
}

function looseRows(looseCoil: Record<string, unknown>): { level: number; rows: DetailRow[] } {
  let maxWidth = 0
  const rows: DetailRow[] = []

  for (const side of ['S', 'L'] as const) {
    const items = recordsArray(looseCoil[side])
    const sideMax = items.reduce((max, item) => Math.max(max, looseWidthMm(item)), 0)
    maxWidth = Math.max(maxWidth, sideMax)
    rows.push({ key: `${sideLabel(side)}最大宽度`, value: sideMax > 0 ? formatMm(sideMax) : '无数据' })
  }

  return {
    level: maxWidth > 25 ? 3 : maxWidth > 0 ? 1 : 0,
    rows: [{ key: '最大松卷宽度', value: formatMm(maxWidth > 0 ? maxWidth : null) }, ...rows],
  }
}

export function buildCurrentCoilAlarmSections(alarmData: unknown): CoilAlarmSection[] {
  const data = asRecord(alarmData)
  const flatRoll = flatRollRows(asRecord(data.FlatRoll))
  const taperShape = taperRows(asRecord(data.TaperShape))
  const looseCoil = looseRows(asRecord(data.LooseCoil))

  return [
    { title: '扁卷检测', level: flatRoll.level, rows: flatRoll.rows },
    { title: '塔形检测', level: taperShape.level, rows: taperShape.rows },
    { title: '松卷检测', level: looseCoil.level, rows: looseCoil.rows },
  ]
}
