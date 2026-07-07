import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Button, Input, InputNumber, Modal, message } from 'antd'

import { applyRuntimeConnectionSettings, applyApiBaseUrlOverride } from '@/services/api'
import {
  normalizeApiServerIp,
  normalizeApiServerPort,
  useUiSettingsStore,
} from '@/stores/uiSettingsStore'
import { persistCurrentConnectionSettingsToNative } from '@/utils/nativeSettings'
import './ConnectSettingsModal.css'

interface ConnectSettingsModalProps {
  open: boolean
  onClose: () => void
}

const CONNECT_HOST_SHORTCUTS = ['127.0.0.1', '192.168.99.100']

export default function ConnectSettingsModal({ open, onClose }: ConnectSettingsModalProps) {
  const queryClient = useQueryClient()
  const apiServerIp = useUiSettingsStore((state) => state.apiServerIp)
  const apiServerPort = useUiSettingsStore((state) => state.apiServerPort)
  const databasPort = useUiSettingsStore((state) => state.databasPort)
  const dataPort = useUiSettingsStore((state) => state.dataPort)
  const plcPort = useUiSettingsStore((state) => state.plcPort)
  const alg2dPort = useUiSettingsStore((state) => state.alg2dPort)
  const useRustImageServer = useUiSettingsStore((state) => state.useRustImageServer)
  const rustImageServerPort = useUiSettingsStore((state) => state.rustImageServerPort)
  const setApiServerIp = useUiSettingsStore((state) => state.setApiServerIp)
  const setApiServerPort = useUiSettingsStore((state) => state.setApiServerPort)
  const [ipDraft, setIpDraft] = useState(apiServerIp)
  const [portDraft, setPortDraft] = useState(apiServerPort)

  useEffect(() => {
    if (!open) return
    setIpDraft(apiServerIp)
    setPortDraft(apiServerPort)
  }, [apiServerIp, apiServerPort, open])

  const applyConnection = (closeAfterApply: boolean) => {
    const nextIp = normalizeApiServerIp(ipDraft)
    const nextPort = normalizeApiServerPort(portDraft)
    const nextBaseUrls = applyRuntimeConnectionSettings({
      serverIp: nextIp,
      serverPort: nextPort,
      databasPort,
      dataPort,
      plcPort,
      alg2dPort,
      useRustImageServer,
      rustImageServerPort,
    })

    setApiServerIp(nextIp)
    setApiServerPort(nextPort)
    setIpDraft(nextIp)
    setPortDraft(nextPort)
    applyApiBaseUrlOverride(nextBaseUrls.apiBaseUrl)
    queryClient.invalidateQueries()
    void persistCurrentConnectionSettingsToNative().catch(() => {
      message.warning('保存连接设置到本地配置失败')
    })
    message.success(`API连接已切换到 ${nextBaseUrls.apiBaseUrl}`)

    if (closeAfterApply) {
      onClose()
    }
  }

  return (
    <Modal
      className="connect-settings-modal"
      title={null}
      width={500}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnHidden={false}
    >
      <section className="connect-settings-dialog" data-qml-connect-dialog>
        <h3 data-qml-connect-title>连接设置</h3>
        <div className="connect-settings-fields">
          <label className="connect-settings-field">
            <span>Ip 地址 : </span>
            <Input
              data-qml-connect-ip-input
              value={ipDraft}
              onChange={(event) => setIpDraft(event.target.value)}
            />
          </label>
          <label className="connect-settings-field connect-settings-port-field">
            <span>端口号 : </span>
            <InputNumber
              data-qml-connect-port-input
              min={1}
              max={65535}
              value={portDraft}
              onChange={(value) => setPortDraft(value ?? 5011)}
            />
          </label>
        </div>
        <div className="connect-settings-shortcuts">
          {CONNECT_HOST_SHORTCUTS.map((host) => (
            <button key={host} type="button" onClick={() => setIpDraft(host)}>
              {host}
            </button>
          ))}
        </div>
        <div className="connect-settings-actions">
          <Button data-qml-connect-apply onClick={() => applyConnection(false)}>
            Apply
          </Button>
          <Button data-qml-connect-ok type="primary" onClick={() => applyConnection(true)}>
            OK
          </Button>
        </div>
      </section>
    </Modal>
  )
}
