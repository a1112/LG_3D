import { runtimeApi } from '@/services/api'

import {
  openNativePath,
  selectNativeSavePath,
  type NativeOpenPathResult,
  type NativeSavePathResult,
} from './nativeDialogs'

export type DatabaseBackupExtension = 'sql' | 'db'

export type DatabaseBackupMenuResult =
  | { status: 'saved'; path: string }
  | { status: 'failed'; path: string }
  | { status: 'cancelled' }
  | { status: 'unavailable' }

interface DatabaseBackupFromNativeSaveDialogDeps {
  now?: Date
  extension?: DatabaseBackupExtension
  selectSavePath?: (defaultName: string) => Promise<NativeSavePathResult>
  saveToSql?: (path: string) => Promise<unknown>
  openPath?: (path: string) => Promise<NativeOpenPathResult>
}

function pad2(value: number): string {
  return String(value).padStart(2, '0')
}

export function formatBackupTimestamp(date = new Date()): string {
  return [
    date.getFullYear(),
    pad2(date.getMonth() + 1),
    pad2(date.getDate()),
    '_',
    pad2(date.getHours()),
    pad2(date.getMinutes()),
    pad2(date.getSeconds()),
  ].join('')
}

export function buildDatabaseBackupFileName(extension: DatabaseBackupExtension, date = new Date()): string {
  return `lg3d_backup_${formatBackupTimestamp(date)}.${extension}`
}

export function buildDatabaseBackupPath(
  baseFolder: string,
  extension: DatabaseBackupExtension,
  date = new Date(),
): string {
  const normalizedFolder = baseFolder.trim().replace(/\//g, '\\').replace(/\\+$/, '')
  return `${normalizedFolder}\\${buildDatabaseBackupFileName(extension, date)}`
}

function readState(value: unknown): boolean {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false
  return Boolean((value as Record<string, unknown>).state)
}

export async function runDatabaseBackupFromNativeSaveDialog(
  deps: DatabaseBackupFromNativeSaveDialogDeps = {},
): Promise<DatabaseBackupMenuResult> {
  const extension = deps.extension ?? 'db'
  const defaultName = buildDatabaseBackupFileName(extension, deps.now ?? new Date())
  const selectSavePath = deps.selectSavePath ?? selectNativeSavePath
  const saveToSql = deps.saveToSql ?? runtimeApi.saveToSql
  const openPath = deps.openPath ?? openNativePath
  const selected = await selectSavePath(defaultName)

  if (selected.status !== 'selected') {
    return { status: selected.status }
  }

  const result = await saveToSql(selected.path)
  if (!readState(result)) {
    return { status: 'failed', path: selected.path }
  }

  await openPath(selected.path)
  return { status: 'saved', path: selected.path }
}
