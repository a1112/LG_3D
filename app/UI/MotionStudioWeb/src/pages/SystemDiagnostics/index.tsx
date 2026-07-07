import { useEffect, useMemo, useRef, useState } from 'react'

import { Button, Empty, Input, InputNumber, Progress, Segmented, Tag, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import {
  ApiOutlined,
  CameraOutlined,
  CloudServerOutlined,
  CloudSyncOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  DownloadOutlined,
  HddOutlined,
  LaptopOutlined,
  LineChartOutlined,
  SlidersOutlined,
  PartitionOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  SaveOutlined,
  ScissorOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'

import {
  area2dApi,
  buildReDetectionWsPath,
  buildServerStateWsPath,
  controlApi,
  diagnosticApi,
  joinBaseUrl,
  plcApi,
  runtimeApi,
  serviceBaseUrls,
  settingsApi,
  systemApi,
} from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import {
  buildAreaStatusView,
  buildDefaultAreaClipConfig,
  normalizeAreaSurfaceKey,
  type AreaSurfaceKey,
} from '@/utils/area2d'
import { buildDatabaseBackupFileName, buildDatabaseBackupPath, type DatabaseBackupExtension } from '@/utils/backup'
import { buildCameraAdjustmentRows, formatCameraFrameAge } from '@/utils/cameraAdjustment'
import { buildControlConfigRows } from '@/utils/controlConfig'
import { formatSpeedtestUploadResult } from '@/utils/speedtest'
import { getRuntimeTestMode, getTestModeLabel } from '@/utils/testMode'
import {
  buildCoilListReDetectionRange,
  buildReDetectionWebSocketStartMessage,
  buildReDetectionStatusView,
  normalizeReDetectionRange,
  parseReDetectionWebSocketMessage,
  resolveReDetectionWsUrl,
  type ReDetectionRange,
} from '@/utils/reDetection'
import {
  buildServerStateRows,
  buildServerStateSummary,
  parseServerStateWebSocketMessage,
  resolveServerStateWsUrl,
} from '@/utils/serverState'
import {
  buildDeviceCurveChart,
  buildDeviceCurveViewModel,
  formatDeviceCurveValue,
  type DeviceCurveChart,
} from '@/utils/plcCurve'
import { getSurfaceSaveFolder } from '@/utils/coilActions'
import { openQmlExternalUrl } from '@/utils/coilActions'
import { openNativePath, selectNativeSavePath } from '@/utils/nativeDialogs'
import './SystemDiagnostics.css'

const DEFAULT_DATABASE_BACKUP_FOLDER = 'D:\\Backup\\LG3D'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readText(record: Record<string, unknown>, keys: string[], fallback = '--') {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  }
  return fallback
}

function countObjectEntries(value: unknown) {
  const record = asRecord(value)
  return Object.keys(record).length
}

function pathCount(openApi: unknown) {
  return countObjectEntries(asRecord(openApi).paths)
}

function cameraCount(captureStatus: unknown): number {
  const record = asRecord(captureStatus)
  return Object.values(record).reduce<number>((total, value) => {
    if (Array.isArray(value)) return total + value.length
    if (value && typeof value === 'object') return total + Object.keys(value as Record<string, unknown>).length
    return total
  }, 0)
}

function healthState(health: unknown) {
  const record = asRecord(health)
  return readText(record, ['status', 'state'], 'unknown')
}

function backupExtensionFromPath(path: string): DatabaseBackupExtension {
  return path.trim().toLowerCase().endsWith('.sql') ? 'sql' : 'db'
}

function StatTile({
  icon,
  label,
  value,
  tone = 'normal',
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  tone?: 'normal' | 'ok' | 'warn'
}) {
  return (
    <div className={`system-stat-tile ${tone}`}>
      <span className="system-stat-icon">{icon}</span>
      <span className="system-stat-label">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function JsonPreview({ value }: { value: unknown }) {
  if (value == null) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
  return <pre className="system-json-preview">{JSON.stringify(value, null, 2)}</pre>
}

function DeviceCurveChartView({ chart }: { chart: DeviceCurveChart }) {
  const width = 760
  const height = 220
  const padding = { left: 44, right: 18, top: 16, bottom: 32 }
  const plotWidth = width - padding.left - padding.right
  const plotHeight = height - padding.top - padding.bottom
  const xSpan = chart.axis.maxX - chart.axis.minX || 1
  const ySpan = chart.axis.maxY - chart.axis.minY || 1
  const project = (point: { x: number; y: number }) => ({
    x: padding.left + ((point.x - chart.axis.minX) / xSpan) * plotWidth,
    y: padding.top + plotHeight - ((point.y - chart.axis.minY) / ySpan) * plotHeight,
  })

  return (
    <div className="device-curve-chart" role="img" aria-label="设备曲线折线图">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={padding.top + plotHeight} />
        <line x1={padding.left} y1={padding.top + plotHeight} x2={padding.left + plotWidth} y2={padding.top + plotHeight} />
        <text x={padding.left} y={height - 8}>{formatDeviceCurveValue(chart.axis.minX)}</text>
        <text x={padding.left + plotWidth - 60} y={height - 8}>{formatDeviceCurveValue(chart.axis.maxX)}</text>
        <text x={4} y={padding.top + 8}>{formatDeviceCurveValue(chart.axis.maxY)}</text>
        <text x={4} y={padding.top + plotHeight}>{formatDeviceCurveValue(chart.axis.minY)}</text>
        {chart.series.map((series) => {
          const path = series.points
            .map((point, index) => {
              const projected = project(point)
              return `${index === 0 ? 'M' : 'L'} ${projected.x.toFixed(2)} ${projected.y.toFixed(2)}`
            })
            .join(' ')
          return path ? <path key={series.key} d={path} stroke={series.color} /> : null
        })}
      </svg>
      <div className="device-curve-legend">
        {chart.series.map((series) => (
          <span key={series.key}>
            <i style={{ background: series.color }} />
            {series.label}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function SystemDiagnosticsPage() {
  const location = useLocation()
  const queryClient = useQueryClient()
  const coilList = useCoilStore((state) => state.coilList)
  const [backupPath, setBackupPath] = useState(() => buildDatabaseBackupPath(DEFAULT_DATABASE_BACKUP_FOLDER, 'db'))
  const [areaSurface, setAreaSurface] = useState<AreaSurfaceKey>('S')
  const [areaCoilId, setAreaCoilId] = useState(193113)
  const [areaOffset, setAreaOffset] = useState(40)
  const [curveStartId, setCurveStartId] = useState(0)
  const [curveEndId, setCurveEndId] = useState(0)
  const [curveLimit, setCurveLimit] = useState(200)
  const [areaActionResult, setAreaActionResult] = useState<unknown>(null)
  const [speedtestUploadResult, setSpeedtestUploadResult] = useState<unknown>(null)

  useEffect(() => {
    if (location.hash !== '#network-speedtest') return
    document.getElementById('network-speedtest')?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  }, [location.hash])
  const [controlKey, setControlKey] = useState('')
  const [controlValue, setControlValue] = useState('')
  const [cameraDrafts, setCameraDrafts] = useState<Record<string, { exposureTime?: number; gain?: number }>>({})
  const [reDetectionRange, setReDetectionRange] = useState<ReDetectionRange>({ fromId: 0, toId: 0 })
  const [reDetectionWsReady, setReDetectionWsReady] = useState(false)
  const [reDetectionWsStatus, setReDetectionWsStatus] = useState<unknown>(null)
  const [reDetectionReconnectSerial, setReDetectionReconnectSerial] = useState(0)
  const reDetectionSocketRef = useRef<WebSocket | null>(null)
  const [serverStateWsReady, setServerStateWsReady] = useState(false)
  const [serverStateWsData, setServerStateWsData] = useState<unknown>(null)
  const healthQuery = useQuery({ queryKey: ['system', 'health'], queryFn: systemApi.getHealth, retry: 1 })
  const runtimeQuery = useQuery({ queryKey: ['system', 'runtime'], queryFn: systemApi.getRuntimeInfo, retry: 1 })
  const openApiQuery = useQuery({ queryKey: ['system', 'openapi'], queryFn: systemApi.getOpenApi, retry: 1 })
  const hardwareQuery = useQuery({ queryKey: ['system', 'hardware'], queryFn: systemApi.getHardware, retry: 1 })
  const captureQuery = useQuery({ queryKey: ['system', 'capture'], queryFn: systemApi.getCaptureStatus, retry: 1 })
  const cameraQuery = useQuery({ queryKey: ['system', 'cameraAdjust'], queryFn: systemApi.getCameraAdjust, retry: 1 })
  const plcInfoQuery = useQuery({ queryKey: ['system', 'plcInfo'], queryFn: plcApi.getInfo, retry: 1 })
  const infoQuery = useQuery({
    queryKey: ['system', 'info'],
    queryFn: systemApi.getInfo,
    staleTime: 60_000,
    retry: 1,
  })
  const reDetectionFolder = useMemo(() => {
    const saveFolderS = getSurfaceSaveFolder(infoQuery.data, 'S')
    const saveFolderL = getSurfaceSaveFolder(infoQuery.data, 'L')
    return saveFolderS || saveFolderL
  }, [infoQuery.data])
  const controlConfigQuery = useQuery({ queryKey: ['control', 'config'], queryFn: controlApi.getConfig, retry: 1 })
  const areaStatusQuery = useQuery({ queryKey: ['area2d', 'status'], queryFn: area2dApi.getStatus, retry: 1 })
  const reDetectionStatusQuery = useQuery({
    queryKey: ['runtime', 'reDetectionStatus', 'system'],
    queryFn: runtimeApi.getReDetectionStatus,
    enabled: !reDetectionWsReady,
    retry: 1,
    refetchInterval: reDetectionWsReady ? false : 1000,
  })
  const serverStateQuery = useQuery({
    queryKey: ['runtime', 'serverState', 'system'],
    queryFn: runtimeApi.getServerState,
    enabled: !serverStateWsReady,
    retry: 1,
    refetchInterval: serverStateWsReady ? false : 1000,
  })
  const testModeQuery = useQuery({
    queryKey: ['settings', 'testModeStatus'],
    queryFn: settingsApi.getTestModeStatus,
    retry: 1,
    staleTime: 30_000,
  })

  useEffect(() => {
    let closed = false
    const socket = new WebSocket(resolveServerStateWsUrl(serviceBaseUrls.apiWsBaseUrl, buildServerStateWsPath()))
    setServerStateWsReady(false)

    socket.onopen = () => {
      if (!closed) setServerStateWsReady(true)
    }
    socket.onmessage = (event) => {
      if (!closed) setServerStateWsData(parseServerStateWebSocketMessage(String(event.data)))
    }
    socket.onerror = () => {
      if (!closed) setServerStateWsReady(false)
    }
    socket.onclose = () => {
      if (!closed) setServerStateWsReady(false)
    }

    return () => {
      closed = true
      setServerStateWsReady(false)
      socket.close()
    }
  }, [])

  useEffect(() => {
    let closed = false
    const socket = new WebSocket(resolveReDetectionWsUrl(serviceBaseUrls.apiWsBaseUrl, buildReDetectionWsPath()))
    reDetectionSocketRef.current = socket
    setReDetectionWsReady(false)
    setReDetectionWsStatus(null)

    socket.onopen = () => {
      if (!closed) {
        setReDetectionWsReady(true)
        setReDetectionWsStatus({})
      }
    }
    socket.onmessage = (event) => {
      if (!closed) setReDetectionWsStatus(parseReDetectionWebSocketMessage(String(event.data)))
    }
    socket.onerror = () => {
      if (!closed) {
        setReDetectionWsReady(false)
        setReDetectionWsStatus({ error: '连接断开!' })
      }
    }
    socket.onclose = () => {
      if (!closed) {
        setReDetectionWsReady(false)
        setReDetectionWsStatus({ error: '连接断开!' })
      }
      if (reDetectionSocketRef.current === socket) {
        reDetectionSocketRef.current = null
      }
    }

    return () => {
      closed = true
      setReDetectionWsReady(false)
      if (reDetectionSocketRef.current === socket) {
        reDetectionSocketRef.current = null
      }
      socket.close()
    }
  }, [reDetectionReconnectSerial])

  const syncMutation = useMutation({
    mutationFn: (limit: number) => systemApi.syncSummaries(limit),
    onSuccess: (result) => {
      const record = asRecord(result)
      message.success(readText(record, ['message'], '摘要同步请求已完成'))
    },
    onError: () => message.error('摘要同步请求失败'),
  })

  const backupMutation = useMutation({
    mutationFn: (path: string) => runtimeApi.saveToSql(path),
    onSuccess: (result, path) => {
      const state = Boolean(asRecord(result).state)
      if (state) {
        message.success('数据库备份已完成')
        void openNativePath(path).catch(() => undefined)
      } else {
        message.warning('数据库备份未成功，请检查路径或文件类型')
      }
    },
    onError: () => message.error('数据库备份请求失败'),
  })

  const controlPropertyMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) => controlApi.setProperty(key, value),
    onSuccess: () => {
      message.success('控制参数已发送')
      queryClient.invalidateQueries({ queryKey: ['control', 'config'] })
    },
    onError: () => message.error('控制参数发送失败'),
  })

  const speedtestUploadMutation = useMutation({
    mutationFn: (formData: FormData) => diagnosticApi.uploadSpeedtest(formData),
    onSuccess: (result) => {
      setSpeedtestUploadResult(result)
      const summary = formatSpeedtestUploadResult(result)
      message.success(summary ? `上传测速完成：${summary.speed}` : '上传测速已完成')
    },
    onError: () => message.error('上传测速失败'),
  })

  const refreshAreaStatus = () => {
    queryClient.invalidateQueries({ queryKey: ['area2d', 'status'] })
  }

  const clipConfigMutation = useMutation({
    mutationFn: ({ surfaceKey, offset }: { surfaceKey: AreaSurfaceKey; offset: number }) =>
      area2dApi.setClipConfig(surfaceKey, buildDefaultAreaClipConfig(surfaceKey, { offset })),
    onSuccess: (result) => {
      setAreaActionResult(result)
      message.success('2D 裁剪参数已发送')
      refreshAreaStatus()
    },
    onError: () => message.error('2D 裁剪参数发送失败'),
  })

  const areaRejoinMutation = useMutation({
    mutationFn: ({ coilId, surfaceKey }: { coilId: number; surfaceKey: AreaSurfaceKey }) =>
      area2dApi.rejoin(coilId, surfaceKey),
    onSuccess: (result) => {
      setAreaActionResult(result)
      message.success('2D 重拼任务已入队')
      refreshAreaStatus()
    },
    onError: () => message.error('2D 重拼请求失败'),
  })

  const areaScanMutation = useMutation({
    mutationFn: area2dApi.scan,
    onSuccess: (result) => {
      setAreaActionResult(result)
      message.success('2D 区域扫描已执行')
      refreshAreaStatus()
    },
    onError: () => message.error('2D 区域扫描失败'),
  })

  const plcCurveMutation = useMutation({
    mutationFn: () => plcApi.getCurveAll(curveStartId, curveEndId, curveLimit),
    onError: () => message.error('设备曲线加载失败'),
  })

  const cameraAdjustMutation = useMutation({
    mutationFn: ({ cameraKey, exposureTime, gain }: { cameraKey: string; exposureTime: number; gain: number }) =>
      systemApi.setCameraAdjustment(cameraKey, exposureTime, gain, true),
    onSuccess: (_result, variables) => {
      message.success(`${variables.cameraKey} 参数已发送`)
      queryClient.invalidateQueries({ queryKey: ['system', 'cameraAdjust'] })
      queryClient.invalidateQueries({ queryKey: ['system', 'capture'] })
    },
    onError: () => message.error('相机参数发送失败'),
  })

  const cameraReconnectMutation = useMutation({
    mutationFn: systemApi.reconnectCameraAdjustment,
    onSuccess: (_result, cameraKey) => {
      message.success(`${cameraKey} 重连请求已发送`)
      queryClient.invalidateQueries({ queryKey: ['system', 'cameraAdjust'] })
      queryClient.invalidateQueries({ queryKey: ['system', 'capture'] })
    },
    onError: () => message.error('相机重连请求失败'),
  })

  const reDetectionStartMutation = useMutation({
    mutationFn: async (range: ReDetectionRange) => {
      const socket = reDetectionSocketRef.current
      setReDetectionWsStatus({ running: true, progress: 0, total: 0, pending: 0 })
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(buildReDetectionWebSocketStartMessage(range, reDetectionFolder))
        return { started: true, transport: 'websocket', ...range }
      }

      return runtimeApi.startReDetection(range.fromId, range.toId)
    },
    onSuccess: () => {
      message.success('已启动重新识别')
      queryClient.invalidateQueries({ queryKey: ['runtime', 'reDetectionStatus', 'system'] })
    },
    onError: () => {
      setReDetectionWsStatus({ error: '重新识别启动失败' })
      message.error('重新识别启动失败')
    },
  })

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['system'] })
    queryClient.invalidateQueries({ queryKey: ['runtime', 'reDetectionStatus', 'system'] })
    queryClient.invalidateQueries({ queryKey: ['runtime', 'serverState', 'system'] })
    refreshAreaStatus()
    queryClient.invalidateQueries({ queryKey: ['settings', 'testModeStatus'] })
  }
  const openApiDocs = () => {
    void openQmlExternalUrl(joinBaseUrl(serviceBaseUrls.apiBaseUrl, '/docs'))
  }
  const openSpeedtestDownload = () => {
    void openQmlExternalUrl(diagnosticApi.getSpeedtestDownloadUrl(1))
  }

  const openApiInfo = asRecord(asRecord(openApiQuery.data).info)
  const runtimeInfo = asRecord(runtimeQuery.data)
  const hardware = asRecord(hardwareQuery.data)
  const areaStatusView = buildAreaStatusView(areaStatusQuery.data, areaSurface)
  const areaClipConfig = areaStatusView.clipConfig
  const testMode = asRecord(testModeQuery.data)
  const cameraAdjust = asRecord(cameraQuery.data)
  const plcInfo = asRecord(plcInfoQuery.data)
  const plcTypeList = Array.isArray(plcInfo.typeList) ? plcInfo.typeList.map(String) : []
  const cameraRows = buildCameraAdjustmentRows(cameraQuery.data)
  const controlRows = buildControlConfigRows(controlConfigQuery.data)
  const reDetectionStatusSource = reDetectionWsStatus ?? reDetectionStatusQuery.data
  const reDetectionStatus = buildReDetectionStatusView(reDetectionStatusSource)
  const serverStateData = serverStateWsData ?? serverStateQuery.data
  const serverStateRows = buildServerStateRows(serverStateData)
  const serverStateSummary = buildServerStateSummary(serverStateData)
  const gpuModels = Array.isArray(runtimeInfo.gpus) ? runtimeInfo.gpus.join('\n') : ''
  const areaQueueDepth = areaStatusView.surfaceQueueDepth
  const areaJoinQueueDepth = areaStatusView.joinQueueDepth
  const refreshBackupPath = (extension: DatabaseBackupExtension) => {
    setBackupPath(buildDatabaseBackupPath(DEFAULT_DATABASE_BACKUP_FOLDER, extension))
  }
  const chooseDatabaseBackupPath = async () => {
    try {
      const selected = await selectNativeSavePath(buildDatabaseBackupFileName(backupExtensionFromPath(backupPath)))
      if (selected.status === 'selected') {
        setBackupPath(selected.path)
      } else if (selected.status === 'unavailable') {
        message.info('当前环境不可用，可手动输入备份路径')
      }
    } catch {
      message.error('保存路径选择失败')
    }
  }
  const speedtestUploadSummary = formatSpeedtestUploadResult(speedtestUploadResult)
  const plcCurveItems = Array.isArray(asRecord(plcCurveMutation.data).items)
    ? (asRecord(plcCurveMutation.data).items as unknown[])
    : []
  const plcCurveModel = buildDeviceCurveViewModel(plcCurveItems)
  const plcCurveChart = buildDeviceCurveChart(plcCurveModel.rows)
  const applyCurrentCoilListRange = () => {
    const ids = coilList.map((coil) => coil.id).filter((id) => Number.isFinite(id) && id > 0)
    if (ids.length === 0) {
      message.info('当前列表暂无可用流水号')
      return
    }
    setCurveStartId(Math.min(...ids))
    setCurveEndId(Math.max(...ids))
  }
  const applyCurrentListReDetectionRange = () => {
    const range = buildCoilListReDetectionRange(coilList)
    if (range.fromId === 0 || range.toId === 0) {
      message.info('当前列表暂无可用流水号')
      return
    }
    setReDetectionRange(range)
  }
  const startReDetection = () => {
    const range = normalizeReDetectionRange(reDetectionRange)
    setReDetectionRange(range)
    reDetectionStartMutation.mutate(range)
  }
  const reconnectReDetectionSocket = () => {
    reDetectionSocketRef.current?.close()
    setReDetectionWsReady(false)
    setReDetectionWsStatus(null)
    setReDetectionReconnectSerial((serial) => serial + 1)
    queryClient.invalidateQueries({ queryKey: ['runtime', 'reDetectionStatus', 'system'] })
  }
  const handleSpeedtestUpload: UploadProps['beforeUpload'] = (file) => {
    const formData = new FormData()
    formData.append('file', file)
    speedtestUploadMutation.mutate(formData)
    return false
  }
  const setCameraDraftValue = (cameraKey: string, field: 'exposureTime' | 'gain', value: number | null) => {
    setCameraDrafts((drafts) => ({
      ...drafts,
      [cameraKey]: {
        ...drafts[cameraKey],
        [field]: typeof value === 'number' ? value : 0,
      },
    }))
  }
  const readCameraDraftValue = (cameraKey: string, field: 'exposureTime' | 'gain', fallback: number) =>
    cameraDrafts[cameraKey]?.[field] ?? fallback

  return (
    <div className="system-page">
      <div className="system-toolbar">
        <div className="system-title">
          <DashboardOutlined />
          <span>系统诊断</span>
          <Tag color={healthState(healthQuery.data) === 'ok' ? 'green' : 'gold'}>{healthState(healthQuery.data)}</Tag>
        </div>
        <div className="system-actions">
          <Button size="small" icon={<ReloadOutlined />} onClick={refreshAll}>
            刷新
          </Button>
          <Button size="small" icon={<ApiOutlined />} onClick={openApiDocs}>
            API 文档
          </Button>
          <Button size="small" icon={<DownloadOutlined />} onClick={openSpeedtestDownload}>
            1MB 测速
          </Button>
        </div>
      </div>

      <div className="system-stat-grid">
        <StatTile icon={<ApiOutlined />} label="OpenAPI 路径" value={pathCount(openApiQuery.data)} tone="ok" />
        <StatTile icon={<LaptopOutlined />} label="缓存模式" value={readText(runtimeInfo, ['cache_mode'])} />
        <StatTile icon={<HddOutlined />} label="硬件项" value={Object.keys(hardware).length} />
        <StatTile icon={<CameraOutlined />} label="相机状态项" value={cameraCount(captureQuery.data)} />
        <StatTile
          icon={<DatabaseOutlined />}
          label="测试模式"
          value={getTestModeLabel(testMode)}
          tone={getRuntimeTestMode(testMode) ? 'warn' : 'ok'}
        />
      </div>

      <div className="system-content-grid">
        <section className="system-panel">
          <div className="system-panel-title">
            <ApiOutlined />
            API Schema
          </div>
          <dl className="system-kv">
            <dt>Title</dt>
            <dd>{readText(openApiInfo, ['title'])}</dd>
            <dt>Version</dt>
            <dd>{readText(openApiInfo, ['version'])}</dd>
            <dt>Paths</dt>
            <dd>{pathCount(openApiQuery.data)}</dd>
          </dl>
        </section>

        <section className="system-panel">
          <div className="system-panel-title">
            <LaptopOutlined />
            运行环境
          </div>
          <dl className="system-kv runtime-kv">
            <dt>Python</dt>
            <dd>{readText(runtimeInfo, ['python_version'])}</dd>
            <dt>缓存</dt>
            <dd>{readText(runtimeInfo, ['cache_mode'])}</dd>
            <dt>CPU</dt>
            <dd>{readText(runtimeInfo, ['cpu_model'])}</dd>
            <dt>GPU</dt>
            <dd>{gpuModels || '--'}</dd>
            <dt>本地模式</dt>
            <dd>{readText(runtimeInfo, ['is_local'])}</dd>
            <dt>开发者模式</dt>
            <dd>{readText(runtimeInfo, ['developer_mode'])}</dd>
            <dt>离线模式</dt>
            <dd>{readText(runtimeInfo, ['offline_mode'])}</dd>
          </dl>
        </section>

        <section className="system-panel plc-info-panel">
          <div className="system-panel-title">
            <CloudServerOutlined />
            PLC连接信息
          </div>
          <dl className="system-kv">
            <dt>PLC IP</dt>
            <dd>{readText(plcInfo, ['plc_ip'])}</dd>
            <dt>Rack</dt>
            <dd>{readText(plcInfo, ['rack'])}</dd>
            <dt>Slot</dt>
            <dd>{readText(plcInfo, ['slot'])}</dd>
            <dt>类型</dt>
            <dd>{plcTypeList.join(' / ') || '--'}</dd>
          </dl>
        </section>

        <section className="system-panel" id="network-speedtest">
          <div className="system-panel-title">
            <UploadOutlined />
            上传测速
          </div>
          <div className="speedtest-upload-stack">
            <Upload beforeUpload={handleSpeedtestUpload} showUploadList={false} maxCount={1}>
              <Button
                size="small"
                type="primary"
                icon={<UploadOutlined />}
                loading={speedtestUploadMutation.isPending}
              >
                选择文件并上传
              </Button>
            </Upload>
            {speedtestUploadSummary ? (
              <dl className="system-kv speedtest-result-kv">
                <dt>文件</dt>
                <dd>{speedtestUploadSummary.filename}</dd>
                <dt>大小</dt>
                <dd>{speedtestUploadSummary.fileSize}</dd>
                <dt>耗时</dt>
                <dd>{speedtestUploadSummary.elapsed}</dd>
                <dt>速度</dt>
                <dd>{speedtestUploadSummary.speed}</dd>
              </dl>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无上传结果" />
            )}
          </div>
        </section>

        <section className="system-panel">
          <div className="system-panel-title">
            <DatabaseOutlined />
            数据库备份
          </div>
          <div className="backup-control-stack">
            <Input
              size="small"
              value={backupPath}
              onChange={(event) => setBackupPath(event.target.value)}
              placeholder="D:\Backup\LG3D\lg3d_backup_YYYYMMDD_HHMMSS.db"
            />
            <div className="backup-action-row">
              <Button size="small" onClick={() => refreshBackupPath('sql')}>
                生成 SQL 路径
              </Button>
              <Button size="small" onClick={() => refreshBackupPath('db')}>
                生成 SQLite 路径
              </Button>
              <Button size="small" icon={<SaveOutlined />} onClick={chooseDatabaseBackupPath}>
                选择保存路径
              </Button>
              <Button
                size="small"
                type="primary"
                icon={<SaveOutlined />}
                loading={backupMutation.isPending}
                onClick={() => backupMutation.mutate(backupPath)}
              >
                开始备份
              </Button>
            </div>
          </div>
          <JsonPreview value={backupMutation.data ?? null} />
        </section>

        <section className="system-panel">
          <div className="system-panel-title">
            <CloudSyncOutlined />
            摘要同步
          </div>
          <div className="sync-control-row">
            <InputNumber size="small" min={1} max={10000} defaultValue={100} id="summary-sync-limit" />
            <Button
              size="small"
              type="primary"
              icon={<CloudSyncOutlined />}
              loading={syncMutation.isPending}
              onClick={() => {
                const input = document.getElementById('summary-sync-limit') as HTMLInputElement | null
                syncMutation.mutate(Number(input?.value || 100))
              }}
            >
              同步摘要
            </Button>
          </div>
          <JsonPreview value={syncMutation.data ?? null} />
        </section>

        <section className="system-panel control-config-panel">
          <div className="system-panel-title">
            <SlidersOutlined />
            参数控制
          </div>
          <div className="control-config-stack">
            {controlRows.length > 0 ? (
              <div className="control-config-list">
                {controlRows.slice(0, 8).map((row) => (
                  <button
                    className="control-config-row"
                    key={row.key}
                    type="button"
                    onClick={() => {
                      setControlKey(row.key)
                      setControlValue(row.value)
                    }}
                  >
                    <span>{row.key}</span>
                    <strong>{row.value || '--'}</strong>
                  </button>
                ))}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Control.json 暂无可显示参数" />
            )}
            <div className="control-config-form">
              <Input
                size="small"
                value={controlKey}
                onChange={(event) => setControlKey(event.target.value)}
                placeholder="参数 key，例如 lower_limit"
              />
              <Input
                size="small"
                value={controlValue}
                onChange={(event) => setControlValue(event.target.value)}
                placeholder="参数 value"
              />
              <Button
                size="small"
                type="primary"
                icon={<SlidersOutlined />}
                disabled={!controlKey.trim()}
                loading={controlPropertyMutation.isPending}
                onClick={() => controlPropertyMutation.mutate({ key: controlKey.trim(), value: controlValue })}
              >
                发送参数
              </Button>
            </div>
          </div>
          <JsonPreview value={controlPropertyMutation.data ?? controlConfigQuery.data ?? null} />
        </section>

        <section className="system-panel re-detection-panel">
          <div className="system-panel-title">
            <PlayCircleOutlined />
            重新识别
          </div>
          <div className="re-detection-stack">
            <div className="re-detection-status-row">
              {reDetectionStatus.error ? (
                <>
                  <span className="re-detection-error">{reDetectionStatus.error}</span>
                  <Button size="small" onClick={reconnectReDetectionSocket}>
                    重新连接
                  </Button>
                </>
              ) : reDetectionStatus.showProgress ? (
                <>
                  <Tag color={reDetectionStatus.color}>{reDetectionStatus.label}</Tag>
                  <span>总数 {reDetectionStatus.total}</span>
                  <span>待处理 {reDetectionStatus.pending}</span>
                </>
              ) : null}
            </div>
            {reDetectionStatus.showProgress ? (
              <Progress percent={reDetectionStatus.percent} status={reDetectionStatus.running ? 'active' : 'normal'} />
            ) : null}
            <div className="re-detection-controls">
              <InputNumber
                size="small"
                min={0}
                disabled={!reDetectionStatus.canChange}
                value={reDetectionRange.fromId}
                onChange={(value) =>
                  setReDetectionRange((range) => ({
                    ...range,
                    fromId: typeof value === 'number' ? value : 0,
                  }))
                }
                aria-label="重新识别起始流水号"
              />
              <InputNumber
                size="small"
                min={0}
                disabled={!reDetectionStatus.canChange}
                value={reDetectionRange.toId}
                onChange={(value) =>
                  setReDetectionRange((range) => ({
                    ...range,
                    toId: typeof value === 'number' ? value : 0,
                  }))
                }
                aria-label="重新识别结束流水号"
              />
              <Button size="small" disabled={!reDetectionStatus.canChange} onClick={applyCurrentListReDetectionRange}>
                当前列表范围
              </Button>
              {!reDetectionStatus.error ? (
                <Button
                  size="small"
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  disabled={reDetectionRange.fromId <= 0 || reDetectionRange.toId <= 0}
                  loading={reDetectionStartMutation.isPending}
                  onClick={startReDetection}
                >
                  识别
                </Button>
              ) : null}
            </div>
          </div>
          <JsonPreview value={reDetectionStartMutation.data ?? reDetectionStatusSource ?? null} />
        </section>

        <section className="system-panel server-state-panel">
          <div className="system-panel-title">
            <CloudServerOutlined />
            检测状态
          </div>
          <div className="server-state-stack">
            <div className="server-state-summary-row">
              <Tag color={serverStateSummary.color}>{serverStateSummary.label}</Tag>
              <span>总数 {serverStateSummary.total}</span>
              <span>异常 {serverStateSummary.abnormal}</span>
            </div>
            {serverStateRows.length > 0 ? (
              <div className="server-state-list">
                {serverStateRows.map((row) => (
                  <div className="server-state-row" key={row.key}>
                    <div className="server-state-meta">
                      <strong>{row.title}</strong>
                      <small>{row.message || '--'}</small>
                    </div>
                    <Tag color={row.color}>{row.value || '--'}</Tag>
                  </div>
                ))}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无检测状态" />
            )}
          </div>
          <JsonPreview value={serverStateData ?? null} />
        </section>

        <section className="system-panel area2d-panel">
          <div className="system-panel-title">
            <PartitionOutlined />
            2D 区域拼接
          </div>
          <div className="area2d-control-stack">
            <div className="area2d-status-row">
              <Tag color={areaStatusView.status === 'ok' ? 'green' : 'gold'}>
                {areaStatusView.status}
              </Tag>
              <span>表面队列 {areaQueueDepth}</span>
              <span>总队列 {areaJoinQueueDepth}</span>
              <span>扫描中 {String(areaStatusView.scanRunning)}</span>
            </div>
            <div className="area2d-clip-config-row">
              <strong>当前裁剪</strong>
              {areaClipConfig ? (
                <>
                  <span>模式 {areaClipConfig.mode}</span>
                  <span>fixed {areaClipConfig.fixed}</span>
                  <span>c {areaClipConfig.c}</span>
                  <span>a {areaClipConfig.a}</span>
                  <span>b {areaClipConfig.b}</span>
                  <span>offset {areaClipConfig.offset ?? '--'}</span>
                </>
              ) : (
                <span>--</span>
              )}
            </div>
            <div className="area2d-control-row">
              <Segmented
                size="small"
                value={areaSurface}
                options={[
                  { label: 'S 面', value: 'S' },
                  { label: 'L 面', value: 'L' },
                ]}
                onChange={(value) => setAreaSurface(normalizeAreaSurfaceKey(value))}
              />
              <InputNumber
                size="small"
                min={0}
                value={areaCoilId}
                onChange={(value) => setAreaCoilId(typeof value === 'number' ? value : 0)}
                aria-label="2D 重拼 Coil ID"
              />
              <InputNumber
                size="small"
                min={0}
                max={500}
                value={areaOffset}
                onChange={(value) => setAreaOffset(typeof value === 'number' ? value : 40)}
                aria-label="2D 动态裁剪偏移"
              />
            </div>
            <div className="area2d-action-row">
              <Button
                size="small"
                icon={<ScissorOutlined />}
                loading={clipConfigMutation.isPending}
                onClick={() => clipConfigMutation.mutate({ surfaceKey: areaSurface, offset: areaOffset })}
              >
                发送裁剪
              </Button>
              <Button
                size="small"
                type="primary"
                icon={<PartitionOutlined />}
                loading={areaRejoinMutation.isPending}
                onClick={() => areaRejoinMutation.mutate({ coilId: areaCoilId, surfaceKey: areaSurface })}
              >
                重拼入队
              </Button>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={areaScanMutation.isPending || areaStatusQuery.isFetching}
                onClick={() => areaScanMutation.mutate()}
              >
                扫描任务
              </Button>
            </div>
          </div>
          <JsonPreview value={areaActionResult ?? areaStatusQuery.data} />
        </section>

        <section className="system-panel device-curve-panel">
          <div className="system-panel-title">
            <LineChartOutlined />
            设备曲线
          </div>
          <div className="device-curve-stack">
            <div className="device-curve-controls">
              <InputNumber
                size="small"
                min={0}
                value={curveStartId}
                onChange={(value) => setCurveStartId(typeof value === 'number' ? value : 0)}
                aria-label="设备曲线起始ID"
              />
              <InputNumber
                size="small"
                min={0}
                value={curveEndId}
                onChange={(value) => setCurveEndId(typeof value === 'number' ? value : 0)}
                aria-label="设备曲线结束ID"
              />
              <InputNumber
                size="small"
                min={1}
                max={10000}
                value={curveLimit}
                onChange={(value) => setCurveLimit(typeof value === 'number' ? value : 200)}
                aria-label="设备曲线数量"
              />
              <Button size="small" onClick={applyCurrentCoilListRange}>
                当前列表范围
              </Button>
              <Button
                size="small"
                type="primary"
                icon={<LineChartOutlined />}
                loading={plcCurveMutation.isPending}
                onClick={() => plcCurveMutation.mutate()}
              >
                刷新曲线
              </Button>
            </div>
            <div className="device-curve-summary">
              <Tag color="blue">总长均值 {formatDeviceCurveValue(plcCurveModel.totalLengthAvg)}</Tag>
              <Tag color="green">S端距离均值 {formatDeviceCurveValue(plcCurveModel.distanceSAvg)}</Tag>
              <Tag color="purple">L端距离均值 {formatDeviceCurveValue(plcCurveModel.distanceLAvg)}</Tag>
            </div>
            <DeviceCurveChartView chart={plcCurveChart} />
            {plcCurveModel.rows.length > 0 ? (
              <div className="device-curve-table">
                <div className="device-curve-row header">
                  <span>Coil ID</span>
                  <span>宽度</span>
                  <span>S位置</span>
                  <span>L位置</span>
                  <span>激光</span>
                  <span>S距离</span>
                  <span>L距离</span>
                  <span>总长</span>
                  <span>平均误差</span>
                </div>
                {plcCurveModel.rows.slice(0, 12).map((row, index) => (
                  <div className="device-curve-row" key={`${row.coil_id}-${index}`}>
                    <span>{row.coil_id}</span>
                    <span>{formatDeviceCurveValue(row.width_)}</span>
                    <span>{formatDeviceCurveValue(row.location_S)}</span>
                    <span>{formatDeviceCurveValue(row.location_L)}</span>
                    <span>{formatDeviceCurveValue(row.location_laser)}</span>
                    <span>{formatDeviceCurveValue(row.median_3d_mm_S)}</span>
                    <span>{formatDeviceCurveValue(row.median_3d_mm_L)}</span>
                    <span>{formatDeviceCurveValue(row.total_length)}</span>
                    <span>{formatDeviceCurveValue(row.total_error)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无设备曲线数据" />
            )}
          </div>
        </section>

        <section className="system-panel">
          <div className="system-panel-title">
            <HddOutlined />
            硬件状态
          </div>
          <JsonPreview value={hardwareQuery.data} />
        </section>

        <section className="system-panel">
          <div className="system-panel-title">
            <CameraOutlined />
            相机与采集
          </div>
          <dl className="system-kv">
            <dt>配置文件</dt>
            <dd>{readText(cameraAdjust, ['configFile'])}</dd>
            <dt>采集服务</dt>
            <dd>{readText(cameraAdjust, ['captureServiceUrl'])}</dd>
          </dl>
          <div className="camera-adjust-list">
            {cameraRows.length > 0 ? (
              cameraRows.map((camera) => {
                const exposureTime = readCameraDraftValue(camera.key, 'exposureTime', camera.exposureTime)
                const gain = readCameraDraftValue(camera.key, 'gain', camera.gain)
                const busy =
                  (cameraAdjustMutation.isPending &&
                    cameraAdjustMutation.variables?.cameraKey === camera.key) ||
                  (cameraReconnectMutation.isPending && cameraReconnectMutation.variables === camera.key)

                return (
                  <div className="camera-adjust-row" key={camera.key}>
                    <span className={`camera-status-mark ${camera.connected && camera.ok ? 'ok' : camera.connected ? 'warn' : 'error'}`} />
                    <div className="camera-adjust-meta">
                      <strong>{camera.key || '--'}</strong>
                      <span>{camera.name || '--'} SN: {camera.sn || '--'}</span>
                      <small>
                        最近帧 {formatCameraFrameAge(camera.lastFrameAge)} / 3D {formatCameraFrameAge(camera.lastFrameAge3D)}
                        {' · '}
                        参数源 {camera.source || '--'}
                      </small>
                      <small>{camera.message || camera.lastError3D || camera.serviceUrl || camera.paramFile || '--'}</small>
                    </div>
                    <div className="camera-adjust-controls">
                      <InputNumber
                        size="small"
                        min={1}
                        max={1_000_000}
                        value={exposureTime}
                        disabled={!camera.writable || busy}
                        aria-label={`${camera.key} 曝光时间`}
                        onChange={(value) => setCameraDraftValue(camera.key, 'exposureTime', value)}
                      />
                      <InputNumber
                        size="small"
                        min={0}
                        max={1000}
                        value={gain}
                        disabled={!camera.writable || busy}
                        aria-label={`${camera.key} 增益`}
                        onChange={(value) => setCameraDraftValue(camera.key, 'gain', value)}
                      />
                      <Button
                        size="small"
                        type="primary"
                        disabled={!camera.key || !camera.writable}
                        loading={cameraAdjustMutation.isPending && cameraAdjustMutation.variables?.cameraKey === camera.key}
                        onClick={() =>
                          cameraAdjustMutation.mutate({
                            cameraKey: camera.key,
                            exposureTime,
                            gain,
                          })
                        }
                      >
                        保存
                      </Button>
                      <Button
                        size="small"
                        icon={<ReloadOutlined />}
                        disabled={!camera.key}
                        loading={cameraReconnectMutation.isPending && cameraReconnectMutation.variables === camera.key}
                        onClick={() => cameraReconnectMutation.mutate(camera.key)}
                      >
                        重连
                      </Button>
                    </div>
                  </div>
                )
              })
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无相机调整项" />
            )}
          </div>
          <JsonPreview value={captureQuery.data} />
        </section>
      </div>
    </div>
  )
}
