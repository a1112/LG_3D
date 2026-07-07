import { describe, expect, it, vi } from 'vitest'

import {
  buildBackupImageDefaultName,
  buildBackupImageDefaultPath,
  buildBackupImageInitialRange,
  isBackupImageFinishedMessage,
  openBackupImageFolder,
  resolveBackupImageWsUrl,
} from './backupImage'

describe('QML image backup helpers', () => {
  it('uses visible coil min/max ids for BackupDataView start and end fields', () => {
    expect(
      buildBackupImageInitialRange([
        { id: 193113 },
        { id: 16019 },
        { id: 220000 },
      ]),
    ).toEqual({ fromId: 16019, toId: 220000 })
  })

  it('formats the QML default backup folder name', () => {
    expect(buildBackupImageDefaultName(new Date('2026-06-28T07:30:45'))).toBe('备份_2026_06_28 07_30_45')
  })

  it('builds the QML default backup output path under the desktop directory', () => {
    expect(
      buildBackupImageDefaultPath('C:\\Users\\operator\\Desktop', new Date('2026-06-28T07:30:45')),
    ).toBe('C:\\Users\\operator\\Desktop\\备份_2026_06_28 07_30_45')
  })

  it('resolves websocket urls through the Vite proxy or a direct API base', () => {
    expect(resolveBackupImageWsUrl('/api', '/ws/backupImageTask', 'http://127.0.0.1:3015')).toBe(
      'ws://127.0.0.1:3015/ws/backupImageTask',
    )
    expect(resolveBackupImageWsUrl('http://127.0.0.1:5011', '/ws/backupImageTask')).toBe(
      'ws://127.0.0.1:5011/ws/backupImageTask',
    )
    expect(resolveBackupImageWsUrl('ws://127.0.0.1:5011', '/ws/backupImageTask')).toBe(
      'ws://127.0.0.1:5011/ws/backupImageTask',
    )
  })

  it('treats numeric websocket messages at or above 100 as finished', () => {
    expect(isBackupImageFinishedMessage('99')).toBe(false)
    expect(isBackupImageFinishedMessage('100')).toBe(true)
    expect(isBackupImageFinishedMessage('101')).toBe(true)
    expect(isBackupImageFinishedMessage('not-number')).toBe(false)
  })

  it('opens finished backup folders through Tauri before falling back to file urls', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'opened', path: 'D:\\Backup\\Images' })
    const openWindow = vi.fn()

    await expect(openBackupImageFolder(' D:\\Backup\\Images ', { openNative, openWindow })).resolves.toBe('native')

    expect(openNative).toHaveBeenCalledWith('D:\\Backup\\Images')
    expect(openWindow).not.toHaveBeenCalled()
  })

  it('uses QML-compatible file urls when native folder opening is unavailable', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'unavailable' })
    const openWindow = vi.fn()

    await expect(openBackupImageFolder('D:\\Backup\\Images', { openNative, openWindow })).resolves.toBe('browser')

    expect(openWindow).toHaveBeenCalledWith('file:///D:/Backup/Images', '_blank', 'noopener,noreferrer')
  })
})
