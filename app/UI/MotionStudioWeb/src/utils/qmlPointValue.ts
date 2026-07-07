import type { QmlPointValueShowType } from '@/stores/uiSettingsStore'

export const DEFAULT_SCAN_3D_SCALE_Z = 0.016229506582021713
export const DEFAULT_SCAN_3D_SCALE_X = 0.33693358302116394
export const DEFAULT_SCAN_3D_SCALE_Y = 0.33693358302116394

export interface QmlPointValueFormatOptions {
  pointValueShowType?: QmlPointValueShowType
  scan3dScaleZ?: number
  scan3dScaleX?: number
  scan3dScaleY?: number
  scan3dCoordinateOffsetZ?: number
  medianZ?: number
}

export interface QmlHoverPointInfo {
  x: number
  y: number
  xMm: string
  yMm: string
  z: string
}

export interface QmlHoverPointInfoParams {
  point: {
    x: unknown
    y: unknown
  }
  rawValue: unknown
  options?: QmlPointValueFormatOptions
}

export interface QmlCrossViewZColorThresholds {
  thresholdDown?: number
  thresholdUp?: number
}

export interface QmlXyzPointSource {
  Id?: number | string | null
  id?: number | string | null
  x?: number | string | null
  y?: number | string | null
  z?: number | string | null
  z_mm?: number | string | null
  p_x?: number | string | null
  p_y?: number | string | null
  p_z?: number | string | null
  type?: string | null
  [key: string]: unknown
}

export interface QmlXyzListItem {
  id: string
  title: string
  xMm: string
  yMm: string
  zMm: string
  zColor: 'red' | 'green'
  type: string
}

export interface QmlXyzListOptions extends QmlPointValueFormatOptions, QmlCrossViewZColorThresholds {
  center?: {
    x?: unknown
    y?: unknown
  } | null
}

function numberOr(value: unknown, fallback: number): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : fallback
}

