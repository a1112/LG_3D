import axios from 'axios'
import type { CoilData, DefectData, HeightLineSegment, ApiResponse, SurfaceKey } from '@/types'
import { recordApiRequest } from '@/utils/apiHistory'
import { normalizeListValueChangeKeys } from '@/utils/listValueChange'

type ServiceEnv = Record<string, string | undefined>

export interface HeightLineCoords {
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface HeightPointCoords {
  x: number
  y: number
}

export interface CoilDataAreaParams {
  scale?: number
  mask?: boolean
  valueFrom?: number
  valueTo?: number
  r?: number
  g?: number
  b?: number
}

export interface CoilDataErrorParams {
  scale?: number
  mask?: boolean
  minValue?: number
  maxValue?: number
  force_cache?: boolean
}

export interface CoilDataRenderParams {
  scale?: number
  mask?: boolean
  minValue?: number
  maxValue?: number
  grayscale?: boolean
}

export interface ServiceBaseUrls {
  apiBaseUrl: string
  imageBaseUrl: string
  databaseBaseUrl: string
  dataBaseUrl: string
  plcBaseUrl: string
  alg2dBaseUrl: string
  apiWsBaseUrl: string
  databaseWsBaseUrl: string
}

export interface ImageRuntimeSettings {
  useRustImageServer: boolean
  rustImageServerPort: number
  useSharedFolder?: boolean
  sharedFolderBaseName?: string
  imageMaskChecked?: boolean
  quickImageEnabled?: boolean
}

export interface RuntimeConnectionSettings {
  serverIp: string
  serverPort: number
  databasPort: number
  dataPort: number
  plcPort: number
  alg2dPort: number
  useRustImageServer: boolean
  rustImageServerPort: number
}

export interface RuntimeApiConnectionSettings {
  serverIp: string
  serverPort: number
}

export type DataAvailabilitySurface = Record<string, boolean | undefined>
export type DataAvailabilityBySurface = Partial<Record<SurfaceKey, DataAvailabilitySurface>>

export function buildRuntimeConnectionBaseUrls(settings: RuntimeConnectionSettings): ServiceBaseUrls {
  const host = normalizeRuntimeHost(settings.serverIp)
  const apiPort = normalizeRuntimePort(settings.serverPort, 5011)
  const databasePort = normalizeRuntimePort(settings.databasPort, 6011)
  const dataPort = normalizeRuntimePort(settings.dataPort, 6013)
  const plcPort = normalizeRuntimePort(settings.plcPort, 6014)
  const alg2dPort = normalizeRuntimePort(settings.alg2dPort, 5011)
  const imagePort = settings.useRustImageServer ? normalizeRuntimePort(settings.rustImageServerPort) : apiPort

  return {
    apiBaseUrl: `http://${host}:${apiPort}`,
    imageBaseUrl: `http://${host}:${imagePort}`,
    databaseBaseUrl: `http://${host}:${databasePort}`,
    dataBaseUrl: `http://${host}:${dataPort}`,
    plcBaseUrl: `http://${host}:${plcPort}`,
    alg2dBaseUrl: `http://${host}:${alg2dPort}`,
    apiWsBaseUrl: `ws://${host}:${apiPort}`,
    databaseWsBaseUrl: `ws://${host}:${databasePort}`,
  }
}

export function applyRuntimeConnectionSettings(settings: RuntimeConnectionSettings): ServiceBaseUrls {
  const nextBaseUrls = buildRuntimeConnectionBaseUrls(settings)
  Object.assign(serviceBaseUrls, nextBaseUrls)
  apiClient.defaults.baseURL = nextBaseUrls.apiBaseUrl
  return { ...serviceBaseUrls }
}

export interface ExportXlsxConfig {
  export_type: string
  detection_3d_info: boolean
  defect_info: boolean
  defect_show_info: boolean
  defect_un_show_info: boolean
  area_defect_image?: boolean
  export_plc_data: boolean
  startDate: string
  endDate: string
}

export interface Alg2dTestPayload {
  model: string
  target: string
  output: string
  threshold?: number
  mode?: 'copy' | 'move' | string
  options?: Record<string, unknown>
}

export interface AreaClipConfigPayload {
  surface_key?: string
  mode?: 'fixed' | 'dynamic' | string
  fixed?: number
  a?: number
  b?: number
  c?: number
  offset?: number
}

export interface AreaRejoinPayload {
  coil_id: number
  surface_key?: string
}

export interface SetTestModeBody {
  enabled: boolean
}

export interface CameraAdjustmentPayload {
  exposureTime: number
  gain: number
  save: boolean
}

function normalizeBaseUrl(baseUrl: string): string {
  const trimmed = baseUrl.trim()
  if (trimmed === '') return ''
  if (trimmed === '/') return ''
  return trimmed.replace(/\/+$/, '')
}

function normalizeRuntimeHost(host: string, fallback = '127.0.0.1'): string {
  const trimmed = host.trim()
  if (!trimmed || !/^[a-zA-Z0-9.-]+$/.test(trimmed)) return fallback
  return trimmed
}

export function joinBaseUrl(baseUrl: string, path: string): string {
  const base = normalizeBaseUrl(baseUrl)
  const normalizedPath = path.replace(/^\/+/, '')
  if (!base) return `/${normalizedPath}`
  return `${base}/${normalizedPath}`
}

export function resolveServiceBaseUrls(env: ServiceEnv): ServiceBaseUrls {
  const apiBaseUrl = normalizeBaseUrl(env.VITE_API_BASE_URL || '/api') || '/api'
  const runtimeDefaults = apiBaseUrl.startsWith('/')
    ? {
        host: typeof window === 'undefined' ? '127.0.0.1' : window.location.hostname,
      }
    : {
        host: apiBaseUrl.replace(/^https?:\/\//, '').replace(/\/.*/, '').split(':')[0],
      }

  return {
    apiBaseUrl,
    imageBaseUrl: normalizeBaseUrl(env.VITE_IMAGE_BASE_URL || apiBaseUrl) || apiBaseUrl,
    databaseBaseUrl: apiBaseUrl,
    dataBaseUrl: apiBaseUrl,
    plcBaseUrl: apiBaseUrl,
    alg2dBaseUrl: apiBaseUrl,
    apiWsBaseUrl: `ws://${runtimeDefaults.host}:5011`,
    databaseWsBaseUrl: `ws://${runtimeDefaults.host}:6011`,
  }
}

export const serviceBaseUrls = resolveServiceBaseUrls(import.meta.env)

function normalizeRuntimePort(port: number, fallback = 6013): number {
  if (!Number.isFinite(port)) return fallback
  return Math.min(Math.max(Math.trunc(port), 1), 65535)
}

export function buildRuntimeApiBaseUrl(settings: RuntimeApiConnectionSettings): string {
  return `http://${normalizeRuntimeHost(settings.serverIp)}:${normalizeRuntimePort(settings.serverPort, 5011)}`
}

export function resolveImageRuntimeBaseUrl(
  settings: ImageRuntimeSettings,
  bases: ServiceBaseUrls = serviceBaseUrls,
  hostname = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1',
): string {
  if (!settings.useRustImageServer) {
    return bases.apiBaseUrl
  }

  return `http://${hostname}:${normalizeRuntimePort(settings.rustImageServerPort)}`
}

function normalizeSharedFolderBaseName(value: string | undefined): string {
  const trimmed = value?.trim()
  return trimmed || 'Save_'
}

export function resolveQmlSurfaceImageUrl(
  settings: ImageRuntimeSettings,
  surfaceKey: string,
  coilId: number,
  viewKey: string,
  preview = false,
  imageBaseUrl = resolveImageRuntimeBaseUrl(settings),
  hostname = typeof window !== 'undefined' ? window.location.hostname : '127.0.0.1',
): string {
  const normalizedSurface = normalizeSurfaceKey(surfaceKey)
  const imageMaskChecked = settings.imageMaskChecked === true
  const quickImageEnabled = settings.quickImageEnabled === true
  const rawViewKey = String(viewKey || 'GRAY')
  const normalizedViewKey = imageMaskChecked && rawViewKey === 'AREA' ? 'AREA_MASK' : rawViewKey

  if (normalizedViewKey === 'AREA' || normalizedViewKey === 'AREA_MASK') {
    const path = preview
      ? buildImagePreviewPath(normalizedSurface, coilId, normalizedViewKey)
      : buildImageAreaPath(normalizedSurface, coilId, normalizedViewKey)
    return joinBaseUrl(imageBaseUrl, path)
  }

  if (!settings.useSharedFolder) {
    const path = preview
      ? buildImagePreviewPath(normalizedSurface, coilId, normalizedViewKey)
      : buildImageSourcePath(normalizedSurface, coilId, normalizedViewKey)
    const url = joinBaseUrl(imageBaseUrl, path)
    return !preview && settings.imageMaskChecked !== undefined ? appendOptionalParams(url, { mask: imageMaskChecked }) : url
  }

  const folderBase = `file:////${hostname}/${normalizeSharedFolderBaseName(settings.sharedFolderBaseName)}${normalizedSurface}/${coilId}`
  if (preview) {
    return `${folderBase}/preView/${encodeURIComponent(normalizedViewKey)}.png`
  }
  if (imageMaskChecked) {
    return `${folderBase}/mask/${encodeURIComponent(normalizedViewKey)}.png`
  }
  if (quickImageEnabled) {
    return `${folderBase}/jpg/${encodeURIComponent(normalizedViewKey)}.jpg`
  }
  return `${folderBase}/png/${encodeURIComponent(normalizedViewKey)}.png`
}

// 创建axios实例
const apiClient = axios.create({
  baseURL: serviceBaseUrls.apiBaseUrl,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function applyApiBaseUrlOverride(baseUrl: string): ServiceBaseUrls {
  const nextApiBaseUrl = normalizeBaseUrl(baseUrl) || '/api'
  const previousApiBaseUrl = serviceBaseUrls.apiBaseUrl
  const imageBaseFollowedApi = serviceBaseUrls.imageBaseUrl === previousApiBaseUrl

  serviceBaseUrls.apiBaseUrl = nextApiBaseUrl
  if (imageBaseFollowedApi) {
    serviceBaseUrls.imageBaseUrl = nextApiBaseUrl
  }
  if (/^https?:\/\//.test(nextApiBaseUrl)) {
    const parsed = new URL(nextApiBaseUrl)
    const port = Number.parseInt(parsed.port, 10)
    const fallbackPort = parsed.protocol === 'wss:' || parsed.protocol === 'https:' ? 443 : 80
    const nextWsPort = Number.isFinite(port) && port > 0 ? port : fallbackPort
    serviceBaseUrls.apiWsBaseUrl = `ws${parsed.protocol === 'https:' ? 's' : ''}://${parsed.hostname}:${nextWsPort}`
  }
  apiClient.defaults.baseURL = nextApiBaseUrl

  return serviceBaseUrls
}

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    recordApiRequest({
      method: config.method,
      url: joinBaseUrl(String(config.baseURL ?? ''), String(config.url ?? '')),
    })
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

type BackendListResponse<T> = {
  value?: T[]
  coilList?: T[]
  Count?: number
  data?: T[]
  code?: number
  message?: string
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function readNumber(record: Record<string, unknown>, keys: string[], fallback = 0): number {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) return Number(value)
  }
  return fallback
}

function readOptionalNumber(record: Record<string, unknown>, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) return Number(value)
  }
  return undefined
}

function readString(record: Record<string, unknown>, keys: string[], fallback = ''): string {
  for (const key of keys) {
    const value = record[key]
    if (value !== undefined && value !== null) return String(value)
  }
  return fallback
}

function formatBackendDate(value: unknown): string {
  if (!value) return ''
  if (typeof value === 'string') return value
  const record = asRecord(value)
  const year = readNumber(record, ['year'])
  const month = readNumber(record, ['month'])
  const day = readNumber(record, ['day'])
  const hour = readNumber(record, ['hour'])
  const minute = readNumber(record, ['minute'])
  const second = readNumber(record, ['second'])
  if (!year || !month || !day) return ''
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${year}-${pad(month)}-${pad(day)} ${pad(hour)}:${pad(minute)}:${pad(second)}`
}

function normalizeSurfaceKey(surface: unknown): SurfaceKey {
  const text = String(surface ?? 'S').toUpperCase()
  return text === 'L' ? 'L' : 'S'
}

function normalizePixelCoord(value: unknown): number {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 0
  return Math.max(0, Math.trunc(numberValue))
}

function requireSurfaceKey(surface: unknown): SurfaceKey {
  const text = String(surface ?? '').trim().toUpperCase()
  if (text === 'S' || text === 'L') return text
  throw new Error('clip-max requires a valid surface')
}

function requireClipMaxCoilId(coilId: number): number {
  if (Number.isInteger(coilId) && coilId > 0) return coilId
  throw new Error('clip-max requires a valid coil id')
}

function countChildDefectsBySurface(record: Record<string, unknown>, surface: SurfaceKey): number {
  const children = record.childrenCoilDefect
  if (!Array.isArray(children)) return 0

  return children.filter((item) => normalizeSurfaceKey(asRecord(item).surface) === surface).length
}

function normalizeCoil(item: unknown): CoilData {
  const record = asRecord(item)
  const id = readNumber(record, ['id', 'Id', 'SecondaryCoilId', 'secondaryCoilId', 'secondary_coil_id'])
  const statusS = readNumber(record, ['statusS', 'Status_S', 'StatusS', 'status_s'])
  const statusL = readNumber(record, ['statusL', 'Status_L', 'StatusL', 'status_l'])
  const explicitDefectCountS = readOptionalNumber(record, ['defectCountS', 'DefectCountS', 'defect_count_s'])
  const explicitDefectCountL = readOptionalNumber(record, ['defectCountL', 'DefectCountL', 'defect_count_l'])
  return {
    id,
    coilNo: readString(
      record,
      ['coilNo', 'CoilNo', 'coil_no', 'SecondaryCoilId', 'secondaryCoilId', 'secondary_coil_id'],
      String(id || '')
    ),
    dateTime: formatBackendDate(
      record.dateTime ??
        record.DateTime ??
        record.createTime ??
        record.CreateTime ??
        record.detectionTime ??
        record.DetectionTime ??
        record.create_time ??
        record.detection_time
    ),
    status: Math.max(
      statusS,
      statusL,
      readNumber(record, ['status', 'Status', 'checkStatus', 'CheckStatus', 'check_status'])
    ),
    surfaceKey: 'S',
    grade: readNumber(record, ['grade', 'Grade']),
    defectCountS: explicitDefectCountS ?? countChildDefectsBySurface(record, 'S'),
    defectCountL: explicitDefectCountL ?? countChildDefectsBySurface(record, 'L'),
    statusS,
    statusL,
    alarmInfo: record.alarmInfo ?? record.AlarmInfo,
    raw: record,
  }
}

function normalizeDefect(item: unknown): DefectData {
  const record = asRecord(item)
  const id = readNumber(record, ['id', 'Id'])
  const x = readNumber(record, ['defectX', 'x', 'X'])
  const y = readNumber(record, ['defectY', 'y', 'Y'])
  const width = readNumber(record, ['defectW', 'width', 'Width', 'w', 'W'])
  const height = readNumber(record, ['defectH', 'height', 'Height', 'h', 'H'])
  return {
    id,
    coilId: readNumber(record, ['coilId', 'secondaryCoilId', 'SecondaryCoilId']),
    surface: normalizeSurfaceKey(record.surface),
    defectType: readString(record, ['defectName', 'DefectName', 'defectType', 'name', 'configDefectName'], '缺陷'),
    position: { x, y },
    size: { width, height },
    confidence: Math.max(0, Math.min(1, readNumber(record, ['confidence', 'defectSource'], 1))),
    description: readString(record, ['description', 'Msg', 'msg']),
    level: readNumber(record, ['defectLevel', 'level'], -1),
    raw: record,
  }
}

function normalizeListResponse<TIn, TOut>(response: BackendListResponse<TIn> | TIn[], mapper: (item: TIn) => TOut): ApiResponse<TOut[]> {
  const items = Array.isArray(response)
    ? response
    : Array.isArray(response.value)
      ? response.value
      : Array.isArray(response.coilList)
        ? response.coilList
      : Array.isArray(response.data)
        ? response.data
        : []
  return {
    code: Array.isArray(response) ? 0 : response.code ?? 0,
    data: items.map(mapper),
    count: Array.isArray(response) ? items.length : response.Count ?? items.length,
    message: Array.isArray(response) ? undefined : response.message,
  }
}

export function buildHeightLinePath(surfaceKey: string, coilId: number, coords?: HeightLineCoords): string {
  const path = `/coilData/heightData/${surfaceKey}/${coilId}`
  if (!coords) return path

  const params = new URLSearchParams({
    x1: String(coords.x1),
    y1: String(coords.y1),
    x2: String(coords.x2),
    y2: String(coords.y2),
  })
  return `${path}?${params.toString()}`
}

export function buildHeightPointPath(surfaceKey: string, coilId: number, coords: HeightPointCoords): string {
  const params = new URLSearchParams({
    x: String(normalizePixelCoord(coords.x)),
    y: String(normalizePixelCoord(coords.y)),
  })
  return `/coilData/heightPoint/${normalizeSurfaceKey(surfaceKey)}/${coilId}?${params.toString()}`
}

function appendOptionalParams(path: string, values: Record<string, number | boolean | undefined>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined) params.set(key, String(value))
  }
  const query = params.toString()
  return query ? `${path}?${query}` : path
}

export function buildCoilDataAreaPath(surfaceKey: string, coilId: number, params?: CoilDataAreaParams): string {
  return appendOptionalParams(`/coilData/Area/${normalizeSurfaceKey(surfaceKey)}/${coilId}`, {
    scale: params?.scale,
    mask: params?.mask,
    valueFrom: params?.valueFrom,
    valueTo: params?.valueTo,
    r: params?.r,
    g: params?.g,
    b: params?.b,
  })
}

export function buildCoilDataRenderPath(surfaceKey: string, coilId: number, params?: CoilDataRenderParams): string {
  return appendOptionalParams(`/coilData/Render/${normalizeSurfaceKey(surfaceKey)}/${coilId}`, {
    scale: params?.scale,
    mask: params?.mask,
    minValue: params?.minValue,
    maxValue: params?.maxValue,
    grayscale: params?.grayscale,
  })
}

export function buildCoilDataErrorPath(surfaceKey: string, coilId: number, params?: CoilDataErrorParams): string {
  return appendOptionalParams(`/coilData/Error/${normalizeSurfaceKey(surfaceKey)}/${coilId}`, {
    scale: params?.scale,
    mask: params?.mask,
    minValue: params?.minValue,
    maxValue: params?.maxValue,
    force_cache: params?.force_cache,
  })
}

export function buildDefaultCoilDataErrorPath(
  surfaceKey: string,
  coilId: number,
  thresholds?: Pick<CoilDataErrorParams, 'minValue' | 'maxValue'>,
): string {
  return buildCoilDataErrorPath(surfaceKey, coilId, {
    scale: 1,
    mask: false,
    minValue: thresholds?.minValue ?? -100,
    maxValue: thresholds?.maxValue ?? 100,
  })
}

export function buildDefectAllPath(startCoilId: number, endCoilId: number): string {
  return `/search/getDefectAll/${startCoilId}/${endCoilId}`
}

export function buildDefectsAllPath(coilId: number, surfaceKey: string): string {
  return `/search/defects_all/${coilId}/${normalizeSurfaceKey(surfaceKey)}`
}

export function buildManualDefectsPath(coilId: number, surfaceKey: string): string {
  return `/manual_defects/${coilId}/${normalizeSurfaceKey(surfaceKey)}`
}

export function buildManualDefectAddPath(): string {
  return '/manual_defect/add'
}

export function buildManualDefectUpdatePath(defectId: number): string {
  return `/manual_defect/update/${defectId}`
}

export function buildDeleteManualDefectPath(defectId: number): string {
  return `/manual_defect/delete/${defectId}`
}

export function buildManualDefectExportPath(): string {
  return '/export_defects'
}

export function buildCoilDetailPath(coilId: number): string {
  return `/detail/${coilId}`
}

export function buildDataHasPath(coilId: number): string {
  return `/data_has/${coilId}`
}

export function buildCoilStatePath(coilId: number): string {
  return `/search/CoilState/${coilId}`
}

export function buildPlcDataPath(coilId: number): string {
  return `/search/PlcData/${coilId}`
}

export function buildPlcInfoPath(): string {
  return '/plc/info/'
}

export function buildPlcConnectPath(plcIp: string, rack: number, slot: number): string {
  return `/plc/connect/${encodeURIComponent(plcIp)}/${rack}/${slot}`
}

export function buildPlcGetPath(addr: string, typeStr: string, length: number): string {
  return `/plc/get/${encodeURIComponent(addr)}/${encodeURIComponent(typeStr)}/${length}`
}

export function buildCoilStatusPath(coilId: number): string {
  return `/check/get_coil_status/${coilId}`
}

export function buildSetCoilStatusPath(coilId: number, status: number, msg?: string): string {
  const trimmedMsg = msg?.trim()
  if (!trimmedMsg) return `/check/set_coil_status/${coilId}/${status}`
  return `/check/set_coil_status/${coilId}/${status}/${encodeURIComponent(trimmedMsg)}`
}

export function buildSearchCoilNoPath(coilNo: string): string {
  return `/search/coilNo/${encodeURIComponent(coilNo)}`
}

export function buildSearchCoilIdPath(coilId: number): string {
  return `/search/coilId/${coilId}`
}

export function buildSearchDateTimePath(start: string, end: string): string {
  return `/search/DateTime/${start}/${end}`
}

export function buildCoilAlarmPath(coilId: number): string {
  return `/coilAlarm/${coilId}`
}

export function buildFlushPath(coilId: number): string {
  return `/flush/${coilId}`
}

export function buildCoilListValueChangeKeysPath(): string {
  return '/coil_list_value_change_keys'
}

export function buildDefectDictPath(): string {
  return '/defectDict'
}

export function buildDefectDictAllPath(): string {
  return '/defectDictAll'
}

export function buildSetDefectDictPath(): string {
  return '/setDefectDict'
}

export function buildControlConfigPath(): string {
  return '/control/config'
}

export function buildSetControlConfigPath(): string {
  return '/control/set_config'
}

export function buildSetControlPropertyPath(key: string, value: string): string {
  const params = new URLSearchParams({ key, value })
  return `/control/set_property?${params.toString()}`
}

export function buildDownloadTestPath(): string {
  return '/download_test'
}

export function buildSpeedtestDownloadPath(sizeInMb?: number): string {
  if (sizeInMb === undefined) return '/speedtest/download'
  const params = new URLSearchParams({ size_in_mb: sizeInMb.toString() })
  return `/speedtest/download?${params.toString()}`
}

export function buildSpeedtestUploadPath(): string {
  return '/speedtest/upload'
}

function appendFiniteNumberParam(params: URLSearchParams, key: string, value: number | undefined): void {
  if (value !== undefined && Number.isFinite(value)) params.set(key, String(value))
}

export function buildPlcCurvePath(field: string, startId?: number, endId?: number, limit?: number): string {
  const params = new URLSearchParams()
  appendFiniteNumberParam(params, 'start_id', startId)
  appendFiniteNumberParam(params, 'end_id', endId)
  appendFiniteNumberParam(params, 'limit', limit)
  const query = params.toString()
  const path = `/plc_curve/${encodeURIComponent(field)}`
  return query ? `${path}?${query}` : path
}

export function buildPlcCurveAllPath(startId?: number, endId?: number, limit?: number): string {
  const params = new URLSearchParams()
  appendFiniteNumberParam(params, 'start_id', startId)
  appendFiniteNumberParam(params, 'end_id', endId)
  appendFiniteNumberParam(params, 'limit', limit)
  const query = params.toString()
  return query ? `/plc_curve_all?${query}` : '/plc_curve_all'
}

export function buildInfoPath(): string {
  return '/info'
}

export function buildDatabaseInfoPath(): string {
  return '/database_info'
}

export function buildVersionPath(): string {
  return '/version'
}

export function buildHealthPath(): string {
  return '/health'
}

export function buildDelayPath(): string {
  return '/delay'
}

export function buildRuntimeInfoPath(): string {
  return '/runtime_info'
}

export function buildOpenApiPath(): string {
  return '/openapi.json'
}

export function buildHardwarePath(): string {
  return '/hardware'
}

export function buildCaptureStatusPath(): string {
  return '/capture_status'
}

export function buildCaptureStatusCompatPath(): string {
  return '/capture/status'
}

export function buildCaptureFilesPath(clear = false): string {
  if (!clear) return '/capture/files'
  return '/capture/files?clear=true'
}

export function buildGetListenerAddFilePath(clear = false): string {
  if (!clear) return '/getListenerAddFile'
  return '/getListenerAddFile?clear=true'
}

export function buildCameraAdjustPath(): string {
  return '/camera_adjust'
}

export function buildCameraStatusPath(): string {
  return '/camera/status'
}

export function buildCamerasPath(): string {
  return '/cameras'
}

export function buildCameraStatusByKeyPath(cameraKey: string): string {
  return `/cameras/${encodeURIComponent(cameraKey)}/status`
}

export function buildCameraFilesByKeyPath(cameraKey: string): string {
  return `/cameras/${encodeURIComponent(cameraKey)}/files`
}

export function buildCameraAdjustmentPath(cameraKey: string): string {
  return `/camera_adjust/${encodeURIComponent(cameraKey)}`
}

export function buildCameraParamsPath(): string {
  return '/camera/params'
}

export function buildCameraReconnectCompatPath(): string {
  return '/camera/reconnect'
}

export function buildCameraParamsByKeyPath(cameraKey: string): string {
  return `/cameras/${encodeURIComponent(cameraKey)}/params`
}

export function buildCameraReconnectByKeyPath(cameraKey: string): string {
  return `/cameras/${encodeURIComponent(cameraKey)}/reconnect`
}

export function buildCameraReconnectPath(cameraKey: string): string {
  return `${buildCameraAdjustmentPath(cameraKey)}/reconnect`
}

export function buildCameraAdjustmentPayload(
  exposureTime: number,
  gain: number,
  save = true,
): CameraAdjustmentPayload {
  return {
    exposureTime,
    gain,
    save,
  }
}

export function buildCameraAlarmPath(): string {
  return '/cameraAlarm'
}

export function buildCameraDataPath(coilId: number, cameraKey: string): string {
  return `/cameraData/${coilId}/${encodeURIComponent(cameraKey)}`
}

export function buildSyncSummariesPath(limit?: number): string {
  if (limit === undefined) return '/sync_summaries'
  const params = new URLSearchParams({ limit: String(limit) })
  return `/sync_summaries?${params.toString()}`
}

export function buildSyncSummariesRangePath(): string {
  return '/sync_summaries_range'
}

export function buildTestModePath(): string {
  return '/settings/test_mode'
}

export function buildTestModeStatusPath(): string {
  return '/settings/test_mode_status'
}

export function buildSetTestModeBody(enabled: boolean): SetTestModeBody {
  return { enabled }
}

export function buildPointDataPath(coilId: number, surfaceKey: string): string {
  return `/get_point_data/${coilId}/${surfaceKey}`
}

export function buildLineDataPath(coilId: number, surfaceKey: string): string {
  return `/get_line_data/${coilId}/${surfaceKey}`
}

export function buildClassifierImagePath(
  coilId: number,
  surfaceKey: string,
  defectName: string,
  x: number,
  y: number,
  w: number,
  h: number
): string {
  return `/classifier_image/${coilId}/${normalizeSurfaceKey(surfaceKey)}/${encodeURIComponent(defectName)}/${x}/${y}/${w}/${h}`
}

export function buildDefectImagePath(
  surfaceKey: string,
  coilId: number,
  type: string,
  x: number,
  y: number,
  w: number,
  h: number
): string {
  return `/defect_image/${normalizeSurfaceKey(surfaceKey)}/${coilId}/${encodeURIComponent(type)}/${x}/${y}/${w}/${h}`
}

export function buildImagePreviewPath(surfaceKey: string, coilId: number, type: string): string {
  return `/image/preview/${normalizeSurfaceKey(surfaceKey)}/${coilId}/${encodeURIComponent(type)}`
}

export function buildImageSourcePath(surfaceKey: string, coilId: number, type: string): string {
  return `/image/source/${normalizeSurfaceKey(surfaceKey)}/${coilId}/${encodeURIComponent(type)}`
}

export function buildImageAreaPath(surfaceKey: string, coilId: number, type?: string): string {
  const path = `/image/area/${normalizeSurfaceKey(surfaceKey)}/${coilId}`
  const normalizedType = type?.trim()
  if (!normalizedType || normalizedType.toUpperCase() === 'AREA') return path
  return `${path}/${encodeURIComponent(normalizedType)}`
}

export function buildClipMaxImagePath(coilId: number, surfaceKey: string, saveUrl?: string): string {
  const path = `/clipMaxImage/${requireClipMaxCoilId(coilId)}/${requireSurfaceKey(surfaceKey)}`
  if (!saveUrl) return path

  const params = new URLSearchParams({ save_url: saveUrl })
  return `${path}?${params.toString()}`
}

export function buildReDetectionStatusPath(): string {
  return '/reDetection/status'
}

export function buildReDetectionStartPath(fromId: number, toId: number): string {
  return `/reDetection/start/${fromId}/${toId}`
}

export function buildReDetectionWsPath(): string {
  return '/ws/reDetection'
}

export function buildHeightPointWsPath(): string {
  return '/ws/coilData/heightPoint'
}

export function buildServerStatePath(): string {
  return '/getServerState'
}

export function buildServerStateWsPath(): string {
  return '/ws/DetectionState'
}

export function buildAlg2dModelsPath(): string {
  return '/alg_2d/models'
}

export function buildAlg2dTestStartPath(): string {
  return '/alg_2d/test/start'
}

export function buildAlg2dTestStopPath(): string {
  return '/alg_2d/test/stop'
}

export function buildAlg2dTestProgressWsPath(): string {
  return '/ws/alg_2d/test/progress'
}

export function buildClipConfigPath(): string {
  return '/clip_config'
}

export function buildAreaRejoinPath(): string {
  return '/area/rejoin'
}

export function buildAreaRejoinPayload(coilId: number, surfaceKey?: string): AreaRejoinPayload {
  const payload: AreaRejoinPayload = { coil_id: coilId }
  if (surfaceKey) payload.surface_key = normalizeSurfaceKey(surfaceKey)
  return payload
}

export function buildAreaStatusPath(): string {
  return '/area/status'
}

export function buildAreaScanPath(): string {
  return '/area/scan'
}

function normalizePathSegmentPath(path: string): string {
  return path.trim().replace(/\\/g, '/').replace(/^\/+/, '')
}

export function buildBackupImageTaskPath(fromId: number, toId: number, saveFolder: string): string {
  return `/backupImageTask/${fromId}/${toId}/${normalizePathSegmentPath(saveFolder)}`
}

export function buildBackupImageTaskWsPath(): string {
  return '/ws/backupImageTask'
}

export function buildSaveToSqlPath(sqlFile: string): string {
  return `/save_to_sql/${normalizePathSegmentPath(sqlFile)}`
}

function buildQuickExportPath(path: string, exportType?: string): string {
  if (!exportType) return path
  const params = new URLSearchParams({ export_type: exportType })
  return `${path}?${params.toString()}`
}

export function buildExport1hPath(exportType?: string): string {
  return buildQuickExportPath('/export_1h', exportType)
}

export function buildExport24hPath(exportType?: string): string {
  return buildQuickExportPath('/export_24h', exportType)
}

export function buildExportTodayPath(exportType?: string): string {
  return buildQuickExportPath('/export_today', exportType)
}

export function buildExportDataSimplePath(): string {
  return '/exportDataSimple'
}

export function buildExportXlsxByIdPath(startCoilId: number, endCoilId: number, exportType?: string): string {
  return buildQuickExportPath(`/exportXlsxById/${startCoilId}/${endCoilId}`, exportType)
}

export function buildExportXlsxByDateTimePath(start: string, end: string, exportType?: string): string {
  return buildQuickExportPath(`/exportXlsxByDateTime/${start}/${end}`, exportType)
}

export function buildExportXlsxPath(): string {
  return '/export_xlsx'
}

// 卷材数据API
export const coilApi = {
  // 获取卷材列表
  getCoilList: (number: number = 20) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(`/coilList/${number}`)
      .then((response) => normalizeListResponse(response, normalizeCoil)),

  // 按卷号搜索
  searchByCoilNo: (coilNo: string) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(
        buildSearchCoilNoPath(coilNo),
      )
      .then((response) => normalizeListResponse(response, normalizeCoil)),

  // 按流水号搜索
  searchByCoilId: (coilId: number) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(
        buildSearchCoilIdPath(coilId),
      )
      .then((response) => normalizeListResponse(response, normalizeCoil)),

  // 获取卷材详情
  getCoilDetail: (coilId: number) =>
    apiClient.get<unknown, unknown>(buildCoilDetailPath(coilId)).then((response) => normalizeCoil(response)),

  // 获取卷材 3D 状态明细
  getCoilState: (coilId: number) =>
    apiClient.get<unknown, unknown>(buildCoilStatePath(coilId)),

  getCoilInfo: (coilId: number, surfaceKey: string) =>
    apiClient.get<unknown, unknown>(`/coilInfo/${coilId}/${normalizeSurfaceKey(surfaceKey)}`),

  getDataAvailability: (coilId: number) =>
    apiClient.get<DataAvailabilityBySurface, DataAvailabilityBySurface>(buildDataHasPath(coilId)),

  // 获取卷材 PLC 数据
  getPlcData: (coilId: number) =>
    apiClient.get<unknown, unknown>(buildPlcDataPath(coilId)),

  // 获取卷材人工判级状态
  getCoilStatus: (coilId: number) =>
    apiClient.get<unknown, unknown>(buildCoilStatusPath(coilId)),

  // 设置卷材人工判级状态
  setCoilStatus: (coilId: number, status: number, msg?: string) =>
    apiClient.get<unknown, unknown>(buildSetCoilStatusPath(coilId, status, msg)),

  // 获取卷材报警详情
  getCoilAlarm: (coilId: number) =>
    apiClient.get<unknown, unknown>(buildCoilAlarmPath(coilId)),

  // 向上刷新卷材列表
  flush: (coilId: number) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(buildFlushPath(coilId))
      .then((response) => normalizeListResponse(response, normalizeCoil)),

  // 获取列表数值变化可选字段
  getCoilListValueChangeKeys: () =>
    apiClient.get<unknown, unknown>(buildCoilListValueChangeKeysPath()).then(normalizeListValueChangeKeys),

  // 按时间范围搜索
  searchByDateTime: (start: string, end: string) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(
        buildSearchDateTimePath(start, end)
      )
      .then((response) => normalizeListResponse(response, normalizeCoil)),

  getSearchByCoilIdUrl: (coilId: number) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildSearchCoilIdPath(coilId)),
}

// 缺陷数据API
export const defectApi = {
  // 获取缺陷数据
  getDefects: (coilId: number, direction: string) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(`/search/defects/${coilId}/${direction}`)
      .then((response) => normalizeListResponse(response, normalizeDefect)),

  // 获取卷号区间内全部自动缺陷
  getDefectAll: (startCoilId: number, endCoilId: number) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(
        buildDefectAllPath(startCoilId, endCoilId)
      )
      .then((response) => normalizeListResponse(response, normalizeDefect)),

  // 获取单卷单面自动和手动缺陷
  getDefectsAll: (coilId: number, direction: string) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(
        buildDefectsAllPath(coilId, direction)
      )
      .then((response) => normalizeListResponse(response, normalizeDefect)),

  // 获取单卷单面手动缺陷
  getManualDefects: (coilId: number, direction: string) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(
        buildManualDefectsPath(coilId, direction)
      )
      .then((response) => normalizeListResponse(response, normalizeDefect)),

  addManualDefect: (data: Record<string, unknown>) =>
    apiClient.post<unknown, unknown>(buildManualDefectAddPath(), data),

  updateManualDefect: (defectId: number, data: Record<string, unknown>) =>
    apiClient.put<unknown, unknown>(buildManualDefectUpdatePath(defectId), data),

  deleteManualDefect: (defectId: number) =>
    apiClient.delete<unknown, unknown>(buildDeleteManualDefectPath(defectId)),

  exportManualDefects: (data: Record<string, unknown>) =>
    apiClient.post<unknown, unknown>(buildManualDefectExportPath(), data),
}

// 高度数据API
export const heightDataApi = {
  // 获取高度线数据
  getHeightLine: (surfaceKey: string, coilId: number, coords?: HeightLineCoords) =>
    apiClient.get<HeightLineSegment[], HeightLineSegment[]>(
      buildHeightLinePath(surfaceKey, coilId, coords)
    ),

  // 获取高度点数据
  getHeightPoint: (surfaceKey: string, coilId: number, coords: HeightPointCoords) =>
    apiClient.get<number | string, number | string>(
      buildHeightPointPath(surfaceKey, coilId, coords)
    ),

  // 获取3D渲染数据
  getRenderData: (surfaceKey: string, coilId: number, params?: CoilDataRenderParams) =>
    apiClient.get<ArrayBuffer, ArrayBuffer>(buildCoilDataRenderPath(surfaceKey, coilId, params), {
      responseType: 'arraybuffer',
    }),

  // 获取区域叠加图
  getAreaOverlay: (surfaceKey: string, coilId: number, params?: CoilDataAreaParams) =>
    apiClient.get<ArrayBuffer, ArrayBuffer>(buildCoilDataAreaPath(surfaceKey, coilId, params), {
      responseType: 'arraybuffer',
    }),

  // 获取误差数据
  getErrorData: (surfaceKey: string, coilId: number, params?: CoilDataErrorParams) =>
    apiClient.get<ArrayBuffer, ArrayBuffer>(buildCoilDataErrorPath(surfaceKey, coilId, params), {
      responseType: 'arraybuffer',
    }),

  getErrorImageUrl: (surfaceKey: string, coilId: number, thresholds?: Pick<CoilDataErrorParams, 'minValue' | 'maxValue'>) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildDefaultCoilDataErrorPath(surfaceKey, coilId, thresholds)),
}

// 点线测量数据 API
export const measurementDataApi = {
  getPointData: (coilId: number, surfaceKey: string) =>
    apiClient.get<unknown[], unknown[]>(buildPointDataPath(coilId, surfaceKey)),

  getLineData: (coilId: number, surfaceKey: string) =>
    apiClient.get<unknown[], unknown[]>(buildLineDataPath(coilId, surfaceKey)),
}

// 图像工具 API
export const imageToolApi = {
  getClassifierImageUrl: (
    coilId: number,
    surfaceKey: string,
    defectName: string,
    x: number,
    y: number,
    w: number,
    h: number
  ) => joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildClassifierImagePath(coilId, surfaceKey, defectName, x, y, w, h)),

  clipMaxImage: (coilId: number, surfaceKey: string, saveUrl?: string) =>
    apiClient.get<unknown, unknown>(buildClipMaxImagePath(coilId, surfaceKey, saveUrl)),
}

// 运行状态与重识别 API
export const runtimeApi = {
  getReDetectionStatus: () =>
    apiClient.get<unknown, unknown>(buildReDetectionStatusPath()),

  startReDetection: (fromId: number, toId: number) =>
    apiClient.get<unknown, unknown>(buildReDetectionStartPath(fromId, toId)),

  getServerState: () =>
    apiClient.get<unknown, unknown>(buildServerStatePath()),

  backupImageTask: (fromId: number, toId: number, saveFolder: string) =>
    apiClient.get<unknown, unknown>(buildBackupImageTaskPath(fromId, toId, saveFolder)),

  saveToSql: (sqlFile: string) =>
    apiClient.get<unknown, unknown>(buildSaveToSqlPath(sqlFile)),
}

// 参数控制 API
export const controlApi = {
  getConfig: () =>
    apiClient.get<Record<string, unknown>, Record<string, unknown>>(buildControlConfigPath()),

  setConfig: (data: Record<string, unknown>) =>
    apiClient.post<unknown, unknown>(buildSetControlConfigPath(), data),

  setProperty: (key: string, value: string | number | boolean) =>
    apiClient.get<unknown, unknown>(buildSetControlPropertyPath(key, String(value))),
}

// 诊断与测速 API
export const diagnosticApi = {
  getDownloadTestUrl: () =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildDownloadTestPath()),

  getSpeedtestDownloadUrl: (sizeInMb?: number) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildSpeedtestDownloadPath(sizeInMb)),

  uploadSpeedtest: (formData: FormData) =>
    apiClient.post<unknown, unknown>(buildSpeedtestUploadPath(), formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }),
}

// 系统诊断 API
export const systemApi = {
  getInfo: () =>
    apiClient.get<unknown, unknown>(buildInfoPath()),

  getDatabaseInfo: () =>
    apiClient.get<unknown, unknown>(buildDatabaseInfoPath()),

  getVersion: () =>
    apiClient.get<unknown, unknown>(buildVersionPath()),

  getHealth: () =>
    apiClient.get<unknown, unknown>(buildHealthPath()),

  getDelay: () =>
    apiClient.get<unknown, unknown>(buildDelayPath()),

  getRuntimeInfo: () =>
    apiClient.get<unknown, unknown>(buildRuntimeInfoPath()),

  getOpenApi: () =>
    apiClient.get<unknown, unknown>(buildOpenApiPath()),

  getHardware: () =>
    apiClient.get<unknown, unknown>(buildHardwarePath()),

  getCaptureStatus: () =>
    apiClient.get<unknown, unknown>(buildCaptureStatusPath()),

  getCaptureStatusCompat: () =>
    apiClient.get<unknown, unknown>(buildCaptureStatusCompatPath()),

  getCaptureFiles: (clear = false) =>
    apiClient.get<unknown, unknown>(buildCaptureFilesPath(clear)),

  getListenerAddFile: (clear = false) =>
    apiClient.get<unknown, unknown>(buildGetListenerAddFilePath(clear)),

  getCameraStatus: () =>
    apiClient.get<unknown, unknown>(buildCameraStatusPath()),

  getCamerasStatus: () =>
    apiClient.get<unknown, unknown>(buildCamerasPath()),

  getCameraStatusByKey: (cameraKey: string) =>
    apiClient.get<unknown, unknown>(buildCameraStatusByKeyPath(cameraKey)),

  getCameraFilesByKey: (cameraKey: string) =>
    apiClient.get<unknown, unknown>(buildCameraFilesByKeyPath(cameraKey)),

  getCameraAdjust: () =>
    apiClient.get<unknown, unknown>(buildCameraAdjustPath()),

  setCameraAdjustment: (cameraKey: string, exposureTime: number, gain: number, save = true) =>
    apiClient.post<unknown, unknown>(
      buildCameraAdjustmentPath(cameraKey),
      buildCameraAdjustmentPayload(exposureTime, gain, save),
    ),

  reconnectCameraAdjustment: (cameraKey: string) =>
    apiClient.post<unknown, unknown>(buildCameraReconnectPath(cameraKey), {}),

  setCameraParams: (exposureTime: number, gain: number, save = true) =>
    apiClient.post<unknown, unknown>(
      buildCameraParamsPath(),
      buildCameraAdjustmentPayload(exposureTime, gain, save),
    ),

  reconnectCamera: () =>
    apiClient.post<unknown, unknown>(buildCameraReconnectCompatPath(), {}),

  setCameraParamsByKey: (cameraKey: string, exposureTime: number, gain: number, save = true) =>
    apiClient.post<unknown, unknown>(
      buildCameraParamsByKeyPath(cameraKey),
      buildCameraAdjustmentPayload(exposureTime, gain, save),
    ),

  reconnectCameraByKey: (cameraKey: string) =>
    apiClient.post<unknown, unknown>(buildCameraReconnectByKeyPath(cameraKey), {}),

  getCameraAlarm: () =>
    apiClient.get<unknown, unknown>(buildCameraAlarmPath()),

  getCameraData: (coilId: number, cameraKey: string) =>
    apiClient.get<Record<string, unknown>, Record<string, unknown>>(buildCameraDataPath(coilId, cameraKey)),

  getCameraDataUrl: (coilId: number, cameraKey: string) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildCameraDataPath(coilId, cameraKey)),

  syncSummaries: (limit?: number) =>
    apiClient.post<unknown, unknown>(buildSyncSummariesPath(limit), {}),

  syncSummariesRange: (coilIds: number[]) =>
    apiClient.post<unknown, unknown>(buildSyncSummariesRangePath(), { coil_ids: coilIds }),
}

// 2D 算法测试 API
export const algTestApi = {
  getModels: () =>
    apiClient.get<unknown, unknown>(buildAlg2dModelsPath()),

  start: (payload: Alg2dTestPayload) =>
    apiClient.post<unknown, unknown>(buildAlg2dTestStartPath(), payload),

  stop: (taskId?: string) =>
    apiClient.post<unknown, unknown>(buildAlg2dTestStopPath(), taskId ? { task_id: taskId } : {}),

  progressWsPath: () =>
    buildAlg2dTestProgressWsPath(),
}

// 2D 区域拼接 API
export const area2dApi = {
  setClipConfig: (surfaceKey: string, payload: AreaClipConfigPayload) =>
    apiClient.post<unknown, unknown>(buildClipConfigPath(), {
      ...payload,
      surface_key: surfaceKey,
    }),

  rejoin: (coilId: number, surfaceKey?: string) => {
    return apiClient.post<unknown, unknown>(buildAreaRejoinPath(), buildAreaRejoinPayload(coilId, surfaceKey))
  },

  getStatus: () =>
    apiClient.get<unknown, unknown>(buildAreaStatusPath()),

  scan: () =>
    apiClient.post<unknown, unknown>(buildAreaScanPath(), {}),
}

/**
 * 图像尺寸参数
 */
export interface ImageSizeParams {
  width?: number
  height?: number
  quality?: number
  format?: 'jpg' | 'png' | 'webp'
}

/**
 * 构建带尺寸参数的图像URL
 */
function buildImageUrl(baseUrl: string, params?: ImageSizeParams): string {
  if (!params) return baseUrl

  const url = new URL(baseUrl, window.location.origin)

  if (params.width) url.searchParams.set('width', params.width.toString())
  if (params.height) url.searchParams.set('height', params.height.toString())
  if (params.quality) url.searchParams.set('quality', params.quality.toString())
  if (params.format) url.searchParams.set('format', params.format)

  return url.toString()
}

// 图像API
export const imageApi = {
  // 获取预览图像（固定URL）
  getPreview: (surfaceKey: string, coilId: number, type: string, baseUrl = serviceBaseUrls.imageBaseUrl) =>
    joinBaseUrl(baseUrl, buildImagePreviewPath(surfaceKey, coilId, type)),

  // 获取预览图像（支持动态尺寸）
  getPreviewSized: (
    surfaceKey: string,
    coilId: number,
    type: string,
    size?: ImageSizeParams,
    baseUrl = serviceBaseUrls.imageBaseUrl,
  ) =>
    buildImageUrl(
      joinBaseUrl(baseUrl, buildImagePreviewPath(surfaceKey, coilId, type)),
      size
    ),

  // 获取源图像（固定URL）
  getSource: (surfaceKey: string, coilId: number, type: string, baseUrl = serviceBaseUrls.imageBaseUrl) =>
    joinBaseUrl(baseUrl, buildImageSourcePath(surfaceKey, coilId, type)),

  // 获取源图像（支持动态尺寸）
  getSourceSized: (
    surfaceKey: string,
    coilId: number,
    type: string,
    size?: ImageSizeParams,
    baseUrl = serviceBaseUrls.imageBaseUrl,
  ) =>
    buildImageUrl(
      joinBaseUrl(baseUrl, buildImageSourcePath(surfaceKey, coilId, type)),
      size
    ),

  // 获取区域图像
  getArea: (surfaceKey: string, coilId: number, baseUrl = serviceBaseUrls.imageBaseUrl) =>
    joinBaseUrl(baseUrl, buildImageAreaPath(surfaceKey, coilId)),

  // 获取区域图像（支持动态尺寸）
  getAreaSized: (
    surfaceKey: string,
    coilId: number,
    size?: ImageSizeParams,
    baseUrl = serviceBaseUrls.imageBaseUrl,
  ) =>
    buildImageUrl(
      joinBaseUrl(baseUrl, buildImageAreaPath(surfaceKey, coilId)),
      size
    ),

  // 获取缺陷区域图像（固定URL）
  getDefectImage: (
    surfaceKey: string,
    coilId: number,
    type: string,
    x: number,
    y: number,
    w: number,
    h: number,
    baseUrl = serviceBaseUrls.imageBaseUrl,
  ) =>
    joinBaseUrl(
      baseUrl,
      buildDefectImagePath(surfaceKey, coilId, type, x, y, w, h),
    ),

  // 获取缺陷区域图像（支持动态尺寸）
  getDefectImageSized: (
    surfaceKey: string,
    coilId: number,
    type: string,
    x: number,
    y: number,
    w: number,
    h: number,
    size?: ImageSizeParams,
    baseUrl = serviceBaseUrls.imageBaseUrl,
  ) =>
    buildImageUrl(
      joinBaseUrl(
        baseUrl,
        buildDefectImagePath(surfaceKey, coilId, type, x, y, w, h),
      ),
      size
    ),
}

// PLC数据API
export const plcApi = {
  getInfo: () =>
    apiClient.get<unknown, unknown>(buildPlcInfoPath()),

  connect: (plcIp: string, rack: number, slot: number) =>
    apiClient.get<unknown, unknown>(buildPlcConnectPath(plcIp, rack, slot)),

  getValue: (addr: string, typeStr: string, length: number) =>
    apiClient.get<unknown, unknown>(buildPlcGetPath(addr, typeStr, length)),

  // 获取PLC曲线数据
  getCurve: (field: string, startId?: number, endId?: number, limit?: number) =>
    apiClient.get<unknown, unknown>(buildPlcCurvePath(field, startId, endId, limit)),

  getCurveAll: (startId?: number, endId?: number, limit?: number) =>
    apiClient.get<unknown, unknown>(buildPlcCurveAllPath(startId, endId, limit)),

  // 获取硬件信息
  getHardware: () =>
    apiClient.get<unknown, unknown>('/hardware'),
}

// 设置与系统信息 API
export const settingsApi = {
  getTestMode: () =>
    apiClient.get<unknown, unknown>(buildTestModePath()),

  setTestMode: (enabled: boolean) =>
    apiClient.post<unknown, unknown>(buildTestModePath(), buildSetTestModeBody(enabled)),

  getTestModeStatus: () =>
    apiClient.get<unknown, unknown>(buildTestModeStatusPath()),
}

// 缺陷字典配置 API
export const defectConfigApi = {
  getDefectDict: () =>
    apiClient.get<unknown, unknown>(buildDefectDictPath()),

  getDefectDictAll: () =>
    apiClient.get<unknown[], unknown[]>(buildDefectDictAllPath()),

  setDefectDict: (data: Record<string, unknown>) =>
    apiClient.post<unknown, unknown>(buildSetDefectDictPath(), data),
}

// 导出数据API
export const exportApi = {
  // 导出最近1小时的数据
  export1h: (exportType?: string) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildExport1hPath(exportType)),

  // 导出最近24小时的数据
  export24h: (exportType?: string) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildExport24hPath(exportType)),

  // 导出今天的数据
  exportToday: (exportType?: string) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildExportTodayPath(exportType)),

  // QML legacy simple export
  exportDataSimple: () =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildExportDataSimplePath()),

  // 按卷号范围导出
  exportXlsxById: (startCoilId: number, endCoilId: number, exportType?: string) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildExportXlsxByIdPath(startCoilId, endCoilId, exportType)),

  // 按时间范围导出
  exportXlsxByDateTime: (start: string, end: string, exportType?: string) =>
    joinBaseUrl(serviceBaseUrls.apiBaseUrl, buildExportXlsxByDateTimePath(start, end, exportType)),

  // 按配置导出
  exportXlsx: (config: ExportXlsxConfig) =>
    apiClient.post<ArrayBuffer, ArrayBuffer>(buildExportXlsxPath(), config, {
      responseType: 'arraybuffer',
    }),

  // 触发浏览器下载
  downloadExport: (url: string) => {
    const iframe = document.createElement('iframe')
    iframe.style.display = 'none'
    iframe.src = url
    document.body.appendChild(iframe)
    setTimeout(() => {
      document.body.removeChild(iframe)
    }, 1000)
  },
}

export default apiClient
