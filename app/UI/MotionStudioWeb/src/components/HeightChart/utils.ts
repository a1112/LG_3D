import type { HeightLineSegment, HeightPointTuple } from '@/types'
import { DEFAULT_SCAN_3D_SCALE_X, DEFAULT_SCAN_3D_SCALE_Z } from '@/utils/qmlPointValue'

export interface QmlHeightChartPoint {
  sampleKey: string
  segmentIndex: number
  pointIndex: number
  distanceMm: number
  heightMm: number
  rawZ: number
}

export interface QmlHeightChartCenter {
  x: number
  y: number
}

export interface QmlHeightChartOptions {
  innerCircleCenter?: QmlHeightChartCenter | null
  scan3dScaleX?: number | null
  scan3dScaleZ?: number | null
  scan3dCoordinateOffsetZ?: number | null
}

export interface QmlHeightChartReferenceOptions {
  medianZ?: number | null
  warningThresholdUp?: number | null
  warningThresholdDown?: number | null
}

export interface QmlHeightChartReferenceLines {
  median: number | null
  upper: number | null
  lower: number | null
}

export interface QmlHeightChartZDomainOptions {
  offsetZ?: number | null
  tickSizeZ?: number | null
  tickCountZ?: number | null
  dragOffsetZ?: number | null
}

export interface QmlHeightChartZDomain {
  minZ: number
  maxZ: number
  safeTickSizeZ: number
  safeOffsetZ: number
  safeDragOffsetZ: number
}

export interface QmlHeightChartDragOffsetOptions {
  startY: number
  currentY: number
  drawWidth?: number | null
  tickSizeZ?: number | null
  tickCountZ?: number | null
}

export interface QmlHeightChartHoverOverlayOptions {
  chartData: QmlHeightChartPoint[]
  pointerX?: number | null
  chartWidth?: number | null
  drawHeight?: number | null
  zDomain: QmlHeightChartZDomain
  medianZ?: number | null
}

export interface QmlHeightChartHoverOverlay {
  x: number
  y: number
  verticalHeight: number
  horizontalX: number
  horizontalWidth: number
  distanceLabel: string
  valueLabel: string
}

export const QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z = 12
export const QML_HEIGHT_CHART_PLOT_LEFT = 5
export const QML_HEIGHT_CHART_RIGHT_GUTTER = 35

function finiteNumber(value: unknown): number | null {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function numberOr(value: unknown, fallback: number): number {
  return finiteNumber(value) ?? fallback
}

function roundChartNumber(value: number): number {
  return Math.round(value * 1000) / 1000
}

function recordValue(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value) as unknown
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : null
    } catch {
      return null
    }
  }

  return null
}

function pointFromTupleOrObject(value: unknown): QmlHeightChartCenter | null {
  if (Array.isArray(value)) {
    const x = finiteNumber(value[0])
    const y = finiteNumber(value[1])
    return x == null || y == null ? null : { x, y }
  }

  const record = recordValue(value)
  if (!record) return null

  const x = finiteNumber(record.x ?? record['0'])
  const y = finiteNumber(record.y ?? record['1'])
  return x == null || y == null ? null : { x, y }
}

function isQmlChartFiltered(values: number[], index: number, lookBehind = 5, threshold = 300): boolean {
  for (let previousOffset = 1; previousOffset < lookBehind; previousOffset += 1) {
    if (index - previousOffset < 0) continue
    if (Math.abs(values[index] - values[index - previousOffset]) > threshold) {
      return true
    }
  }

  return false
}

