import { describe, expect, it } from 'vitest'

import {
  buildApiDelayView,
  buildOperationSidebarAlarmRows,
  buildQmlGlobalServerMsgRows,
  readImageServiceHealthOk,
} from './serviceConnection'

describe('QML API delay status helpers', () => {
  it('maps measured delay to QML connection colors', () => {
    expect(buildApiDelayView(42)).toEqual({
      label: 'API 42ms',
      state: 'ok',
      title: 'API 服务延迟 42ms',
    })
    expect(buildApiDelayView(200)).toEqual({
      label: 'API 200ms',
      state: 'warn',
      title: 'API 服务延迟 200ms',
    })
    expect(buildApiDelayView(-1)).toEqual({
      label: 'API 离线',
      state: 'error',
      title: 'API 服务连接失败',
    })
  })

  it('uses the QML red state before a delay sample is available', () => {
    expect(buildApiDelayView(undefined)).toEqual({
      label: 'API 未连接',
      state: 'error',
      title: 'API 服务尚未完成延迟检测',
    })
  })

  it('builds the QML GlobalServerMsg service socket rows with stable service keys', () => {
    expect(
      buildQmlGlobalServerMsgRows({
        label: 'API 42ms',
        state: 'ok',
        title: 'API 服务延迟 42ms',
      }),
    ).toEqual([
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
        label: 'API 42ms',
        state: 'ok',
        title: 'API 服务延迟 42ms',
      },
    ])
  })

  it('maps image-service health into the OperationSidebar alarm row instead of a static pending label', () => {
    expect(buildOperationSidebarAlarmRows({ imageHealthOk: true }).map((row) => `${row.state}:${row.label}`)).toEqual([
      'ok:PLC 通信正常',
      'ok:Redis 缓存在线',
      'ok:图像服务在线',
    ])

    expect(buildOperationSidebarAlarmRows({ imageHealthOk: false })[2]).toEqual({
      key: 'image',
      label: '图像服务离线',
      state: 'error',
      title: '图像服务 health 检查失败',
    })

    expect(buildOperationSidebarAlarmRows({ imageHealthOk: undefined })[2]).toMatchObject({
      key: 'image',
      label: '图像服务待确认',
      state: 'warn',
    })
  })

  it('accepts Rust image-service and main-API health payloads for the sidebar image alarm', () => {
    expect(readImageServiceHealthOk({ status: 'ok', service: 'rust_image_service' })).toBe(true)
    expect(readImageServiceHealthOk({ status: 'ok', service: 'rust_api_service' })).toBe(true)
    expect(readImageServiceHealthOk({ status: 'error' })).toBe(false)
    expect(readImageServiceHealthOk(null)).toBe(false)
  })
})
