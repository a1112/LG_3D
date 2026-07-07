export interface DeviceCurveRow {
  coil_id: number
  time: string
  location_S: unknown
  location_L: unknown
  location_laser: unknown
  median_3d_mm_S: unknown
  median_3d_mm_L: unknown
  median_3d_mm_avg: unknown
  width_: unknown
  total_length: number
  total_error: number
  distance_s_error: number
  distance_l_error: number
}

export interface DeviceCurveViewModel {
  rows: DeviceCurveRow[]
  totalLengthAvg: number
  distanceSAvg: number
  distanceLAvg: number
}

export interface DeviceCurvePoint {
  x: number
  y: number
}

export interface DeviceCurveSeries {
  key: keyof Pick<
    DeviceCurveRow,
    'location_S' | 'location_L' | 'location_laser' | 'median_3d_mm_S' | 'median_3d_mm_L' | 'width_'
  >
  label: string
  color: string
  points: DeviceCurvePoint[]
}

export interface DeviceCurveChart {
  axis: {
    minX: number
    maxX: number
    minY: number
    maxY: number
  }
  series: DeviceCurveSeries[]
}

const CHART_SERIES_DEFS: Array<Omit<DeviceCurveSeries, 'points'>> = [
  { key: 'location_S', label: 'S端位置', color: '#3ba4ff' },
  { key: 'location_L', label: 'L端位置', color: '#5ad16b' },
  { key: 'location_laser', label: '激光距离', color: '#ff9b3b' },
  { key: 'median_3d_mm_S', label: 'S端距离', color: '#ff5a5a' },
  { key: 'median_3d_mm_L', label: 'L端距离', color: '#ff6fc1' },
  { key: 'width_', label: '宽度', color: '#8bd450' },
]

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function finiteNumber(value: unknown): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : Number.NaN
}

function average(sum: number, count: number): number {
  return count > 0 ? sum / count : 0
}

export function buildDeviceCurveViewModel(items: unknown[]): DeviceCurveViewModel {
  const rows: DeviceCurveRow[] = []
  let totalSum = 0
  let totalCount = 0
  let distSSum = 0
  let distSCount = 0
  let distLSum = 0
  let distLCount = 0

  for (const item of items) {
    const record = asRecord(item)
    const widthVal = finiteNumber(record.width_)
    const distS = finiteNumber(record.median_3d_mm_S)
    const distL = finiteNumber(record.median_3d_mm_L)
    let totalLength = Number.NaN

    if (Number.isFinite(widthVal) && Number.isFinite(distS) && Number.isFinite(distL) && distS >= 100 && distL >= 100) {
      totalLength = widthVal + distS + distL
      totalSum += totalLength
      totalCount += 1
    }
    if (Number.isFinite(distS) && distS >= 100) {
      distSSum += distS
      distSCount += 1
    }
    if (Number.isFinite(distL) && distL >= 100) {
      distLSum += distL
      distLCount += 1
    }

    rows.push({
      coil_id: finiteNumber(record.coil_id),
      time: typeof record.time === 'string' ? record.time : '',
      location_S: record.location_S,
      location_L: record.location_L,
      location_laser: record.location_laser,
      median_3d_mm_S: record.median_3d_mm_S,
      median_3d_mm_L: record.median_3d_mm_L,
      median_3d_mm_avg: record.median_3d_mm_avg,
      width_: record.width_,
      total_length: totalLength,
      total_error: 0,
      distance_s_error: 0,
      distance_l_error: 0,
    })
  }

  const totalLengthAvg = average(totalSum, totalCount)
  const distanceSAvg = average(distSSum, distSCount)
  const distanceLAvg = average(distLSum, distLCount)

  return {
    totalLengthAvg,
    distanceSAvg,
    distanceLAvg,
    rows: rows.map((row) => {
      const totalLength = finiteNumber(row.total_length)
      const distS = finiteNumber(row.median_3d_mm_S)
      const distL = finiteNumber(row.median_3d_mm_L)
      return {
        ...row,
        total_error: Number.isFinite(totalLength) ? totalLength - totalLengthAvg : Number.NaN,
        distance_s_error: Number.isFinite(distS) ? distS - distanceSAvg : Number.NaN,
        distance_l_error: Number.isFinite(distL) ? distL - distanceLAvg : Number.NaN,
      }
    }),
  }
}

export function formatDeviceCurveValue(value: unknown): string {
  const numberValue = finiteNumber(value)
  return Number.isFinite(numberValue) ? numberValue.toFixed(3) : ''
}

export function buildDeviceCurveChart(rows: DeviceCurveRow[]): DeviceCurveChart {
  const series = CHART_SERIES_DEFS.map((definition) => ({
    ...definition,
    points: rows.flatMap((row) => {
      const x = finiteNumber(row.coil_id)
      const y = finiteNumber(row[definition.key])
      return Number.isFinite(x) && Number.isFinite(y) ? [{ x, y }] : []
    }),
  }))

  const allPoints = series.flatMap((item) => item.points)
  if (allPoints.length === 0) {
    return {
      axis: { minX: 0, maxX: 1, minY: 0, maxY: 1 },
      series,
    }
  }

  const xValues = allPoints.map((point) => point.x)
  const yValues = allPoints.map((point) => point.y)
  let minX = Math.min(...xValues)
  let maxX = Math.max(...xValues)
  let minY = Math.min(...yValues)
  let maxY = Math.max(...yValues)

  if (minX === maxX) {
    minX -= 1
    maxX += 1
  }
  if (minY === maxY) {
    minY -= 1
    maxY += 1
  }

  return {
    axis: { minX, maxX, minY, maxY },
    series,
  }
}
