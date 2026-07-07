export type MaintenanceActionId =
  | 'remoteDesktop'
  | 'pingServer'
  | 'restore'
  | 'restartAllServices'
  | 'serviceManagement'
  | 'restartServer'
  | 'backupToFile'
  | 'restoreFromBackup'
  | 'networkSpeedtest'
  | 'exitSystem'

export type MaintenanceActionStatus = '可用' | '待接入'
export type MaintenanceActionSideEffect = 'externalProcess' | 'navigation' | 'windowClose' | 'modal'

export interface MaintenanceAction {
  id: MaintenanceActionId
  label: string
  parentLabel?: string
  commandPreview?: string
  enabled: boolean
  status: MaintenanceActionStatus
  sideEffect?: MaintenanceActionSideEffect
}

export interface MaintenanceToolGroup {
  key: 'maintenance' | 'feature' | 'system'
  title: string
  actions: MaintenanceAction[]
}

export interface RemoteServiceRow {
  key: string
  title: string
  port: number
  message: string
  docsUrl: string
  actions: RemoteServiceAction[]
}

export interface RemoteServicePortSettings {
  databasPort?: number
  dataPort?: number
  plcPort?: number
  host?: string
  protocol?: string
}

export type RemoteServiceActionId = 'openApiDocs' | 'restartService'

export interface RemoteServiceAction {
  id: RemoteServiceActionId
  label: string
  enabled: boolean
  status: MaintenanceActionStatus
  href?: string
}

const SAFE_HOST_PATTERN = /^[a-zA-Z0-9._:-]+$/

function normalizeServicePort(value: number | undefined, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return Math.min(Math.max(Math.trunc(value), 1), 65535)
}

export function buildRemoteServiceRows(settings: RemoteServicePortSettings = {}): RemoteServiceRow[] {
  const databasPort = normalizeServicePort(settings.databasPort, 6011)
  const dataPort = normalizeServicePort(settings.dataPort, 6013)
  const plcPort = normalizeServicePort(settings.plcPort, 6014)
  const host = normalizeMaintenanceHost(settings.host ?? '') || '127.0.0.1'
  const docsForPort = (port: number) => buildRemoteServiceDocsUrl(port, host, settings.protocol)
  const actionsForPort = (port: number): RemoteServiceAction[] => [
    {
      id: 'openApiDocs',
      label: '打开接口文档',
      enabled: true,
      href: docsForPort(port),
      status: '可用',
    },
    {
      id: 'restartService',
      label: '重启服务',
      enabled: false,
      status: '待接入',
    },
  ]

  return [
    {
      key: 'capture',
      title: '采集服务',
      port: databasPort,
      message: 'api服务:采集务器（6相机）',
      docsUrl: docsForPort(databasPort),
      actions: actionsForPort(databasPort),
    },
    {
      key: 'data',
      title: '数据服务',
      port: databasPort,
      message: 'api服务:数据服务器',
      docsUrl: docsForPort(databasPort),
      actions: actionsForPort(databasPort),
    },
    {
      key: 'threeD',
      title: '3D服务',
      port: dataPort,
      message: 'api服务:PLC 交互',
      docsUrl: docsForPort(dataPort),
      actions: actionsForPort(dataPort),
    },
    {
      key: 'plc',
      title: 'PLC服务',
      port: plcPort,
      message: 'api服务:PLC 交互',
      docsUrl: docsForPort(plcPort),
      actions: actionsForPort(plcPort),
    },
  ]
}

export function normalizeMaintenanceHost(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ''

  const withoutProtocol = trimmed.replace(/^[a-zA-Z][a-zA-Z\d+.-]*:\/\//, '')
  const host = withoutProtocol.split(/[/?#]/)[0].replace(/^\[/, '').replace(/\]$/, '').split(':')[0]
  if (!host || !SAFE_HOST_PATTERN.test(host)) return ''
  return host
}

export function buildRemoteServiceDocsUrl(port: number, rawHost = '127.0.0.1', protocol = 'http://'): string {
  const host = normalizeMaintenanceHost(rawHost) || '127.0.0.1'
  const scheme = protocol.trim().toLowerCase().startsWith('https') ? 'https' : 'http'
  return `${scheme}://${host}:${normalizeServicePort(port, 6011)}/docs`
}

function externalAction(
  id: 'remoteDesktop' | 'pingServer',
  label: string,
  host: string,
): MaintenanceAction {
  const enabled = host.length > 0
  const commandPreview = id === 'remoteDesktop'
    ? `mstsc /v ${enabled ? host : '<server>'}`
    : `ping ${enabled ? host : '<server>'} -t`

  return {
    id,
    label,
    commandPreview,
    enabled,
    status: enabled ? '可用' : '待接入',
    sideEffect: 'externalProcess',
  }
}

function placeholderAction(id: MaintenanceActionId, label: string, parentLabel?: string): MaintenanceAction {
  return {
    id,
    label,
    parentLabel,
    enabled: false,
    status: '待接入',
  }
}

function navigationAction(id: 'networkSpeedtest', label: string, parentLabel: string): MaintenanceAction {
  return {
    id,
    label,
    parentLabel,
    enabled: true,
    status: '可用',
    sideEffect: 'navigation',
  }
}

export function buildMaintenanceToolGroups(rawHost: string): MaintenanceToolGroup[] {
  const host = normalizeMaintenanceHost(rawHost)

  return [
    {
      key: 'maintenance',
      title: '维护',
      actions: [
        externalAction('remoteDesktop', '远程到服务器', host),
        externalAction('pingServer', 'Ping 服务器', host),
        placeholderAction('restore', '一键恢复'),
        placeholderAction('restartAllServices', '重启全部服务'),
        {
          id: 'serviceManagement',
          label: '服务管理',
          enabled: true,
          status: '可用',
          sideEffect: 'modal',
        },
        placeholderAction('restartServer', '重启服务器'),
      ],
    },
    {
      key: 'feature',
      title: '功能',
      actions: [
        {
          id: 'backupToFile',
          label: '备份到 ...',
          parentLabel: '数据库备份',
          enabled: true,
          status: '可用',
          sideEffect: 'navigation',
        },
        placeholderAction('restoreFromBackup', '从 备份 恢复', '数据库备份'),
        navigationAction('networkSpeedtest', '网络测速', '测试'),
      ],
    },
    {
      key: 'system',
      title: '系统',
      actions: [
        {
          id: 'exitSystem',
          label: '退出系统',
          enabled: true,
          status: '可用',
          sideEffect: 'windowClose',
        },
      ],
    },
  ]
}
