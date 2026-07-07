import type { AreaClipConfigPayload } from '@/services/api'

export type AreaSurfaceKey = 'S' | 'L'
export type AreaClipMode = 'fixed' | 'dynamic'

export interface AreaStatusView {
  status: string
  surfaceQueueDepth: number
  joinQueueDepth: number
  scanRunning: boolean
  clipConfig?: AreaStatusClipConfig
}

export interface AreaStatusClipConfig {
  mode: AreaClipMode
  fixed: number
  a: number
  b: number
  c: number
  offset?: number
}

export interface QmlAreaClipSettings {
  surfaceKey: AreaSurfaceKey
  label: string
  mode: AreaClipMode
  fixed: number
  a: number
  b: number
  c: number
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function readQueueDepth(value: unknown): number | undefined {
  const record = asRecord(value)
  return readNumber(record.queueDepth ?? record.queue_depth ?? record.queueSize)
}

function readBoolean(value: unknown): boolean {
  return value === true
}

function readClipMode(value: unknown, fallback: AreaClipMode): AreaClipMode {
  return value === 'dynamic' || value === 'fixed' ? value : fallback
}

export function normalizeAreaSurfaceKey(value: unknown, fallback: AreaSurfaceKey = 'S'): AreaSurfaceKey {
  return String(value ?? fallback).trim().toUpperCase() === 'L' ? 'L' : fallback
}

export function buildDefaultAreaClipConfig(surfaceKey: unknown, overrides: Partial<AreaClipConfigPayload> = {}) {
  const normalizedSurface = normalizeAreaSurfaceKey(surfaceKey)
  const { surface_key: overrideSurfaceKey, ...restOverrides } = overrides

  return {
    mode: 'dynamic',
    offset: 40,
    ...restOverrides,
    surface_key: normalizeAreaSurfaceKey(overrideSurfaceKey ?? normalizedSurface),
  } satisfies AreaClipConfigPayload
}

export function buildQmlAreaClipSettings(): QmlAreaClipSettings[] {
  return [
    {
      surfaceKey: 'S',
      label: 'S端',
      mode: 'fixed',
      fixed: 200,
      a: 3,
      b: 220,
      c: 2600,
    },
    {
      surfaceKey: 'L',
      label: 'L端',
      mode: 'fixed',
      fixed: 200,
      a: 3,
      b: 220,
      c: 4000,
    },
  ]
}

export function buildQmlAreaClipSettingsFromStatus(
  value: unknown,
  fallbackSettings: QmlAreaClipSettings[] = buildQmlAreaClipSettings(),
): QmlAreaClipSettings[] {
  const record = asRecord(value)
  const surfaces = asRecord(record.surfaces)
  const fallbackBySurface = new Map(fallbackSettings.map((setting) => [setting.surfaceKey, setting]))

  return buildQmlAreaClipSettings().map((defaultSetting) => {
    const fallback = fallbackBySurface.get(defaultSetting.surfaceKey) ?? defaultSetting
    const surface = asRecord(surfaces[defaultSetting.surfaceKey])
    const clipConfig = asRecord(surface.clipConfig ?? surface.clip_config)

    return {
      surfaceKey: defaultSetting.surfaceKey,
      label: defaultSetting.label,
      mode: readClipMode(clipConfig.mode, fallback.mode),
      fixed: readNumber(clipConfig.fixed) ?? fallback.fixed,
      a: readNumber(clipConfig.a) ?? fallback.a,
      b: readNumber(clipConfig.b) ?? fallback.b,
      c: readNumber(clipConfig.c) ?? fallback.c,
    }
  })
}

export function buildAreaClipPayloadFromSettings(settings: QmlAreaClipSettings): AreaClipConfigPayload {
  return {
    surface_key: settings.surfaceKey,
    mode: settings.mode,
    fixed: settings.fixed,
    a: settings.a,
    b: settings.b,
    c: settings.c,
  }
}

export function readAreaQueueDepth(value: unknown): number {
  return readQueueDepth(value) ?? 0
}

export function buildAreaStatusView(value: unknown, surfaceKey: unknown): AreaStatusView {
  const record = asRecord(value)
  const normalizedSurfaceKey = normalizeAreaSurfaceKey(surfaceKey)
  const surfaces = asRecord(record.surfaces)
  const currentSurface = asRecord(surfaces[normalizedSurfaceKey])
  const queueDepths = asRecord(record.queueDepths)
  const scanner = asRecord(record.scanner)
  const defaultClipConfig = buildQmlAreaClipSettings().find(
    (setting) => setting.surfaceKey === normalizedSurfaceKey,
  )!
  const clipConfig = asRecord(currentSurface.clipConfig ?? currentSurface.clip_config)
  const hasClipConfig = Object.keys(clipConfig).length > 0

  return {
    status: typeof record.status === 'string' ? record.status : 'unknown',
    surfaceQueueDepth:
      readQueueDepth(currentSurface) ?? readNumber(queueDepths[normalizedSurfaceKey]) ?? 0,
    joinQueueDepth:
      readNumber(record.joinQueueSize) ?? readNumber(queueDepths.join) ?? readQueueDepth(record) ?? 0,
    scanRunning: readBoolean(scanner.scanRunning ?? scanner.running),
    clipConfig: hasClipConfig
      ? {
          mode: readClipMode(clipConfig.mode, defaultClipConfig.mode),
          fixed: readNumber(clipConfig.fixed) ?? defaultClipConfig.fixed,
          a: readNumber(clipConfig.a) ?? defaultClipConfig.a,
          b: readNumber(clipConfig.b) ?? defaultClipConfig.b,
          c: readNumber(clipConfig.c) ?? defaultClipConfig.c,
          offset: readNumber(clipConfig.offset),
        }
      : undefined,
  }
}
