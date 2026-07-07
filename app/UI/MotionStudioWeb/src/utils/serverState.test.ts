import { describe, expect, it } from 'vitest'

import {
  buildServerStateRows,
  buildServerStateSummary,
  parseServerStateWebSocketMessage,
  resolveServerStateWsUrl,
} from './serverState'

describe('server state helpers', () => {
  it('maps Python/QML message objects into scan-friendly rows', () => {
    expect(
      buildServerStateRows([
        {
          key: '算法',
          value: '运行',
          msg: '检测线程已启动',
          level: 1,
        },
        {
          name: 'PLC',
          state: '异常',
          message: 'PLC 连接超时',
          level: '3',
        },
      ]),
    ).toEqual([
      {
        key: '算法',
        title: '算法',
        value: '运行',
        message: '检测线程已启动',
        level: 1,
        color: 'success',
      },
      {
        key: 'PLC',
        title: 'PLC',
        value: '异常',
        message: 'PLC 连接超时',
        level: 3,
        color: 'error',
      },
    ])
  })

  it('keeps useful rows for string messages and object maps', () => {
    expect(buildServerStateRows(['相机等待触发'])[0]).toMatchObject({
      key: '0',
      title: '状态 1',
      value: '相机等待触发',
      message: '相机等待触发',
      level: 1,
    })

    expect(
      buildServerStateRows({
        runtime: {
          title: '运行时',
          value: true,
          msg: 'ready',
        },
      }),
    ).toEqual([
      {
        key: 'runtime',
        title: '运行时',
        value: 'true',
        message: 'ready',
        level: 1,
        color: 'success',
      },
    ])
  })

  it('summarizes empty, normal, and abnormal server states', () => {
    expect(buildServerStateSummary([])).toEqual({
      label: '暂无检测状态',
      color: 'default',
      total: 0,
      abnormal: 0,
    })

    expect(buildServerStateSummary([{ level: 1 }, { level: 2 }, { level: 3 }])).toEqual({
      label: '2 项异常',
      color: 'error',
      total: 3,
      abnormal: 2,
    })
  })

  it('parses QML websocket server-state messages with safe empty fallback', () => {
    expect(
      parseServerStateWebSocketMessage(
        JSON.stringify([
          { key: '相机', value: '运行', msg: 'ready', level: 1 },
          ['PLC', '异常'],
        ]),
      ),
    ).toEqual([
      { key: '相机', value: '运行', msg: 'ready', level: 1 },
      ['PLC', '异常'],
    ])

    expect(parseServerStateWebSocketMessage('not-json')).toEqual([])
  })

  it('resolves DetectionState websocket URLs through the Vite proxy or a direct API base', () => {
    expect(resolveServerStateWsUrl('/api', '/ws/DetectionState', 'http://127.0.0.1:3015')).toBe(
      'ws://127.0.0.1:3015/ws/DetectionState',
    )
    expect(resolveServerStateWsUrl('http://127.0.0.1:5011', '/ws/DetectionState')).toBe(
      'ws://127.0.0.1:5011/ws/DetectionState',
    )
    expect(resolveServerStateWsUrl('ws://127.0.0.1:5011', '/ws/DetectionState')).toBe(
      'ws://127.0.0.1:5011/ws/DetectionState',
    )
  })
})
