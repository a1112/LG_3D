import { joinBaseUrl } from '@/services/api'
import {
  getNativeDefaultDownloadDirectory,
  openNativePath,
  saveNativeFile,
  writeNativeFile,
  type NativeFileSaveResult,
  type NativeOpenPathResult,
} from '@/utils/nativeDialogs'

export interface SoftwareUpdateManifest {
  version: string
  downloadUrl: string
  fileName: string
  releaseNotes: string
}

export type SoftwareUpdateDownloadResult =
  | NativeFileSaveResult
  | { status: 'downloaded'; fileName: string }

export type SoftwareUpdateOpenResult = NativeOpenPathResult | { status: 'skipped' }
export type SoftwareUpdateInstallTarget = 'folder' | 'package' | 'install'
export interface SoftwareUpdateProgressEvent {
  received: number
  total: number
  progress: number
}

export interface SoftwareUpdateFileNameOptions {
  fileName: string
  downloadUrl: string
  now?: Date
}

export interface SoftwareUpdateDownloadOptions {
  url: string
  fileName: string
  downloadUrl?: string
  now?: Date
  onProgress?: (event: SoftwareUpdateProgressEvent) => void
}

interface SoftwareUpdateDownloadDependencies {
  fetchBytes?: (url: string, onProgress?: (event: SoftwareUpdateProgressEvent) => void) => Promise<ArrayBuffer>
  defaultDownloadDirectory?: () => Promise<string | null>
  writeFile?: (path: string, contents: ArrayBuffer | Uint8Array) => Promise<NativeFileSaveResult>
  saveFile?: (defaultName: string, contents: ArrayBuffer | Uint8Array) => Promise<NativeFileSaveResult>
  browserDownload?: (fileName: string, contents: ArrayBuffer) => void
}

interface SoftwareUpdateOpenDependencies {
  openPath?: (path: string) => Promise<NativeOpenPathResult>
  defaultDownloadDirectory?: () => Promise<string | null>
  closeApp?: () => Promise<void>
}

function stringValue(value: unknown): string {
  if (value === undefined || value === null) return ''
  return String(value).trim()
}

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object') return {}
  return value as Record<string, unknown>
}

function firstValue(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = stringValue(record[key])
    if (value) return value
  }
  return ''
}

function versionNumbers(version: string): number[] {
  return Array.from(version.matchAll(/\d+/g), (match) => Number.parseInt(match[0], 10))
}

export function compareSoftwareVersions(left: string, right: string): number {
  const leftNums = versionNumbers(left)
  const rightNums = versionNumbers(right)
  const count = Math.max(leftNums.length, rightNums.length)

  for (let index = 0; index < count; index += 1) {
    const leftValue = leftNums[index] ?? 0
    const rightValue = rightNums[index] ?? 0
    if (leftValue > rightValue) return 1
    if (leftValue < rightValue) return -1
  }

  return 0
}

export function normalizeSoftwareUpdateManifest(data: unknown): SoftwareUpdateManifest {
  const root = asRecord(data)
  const payload = asRecord(root.data ?? root)

  return {
    version: firstValue(payload, ['version', 'latest_version', 'latestVersion', 'app_version', 'appVersion']),
    downloadUrl: firstValue(payload, ['download_url', 'downloadUrl', 'package_url', 'packageUrl', 'url']),
    fileName: firstValue(payload, ['file_name', 'fileName', 'filename', 'name']),
    releaseNotes: firstValue(payload, ['notes', 'release_notes', 'releaseNotes', 'description', 'changelog']),
  }
}

export function resolveSoftwareUpdateUrl(url: string, manifestUrl: string): string {
  const target = stringValue(url)
  if (!target || /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(target)) return target

  const originMatch = manifestUrl.match(/^([a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^/]+)/)
  if (target.startsWith('/') && originMatch) {
    return `${originMatch[1]}${target}`
  }

  const slashIndex = manifestUrl.lastIndexOf('/')
  const baseFolder = slashIndex >= 0 ? manifestUrl.slice(0, slashIndex + 1) : manifestUrl
  return `${baseFolder}${target}`
}

export function buildDefaultSoftwareManifestUrl(apiBaseUrl: string): string {
  return joinBaseUrl(apiBaseUrl, '/software_update/manifest')
}

