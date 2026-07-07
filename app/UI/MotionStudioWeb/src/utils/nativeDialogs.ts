import { invoke } from '@tauri-apps/api/core'

import { hasTauriRuntime } from './tauriWindow'

interface NativeDirectoryDependencies {
  hasRuntime?: () => boolean
  invokeCommand?: (command: string, args?: Record<string, unknown>) => Promise<unknown>
  defaultDirectory?: string | null
}

export type NativeFileSaveResult =
  | { status: 'saved'; path: string }
  | { status: 'cancelled' }
  | { status: 'unavailable' }

export type NativeSavePathResult =
  | { status: 'selected'; path: string }
  | { status: 'cancelled' }
  | { status: 'unavailable' }

export type NativeOpenPathResult =
  | { status: 'opened'; path: string }
  | { status: 'unavailable' }

export async function selectNativeDirectory(deps: NativeDirectoryDependencies = {}): Promise<string | null> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand = deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))

  if (!runtimeAvailable()) {
    return null
  }

  const defaultDirectory = deps.defaultDirectory?.trim()
  const selected = defaultDirectory
    ? await invokeCommand('select_directory', { defaultDirectory })
    : await invokeCommand('select_directory')
  if (typeof selected !== 'string') return null
  const trimmed = selected.trim()
  return trimmed ? trimmed : null
}

export async function getNativeDefaultDownloadDirectory(
  deps: NativeDirectoryDependencies = {},
): Promise<string | null> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand =
    deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))

  if (!runtimeAvailable()) {
    return null
  }

  const directory = await invokeCommand('default_download_directory')
  if (typeof directory !== 'string') return null
  const trimmed = directory.trim()
  return trimmed ? trimmed : null
}

export async function getNativeDefaultDesktopDirectory(
  deps: NativeDirectoryDependencies = {},
): Promise<string | null> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand =
    deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))

  if (!runtimeAvailable()) {
    return null
  }

  const directory = await invokeCommand('default_desktop_directory')
  if (typeof directory !== 'string') return null
  const trimmed = directory.trim()
  return trimmed ? trimmed : null
}

export async function getNativeDefaultPicturesDirectory(
  deps: NativeDirectoryDependencies = {},
): Promise<string | null> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand =
    deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))

  if (!runtimeAvailable()) {
    return null
  }

  const directory = await invokeCommand('default_pictures_directory')
  if (typeof directory !== 'string') return null
  const trimmed = directory.trim()
  return trimmed ? trimmed : null
}

function toByteArray(contents: ArrayBuffer | Uint8Array): number[] {
  const bytes = contents instanceof Uint8Array ? contents : new Uint8Array(contents)
  return Array.from(bytes)
}

export async function saveNativeFile(
  defaultName: string,
  contents: ArrayBuffer | Uint8Array,
  deps: NativeDirectoryDependencies = {},
): Promise<NativeFileSaveResult> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand = deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))

  if (!runtimeAvailable()) {
    return { status: 'unavailable' }
  }

  const defaultDirectory = deps.defaultDirectory?.trim()
  const selected = await invokeCommand('save_file', {
    defaultName,
    contents: toByteArray(contents),
    ...(defaultDirectory ? { defaultDirectory } : {}),
  })
  if (typeof selected !== 'string') return { status: 'cancelled' }
  const trimmed = selected.trim()
  return trimmed ? { status: 'saved', path: trimmed } : { status: 'cancelled' }
}

export async function writeNativeFile(
  path: string,
  contents: ArrayBuffer | Uint8Array,
  deps: NativeDirectoryDependencies = {},
): Promise<NativeFileSaveResult> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand = deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))
  const trimmedPath = path.trim()

  if (!runtimeAvailable()) {
    return { status: 'unavailable' }
  }
  if (!trimmedPath) {
    return { status: 'cancelled' }
  }

  const selected = await invokeCommand('write_file', {
    path: trimmedPath,
    contents: toByteArray(contents),
  })
  if (typeof selected !== 'string') return { status: 'cancelled' }
  const trimmed = selected.trim()
  return trimmed ? { status: 'saved', path: trimmed } : { status: 'cancelled' }
}

export async function selectNativeSavePath(
  defaultName: string,
  deps: NativeDirectoryDependencies = {},
): Promise<NativeSavePathResult> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand = deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))

  if (!runtimeAvailable()) {
    return { status: 'unavailable' }
  }

  const defaultDirectory = deps.defaultDirectory?.trim()
  const selected = await invokeCommand('save_file_path', {
    defaultName,
    ...(defaultDirectory ? { defaultDirectory } : {}),
  })
  if (typeof selected !== 'string') return { status: 'cancelled' }
  const trimmed = selected.trim()
  return trimmed ? { status: 'selected', path: trimmed } : { status: 'cancelled' }
}

export async function openNativePath(
  path: string,
  deps: NativeDirectoryDependencies = {},
): Promise<NativeOpenPathResult> {
  const runtimeAvailable = deps.hasRuntime ?? hasTauriRuntime
  const invokeCommand = deps.invokeCommand ?? ((command: string, args?: Record<string, unknown>) => invoke<unknown>(command, args))
  const trimmed = path.trim()

  if (!runtimeAvailable() || !trimmed) {
    return { status: 'unavailable' }
  }

  const opened = await invokeCommand('open_path', { path: trimmed })
  return { status: 'opened', path: typeof opened === 'string' && opened.trim() ? opened.trim() : trimmed }
}
