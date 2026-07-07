import { useEffect, useRef, useState } from 'react'
import { Button, Input, InputNumber, Modal, Progress, Tag, message } from 'antd'

import { buildBackupImageTaskWsPath, serviceBaseUrls } from '@/services/api'
import type { CoilData } from '@/types'
import {
  buildBackupImageDefaultPath,
  buildBackupImageInitialRange,
  isBackupImageFinishedMessage,
  openBackupImageFolder,
  resolveBackupImageWsUrl,
} from '@/utils/backupImage'
import { getNativeDefaultDesktopDirectory, selectNativeDirectory } from '@/utils/nativeDialogs'
import './BackupImageModal.css'

interface BackupImageModalProps {
  open: boolean
  coilList: CoilData[]
  onClose: () => void
}

type BackupStatus = 'idle' | 'running' | 'finished' | 'error'

const QML_BACKUP_FALLBACK_DESKTOP = '桌面'

export default function BackupImageModal({ open, coilList, onClose }: BackupImageModalProps) {
  const [fromId, setFromId] = useState(0)
  const [toId, setToId] = useState(0)
  const [outputPath, setOutputPath] = useState(() => buildBackupImageDefaultPath(QML_BACKUP_FALLBACK_DESKTOP))
  const [status, setStatus] = useState<BackupStatus>('idle')
  const [progress, setProgress] = useState(0)
  const [errorText, setErrorText] = useState('')
  const [connectionAttempt, setConnectionAttempt] = useState(0)
  const socketRef = useRef<WebSocket | null>(null)
  const backupStartedRef = useRef(false)
  const backupFinishedRef = useRef(false)
  const outputPathRef = useRef(outputPath)

  useEffect(() => {
    outputPathRef.current = outputPath
  }, [outputPath])

  useEffect(() => {
    if (!open) {
      socketRef.current?.close()
      socketRef.current = null
      backupStartedRef.current = false
      backupFinishedRef.current = false
      return
    }

    let closed = false
    const range = buildBackupImageInitialRange(coilList)
    const openedAt = new Date()
    setFromId(range.fromId)
    setToId(range.toId)
    setOutputPath(buildBackupImageDefaultPath(QML_BACKUP_FALLBACK_DESKTOP, openedAt))
    setStatus('idle')
    setProgress(0)
    setErrorText('')

    getNativeDefaultDesktopDirectory().then((desktopFolder) => {
      if (closed || !desktopFolder) return
      setOutputPath(buildBackupImageDefaultPath(desktopFolder, openedAt))
    })

    return () => {
      closed = true
    }
  }, [coilList, open])

  useEffect(() => {
    if (!open) {
      return
    }

    let closed = false
    const socket = new WebSocket(resolveBackupImageWsUrl(serviceBaseUrls.apiWsBaseUrl, buildBackupImageTaskWsPath()))
    socketRef.current = socket
    backupStartedRef.current = false
    backupFinishedRef.current = false

    socket.onopen = () => {
      if (!closed) {
        setStatus('idle')
        setErrorText('')
      }
    }
    socket.onmessage = (event) => {
      if (closed) return
      if (backupStartedRef.current) setStatus('running')
      const text = String(event.data)
      const value = Number.parseInt(text, 10)
      if (Number.isFinite(value)) {
        setProgress(Math.max(0, Math.min(1, value / 100)))
      }
      if (isBackupImageFinishedMessage(text)) {
        backupFinishedRef.current = true
        backupStartedRef.current = false
        setStatus('finished')
        setProgress(1)
        socket.close()
        void openBackupImageFolder(outputPathRef.current)
      }
    }
    socket.onerror = () => {
      if (closed || backupFinishedRef.current) return
      setStatus('error')
      setErrorText('备份连接错误')
    }
    socket.onclose = () => {
      if (!closed && !backupFinishedRef.current && socketRef.current === socket) {
        setStatus('error')
        setErrorText('连接断开!')
      }
      if (socketRef.current === socket) {
        socketRef.current = null
      }
    }

    return () => {
      closed = true
      if (socketRef.current === socket) {
        socketRef.current = null
      }
      socket.close()
    }
  }, [connectionAttempt, open])

  const chooseFolder = async () => {
    try {
      const selected = await selectNativeDirectory()
      if (!selected) {
        message.info('可手动输入保存位置')
        return
      }
      setOutputPath(buildBackupImageDefaultPath(selected))
    } catch {
      message.error('目录选择失败')
    }
  }

  const reconnect = () => {
    backupStartedRef.current = false
    backupFinishedRef.current = false
    socketRef.current?.close()
    socketRef.current = null
    setStatus('idle')
    setProgress(0)
    setErrorText('')
    setConnectionAttempt((attempt) => attempt + 1)
  }

  const startBackup = () => {
    if (!outputPath.trim()) {
      message.warning('请输入保存位置')
      return
    }

    const socket = socketRef.current
    if (socket?.readyState !== WebSocket.OPEN) {
      setStatus('error')
      setErrorText('连接断开!')
      return
    }

    backupStartedRef.current = true
    backupFinishedRef.current = false
    setStatus('running')
    setProgress(0)
    setErrorText('')
    socket.send(JSON.stringify({ from_id: fromId, to_id: toId, folder: outputPath.trim() }))
  }

  const canChange = status === 'idle'
  const percent = Math.round(progress * 100)

  return (
    <Modal title={null} open={open} width={590} footer={null} onCancel={onClose} destroyOnHidden>
      <div className="backup-image-modal" data-qml-backup-data-view>
        <div className="backup-image-head">
          <strong className="backup-image-title" data-qml-backup-data-title>
            数据备份
          </strong>
          {status === 'error' && (
            <Button size="small" onClick={reconnect}>
              重新连接
            </Button>
          )}
        </div>

        <div className="backup-image-grid">
          <label>
            <span>起始流水号</span>
            <InputNumber disabled={!canChange} min={0} value={fromId} onChange={(value) => setFromId(Number(value ?? 0))} />
          </label>
          <label>
            <span>结束流水号</span>
            <InputNumber disabled={!canChange} min={0} value={toId} onChange={(value) => setToId(Number(value ?? 0))} />
          </label>
        </div>

        <label className="backup-image-path">
          <span>保存位置</span>
          <div>
            <Input disabled={!canChange} value={outputPath} onChange={(event) => setOutputPath(event.target.value)} />
            <Button disabled={!canChange} onClick={chooseFolder}>
              选择
            </Button>
          </div>
        </label>

        <div className="backup-image-status">
          {(status === 'running' || status === 'finished') && (
            <>
              <Progress percent={percent} status={status === 'running' ? 'active' : 'success'} />
              <Tag color={status === 'running' ? 'processing' : 'success'}>
                {status === 'running' ? '备份中...' : '备份完成'}
              </Tag>
            </>
          )}
          {status === 'error' && <span className="backup-image-error">{errorText || '备份失败'}</span>}
        </div>

        <div className="backup-image-actions">
          {(status === 'running' || status === 'finished') && (
            <Button onClick={() => void openBackupImageFolder(outputPath)}>
              打开文件夹
            </Button>
          )}
          {status !== 'error' && (
            <Button type="primary" disabled={!canChange} onClick={startBackup}>
              备份
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}
