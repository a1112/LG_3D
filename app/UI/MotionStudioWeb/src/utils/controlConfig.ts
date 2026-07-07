export interface ControlConfigRow {
  key: string
  value: string
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

export function formatControlConfigValue(value: unknown): string {
  if (value === undefined || value === null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value)
}

export function buildControlConfigRows(config: unknown): ControlConfigRow[] {
  if (!isPlainRecord(config)) return []

  const rows: ControlConfigRow[] = []
  const visit = (prefix: string, record: Record<string, unknown>) => {
    for (const key of Object.keys(record).sort()) {
      const value = record[key]
      const rowKey = prefix ? `${prefix}.${key}` : key
      if (isPlainRecord(value)) {
        visit(rowKey, value)
      } else {
        rows.push({ key: rowKey, value: formatControlConfigValue(value) })
      }
    }
  }

  visit('', config)
  return rows
}
