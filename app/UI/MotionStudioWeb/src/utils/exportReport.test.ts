import { describe, expect, it, vi } from 'vitest'

import {
  buildDefaultExportXlsxConfig,
  buildExportInitialDateRange,
  buildQmlExportDefaultFileName,
  buildQmlExportDefaultOutputPath,
  buildQuickExportFileName,
  openSavedExportPath,
  resolveExportFolderPath,
  resolveQuickExportUrl,
  saveExportPayload,
} from './exportReport'

describe('export report helpers', () => {
  it('builds QML ExportConfigView-compatible default xlsx config', () => {
    expect(
      buildDefaultExportXlsxConfig({
        startDate: new Date(2026, 5, 28, 8, 15),
        endDate: new Date(2026, 5, 28, 9, 45),
      }),
    ).toEqual({
      export_type: 'xlsx',
      detection_3d_info: true,
      defect_info: true,
      defect_show_info: true,
      defect_un_show_info: false,
      export_plc_data: false,
      startDate: '202606280815',
      endDate: '202606280945',
    })
  })

  it('initializes export date range from last and first visible coil like QML', () => {
    const range = buildExportInitialDateRange([
      { id: 3, coilNo: 'A', dateTime: '2026-06-28T09:45:00', status: 0, surfaceKey: 'S' },
      { id: 2, coilNo: 'B', dateTime: '2026-06-28T09:00:00', status: 0, surfaceKey: 'S' },
      { id: 1, coilNo: 'C', dateTime: '2026-06-28T08:15:00', status: 0, surfaceKey: 'S' },
    ])

    expect(range).toEqual({
      startDate: new Date(2026, 5, 28, 8, 15),
      endDate: new Date(2026, 5, 28, 9, 45),
    })
  })

  it('builds the QML ExportView default desktop workbook path', () => {
    const date = new Date(2026, 6, 2, 4, 29, 16)

    expect(buildQmlExportDefaultFileName(date)).toBe('2026_07_02 04_29_16.xlsx')
    expect(buildQmlExportDefaultOutputPath('C:\\Users\\operator\\Desktop', date)).toBe(
      'C:\\Users\\operator\\Desktop\\2026_07_02 04_29_16.xlsx',
    )
    expect(buildQmlExportDefaultOutputPath('/home/operator/Desktop/', date)).toBe(
      '/home/operator/Desktop/2026_07_02 04_29_16.xlsx',
    )
  })

  it('resolves quick export buttons to the Python-compatible routes', () => {
    const api = {
      exportToday: () => '/api/export_today',
      export1h: () => '/api/export_1h',
      export24h: () => '/api/export_24h',
    }

    expect(resolveQuickExportUrl('today', api)).toBe('/api/export_today')
    expect(resolveQuickExportUrl('1h', api)).toBe('/api/export_1h')
    expect(resolveQuickExportUrl('24h', api)).toBe('/api/export_24h')
  })

  it('builds stable quick export filenames for native save dialogs', () => {
    const baseName = buildQmlExportDefaultFileName(new Date(2026, 6, 2, 4, 29, 16))

    expect(buildQuickExportFileName('today', baseName)).toBe('2026_07_02 04_29_16_today.xlsx')
    expect(buildQuickExportFileName('1h', baseName)).toBe('2026_07_02 04_29_16_1h.xlsx')
    expect(buildQuickExportFileName('24h', baseName)).toBe('2026_07_02 04_29_16_24h.xlsx')
  })

  it('saves export payloads natively before using browser fallback', async () => {
    const saveFile = vi.fn().mockResolvedValue({ status: 'saved', path: 'D:\\exports\\report.xlsx' })
    const downloadBlob = vi.fn()

    const result = await saveExportPayload(new Uint8Array([80, 75]).buffer, 'report.xlsx', {
      saveFile,
      downloadBlob,
    })

    expect(result).toEqual({ status: 'saved', path: 'D:\\exports\\report.xlsx' })
    expect(saveFile).toHaveBeenCalledWith('report.xlsx', new Uint8Array([80, 75]))
    expect(downloadBlob).not.toHaveBeenCalled()
  })

  it('falls back to browser download only when native save is unavailable', async () => {
    const saveFile = vi.fn().mockResolvedValue({ status: 'unavailable' })
    const downloadBlob = vi.fn()

    const result = await saveExportPayload(new Uint8Array([80, 75]).buffer, 'report.xlsx', {
      saveFile,
      downloadBlob,
    })

    expect(result).toEqual({ status: 'downloaded' })
    expect(downloadBlob).toHaveBeenCalledWith(expect.any(Blob), 'report.xlsx')
  })

  it('does not download when the native save dialog is cancelled', async () => {
    const saveFile = vi.fn().mockResolvedValue({ status: 'cancelled' })
    const downloadBlob = vi.fn()

    const result = await saveExportPayload(new ArrayBuffer(0), 'report.xlsx', {
      saveFile,
      downloadBlob,
    })

    expect(result).toEqual({ status: 'cancelled' })
    expect(downloadBlob).not.toHaveBeenCalled()
  })

  it('resolves the saved export folder like QML tool.fileFolderPath', () => {
    expect(resolveExportFolderPath('D:\\exports\\report.xlsx')).toBe('D:\\exports')
    expect(resolveExportFolderPath('/home/operator/Desktop/report.xlsx')).toBe('/home/operator/Desktop')
    expect(resolveExportFolderPath('/report.xlsx')).toBe('/')
    expect(resolveExportFolderPath('report.xlsx')).toBe('')
  })

  it('opens the saved export file or containing folder after export finishes', async () => {
    const openPath = vi.fn().mockResolvedValue({ status: 'opened', path: 'D:\\exports\\report.xlsx' })

    await expect(openSavedExportPath('D:\\exports\\report.xlsx', 'file', { openPath })).resolves.toBe('native')
    await expect(openSavedExportPath('D:\\exports\\report.xlsx', 'folder', { openPath })).resolves.toBe('native')

    expect(openPath).toHaveBeenNthCalledWith(1, 'D:\\exports\\report.xlsx')
    expect(openPath).toHaveBeenNthCalledWith(2, 'D:\\exports')
  })
})
