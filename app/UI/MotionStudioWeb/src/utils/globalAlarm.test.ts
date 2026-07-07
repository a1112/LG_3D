import { describe, expect, it } from 'vitest'

import {
  buildGlobalAlarmNetworkProbeTargets,
  buildGlobalAlarmViewModel,
  measureGlobalAlarmNetworkDelays,
} from './globalAlarm'

describe('buildGlobalAlarmViewModel', () => {
  it('maps QML global alarm camera and hardware sections', () => {
    const viewModel = buildGlobalAlarmViewModel({
      cameraAlarm: {
        S_D: { cameraKey: 'Cap_S_D', cameraName: '入口相机', level: 3, msg: '2D相机采集异常' },
        camera2: { level: 1, msg: 'ok' },
      },
      hardware: {
        cpu: { key: 'CPU', value: '48.0%', level: 1, msg: 'CPU 使用率: 48.0%' },
        disk: { key: '硬盘', value: '92.0%', level: 3, msg: '磁盘空间不足' },
      },
      networkPorts: {
        capture: 6001,
        data: 6005,
        threeD: 6005,
        plc: 6005,
      },
    })

    expect(viewModel.cameras).toMatchObject([
      { key: 'S_D', title: 'S_D', value: '异常', level: 3, message: '2D相机采集异常' },
      { key: 'camera2', title: 'camera2', value: '正常', level: 1, message: 'ok' },
    ])
    expect(viewModel.networks.map((item) => `${item.title}:${item.port}`)).toEqual([
      '采集服务:6001',
      '数据服务:6005',
      '3D服务:6005',
      'PLC服务:6005',
    ])
    expect(viewModel.hardware).toEqual([
      { key: 'cpu', title: 'CPU', value: '48.0%', level: 1, message: 'CPU 使用率: 48.0%' },
      { key: 'disk', title: '硬盘', value: '92.0%', level: 1, message: '磁盘空间不足' },
    ])
    expect(viewModel.maxLevel).toBe(3)
  })

  it('keeps QML hardware cards at the delegate default level even when the backend sends levels', () => {
    const viewModel = buildGlobalAlarmViewModel({
      hardware: {
        disk: { key: '硬盘', value: '96.0%', level: 3, msg: '磁盘空间不足' },
        memory: { key: '内存', value: '88.0%', level: 2, msg: '内存偏高' },
      },
    })

    expect(viewModel.hardware).toEqual([
      { key: 'disk', title: '硬盘', value: '96.0%', level: 1, message: '磁盘空间不足' },
      { key: 'memory', title: '内存', value: '88.0%', level: 1, message: '内存偏高' },
    ])
    expect(viewModel.maxLevel).toBe(1)
  })

  it('falls back to normal empty sections when sources are absent', () => {
    expect(buildGlobalAlarmViewModel({})).toMatchObject({
      cameras: [],
      hardware: [],
      maxLevel: 1,
    })
  })

  it('uses QML CoreSetting default network ports when no overrides are provided', () => {
    const viewModel = buildGlobalAlarmViewModel({})
    const targets = buildGlobalAlarmNetworkProbeTargets({
      apiBaseUrl: 'http://127.0.0.1:5011/api',
    })

    expect(viewModel.networks.map((item) => `${item.title}:${item.port}`)).toEqual([
      '采集服务:6011',
      '数据服务:6011',
      '3D服务:6013',
      'PLC服务:6014',
    ])
    expect(targets.map((target) => `${target.key}:${target.delayUrl}`)).toEqual([
      'capture:http://127.0.0.1:6011/delay',
      'data:http://127.0.0.1:6011/delay',
      'threeD:http://127.0.0.1:6013/delay',
      'plc:http://127.0.0.1:6014/delay',
    ])
  })

  it('maps QML network delay samples into live network card values', () => {
    const viewModel = buildGlobalAlarmViewModel({
      networkDelay: {
        capture: { ok: true, delayMs: 42 },
        data: { ok: false, delayMs: 9 },
        threeD: { ok: true, delayMs: 250 },
      },
    })

    expect(viewModel.networks).toMatchObject([
      { key: 'capture', value: '42 ms', level: 1 },
      { key: 'data', value: '连接错误', level: 3 },
      { key: 'threeD', value: '250 ms', level: 1 },
      { key: 'plc', value: '待检测', level: 1 },
    ])
    expect(viewModel.maxLevel).toBe(3)
  })

  it('adds current API docs links to QML network status cards', () => {
    const viewModel = buildGlobalAlarmViewModel({
      networkDocsUrl: '/api/docs',
    })

    expect(viewModel.networks.map((item) => item.docsUrl)).toEqual([
      '/api/docs',
      '/api/docs',
      '/api/docs',
      '/api/docs',
    ])
  })

  it('builds QML api.openApi(port) docs links per network service port', () => {
    const viewModel = buildGlobalAlarmViewModel({
      networkRemoteHost: 'http://192.168.2.10:5011/api',
      networkPorts: {
        capture: 6001,
        data: 6005,
        threeD: 5011,
        plc: 6013,
      },
    })

    expect(viewModel.networks.map((item) => `${item.title}:${item.docsUrl}`)).toEqual([
      '采集服务:http://192.168.2.10:6001/docs',
      '数据服务:http://192.168.2.10:6005/docs',
      '3D服务:http://192.168.2.10:5011/docs',
      'PLC服务:http://192.168.2.10:6013/docs',
    ])
  })

  it('exposes the QML network-card context actions for each service', () => {
    const viewModel = buildGlobalAlarmViewModel({
      networkRemoteHost: 'http://192.168.2.10:5011/api',
      networkPorts: {
        capture: 6001,
      },
    })

    expect(viewModel.networks[0].actions).toEqual([
      {
        id: 'openApiDocs',
        label: '打开接口文档',
        enabled: true,
        status: '可用',
        href: 'http://192.168.2.10:6001/docs',
      },
      {
        id: 'restartService',
        label: '重启服务',
        enabled: false,
        status: '待接入',
      },
    ])
  })

  it('exposes the QML camera-card context actions for each camera', () => {
    const viewModel = buildGlobalAlarmViewModel({
      cameraAlarm: {
        S_D: { cameraKey: 'Cap_S_D', cameraName: '入口相机', level: 1, msg: 'ok' },
      },
    })

    expect(viewModel.cameras[0]).toMatchObject({
      actions: [
        {
          id: 'openCurrentCoilCameraData',
          label: '打开当前卷相机数据',
          enabled: true,
          status: '可用',
        },
        {
          id: 'openRawDataSavePath',
          label: '打开原始数据保存路径',
          enabled: true,
          status: '可用',
        },
        {
          id: 'restartCamera',
          label: '重启相机',
          enabled: true,
          status: '可用',
        },
      ],
    })
  })

  it('uses the QML injected camera Key for the card title and data lookup key', () => {
    const viewModel = buildGlobalAlarmViewModel({
      cameraAlarm: {
        S_D: { cameraKey: 'Cap_S_D', cameraName: '入口相机', Key: 'QML_S_D', level: 1 },
        L_D: { cameraKey: 'Cap_L_D', cameraName: '出口相机', level: 3 },
      },
    })

    expect(viewModel.cameras.map((item) => `${item.key}:${item.title}`)).toEqual([
      'QML_S_D:QML_S_D',
      'L_D:L_D',
    ])
  })

  it('adds the QML network header remote desktop action with a sanitized host', () => {
    const viewModel = buildGlobalAlarmViewModel({
      networkRemoteHost: 'http://192.168.2.10:5011/api',
    })

    expect(viewModel.networkHeaderActions).toEqual([
      {
        id: 'remoteDesktop',
        label: '远程到服务器',
        enabled: true,
        status: '可用',
        commandPreview: 'mstsc /v 192.168.2.10',
      },
    ])
  })

  it('keeps the QML network header remote action disabled when the host is unsafe', () => {
    const viewModel = buildGlobalAlarmViewModel({
      networkRemoteHost: 'http://server.local;shutdown:5011',
    })

    expect(viewModel.networkHeaderActions).toEqual([
      {
        id: 'remoteDesktop',
        label: '远程到服务器',
        enabled: false,
        status: '待接入',
        commandPreview: 'mstsc /v <server>',
      },
    ])
  })

  it('builds QML-style per-port delay probes from the current API host', () => {
    const targets = buildGlobalAlarmNetworkProbeTargets({
      apiBaseUrl: 'http://192.168.2.10:5011/api',
      networkPorts: {
        capture: 6001,
        data: 6005,
        threeD: 5011,
        plc: 6013,
      },
    })

    expect(targets.map((target) => `${target.key}:${target.delayUrl}`)).toEqual([
      'capture:http://192.168.2.10:6001/delay',
      'data:http://192.168.2.10:6005/delay',
      'threeD:http://192.168.2.10:5011/delay',
      'plc:http://192.168.2.10:6013/delay',
    ])
  })

  it('measures QML network delay probes independently per service', async () => {
    let now = 100
    const samples = await measureGlobalAlarmNetworkDelays(
      [
        { key: 'capture', title: '采集服务', port: 6001, delayUrl: 'http://127.0.0.1:6001/delay' },
        { key: 'data', title: '数据服务', port: 6005, delayUrl: 'http://127.0.0.1:6005/delay' },
      ],
      async (url) => {
        now += 7
        if (url.includes(':6005')) throw new Error('connection refused')
        return { ok: true }
      },
      () => now,
    )

    expect(samples).toEqual({
      capture: { ok: true, delayMs: 7 },
      data: { ok: false, delayMs: 7 },
    })
  })

  it('adds an abort signal to QML network delay probes so offline ports do not stay pending', async () => {
    const initArgs: RequestInit[] = []

    await measureGlobalAlarmNetworkDelays(
      [{ key: 'capture', title: '采集服务', port: 6001, delayUrl: 'http://127.0.0.1:6001/delay' }],
      async (_url, init) => {
        initArgs.push(init || {})
        return { ok: true }
      },
      () => 100,
      750,
    )

    expect(initArgs).toHaveLength(1)
    expect(initArgs[0].signal).toBeInstanceOf(AbortSignal)
  })
})
