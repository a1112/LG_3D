import { buildSearchCoilIdPath, joinBaseUrl } from '@/services/api'
import type { CoilData, SurfaceKey } from '@/types'
import { openNativePath, type NativeOpenPathResult } from './nativeDialogs'

export type CoilCopyField = 'coilNo' | 'coilId' | 'dateTime'

export interface CoilSaveFolderInput {
  coilId: number
  surfaceKey: SurfaceKey
  saveFolder?: string
  serverHost?: string
  sharedFolderBaseName?: string
}

export interface ClipMaxActionInput extends CoilSaveFolderInput {
  clipMaxImage: (coilId: number, surfaceKey: SurfaceKey, saveUrl?: string) => Promise<unknown>
}

export interface ReDetectionRange {
  fromId: number
  toId: number
}

export type CoilSaveFolderOpenResult = 'native' | 'browser' | 'skipped'
export type QmlExternalOpenResult = 'native' | 'browser' | 'skipped'

interface CoilSaveFolderOpenDependencies {
  openNative?: (path: string) => Promise<NativeOpenPathResult>
  openWindow?: (url: string, target?: string, features?: string) => unknown
}

interface QmlExternalOpenDependencies {
  openNative?: (url: string) => Promise<NativeOpenPathResult>
  openWindow?: (url: string, target?: string, features?: string) => unknown
}

interface ApiHistoryLikeEntry {
  method?: string
  url: string
}

function shouldOpenQmlUrlNatively(url: string): boolean {
  return (
    /^[a-z][a-z0-9+.-]*:/i.test(url) ||
    /^[a-z]:[\\/]/i.test(url) ||
    url.startsWith('\\\\')
  )
}

export function getCoilCopyText(coil: CoilData, field: CoilCopyField): string {
  if (field === 'coilNo') return coil.coilNo
  if (field === 'coilId') return String(coil.id)
  return coil.dateTime
}

export function buildRawCoilSearchUrl(coilId: number, apiBaseUrl = '/api'): string {
  return joinBaseUrl(apiBaseUrl, buildSearchCoilIdPath(coilId))
}

export function buildCoilListDataSourceUrl(limit: number, apiBaseUrl = '/api'): string {
  return joinBaseUrl(apiBaseUrl, `/coilList/${limit}`)
}

function getUrlPathSegments(url: string): string[] {
  try {
    return new URL(url, 'http://localhost').pathname.split('/').filter(Boolean)
  } catch {
    return url.split(/[?#]/, 1)[0].split('/').filter(Boolean)
  }
}

function isQmlCoilListUrl(url: string): boolean {
  return getUrlPathSegments(url).includes('coilList')
}

export function resolveQmlCoilListDataSourceUrl(history: ApiHistoryLikeEntry[], fallbackUrl: string): string {
  return history.find((entry) => isQmlCoilListUrl(entry.url))?.url ?? fallbackUrl
}

function normalizeFolderPath(path: string): string {
  return path.trim().replace(/\\/g, '/').replace(/\/+$/, '')
}

function isLocalHost(host: string): boolean {
  const normalized = host.trim().toLowerCase()
  return normalized === '' || normalized === '127.0.0.1' || normalized === 'localhost' || normalized === '::1'
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function getSurfaceSaveFolder(info: unknown, surfaceKey: SurfaceKey): string {
  const surface = asRecord(asRecord(info)[`surface${surfaceKey}`])
  const saveFolder = surface.saveFolder
  return typeof saveFolder === 'string' ? saveFolder : ''
}

export function buildCoilSaveFolderUrl({
  coilId,
  surfaceKey,
  saveFolder,
  serverHost = '127.0.0.1',
  sharedFolderBaseName = 'Save_',
}: CoilSaveFolderInput): string {
  if (isLocalHost(serverHost) && saveFolder?.trim()) {
    return `file:///${normalizeFolderPath(saveFolder)}/${coilId}`
  }

  return `file:////${serverHost}/${sharedFolderBaseName}${surfaceKey}/${coilId}`
}

export function buildCoilSaveFolderPath(fileUrl: string): string {
  return fileUrl.startsWith('file:///') ? fileUrl.substring(8) : fileUrl
}

export function buildCoilSaveFolderNativePath(fileUrl: string): string {
  const trimmed = fileUrl.trim()
  if (trimmed.startsWith('file:////')) {
    return `\\\\${trimmed.substring(9).replace(/\//g, '\\')}`
  }
  if (trimmed.startsWith('file:///')) {
    return trimmed.substring(8).replace(/\//g, '\\')
  }
  return trimmed
}

export async function openCoilSaveFolderUrl(
  fileUrl: string,
  deps: CoilSaveFolderOpenDependencies = {},
): Promise<CoilSaveFolderOpenResult> {
  const trimmed = fileUrl.trim()
  if (!trimmed) return 'skipped'

  const openNative = deps.openNative ?? openNativePath
  const nativeResult = await openNative(buildCoilSaveFolderNativePath(trimmed)).catch(
    () => ({ status: 'unavailable' }) as NativeOpenPathResult,
  )
  if (nativeResult.status === 'opened') return 'native'

  const openWindow = deps.openWindow ?? (typeof window !== 'undefined' ? window.open.bind(window) : undefined)
  if (!openWindow) return 'skipped'

  openWindow(trimmed, '_blank', 'noopener,noreferrer')
  return 'browser'
}

export async function openQmlExternalUrl(
  url: string,
  deps: QmlExternalOpenDependencies = {},
): Promise<QmlExternalOpenResult> {
  const trimmed = url.trim()
  if (!trimmed) return 'skipped'

  if (shouldOpenQmlUrlNatively(trimmed)) {
    const openNative = deps.openNative ?? openNativePath
    const nativeResult = await openNative(trimmed).catch(() => ({ status: 'unavailable' }) as NativeOpenPathResult)
    if (nativeResult.status === 'opened') return 'native'
  }

  const openWindow = deps.openWindow ?? (typeof window !== 'undefined' ? window.open.bind(window) : undefined)
  if (!openWindow) return 'skipped'

  openWindow(trimmed, '_blank', 'noopener,noreferrer')
  return 'browser'
}

export async function runClipMaxAndGetFolderUrl(input: ClipMaxActionInput): Promise<string> {
  if (!Number.isInteger(input.coilId) || input.coilId <= 0) {
    throw new Error('clip-max requires a valid coil id')
  }
  if (input.surfaceKey !== 'S' && input.surfaceKey !== 'L') {
    throw new Error('clip-max requires a valid surface')
  }
  const folderUrl = buildCoilSaveFolderUrl(input)
  const saveUrl = input.saveFolder?.trim() ? `${normalizeFolderPath(input.saveFolder)}/${input.coilId}` : undefined
  await input.clipMaxImage(input.coilId, input.surfaceKey, saveUrl)
  return folderUrl
}

export function getCurrentCoilReDetectionRange(coil: CoilData | null): ReDetectionRange {
  const coilId = coil?.id ?? 0
  return { fromId: coilId, toId: coilId }
}

export function getCoilListReDetectionRange(coils: CoilData[]): ReDetectionRange {
  if (coils.length === 0) return { fromId: 0, toId: 0 }
  return {
    fromId: coils[coils.length - 1].id,
    toId: coils[0].id,
  }
}
