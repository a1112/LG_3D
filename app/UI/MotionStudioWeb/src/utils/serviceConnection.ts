export type ApiDelayState = 'ok' | 'warn' | 'error'

export interface ApiDelayView {
  label: string
  state: ApiDelayState
  title: string
}

export interface QmlGlobalServerMsgRow {
  key: 'plc' | 'redis' | 'api'
  label: string
  state: ApiDelayState
  title: string
}

export interface OperationSidebarAlarmRow {
  key: 'plc' | 'redis' | 'image'
  label: string
  state: ApiDelayState
  title: string
}

export function buildApiDelayView(delayMs: number | undefined): ApiDelayView {
  if (delayMs === undefined) {
    return {
      label: 'API 未连接',
      state: 'error',
      title: 'API 服务尚未完成延迟检测',
    }
  }

  if (delayMs <= 0) {
    return {
      label: 'API 离线',
      state: 'error',
      title: 'API 服务连接失败',
    }
  }

  const label = `API ${delayMs}ms`
  return {
    label,
    state: delayMs < 200 ? 'ok' : 'warn',
    title: `API 服务延迟 ${delayMs}ms`,
  }
}

export function buildQmlGlobalServerMsgRows(apiDelayView: ApiDelayView): QmlGlobalServerMsgRow[] {
  return [
    {
      key: 'plc',
      label: 'PLC',
      state: 'ok',
      title: 'PLC 通信正常',
    },
    {
      key: 'redis',
      label: 'Redis',
      state: 'ok',
      title: 'Redis 缓存在线',
    },
    {
      key: 'api',
      label: apiDelayView.label,
      state: apiDelayView.state,
      title: apiDelayView.title,
    },
  ]
}

export function readImageServiceHealthOk(payload: unknown): boolean {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return false

  return (payload as Record<string, unknown>).status === 'ok'
}

export function buildOperationSidebarAlarmRows(input: { imageHealthOk?: boolean } = {}): OperationSidebarAlarmRow[] {
  const imageRow =
    input.imageHealthOk === undefined
      ? {
          label: '图像服务待确认',
          state: 'warn' as const,
          title: '图像服务尚未完成 health 检查',
        }
      : input.imageHealthOk
        ? {
            label: '图像服务在线',
            state: 'ok' as const,
            title: '图像服务 health 检查正常',
          }
        : {
            label: '图像服务离线',
            state: 'error' as const,
            title: '图像服务 health 检查失败',
          }

  return [
    {
      key: 'plc',
      label: 'PLC 通信正常',
      state: 'ok',
      title: 'PLC 通信正常',
    },
    {
      key: 'redis',
      label: 'Redis 缓存在线',
      state: 'ok',
      title: 'Redis 缓存在线',
    },
    {
      key: 'image',
      ...imageRow,
    },
  ]
}
