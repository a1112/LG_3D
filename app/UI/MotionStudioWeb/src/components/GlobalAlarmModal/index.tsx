import { Button, Modal, Spin, Tag, Tooltip, message } from 'antd'
import {
  ApiOutlined,
  CameraOutlined,
  CloudServerOutlined,
  DesktopOutlined,
  FolderOpenOutlined,
  HddOutlined,
  RedoOutlined,
} from '@ant-design/icons'
import { invoke } from '@tauri-apps/api/core'
import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { serviceBaseUrls, systemApi } from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import { useUiSettingsStore } from '@/stores/uiSettingsStore'
import { openQmlExternalUrl } from '@/utils/coilActions'
import { normalizeMaintenanceHost } from '@/utils/maintenanceTools'
import { openNativePath } from '@/utils/nativeDialogs'
import { hasTauriRuntime } from '@/utils/tauriWindow'
import {
  buildGlobalAlarmNetworkProbeTargets,
  buildGlobalAlarmViewModel,
  measureGlobalAlarmNetworkDelays,
  type AlarmSummaryItem,
  type CameraAlarmItem,
  type GlobalAlarmNetworkHeaderAction,
  type NetworkAlarmItem,
} from '@/utils/globalAlarm'
import './GlobalAlarmModal.css'

interface GlobalAlarmModalProps {
  open: boolean
  onClose: () => void
}

function levelColor(level: number): string {
  if (level >= 3) return 'error'
  if (level >= 2) return 'warning'
  return 'success'
}

function AlarmCard({ item }: { item: AlarmSummaryItem }) {
  return (
    <Tooltip title={item.message || item.title}>
      <div className={`global-alarm-card global-alarm-hardware-card level-${Math.min(Math.max(item.level, 1), 3)}`}>
        <span>{item.title}</span>
        <span className="global-alarm-separator">:</span>
        <Tag color={levelColor(item.level)}>{item.value}</Tag>
      </div>
    </Tooltip>
  )
}

function readCameraDataFolder(data: unknown): string {
  if (!data || typeof data !== 'object' || Array.isArray(data)) return ''
  const record = data as Record<string, unknown>
  const folder = record.folder ?? record.path ?? record.savePath ?? record.save_path
  return typeof folder === 'string' ? folder.trim() : ''
}