function finiteNumber(value: unknown): number | null {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function finiteRecordNumber(record: Record<string, unknown>, key: string, fallback: number): number {
  return numberOr(record[key], fallback)
}

function fixed(value: number, fractionDigits: number): string {
  return value.toFixed(fractionDigits)
}

function firstFiniteNumber(record: QmlXyzPointSource, keys: string[]): number | null {
  for (const key of keys) {
    const numberValue = finiteNumber(record[key])
    if (numberValue !== null) return numberValue
  }
  return null
}

function firstValue(record: QmlXyzPointSource, keys: string[]): unknown {
  for (const key of keys) {
    const value = record[key]
    if (value !== undefined && value !== null) return value
  }
  return undefined
}

function qmlCenteredMmText(value: number, centerValue: unknown, scaleValue: unknown, fallbackScale: number): string {
  return fixed((value - numberOr(centerValue, 0)) * numberOr(scaleValue, fallbackScale), 0)
}

function qmlXyzZText(source: QmlXyzPointSource, options: QmlXyzListOptions): string {
  const type = String(source.type ?? '')
  const zMm = firstValue(source, ['z_mm'])
  if (zMm !== undefined) return String(zMm)

  const zValue = firstValue(source, ['p_z', 'z'])
  if (type === 'user') {
    return buildQmlPointValueText(zValue, { ...options, pointValueShowType: 'mm-relative' })
  }

  const numberValue = finiteNumber(zValue)
  return numberValue === null ? '0' : String(zValue)
}

export function qmlRawToAbsoluteMm(rawValue: unknown, options: QmlPointValueFormatOptions = {}): number {
  const value = Number(rawValue)
  if (!Number.isFinite(value)) return 0

  return value * numberOr(options.scan3dScaleZ, DEFAULT_SCAN_3D_SCALE_Z) + numberOr(options.scan3dCoordinateOffsetZ, 0)
}

export function qmlRawToRelativeMm(rawValue: unknown, options: QmlPointValueFormatOptions = {}): number {
  const value = Number(rawValue)
  if (!Number.isFinite(value) || value <= 0) return 0

  return qmlRawToAbsoluteMm(value, options) - numberOr(options.medianZ, 0)
}

export function buildQmlPointValueText(rawValue: unknown, options: QmlPointValueFormatOptions = {}): string {
  if (options.pointValueShowType === 'int-raw') {
    return String(rawValue)
  }

  if (options.pointValueShowType === 'mm-absolute') {
    return fixed(qmlRawToAbsoluteMm(rawValue, options), 2)
  }

  if (Number(rawValue) < 0.01) {
    return '-inf'
  }
  return fixed(qmlRawToRelativeMm(rawValue, options), 2)
}

export function qmlXToMmText(xValue: unknown, options: QmlPointValueFormatOptions = {}): string {
  return fixed(numberOr(xValue, 0) * numberOr(options.scan3dScaleX, DEFAULT_SCAN_3D_SCALE_X), 0)
}

export function qmlYToMmText(yValue: unknown, options: QmlPointValueFormatOptions = {}): string {
  return fixed(numberOr(yValue, 0) * numberOr(options.scan3dScaleY, DEFAULT_SCAN_3D_SCALE_Y), 0)
}

export function coilInfoToQmlPointValueOptions(coilInfo: unknown): QmlPointValueFormatOptions {
  const record = coilInfo && typeof coilInfo === 'object' ? (coilInfo as Record<string, unknown>) : {}

  return {
    scan3dScaleX: finiteRecordNumber(record, 'scan3dCoordinateScaleX', DEFAULT_SCAN_3D_SCALE_X),
    scan3dScaleY: finiteRecordNumber(record, 'scan3dCoordinateScaleY', DEFAULT_SCAN_3D_SCALE_Y),
    scan3dScaleZ: finiteRecordNumber(record, 'scan3dCoordinateScaleZ', DEFAULT_SCAN_3D_SCALE_Z),
    scan3dCoordinateOffsetZ: finiteRecordNumber(record, 'scan3dCoordinateOffsetZ', 0),
    medianZ: finiteRecordNumber(record, 'median_3d_mm', 0),
  }
}

export function getQmlCrossViewZColor(
  zText: unknown,
  { thresholdDown = -100, thresholdUp = 100 }: QmlCrossViewZColorThresholds = {},
): 'red' | 'green' {
  const zValue = Number.parseInt(String(zText), 10)
  if (!Number.isFinite(zValue)) return 'green'

  return zValue < thresholdDown || zValue > thresholdUp ? 'red' : 'green'
}

export function buildQmlHoverPointInfo({
  point,
  rawValue,
  options = {},
}: QmlHoverPointInfoParams): QmlHoverPointInfo {
  const x = Math.trunc(numberOr(point.x, 0))
  const y = Math.trunc(numberOr(point.y, 0))

  return {
    x,
    y,
    xMm: qmlXToMmText(x, options),
    yMm: qmlYToMmText(y, options),
    z: buildQmlPointValueText(rawValue, options),
  }
}

export function buildQmlXyzListItems(
  points: QmlXyzPointSource[] = [],
  options: QmlXyzListOptions = {},
): QmlXyzListItem[] {
  return points.flatMap((source, index) => {
    const x = firstFiniteNumber(source, ['p_x', 'x'])
    const y = firstFiniteNumber(source, ['p_y', 'y'])
    if (x === null || y === null) return []

    const type = String(source.type ?? '')
    const zMm = qmlXyzZText(source, options)
    return [
      {
        id: String(source.Id ?? source.id ?? index),
        title: `点 ${index}`,
        xMm: qmlCenteredMmText(x, options.center?.x, options.scan3dScaleX, DEFAULT_SCAN_3D_SCALE_X),
        yMm: qmlCenteredMmText(y, options.center?.y, options.scan3dScaleY, DEFAULT_SCAN_3D_SCALE_Y),
        zMm,
        zColor: getQmlCrossViewZColor(zMm, options),
        type,
      },
    ]
  })
}
