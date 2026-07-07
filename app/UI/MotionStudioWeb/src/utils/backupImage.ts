import { openNativePath, type NativeOpenPathResult } from './nativeDialogs'

interface CoilLike {
  id?: number
}

export interface BackupImageRange {
  fromId: number
  toId: number
}

export type BackupImageOpenResult = 'native' | 'browser' | 'skipped'

interface BackupImageFolderOpenDependencies {
  openNative?: (path: string) => Promise<NativeOpenPathResult>
  openWindow?: (url: string, target?: string, features?: string) => unknown
}

function joinBackupImageFolder(folder: string, name: string): string {
  const trimmed = folder.trim().replace(/[\\/]+$/, '')
  if (!trimmed) return name
  return `${trimmed}\\${name}`
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

export function buildBackupImageInitialRange(coils: CoilLike[]): BackupImageRange {
  const ids = coils
    .map((coil) => Number(coil.id))
    .filter((id) => Number.isFinite(id) && id > 0)
  if (ids.length === 0) return { fromId: 0, toId: 0 }
  return {
    fromId: Math.min(...ids),
    toId: Math.max(...ids),
  }
}

export function buildBackupImageDefaultName(date = new Date()): string {
  return `备份_${date.getFullYear()}_${pad(date.getMonth() + 1)}_${pad(date.getDate())} ${pad(date.getHours())}_${pad(date.getMinutes())}_${pad(date.getSeconds())}`
}

export function buildBackupImageDefaultPath(folder: string, date = new Date()): string {
  return joinBackupImageFolder(folder, buildBackupImageDefaultName(date))
}

export function resolveBackupImageWsUrl(
  apiBaseUrl: string,
  wsPath: string,
  origin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1',
): string {
  const normalizedPath = wsPath.startsWith('/') ? wsPath : `/${wsPath}`
  if (/^https?:\/\//.test(apiBaseUrl)) {
    const base = new URL(apiBaseUrl)
    base.protocol = base.protocol === 'https:' ? 'wss:' : 'ws:'
    base.pathname = normalizedPath
    base.search = ''
    base.hash = ''
    return base.toString()
  }

  if (/^wss?:\/\//.test(apiBaseUrl)) {
    const base = new URL(apiBaseUrl)
    base.pathname = normalizedPath
    base.search = ''
    base.hash = ''
    return base.toString()
  }

  const url = new URL(normalizedPath, origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString()
}

export function isBackupImageFinishedMessage(message: string): boolean {
  const value = Number.parseInt(message, 10)
  return Number.isFinite(value) && value >= 100
}

function buildBackupFolderFileUrl(path: string): string {
  return `file:///${path.replace(/\\/g, '/')}`
}

export async function openBackupImageFolder(
  path: string,
  deps: BackupImageFolderOpenDependencies = {},
): Promise<BackupImageOpenResult> {
  const trimmed = path.trim()
  if (!trimmed) return 'skipped'

  const openNative = deps.openNative ?? openNativePath
  const nativeResult = await openNative(trimmed).catch(() => ({ status: 'unavailable' }) as NativeOpenPathResult)
  if (nativeResult.status === 'opened') return 'native'

  const openWindow = deps.openWindow ?? (typeof window !== 'undefined' ? window.open.bind(window) : undefined)
  if (!openWindow) return 'skipped'

  openWindow(buildBackupFolderFileUrl(trimmed), '_blank', 'noopener,noreferrer')
  return 'browser'
}