export function normalizeQmlHeightChartInnerCircleCenter(source: unknown): QmlHeightChartCenter | null {
  const record = recordValue(source)
  if (!record) return null

  const circleConfig = recordValue(record.circleConfig)
  const innerCircle = recordValue(circleConfig?.inner_circle) ?? recordValue(record.inner_circle)
  const circlexCenter = pointFromTupleOrObject(innerCircle?.circlex)
  if (circlexCenter) return circlexCenter

  const flatCenter = pointFromTupleOrObject({
    x: record.inner_circle_center_x ?? innerCircle?.inner_circle_center_x,
    y: record.inner_circle_center_y ?? innerCircle?.inner_circle_center_y,
  })
  if (flatCenter) return flatCenter

  const ellipse = Array.isArray(innerCircle?.ellipse) ? innerCircle?.ellipse : record.inner_ellipse
  return Array.isArray(ellipse) ? pointFromTupleOrObject(ellipse[0]) : null
}

export function qmlRawZToAbsoluteMm(rawZ: unknown, options: QmlHeightChartOptions = {}): number {
  const rawValue = numberOr(rawZ, 0)
  const scan3dScaleZ = numberOr(options.scan3dScaleZ, DEFAULT_SCAN_3D_SCALE_Z)
  const scan3dCoordinateOffsetZ = numberOr(options.scan3dCoordinateOffsetZ, 0)
  return roundChartNumber(rawValue * scan3dScaleZ + scan3dCoordinateOffsetZ)
}

export function qmlHeightChartDistanceMm(
  [x, y]: HeightPointTuple,
  options: QmlHeightChartOptions = {},
): number {
  const center = options.innerCircleCenter ?? { x: 0, y: 0 }
  const scan3dScaleX = numberOr(options.scan3dScaleX, DEFAULT_SCAN_3D_SCALE_X)
  const direction = x < center.x ? -1 : 1
  const distancePx = Math.sqrt((x - center.x) ** 2 + (y - center.y) ** 2)
  return roundChartNumber(distancePx * scan3dScaleX * direction)
}

export function buildQmlHeightChartData(
  data: HeightLineSegment[] | undefined,
  options: QmlHeightChartOptions = {},
): QmlHeightChartPoint[] {
  if (!data || data.length === 0) return []

  return data.flatMap((segment, segmentIndex) => {
    const points = segment.points ?? []
    if (points.length === 0) return []

    const heightValues = points.map((point) => qmlRawZToAbsoluteMm(point[2], options))
    return points.flatMap((point, pointIndex) => {
      const isEdgePoint = pointIndex === 0 || pointIndex === points.length - 1
      if (!isEdgePoint && isQmlChartFiltered(heightValues, pointIndex)) return []

      return [
        {
          sampleKey: `${segmentIndex + 1}-${pointIndex + 1}`,
          segmentIndex,
          pointIndex,
          distanceMm: qmlHeightChartDistanceMm(point, options),
          heightMm: heightValues[pointIndex],
          rawZ: numberOr(point[2], 0),
        },
      ]
    })
  })
}

export function buildQmlHeightChartReferenceLines({
  medianZ,
  warningThresholdUp,
  warningThresholdDown,
}: QmlHeightChartReferenceOptions): QmlHeightChartReferenceLines {
  const median = finiteNumber(medianZ)
  if (median == null) {
    return { median: null, upper: null, lower: null }
  }

  const up = finiteNumber(warningThresholdUp)
  const down = finiteNumber(warningThresholdDown)
  return {
    median,
    upper: up == null ? null : roundChartNumber(median + up),
    lower: down == null ? null : roundChartNumber(median + down),
  }
}

export function buildQmlHeightChartZDomain({
  offsetZ,
  tickSizeZ,
  tickCountZ,
  dragOffsetZ,
}: QmlHeightChartZDomainOptions): QmlHeightChartZDomain {
  const tickSizeValue = finiteNumber(tickSizeZ)
  const safeTickSizeZ =
    tickSizeValue == null || tickSizeValue <= 0 ? QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z : tickSizeValue
  const safeTickCountZ = Math.max(1, Math.floor(numberOr(tickCountZ, 1)))
  const safeOffsetZ = numberOr(offsetZ, 0)
  const safeDragOffsetZ = numberOr(dragOffsetZ, 0)
  const halfRangeZ = (safeTickSizeZ * safeTickCountZ) / 2

  return {
    minZ: roundChartNumber(safeOffsetZ - halfRangeZ + safeDragOffsetZ),
    maxZ: roundChartNumber(safeOffsetZ + halfRangeZ + safeDragOffsetZ),
    safeTickSizeZ: roundChartNumber(safeTickSizeZ),
    safeOffsetZ: roundChartNumber(safeOffsetZ),
    safeDragOffsetZ: roundChartNumber(safeDragOffsetZ),
  }
}

