import { type ReactNode, useEffect, useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Descriptions,
  Drawer,
  Empty,
  Input,
  InputNumber,
  Progress,
  Select,
  Slider,
  Switch,
  Tabs,
  message,
} from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { applyApiBaseUrlOverride, applyRuntimeConnectionSettings, buildRuntimeApiBaseUrl, plcApi, serviceBaseUrls, settingsApi, systemApi } from '@/services/api'
import {
  QML_PLACEHOLDER_SETTINGS_TAB_KEYS,
  QML_SETTINGS_TAB_OPTIONS,
  QML_DISPLAY_STYLE_OPTIONS,
  QML_THEME_OPTIONS,
  normalizeApiServerIp,
  normalizeApiServerPort,
  useUiSettingsStore,
} from '@/stores/uiSettingsStore'
import {
  buildDefaultSoftwareManifestUrl,
  compareSoftwareVersions,
  downloadSoftwareUpdatePackage,
  normalizeSoftwareUpdateManifest,
  openDownloadedSoftwareUpdate,
  openSoftwareUpdateInstallTarget,
  resolveSoftwareUpdateFolderPath,
  resolveSoftwareUpdateUrl,
  type SoftwareUpdateManifest,
} from '@/utils/softwareUpdate'
import { persistCurrentConnectionSettingsToNative } from '@/utils/nativeSettings'
import { tauriWindow } from '@/utils/tauriWindow'
import { getNativeDefaultDownloadDirectory } from '@/utils/nativeDialogs'
import { buildCameraAdjustmentRows, formatCameraFrameAge } from '@/utils/cameraAdjustment'
import { globalImageCache } from '@/utils/imageCache'
import { buildQmlInfoSettingRows, getConfiguredTestMode, getRuntimeTestMode, getTestModeLabel } from '@/utils/testMode'
import './SettingsPanel.css'

interface SettingsPanelProps {
  open: boolean
  onClose: () => void
}

function readStatusField(data: unknown, keys: string[]) {
  if (!data || typeof data !== 'object') return '--'
  const record = data as Record<string, unknown>
  for (const key of keys) {
    const value = record[key]
    if (value !== undefined && value !== null) {
      return String(value)
    }
  }
  return '--'
}

const settingsTabLabels = Object.fromEntries(
  QML_SETTINGS_TAB_OPTIONS.map((item) => [item.key, item.label])
) as Record<(typeof QML_SETTINGS_TAB_OPTIONS)[number]['key'], string>

function QmlBaseSettingPlaceholder() {
  return (
    <div className="settings-qml-placeholder">
      <span>index:0</span>
    </div>
  )
}

function renderQmlInfoSettingValue(row: { label: string; value: string }) {
  if (row.label === '运行模式：') {
    return (
      <span className={`settings-mode-badge ${row.value === '测试模式' ? 'test' : 'prod'}`}>
        {row.value}
      </span>
    )
  }

  return row.value
}

const settingsPanelTitle = (
  <div className="settings-panel-title">
    <span>设置</span>
    <small>系统参数与显示配置</small>
  </div>
)

function renderSettingsPanelCloseButton(onClose: () => void) {
  return (
    <button
      aria-label="关闭"
      className="settings-panel-close"
      title="关闭"
      type="button"
      onClick={onClose}
    >
      x
    </button>
  )
}

function QmlGeneralSettingSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="settings-qml-section">
      <div className="settings-qml-section-title">{title}</div>
      <div className="settings-qml-section-divider" />
      <div className="settings-qml-section-body">{children}</div>
    </section>
  )
}

function QmlSettingGroupBox({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section aria-label={title} className="settings-qml-groupbox">
      <div className="settings-qml-groupbox-title">{title}</div>
      <div className="settings-qml-groupbox-body">{children}</div>
    </section>
  )
}

