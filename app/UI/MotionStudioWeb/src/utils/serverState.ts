export interface ServerStateRow {
  key: string
  title: string
  value: string
  message: string
  level: number
  color: 'success' | 'warning' | 'error'
}

export interface ServerStateSummary {
  label: string
  color: 'success' | 'warning' | 'error' | 'default'
  total: number
  abnormal: number
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readString(record: Record<string, unknown>, keys: string[], fallback = ''): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  }
  return fallback
}

function readLevel(record: Record<string, unknown>, fallback = 1): number {
  const value = record.level ?? record.Level ?? record.alarmLevel
  if (typeof value === 'number' && Number.isFinite(value)) return Math.trunc(value)
  if (typeof value === 'string' && Number.isFinite(Number(value))) return Math.trunc(Number(value))
  return fallback
}

function levelColor(level: number): ServerStateRow['color'] {
  if (level >= 3) return 'error'
  if (level >= 2) return 'warning'
  return 'success'
}

function sourceItems(value: unknown): Array<[string, unknown]> {
  if (Array.isArray(value)) return value.map((item, index) => [String(index), item])
  return Object.entries(asRecord(value))
}

export function buildServerStateRows(value: unknown): ServerStateRow[] {
  return sourceItems(value).map(([fallbackKey, item], index) => {
    if (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean') {
      const text = String(item)
      return {
        key: fallbackKey,
        title: `状态 ${index + 1}`,
        value: text,
        message: text,
        level: 1,
        color: 'success',
      }
    }

    const record = asRecord(item)
    const key = readString(record, ['key', 'Key', 'name'], fallbackKey)
    const title = readString(record, ['title', 'key', 'Key', 'name'], key)
    const valueText = readString(record, ['value', 'state', 'status'], '--')
    const message = readString(record, ['msg', 'message', 'detail'], valueText)
    const level = readLevel(record)

    return {
      key,
      title,
      value: valueText,
      message,
      level,
      color: levelColor(level),
    }
  })
}

export function buildServerStateSummary(value: unknown): ServerStateSummary {
  const rows = buildServerStateRows(value)
  const abnormal = rows.filter((row) => row.level >= 2).length
  if (rows.length === 0) {
    return {
      label: '暂无检测状态',
      color: 'default',
      total: 0,
      abnormal: 0,
    }
  }
  if (abnormal > 0) {
    return {
      label: `${abnormal} 项异常`,
      color: rows.some((row) => row.level >= 3) ? 'error' : 'warning',
      total: rows.length,
      abnormal,
    }
  }
  return {
    label: '检测状态正常',
    color: 'success',
    total: rows.length,
    abnormal: 0,
  }
}

export function parseServerStateWebSocketMessage(message: string): unknown {
  try {
    return JSON.parse(message)
  } catch {
    return []
  }
}

export function resolveServerStateWsUrl(
  apiBaseUrl: string,
  wsPath: string,
  origin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1',
): string {
  const normalizedPath = wsPath.startsWith('/') ? wsPath : `/${wsPath}`
  if (/^https?:\/\//.test(apiBaseUrl)) {
    const base = new URL(apiBaseUrl)
    base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    base.pathname = normalizedPath
    base.search = ''
    base.hash = ''
    return base.toString()
  }

  if (/^wss?:\/\//.test(apiBaseUrl)) {
    const base = new URL(apiBaseUrl)
    base.pathname = normalizedPath
    base.search = ''
    base.hash = ''
    return base.toString()
  }

  const url = new URL(normalizedPath, origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}
