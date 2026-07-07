import type { CoilData } from '@/types'

export interface ListValueChangeRange {
  startId: string
  endId: string
}

export interface ListValueChangePoint {
  coilId: number
  coilNo: string
  label: string
  value: number
}

export interface ListValueChangeFilterRange {
  startId?: string
  endId?: string
}

const NORMALIZED_KEY_MAP: Record<string, keyof CoilData> = {
  Grade: 'grade',
  DefectCountS: 'defectCountS',
  DefectCountL: 'defectCountL',
  Status_S: 'statusS',
  Status_L: 'statusL',
}

const QML_DISPLAY_KEY_MAP: Record<string, string> = {
  二级内径: 'CoilInside',
  二级卷径: 'CoilDia',
  二级厚度: 'Thickness',
  宽度: 'Width',
}

const RAW_KEY_ALIASES: Record<string, string[]> = {
  CoilInside: ['CoilInside', 'coilInside', 'coil_inside'],
  CoilDia: ['CoilDia', 'coilDia', 'coil_dia'],
  Thickness: ['Thickness', 'coilThickness', 'thickness'],
  Width: ['Width', 'coilWidth', 'width'],
}

export function buildListValueChangeInitialRange(coilList: CoilData[]): ListValueChangeRange {
  if (coilList.length === 0) {
    return { startId: '', endId: '' }
  }

  return {
    startId: String(coilList[coilList.length - 1].id),
    endId: String(coilList[0].id),
  }
}

export function normalizeListValueChangeKeys(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
}

function parseIdInput(value: string | undefined): number | null {
  if (!value || value.trim() === '') return null
  const parsed = Number(value)
  return Number.isInteger(parsed) ? parsed : null
}

function isInsideRange(coilId: number, range: ListValueChangeFilterRange | undefined): boolean {
  const start = parseIdInput(range?.startId)
  const end = parseIdInput(range?.endId)
  if (start === null && end === null) return true

  const lower = Math.min(start ?? end ?? coilId, end ?? start ?? coilId)
  const upper = Math.max(start ?? end ?? coilId, end ?? start ?? coilId)
  return coilId >= lower && coilId <= upper
}

function asFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) return Number(value)
  return null
}

function readCoilNumericValue(coil: CoilData, key: string): number | null {
  if (key === '缺陷') {
    const sCount = readCoilNumericValue(coil, 'DefectCountS') ?? 0
    const lCount = readCoilNumericValue(coil, 'DefectCountL') ?? 0
    return sCount + lCount
  }

  const rawKey = QML_DISPLAY_KEY_MAP[key] ?? key
  for (const candidateKey of RAW_KEY_ALIASES[rawKey] ?? [rawKey]) {
    const rawNumber = asFiniteNumber(coil.raw?.[candidateKey])
    if (rawNumber !== null) return rawNumber
  }

  const normalizedKey = NORMALIZED_KEY_MAP[rawKey]
  if (!normalizedKey) return null
  return asFiniteNumber(coil[normalizedKey])
}

export function buildListValueChangePoints(
  coilList: CoilData[],
  key: string | undefined,
  range?: ListValueChangeFilterRange,
): ListValueChangePoint[] {
  if (!key) return []

  return [...coilList]
    .sort((left, right) => left.id - right.id)
    .flatMap((coil) => {
      if (!isInsideRange(coil.id, range)) return []
      const value = readCoilNumericValue(coil, key)
      if (value === null) return []
      return [
        {
          coilId: coil.id,
          coilNo: coil.coilNo,
          label: String(coil.id),
          value,
        },
      ]
    })
}

export function chooseListValueChangeKey(keys: string[], _coilList: CoilData[]): string | undefined {
  if (keys.length === 0) return undefined
  return keys[0]
}
