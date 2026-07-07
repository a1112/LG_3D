import { describe, expect, it, vi } from 'vitest'

import {
  buildDefaultSoftwareManifestUrl,
  compareSoftwareVersions,
  downloadSoftwareUpdatePackage,
  openDownloadedSoftwareUpdate,
  openSoftwareUpdateInstallTarget,
  resolveSoftwareUpdateFolderPath,
  resolveSoftwareUpdateFileName,
  normalizeSoftwareUpdateManifest,
  resolveSoftwareUpdateUrl,
} from './softwareUpdate'

describe('software update helpers', () => {
  it('compares QML-style dotted versions numerically', () => {
    expect(compareSoftwareVersions('0.2.10', '0.2.4')).toBe(1)
    expect(compareSoftwareVersions('v1.0', '1.0.0')).toBe(0)
    expect(compareSoftwareVersions('1.9.9', '1.10.0')).toBe(-1)
  })

  it('normalizes software update manifests accepted by QML SoftwareUpdate', () => {
    expect(
      normalizeSoftwareUpdateManifest({
        data: {
          latestVersion: '0.2.4',
          packageUrl: '/updates/MotionStudio_0.2.4.exe',
          fileName: 'MotionStudio_0.2.4.exe',
          releaseNotes: '修复渲染与导出',
        },
      }),
    ).toEqual({
      version: '0.2.4',
      downloadUrl: '/updates/MotionStudio_0.2.4.exe',
      fileName: 'MotionStudio_0.2.4.exe',
      releaseNotes: '修复渲染与导出',
    })
  })

  it('resolves relative update package URLs from the manifest URL', () => {
    expect(resolveSoftwareUpdateUrl('/packages/app.exe', 'http://127.0.0.1:5011/software_update/manifest')).toBe(
      'http://127.0.0.1:5011/packages/app.exe',
    )
    expect(resolveSoftwareUpdateUrl('app.exe', 'http://127.0.0.1:5011/software_update/manifest')).toBe(
      'http://127.0.0.1:5011/software_update/app.exe',
    )
  })

  it('builds the default manifest URL from the active API base', () => {
    expect(buildDefaultSoftwareManifestUrl('/api')).toBe('/api/software_update/manifest')
    expect(buildDefaultSoftwareManifestUrl('http://127.0.0.1:5011')).toBe(
      'http://127.0.0.1:5011/software_update/manifest',
    )
  })

  it('resolves QML-compatible update package file names', () => {
    expect(
      resolveSoftwareUpdateFileName({
        fileName: ' MotionStudio:0.2.4?.exe ',
        downloadUrl: '',
        now: new Date('2026-06-29T07:30:45'),
      }),
    ).toBe('MotionStudio_0.2.4_.exe')
    expect(
      resolveSoftwareUpdateFileName({
        fileName: '',
        downloadUrl: 'http://127.0.0.1:5011/packages/MotionStudio%200.2.4.exe?token=1',
        now: new Date('2026-06-29T07:30:45'),
      }),
    ).toBe('MotionStudio 0.2.4.exe')
    expect(
      resolveSoftwareUpdateFileName({
        fileName: '',
        downloadUrl: '',
        now: new Date('2026-06-29T07:30:45'),
      }),
    ).toBe('MotionStudioUpdate_20260629_073045.exe')
  })

  it('saves update packages through Tauri when native save is available', async () => {
    const saveFile = vi.fn().mockResolvedValue({ status: 'saved', path: 'D:\\Downloads\\MotionStudio.exe' })
    const browserDownload = vi.fn()

    const result = await downloadSoftwareUpdatePackage(
      {
        url: 'http://127.0.0.1:5011/packages/MotionStudio.exe',
        fileName: '',
        now: new Date('2026-06-29T07:30:45'),
      },
      {
        fetchBytes: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3]).buffer),
        saveFile,
        browserDownload,
      },
    )

    expect(result).toEqual({ status: 'saved', path: 'D:\\Downloads\\MotionStudio.exe' })
    expect(saveFile).toHaveBeenCalledWith('MotionStudio.exe', expect.any(ArrayBuffer))
    expect(browserDownload).not.toHaveBeenCalled()
  })

  it('writes update packages directly into the QML default download folder when available', async () => {
    const saveFile = vi.fn()
    const browserDownload = vi.fn()
    const writeFile = vi.fn().mockResolvedValue({ status: 'saved', path: 'D:\\Downloads\\MotionStudio.exe' })

    const result = await downloadSoftwareUpdatePackage(
      {
        url: 'http://127.0.0.1:5011/packages/MotionStudio.exe',
        fileName: '',
        now: new Date('2026-06-29T07:30:45'),
      },
      {
        fetchBytes: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3]).buffer),
        defaultDownloadDirectory: vi.fn().mockResolvedValue('D:\\Downloads'),
        writeFile,
        saveFile,
        browserDownload,
      },
    )

    expect(result).toEqual({ status: 'saved', path: 'D:\\Downloads\\MotionStudio.exe' })
    expect(writeFile).toHaveBeenCalledWith('D:\\Downloads\\MotionStudio.exe', expect.any(ArrayBuffer))
    expect(saveFile).not.toHaveBeenCalled()
    expect(browserDownload).not.toHaveBeenCalled()
  })

  it('falls back to browser download when Tauri save is unavailable', async () => {
    const browserDownload = vi.fn()

    const result = await downloadSoftwareUpdatePackage(
      {
        url: 'http://127.0.0.1:5011/packages/MotionStudio.exe',
        fileName: 'setup.exe',
        now: new Date('2026-06-29T07:30:45'),
      },
      {
        fetchBytes: vi.fn().mockResolvedValue(new Uint8Array([1, 2, 3]).buffer),
        saveFile: vi.fn().mockResolvedValue({ status: 'unavailable' }),
        browserDownload,
      },
    )

    expect(result).toEqual({ status: 'downloaded', fileName: 'setup.exe' })
    expect(browserDownload).toHaveBeenCalledWith('setup.exe', expect.any(ArrayBuffer))
  })

  it('reports QML-style download byte progress while fetching update packages', async () => {
    const progressEvents: Array<{ received: number; total: number; progress: number }> = []

    await downloadSoftwareUpdatePackage(
      {
        url: 'http://127.0.0.1:5011/packages/MotionStudio.exe',
        fileName: 'setup.exe',
        onProgress: (event) => progressEvents.push(event),
      },
      {
        fetchBytes: async (_url, onProgress) => {
          onProgress?.({ received: 2, total: 4, progress: 0.5 })
          onProgress?.({ received: 4, total: 4, progress: 1 })
          return new Uint8Array([1, 2, 3, 4]).buffer
        },
        saveFile: vi.fn().mockResolvedValue({ status: 'saved', path: 'D:\\Downloads\\setup.exe' }),
      },
    )

    expect(progressEvents).toEqual([
      { received: 2, total: 4, progress: 0.5 },
      { received: 4, total: 4, progress: 1 },
    ])
  })

  it('opens the saved installer only when auto-open is enabled', async () => {
    const openPath = vi.fn().mockResolvedValue({ status: 'opened', path: 'D:\\Downloads\\MotionStudio.exe' })

    await expect(
      openDownloadedSoftwareUpdate(
        { status: 'saved', path: 'D:\\Downloads\\MotionStudio.exe' },
        true,
        { openPath },
      ),
    ).resolves.toEqual({ status: 'opened', path: 'D:\\Downloads\\MotionStudio.exe' })
    expect(openPath).toHaveBeenCalledWith('D:\\Downloads\\MotionStudio.exe')

    await expect(
      openDownloadedSoftwareUpdate(
        { status: 'saved', path: 'D:\\Downloads\\MotionStudio.exe' },
        false,
        { openPath },
      ),
    ).resolves.toEqual({ status: 'skipped' })
    await expect(
      openDownloadedSoftwareUpdate(
        { status: 'downloaded', fileName: 'MotionStudio.exe' },
        true,
        { openPath },
      ),
    ).resolves.toEqual({ status: 'skipped' })
    expect(openPath).toHaveBeenCalledTimes(1)
  })

  it('resolves the saved update package folder for Windows and POSIX paths', () => {
    expect(resolveSoftwareUpdateFolderPath(' D:\\Downloads\\MotionStudio.exe ')).toBe('D:\\Downloads')
    expect(resolveSoftwareUpdateFolderPath('D:\\MotionStudio.exe')).toBe('D:\\')
    expect(resolveSoftwareUpdateFolderPath('C:/Users/operator/Downloads/MotionStudio.msi')).toBe(
      'C:/Users/operator/Downloads',
    )
    expect(resolveSoftwareUpdateFolderPath('/opt/lg3d/MotionStudio.zip')).toBe('/opt/lg3d')
    expect(resolveSoftwareUpdateFolderPath('MotionStudio.exe')).toBe('')
  })

  it('opens QML-style update package actions from the saved path', async () => {
    const openPath = vi.fn().mockImplementation(async (path: string) => ({ status: 'opened', path }))
    const closeApp = vi.fn().mockResolvedValue(undefined)

    await expect(
      openSoftwareUpdateInstallTarget('D:\\Downloads\\MotionStudio.exe', 'folder', { openPath, closeApp }),
    ).resolves.toEqual({ status: 'opened', path: 'D:\\Downloads' })
    await expect(
      openSoftwareUpdateInstallTarget('D:\\Downloads\\MotionStudio.exe', 'package', { openPath, closeApp }),
    ).resolves.toEqual({ status: 'opened', path: 'D:\\Downloads\\MotionStudio.exe' })
    await expect(
      openSoftwareUpdateInstallTarget('D:\\Downloads\\MotionStudio.exe', 'install', { openPath, closeApp }),
    ).resolves.toEqual({ status: 'opened', path: 'D:\\Downloads\\MotionStudio.exe' })

    expect(openPath).toHaveBeenNthCalledWith(1, 'D:\\Downloads')
    expect(openPath).toHaveBeenNthCalledWith(2, 'D:\\Downloads\\MotionStudio.exe')
    expect(openPath).toHaveBeenNthCalledWith(3, 'D:\\Downloads\\MotionStudio.exe')
    expect(closeApp).toHaveBeenCalledTimes(1)
  })

  it('opens the QML default download folder before an update package has been saved', async () => {
    const openPath = vi.fn().mockImplementation(async (path: string) => ({ status: 'opened', path }))
    const defaultDownloadDirectory = vi.fn().mockResolvedValue('C:\\Users\\operator\\Downloads')

    await expect(
      openSoftwareUpdateInstallTarget('', 'folder', {
        openPath,
        defaultDownloadDirectory,
      }),
    ).resolves.toEqual({ status: 'opened', path: 'C:\\Users\\operator\\Downloads' })

    expect(defaultDownloadDirectory).toHaveBeenCalledTimes(1)
    expect(openPath).toHaveBeenCalledWith('C:\\Users\\operator\\Downloads')
  })

  it('skips update package actions when there is no saved local path', async () => {
    const openPath = vi.fn()
    const closeApp = vi.fn()
    const defaultDownloadDirectory = vi.fn().mockResolvedValue(null)

    await expect(
      openSoftwareUpdateInstallTarget('', 'folder', { openPath, closeApp, defaultDownloadDirectory }),
    ).resolves.toEqual({
      status: 'skipped',
    })
    await expect(openSoftwareUpdateInstallTarget('', 'package', { openPath, closeApp })).resolves.toEqual({
      status: 'skipped',
    })
    await expect(openSoftwareUpdateInstallTarget('', 'install', { openPath, closeApp })).resolves.toEqual({
      status: 'skipped',
    })

    expect(openPath).not.toHaveBeenCalled()
    expect(closeApp).not.toHaveBeenCalled()
  })
})
