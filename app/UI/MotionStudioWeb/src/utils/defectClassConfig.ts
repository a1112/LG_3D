export interface DefectClassConfigRow {
  name: string
  level: number
  show: boolean
  color: string
  original?: DictRecord
}

export type DefectClassConfigPayload = Record<string, DictRecord & { level: string; show: string; color: string }>

type DictRecord = Record<string, unknown>

function asRecord(value: unknown): DictRecord {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as DictRecord) : {}
}

function dictionaryData(defectDict: unknown): DictRecord {
  const record = asRecord(defectDict)
  return asRecord('data' in record ? record.data : defectDict)
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') return value.toLowerCase() === 'true'
  return fallback
}

function readLevel(value: unknown): number {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? Math.min(Math.max(Math.trunc(numericValue), 0), 5) : 0
}

function colorChannelToHex(value: unknown, useUnitScale: boolean): string | null {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return null
  const scaledValue = useUnitScale ? numericValue * 255 : numericValue
  const clampedValue = Math.min(Math.max(Math.round(scaledValue), 0), 255)
  return clampedValue.toString(16).padStart(2, '0')
}

function readColor(value: unknown): string {
  if (typeof value === 'string' && value.trim().length > 0) return value

  const record = asRecord(value)
  if ('r' in record && 'g' in record && 'b' in record) {
    const channels = [Number(record.r), Number(record.g), Number(record.b)]
    const useUnitScale = channels.every((channel) => Number.isFinite(channel) && channel >= 0 && channel <= 1)
    const red = colorChannelToHex(record.r, useUnitScale)
    const green = colorChannelToHex(record.g, useUnitScale)
    const blue = colorChannelToHex(record.b, useUnitScale)
    if (red && green && blue) return `#${red}${green}${blue}`
  }

  if ('color' in record) return readColor(record.color)
  if ('defectColor' in record) return readColor(record.defectColor)

  return '#FFA500'
}

const COLOR_PICKER_NAMED_COLORS: Record<string, string> = {
  black: '#000000',
  blue: '#0000ff',
  gray: '#808080',
  grey: '#808080',
  green: '#008000',
  orange: '#ffa500',
  red: '#ff0000',
  white: '#ffffff',
  yellow: '#ffff00',
}

export function getDefectClassColorPickerValue(color: string): string {
  const trimmedColor = color.trim()
  if (/^#[0-9a-fA-F]{6}$/.test(trimmedColor)) return trimmedColor
  if (/^#[0-9a-fA-F]{3}$/.test(trimmedColor)) {
    const [, red, green, blue] = trimmedColor
    return `#${red}${red}${green}${green}${blue}${blue}`.toLowerCase()
  }
  return COLOR_PICKER_NAMED_COLORS[trimmedColor.toLowerCase()] ?? '#ffffff'
}

export function buildDefectClassConfigRows(defectDict: unknown): DefectClassConfigRow[] {
  const rows = Object.entries(dictionaryData(defectDict)).map(([name, value]) => {
    const record = asRecord(value)
    const row: DefectClassConfigRow = {
      name,
      level: readLevel(record.level),
      show: readBoolean(record.show, true),
      color: readColor(record.color),
    }
    Object.defineProperty(row, 'original', {
      enumerable: false,
      value: { ...record },
    })
    return row
  })

  return [...rows.filter((row) => row.show), ...rows.filter((row) => !row.show)]
}

export function updateDefectClassConfigRow(
  row: DefectClassConfigRow,
  patch: Partial<DefectClassConfigRow>,
): DefectClassConfigRow {
  const nextRow: DefectClassConfigRow = { ...row, ...patch }
  Object.defineProperty(nextRow, 'original', {
    enumerable: false,
    value: row.original,
  })
  return nextRow
}

export function buildDefectClassConfigPayload(rows: DefectClassConfigRow[]): DefectClassConfigPayload {
  return Object.fromEntries(
    rows
      .filter((row) => row.name.trim().length > 0)
      .map((row) => [
        row.name,
        {
          ...(row.original ?? {}),
          level: String(readLevel(row.level)),
          show: String(row.show),
          color: readColor(row.color),
        },
      ]),
  )
}
