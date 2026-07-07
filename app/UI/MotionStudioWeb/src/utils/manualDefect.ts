import type { DefectData } from '@/types'

export type ManualDefectExportScope = 'all' | 'manual' | 'selected'

export interface ManualDefectFormValues {
  defectName: string
  defectX: number
  defectY: number
  defectW: number
  defectH: number
  remark?: string
}

export interface ManualDefectExportOptions {
  groupByCategory?: boolean
  includeInfo?: boolean
  highQuality?: boolean
}

export interface ManualDefectExportCounts {
  total: number
  manual: number
  selected: number
}

export interface ManualDefectExportResult {
  exported?: number
  total?: number
  categories?: number
}

export interface ManualDefectAddPayloadParams {
  coilId: number
  surfaceKey: string
  rect: {
    x: number
    y: number
    width: number
    height: number
  }
  defectName: string
  remark?: string
}

function rawRecord(defect: DefectData | null): Record<string, unknown> {
  return defect?.raw && typeof defect.raw === 'object' ? defect.raw : {}
}

function isFinitePositive(value: number, fallback: number): number {
  return Number.isFinite(value) && value > 0 ? Math.trunc(value) : fallback
}

function isFiniteNonNegative(value: number, fallback: number): number {
  return Number.isFinite(value) && value >= 0 ? Math.trunc(value) : fallback
}

function isQmlTruthyNumber(value: unknown, fallback: number): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) && numberValue !== 0 ? Math.trunc(numberValue) : fallback
}

function readQmlTruthyNumber(values: unknown[], fallback: number): number {
  for (const value of values) {
    const numberValue = Number(value)
    if (Number.isFinite(numberValue) && numberValue !== 0) return Math.trunc(numberValue)
  }

  return fallback
}

function isQmlTruthyString(value: unknown, fallback: string): string {
  if (value === undefined || value === null || value === '') return fallback
  return String(value)
}

function readRawString(record: Record<string, unknown>, key: string, fallback = ''): string {
  const value = record[key]
  if (value === undefined || value === null) return fallback
  return String(value)
}

export function canEditManualDefect(defect: DefectData | null): boolean {
  if (!defect) return false

  return (rawRecord(defect).type || 'manual') === 'manual'
}

export function buildManualDefectUpdatePayload(values: ManualDefectFormValues): ManualDefectFormValues {
  return {
    defectName: values.defectName.trim() || '未知缺陷',
    defectX: isFiniteNonNegative(values.defectX, 0),
    defectY: isFiniteNonNegative(values.defectY, 0),
    defectW: isFinitePositive(values.defectW, 100),
    defectH: isFinitePositive(values.defectH, 100),
    remark: values.remark ?? '',
  }
}

export function buildManualDefectAddPayload({
  coilId,
  surfaceKey,
  rect,
  defectName,
  remark,
}: ManualDefectAddPayloadParams): Record<string, unknown> {
  return {
    secondaryCoilId: coilId,
    surface: surfaceKey,
    defectName: defectName.trim() || '未知缺陷',
    defectX: Math.round(rect.x),
    defectY: Math.round(rect.y),
    defectW: Math.round(rect.width),
    defectH: Math.round(rect.height),
    remark: remark ?? '',
    annotator: '系统用户',
  }
}

export function getManualDefectFormValues(defect: DefectData): ManualDefectFormValues {
  const raw = rawRecord(defect)
  return {
    defectName: readRawString(raw, 'defectName', defect.defectType),
    defectX: Number(raw.defectX ?? defect.position.x),
    defectY: Number(raw.defectY ?? defect.position.y),
    defectW: Number(raw.defectW ?? defect.size.width),
    defectH: Number(raw.defectH ?? defect.size.height),
    remark: readRawString(raw, 'remark'),
  }
}

export function getExportableDefects(defects: DefectData[], scope: ManualDefectExportScope): DefectData[] {
  if (scope === 'manual') return defects.filter((defect) => rawRecord(defect).type === 'manual')
  if (scope === 'selected') return defects.filter((defect) => rawRecord(defect).selected === true)
  return defects
}

export function getManualDefectExportCounts(defects: DefectData[]): ManualDefectExportCounts {
  return {
    total: defects.length,
    manual: defects.filter((defect) => rawRecord(defect).type === 'manual').length,
    selected: defects.filter((defect) => rawRecord(defect).selected === true).length,
  }
}

export function defectToPythonPayload(defect: DefectData): Record<string, unknown> {
  const raw = rawRecord(defect)
  return {
    secondaryCoilId: readQmlTruthyNumber([raw.secondaryCoilId, raw.Id, defect.coilId, defect.id], 0),
    surface: isQmlTruthyString(raw.surface ?? defect.surface, 'S'),
    defectName: isQmlTruthyString(raw.defectName ?? defect.defectType, 'Unknown'),
    defectX: isQmlTruthyNumber(raw.defectX ?? defect.position.x, 0),
    defectY: isQmlTruthyNumber(raw.defectY ?? defect.position.y, 0),
    defectW: isQmlTruthyNumber(raw.defectW ?? defect.size.width, 100),
    defectH: isQmlTruthyNumber(raw.defectH ?? defect.size.height, 100),
  }
}

export function buildManualDefectExportPayload(
  defects: DefectData[],
  folderPath: string,
  scope: ManualDefectExportScope,
  options: ManualDefectExportOptions = {},
): Record<string, unknown> {
  return {
    defects: getExportableDefects(defects, scope).map(defectToPythonPayload),
    folder_path: folderPath,
    group_by_category: options.groupByCategory ?? true,
    include_info: options.includeInfo ?? true,
    high_quality: options.highQuality ?? false,
  }
}

export function formatManualDefectExportResult(result: ManualDefectExportResult): string {
  return `成功导出 ${result.exported ?? 0} 个缺陷图像\n共 ${result.total ?? 0} 个缺陷\n分类: ${
    result.categories ?? 0
  } 个`
}

export function formatManualDefectExportError(error: unknown): string {
  return `导出过程中发生错误:\n${JSON.stringify(error)}`
}
