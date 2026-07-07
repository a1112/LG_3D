import { describe, expect, it, vi } from 'vitest'

import {
  buildCoilListDataSourceUrl,
  buildCoilSaveFolderPath,
  buildCoilSaveFolderNativePath,
  buildCoilSaveFolderUrl,
  buildRawCoilSearchUrl,
  getCoilListReDetectionRange,
  getCoilCopyText,
  getCurrentCoilReDetectionRange,
  getSurfaceSaveFolder,
  openCoilSaveFolderUrl,
  openQmlExternalUrl,
  resolveQmlCoilListDataSourceUrl,
  runClipMaxAndGetFolderUrl,
} from './coilActions'
import type { CoilData } from '@/types'

const coil: CoilData = {
  id: 16019,
  coilNo: '4V07441200',
  dateTime: '2026-06-28 14:41:00',
  status: -3,
  surfaceKey: 'S',
  grade: 0,
  defectCountS: 0,
  defectCountL: 0,
}

describe('coil action helpers', () => {
  it('builds copy payloads matching the QML left-list actions', () => {
    expect(getCoilCopyText(coil, 'coilNo')).toBe('4V07441200')
    expect(getCoilCopyText(coil, 'coilId')).toBe('16019')
    expect(getCoilCopyText(coil, 'dateTime')).toBe('2026-06-28 14:41:00')
  })

  it('builds a raw backend search URL for the selected coil', () => {
    expect(buildRawCoilSearchUrl(16019, '/api/')).toBe('/api/search/coilId/16019')
    expect(buildRawCoilSearchUrl(16019, 'http://127.0.0.1:5011/')).toBe(
      'http://127.0.0.1:5011/search/coilId/16019',
    )
  })

  it('builds the QML list data-source URL from the active coilList request', () => {
    expect(buildCoilListDataSourceUrl(80, '/api/')).toBe('/api/coilList/80')
    expect(buildCoilListDataSourceUrl(80, 'http://127.0.0.1:5011/')).toBe('http://127.0.0.1:5011/coilList/80')
  })

  it('resolves the QML latest coilList data-source URL from API history', () => {
    const fallbackUrl = buildCoilListDataSourceUrl(80, '/api')

    expect(
      resolveQmlCoilListDataSourceUrl(
        [
          { method: 'GET', url: '/api/flush/193110' },
          { method: 'GET', url: '/api/search/coilId/16019' },
          { method: 'GET', url: '/api/coilList/120' },
          { method: 'GET', url: '/api/coilList/80' },
        ],
        fallbackUrl,
      ),
    ).toBe('/api/coilList/120')
    expect(
      resolveQmlCoilListDataSourceUrl(
        [
          { method: 'GET', url: 'http://127.0.0.1:5011/flush/193110' },
          { method: 'GET', url: 'http://127.0.0.1:5011/coilList/60' },
        ],
        fallbackUrl,
      ),
    ).toBe('http://127.0.0.1:5011/coilList/60')
    expect(resolveQmlCoilListDataSourceUrl([{ method: 'GET', url: '/api/search/coilNo/ABC' }], fallbackUrl)).toBe(
      fallbackUrl,
    )
  })

  it('builds local save-folder URLs from the server info saveFolder like QML SurfaceData.getBaseUrl', () => {
    const url = buildCoilSaveFolderUrl({
      coilId: 193113,
      surfaceKey: 'S',
      saveFolder: 'F:\\datasets\\LG_3D_DataBase\\DataSave\\Save_S',
      serverHost: '127.0.0.1',
    })

    expect(url).toBe('file:///F:/datasets/LG_3D_DataBase/DataSave/Save_S/193113')
    expect(buildCoilSaveFolderPath(url)).toBe('F:/datasets/LG_3D_DataBase/DataSave/Save_S/193113')
  })

  it('builds shared save-folder URLs when the API server is remote like QML SurfaceData.getSharedFolderBase', () => {
    const url = buildCoilSaveFolderUrl({
      coilId: 193113,
      surfaceKey: 'L',
      saveFolder: 'D:\\ignored\\Save_L',
      serverHost: '10.10.2.5',
      sharedFolderBaseName: 'Save_',
    })

    expect(url).toBe('file:////10.10.2.5/Save_L/193113')
    expect(buildCoilSaveFolderPath(url)).toBe('/10.10.2.5/Save_L/193113')
  })

  it('converts local and shared file URLs into native open paths for Tauri', () => {
    expect(buildCoilSaveFolderNativePath('file:///F:/Data/Save_S/193113')).toBe('F:\\Data\\Save_S\\193113')
    expect(buildCoilSaveFolderNativePath('file:////10.10.2.5/Save_L/193113')).toBe(
      '\\\\10.10.2.5\\Save_L\\193113',
    )
  })

  it('opens save folders through Tauri before falling back to browser file URLs', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'opened', path: 'F:\\Data\\Save_S\\193113' })
    const openWindow = vi.fn()

    await expect(openCoilSaveFolderUrl('file:///F:/Data/Save_S/193113', { openNative, openWindow })).resolves.toBe(
      'native',
    )

    expect(openNative).toHaveBeenCalledWith('F:\\Data\\Save_S\\193113')
    expect(openWindow).not.toHaveBeenCalled()
  })

  it('keeps the QML file URL browser fallback when native folder opening is unavailable', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'unavailable' })
    const openWindow = vi.fn()

    await expect(openCoilSaveFolderUrl('file:////10.10.2.5/Save_L/193113', { openNative, openWindow })).resolves.toBe(
      'browser',
    )

    expect(openNative).toHaveBeenCalledWith('\\\\10.10.2.5\\Save_L\\193113')
    expect(openWindow).toHaveBeenCalledWith('file:////10.10.2.5/Save_L/193113', '_blank', 'noopener,noreferrer')
  })

  it('opens absolute QML external backend URLs through Tauri before browser fallback', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'opened', path: 'http://127.0.0.1:5011/search/coilId/16019' })
    const openWindow = vi.fn()

    await expect(
      openQmlExternalUrl('http://127.0.0.1:5011/search/coilId/16019', { openNative, openWindow }),
    ).resolves.toBe('native')

    expect(openNative).toHaveBeenCalledWith('http://127.0.0.1:5011/search/coilId/16019')
    expect(openWindow).not.toHaveBeenCalled()
  })

  it('keeps relative QML external backend URLs inside the webview instead of native path opening', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'opened', path: '/api/search/coilId/16019' })
    const openWindow = vi.fn()

    await expect(openQmlExternalUrl('/api/search/coilId/16019', { openNative, openWindow })).resolves.toBe('browser')

    expect(openNative).not.toHaveBeenCalled()
    expect(openWindow).toHaveBeenCalledWith('/api/search/coilId/16019', '_blank', 'noopener,noreferrer')
  })

  it('keeps the browser fallback for absolute QML external backend URLs when native open is unavailable', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'unavailable' })
    const openWindow = vi.fn()

    await expect(openQmlExternalUrl('http://127.0.0.1:5011/coilList/80', { openNative, openWindow })).resolves.toBe(
      'browser',
    )

    expect(openNative).toHaveBeenCalledWith('http://127.0.0.1:5011/coilList/80')
    expect(openWindow).toHaveBeenCalledWith('http://127.0.0.1:5011/coilList/80', '_blank', 'noopener,noreferrer')
  })

  it('reads surface save folders from the /info payload', () => {
    const info = {
      surfaceS: { saveFolder: 'F:\\DataSave\\Save_S' },
      surfaceL: { saveFolder: 'F:\\DataSave\\Save_L' },
    }

    expect(getSurfaceSaveFolder(info, 'S')).toBe('F:\\DataSave\\Save_S')
    expect(getSurfaceSaveFolder(info, 'L')).toBe('F:\\DataSave\\Save_L')
    expect(getSurfaceSaveFolder({}, 'S')).toBe('')
  })

  it('runs QML-compatible clip-max generation in the folder that will be opened', async () => {
    const calls: Array<[number, string, string | undefined]> = []

    const folderUrl = await runClipMaxAndGetFolderUrl({
      coilId: 193113,
      surfaceKey: 'S',
      saveFolder: 'F:\\datasets\\LG_3D_DataBase\\DataSave\\Save_S',
      serverHost: '127.0.0.1',
      clipMaxImage: async (coilId, surfaceKey, saveUrl) => {
        calls.push([coilId, surfaceKey, saveUrl])
        return null
      },
    })

    expect(calls).toEqual([[193113, 'S', 'F:/datasets/LG_3D_DataBase/DataSave/Save_S/193113']])
    expect(folderUrl).toBe('file:///F:/datasets/LG_3D_DataBase/DataSave/Save_S/193113')
  })

  it('rejects invalid clip-max coil ids before calling the side-effecting API', async () => {
    const clipMaxImage = vi.fn(async () => null)

    await expect(
      runClipMaxAndGetFolderUrl({
        coilId: 0,
        surfaceKey: 'S',
        saveFolder: 'F:\\datasets\\LG_3D_DataBase\\DataSave\\Save_S',
        serverHost: '127.0.0.1',
        clipMaxImage,
      }),
    ).rejects.toThrow('valid coil id')

    expect(clipMaxImage).not.toHaveBeenCalled()
  })

  it('rejects invalid clip-max surfaces before calling the side-effecting API', async () => {
    const clipMaxImage = vi.fn(async () => null)

    await expect(
      runClipMaxAndGetFolderUrl({
        coilId: 193113,
        surfaceKey: 'X' as 'S',
        saveFolder: 'F:\\datasets\\LG_3D_DataBase\\DataSave\\Save_S',
        serverHost: '127.0.0.1',
        clipMaxImage,
      }),
    ).rejects.toThrow('valid surface')

    expect(clipMaxImage).not.toHaveBeenCalled()
  })

  it('builds the current-coil re-detection range like QML popupReDetectionView(id, id)', () => {
    expect(getCurrentCoilReDetectionRange(coil)).toEqual({ fromId: 16019, toId: 16019 })
    expect(getCurrentCoilReDetectionRange(null)).toEqual({ fromId: 0, toId: 0 })
  })

  it('builds the list re-detection range from the visible list edges like QML currentCoilListModel', () => {
    const coils: CoilData[] = [
      { ...coil, id: 193113 },
      { ...coil, id: 16040 },
      { ...coil, id: 16019 },
    ]

    expect(getCoilListReDetectionRange(coils)).toEqual({ fromId: 16019, toId: 193113 })
    expect(getCoilListReDetectionRange([])).toEqual({ fromId: 0, toId: 0 })
  })
})
