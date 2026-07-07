import { Button, Empty, Modal, Tag, Tooltip, message } from 'antd'
import { useMemo, useState } from 'react'
import {
  ApiOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  DesktopOutlined,
  PoweroffOutlined,
  ReloadOutlined,
  RedoOutlined,
  ToolOutlined,
  WifiOutlined,
} from '@ant-design/icons'
import { invoke } from '@tauri-apps/api/core'
import { useNavigate } from 'react-router-dom'

import {
  buildMaintenanceToolGroups,
  buildRemoteServiceRows,
  normalizeMaintenanceHost,
  type MaintenanceAction,
  type RemoteServiceRow,
} from '@/utils/maintenanceTools'
import { runDatabaseBackupFromNativeSaveDialog } from '@/utils/backup'
import { openQmlExternalUrl } from '@/utils/coilActions'
import { useUiSettingsStore } from '@/stores/uiSettingsStore'
import { hasTauriRuntime, tauriWindow } from '@/utils/tauriWindow'
import './MaintenanceMenuModal.css'

interface MaintenanceMenuModalProps {
  open: boolean
  onClose: () => void
}

function actionIcon(action: MaintenanceAction) {
  switch (action.id) {
    case 'remoteDesktop':
      return <DesktopOutlined />
    case 'pingServer':
    case 'networkSpeedtest':
      return <WifiOutlined />
    case 'restartAllServices':
    case 'restartServer':
      return <ReloadOutlined />
    case 'backupToFile':
    case 'restoreFromBackup':
      return <DatabaseOutlined />
    case 'exitSystem':
      return <PoweroffOutlined />
    case 'serviceManagement':
      return <CloudServerOutlined />
    default:
      return <ToolOutlined />
  }
}

function RemoteServiceRowView({ row }: { row: RemoteServiceRow }) {
  return (
    <div className="maintenance-service-row">
      <div>
        <strong>{row.title}</strong>
        <small>{row.message}</small>
      </div>
      <div className="maintenance-service-actions">
        <Tag color="processing">{row.port}</Tag>
        {row.actions.map((action) => (
          <Tooltip key={action.id} title={action.enabled ? action.label : `${action.label}（${action.status}）`}>
            <Button
              aria-label={`${row.title}${action.label}`}
              disabled={!action.enabled}
              icon={action.id === 'openApiDocs' ? <ApiOutlined /> : <RedoOutlined />}
              onClick={action.id === 'openApiDocs' ? () => void openQmlExternalUrl(action.href ?? '') : undefined}
              size="small"
            />
          </Tooltip>
        ))}
      </div>
    </div>
  )
}

export default function MaintenanceMenuModal({ open, onClose }: MaintenanceMenuModalProps) {
  const navigate = useNavigate()
  const [serviceManagementOpen, setServiceManagementOpen] = useState(false)
  const databasPort = useUiSettingsStore((state) => state.databasPort)
  const dataPort = useUiSettingsStore((state) => state.dataPort)
  const plcPort = useUiSettingsStore((state) => state.plcPort)
  const host = normalizeMaintenanceHost(window.location.hostname || '127.0.0.1') || '127.0.0.1'
  const groups = buildMaintenanceToolGroups(host)
  const serviceRows = useMemo(
    () => buildRemoteServiceRows({ databasPort, dataPort, plcPort, host }),
    [dataPort, databasPort, plcPort, host],
  )

  const runAction = async (action: MaintenanceAction) => {
    if (!action.enabled) return

    if (action.sideEffect === 'externalProcess') {
      if (!hasTauriRuntime()) {
        message.info(`Web 预览不启动本地命令：${action.commandPreview}`)
        return
      }
      try {
        const preview = await invoke<string>('launch_maintenance_tool', { action: action.id, host })
        message.success(`已启动：${preview}`)
      } catch (error) {
        message.error(`启动失败：${String(error)}`)
      }
      return
    }

    if (action.id === 'serviceManagement') {
      setServiceManagementOpen(true)
      onClose()
      return
    }
    if (action.id === 'backupToFile') {
      try {
        const result = await runDatabaseBackupFromNativeSaveDialog()
        if (result.status === 'saved') {
          message.success('数据库备份已完成')
          onClose()
        } else if (result.status === 'failed') {
          message.warning('数据库备份未成功，请检查路径或文件类型')
        } else if (result.status === 'unavailable') {
          navigate('/system')
          onClose()
          message.info('Web 预览请在系统诊断中使用数据库备份')
        }
      } catch (error) {
        message.error(`数据库备份请求失败：${String(error)}`)
      }
      return
    }
    if (action.id === 'networkSpeedtest') {
      navigate('/system#network-speedtest')
      onClose()
      message.info('已打开系统诊断，请在网络测速区执行测试')
      return
    }
    if (action.id === 'exitSystem') {
      if (hasTauriRuntime()) {
        await tauriWindow.close()
      } else {
        message.info('Web 预览不关闭浏览器窗口')
      }
    }
  }

  return (
    <>
    <Modal
      className="maintenance-menu-modal tools-menu-modal"
      title={null}
      width={360}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnHidden
    >
      <nav className="maintenance-menu" data-qml-tools-menu-view aria-label="工具菜单">
        <div className="maintenance-groups">
          {groups.map((group) => (
            <section className="maintenance-group" key={group.key}>
              <h3>
                <ToolOutlined />
                {group.title}
              </h3>
              <div className="maintenance-action-list">
                {group.actions.map((action) => (
                  <button
                    className="maintenance-action"
                    disabled={!action.enabled}
                    key={action.id}
                    type="button"
                    onClick={() => runAction(action)}
                  >
                    <span className="maintenance-action-icon">{actionIcon(action)}</span>
                    <span className="maintenance-action-main">
                      <strong>{action.label}</strong>
                      <small>
                        {action.parentLabel
                          ? action.commandPreview
                            ? `${action.parentLabel} · ${action.commandPreview}`
                            : action.parentLabel
                          : action.commandPreview || (action.enabled ? '打开对应功能' : '功能待接入')}
                      </small>
                    </span>
                    <Tag color={action.enabled ? 'blue' : 'default'}>{action.status}</Tag>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      </nav>
    </Modal>
    <Modal
      className="maintenance-menu-modal service-management-modal"
      title={null}
      width={600}
      open={serviceManagementOpen}
      onCancel={() => setServiceManagementOpen(false)}
      footer={null}
      destroyOnHidden
    >
      <section className="maintenance-service-panel service-management-panel" data-qml-server-mange-view>
        <h3 className="service-management-title" data-qml-server-mange-title>
          远程服务管理
        </h3>
        {serviceRows.length > 0 ? (
          <div className="maintenance-service-list">
            {serviceRows.map((row) => (
              <RemoteServiceRowView key={row.key} row={row} />
            ))}
          </div>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无服务项" />
        )}
      </section>
    </Modal>
    </>
  )
}
