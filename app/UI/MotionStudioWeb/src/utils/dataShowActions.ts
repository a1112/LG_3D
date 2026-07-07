import {
  buildCoilDataRenderPath,
  buildHeightLinePath,
  joinBaseUrl,
  resolveQmlSurfaceImageUrl,
  type CoilDataRenderParams,
  type HeightLineCoords,
  type ImageRuntimeSettings,
} from '@/services/api'
import type { SurfaceKey } from '@/types'
import { DEFAULT_SCAN_3D_SCALE_Z } from './qmlPointValue'
import { openNativePath, type NativeOpenPathResult } from './nativeDialogs'

export type DataShowOpenUrlMode = 'area' | 'gray' | 'depth' | 'three'

const DEFAULT_RENDER_SCALE = 1
const DEFAULT_RENDER_RANGE_Z = 20

export interface DataShowOpenUrlInput {
  mode: DataShowOpenUrlMode
  surfaceKey: string
  coilId: number
  imageRuntimeSettings: ImageRuntimeSettings
  imageBaseUrl: string
  renderParams?: CoilDataRenderParams
}

export interface DataShowHeightDataReturnUrlInput {
  surfaceKey: string
  coilId: number
  coords: HeightLineCoords
  apiBaseUrl: string
}

export interface DataShowRenderParamsInput {
  coilInfo: unknown
  planeZMm?: number
  renderScale?: number
  rangeZ?: number
  mask?: boolean
  grayscale?: boolean
}

export type DataShowRenderStageKey = 'gray-preview' | 'color-render'
export type DataShowRenderViewKey = 'GRAY' | 'JET'
export type DataShowRenderImageTypeText = '灰度预览' | '彩色显示'

export interface DataShowRenderStage {
  key: DataShowRenderStageKey
  viewKey: DataShowRenderViewKey
  label: DataShowRenderImageTypeText
  delayMs: number
  params: CoilDataRenderParams
}

export type DataShowExternalOpenResult = 'native' | 'browser' | 'skipped'

interface DataShowExternalOpenDependencies {
  openNative?: (url: string) => Promise<NativeOpenPathResult>
  openWindow?: (url: string, target?: string, features?: string) => unknown
}

function normalizeDataShowSurfaceKey(surfaceKey: string): SurfaceKey {
  return String(surfaceKey || 'S').toUpperCase() === 'L' ? 'L' : 'S'
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function finiteRecordNumber(record: Record<string, unknown>, key: string): number | undefined {
  return finiteNumber(record[key])
}

function finiteNumber(value: unknown): number | undefined {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : undefined
}

function positiveNumberOr(value: unknown, fallback: number): number {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) && numberValue > 0 ? numberValue : fallback
}

export function buildDataShowRenderParams(input: DataShowRenderParamsInput): CoilDataRenderParams | null {
  const record = asRecord(input.coilInfo)
  const medianZInt = finiteRecordNumber(record, 'median_3d')
  const medianZMm = finiteRecordNumber(record, 'median_3d_mm')
  if (medianZInt === undefined || medianZMm === undefined) return null

  const scan3dScaleZ = positiveNumberOr(finiteRecordNumber(record, 'scan3dCoordinateScaleZ'), DEFAULT_SCAN_3D_SCALE_Z)
  const planeZMm = finiteNumber(input.planeZMm)
  const renderCenterZ =
    planeZMm === undefined ? medianZInt : medianZInt + (planeZMm - medianZMm) / scan3dScaleZ
  const rangeZValue = positiveNumberOr(input.rangeZ, DEFAULT_RENDER_RANGE_Z) / scan3dScaleZ

  return {
    scale: positiveNumberOr(input.renderScale, DEFAULT_RENDER_SCALE),
    mask: input.mask ?? true,
    minValue: Math.trunc(renderCenterZ - rangeZValue),
    maxValue: Math.trunc(renderCenterZ + rangeZValue),
    grayscale: input.grayscale ?? false,
  }
}

export function buildDataShowRenderStages(
  params: CoilDataRenderParams | null,
  enable1024CacheMode: boolean,
): DataShowRenderStage[] {
  if (!params) return []

  const colorStage: DataShowRenderStage = {
    key: 'color-render',
    viewKey: 'JET',
    label: '彩色显示',
    delayMs: 0,
    params: { ...params, grayscale: false },
  }

  if (!enable1024CacheMode) return [colorStage]

  return [
    {
      key: 'gray-preview',
      viewKey: 'GRAY',
      label: '灰度预览',
      delayMs: 0,
      params: { ...params, grayscale: true },
    },
    {
      ...colorStage,
      delayMs: 500,
    },
  ]
}

function shouldOpenDataShowUrlNatively(url: string): boolean {
  return (
    /^[a-z][a-z0-9+.-]*:/i.test(url) ||
    /^[a-z]:[\\/]/i.test(url) ||
    url.startsWith('\\\\')
  )
}

export function buildDataShowOpenUrl(input: DataShowOpenUrlInput): string {
  const surface = normalizeDataShowSurfaceKey(input.surfaceKey)
  const coilId = Math.trunc(input.coilId)

  if (input.mode === 'three') {
    return joinBaseUrl(input.imageBaseUrl, buildCoilDataRenderPath(surface, coilId, input.renderParams))
  }

  if (input.mode === 'gray' || input.mode === 'depth') {
    return resolveQmlSurfaceImageUrl(
      input.imageRuntimeSettings,
      surface,
      coilId,
      input.mode === 'gray' ? 'GRAY' : 'JET',
      false,
      input.imageBaseUrl,
    )
  }

  return resolveQmlSurfaceImageUrl(
    input.imageRuntimeSettings,
    surface,
    coilId,
    'AREA',
    false,
    input.imageBaseUrl,
  )
}

export function buildDataShowHeightDataReturnUrl(input: DataShowHeightDataReturnUrlInput): string {
  const surface = normalizeDataShowSurfaceKey(input.surfaceKey)
  const coilId = Math.trunc(input.coilId)
  return joinBaseUrl(input.apiBaseUrl, buildHeightLinePath(surface, coilId, input.coords))
}

export async function openDataShowExternalUrl(
  url: string,
  deps: DataShowExternalOpenDependencies = {},
): Promise<DataShowExternalOpenResult> {
  const trimmed = url.trim()
  if (!trimmed) return 'skipped'

  if (shouldOpenDataShowUrlNatively(trimmed)) {
    const openNative = deps.openNative ?? openNativePath
    const nativeResult = await openNative(trimmed).catch(() => ({ status: 'unavailable' }) as NativeOpenPathResult)
    if (nativeResult.status === 'opened') return 'native'
  }

  const openWindow = deps.openWindow ?? (typeof window !== 'undefined' ? window.open.bind(window) : undefined)
  if (!openWindow) return 'skipped'

  openWindow(trimmed, '_blank', 'noopener,noreferrer')
  return 'browser'
}
