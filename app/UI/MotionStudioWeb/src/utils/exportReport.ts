import type { ExportXlsxConfig } from '@/services/api'
import type { CoilData } from '@/types'
import {
  openNativePath,
  type NativeFileSaveResult,
  type NativeOpenPathResult,
} from '@/utils/nativeDialogs'
import { formatQmlDateTimeMinute, getQmlCurrentDayRange } from '@/utils/qmlDateTime'

export interface ExportDateRange {
  startDate: Date
  endDate: Date
}

export interface ExportOptionState {
  detection3dInfo?: boolean
  defectInfo?: boolean
  defectShowInfo?: boolean
  defectUnShowInfo?: boolean
  exportPlcData?: boolean
}

export type QuickExportKind = 'today' | '1h' | '24h'

interface QuickExportApi {
  exportToday: () => string
  export1h: () => string
  export24h: () => string
}

export type ExportSaveResult = NativeFileSaveResult | { status: 'downloaded' }
export type ExportOpenTarget = 'file' | 'folder'
export type ExportOpenResult = 'native' | 'skipped'

interface SaveExportPayloadDeps {
  saveFile: (defaultName: string, contents: Uint8Array) => Promise<NativeFileSaveResult>
  downloadBlob: (blob: Blob, filename: string) => void
}

interface OpenSavedExportPathDeps {
  openPath?: (path: string) => Promise<NativeOpenPathResult>
}

function parseCoilDate(value: string): Date | null {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

function joinNativePath(folder: string, name: string): string {
  const trimmed = folder.trim().replace(/[\\/]+$/, '')
  if (!trimmed) return name
  const separator = trimmed.includes('\\') ? '\\' : '/'
  return `${trimmed}${separator}${name}`
}

export function resolveQuickExportUrl(kind: QuickExportKind, api: QuickExportApi): string {
  if (kind === 'today') return api.exportToday()
  if (kind === '1h') return api.export1h()
  return api.export24h()
}

export function buildQmlExportDefaultFileName(date = new Date()): string {
  return `${date.getFullYear()}_${pad(date.getMonth() + 1)}_${pad(date.getDate())} ${pad(date.getHours())}_${pad(date.getMinutes())}_${pad(date.getSeconds())}.xlsx`
}

export function buildQmlExportDefaultOutputPath(folder: string, date = new Date()): string {
  return joinNativePath(folder, buildQmlExportDefaultFileName(date))
}

export function buildQuickExportFileName(kind: QuickExportKind, baseFileName = buildQmlExportDefaultFileName()): string {
  const trimmed = baseFileName.trim() || buildQmlExportDefaultFileName()
  const suffix = `_${kind}.xlsx`
  return trimmed.includes('.xlsx') ? trimmed.replace('.xlsx', suffix) : `${trimmed}${suffix}`
}

export async function saveExportPayload(
  payload: ArrayBuffer | Uint8Array,
  filename: string,
  deps: SaveExportPayloadDeps,
): Promise<ExportSaveResult> {
  const bytes = payload instanceof Uint8Array ? payload : new Uint8Array(payload)
  const nativeResult = await deps.saveFile(filename, bytes)
  if (nativeResult.status === 'saved' || nativeResult.status === 'cancelled') {
    return nativeResult
  }

  const blobBytes = new ArrayBuffer(bytes.byteLength)
  new Uint8Array(blobBytes).set(bytes)
  deps.downloadBlob(new Blob([blobBytes]), filename)
  return { status: 'downloaded' }
}

export function resolveExportFolderPath(path: string): string {
  const trimmed = path.trim()
  const separatorIndex = Math.max(trimmed.lastIndexOf('\\'), trimmed.lastIndexOf('/'))
  if (separatorIndex < 0) return ''
  if (separatorIndex === 0) return '/'
  return trimmed.slice(0, separatorIndex)
}

export async function openSavedExportPath(
  path: string,
  target: ExportOpenTarget,
  deps: OpenSavedExportPathDeps = {},
): Promise<ExportOpenResult> {
  const targetPath = target === 'folder' ? resolveExportFolderPath(path) : path.trim()
  if (!targetPath) return 'skipped'

  const openPath = deps.openPath ?? openNativePath
  const result = await openPath(targetPath).catch(() => ({ status: 'unavailable' }) as NativeOpenPathResult)
  return result.status === 'opened' ? 'native' : 'skipped'
}

export function buildExportInitialDateRange(coilList: CoilData[], now = new Date()): ExportDateRange {
  if (coilList.length === 0) {
    const [startDate, endDate] = getQmlCurrentDayRange(now)
    return { startDate, endDate }
  }

  const firstDate = parseCoilDate(coilList[0].dateTime)
  const lastDate = parseCoilDate(coilList[coilList.length - 1].dateTime)

  if (!firstDate || !lastDate) {
    const [startDate, endDate] = getQmlCurrentDayRange(now)
    return { startDate, endDate }
  }

  return {
    startDate: lastDate,
    endDate: firstDate,
  }
}

export function buildDefaultExportXlsxConfig(
  range: ExportDateRange,
  options: ExportOptionState = {},
): ExportXlsxConfig {
  return {
    export_type: 'xlsx',
    detection_3d_info: options.detection3dInfo ?? true,
    defect_info: options.defectInfo ?? true,
    defect_show_info: options.defectShowInfo ?? true,
    defect_un_show_info: options.defectUnShowInfo ?? false,
    export_plc_data: options.exportPlcData ?? false,
    startDate: formatQmlDateTimeMinute(range.startDate),
    endDate: formatQmlDateTimeMinute(range.endDate),
  }
}
