import { describe, expect, it } from 'vitest'

import {
  buildCoilListReDetectionRange,
  buildReDetectionWebSocketStartMessage,
  buildReDetectionStatusView,
  normalizeReDetectionRange,
  parseReDetectionWebSocketMessage,
  resolveReDetectionWsUrl,
} from './reDetection'

describe('reDetection helpers', () => {
  it('maps QML-compatible running and finished status messages', () => {
    expect(
      buildReDetectionStatusView({
        running: true,
        progress: 0.428,
        total: 12,
        pending: 7,
      }),
    ).toEqual({
      running: true,
      canChange: false,
      showProgress: true,
      progress: 0.428,
      percent: 43,
      total: 12,
      pending: 7,
      label: '运行...',
      color: 'processing',
    })

    expect(
      buildReDetectionStatusView({
        running: false,
        progress: 1,
        total: 12,
        pending: 0,
      }),
    ).toMatchObject({
      canChange: false,
      showProgress: true,
      percent: 100,
      label: '运行完成',
      color: 'success',
    })
  })

  it('keeps QML-compatible defaults for idle and error states', () => {
    expect(buildReDetectionStatusView({})).toMatchObject({
      running: false,
      canChange: true,
      showProgress: false,
      percent: 0,
      total: 0,
      pending: 0,
      label: '未运行',
      color: 'default',
    })
    expect(buildReDetectionStatusView({ error: '连接断开!' })).toMatchObject({
      canChange: false,
      showProgress: false,
      label: '运行失败',
      color: 'error',
      error: '连接断开!',
    })
  })

  it('normalizes operator-entered ranges and current-list ranges', () => {
    expect(normalizeReDetectionRange({ fromId: 0, toId: 0 }, 193113)).toEqual({
      fromId: 193113,
      toId: 193113,
    })
    expect(normalizeReDetectionRange({ fromId: 90.8, toId: 80.2 })).toEqual({
      fromId: 80,
      toId: 90,
    })
    expect(buildCoilListReDetectionRange([{ id: 120 }, { id: 118 }, { id: 121 }])).toEqual({
      fromId: 118,
      toId: 121,
    })
  })

  it('parses QML websocket status messages and keeps malformed messages running', () => {
    const parsed = parseReDetectionWebSocketMessage(
      JSON.stringify({
        from_id: 100,
        to_id: 102,
        running: true,
        progress: 0.5,
        total: 3,
        pending: 2,
      }),
    )

    expect(parsed).toMatchObject({
      from_id: 100,
      to_id: 102,
      running: true,
      progress: 0.5,
      total: 3,
      pending: 2,
    })
    expect(parsed.__fromWebSocket).toBe(true)

    expect(buildReDetectionStatusView(parseReDetectionWebSocketMessage('not-json'))).toMatchObject({
      running: true,
      label: '运行...',
      color: 'processing',
    })
  })

  it('keeps non-error QML websocket messages running until total work is finished', () => {
    expect(
      buildReDetectionStatusView(
        parseReDetectionWebSocketMessage(
          JSON.stringify({
            progress: 0.2,
            total: 10,
            pending: 4,
          }),
        ),
      ),
    ).toMatchObject({
      running: true,
      canChange: false,
      showProgress: true,
      percent: 20,
      label: '运行...',
      color: 'processing',
    })

    expect(
      buildReDetectionStatusView(
        parseReDetectionWebSocketMessage(
          JSON.stringify({
            running: false,
            progress: 0.8,
            total: 10,
            pending: 2,
          }),
        ),
      ),
    ).toMatchObject({
      running: true,
      canChange: false,
      showProgress: true,
      percent: 80,
      label: '运行...',
      color: 'processing',
    })
  })

  it('keeps the websocket source marker internal so diagnostics JSON does not expose it', () => {
    const parsed = parseReDetectionWebSocketMessage(
      JSON.stringify({
        progress: 0.2,
        total: 10,
        pending: 4,
      }),
    )

    expect(parsed.__fromWebSocket).toBe(true)
    expect(JSON.stringify(parsed)).not.toContain('__fromWebSocket')
  })

  it('resolves QML websocket URLs through the Vite proxy or a direct API base', () => {
    expect(resolveReDetectionWsUrl('/api', '/ws/reDetection', 'http://127.0.0.1:3015')).toBe(
      'ws://127.0.0.1:3015/ws/reDetection',
    )
    expect(resolveReDetectionWsUrl('http://127.0.0.1:5011', '/ws/reDetection')).toBe(
      'ws://127.0.0.1:5011/ws/reDetection',
    )
    expect(resolveReDetectionWsUrl('ws://127.0.0.1:5011', '/ws/reDetection')).toBe(
      'ws://127.0.0.1:5011/ws/reDetection',
    )
  })

  it('builds the QML websocket start payload with snake_case ids and optional folder', () => {
    expect(JSON.parse(buildReDetectionWebSocketStartMessage({ fromId: 42.9, toId: 44.1 }))).toEqual({
      from_id: 42,
      to_id: 44,
    })
    expect(
      JSON.parse(buildReDetectionWebSocketStartMessage({ fromId: 42, toId: 44 }, ' D:/output/recheck ')),
    ).toEqual({
      from_id: 42,
      to_id: 44,
      folder: 'D:/output/recheck',
    })
  })
})
