import axios from 'axios'
import type { CoilData, DefectData, HeightLineSegment, ApiResponse, SurfaceKey } from '@/types'

// 创建axios实例
const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
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

function normalizeCoil(item: unknown): CoilData {
  const record = asRecord(item)
  const id = readNumber(record, ['id', 'Id', 'SecondaryCoilId', 'secondaryCoilId'])
  const statusS = readNumber(record, ['statusS', 'Status_S', 'StatusS', 'status_s'])
  const statusL = readNumber(record, ['statusL', 'Status_L', 'StatusL', 'status_l'])
  return {
    id,
    coilNo: readString(record, ['coilNo', 'CoilNo', 'SecondaryCoilId'], String(id || '')),
    dateTime: formatBackendDate(record.dateTime ?? record.DateTime ?? record.CreateTime ?? record.DetectionTime),
    status: Math.max(statusS, statusL, readNumber(record, ['status', 'Status', 'CheckStatus'])),
    surfaceKey: 'S',
    grade: readNumber(record, ['grade', 'Grade']),
    defectCountS: readNumber(record, ['defectCountS', 'DefectCountS']),
    defectCountL: readNumber(record, ['defectCountL', 'DefectCountL']),
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
    defectType: readString(record, ['configDefectName', 'defectName', 'defectType', 'name'], '缺陷'),
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

// 卷材数据API
export const coilApi = {
  // 获取卷材列表
  getCoilList: (number: number = 20) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(`/coilList/${number}`)
      .then((response) => normalizeListResponse(response, normalizeCoil)),

  // 按卷号搜索
  searchByCoilNo: (coilNo: string) =>
    apiClient.get<unknown, unknown>(`/search/coilNo/${coilNo}`).then((response) => normalizeCoil(response)),

  // 按时间范围搜索
  searchByDateTime: (start: string, end: string) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(`/search/DateTime/${start}/${end}`)
      .then((response) => normalizeListResponse(response, normalizeCoil)),
}

// 缺陷数据API
export const defectApi = {
  // 获取缺陷数据
  getDefects: (coilId: number, direction: string) =>
    apiClient
      .get<BackendListResponse<unknown> | unknown[], BackendListResponse<unknown> | unknown[]>(`/search/defects/${coilId}/${direction}`)
      .then((response) => normalizeListResponse(response, normalizeDefect)),
}

// 高度数据API
export const heightDataApi = {
  // 获取高度线数据
  getHeightLine: (surfaceKey: string, coilId: number) =>
    apiClient.get<HeightLineSegment[], HeightLineSegment[]>(
      `/coilData/heightData/${surfaceKey}/${coilId}`
    ),

  // 获取高度点数据
  getHeightPoint: (surfaceKey: string, coilId: number) =>
    apiClient.get<number | string, number | string>(
      `/coilData/heightPoint/${surfaceKey}/${coilId}`
    ),

  // 获取3D渲染数据
  getRenderData: (surfaceKey: string, coilId: number) =>
    apiClient.get<ArrayBuffer, ArrayBuffer>(`/coilData/Render/${surfaceKey}/${coilId}`, {
      responseType: 'arraybuffer',
    }),

  // 获取误差数据
  getErrorData: (surfaceKey: string, coilId: number) =>
    apiClient.get<ArrayBuffer, ArrayBuffer>(`/coilData/Error/${surfaceKey}/${coilId}`, {
      responseType: 'arraybuffer',
    }),
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
  getPreview: (surfaceKey: string, coilId: number, type: string) =>
    `/api/image/preview/${surfaceKey}/${coilId}/${type}`,

  // 获取预览图像（支持动态尺寸）
  getPreviewSized: (
    surfaceKey: string,
    coilId: number,
    type: string,
    size?: ImageSizeParams
  ) =>
    buildImageUrl(
      `/api/image/preview/${surfaceKey}/${coilId}/${type}`,
      size
    ),

  // 获取源图像（固定URL）
  getSource: (surfaceKey: string, coilId: number, type: string) =>
    `/api/image/source/${surfaceKey}/${coilId}/${type}`,

  // 获取源图像（支持动态尺寸）
  getSourceSized: (
    surfaceKey: string,
    coilId: number,
    type: string,
    size?: ImageSizeParams
  ) =>
    buildImageUrl(
      `/api/image/source/${surfaceKey}/${coilId}/${type}`,
      size
    ),

  // 获取区域图像
  getArea: (surfaceKey: string, coilId: number) =>
    `/api/image/area/${surfaceKey}/${coilId}`,

  // 获取区域图像（支持动态尺寸）
  getAreaSized: (
    surfaceKey: string,
    coilId: number,
    size?: ImageSizeParams
  ) =>
    buildImageUrl(
      `/api/image/area/${surfaceKey}/${coilId}`,
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
    h: number
  ) =>
    `/api/defect_image/${surfaceKey}/${coilId}/${type}/${x}/${y}/${w}/${h}`,

  // 获取缺陷区域图像（支持动态尺寸）
  getDefectImageSized: (
    surfaceKey: string,
    coilId: number,
    type: string,
    x: number,
    y: number,
    w: number,
    h: number,
    size?: ImageSizeParams
  ) =>
    buildImageUrl(
      `/api/defect_image/${surfaceKey}/${coilId}/${type}/${x}/${y}/${w}/${h}`,
      size
    ),
}

// PLC数据API
export const plcApi = {
  // 获取PLC曲线数据
  getCurve: (field: string) =>
    apiClient.get<unknown, unknown>(`/plc_curve/${field}`),

  // 获取硬件信息
  getHardware: () =>
    apiClient.get<unknown, unknown>('/hardware'),
}

// 设置与系统信息 API
export const settingsApi = {
  getTestMode: () =>
    apiClient.get<unknown, unknown>('/settings/test_mode'),

  setTestMode: (enabled: boolean) =>
    apiClient.post<unknown, unknown>('/settings/test_mode', { enabled }),

  getTestModeStatus: () =>
    apiClient.get<unknown, unknown>('/settings/test_mode_status'),
}

// 导出数据API
export const exportApi = {
  // 导出最近1小时的数据
  export1h: (exportType?: string) => {
    const params = exportType ? `?export_type=${exportType}` : ''
    return `/api/export_1h${params}`
  },

  // 导出最近24小时的数据
  export24h: (exportType?: string) => {
    const params = exportType ? `?export_type=${exportType}` : ''
    return `/api/export_24h${params}`
  },

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
