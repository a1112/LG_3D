import { buildRemoteServiceDocsUrl, normalizeMaintenanceHost } from './maintenanceTools'

export interface AlarmSummaryItem {
  key: string
  title: string
  value: string
  level: number
  message: string
}

export interface CameraAlarmItem extends AlarmSummaryItem {
  actions: GlobalAlarmCameraCardAction[]
}

export interface NetworkAlarmItem extends AlarmSummaryItem {
  port: number
  docsUrl?: string
  actions: GlobalAlarmNetworkCardAction[]
}

export type GlobalAlarmNetworkKey = 'capture' | 'data' | 'threeD' | 'plc'

export interface GlobalAlarmNetworkProbeTarget {
  key: GlobalAlarmNetworkKey
  title: string
  port: number
  delayUrl: string
}

export interface GlobalAlarmNetworkProbeOptions {
  apiBaseUrl: string
  networkPorts?: GlobalAlarmNetworkPorts
  browserOrigin?: string
}

export interface GlobalAlarmNetworkDelaySample {
  ok: boolean
  delayMs: number
}

export interface GlobalAlarmNetworkPorts {
  capture?: number
  data?: number
  threeD?: number
  plc?: number
}

export type GlobalAlarmNetworkDelaySamples =
  | GlobalAlarmNetworkDelaySample
  | Partial<Record<'capture' | 'data' | 'threeD' | 'plc', GlobalAlarmNetworkDelaySample>>

export interface GlobalAlarmSources {
  cameraAlarm?: unknown
  hardware?: unknown
  networkPorts?: GlobalAlarmNetworkPorts
  networkDelay?: GlobalAlarmNetworkDelaySamples
  networkDocsUrl?: string
  networkRemoteHost?: string
}

export interface GlobalAlarmViewModel {
  cameras: CameraAlarmItem[]
  networks: NetworkAlarmItem[]
  networkHeaderActions: GlobalAlarmNetworkHeaderAction[]
  hardware: AlarmSummaryItem[]
  maxLevel: number
}

export interface GlobalAlarmNetworkHeaderAction {
  id: 'remoteDesktop'
  label: string
  enabled: boolean
  status: '可用' | '待接入'
  commandPreview: string
}

export interface GlobalAlarmNetworkCardAction {
  id: 'openApiDocs' | 'restartService'
  label: string
  enabled: boolean
  status: '可用' | '待接入'
  href?: string
}

export interface GlobalAlarmCameraCardAction {
  id: 'openCurrentCoilCameraData' | 'openRawDataSavePath' | 'restartCamera'
  label: string
  enabled: boolean
  status: '可用' | '待接入'
}

type NetworkDefinition = {
  key: GlobalAlarmNetworkKey
  title: string
  message: string
  portKey: keyof GlobalAlarmNetworkPorts
  defaultPort: number
}

const NETWORK_DEFINITIONS: NetworkDefinition[] = [
  {
    key: 'capture',
    title: '采集服务',
    message: 'api服务:采集务器（6相机）',
    portKey: 'capture',
    defaultPort: 6011,
  },
  {
    key: 'data',
    title: '数据服务',
    message: 'api服务:数据服务器',
    portKey: 'data',
    defaultPort: 6011,
  },
  {
    key: 'threeD',
    title: '3D服务',
    message: 'api服务:PLC 交互',
    portKey: 'threeD',
    defaultPort: 6013,
  },
  {
    key: 'plc',
    title: 'PLC服务',
    message: 'api服务:PLC 交互',
    portKey: 'plc',
    defaultPort: 6014,
  },
]

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readString(record: Record<string, unknown>, keys: string[], fallback = ''): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim().length > 0) return value
    if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  }
  return fallback
}

function readLevel(record: Record<string, unknown>, fallback = 1): number {
  const value = record.level
  if (typeof value === 'number' && Number.isFinite(value)) return Math.trunc(value)
  if (typeof value === 'string') {
    const numericValue = Number(value)
    if (Number.isFinite(numericValue)) return Math.trunc(numericValue)
  }
  return fallback
}

function normalizePort(value: number | undefined, fallback: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return Math.trunc(value)
}

function formatDelayMs(delayMs: number): string {
  if (!Number.isFinite(delayMs)) return '0 ms'
  return `${Math.max(0, Math.round(delayMs))} ms`
}

function buildCameraCardActions(): GlobalAlarmCameraCardAction[] {
  return [
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
  ]
}

function buildCameraItems(cameraAlarm: unknown): CameraAlarmItem[] {
  return Object.entries(asRecord(cameraAlarm)).map(([key, value]) => {
    const record = asRecord(value)
    const level = readLevel(record)
    const qmlKey = readString(record, ['Key'], key)
    return {
      key: qmlKey,
      title: qmlKey,
      value: level > 1 ? '异常' : '正常',
      level,
      message: readString(record, ['msg', 'message', 'lastError2D', 'lastError3D']),
      actions: buildCameraCardActions(),
    }
  })
}

function buildHardwareItems(hardware: unknown): AlarmSummaryItem[] {
  return Object.entries(asRecord(hardware)).map(([key, value]) => {
    const record = asRecord(value)
    return {
      key,
      title: readString(record, ['key', 'title'], key),
      value: readString(record, ['value'], '--'),
      level: 1,
      message: readString(record, ['msg', 'message']),
    }
  })
}

function readNetworkDelaySample(
  key: NetworkAlarmItem['key'],
  samples: GlobalAlarmNetworkDelaySamples | undefined,
): GlobalAlarmNetworkDelaySample | undefined {
  if (!samples) return undefined
  if ('ok' in samples) return samples
  return samples[key as keyof typeof samples]
}

