import { invoke } from '@tauri-apps/api/core'

import { applyRuntimeConnectionSettings, type RuntimeConnectionSettings } from '@/services/api'
import {
  normalizeApiServerIp,
  normalizeApiServerPort,
  normalizeAlg2dServicePort,
  normalizeImageServerPort,
  normalizeQmlServicePort,
  useUiSettingsStore,
} from '@/stores/uiSettingsStore'
import { hasTauriRuntime } from './tauriWindow'

interface NativeSettingsDependencies {
  hasRuntime?: () => boolean
  invokeCommand?: (command: string, args?: Record<string, unknown>) => Promise<unknown>
}

interface NativeSettingsRuntimeDependencies {
  hasRuntime: () => boolean
  invokeCommand: (command: string, args?: Record<string, unknown>) => Promise<unknown>
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function readPort(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value.trim())
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return fallback
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  if (typeof value === 'boolean') {
    return value
  }
  if (typeof value === 'string') {
    if (value.trim().toLowerCase() === 'true') return true
    if (value.trim().toLowerCase() === 'false') return false
  }
  return fallback
}

function normalizeIncomingConnectionSettings(raw: Record<string, unknown>): RuntimeConnectionSettings {
  return {
    serverIp: normalizeApiServerIp(typeof raw.serverIp === 'string' ? raw.serverIp : ''),
    serverPort: normalizeApiServerPort(readPort(raw.serverPort, 5011)),
    databasPort: normalizeQmlServicePort(readPort(raw.databasPort, 6011), 6011),
    dataPort: normalizeQmlServicePort(readPort(raw.dataPort, 6013), 6013),
    plcPort: normalizeQmlServicePort(readPort(raw.plcPort, 6014), 6014),
    alg2dPort: normalizeAlg2dServicePort(readPort(raw.alg2dPort, 5011)),
    useRustImageServer: readBoolean(raw.useRustImageServer, false),
    rustImageServerPort: normalizeImageServerPort(readPort(raw.rustImageServerPort, 6013)),
  }
}

function toPersistencePayload(settings: RuntimeConnectionSettings): RuntimeConnectionSettings {
  return {
    serverIp: normalizeApiServerIp(settings.serverIp),
    serverPort: normalizeApiServerPort(settings.serverPort),
    databasPort: normalizeQmlServicePort(settings.databasPort, 6011),
    dataPort: normalizeQmlServicePort(settings.dataPort, 6013),
    plcPort: normalizeQmlServicePort(settings.plcPort, 6014),
    alg2dPort: normalizeAlg2dServicePort(settings.alg2dPort),
    useRustImageServer: settings.useRustImageServer,
    rustImageServerPort: normalizeImageServerPort(settings.rustImageServerPort),
  }
}

function getRuntimeDeps(
  deps: NativeSettingsDependencies = {},
): NativeSettingsRuntimeDependencies {
  return {
    hasRuntime: deps.hasRuntime ?? hasTauriRuntime,
    invokeCommand:
      deps.invokeCommand ??
      ((command, args) => invoke<unknown>(command, args)),
  }
}

export async function readNativeConnectionSettings(
  deps: NativeSettingsDependencies = {},
): Promise<RuntimeConnectionSettings | null> {
  const { hasRuntime, invokeCommand } = getRuntimeDeps(deps)
  if (!hasRuntime()) {
    return null
  }
  const response = await invokeCommand('read_connection_settings')
  if (response == null) {
    return null
  }
  if (typeof response !== 'object') {
    return null
  }
  return normalizeIncomingConnectionSettings(asRecord(response))
}

export async function writeNativeConnectionSettings(
  settings: RuntimeConnectionSettings,
  deps: NativeSettingsDependencies = {},
): Promise<boolean> {
  const { hasRuntime, invokeCommand } = getRuntimeDeps(deps)
  if (!hasRuntime()) {
    return false
  }
  const payload = toPersistencePayload(settings)
  await invokeCommand('write_connection_settings', { settings: payload })
  return true
}

export async function persistCurrentConnectionSettingsToNative(
  deps: NativeSettingsDependencies = {},
): Promise<boolean> {
  const state = useUiSettingsStore.getState()
  return writeNativeConnectionSettings(
    {
      serverIp: state.apiServerIp,
      serverPort: state.apiServerPort,
      databasPort: state.databasPort,
      dataPort: state.dataPort,
      plcPort: state.plcPort,
      alg2dPort: state.alg2dPort,
      useRustImageServer: state.useRustImageServer,
      rustImageServerPort: state.rustImageServerPort,
    },
    deps,
  )
}

export async function hydrateConnectionSettingsFromNative(
  deps: NativeSettingsDependencies = {},
): Promise<boolean> {
  const settings = await readNativeConnectionSettings(deps)
  if (settings == null) {
    return false
  }
  const {
    setApiServerIp,
    setApiServerPort,
    setDatabasPort,
    setDataPort,
    setPlcPort,
    setAlg2dPort,
    setUseRustImageServer,
    setRustImageServerPort,
  } = useUiSettingsStore.getState()

  setApiServerIp(settings.serverIp)
  setApiServerPort(settings.serverPort)
  setDatabasPort(settings.databasPort)
  setDataPort(settings.dataPort)
  setPlcPort(settings.plcPort)
  setAlg2dPort(settings.alg2dPort)
  setUseRustImageServer(settings.useRustImageServer)
  setRustImageServerPort(settings.rustImageServerPort)
  applyRuntimeConnectionSettings(settings)
  return true
}
