export interface ReDetectionRange {
  fromId: number
  toId: number
}

export interface ReDetectionStatusView {
  running: boolean
  canChange: boolean
  showProgress: boolean
  progress: number
  percent: number
  total: number
  pending: number
  label: '未运行' | '运行...' | '运行完成' | '运行失败'
  color: 'default' | 'processing' | 'success' | 'error'
  error?: string
}

export interface ReDetectionWebSocketStatus {
  [key: string]: unknown
  running?: boolean
  progress?: number
  total?: number
  pending?: number
  error?: string
  __fromWebSocket?: boolean
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readNumber(record: Record<string, unknown>, key: string): number {
  const value = Number(record[key])
  return Number.isFinite(value) ? value : 0
}

function readBoolean(record: Record<string, unknown>, key: string): boolean {
  return record[key] === true
}

function normalizeId(value: unknown): number {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 0
  return Math.max(0, Math.floor(numberValue))
}

function markWebSocketStatus(record: Record<string, unknown>): ReDetectionWebSocketStatus {
  Object.defineProperty(record, '__fromWebSocket', {
    configurable: true,
    enumerable: false,
    value: true,
  })
  return record
}

export function buildReDetectionStatusView(status: unknown): ReDetectionStatusView {
  const record = asRecord(status)
  const progress = Math.max(0, Math.min(1, readNumber(record, 'progress')))
  const total = normalizeId(record.total)
  const pending = normalizeId(record.pending)
  const error = typeof record.error === 'string' && record.error.trim() ? record.error : undefined

  if (error) {
    return {
      running: false,
      canChange: false,
      showProgress: false,
      progress,
      percent: Math.round(progress * 100),
      total,
      pending,
      label: '运行失败',
      color: 'error',
      error,
    }
  }

  const explicitRunning = readBoolean(record, 'running')
  const finished = !explicitRunning && total > 0 && pending === 0
  const running = explicitRunning || (record.__fromWebSocket === true && !finished)
  return {
    running,
    canChange: !running && !finished,
    showProgress: running || finished,
    progress,
    percent: Math.round(progress * 100),
    total,
    pending,
    label: running ? '运行...' : finished ? '运行完成' : '未运行',
    color: running ? 'processing' : finished ? 'success' : 'default',
  }
}

export function normalizeReDetectionRange(range: Partial<ReDetectionRange>, fallbackId = 0): ReDetectionRange {
  const fallback = normalizeId(fallbackId)
  let fromId = normalizeId(range.fromId) || fallback
  let toId = normalizeId(range.toId) || fromId

  if (fromId > toId) {
    ;[fromId, toId] = [toId, fromId]
  }

  return { fromId, toId }
}

export function buildCoilListReDetectionRange(coils: Array<{ id?: number }>): ReDetectionRange {
  const ids = coils.map((coil) => normalizeId(coil.id)).filter((id) => id > 0)
  if (ids.length === 0) return { fromId: 0, toId: 0 }
  return {
    fromId: Math.min(...ids),
    toId: Math.max(...ids),
  }
}

export function parseReDetectionWebSocketMessage(message: string): ReDetectionWebSocketStatus {
  try {
    const parsed = JSON.parse(message)
    return markWebSocketStatus({ ...asRecord(parsed) })
  } catch {
    return markWebSocketStatus({ running: true, progress: 0, total: 0, pending: 0 })
  }
}

export function buildReDetectionWebSocketStartMessage(range: ReDetectionRange, folder?: string): string {
  const payload: Record<string, unknown> = {
    from_id: normalizeId(range.fromId),
    to_id: normalizeId(range.toId),
  }
  const trimmedFolder = folder?.trim()
  if (trimmedFolder) {
    payload.folder = trimmedFolder
  }
  return JSON.stringify(payload)
}

export function resolveReDetectionWsUrl(
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