function buildFolderFallbackUrl(folder: string): string {
  const trimmed = folder.trim()
  if (/^[a-z][a-z0-9+.-]*:/i.test(trimmed)) return trimmed
  const normalized = trimmed.replace(/\\/g, '/')
  if (normalized.startsWith('//')) return `file:${normalized}`
  if (/^[a-z]:\//i.test(normalized)) return `file:///${normalized}`
  return normalized
}

function CameraCard({
  item,
  coilId,
  restartingCameraKey,
  openingRawCameraKey,
  onRestartCamera,
  onOpenRawDataPath,
}: {
  item: CameraAlarmItem
  coilId: number | null
  restartingCameraKey: string | null
  openingRawCameraKey: string | null
  onRestartCamera: (cameraKey: string) => void
  onOpenRawDataPath: (cameraKey: string) => void
}) {
  const cameraDataUrl = coilId ? systemApi.getCameraDataUrl(coilId, item.key) : undefined
  const cameraActionDisabled = (actionId: string, enabled: boolean) => {
    if (actionId === 'openCurrentCoilCameraData') return !cameraDataUrl
    if (actionId === 'openRawDataSavePath') return !enabled || !coilId || openingRawCameraKey === item.key
    if (actionId === 'restartCamera') return !enabled || restartingCameraKey === item.key
    return !enabled
  }
  const runCameraAction = (actionId: string) => {
    if (actionId === 'openCurrentCoilCameraData') {
      void openQmlExternalUrl(cameraDataUrl ?? '')
      return
    }
    if (actionId === 'restartCamera') {
      onRestartCamera(item.key)
      return
    }
    if (actionId === 'openRawDataSavePath') {
      onOpenRawDataPath(item.key)
    }
  }

  return (
    <Tooltip title={item.message || item.title}>
      <div className={`global-alarm-card global-alarm-camera-card level-${Math.min(Math.max(item.level, 1), 3)}`}>
        <span>{item.title}</span>
        <Tag color={levelColor(item.level)}>{item.value}</Tag>
        <div className="global-alarm-camera-actions">
          {item.actions.map((action) => (
            <Tooltip key={action.id} title={action.enabled ? action.label : `${action.label}（${action.status}）`}>
              <Button
                aria-label={action.id === 'openCurrentCoilCameraData' ? `打开${item.title}当前卷相机数据` : `${item.title}${action.label}`}
                size="small"
                icon={action.id === 'restartCamera' ? <RedoOutlined /> : action.id === 'openRawDataSavePath' ? <FolderOpenOutlined /> : <FolderOpenOutlined />}
                disabled={cameraActionDisabled(action.id, action.enabled)}
                loading={
                  (action.id === 'restartCamera' && restartingCameraKey === item.key)
                  || (action.id === 'openRawDataSavePath' && openingRawCameraKey === item.key)
                }
                onClick={() => runCameraAction(action.id)}
              />
            </Tooltip>
          ))}
        </div>
      </div>
    </Tooltip>
  )
}

function NetworkCard({ item }: { item: NetworkAlarmItem }) {
  return (
    <Tooltip title={`${item.message} · 端口 ${item.port}`}>
      <div
        className={`global-alarm-card global-alarm-network-card level-${Math.min(Math.max(item.level, 1), 3)}`}
      >
        <span>{item.title}</span>
        <span className="global-alarm-separator">:</span>
        <Tag color={levelColor(item.level)}>{item.value}</Tag>
        <div className="global-alarm-network-actions">
          {item.actions.map((action) => (
            <Tooltip key={action.id} title={action.enabled ? action.label : `${action.label}（${action.status}）`}>
              <Button
                aria-label={action.id === 'openApiDocs' ? `打开${item.title}接口文档` : `${item.title}${action.label}`}
                size="small"
                icon={action.id === 'openApiDocs' ? <ApiOutlined /> : action.id === 'restartService' ? <RedoOutlined /> : null}
                disabled={!action.enabled}
                onClick={action.id === 'openApiDocs' ? () => void openQmlExternalUrl(action.href ?? '') : undefined}
              />
            </Tooltip>
          ))}
        </div>
      </div>
    </Tooltip>
  )
}

export default function GlobalAlarmModal({ open, onClose }: GlobalAlarmModalProps) {
  const currentCoil = useCoilStore((state) => state.currentCoil)
  const [restartingCameraKey, setRestartingCameraKey] = useState<string | null>(null)
  const [openingRawCameraKey, setOpeningRawCameraKey] = useState<string | null>(null)
  const databasPort = useUiSettingsStore((state) => state.databasPort)
  const dataPort = useUiSettingsStore((state) => state.dataPort)
  const plcPort = useUiSettingsStore((state) => state.plcPort)
  const remoteHost = normalizeMaintenanceHost(serviceBaseUrls.apiBaseUrl)
    || normalizeMaintenanceHost(window.location.hostname || '127.0.0.1')
    || '127.0.0.1'
  const networkPorts = useMemo(
    () => ({
      capture: databasPort,
      data: databasPort,
      threeD: dataPort,
      plc: plcPort,
    }),
    [dataPort, databasPort, plcPort],
  )
  const cameraQuery = useQuery({
    queryKey: ['globalAlarm', 'cameraAlarm'],
    queryFn: systemApi.getCameraAlarm,
    enabled: open,
    refetchInterval: open ? 10_000 : false,
    retry: 1,
  })
  const hardwareQuery = useQuery({
    queryKey: ['globalAlarm', 'hardware'],
    queryFn: systemApi.getHardware,
    enabled: open,
    refetchInterval: open ? 2_000 : false,
    retry: 1,
  })
  const networkDelayQuery = useQuery({
    queryKey: ['globalAlarm', 'networkDelay', networkPorts.capture, networkPorts.data, networkPorts.threeD, networkPorts.plc],
    queryFn: () =>
      measureGlobalAlarmNetworkDelays(
        buildGlobalAlarmNetworkProbeTargets({
          apiBaseUrl: serviceBaseUrls.apiBaseUrl,
          networkPorts,
        }),
      ),
    enabled: open,
    refetchInterval: open ? 10_000 : false,
    retry: false,
  })

  const viewModel = buildGlobalAlarmViewModel({
    cameraAlarm: cameraQuery.data,
    hardware: hardwareQuery.data,
    networkPorts,
    networkDelay: networkDelayQuery.data,
    networkRemoteHost: remoteHost,
  })
  const loading = cameraQuery.isFetching || hardwareQuery.isFetching || networkDelayQuery.isFetching

  const runNetworkHeaderAction = async (action: GlobalAlarmNetworkHeaderAction) => {
    if (!action.enabled) return

    if (!hasTauriRuntime()) {
      message.info(`Web 预览不启动本地命令：${action.commandPreview}`)
      return
    }

    try {
      const preview = await invoke<string>('launch_maintenance_tool', { action: action.id, host: remoteHost })
      message.success(`已启动：${preview}`)
    } catch (error) {
      message.error(`启动失败：${String(error)}`)
    }
  }

  const restartCamera = async (cameraKey: string) => {
    setRestartingCameraKey(cameraKey)
    try {
      await systemApi.reconnectCameraAdjustment(cameraKey)
      message.success(`已发送相机重连：${cameraKey}`)
      cameraQuery.refetch()
    } catch (error) {
      message.error(`相机重连失败：${String(error)}`)
    } finally {
      setRestartingCameraKey(null)
    }
  }

  const openCameraRawDataPath = async (cameraKey: string) => {
    const coilId = currentCoil?.id
    if (!coilId) {
      message.warning('请先选择当前卷材')
      return
    }

    setOpeningRawCameraKey(cameraKey)
    try {
      const data = await systemApi.getCameraData(coilId, cameraKey)
      const folder = readCameraDataFolder(data)
      if (!folder) {
        message.warning(`未找到相机原始数据路径：${cameraKey}`)
        return
      }

      const nativeResult = await openNativePath(folder).catch(() => ({ status: 'unavailable' as const }))
      if (nativeResult.status === 'opened') {
        message.success(`已打开：${nativeResult.path}`)
        return
      }

      const result = await openQmlExternalUrl(buildFolderFallbackUrl(folder))
      if (result === 'skipped') {
        message.warning(`无法打开相机原始数据路径：${folder}`)
        return
      }
      message.success(`已打开：${folder}`)
    } catch (error) {
      message.error(`打开相机原始数据路径失败：${String(error)}`)
    } finally {
      setOpeningRawCameraKey(null)
    }
  }

  return (
    <Modal
      className="global-alarm-window"
      title={null}
      open={open}
      width={600}
      footer={null}
      onCancel={onClose}
      destroyOnHidden
    >
      <div className="global-alarm-modal" data-qml-global-alarm-view>
        <section className="global-alarm-section">
          <h3>
            <CameraOutlined />
            相机状态
          </h3>
          <div className="global-alarm-grid columns-3">
            {viewModel.cameras.length > 0 ? (
              viewModel.cameras.map((item) => (
                <CameraCard
                  key={item.key}
                  item={item}
                  coilId={currentCoil?.id ?? null}
                  restartingCameraKey={restartingCameraKey}
                  openingRawCameraKey={openingRawCameraKey}
                  onRestartCamera={restartCamera}
                  onOpenRawDataPath={openCameraRawDataPath}
                />
              ))
            ) : (
              <div className="global-alarm-empty">暂无相机状态</div>
            )}
          </div>
        </section>

        <section className="global-alarm-section">
          <div className="global-alarm-section-header">
            <h3>
              <CloudServerOutlined />
              网络状态
            </h3>
            <div className="global-alarm-section-actions">
              {viewModel.networkHeaderActions.map((action) => (
                <Tooltip
                  key={action.id}
                  title={action.enabled ? `${action.label} · ${action.commandPreview}` : `${action.label}（${action.status}）`}
                >
                  <Button
                    aria-label={action.label}
                    disabled={!action.enabled}
                    icon={<DesktopOutlined />}
                    size="small"
                    onClick={() => runNetworkHeaderAction(action)}
                  />
                </Tooltip>
              ))}
            </div>
          </div>
          <div className="global-alarm-grid columns-2">
            {viewModel.networks.map((item) => (
              <NetworkCard key={item.key} item={item} />
            ))}
          </div>
        </section>

        <section className="global-alarm-section">
          <h3>
            <HddOutlined />
            服务器状态
          </h3>
          <div className="global-alarm-grid columns-2">
            {viewModel.hardware.length > 0 ? (
              viewModel.hardware.map((item) => <AlarmCard key={item.key} item={item} />)
            ) : (
              <div className="global-alarm-empty">暂无服务器状态</div>
            )}
          </div>
        </section>

        {loading && (
          <div className="global-alarm-loading">
            <Spin size="small" />
          </div>
        )}
      </div>
    </Modal>
  )
}
