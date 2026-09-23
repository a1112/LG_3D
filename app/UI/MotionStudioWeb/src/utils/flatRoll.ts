function detail(item: Record<string, unknown>): Record<string, unknown> {
  let value = item.data
  if (typeof value === 'string') {
    try {
      value = JSON.parse(value)
    } catch {
      return {}
    }
  }
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

export function calibratedFlatRollDiameter(item: Record<string, unknown>): number | null {
  const value = Number(detail(item).inner_diameter_mm)
  return Number.isFinite(value) && value > 0 ? value : null
}

export function calibratedFlatRollLevel(item: Record<string, unknown>): number {
  const level = Number(item.level)
  return calibratedFlatRollDiameter(item) !== null && Number.isInteger(level) && level >= 1 && level <= 5 ? level : 0
}

export function flatRollInnerAngle(item: Record<string, unknown>): unknown {
  return detail(item).inner_ellipse_angle ?? item.inner_circle_radius
}