export default function SettingsPanel({ open, onClose }: SettingsPanelProps) {
  const queryClient = useQueryClient()
  const apiServerIp = useUiSettingsStore((state) => state.apiServerIp)
  const apiServerPort = useUiSettingsStore((state) => state.apiServerPort)
  const qmlThemeName = useUiSettingsStore((state) => state.qmlThemeName)
  const qmlDisplayStyleName = useUiSettingsStore((state) => state.qmlDisplayStyleName)
  const softwareUpdateManifestUrl = useUiSettingsStore((state) => state.softwareUpdateManifestUrl)
  const softwareUpdatePackageUrl = useUiSettingsStore((state) => state.softwareUpdatePackageUrl)
  const softwareUpdateAutoOpen = useUiSettingsStore((state) => state.softwareUpdateAutoOpen)
  const useSharedFolder = useUiSettingsStore((state) => state.useSharedFolder)
  const sharedFolderBaseName = useUiSettingsStore((state) => state.sharedFolderBaseName)
  const showTileDebugBorders = useUiSettingsStore((state) => state.showTileDebugBorders)
  const defaultAreaTileCount = useUiSettingsStore((state) => state.defaultAreaTileCount)
  const autoKeepTimeMax = useUiSettingsStore((state) => state.autoKeepTimeMax)
  const dataHeaderHeight = useUiSettingsStore((state) => state.dataHeaderHeight)
  const useImageCache = useUiSettingsStore((state) => state.useImageCache)
  const maxImageCache = useUiSettingsStore((state) => state.maxImageCache)
  const enable1024CacheMode = useUiSettingsStore((state) => state.enable1024CacheMode)
  const showErrorOverlay = useUiSettingsStore((state) => state.showErrorOverlay)
  const useRustImageServer = useUiSettingsStore((state) => state.useRustImageServer)
  const rustImageServerPort = useUiSettingsStore((state) => state.rustImageServerPort)
  const databasPort = useUiSettingsStore((state) => state.databasPort)
  const dataPort = useUiSettingsStore((state) => state.dataPort)
  const plcPort = useUiSettingsStore((state) => state.plcPort)
  const alg2dPort = useUiSettingsStore((state) => state.alg2dPort)
  const towerWarningThresholdUp = useUiSettingsStore((state) => state.towerWarningThresholdUp)
  const towerWarningThresholdDown = useUiSettingsStore((state) => state.towerWarningThresholdDown)
  const towerWarningOpacity = useUiSettingsStore((state) => state.towerWarningOpacity)
  const setApiServerIp = useUiSettingsStore((state) => state.setApiServerIp)
  const setApiServerPort = useUiSettingsStore((state) => state.setApiServerPort)
  const setQmlThemeName = useUiSettingsStore((state) => state.setQmlThemeName)
  const setQmlDisplayStyleName = useUiSettingsStore((state) => state.setQmlDisplayStyleName)
  const setSoftwareUpdateManifestUrl = useUiSettingsStore((state) => state.setSoftwareUpdateManifestUrl)
  const setSoftwareUpdatePackageUrl = useUiSettingsStore((state) => state.setSoftwareUpdatePackageUrl)
  const setSoftwareUpdateAutoOpen = useUiSettingsStore((state) => state.setSoftwareUpdateAutoOpen)
  const setUseSharedFolder = useUiSettingsStore((state) => state.setUseSharedFolder)
  const setSharedFolderBaseName = useUiSettingsStore((state) => state.setSharedFolderBaseName)
  const setShowTileDebugBorders = useUiSettingsStore((state) => state.setShowTileDebugBorders)
  const setDefaultAreaTileCount = useUiSettingsStore((state) => state.setDefaultAreaTileCount)
  const setAutoKeepTimeMax = useUiSettingsStore((state) => state.setAutoKeepTimeMax)
  const setDataHeaderHeight = useUiSettingsStore((state) => state.setDataHeaderHeight)
  const setUseImageCache = useUiSettingsStore((state) => state.setUseImageCache)
  const setMaxImageCache = useUiSettingsStore((state) => state.setMaxImageCache)
  const setEnable1024CacheMode = useUiSettingsStore((state) => state.setEnable1024CacheMode)
  const setShowErrorOverlay = useUiSettingsStore((state) => state.setShowErrorOverlay)
  const setUseRustImageServer = useUiSettingsStore((state) => state.setUseRustImageServer)
  const setRustImageServerPort = useUiSettingsStore((state) => state.setRustImageServerPort)
  const setDatabasPort = useUiSettingsStore((state) => state.setDatabasPort)
  const setDataPort = useUiSettingsStore((state) => state.setDataPort)
  const setPlcPort = useUiSettingsStore((state) => state.setPlcPort)
  const setAlg2dPort = useUiSettingsStore((state) => state.setAlg2dPort)
  const setTowerWarningThresholdUp = useUiSettingsStore((state) => state.setTowerWarningThresholdUp)
  const setTowerWarningThresholdDown = useUiSettingsStore((state) => state.setTowerWarningThresholdDown)
  const setTowerWarningOpacity = useUiSettingsStore((state) => state.setTowerWarningOpacity)
  const [apiServerIpDraft, setApiServerIpDraft] = useState(apiServerIp)
  const [apiServerPortDraft, setApiServerPortDraft] = useState(apiServerPort)
  const [currentApiBaseUrl, setCurrentApiBaseUrl] = useState(serviceBaseUrls.apiBaseUrl)
  const [softwareManifestDraft, setSoftwareManifestDraft] = useState(softwareUpdateManifestUrl)
  const [softwarePackageDraft, setSoftwarePackageDraft] = useState(softwareUpdatePackageUrl)
  const [softwareStatus, setSoftwareStatus] = useState('未检查')
  const [softwareManifest, setSoftwareManifest] = useState<SoftwareUpdateManifest | null>(null)
  const [softwareBusy, setSoftwareBusy] = useState(false)
  const [softwareDownloadBusy, setSoftwareDownloadBusy] = useState(false)
  const [softwareActionBusy, setSoftwareActionBusy] = useState(false)
  const [softwareSavedPath, setSoftwareSavedPath] = useState('')
  const [softwareDownloadFolder, setSoftwareDownloadFolder] = useState('')
  const [softwareProgress, setSoftwareProgress] = useState(0)
  const [cameraDrafts, setCameraDrafts] = useState<Record<string, { exposureTime?: number; gain?: number }>>({})

  useEffect(() => {
    if (!open) return
    setApiServerIpDraft(apiServerIp)
    setApiServerPortDraft(apiServerPort)
    setCurrentApiBaseUrl(serviceBaseUrls.apiBaseUrl)
    setSoftwareManifestDraft(softwareUpdateManifestUrl)
    setSoftwarePackageDraft(softwareUpdatePackageUrl)
  }, [apiServerIp, apiServerPort, open, softwareUpdateManifestUrl, softwareUpdatePackageUrl])

  useEffect(() => {
    globalImageCache.configure({ enabled: useImageCache, maxItems: maxImageCache })
  }, [maxImageCache, useImageCache])

  useEffect(() => {
    if (!open) return
    let active = true
    void getNativeDefaultDownloadDirectory().then((directory) => {
      if (active && directory) {
        setSoftwareDownloadFolder(directory)
      }
    })
    return () => {
      active = false
    }
  }, [open])

  const { data: currentVersion } = useQuery({
    queryKey: ['system', 'version', 'settings'],
    queryFn: systemApi.getVersion,
    enabled: open,
    retry: 1,
  })

  const runtimeApiBaseUrl = useMemo(
    () =>
      buildRuntimeApiBaseUrl({
        serverIp: apiServerIpDraft,
        serverPort: apiServerPortDraft,
      }),
    [apiServerIpDraft, apiServerPortDraft],
  )

  const defaultSoftwareManifestUrl = useMemo(
    () => buildDefaultSoftwareManifestUrl(currentApiBaseUrl),
    [currentApiBaseUrl],
  )

  const activeSoftwareManifestUrl = softwareManifestDraft.trim() || defaultSoftwareManifestUrl
  const resolvedSoftwarePackageUrl = useMemo(() => {
    const manualUrl = softwarePackageDraft.trim()
    if (manualUrl) return manualUrl
    if (!softwareManifest?.downloadUrl) return ''
    return resolveSoftwareUpdateUrl(softwareManifest.downloadUrl, activeSoftwareManifestUrl)
  }, [activeSoftwareManifestUrl, softwareManifest, softwarePackageDraft])
  const softwareSaveDestination = softwareSavedPath
    ? resolveSoftwareUpdateFolderPath(softwareSavedPath) || softwareSavedPath
    : softwareDownloadFolder || '浏览器下载目录'

  const softwareUpdateAvailable =
    softwareManifest?.version && typeof currentVersion === 'string'
      ? compareSoftwareVersions(softwareManifest.version, currentVersion) > 0
      : false
  const currentQmlTheme = useMemo(
    () => QML_THEME_OPTIONS.find((item) => item.key === qmlThemeName) ?? QML_THEME_OPTIONS[0],
    [qmlThemeName],
  )
  const currentQmlDisplayStyle = useMemo(
    () =>
      QML_DISPLAY_STYLE_OPTIONS.find((item) => item.key === qmlDisplayStyleName) ?? QML_DISPLAY_STYLE_OPTIONS[0],
    [qmlDisplayStyleName],
  )

  const applyRuntimeApiConnection = () => {
    const nextIp = normalizeApiServerIp(apiServerIpDraft)
    const nextPort = normalizeApiServerPort(apiServerPortDraft)
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
    setApiServerIpDraft(nextIp)
    setApiServerPortDraft(nextPort)
    setCurrentApiBaseUrl(nextBaseUrls.apiBaseUrl)
    applyApiBaseUrlOverride(nextBaseUrls.apiBaseUrl)
    void persistCurrentConnectionSettingsToNative().catch(() => {
      message.warning('保存连接设置到本地配置失败')
    })
    queryClient.invalidateQueries()
    message.success(`API连接已切换到 ${nextBaseUrls.apiBaseUrl}`)
  }

  const restoreDefaultApiProxy = () => {
    applyApiBaseUrlOverride('/api')
    setCurrentApiBaseUrl('/api')
    queryClient.invalidateQueries()
    message.success('API连接已恢复默认代理')
  }

  const checkSoftwareUpdate = async () => {
    const nextManifestUrl = softwareManifestDraft.trim()
    const nextPackageUrl = softwarePackageDraft.trim()
    setSoftwareUpdateManifestUrl(nextManifestUrl)
    setSoftwareUpdatePackageUrl(nextPackageUrl)
    setSoftwareBusy(true)
    setSoftwareStatus('正在检查更新...')
    setSoftwareSavedPath('')
    setSoftwareProgress(0)

    try {
      const response = await fetch(nextManifestUrl || defaultSoftwareManifestUrl)
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`)
      }
      const manifest = normalizeSoftwareUpdateManifest(await response.json())
      if (!manifest.version && !manifest.downloadUrl && !nextPackageUrl) {
        throw new Error('更新清单缺少 version 或下载地址')
      }
      setSoftwareManifest(manifest)
      if (manifest.version && typeof currentVersion === 'string' && compareSoftwareVersions(manifest.version, currentVersion) <= 0) {
        setSoftwareStatus('当前已是最新版本')
      } else if (manifest.version) {
        setSoftwareStatus(`发现新版本 ${manifest.version}`)
      } else {
        setSoftwareStatus('已读取安装包信息')
      }
    } catch (error) {
      if (nextPackageUrl) {
        setSoftwareManifest(null)
        setSoftwareStatus('检查失败，已使用手动安装包地址')
      } else {
        setSoftwareStatus(`检查更新失败: ${error instanceof Error ? error.message : String(error)}`)
      }
    } finally {
      setSoftwareBusy(false)
    }
  }

  const downloadSoftwarePackage = async () => {
    if (!resolvedSoftwarePackageUrl) return
    setSoftwareDownloadBusy(true)
    setSoftwareStatus('正在下载更新包...')
    setSoftwareSavedPath('')
    setSoftwareProgress(0)

    try {
      const result = await downloadSoftwareUpdatePackage({
        url: resolvedSoftwarePackageUrl,
        downloadUrl: softwareManifest?.downloadUrl ?? resolvedSoftwarePackageUrl,
        fileName: softwareManifest?.fileName ?? '',
        onProgress: (event) => setSoftwareProgress(Math.round(event.progress * 100)),
      })
      if (result.status === 'saved') {
        setSoftwareSavedPath(result.path)
        setSoftwareDownloadFolder(resolveSoftwareUpdateFolderPath(result.path) || softwareDownloadFolder)
        setSoftwareProgress(100)
        const openResult = await openDownloadedSoftwareUpdate(result, softwareUpdateAutoOpen)
        if (openResult.status === 'opened') {
          setSoftwareStatus(`更新包已保存并打开：${openResult.path}`)
        } else if (openResult.status === 'unavailable') {
          setSoftwareStatus(`更新包已保存到 ${result.path}，自动打开不可用`)
        } else {
          setSoftwareStatus(`更新包已保存到 ${result.path}`)
        }
      } else if (result.status === 'downloaded') {
        setSoftwareProgress(100)
        setSoftwareStatus(`更新包已下载：${result.fileName}`)
      } else if (result.status === 'cancelled') {
        setSoftwareStatus('已取消下载')
      } else {
        setSoftwareStatus('下载功能不可用')
      }
    } catch (error) {
      setSoftwareStatus(`下载更新失败: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setSoftwareDownloadBusy(false)
    }
  }

  const openSoftwarePackageTarget = async (target: 'folder' | 'package' | 'install') => {
    if (!softwareSavedPath && target !== 'folder') return
    setSoftwareActionBusy(true)
    try {
      const result = await openSoftwareUpdateInstallTarget(softwareSavedPath, target, {
        closeApp: tauriWindow.close,
      })
      if (result.status === 'opened') {
        if (target === 'folder') {
          setSoftwareStatus(`已打开更新目录：${result.path}`)
        } else if (target === 'install') {
          setSoftwareStatus(`已启动安装包并退出：${result.path}`)
        } else {
          setSoftwareStatus(`已打开安装包：${result.path}`)
        }
      } else {
        setSoftwareStatus('打开更新包失败：当前环境不可用')
      }
    } catch (error) {
      setSoftwareStatus(`打开更新包失败: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setSoftwareActionBusy(false)
    }
  }

  const {
    data: testModeStatus,
    isFetching: testModeLoading,
    refetch: refetchTestModeStatus,
  } = useQuery({
    queryKey: ['settings', 'testModeStatus'],
    queryFn: settingsApi.getTestModeStatus,
    enabled: open,
    retry: 1,
  })

  const {
    data: hardwareInfo,
    isFetching: hardwareLoading,
    refetch: refetchHardwareInfo,
  } = useQuery({
    queryKey: ['hardware'],
    queryFn: plcApi.getHardware,
    enabled: open,
    retry: 1,
  })

  const refetchQmlInfoSetting = () => {
    void refetchTestModeStatus()
    void refetchHardwareInfo()
  }

  const cameraAdjustQuery = useQuery({
    queryKey: ['settings', 'cameraAdjust'],
    queryFn: systemApi.getCameraAdjust,
    enabled: open,
    retry: 1,
    refetchInterval: open ? 5000 : false,
  })

  const cameraRows = useMemo(() => buildCameraAdjustmentRows(cameraAdjustQuery.data), [cameraAdjustQuery.data])

  const readCameraDraftValue = (cameraKey: string, field: 'exposureTime' | 'gain', fallback: number) =>
    cameraDrafts[cameraKey]?.[field] ?? fallback

  const setCameraDraftValue = (cameraKey: string, field: 'exposureTime' | 'gain', value: number | null) => {
    setCameraDrafts((current) => ({
      ...current,
      [cameraKey]: {
        ...current[cameraKey],
        [field]: value ?? 0,
      },
    }))
  }

  const testModeMutation = useMutation({
    mutationFn: settingsApi.setTestMode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'testModeStatus'] })
      message.success('测试模式已更新')
    },
    onError: () => {
      message.error('测试模式更新失败')
    },
  })

  const cameraAdjustMutation = useMutation({
    mutationFn: ({
      cameraKey,
      exposureTime,
      gain,
    }: {
      cameraKey: string
      exposureTime: number
      gain: number
    }) => systemApi.setCameraAdjustment(cameraKey, exposureTime, gain, true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'cameraAdjust'] })
      queryClient.invalidateQueries({ queryKey: ['system', 'cameraAdjust'] })
      message.success('相机参数已保存')
    },
    onError: () => {
      message.error('相机参数保存失败')
    },
  })

  const cameraReconnectMutation = useMutation({
    mutationFn: (cameraKey: string) => systemApi.reconnectCameraAdjustment(cameraKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'cameraAdjust'] })
      queryClient.invalidateQueries({ queryKey: ['system', 'cameraAdjust'] })
      message.success('已发送相机重连')
    },
    onError: () => {
      message.error('相机重连失败')
    },
  })

  const runtimeTestModeEnabled = getRuntimeTestMode(testModeStatus)
  const configuredTestModeEnabled = getConfiguredTestMode(testModeStatus)
  const qmlInfoRows = useMemo(
    () =>
      buildQmlInfoSettingRows(testModeStatus, {
        apiServerIp,
        apiServerPort,
        useSharedFolder,
        sharedFolderBaseName,
      }),
    [apiServerIp, apiServerPort, sharedFolderBaseName, testModeStatus, useSharedFolder],
  )

  return (
    <Drawer
      className="settings-panel"
      closable={false}
      extra={renderSettingsPanelCloseButton(onClose)}
      rootClassName="settings-panel-root"
      title={settingsPanelTitle}
      placement="right"
      width="min(520px, 100vw)"
      open={open}
      onClose={onClose}
      destroyOnHidden={false}
    >
      <Tabs
        defaultActiveKey="general"
        items={[
          {
            key: 'general',
            label: settingsTabLabels.general,
            children: (
              <div className="settings-section">
                <QmlGeneralSettingSection title="图像服务">
                  <label className="settings-row">
                    <span>后端</span>
                    <Select
                      className="settings-select"
                      value={useRustImageServer ? 'rust' : 'python'}
                      options={[
                        { label: 'Python', value: 'python' },
                        { label: 'Rust', value: 'rust' },
                      ]}
                      onChange={(value) => setUseRustImageServer(value === 'rust')}
                    />
                  </label>
                  <p className="settings-note">
                    {useRustImageServer ? '当前使用 Rust 图像服务' : '当前使用 Python 图像服务（5010）'}
                  </p>
                  <label className="settings-row">
                    <span>Rust 端口</span>
                    <InputNumber
                      min={1}
                      max={65535}
                      value={rustImageServerPort}
                      disabled={!useRustImageServer}
                      onChange={(value) => setRustImageServerPort(value ?? 6013)}
                    />
                  </label>
                  <p className="settings-note">默认 6013，仅启用 Rust 后生效。</p>
                </QmlGeneralSettingSection>
                <QmlGeneralSettingSection title="AREA 瓦格">
                  <label className="settings-row">
                    <span>初始分块</span>
                    <InputNumber
                      min={1}
                      max={10}
                      value={defaultAreaTileCount}
                      onChange={(value) => setDefaultAreaTileCount(value ?? 3)}
                    />
                  </label>
                  <p className="settings-note">每边块数，默认 3；加载完成后按尺寸自动调整。</p>
                </QmlGeneralSettingSection>
                <QmlGeneralSettingSection title="缓存与显示">
                  <label className="settings-row">
                    <span>启用 1024 缓存模式（falsecolor 缩略图）</span>
                    <Switch checked={enable1024CacheMode} onChange={setEnable1024CacheMode} />
                  </label>
                  <label className="settings-row">
                    <span>显示叠加图层（塔形报警 Error 图层）</span>
                    <Switch checked={showErrorOverlay} onChange={setShowErrorOverlay} />
                  </label>
                </QmlGeneralSettingSection>
                <div className="settings-group-title">API 服务</div>
                <label className="settings-row">
                  <span>服务器 IP</span>
                  <Input
                    className="settings-input"
                    value={apiServerIpDraft}
                    onChange={(event) => setApiServerIpDraft(event.target.value)}
                  />
                </label>
                <label className="settings-row">
                  <span>端口号</span>
                  <InputNumber
                    min={1}
                    max={65535}
                    value={apiServerPortDraft}
                    onChange={(value) => setApiServerPortDraft(value ?? 5011)}
                  />
                </label>
                <div className="settings-row settings-row-stacked">
                  <div className="settings-row-header">
                    <span>当前 API</span>
                    <code>{currentApiBaseUrl}</code>
                  </div>
                  <div className="settings-row-header">
                    <span>目标连接</span>
                    <code>{runtimeApiBaseUrl}</code>
                  </div>
                </div>
                <div className="settings-action-row">
                  <Button type="primary" onClick={applyRuntimeApiConnection}>
                    应用连接
                  </Button>
                  <Button onClick={restoreDefaultApiProxy}>恢复默认代理</Button>
                </div>
                <div className="settings-group-title">服务端口</div>
                <label className="settings-row">
                  <span>数据库端口</span>
                  <InputNumber
                    min={1}
                    max={65535}
                    value={databasPort}
                    onChange={(value) => setDatabasPort(value ?? 6011)}
                  />
                </label>
                <label className="settings-row">
                  <span>数据端口</span>
                  <InputNumber
                    min={1}
                    max={65535}
                    value={dataPort}
                    onChange={(value) => setDataPort(value ?? 6013)}
                  />
                </label>
                <label className="settings-row">
                  <span>PLC端口</span>
                  <InputNumber
                    min={1}
                    max={65535}
                    value={plcPort}
                    onChange={(value) => setPlcPort(value ?? 6014)}
                  />
                </label>
                <label className="settings-row">
                  <span>2D算法端口</span>
                  <InputNumber
                    min={1}
                    max={65535}
                    value={alg2dPort}
                    onChange={(value) => setAlg2dPort(value ?? 5011)}
                  />
                </label>
                <p className="settings-note">
                  默认与 QML CoreSetting 一致：数据库 6011、数据 6013、PLC 6014；2D算法 5011 复用 Rust API；网络报警和远程服务管理分别使用数据库/数据/PLC端口。
                </p>
                <div className="settings-group-title">列表行为</div>
                <label className="settings-row">
                  <span>保持最新自动恢复</span>
                  <InputNumber
                    min={1}
                    max={1440}
                    value={autoKeepTimeMax}
                    onChange={(value) => setAutoKeepTimeMax(value ?? 180)}
                  />
                </label>
                <p className="settings-note">对应 QML CoreSetting.autoKeepTimeMax，单位为 7 秒计时次数，默认 180。</p>
                <div className="settings-group-title">数据展示</div>
                <label className="settings-row">
                  <span>数据头部高度</span>
                  <InputNumber
                    min={120}
                    max={720}
                    value={dataHeaderHeight}
                    onChange={(value) => setDataHeaderHeight(value ?? 320)}
                  />
                </label>
                <p className="settings-note">对应 QML CoreSetting.dataHeaderHeight，默认 320 px。</p>
                <div className="settings-group-title">图像路径</div>
                <label className="settings-row">
                  <span>图像模式</span>
                  <Select
                    className="settings-select"
                    value={useSharedFolder ? 'shared' : 'http'}
                    options={[
                      { label: '共享文件夹模式', value: 'shared' },
                      { label: 'HTTP模式', value: 'http' },
                    ]}
                    onChange={(value) => setUseSharedFolder(value === 'shared')}
                  />
                </label>
                <label className="settings-row">
                  <span>共享根名前缀</span>
                  <Input
                    className="settings-input"
                    value={sharedFolderBaseName}
                    disabled={!useSharedFolder}
                    onChange={(event) => setSharedFolderBaseName(event.target.value)}
                  />
                </label>
                <p className="settings-note">
                  共享路径按 QML 规则拼接为 file:////服务器/{sharedFolderBaseName}S 或 L/流水号；AREA 图像保持 HTTP。
                </p>
                <div className="settings-group-title">图像预缓存</div>
                <label className="settings-row">
                  <span>启用图像预缓存</span>
                  <Switch checked={useImageCache} onChange={setUseImageCache} />
                </label>
                <label className="settings-row">
                  <span>最大缓存项</span>
                  <InputNumber
                    min={1}
                    max={200}
                    value={maxImageCache}
                    disabled={!useImageCache}
                    onChange={(value) => setMaxImageCache(value ?? 15)}
                  />
                </label>
                <p className="settings-note">对应 QML ImageCache，默认关闭，最大缓存项默认 15。</p>
                <div className="settings-group-title">塔形警戒</div>
                <label className="settings-row">
                  <span>上限</span>
                  <InputNumber
                    min={0}
                    max={100}
                    value={towerWarningThresholdUp}
                    onChange={(value) => setTowerWarningThresholdUp(value ?? 100)}
                  />
                </label>
                <label className="settings-row">
                  <span>下限</span>
                  <InputNumber
                    min={-100}
                    max={0}
                    value={towerWarningThresholdDown}
                    onChange={(value) => setTowerWarningThresholdDown(value ?? -100)}
                  />
                </label>
                <div className="settings-row settings-row-stacked">
                  <div className="settings-row-header">
                    <span>叠加透明度</span>
                    <span>{towerWarningOpacity}%</span>
                  </div>
                  <Slider
                    min={0}
                    max={100}
                    value={towerWarningOpacity}
                    onChange={setTowerWarningOpacity}
                  />
                </div>
              </div>
            ),
          },
          {
            key: 'style',
            label: settingsTabLabels.style,
            children: (
              <div className="settings-section">
                <div className="settings-group-title">主题调试</div>
                <div className="settings-tile-grid">
                  {QML_THEME_OPTIONS.map((theme) => {
                    const selected = theme.key === qmlThemeName
                    return (
                      <button
                        key={theme.key}
                        type="button"
                        className={`settings-style-tile${selected ? ' selected' : ''}`}
                        aria-pressed={selected}
                        onClick={() => setQmlThemeName(theme.key)}
                      >
                        <div className="settings-style-tile-header">
                          <strong>{theme.name}</strong>
                          <span>{selected ? '当前' : '切换'}</span>
                        </div>
                        <div className="settings-swatch-row">
                          {[theme.backgroundColor, theme.panelColor, theme.gridLineColor, theme.selectionColor].map(
                            (color) => (
                              <span key={color} className="settings-swatch" style={{ backgroundColor: color }} />
                            ),
                          )}
                        </div>
                        <div
                          className="settings-style-sample"
                          style={{
                            backgroundColor: theme.headerColor,
                            borderColor: selected ? theme.titleColor : theme.headerBorderColor,
                            color: theme.textColor,
                          }}
                        >
                          {theme.key}
                        </div>
                      </button>
                    )
                  })}
                </div>
                <div className="settings-group-title">显示风格</div>
                <div className="settings-tile-grid">
                  {QML_DISPLAY_STYLE_OPTIONS.map((style) => {
                    const selected = style.key === qmlDisplayStyleName
                    return (
                      <button
                        key={style.key}
                        type="button"
                        className={`settings-style-tile${selected ? ' selected' : ''}`}
                        aria-pressed={selected}
                        onClick={() => setQmlDisplayStyleName(style.key)}
                      >
                        <div className="settings-style-tile-header">
                          <strong>{style.name}</strong>
                          <span>{selected ? '当前' : '切换'}</span>
                        </div>
                        <dl className="settings-style-metrics">
                          <div>
                            <dt>顶栏</dt>
                            <dd>{style.topHeight} px</dd>
                          </div>
                          <div>
                            <dt>按钮</dt>
                            <dd>{style.windowButtonWidth} px</dd>
                          </div>
                          <div>
                            <dt>标题</dt>
                            <dd>{style.titleSize} px</dd>
                          </div>
                        </dl>
                      </button>
                    )
                  })}
                </div>
                <div className="settings-group-title">当前令牌</div>
                <div className="settings-token-grid">
                  {[
                    ['应用背景', currentQmlTheme.backgroundColor],
                    ['面板背景', currentQmlTheme.panelColor],
                    ['标题高亮', currentQmlTheme.titleColor],
                    ['选中状态', currentQmlTheme.selectionColor],
                  ].map(([label, color]) => (
                    <div key={label} className="settings-token-row">
                      <span className="settings-swatch" style={{ backgroundColor: color }} />
                      <span>{label}</span>
                      <code>{color}</code>
                    </div>
                  ))}
                </div>
                <div className="settings-row settings-row-stacked">
                  <div className="settings-row-header">
                    <span>
                      {currentQmlTheme.name} / {currentQmlDisplayStyle.name}
                    </span>
                  </div>
                  <p className="settings-note">
                    顶部高度 {currentQmlDisplayStyle.topHeight}，窗口按钮宽度{' '}
                    {currentQmlDisplayStyle.windowButtonWidth}，圆角 {currentQmlDisplayStyle.controlRadius}
                  </p>
                </div>
              </div>
            ),
          },
          {
            key: 'alarm',
            label: settingsTabLabels.alarm,
            children: QML_PLACEHOLDER_SETTINGS_TAB_KEYS.includes('alarm') ? <QmlBaseSettingPlaceholder /> : null,
          },
          {
            key: 'render',
            label: settingsTabLabels.render,
            children: QML_PLACEHOLDER_SETTINGS_TAB_KEYS.includes('render') ? <QmlBaseSettingPlaceholder /> : null,
          },
          {
            key: 'camera',
            label: settingsTabLabels.camera,
            children: (
              <div className="settings-section">
                <div className="settings-group-title">2D 相机调整</div>
                <div className="settings-row settings-row-stacked">
                  <div className="settings-row-header">
                    <span>状态</span>
                    <span>{cameraAdjustQuery.isFetching ? '刷新中' : cameraRows.length > 0 ? '已刷新' : '暂无相机调整项'}</span>
                  </div>
                  <div className="settings-action-row">
                    <Button loading={cameraAdjustQuery.isFetching} onClick={() => cameraAdjustQuery.refetch()}>
                      刷新
                    </Button>
                  </div>
                </div>
                <div className="settings-camera-list">
                  {cameraRows.length > 0 ? (
                    cameraRows.map((camera) => {
                      const exposureTime = readCameraDraftValue(camera.key, 'exposureTime', camera.exposureTime)
                      const gain = readCameraDraftValue(camera.key, 'gain', camera.gain)
                      const busy =
                        (cameraAdjustMutation.isPending &&
                          cameraAdjustMutation.variables?.cameraKey === camera.key) ||
                        (cameraReconnectMutation.isPending && cameraReconnectMutation.variables === camera.key)

                      return (
                        <div className="settings-camera-row" key={camera.key}>
                          <span
                            className={`settings-camera-status ${
                              camera.connected && camera.ok ? 'ok' : camera.connected ? 'warn' : 'error'
                            }`}
                          />
                          <div className="settings-camera-meta">
                            <strong>{camera.key || '--'}</strong>
                            <span>
                              {camera.name || '--'} SN: {camera.sn || '--'}
                            </span>
                            <small>
                              最近帧 {formatCameraFrameAge(camera.lastFrameAge)} / 3D{' '}
                              {formatCameraFrameAge(camera.lastFrameAge3D)}
                              {' · '}
                              参数源 {camera.source || '--'}
                            </small>
                            <small>{camera.message || camera.lastError3D || camera.serviceUrl || camera.paramFile || '--'}</small>
                          </div>
                          <div className="settings-camera-controls">
                            <label className="settings-camera-field">
                              <span className="settings-camera-field-label">曝光时间</span>
                              <InputNumber
                                size="small"
                                min={1}
                                max={1_000_000}
                                value={exposureTime}
                                disabled={!camera.writable || busy}
                                aria-label={`${camera.key} 曝光时间`}
                                onChange={(value) => setCameraDraftValue(camera.key, 'exposureTime', value)}
                              />
                            </label>
                            <label className="settings-camera-field">
                              <span className="settings-camera-field-label">增益</span>
                              <InputNumber
                                size="small"
                                min={0}
                                max={1000}
                                value={gain}
                                disabled={!camera.writable || busy}
                                aria-label={`${camera.key} 增益`}
                                onChange={(value) => setCameraDraftValue(camera.key, 'gain', value)}
                              />
                            </label>
                            <Button
                              size="small"
                              type="primary"
                              disabled={!camera.key || !camera.writable}
                              loading={
                                cameraAdjustMutation.isPending &&
                                cameraAdjustMutation.variables?.cameraKey === camera.key
                              }
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
              </div>
            ),
          },
          {
            key: 'info',
            label: settingsTabLabels.info,
            children: (
              <div className="settings-section">
                <div className="settings-status-row">
                  <Badge status={runtimeTestModeEnabled ? 'error' : 'success'} />
                  <span>{getTestModeLabel(testModeStatus)}</span>
                </div>
                <div className="settings-group-title">系统信息</div>
                <Descriptions size="small" column={1} bordered>
                  {qmlInfoRows.system.map((row) => (
                    <Descriptions.Item key={row.label} label={row.label}>
                      {renderQmlInfoSettingValue(row)}
                    </Descriptions.Item>
                  ))}
                  <Descriptions.Item label="API状态">
                    {testModeLoading ? '刷新中' : '已连接或待后端响应'}
                  </Descriptions.Item>
                  <Descriptions.Item label="硬件信息">
                    {hardwareLoading ? '刷新中' : readStatusField(hardwareInfo, ['status', 'message', 'hardware'])}
                  </Descriptions.Item>
                </Descriptions>
                <div className="settings-group-title">配置信息</div>
                <Descriptions size="small" column={1} bordered>
                  {qmlInfoRows.config.map((row) => (
                    <Descriptions.Item key={row.label} label={row.label}>
                      {row.value}
                    </Descriptions.Item>
                  ))}
                  <Descriptions.Item label="配置文件">
                    {readStatusField(testModeStatus, ['config_file_path', 'configFilePath'])}
                  </Descriptions.Item>
                  <Descriptions.Item label="配置开关">
                    {configuredTestModeEnabled ? '开启' : '关闭'}
                  </Descriptions.Item>
                </Descriptions>
                <div className="settings-action-row">
                  <Button loading={testModeLoading || hardwareLoading} onClick={refetchQmlInfoSetting}>
                    刷新信息
                  </Button>
                </div>
              </div>
            ),
          },
          {
            key: 'other',
            label: settingsTabLabels.other,
            children: (
              <div className="settings-section">
                <QmlSettingGroupBox title="软件更新">
                  <div className="settings-row settings-row-stacked">
                    <div className="settings-row-header">
                      <span>当前版本</span>
                      <code>{typeof currentVersion === 'string' ? currentVersion : '未知'}</code>
                    </div>
                    <div className="settings-row-header">
                      <span>状态</span>
                      <span>{softwareStatus}</span>
                    </div>
                  </div>
                  <label className="settings-row settings-row-stacked">
                    <span>更新清单</span>
                    <Input
                      value={softwareManifestDraft}
                      placeholder={defaultSoftwareManifestUrl}
                      disabled={softwareBusy}
                      onChange={(event) => setSoftwareManifestDraft(event.target.value)}
                      onBlur={() => setSoftwareUpdateManifestUrl(softwareManifestDraft)}
                    />
                  </label>
                  <label className="settings-row settings-row-stacked">
                    <span>安装包</span>
                    <Input
                      value={softwarePackageDraft}
                      placeholder="可选：直接填写 exe/msi/zip 下载地址"
                      disabled={softwareBusy}
                      onChange={(event) => setSoftwarePackageDraft(event.target.value)}
                      onBlur={() => setSoftwareUpdatePackageUrl(softwarePackageDraft)}
                    />
                  </label>
                  <div className="settings-row settings-row-stacked">
                    <div className="settings-row-header">
                      <span>最新版本</span>
                      <code className={softwareUpdateAvailable ? 'settings-code-ok' : undefined}>
                        {softwareManifest?.version || '未获取'}
                      </code>
                    </div>
                    <div className="settings-row-header">
                      <span>保存到</span>
                      <code>{softwareSaveDestination}</code>
                    </div>
                    {softwareManifest?.releaseNotes && <p className="settings-note">{softwareManifest.releaseNotes}</p>}
                  </div>
                  <label className="settings-row">
                    <span>完成后打开</span>
                    <Switch checked={softwareUpdateAutoOpen} onChange={setSoftwareUpdateAutoOpen} />
                  </label>
                  <div className="settings-action-row">
                    <Button loading={softwareBusy} onClick={checkSoftwareUpdate}>
                      检查更新
                    </Button>
                    <Button
                      loading={softwareDownloadBusy}
                      disabled={!resolvedSoftwarePackageUrl}
                      onClick={downloadSoftwarePackage}
                    >
                      下载更新
                    </Button>
                  </div>
                  {(softwareDownloadBusy || softwareProgress > 0) && (
                    <div className="settings-row settings-row-stacked">
                      <div className="settings-row-header">
                        <span>下载进度</span>
                        <span>{softwareProgress > 0 ? `${softwareProgress}%` : '准备中'}</span>
                      </div>
                      <Progress
                        percent={softwareProgress}
                        showInfo={false}
                        status={softwareDownloadBusy ? 'active' : 'normal'}
                      />
                    </div>
                  )}
                  <div className="settings-action-row">
                    <Button
                      disabled={softwareBusy || softwareDownloadBusy}
                      loading={softwareActionBusy}
                      onClick={() => openSoftwarePackageTarget('folder')}
                    >
                      打开目录
                    </Button>
                    <Button
                      disabled={!softwareSavedPath || softwareDownloadBusy}
                      loading={softwareActionBusy}
                      onClick={() => openSoftwarePackageTarget('package')}
                    >
                      打开安装包
                    </Button>
                    <Button
                      danger
                      disabled={!softwareSavedPath || softwareDownloadBusy}
                      loading={softwareActionBusy}
                      onClick={() => openSoftwarePackageTarget('install')}
                    >
                      退出并安装
                    </Button>
                  </div>
                </QmlSettingGroupBox>
                <QmlSettingGroupBox title="调试选项">
                  <label className="settings-row">
                    <span>显示瓦片边框</span>
                    <Switch checked={showTileDebugBorders} onChange={setShowTileDebugBorders} />
                  </label>
                  <p className="settings-note">显示 AREA 视图的瓦片调试边框（绿色=已完成，黄色=加载中）。</p>
                </QmlSettingGroupBox>
                <QmlSettingGroupBox title="系统设置">
                  <label className="settings-row">
                    <span>测试模式</span>
                    <Switch
                      checked={configuredTestModeEnabled}
                      loading={testModeLoading || testModeMutation.isPending}
                      onChange={(checked) => testModeMutation.mutate(checked)}
                    />
                  </label>
                  <p className="settings-note">启用测试模式后，系统将使用测试数据。</p>
                </QmlSettingGroupBox>
              </div>
            ),
          },
        ]}
      />
    </Drawer>
  )
}
