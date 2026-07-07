import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import backupImageModalSource from './index.tsx?raw'

const qmlSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/Backup/BackupDataView.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./BackupImageModal.css', import.meta.url)), 'utf8')

describe('BackupImageModal QML websocket parity', () => {
  it('mirrors QML BackupDataView with a body title instead of an AntD modal title', () => {
    expect(qmlSource).toContain('width: 590')
    expect(qmlSource).toContain('text: "数据备份"')
    expect(qmlSource).toContain('font.pixelSize: 25')
    expect(qmlSource).toContain('font.family:"Microsoft YaHei"')
    expect(qmlSource).toContain('font.bold: true')
    expect(qmlSource).toContain('Material.color(Material.Orange)')
    expect(backupImageModalSource).toContain('title={null}')
    expect(backupImageModalSource).not.toContain('<Modal title="数据备份"')
    expect(backupImageModalSource).toContain('width={590}')
    expect(backupImageModalSource).toContain('data-qml-backup-data-view')
    expect(backupImageModalSource).toContain('data-qml-backup-data-title')
    expect(backupImageModalSource).toMatch(
      /<div[\s\S]*data-qml-backup-data-view[\s\S]*<strong[\s\S]*data-qml-backup-data-title[\s\S]*数据备份/,
    )
    expect(styleSource).toContain('.backup-image-title')
    expect(styleSource).toContain('font-family: "Microsoft YaHei", Inter, sans-serif;')
    expect(styleSource).toContain('font-size: 25px;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('color: #faad14;')
  })

  it('opens the backup websocket when the modal opens like QML BackupDataView', () => {
    const openEffect = backupImageModalSource.slice(
      backupImageModalSource.indexOf('useEffect(() => {'),
      backupImageModalSource.indexOf('const chooseFolder'),
    )

    expect(openEffect).toContain('new WebSocket(resolveBackupImageWsUrl')
    expect(openEffect).toContain('socketRef.current = socket')
    expect(openEffect).toContain('socket.onmessage')
  })

  it('initializes the default output path from the QML desktop location', () => {
    const openEffect = backupImageModalSource.slice(
      backupImageModalSource.indexOf('useEffect(() => {'),
      backupImageModalSource.indexOf('const chooseFolder'),
    )

    expect(qmlSource).toContain('StandardPaths.DesktopLocation')
    expect(qmlSource).toContain('placeholderText:"桌面/"+ root.outputName')
    expect(backupImageModalSource).not.toContain("D:\\\\Backup\\\\LG3D\\\\Images")
    expect(backupImageModalSource).toContain("const QML_BACKUP_FALLBACK_DESKTOP = '桌面'")
    expect(backupImageModalSource).toContain('buildBackupImageDefaultPath(QML_BACKUP_FALLBACK_DESKTOP)')
    expect(openEffect).toContain('getNativeDefaultDesktopDirectory')
    expect(openEffect).toContain('buildBackupImageDefaultPath')
    expect(openEffect).toContain('buildBackupImageDefaultPath(QML_BACKUP_FALLBACK_DESKTOP, openedAt)')
  })

  it('sends the backup payload through the existing websocket instead of creating a new one on click', () => {
    const startBackup = backupImageModalSource.slice(
      backupImageModalSource.indexOf('const startBackup'),
      backupImageModalSource.indexOf('const canChange'),
    )

    expect(startBackup).not.toContain('new WebSocket')
    expect(startBackup).toContain('const socket = socketRef.current')
    expect(startBackup).toContain('socket.send(JSON.stringify({ from_id: fromId, to_id: toId, folder: outputPath.trim() }))')
  })

  it('keeps QML BackupDataView open-folder action visible while running or finished', () => {
    const actionArea = backupImageModalSource.slice(
      backupImageModalSource.indexOf('<div className="backup-image-actions">'),
      backupImageModalSource.indexOf('<Button type="primary"'),
    )

    expect(actionArea).toContain("status === 'running' || status === 'finished'")
    expect(actionArea).toContain('openBackupImageFolder(outputPath)')
  })

  it('hides the QML BackupDataView backup button while the websocket is in error state', () => {
    const actionArea = backupImageModalSource.slice(
      backupImageModalSource.indexOf('<div className="backup-image-actions">'),
      backupImageModalSource.indexOf('</div>', backupImageModalSource.indexOf('<div className="backup-image-actions">')),
    )

    expect(actionArea).toContain("status !== 'error' &&")
    expect(actionArea).toContain('<Button type="primary"')
    expect(actionArea).toContain('disabled={!canChange}')
    expect(actionArea).toContain('备份')
  })

  it('uses QML text-only backup action buttons without React-only icons', () => {
    expect(qmlSource).toContain('text: "重新连接"')
    expect(qmlSource).toContain('text: "打开文件夹"')
    expect(qmlSource).toContain('text: "备份"')

    expect(backupImageModalSource).not.toContain('@ant-design/icons')
    expect(backupImageModalSource).not.toContain('FolderOpenOutlined')
    expect(backupImageModalSource).not.toContain('ReloadOutlined')
    expect(backupImageModalSource).not.toContain('SaveOutlined')
    expect(backupImageModalSource).not.toContain('icon={<')
  })
})
