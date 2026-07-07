import type { CoilData, DefectData } from '@/types'

export interface DefectClassFilterOption {
  name: string
  color?: string
  level?: number
  show: boolean
}

export const QML_LEFT_LIST_NO_DEFECT_CLASS_NAME = '无缺陷'
export const QML_DEFAULT_DEFECT_COLOR = '#FFA500'

type DictRecord = Record<string, unknown>

export function getQmlDefectClassLevelColor(level: unknown): string {
  const numericLevel = Number(level)
  if (!Number.isFinite(numericLevel)) return '#00000000'
  if (numericLevel >= 3) return 'red'
  if (numericLevel >= 2) return 'yellow'
  if (numericLevel >= 1) return 'gray'
  return '#00000000'
}

function asRecord(value: unknown): DictRecord {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as DictRecord) : {}
}

function normalizeQmlDefectItems(source: unknown): DictRecord[] {
  if (!source) return []
  if (Array.isArray(source)) return source.map(asRecord)

  const record = asRecord(source)
  return Object.keys(record).length > 0 ? [record] : []
}

function readQmlDefectName(defect: unknown): string {
  const record = asRecord(defect)
  for (const key of ['defectName', 'DefectName', 'configDefectName', 'ConfigDefectName', 'name', 'Name']) {
    const value = record[key]
    if (value !== undefined && value !== null && String(value) !== '') return String(value)
  }
  return ''
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') return value.toLowerCase() === 'true'
  return fallback
}

function readNumber(value: unknown): number | undefined {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : undefined
}

function normalizeColor(value: unknown): string | undefined {
  if (value === undefined || value === null) return QML_DEFAULT_DEFECT_COLOR
  if (typeof value === 'string') return value

  const record = asRecord(value)
  if ('color' in record) return normalizeColor(record.color)
  if ('defectColor' in record) return normalizeColor(record.defectColor)

  if ('r' in record && 'g' in record && 'b' in record) {
    const alpha = readNumber(record.a) ?? 1
    return `rgba(${Number(record.r)}, ${Number(record.g)}, ${Number(record.b)}, ${alpha})`
  }

  return QML_DEFAULT_DEFECT_COLOR
}

function normalizeOption(name: string, value: unknown, fallbackShow: boolean): DefectClassFilterOption {
  const record = asRecord(value)
  const option: DefectClassFilterOption = {
    name,
    show: readBoolean(record.show, fallbackShow),
  }
  const color = normalizeColor(record.color ?? record.defectColor)
  const level = readNumber(record.level ?? record.defectLevel)

  if (color) option.color = color
  if (level !== undefined) option.level = level

  return option
}

function getDictionaryData(defectDict: unknown): unknown {
  const record = asRecord(defectDict)
  return 'data' in record ? record.data : defectDict
}

function getDictionaryDefault(defectDict: unknown): DictRecord {
  return asRecord(asRecord(defectDict).default)
}

function isAreaDefectName(defectName: string): boolean {
  return defectName.startsWith('2D_')
}

export function getDataShowDefectClassName(defect: DefectData): string {
  const raw = asRecord(defect.raw)
  for (const key of ['configDefectName', 'ConfigDefectName']) {
    const value = raw[key]
    if (value !== undefined && value !== null && String(value) !== '') return String(value)
  }
  return defect.defectType
}

function buildAreaDefectOption(defectName: string, defectDict: unknown): DefectClassFilterOption {
  const defaults = getDictionaryDefault(defectDict)
  return {
    name: defectName,
    show: true,
    color: normalizeColor(defaults.defectColor ?? defaults.color) ?? '#FFA500',
    level: readNumber(defaults.defectLevel ?? defaults.level) ?? 1,
  }
}

export function buildDefectClassFilterOptions(
  defectDict: unknown,
  defects: DefectData[] = [],
): DefectClassFilterOption[] {
  const dictionaryData = getDictionaryData(defectDict)
  let options: DefectClassFilterOption[] = []

  if (Array.isArray(dictionaryData)) {
    options = dictionaryData
      .map((item) => {
        const record = asRecord(item)
        const name = String(record.name ?? record.defectName ?? '')
        return name ? normalizeOption(name, record, true) : null
      })
      .filter((item): item is DefectClassFilterOption => item !== null)
  } else {
    const dictionaryRecord = asRecord(dictionaryData)
    options = Object.entries(dictionaryRecord).map(([name, value]) => normalizeOption(name, value, true))
  }

  if (options.length === 0) {
    const seen = new Set<string>()
    return defects.flatMap((defect) => {
      if (!defect.defectType || seen.has(defect.defectType)) return []
      seen.add(defect.defectType)
      return [{ name: defect.defectType, show: true }]
    })
  }

  const optionNames = new Set(options.map((option) => option.name))
  for (const defect of defects) {
    if (defect.defectType && isAreaDefectName(defect.defectType) && !optionNames.has(defect.defectType)) {
      options.push(buildAreaDefectOption(defect.defectType, defectDict))
      optionNames.add(defect.defectType)
    }
  }

  return [...options].sort((left, right) => Number(right.show) - Number(left.show))
}

