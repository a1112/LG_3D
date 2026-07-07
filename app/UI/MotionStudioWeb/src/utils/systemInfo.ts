const UNKNOWN_LABEL = '未知'

export interface SystemInfoSources {
  info?: unknown
  runtime?: unknown
  database?: unknown
  version?: unknown
}

export interface SystemInfoViewModel {
  originalImageFolderS: string
  originalImageFolderL: string
  saveImageFolderS: string
  saveImageFolderL: string
  pythonVersion: string
  serverVersion: string
  cacheMode: string
  cpuModel: string
  gpuModels: string
  databaseUrl: string
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function readString(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    if (Array.isArray(value) && value.length > 0) return value.map((item) => String(item ?? '')).join(',')
  }
  return UNKNOWN_LABEL
}

function readSurface(info: unknown, key: string): Record<string, unknown> {
  return asRecord(asRecord(info)[key])
}

function joinSurfaceSources(surface: Record<string, unknown>): string {
  const folderList = surface.folderList
  if (!Array.isArray(folderList)) return UNKNOWN_LABEL

  const sources = folderList
    .map((item) => asRecord(item).source)
    .filter((source): source is string => typeof source === 'string' && source.trim().length > 0)

  return sources.length > 0 ? sources.join('\n') : UNKNOWN_LABEL
}

function readGpuModels(runtime: Record<string, unknown>): string {
  const gpus = runtime.gpus
  if (!Array.isArray(gpus)) return UNKNOWN_LABEL

  const names = gpus
    .map((gpu) => (typeof gpu === 'string' ? gpu : String(gpu ?? '')))
    .filter((gpu) => gpu.trim().length > 0)

  return names.length > 0 ? names.join('\n') : UNKNOWN_LABEL
}

function readVersion(version: unknown): string {
  if (typeof version === 'string' && version.trim()) return version
  if (typeof version === 'number' || typeof version === 'boolean') return String(version)
  return UNKNOWN_LABEL
}

export function buildSystemInfoViewModel({
  info,
  runtime,
  database,
  version,
}: SystemInfoSources): SystemInfoViewModel {
  const surfaceS = readSurface(info, 'surfaceS')
  const surfaceL = readSurface(info, 'surfaceL')
  const runtimeRecord = asRecord(runtime)
  const databaseRecord = asRecord(database)

  return {
    originalImageFolderS: joinSurfaceSources(surfaceS),
    originalImageFolderL: joinSurfaceSources(surfaceL),
    saveImageFolderS: readString(surfaceS, ['saveFolder']),
    saveImageFolderL: readString(surfaceL, ['saveFolder']),
    pythonVersion: readString(runtimeRecord, ['python_version']),
    serverVersion: readVersion(version),
    cacheMode: readString(runtimeRecord, ['cache_mode']),
    cpuModel: readString(runtimeRecord, ['cpu_model']),
    gpuModels: readGpuModels(runtimeRecord),
    databaseUrl: readString(databaseRecord, ['url']),
  }
}
