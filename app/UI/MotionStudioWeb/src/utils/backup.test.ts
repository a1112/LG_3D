import { describe, expect, it, vi } from 'vitest'

import { buildDatabaseBackupPath, runDatabaseBackupFromNativeSaveDialog, formatBackupTimestamp } from './backup'

describe('database backup path helpers', () => {
  it('formats backup timestamps for file-safe Windows paths', () => {
    expect(formatBackupTimestamp(new Date('2026-06-28T07:30:45'))).toBe('20260628_073045')
  })

  it('builds default SQL and SQLite backup paths under the chosen folder', () => {
    const now = new Date('2026-06-28T07:30:45')

    expect(buildDatabaseBackupPath('D:\\Backup\\LG3D\\', 'sql', now)).toBe(
      'D:\\Backup\\LG3D\\lg3d_backup_20260628_073045.sql',
    )
    expect(buildDatabaseBackupPath('D:/Backup/LG3D', 'db', now)).toBe(
      'D:\\Backup\\LG3D\\lg3d_backup_20260628_073045.db',
    )
  })

  it('runs the QML-style backup menu flow after a native save path is selected', async () => {
    const selectSavePath = vi.fn().mockResolvedValue({
      status: 'selected',
      path: 'D:\\Backup\\LG3D\\lg3d_backup_20260701_103015.db',
    })
    const saveToSql = vi.fn().mockResolvedValue({ state: true })
    const openPath = vi.fn().mockResolvedValue({ status: 'opened', path: 'D:\\Backup\\LG3D\\lg3d_backup_20260701_103015.db' })

    const result = await runDatabaseBackupFromNativeSaveDialog({
      now: new Date('2026-07-01T10:30:15'),
      selectSavePath,
      saveToSql,
      openPath,
    })

    expect(result).toEqual({ status: 'saved', path: 'D:\\Backup\\LG3D\\lg3d_backup_20260701_103015.db' })
    expect(selectSavePath).toHaveBeenCalledWith('lg3d_backup_20260701_103015.db')
    expect(saveToSql).toHaveBeenCalledWith('D:\\Backup\\LG3D\\lg3d_backup_20260701_103015.db')
    expect(openPath).toHaveBeenCalledWith('D:\\Backup\\LG3D\\lg3d_backup_20260701_103015.db')
  })

  it('does not call the backup API when native save path selection is unavailable or cancelled', async () => {
    const saveToSql = vi.fn()

    await expect(
      runDatabaseBackupFromNativeSaveDialog({
        selectSavePath: vi.fn().mockResolvedValue({ status: 'unavailable' }),
        saveToSql,
      }),
    ).resolves.toEqual({ status: 'unavailable' })

    await expect(
      runDatabaseBackupFromNativeSaveDialog({
        selectSavePath: vi.fn().mockResolvedValue({ status: 'cancelled' }),
        saveToSql,
      }),
    ).resolves.toEqual({ status: 'cancelled' })

    expect(saveToSql).not.toHaveBeenCalled()
  })
})
