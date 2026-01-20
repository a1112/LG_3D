import axios from 'axios'
import type { CoilData, DefectData, HeightLineData, ApiResponse } from '@/types'

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

// 卷材数据API
export const coilApi = {
  // 获取卷材列表
  getCoilList: (number: number = 20) =>
    apiClient.get<ApiResponse<CoilData[]>>(`/coilList/${number}`),

  // 按卷号搜索
  searchByCoilNo: (coilNo: string) =>
    apiClient.get<ApiResponse<CoilData>>(`/search/coilNo/${coilNo}`),

  // 按时间范围搜索
  searchByDateTime: (start: string, end: string) =>
    apiClient.get<ApiResponse<CoilData[]>>(`/search/DateTime/${start}/${end}`),
}

// 缺陷数据API
export const defectApi = {
  // 获取缺陷数据
  getDefects: (coilId: number, direction: string) =>
    apiClient.get<ApiResponse<DefectData[]>>(`/search/defects/${coilId}/${direction}`),
}

// 高度数据API
export const heightDataApi = {
  // 获取高度线数据
  getHeightLine: (surfaceKey: string, coilId: number) =>
    apiClient.get<ApiResponse<HeightLineData>>(`/coilData/heightData/${surfaceKey}/${coilId}`),

  // 获取高度点数据
  getHeightPoint: (surfaceKey: string, coilId: number) =>
    apiClient.get<ApiResponse<HeightLineData>>(`/coilData/heightPoint/${surfaceKey}/${coilId}`),

  // 获取3D渲染数据
  getRenderData: (surfaceKey: string, coilId: number) =>
    apiClient.get(`/coilData/Render/${surfaceKey}/${coilId}`, {
      responseType: 'arraybuffer',
    }),

  // 获取误差数据
  getErrorData: (surfaceKey: string, coilId: number) =>
    apiClient.get(`/coilData/Error/${surfaceKey}/${coilId}`, {
      responseType: 'arraybuffer',
    }),
}

// 图像API
export const imageApi = {
  // 获取预览图像
  getPreview: (surfaceKey: string, coilId: number, type: string) =>
    `/api/image/preview/${surfaceKey}/${coilId}/${type}`,

  // 获取源图像
  getSource: (surfaceKey: string, coilId: number, type: string) =>
    `/api/image/source/${surfaceKey}/${coilId}/${type}`,

  // 获取区域图像
  getArea: (surfaceKey: string, coilId: number) =>
    `/api/image/area/${surfaceKey}/${coilId}`,

  // 获取缺陷区域图像
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
}

// PLC数据API
export const plcApi = {
  // 获取PLC曲线数据
  getCurve: (field: string) =>
    apiClient.get(`/plc_curve/${field}`),

  // 获取硬件信息
  getHardware: () =>
    apiClient.get('/hardware'),
}

export default apiClient
