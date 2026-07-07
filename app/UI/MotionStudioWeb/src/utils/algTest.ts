import type { Alg2dTestPayload } from '@/services/api'

export interface AlgTestModel {
  name: string
  type: string
  displayName: string
}

export interface AlgTestRunOptions {
  classify_save?: boolean
  save_label?: boolean
  prioritize?: boolean
}

export interface AlgProgressSummary {
  normal: number
  abnormal: number
  skipped: number
  empty: number
}

export interface AlgTestFormState {
  model: AlgTestModel | null
  targetFolder: string
  outputFolder: string
  threshold: number
  mode: 'copy' | 'move'
  classifySave: boolean
  saveLabel: boolean
  prioritize?: boolean
}

export interface AlgProgressMessage {
  taskId?: string
  speed?: number
  done?: number
  total?: number
  eta?: number
  message?: string
  status?: string
  options?: AlgTestRunOptions
  summary?: Partial<AlgProgressSummary>
  errors?: number
  finished?: boolean
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function readNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) return Number(value)
  return fallback
}

function readBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined
}

function normalizeAlgProgressOptions(value: unknown): AlgTestRunOptions | undefined {
  const record = asRecord(value)
  if (!Object.keys(record).length) return undefined

  const options: AlgTestRunOptions = {}
  const classifySave = readBoolean(record.classify_save)
  if (classifySave !== undefined) options.classify_save = classifySave
  const saveLabel = readBoolean(record.save_label)
  if (saveLabel !== undefined) options.save_label = saveLabel
  const prioritize = readBoolean(record.prioritize)
  if (prioritize !== undefined) options.prioritize = prioritize

  return Object.keys(options).length > 0 ? options : undefined
}

function normalizeAlgProgressSummary(value: unknown): Partial<AlgProgressSummary> | undefined {
  const record = asRecord(value)
  const hasKnownField = ['normal', 'abnormal', 'skipped', 'empty'].some(
    (field) => Object.prototype.hasOwnProperty.call(record, field),
  )
  if (!hasKnownField) return undefined

  const summary: Partial<AlgProgressSummary> = {}
  if (Object.prototype.hasOwnProperty.call(record, 'normal')) summary.normal = readNumber(record.normal)
  if (Object.prototype.hasOwnProperty.call(record, 'abnormal')) summary.abnormal = readNumber(record.abnormal)
  if (Object.prototype.hasOwnProperty.call(record, 'skipped')) summary.skipped = readNumber(record.skipped)
  if (Object.prototype.hasOwnProperty.call(record, 'empty')) summary.empty = readNumber(record.empty)
  return summary
}

export function clampAlgThreshold(value: number): number {
  if (!Number.isFinite(value)) return 0.4
  return Math.max(0.01, Math.min(0.99, value))
}

export function normalizeAlgModels(response: unknown): AlgTestModel[] {
  const record = asRecord(response)
  const models = Array.isArray(record.models) ? record.models : Array.isArray(response) ? response : []

  return models
    .map((item) => {
      const model = asRecord(item)
      const name = String(model.name ?? '').trim()
      if (!name) return null
      const type = String(model.type ?? 'detector')
      const displayName = String(model.display_name ?? model.displayName ?? name)
      return { name, type, displayName }
    })
    .filter((item): item is AlgTestModel => item !== null)
}

export function buildAlgTestPayload(state: AlgTestFormState): Alg2dTestPayload {
  if (!state.model) {
    throw new Error('请选择模型')
  }

  const isClassifier = state.model.type === 'classifier'
  return {
    model: state.model.name,
    target: state.targetFolder.trim(),
    output: state.outputFolder.trim(),
    threshold: clampAlgThreshold(state.threshold),
    mode: state.mode,
    options: {
      classify_save: state.classifySave,
      save_label: isClassifier ? false : state.saveLabel,
      ...(state.prioritize ? { prioritize: true } : {}),
    },
  }
}

export function normalizeAlgProgressMessage(message: string): AlgProgressMessage {
  let parsed: unknown
  try {
    parsed = JSON.parse(message)
  } catch {
    parsed = { message }
  }

  const record = asRecord(parsed)
  const result: AlgProgressMessage = {}
  if (record.task_id !== undefined) result.taskId = String(record.task_id)
  if (record.speed !== undefined) result.speed = readNumber(record.speed)
  if (record.done !== undefined) result.done = readNumber(record.done)
  if (record.total !== undefined) result.total = readNumber(record.total)
  if (record.eta !== undefined) result.eta = readNumber(record.eta)
  if (record.message !== undefined) result.message = String(record.message)
  if (record.status !== undefined) result.status = String(record.status)
  const options = normalizeAlgProgressOptions(record.options)
  if (options !== undefined) result.options = options
  const summary = normalizeAlgProgressSummary(record.summary)
  if (summary !== undefined) result.summary = summary
  if (record.errors !== undefined) result.errors = readNumber(record.errors)
  if (record.finished !== undefined) result.finished = Boolean(record.finished)
  return result
}

export function formatAlgEta(seconds: number): string {
  if (!seconds || seconds <= 0) return '计算中'
  if (seconds >= 3600) {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${hours}小时${minutes}分`
  }
  if (seconds >= 60) {
    const minutes = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${minutes}分${secs}秒`
  }
  return `${Math.floor(seconds)}秒`
}

export function formatAlgTestFailureLog(prefix: string, error: unknown): string {
  const message =
    error instanceof Error
      ? error.message
      : typeof error === 'string'
        ? error
        : ''
  const detail = message.trim()
  return detail ? `${prefix}: ${detail}` : prefix
}

export function formatAlgProgressSocketErrorLog(error: unknown): string {
  const record = asRecord(error)
  const detail = String(record.message ?? record.reason ?? '').trim()
  return detail ? `进度连接错误: ${detail}` : '进度连接错误'
}

export function resolveAlgProgressWsUrl(
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