export function buildQmlHeightChartDragOffset({
  startY,
  currentY,
  drawWidth,
  tickSizeZ,
  tickCountZ,
}: QmlHeightChartDragOffsetOptions): number {
  const safeDrawWidth = finiteNumber(drawWidth)
  if (safeDrawWidth == null || safeDrawWidth <= 0) return 0

  const tickSizeValue = finiteNumber(tickSizeZ)
  const safeTickSizeZ =
    tickSizeValue == null || tickSizeValue <= 0 ? QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z : tickSizeValue
  const safeTickCountZ = Math.max(1, Math.floor(numberOr(tickCountZ, 1)))
  return roundChartNumber((currentY - startY) * ((safeTickSizeZ * safeTickCountZ) / safeDrawWidth))
}

export function nextQmlHeightChartTickSize(currentTickSize: unknown, angleDeltaY: number): number {
  const safeCurrent = numberOr(currentTickSize, QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z)
  return roundChartNumber(angleDeltaY > 0 ? safeCurrent - 0.5 : safeCurrent + 0.5)
}

export function buildQmlHeightChartHoverOverlay({
  chartData,
  pointerX,
  chartWidth,
  drawHeight,
  zDomain,
  medianZ,
}: QmlHeightChartHoverOverlayOptions): QmlHeightChartHoverOverlay | null {
  if (chartData.length === 0) return null

  const pointer = finiteNumber(pointerX)
  const safeChartWidth = finiteNumber(chartWidth)
  const safeDrawHeight = finiteNumber(drawHeight)
  if (pointer == null || safeChartWidth == null || safeChartWidth <= 0 || safeDrawHeight == null) return null

  const horizontalX = QML_HEIGHT_CHART_PLOT_LEFT
  const horizontalWidth = Math.max(safeChartWidth - QML_HEIGHT_CHART_RIGHT_GUTTER, 1)
  const clampedX = Math.min(Math.max(pointer, horizontalX), horizontalX + horizontalWidth)
  const distanceValues = chartData.map((point) => point.distanceMm)
  const left = Math.min(...distanceValues)
  const right = Math.max(...distanceValues, left + 1)
  const distanceRange = Math.max(right - left, 1)
  const hoverDistance = left + ((clampedX - horizontalX) / horizontalWidth) * distanceRange
  const nearestPoint = chartData.reduce((closest, point) =>
    Math.abs(point.distanceMm - hoverDistance) < Math.abs(closest.distanceMm - hoverDistance) ? point : closest,
  )
  const zRange = Math.max(zDomain.maxZ - zDomain.minZ, 1)
  const y = safeDrawHeight - ((nearestPoint.heightMm - zDomain.minZ) / zRange) * safeDrawHeight
  const median = numberOr(medianZ, 0)
  const rawZ = Math.trunc(numberOr(nearestPoint.rawZ, 0))
  const relZ = nearestPoint.heightMm - median

  return {
    x: roundChartNumber(clampedX),
    y: roundChartNumber(y),
    verticalHeight: roundChartNumber(Math.max(safeDrawHeight, 1)),
    horizontalX,
    horizontalWidth: roundChartNumber(horizontalWidth),
    distanceLabel: hoverDistance.toFixed(1),
    valueLabel: `raw ${rawZ} | rel ${relZ.toFixed(2)} | abs ${nearestPoint.heightMm.toFixed(2)}`,
  }
}
