import { describe, expect, it } from 'vitest'

import {
  buildRemoteServiceDocsUrl,
  buildRemoteServiceRows,
  buildMaintenanceToolGroups,
  normalizeMaintenanceHost,
  type MaintenanceActionId,
} from './maintenanceTools'

describe('maintenance tool helpers', () => {
  it('matches QML maintenance actions and command previews for a server host', () => {
    const groups = buildMaintenanceToolGroups('192.168.1.20')
    const maintenance = groups.find((group) => group.key === 'maintenance')

    expect(maintenance?.title).toBe('维护')
    expect(maintenance?.actions.map((action) => action.id)).toEqual([
      'remoteDesktop',
      'pingServer',
      'restore',
      'restartAllServices',
      'serviceManagement',
      'restartServer',
    ] satisfies MaintenanceActionId[])
    expect(maintenance?.actions[0]).toMatchObject({
      id: 'remoteDesktop',
      label: '远程到服务器',
      commandPreview: 'mstsc /v 192.168.1.20',
      enabled: true,
      sideEffect: 'externalProcess',
    })
    expect(maintenance?.actions[1]).toMatchObject({
      id: 'pingServer',
      label: 'Ping 服务器',
      commandPreview: 'ping 192.168.1.20 -t',
      enabled: true,
      sideEffect: 'externalProcess',
    })
  })

  it('mirrors QML feature submenus and keeps exit as a top-level system action', () => {
    const groups = buildMaintenanceToolGroups('127.0.0.1')
    const feature = groups.find((group) => group.key === 'feature')
    const system = groups.find((group) => group.key === 'system')

    expect(groups.map((group) => `${group.key}:${group.title}`)).toEqual(['maintenance:维护', 'feature:功能', 'system:系统'])
    expect(feature?.title).toBe('功能')
    expect(feature?.actions.map((action) => `${action.parentLabel}/${action.label}:${action.enabled}`)).toEqual([
      '数据库备份/备份到 ...:true',
      '数据库备份/从 备份 恢复:false',
      '测试/网络测速:true',
    ])
    expect(feature?.actions.find((action) => action.id === 'networkSpeedtest')).toMatchObject({
      enabled: true,
      status: '可用',
      sideEffect: 'navigation',
    })
    expect(feature?.actions.find((action) => action.id === 'restoreFromBackup')).toMatchObject({
      enabled: false,
      status: '待接入',
    })
    expect(system?.actions.map((action) => `${action.label}:${action.enabled}:${action.sideEffect}`)).toEqual([
      '退出系统:true:windowClose',
    ])
    expect(groups.flatMap((group) => group.actions).find((action) => action.id === 'restartServer')).toMatchObject({
      enabled: false,
      status: '待接入',
    })
  })

  it('opens service management as a read-only QML remote-service popup model', () => {
    const actions = buildMaintenanceToolGroups('127.0.0.1').flatMap((group) => group.actions)

    expect(actions.find((action) => action.id === 'serviceManagement')).toMatchObject({
      enabled: true,
      label: '服务管理',
      sideEffect: 'modal',
      status: '可用',
    })
    expect(buildRemoteServiceRows().map((row) => `${row.title}:${row.port}`)).toEqual([
      '采集服务:6011',
      '数据服务:6011',
      '3D服务:6013',
      'PLC服务:6014',
    ])
  })

  it('uses configured QML service ports in the remote-service popup model without tying PLC to data', () => {
    expect(
      buildRemoteServiceRows({ databasPort: 6121, dataPort: 6123, plcPort: 6124 }).map((row) => `${row.title}:${row.port}`),
    ).toEqual([
      '采集服务:6121',
      '数据服务:6121',
      '3D服务:6123',
      'PLC服务:6124',
    ])
  })

  it('builds QML openApi docs URLs for each remote service port', () => {
    expect(buildRemoteServiceDocsUrl(6121, '192.168.1.20')).toBe('http://192.168.1.20:6121/docs')
    expect(
      buildRemoteServiceRows({ host: '192.168.1.20', databasPort: 6121, dataPort: 6123, plcPort: 6124 }).map(
        (row) => row.docsUrl,
      ),
    ).toEqual([
      'http://192.168.1.20:6121/docs',
      'http://192.168.1.20:6121/docs',
      'http://192.168.1.20:6123/docs',
      'http://192.168.1.20:6124/docs',
    ])
  })

  it('mirrors the QML service row context actions without enabling unsafe restarts', () => {
    const rows = buildRemoteServiceRows({ host: '192.168.1.20', databasPort: 6121, dataPort: 6123 })

    expect(rows[0].actions).toEqual([
      {
        id: 'openApiDocs',
        label: '打开接口文档',
        enabled: true,
        href: 'http://192.168.1.20:6121/docs',
        status: '可用',
      },
      {
        id: 'restartService',
        label: '重启服务',
        enabled: false,
        status: '待接入',
      },
    ])
    expect(rows.every((row) => row.actions.some((action) => action.id === 'restartService' && !action.enabled))).toBe(
      true,
    )
  })

  it('normalizes hosts for display and disables external commands when host is invalid', () => {
    expect(normalizeMaintenanceHost(' http://127.0.0.1:5011/path ')).toBe('127.0.0.1')
    expect(normalizeMaintenanceHost('bad host && del C:\\')).toBe('')

    const actions = buildMaintenanceToolGroups('bad host && del C:\\').flatMap((group) => group.actions)
    expect(actions.find((action) => action.id === 'remoteDesktop')).toMatchObject({
      enabled: false,
      commandPreview: 'mstsc /v <server>',
    })
    expect(actions.find((action) => action.id === 'pingServer')).toMatchObject({
      enabled: false,
      commandPreview: 'ping <server> -t',
    })
  })
})
