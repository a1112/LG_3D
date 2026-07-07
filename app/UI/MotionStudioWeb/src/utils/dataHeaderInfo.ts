export interface DataHeaderInfoField {
  label: string
  value: string
}

export interface DataHeaderInfoSection {
  title: '塔形报警' | '扁卷信息'
  level: number
  fields: DataHeaderInfoField[]
}

type Side = 'S' | 'L'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function recordsArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(asRecord).filter((item) => Object.keys(item).length > 0) : []
}

function numberValue(value: unknown, fallback = 0): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function optionalNumber(value: unknown): number | null {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function fmt(value: unknown, digits = 1): string {
  const parsed = optionalNumber(value)
  return parsed === null ? '--' : parsed.toFixed(digits)
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

function buildTaperSide(taperShape: Record<string, unknown>, side: Side) {
  const items = recordsArray(taperShape[side])
  if (items.length === 0) {
    return {
      hasData: false,
      outTaper: 0,
      innerTaper: 0,
      outTaperMax: null,
      innerTaperMax: null,
      level: 0,
    }
  }

  const { outItem, inItem, metaItem } = selectTaperItems(items)
  const outMax = numberValue(outItem.out_taper_max_value, 0)
  const outMin = numberValue(outItem.out_taper_min_value, 0)
  const inMax = numberValue(inItem.in_taper_max_value, 0)
  const inMin = numberValue(inItem.in_taper_min_value, 0)

  return {
    hasData: true,
    outTaper: Math.max(Math.abs(outMax), Math.abs(outMin)),
    innerTaper: Math.max(Math.abs(inMax), Math.abs(inMin)),
    outTaperMax: outMax,
    innerTaperMax: inMax,
    level: numberValue(metaItem.level, 0),
  }
}

function buildTaperSection(data: Record<string, unknown>): DataHeaderInfoSection {
  const taperShape = asRecord(data.TaperShape)
  const s = buildTaperSide(taperShape, 'S')
  const l = buildTaperSide(taperShape, 'L')
  const taperOut = Math.max(l.outTaper, s.outTaper)
  const taperIn = Math.max(l.innerTaper, s.innerTaper)
  const qmlHeaderLevel = Math.max(taperOut > 75 ? 3 : 1, taperIn > 10 ? 3 : 1)

  return {
    title: '塔形报警',
    level: qmlHeaderLevel,
    fields: [
      { label: '外塔(mm)', value: fmt(taperOut, 1) },
      { label: '内塔(mm)', value: fmt(taperIn, 1) },
      { label: 'S端外塔', value: s.hasData ? fmt(s.outTaperMax, 1) : '--' },
      { label: 'S端内塔', value: s.hasData ? fmt(s.innerTaperMax, 1) : '--' },
      { label: 'L端外塔', value: l.hasData ? fmt(l.outTaperMax, 1) : '--' },
      { label: 'L端内塔', value: l.hasData ? fmt(l.innerTaperMax, 1) : '--' },
    ],
  }
}

function flatRollSideDiameterMm(item: Record<string, unknown>): number {
  const width = numberValue(item.inner_circle_width, 0)
  const accuracyX = numberValue(item.accuracy_x, 1)
  return width > 0 ? width * accuracyX : -1
}

function buildFlatRollSide(flatRoll: Record<string, unknown>, side: Side) {
  const rawSide = flatRoll[side]
  const hasData = rawSide !== null && typeof rawSide === 'object' && !Array.isArray(rawSide)
  const item = hasData ? asRecord(rawSide) : {}
  const innerDiameterMm = hasData ? flatRollSideDiameterMm(item) : null

  return {
    hasData,
    innerDiameterMm,
    centerX: hasData ? numberValue(item.inner_circle_center_x, 0) : null,
    centerY: hasData ? numberValue(item.inner_circle_center_y, 0) : null,
    radius: hasData ? numberValue(item.inner_circle_radius, 0) : null,
  }
}

function buildFlatRollSection(data: Record<string, unknown>): DataHeaderInfoSection {
  const flatRoll = asRecord(data.FlatRoll)
  const s = buildFlatRollSide(flatRoll, 'S')
  const l = buildFlatRollSide(flatRoll, 'L')
  const diameters = [s.innerDiameterMm, l.innerDiameterMm].filter((value): value is number => value !== null)
  const innerDiameterMm =
    diameters.length > 0 ? diameters.reduce((sum, value) => sum + value, 0) / diameters.length : null
  const level = innerDiameterMm !== null && innerDiameterMm > 0 ? (innerDiameterMm < 680 ? 2 : 1) : 0
  const centerText = (side: ReturnType<typeof buildFlatRollSide>) =>
    side.hasData ? `${fmt(side.centerX, 0)},${fmt(side.centerY, 0)}` : '--'

  return {
    title: '扁卷信息',
    level,
    fields: [
      { label: '内径(mm)', value: innerDiameterMm !== null && innerDiameterMm > 0 ? fmt(innerDiameterMm, 0) : '--' },
      { label: '等级', value: level > 0 ? String(level) : '--' },
      { label: 'S端内径', value: s.hasData ? fmt(s.innerDiameterMm, 0) : '--' },
      { label: 'L端内径', value: l.hasData ? fmt(l.innerDiameterMm, 0) : '--' },
      { label: 'S端中心', value: centerText(s) },
      { label: 'L端中心', value: centerText(l) },
      { label: 'S端旋转', value: s.hasData ? fmt(s.radius, 1) : '--' },
      { label: 'L端旋转', value: l.hasData ? fmt(l.radius, 1) : '--' },
    ],
  }
}

export function buildDataHeaderInfoSections(alarmData: unknown): DataHeaderInfoSection[] {
  const data = asRecord(alarmData)
  return [buildTaperSection(data), buildFlatRollSection(data)]
}