function applyNetworkDelaySample(
  item: NetworkAlarmItem,
  sample: GlobalAlarmNetworkDelaySample | undefined,
): NetworkAlarmItem {
  if (!sample) return item
  if (!sample.ok) {
    return {
      ...item,
      value: '连接错误',
      level: 3,
    }
  }

  return {
    ...item,
    value: formatDelayMs(sample.delayMs),
    level: 1,
  }
}

function buildNetworkItems(
  ports: GlobalAlarmNetworkPorts = {},
  networkDelay: GlobalAlarmNetworkDelaySamples | undefined,
  networkDocsUrl: string | undefined,
  networkRemoteHost: string | undefined,
): NetworkAlarmItem[] {
  const items = NETWORK_DEFINITIONS.map((definition) => ({
    key: definition.key,
    title: definition.title,
    value: '待检测',
    level: 1,
    message: definition.message,
    port: normalizePort(ports[definition.portKey], definition.defaultPort),
  }))

  return items.map((item) => {
    const protocol = networkRemoteHost?.trim().toLowerCase().startsWith('https') ? 'https://' : 'http://'
    const docsUrl = networkRemoteHost
      ? buildRemoteServiceDocsUrl(item.port, networkRemoteHost, protocol)
      : networkDocsUrl
    const actions: GlobalAlarmNetworkCardAction[] = [
      {
        id: 'openApiDocs',
        label: '打开接口文档',
        enabled: Boolean(docsUrl),
        status: docsUrl ? '可用' : '待接入',
        href: docsUrl,
      },
      {
        id: 'restartService',
        label: '重启服务',
        enabled: false,
        status: '待接入',
      },
    ]
    return applyNetworkDelaySample({ ...item, docsUrl, actions }, readNetworkDelaySample(item.key, networkDelay))
  })
}

function buildNetworkHeaderActions(rawHost: string | undefined): GlobalAlarmNetworkHeaderAction[] {
  const host = normalizeMaintenanceHost(rawHost ?? '')
  const enabled = host.length > 0
  return [
    {
      id: 'remoteDesktop',
      label: '远程到服务器',
      enabled,
      status: enabled ? '可用' : '待接入',
      commandPreview: `mstsc /v ${enabled ? host : '<server>'}`,
    },
  ]
}

function defaultBrowserOrigin(): string {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return window.location.origin
  }
  return 'http://127.0.0.1'
}

function probeHostBase(apiBaseUrl: string, browserOrigin?: string): string {
  const fallbackOrigin = browserOrigin || defaultBrowserOrigin()
  try {
    const url = new URL(apiBaseUrl || '/', fallbackOrigin)
    return `${url.protocol}//${url.hostname}`
  } catch {
    const url = new URL(fallbackOrigin)
    return `${url.protocol}//${url.hostname}`
  }
}

export function buildGlobalAlarmNetworkProbeTargets({
  apiBaseUrl,
  networkPorts = {},
  browserOrigin,
}: GlobalAlarmNetworkProbeOptions): GlobalAlarmNetworkProbeTarget[] {
  const hostBase = probeHostBase(apiBaseUrl, browserOrigin)
  return NETWORK_DEFINITIONS.map((definition) => {
    const port = normalizePort(networkPorts[definition.portKey], definition.defaultPort)
    return {
      key: definition.key,
      title: definition.title,
      port,
      delayUrl: `${hostBase}:${port}/delay`,
    }
  })
}

type DelayFetch = (url: string, init?: RequestInit) => Promise<{ ok?: boolean }>

export async function measureGlobalAlarmNetworkDelays(
  targets: GlobalAlarmNetworkProbeTarget[],
  fetchImpl: DelayFetch = fetch,
  now: () => number = () => Date.now(),
  timeoutMs = 1_000,
): Promise<Partial<Record<GlobalAlarmNetworkKey, GlobalAlarmNetworkDelaySample>>> {
  const samples: Partial<Record<GlobalAlarmNetworkKey, GlobalAlarmNetworkDelaySample>> = {}
  for (const target of targets) {
    const startTime = now()
    const controller = new AbortController()
    const timeoutId = globalThis.setTimeout(() => controller.abort(), Math.max(1, timeoutMs))
    try {
      const response = await fetchImpl(target.delayUrl, {
        method: 'GET',
        cache: 'no-store',
        signal: controller.signal,
      })
      samples[target.key] = {
        ok: response.ok !== false,
        delayMs: Math.max(0, now() - startTime),
      }
    } catch {
      samples[target.key] = {
        ok: false,
        delayMs: Math.max(0, now() - startTime),
      }
    } finally {
      globalThis.clearTimeout(timeoutId)
    }
  }
  return samples
}

export function buildGlobalAlarmViewModel({
  cameraAlarm,
  hardware,
  networkPorts,
  networkDelay,
  networkDocsUrl,
  networkRemoteHost,
}: GlobalAlarmSources): GlobalAlarmViewModel {
  const cameras = buildCameraItems(cameraAlarm)
  const networks = buildNetworkItems(networkPorts, networkDelay, networkDocsUrl, networkRemoteHost)
  const networkHeaderActions = buildNetworkHeaderActions(networkRemoteHost)
  const hardwareItems = buildHardwareItems(hardware)
  const levels = [...cameras, ...networks, ...hardwareItems].map((item) => item.level)

  return {
    cameras,
    networks,
    networkHeaderActions,
    hardware: hardwareItems,
    maxLevel: levels.length > 0 ? Math.max(...levels) : 1,
  }
}
