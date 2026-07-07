export interface CameraAdjustmentRow {
  key: string
  name: string
  sn: string
  serviceUrl: string
  ok: boolean
  connected: boolean
  writable: boolean
  message: string
  source: string
  paramFile: string
  lastFrameAge: number
  lastFrameAge3D: number
  lastError3D: string
  captureRunning: boolean
  serviceReady: boolean
  exposureTime: number
  gain: number
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readString(record: Record<string, unknown>, key: string): string {
  const value = record[key]
  return value === undefined || value === null ? '' : String(value)
}

function readNumber(record: Record<string, unknown>, key: string): number {
  const value = Number(record[key])
  return Number.isFinite(value) ? value : 0
}

function readBoolean(record: Record<string, unknown>, key: string, fallback = false): boolean {
  const value = record[key]
  return typeof value === 'boolean' ? value : fallback
}

export function formatCameraFrameAge(value: number): string {
  return Number.isFinite(value) ? `${value.toFixed(1)} s` : '-'
}

export function buildCameraAdjustmentRows(payload: unknown): CameraAdjustmentRow[] {
  const cameras = asRecord(payload).cameras
  if (!Array.isArray(cameras)) return []

  return cameras.map((item) => {
    const camera = asRecord(item)
    const status = asRecord(camera.status)
    const capture = asRecord(status.capture)
    const params = asRecord(status.params)

    return {
      key: readString(camera, 'key'),
      name: readString(camera, 'name'),
      sn: readString(camera, 'sn'),
      serviceUrl: readString(camera, 'serviceUrl'),
      ok: readBoolean(status, 'ok'),
      connected: readBoolean(status, 'connected'),
      writable: readBoolean(status, 'writable'),
      message: readString(status, 'message'),
      source: readString(status, 'source'),
      paramFile: readString(status, 'paramFile'),
      lastFrameAge: readNumber(status, 'lastFrameAge'),
      lastFrameAge3D: readNumber(status, 'lastFrameAge3D'),
      lastError3D: readString(status, 'lastError3D'),
      captureRunning: readBoolean(capture, 'captureRunning'),
      serviceReady: readBoolean(capture, 'serviceReady', true),
      exposureTime: readNumber(params, 'exposureTime'),
      gain: readNumber(params, 'gain'),
    }
  })
}
