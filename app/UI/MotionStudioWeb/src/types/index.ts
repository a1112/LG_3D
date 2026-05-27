// 卷材数据类型
export interface CoilData {
  id: number
  coilNo: string
  dateTime: string
  status: number
  surfaceKey: string
  // 其他字段...
}

// 缺陷数据类型
export interface DefectData {
  id: number
  coilId: number
  defectType: string
  position: { x: number; y: number }
  size: { width: number; height: number }
  confidence: number
  description?: string
}

// 高度点数据类型
export interface HeightPoint {
  x: number
  y: number
  z: number
}

export type HeightPointTuple = [number, number, number]
export type HeightEndpoint = [number, number]

// 后端 /coilData/heightData 返回的线段数据
export interface HeightLineSegment {
  pointL: HeightEndpoint
  pointR: HeightEndpoint
  points: HeightPointTuple[]
}

// API响应类型
export interface ApiResponse<T> {
  code: number
  data: T
  message?: string
}

// 表面键类型
export type SurfaceKey = 'top' | 'bottom' | 'left' | 'right'

// 卷材状态
export enum CoilStatus {
  Unknown = 0,
  Processing = 1,
  Completed = 2,
  Error = 3,
}
