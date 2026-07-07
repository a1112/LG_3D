export type CoilSearchRequest =
  | { kind: 'none'; text: '' }
  | { kind: 'id'; text: string; coilId: number }
  | { kind: 'coilNo'; text: string }

export type QmlTextSearchMode = 'auto' | 'coilNo' | 'coilId'
export type CoilListMode = 'realtime' | 'history'

export function resolveCoilSearch(input: string, mode: QmlTextSearchMode = 'auto'): CoilSearchRequest {
  const text = input.trim()
  if (!text) return { kind: 'none', text: '' }

  if (mode === 'coilNo') {
    return { kind: 'coilNo', text }
  }

  if (mode === 'coilId') {
    return /^\d+$/.test(text) ? { kind: 'id', text, coilId: Number(text) } : { kind: 'none', text: '' }
  }

  if (/^\d+$/.test(text)) {
    return { kind: 'id', text, coilId: Number(text) }
  }

  return { kind: 'coilNo', text }
}

export function buildQmlHistoryCoilList<T>(backendRows: T[]): T[] {
  return [...backendRows].reverse()
}

export function shouldUseCoilDetailFallback<T>(request: CoilSearchRequest, backendRows: T[]): boolean {
  return request.kind === 'id' && backendRows.length === 0
}

export function buildSearchResultsWithDetailFallback<T extends { id?: number }>(
  request: CoilSearchRequest,
  backendRows: T[],
  detailRow: T | null | undefined,
): T[] {
  if (request.kind !== 'id' || backendRows.length > 0) return backendRows
  if (!detailRow || detailRow.id !== request.coilId) return []
  return [detailRow]
}

export function selectVisibleCoilList<T>(mode: CoilListMode, realtimeRows: T[], historyRows: T[]): T[] {
  return mode === 'history' ? historyRows : realtimeRows
}
