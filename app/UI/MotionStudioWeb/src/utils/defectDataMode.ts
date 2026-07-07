import type { ApiResponse, CoilData, DefectData, SurfaceKey } from '@/types'

export type DefectDataMode = 'auto' | 'range' | 'all' | 'manual'

export interface DefectListRange {
  startId: number
  endId: number
}

export const DEFECT_DATA_MODE_OPTIONS: Array<{ value: DefectDataMode; label: string }> = [
  { value: 'auto', label: '自动' },
  { value: 'range', label: '当前列表' },
  { value: 'all', label: '自动+手动' },
  { value: 'manual', label: '手动' },
]

export interface DefectDataApi {
  getDefects: (coilId: number, direction: string) => Promise<ApiResponse<DefectData[]>>
  getDefectAll: (startCoilId: number, endCoilId: number) => Promise<ApiResponse<DefectData[]>>
  getDefectsAll: (coilId: number, direction: string) => Promise<ApiResponse<DefectData[]>>
  getManualDefects: (coilId: number, direction: string) => Promise<ApiResponse<DefectData[]>>
}

export function buildDefectDataQueryKey(
  mode: DefectDataMode,
  coilId: number | undefined,
  surfaceKey: SurfaceKey,
  range?: DefectListRange,
): Array<string | number | undefined> {
  if (mode === 'range') {
    return ['defects', mode, range?.startId, range?.endId]
  }
  return ['defects', mode, coilId, surfaceKey]
}

export function getDefectListRange(coils: CoilData[]): DefectListRange {
  if (coils.length === 0) return { startId: 0, endId: 0 }

  const firstId = coils[0].id
  const lastId = coils[coils.length - 1].id
  return {
    startId: Math.min(firstId, lastId),
    endId: Math.max(firstId, lastId),
  }
}

export function fetchDefectsByMode(
  mode: DefectDataMode,
  api: DefectDataApi,
  coilId: number,
  surfaceKey: SurfaceKey,
  range?: DefectListRange,
): Promise<ApiResponse<DefectData[]>> {
  if (mode === 'range') {
    if (!range?.startId || !range.endId) return Promise.resolve({ code: 0, data: [], count: 0 })
    return api.getDefectAll(range.startId, range.endId)
  }
  if (mode === 'manual') return api.getManualDefects(coilId, surfaceKey)
  return mode === 'all' ? api.getDefectsAll(coilId, surfaceKey) : api.getDefects(coilId, surfaceKey)
}
