import { describe, expect, it, vi } from 'vitest'

import {
  getNativeDefaultDesktopDirectory,
  getNativeDefaultDownloadDirectory,
  getNativeDefaultPicturesDirectory,
  openNativePath,
  saveNativeFile,
  selectNativeDirectory,
  selectNativeSavePath,
  writeNativeFile,
} from './nativeDialogs'

describe('native dialog helpers', () => {
  it('returns null in web preview mode instead of requiring Tauri APIs', async () => {
    const result = await selectNativeDirectory({
      hasRuntime: () => false,
      invokeCommand: vi.fn(),
    })

    expect(result).toBeNull()
  })

  it('invokes the Tauri directory picker command when native runtime is available', async () => {
    const invokeCommand = vi.fn().mockResolvedValue('D:\\images')

    const result = await selectNativeDirectory({
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toBe('D:\\images')
    expect(invokeCommand).toHaveBeenCalledWith('select_directory')
  })

  it('passes a QML pictures default directory to native folder selection when provided', async () => {
    const invokeCommand = vi.fn().mockResolvedValue('C:\\Users\\operator\\Pictures\\defects')

    const result = await selectNativeDirectory({
      hasRuntime: () => true,
      invokeCommand,
      defaultDirectory: ' C:\\Users\\operator\\Pictures ',
    })

    expect(result).toBe('C:\\Users\\operator\\Pictures\\defects')
    expect(invokeCommand).toHaveBeenCalledWith('select_directory', {
      defaultDirectory: 'C:\\Users\\operator\\Pictures',
    })
  })

  it('normalizes cancelled or non-string native selections to null', async () => {
    await expect(
      selectNativeDirectory({
        hasRuntime: () => true,
        invokeCommand: vi.fn().mockResolvedValue(''),
      }),
    ).resolves.toBeNull()

    await expect(
      selectNativeDirectory({
        hasRuntime: () => true,
        invokeCommand: vi.fn().mockResolvedValue(null),
      }),
    ).resolves.toBeNull()
  })

  it('resolves the QML default download directory through Tauri when available', async () => {
    const invokeCommand = vi.fn().mockResolvedValue(' C:\\Users\\operator\\Downloads ')

    const result = await getNativeDefaultDownloadDirectory({
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toBe('C:\\Users\\operator\\Downloads')
    expect(invokeCommand).toHaveBeenCalledWith('default_download_directory')
  })

  it('resolves the QML image-backup default desktop directory through Tauri when available', async () => {
    const invokeCommand = vi.fn().mockResolvedValue(' C:\\Users\\operator\\Desktop ')

    const result = await getNativeDefaultDesktopDirectory({
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toBe('C:\\Users\\operator\\Desktop')
    expect(invokeCommand).toHaveBeenCalledWith('default_desktop_directory')
  })

  it('resolves the QML defect-export default pictures directory through Tauri when available', async () => {
    const invokeCommand = vi.fn().mockResolvedValue(' C:\\Users\\operator\\Pictures ')

    const result = await getNativeDefaultPicturesDirectory({
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toBe('C:\\Users\\operator\\Pictures')
    expect(invokeCommand).toHaveBeenCalledWith('default_pictures_directory')
  })

  it('returns null for the default desktop directory outside Tauri or when native returns nothing', async () => {
    const webInvokeCommand = vi.fn()

    await expect(
      getNativeDefaultDesktopDirectory({
        hasRuntime: () => false,
        invokeCommand: webInvokeCommand,
      }),
    ).resolves.toBeNull()
    expect(webInvokeCommand).not.toHaveBeenCalled()

    await expect(
      getNativeDefaultDesktopDirectory({
        hasRuntime: () => true,
        invokeCommand: vi.fn().mockResolvedValue(''),
      }),
    ).resolves.toBeNull()
  })

  it('returns null for the default download directory outside Tauri or when native returns nothing', async () => {
    const webInvokeCommand = vi.fn()

    await expect(
      getNativeDefaultDownloadDirectory({
        hasRuntime: () => false,
        invokeCommand: webInvokeCommand,
      }),
    ).resolves.toBeNull()
    expect(webInvokeCommand).not.toHaveBeenCalled()

    await expect(
      getNativeDefaultDownloadDirectory({
        hasRuntime: () => true,
        invokeCommand: vi.fn().mockResolvedValue(''),
      }),
    ).resolves.toBeNull()
  })

  it('returns null for the default pictures directory outside Tauri or when native returns nothing', async () => {
    const webInvokeCommand = vi.fn()

    await expect(
      getNativeDefaultPicturesDirectory({
        hasRuntime: () => false,
        invokeCommand: webInvokeCommand,
      }),
    ).resolves.toBeNull()
    expect(webInvokeCommand).not.toHaveBeenCalled()

    await expect(
      getNativeDefaultPicturesDirectory({
        hasRuntime: () => true,
        invokeCommand: vi.fn().mockResolvedValue(''),
      }),
    ).resolves.toBeNull()
  })

  it('returns unavailable for native file saves in web preview mode', async () => {
    const invokeCommand = vi.fn()

    const result = await saveNativeFile('report.xlsx', new Uint8Array([80, 75, 3]), {
      hasRuntime: () => false,
      invokeCommand,
    })

    expect(result).toEqual({ status: 'unavailable' })
    expect(invokeCommand).not.toHaveBeenCalled()
  })

  it('writes bytes through the Tauri save-file command when native runtime is available', async () => {
    const invokeCommand = vi.fn().mockResolvedValue('D:\\exports\\report.xlsx')

    const result = await saveNativeFile('report.xlsx', new Uint8Array([80, 75, 3]), {
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toEqual({ status: 'saved', path: 'D:\\exports\\report.xlsx' })
    expect(invokeCommand).toHaveBeenCalledWith('save_file', {
      defaultName: 'report.xlsx',
      contents: [80, 75, 3],
    })
  })

  it('writes bytes directly to a QML SimpleFileInput-selected save path', async () => {
    const invokeCommand = vi.fn().mockResolvedValue('D:\\exports\\selected_report.xlsx')

    const result = await writeNativeFile(' D:\\exports\\selected_report.xlsx ', new Uint8Array([80, 75, 3]), {
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toEqual({ status: 'saved', path: 'D:\\exports\\selected_report.xlsx' })
    expect(invokeCommand).toHaveBeenCalledWith('write_file', {
      path: 'D:\\exports\\selected_report.xlsx',
      contents: [80, 75, 3],
    })
  })

  it('does not try direct selected-path writes outside Tauri or with an empty path', async () => {
    const webInvokeCommand = vi.fn()

    await expect(
      writeNativeFile('D:\\exports\\selected_report.xlsx', new Uint8Array([80, 75]), {
        hasRuntime: () => false,
        invokeCommand: webInvokeCommand,
      }),
    ).resolves.toEqual({ status: 'unavailable' })
    expect(webInvokeCommand).not.toHaveBeenCalled()

    const emptyInvokeCommand = vi.fn()
    await expect(
      writeNativeFile('   ', new Uint8Array([80, 75]), {
        hasRuntime: () => true,
        invokeCommand: emptyInvokeCommand,
      }),
    ).resolves.toEqual({ status: 'cancelled' })
    expect(emptyInvokeCommand).not.toHaveBeenCalled()
  })

  it('passes a QML desktop default directory to native file saves when provided', async () => {
    const invokeCommand = vi.fn().mockResolvedValue('C:\\Users\\operator\\Desktop\\report.xlsx')

    const result = await saveNativeFile('report.xlsx', new Uint8Array([80, 75, 3]), {
      hasRuntime: () => true,
      invokeCommand,
      defaultDirectory: ' C:\\Users\\operator\\Desktop ',
    })

    expect(result).toEqual({ status: 'saved', path: 'C:\\Users\\operator\\Desktop\\report.xlsx' })
    expect(invokeCommand).toHaveBeenCalledWith('save_file', {
      defaultName: 'report.xlsx',
      contents: [80, 75, 3],
      defaultDirectory: 'C:\\Users\\operator\\Desktop',
    })
  })

  it('reports native save cancellation without falling back implicitly', async () => {
    await expect(
      saveNativeFile('report.xlsx', new ArrayBuffer(0), {
        hasRuntime: () => true,
        invokeCommand: vi.fn().mockResolvedValue(null),
      }),
    ).resolves.toEqual({ status: 'cancelled' })
  })

  it('selects a native save path without writing placeholder file contents', async () => {
    const invokeCommand = vi.fn().mockResolvedValue('D:\\Backup\\lg3d_backup_20260701_103015.db')

    const result = await selectNativeSavePath('lg3d_backup_20260701_103015.db', {
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toEqual({ status: 'selected', path: 'D:\\Backup\\lg3d_backup_20260701_103015.db' })
    expect(invokeCommand).toHaveBeenCalledWith('save_file_path', {
      defaultName: 'lg3d_backup_20260701_103015.db',
    })
  })

  it('reports native save-path selection cancellation and web-preview unavailability', async () => {
    await expect(
      selectNativeSavePath('backup.db', {
        hasRuntime: () => true,
        invokeCommand: vi.fn().mockResolvedValue(null),
      }),
    ).resolves.toEqual({ status: 'cancelled' })

    const invokeCommand = vi.fn()
    await expect(
      selectNativeSavePath('backup.db', {
        hasRuntime: () => false,
        invokeCommand,
      }),
    ).resolves.toEqual({ status: 'unavailable' })
    expect(invokeCommand).not.toHaveBeenCalled()
  })

  it('opens a saved local path through Tauri when native runtime is available', async () => {
    const invokeCommand = vi.fn().mockResolvedValue('D:\\Downloads\\MotionStudio.exe')

    const result = await openNativePath(' D:\\Downloads\\MotionStudio.exe ', {
      hasRuntime: () => true,
      invokeCommand,
    })

    expect(result).toEqual({ status: 'opened', path: 'D:\\Downloads\\MotionStudio.exe' })
    expect(invokeCommand).toHaveBeenCalledWith('open_path', {
      path: 'D:\\Downloads\\MotionStudio.exe',
    })
  })

  it('does not try to open paths in web preview mode', async () => {
    const invokeCommand = vi.fn()

    const result = await openNativePath('D:\\Downloads\\MotionStudio.exe', {
      hasRuntime: () => false,
      invokeCommand,
    })

    expect(result).toEqual({ status: 'unavailable' })
    expect(invokeCommand).not.toHaveBeenCalled()
  })
})
