import { describe, expect, it } from 'vitest'

import {
  buildAlgTestPayload,
  clampAlgThreshold,
  formatAlgEta,
  formatAlgProgressSocketErrorLog,
  formatAlgTestFailureLog,
  normalizeAlgModels,
  normalizeAlgProgressMessage,
  resolveAlgProgressWsUrl,
} from './algTest'

describe('QML algorithm test helpers', () => {
  it('normalizes QML model list responses and chooses display names', () => {
    expect(
      normalizeAlgModels({
        models: [
          { name: 'detector.pt', type: 'detector' },
          { name: 'cls.json', type: 'classifier', display_name: '分类模型' },
        ],
      }),
    ).toEqual([
      { name: 'detector.pt', type: 'detector', displayName: 'detector.pt' },
      { name: 'cls.json', type: 'classifier', displayName: '分类模型' },
    ])
  })

  it('builds the QML startAlgTest payload and disables labels for classifier models', () => {
    expect(
      buildAlgTestPayload({
        model: { name: 'cls.json', type: 'classifier', displayName: '分类模型' },
        targetFolder: 'D:\\images',
        outputFolder: 'D:\\out',
        threshold: 1.8,
        mode: 'move',
        classifySave: true,
        saveLabel: true,
      }),
    ).toEqual({
      model: 'cls.json',
      target: 'D:\\images',
      output: 'D:\\out',
      threshold: 0.99,
      mode: 'move',
      options: {
        classify_save: true,
        save_label: false,
      },
    })
  })

  it('parses QML websocket progress text into stable UI state fields', () => {
    expect(
      normalizeAlgProgressMessage(
        JSON.stringify({
          task_id: 'alg-1',
          speed: '2.5',
          done: 4,
          total: 10,
          eta: 65,
          message: '处理完成',
          status: '运行中',
          summary: { normal: 3, empty: 1 },
          finished: false,
        }),
      ),
    ).toEqual({
      taskId: 'alg-1',
      speed: 2.5,
      done: 4,
      total: 10,
      eta: 65,
      message: '处理完成',
      status: '运行中',
      summary: { normal: 3, empty: 1 },
      finished: false,
    })
  })

  it('matches QML threshold and ETA display rules', () => {
    expect(clampAlgThreshold(Number.NaN)).toBe(0.4)
    expect(clampAlgThreshold(0)).toBe(0.01)
    expect(clampAlgThreshold(5)).toBe(0.99)
    expect(formatAlgEta(0)).toBe('计算中')
    expect(formatAlgEta(59.9)).toBe('59秒')
    expect(formatAlgEta(65)).toBe('1分5秒')
    expect(formatAlgEta(3662)).toBe('1小时1分')
  })

  it('formats algorithm-test failure logs with QML error detail text', () => {
    expect(formatAlgTestFailureLog('启动失败', '目录不存在')).toBe('启动失败: 目录不存在')
    expect(formatAlgTestFailureLog('停止失败', new Error('任务 ID 不匹配'))).toBe('停止失败: 任务 ID 不匹配')
    expect(formatAlgTestFailureLog('启动失败', null)).toBe('启动失败')
  })

  it('formats QML-style progress websocket error logs with available error detail', () => {
    expect(formatAlgProgressSocketErrorLog({ message: 'connection refused' })).toBe(
      '进度连接错误: connection refused',
    )
    expect(formatAlgProgressSocketErrorLog({ reason: 'server closed' })).toBe('进度连接错误: server closed')
    expect(formatAlgProgressSocketErrorLog({ type: 'error' })).toBe('进度连接错误')
  })

  it('resolves websocket progress URLs for Vite proxy and direct API bases', () => {
    expect(resolveAlgProgressWsUrl('/api', '/ws/alg_2d/test/progress', 'http://127.0.0.1:3015')).toBe(
      'ws://127.0.0.1:3015/ws/alg_2d/test/progress',
    )
    expect(resolveAlgProgressWsUrl('http://127.0.0.1:5011', '/ws/alg_2d/test/progress')).toBe(
      'ws://127.0.0.1:5011/ws/alg_2d/test/progress',
    )
    expect(resolveAlgProgressWsUrl('ws://127.0.0.1:5011', '/ws/alg_2d/test/progress')).toBe(
      'ws://127.0.0.1:5011/ws/alg_2d/test/progress',
    )
  })
})