function sanitizeSoftwareUpdateFileName(name: string): string {
  const baseName = stringValue(name).split(/[\\/]/).pop() ?? ''
  return baseName.replace(/[\\/:*?"<>|]/g, '_')
}

function formatUpdateTimestamp(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
    '_',
    pad(date.getHours()),
    pad(date.getMinutes()),
    pad(date.getSeconds()),
  ].join('')
}

function fileNameFromUrl(url: string): string {
  const cleanUrl = stringValue(url).split('?')[0].split('#')[0]
  const encodedName = cleanUrl.slice(cleanUrl.lastIndexOf('/') + 1)
  try {
    return sanitizeSoftwareUpdateFileName(decodeURIComponent(encodedName))
  } catch {
    return sanitizeSoftwareUpdateFileName(encodedName)
  }
}

export function resolveSoftwareUpdateFileName(options: SoftwareUpdateFileNameOptions): string {
  const manifestName = sanitizeSoftwareUpdateFileName(options.fileName)
  if (manifestName) return manifestName

  const urlName = fileNameFromUrl(options.downloadUrl)
  if (urlName) return urlName

  return `MotionStudioUpdate_${formatUpdateTimestamp(options.now ?? new Date())}.exe`
}

function emitSoftwareUpdateProgress(
  onProgress: ((event: SoftwareUpdateProgressEvent) => void) | undefined,
  received: number,
  total: number,
): void {
  const progress = total > 0 ? Math.min(1, Math.max(0, received / total)) : 0
  onProgress?.({ received, total, progress })
}

async function defaultFetchBytes(
  url: string,
  onProgress?: (event: SoftwareUpdateProgressEvent) => void,
): Promise<ArrayBuffer> {
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`)
  }

  const total = Number.parseInt(response.headers.get('content-length') ?? '0', 10) || 0
  const reader = response.body?.getReader()
  if (!reader) {
    const contents = await response.arrayBuffer()
    emitSoftwareUpdateProgress(onProgress, contents.byteLength, total || contents.byteLength)
    return contents
  }

  const chunks: Uint8Array[] = []
  let received = 0
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    if (!value) continue
    chunks.push(value)
    received += value.byteLength
    emitSoftwareUpdateProgress(onProgress, received, total)
  }

  const contents = new Uint8Array(received)
  let offset = 0
  for (const chunk of chunks) {
    contents.set(chunk, offset)
    offset += chunk.byteLength
  }
  if (received > 0 && total <= 0) {
    emitSoftwareUpdateProgress(onProgress, received, received)
  }
  return contents.buffer
}

function defaultBrowserDownload(fileName: string, contents: ArrayBuffer): void {
  const url = URL.createObjectURL(new Blob([contents]))
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function joinSoftwareUpdatePath(folder: string, fileName: string): string {
  const trimmedFolder = stringValue(folder)
  if (!trimmedFolder) return fileName
  if (/[\\/]$/.test(trimmedFolder)) return `${trimmedFolder}${fileName}`
  const separator = trimmedFolder.includes('\\') || /^[a-zA-Z]:$/.test(trimmedFolder) ? '\\' : '/'
  return `${trimmedFolder}${separator}${fileName}`
}

export async function downloadSoftwareUpdatePackage(
  options: SoftwareUpdateDownloadOptions,
  deps: SoftwareUpdateDownloadDependencies = {},
): Promise<SoftwareUpdateDownloadResult> {
  const fileName = resolveSoftwareUpdateFileName({
    fileName: options.fileName,
    downloadUrl: options.url || options.downloadUrl || '',
    now: options.now,
  })
  const fetchBytes = deps.fetchBytes ?? defaultFetchBytes
  const defaultDownloadDirectory = deps.defaultDownloadDirectory ?? getNativeDefaultDownloadDirectory
  const writeFile = deps.writeFile ?? writeNativeFile
  const saveFile = deps.saveFile ?? saveNativeFile
  const browserDownload = deps.browserDownload ?? defaultBrowserDownload
  const contents = await fetchBytes(options.url, options.onProgress)

  const downloadDirectory = stringValue(await defaultDownloadDirectory())
  if (downloadDirectory) {
    const directSaveResult = await writeFile(joinSoftwareUpdatePath(downloadDirectory, fileName), contents)
    if (directSaveResult.status !== 'unavailable') {
      return directSaveResult
    }
  }

  const nativeSaveResult = await saveFile(fileName, contents)

  if (nativeSaveResult.status !== 'unavailable') {
    return nativeSaveResult
  }

  browserDownload(fileName, contents)
  return { status: 'downloaded', fileName }
}

export async function openDownloadedSoftwareUpdate(
  result: SoftwareUpdateDownloadResult,
  autoOpen: boolean,
  deps: SoftwareUpdateOpenDependencies = {},
): Promise<SoftwareUpdateOpenResult> {
  if (!autoOpen || result.status !== 'saved') {
    return { status: 'skipped' }
  }

  const openPath = deps.openPath ?? openNativePath
  return openPath(result.path)
}

export function resolveSoftwareUpdateFolderPath(path: string): string {
  const trimmed = stringValue(path)
  const slashIndex = Math.max(trimmed.lastIndexOf('\\'), trimmed.lastIndexOf('/'))
  if (slashIndex < 0) return ''
  if (slashIndex === 0) return '/'
  if (slashIndex === 2 && /^[a-zA-Z]:[\\/]/.test(trimmed)) {
    return trimmed.slice(0, 3)
  }
  return trimmed.slice(0, slashIndex)
}

export async function openSoftwareUpdateInstallTarget(
  savedPath: string,
  target: SoftwareUpdateInstallTarget,
  deps: SoftwareUpdateOpenDependencies = {},
): Promise<SoftwareUpdateOpenResult> {
  const path = stringValue(savedPath)

  const openPath = deps.openPath ?? openNativePath
  let targetPath = ''
  if (target === 'folder') {
    targetPath = path ? resolveSoftwareUpdateFolderPath(path) : ''
    if (!targetPath) {
      targetPath = stringValue(await (deps.defaultDownloadDirectory ?? getNativeDefaultDownloadDirectory)())
    }
  } else {
    targetPath = path
  }

  if (!targetPath) {
    return { status: 'skipped' }
  }

  const result = await openPath(targetPath)
  if (target === 'install' && result.status === 'opened') {
    await deps.closeApp?.()
  }
  return result
}