export function buildDataShowDefectClassFilterOptions(
  defectDict: unknown,
  defects: DefectData[] = [],
): DefectClassFilterOption[] {
  const options = buildDefectClassFilterOptions(defectDict)
  if (options.length === 0) {
    const seen = new Set<string>()
    return defects.flatMap((defect) => {
      const className = getDataShowDefectClassName(defect)
      if (!className || seen.has(className)) return []
      seen.add(className)
      return [{ name: className, show: true }]
    })
  }

  const optionNames = new Set(options.map((option) => option.name))
  for (const defect of defects) {
    const className = getDataShowDefectClassName(defect)
    if (className && isAreaDefectName(className) && !optionNames.has(className)) {
      options.push(buildAreaDefectOption(className, defectDict))
      optionNames.add(className)
    }
  }

  return [...options].sort((left, right) => Number(right.show) - Number(left.show))
}

export function getDefaultSelectedDefectClasses(
  options: DefectClassFilterOption[],
  settings: { includeHidden?: boolean } = {},
): string[] {
  return options.filter((option) => settings.includeHidden || option.show).map((option) => option.name)
}

export function getResetDefectClassSelection(options: DefectClassFilterOption[]): string[] {
  return options.filter((option) => option.show).map((option) => option.name)
}

export function getQmlSelectAllDefectClasses(
  options: DefectClassFilterOption[],
  settings: { includeHidden?: boolean } = {},
): string[] {
  return options.filter((option) => settings.includeHidden || option.show).map((option) => option.name)
}

export function getQmlVisibleFilterOptions(
  options: DefectClassFilterOption[],
  settings: { includeHidden?: boolean } = {},
): DefectClassFilterOption[] {
  return options.filter((option) => settings.includeHidden || option.show)
}

export function buildQmlLeftListDefectFilterOptions(defectDict: unknown): DefectClassFilterOption[] {
  return [
    ...getQmlVisibleFilterOptions(buildDefectClassFilterOptions(defectDict)),
    { name: QML_LEFT_LIST_NO_DEFECT_CLASS_NAME, show: false, level: 0 },
  ]
}

export function hasQmlLeftListVisibleDefectOptions(options: DefectClassFilterOption[]): boolean {
  return options.some((option) => option.name !== QML_LEFT_LIST_NO_DEFECT_CLASS_NAME && option.show)
}

export function reconcileQmlDefectClassSelection(
  options: DefectClassFilterOption[],
  selectedClassNames: string[],
  settings: { includeHidden?: boolean; preserveEmpty?: boolean } = {},
): string[] {
  const selectedSet = new Set(selectedClassNames)
  const retained = options.map((option) => option.name).filter((name) => selectedSet.has(name))

  if (settings.preserveEmpty && selectedClassNames.length === 0) {
    return []
  }

  return retained.length > 0 ? retained : getDefaultSelectedDefectClasses(options)
}

export function filterDefectsByClass(defects: DefectData[], selectedClassNames: string[]): DefectData[] {
  const selectedSet = new Set(selectedClassNames)
  return defects.filter((defect) => selectedSet.has(defect.defectType))
}

export function getQmlCoilDefectNames(coil: CoilData): string[] {
  const raw = asRecord(coil.raw)
  const defectItems = normalizeQmlDefectItems(raw.childrenCoilDefect ?? raw.defects)
  return defectItems.map(readQmlDefectName).filter(Boolean)
}

export function filterQmlCoilsByDefectClasses(
  coils: CoilData[],
  selectedClassNames: string[],
  enabled: boolean,
): CoilData[] {
  if (!enabled) return coils

  const selectedSet = new Set(selectedClassNames)
  return coils.filter((coil) => getQmlCoilDefectNames(coil).some((name) => selectedSet.has(name)))
}

export function countDefectsByClass(
  options: Array<Pick<DefectClassFilterOption, 'name'>>,
  defects: DefectData[],
): Record<string, number> {
  const counts = Object.fromEntries(options.map((option) => [option.name, 0]))

  for (const defect of defects) {
    if (defect.defectType in counts) {
      counts[defect.defectType] += 1
    }
  }

  return counts
}

export function countDataShowDefectsByClass(
  options: Array<Pick<DefectClassFilterOption, 'name'>>,
  defects: DefectData[],
): Record<string, number> {
  const counts = Object.fromEntries(options.map((option) => [option.name, 0]))

  for (const defect of defects) {
    const className = getDataShowDefectClassName(defect)
    if (className in counts) {
      counts[className] += 1
    }
  }

  return counts
}

export function filterDataShowDefects(
  defects: DefectData[],
  options: DefectClassFilterOption[],
  settings: { showHidden?: boolean; showArea?: boolean; selectedClassNames?: string[] } = {},
): DefectData[] {
  const optionByName = new Map(options.map((option) => [option.name, option]))
  const selectedSet = settings.selectedClassNames ? new Set(settings.selectedClassNames) : null

  return defects.filter((defect) => {
    const className = getDataShowDefectClassName(defect)

    if (selectedSet && !selectedSet.has(className)) {
      return false
    }

    if (isAreaDefectName(className) && !settings.showArea) {
      return false
    }

    const option = optionByName.get(className)
    if (option && !option.show && !settings.showHidden) {
      return false
    }

    return true
  })
}
