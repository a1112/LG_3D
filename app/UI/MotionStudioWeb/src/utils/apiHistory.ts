import { openNativePath, type NativeOpenPathResult } from './nativeDialogs'

export interface ApiRequestHistoryEntry {
  id: string
  method: string
  url: string
  timestamp: number
}

interface RecordApiRequestInput {
  method?: string
  url?: string
  timestamp?: number
}

export type ApiHistoryExternalOpenResult = 'native' | 'browser' | 'skipped'

interface ApiHistoryExternalOpenDependencies {
  openNative?: (url: string) => Promise<NativeOpenPathResult>
  openWindow?: (url: string, target?: string, features?: string) => unknown
}

const MAX_HISTORY_SIZE = 200
let apiRequestHistory: ApiRequestHistoryEntry[] = []
const listeners = new Set<() => void>()

function notifyListeners() {
  listeners.forEach((listener) => listener())
}

export function recordApiRequest({ method = 'GET', url = '', timestamp = Date.now() }: RecordApiRequestInput): void {
  const normalizedMethod = method.toUpperCase()
  const normalizedUrl = url || '/'
  const entry: ApiRequestHistoryEntry = {
    id: `${timestamp}-${method}-${normalizedUrl}`,
    method: normalizedMethod,
    url: normalizedUrl,
    timestamp,
  }
  apiRequestHistory = [entry, ...apiRequestHistory].slice(0, MAX_HISTORY_SIZE)
  notifyListeners()
}

export function getApiRequestHistory(): ApiRequestHistoryEntry[] {
  return apiRequestHistory
}

export function clearApiRequestHistory(): void {
  apiRequestHistory = []
  notifyListeners()
}

export function subscribeApiRequestHistory(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export async function openApiHistoryExternalUrl(
  url: string,
  deps: ApiHistoryExternalOpenDependencies = {},
): Promise<ApiHistoryExternalOpenResult> {
  const trimmed = url.trim()
  if (!trimmed) return 'skipped'

  const openNative = deps.openNative ?? openNativePath
  const nativeResult = await openNative(trimmed).catch(() => ({ status: 'unavailable' }) as NativeOpenPathResult)
  if (nativeResult.status === 'opened') return 'native'

  const openWindow = deps.openWindow ?? (typeof window !== 'undefined' ? window.open.bind(window) : undefined)
  if (!openWindow) return 'skipped'

  openWindow(trimmed, '_blank', 'noopener,noreferrer')
  return 'browser'
}
