import { useEffect, useMemo, useState, type CSSProperties } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  AlertOutlined,
  ApiOutlined,
  BugOutlined,
  CloseOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  FileExcelOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  MenuOutlined,
  MinusOutlined,
  QuestionCircleOutlined,
  ScissorOutlined,
  SettingOutlined,
  TagsOutlined,
  ToolOutlined,
} from '@ant-design/icons'

import ApiHistoryModal from '@/components/ApiHistoryModal'
import AlgTestModal from '@/components/AlgTestModal'
import ClipSettingModal from '@/components/ClipSettingModal'
import DefectClassModal from '@/components/DefectClassModal'
import ExportReportModal from '@/components/ExportReportModal'
import GlobalAlarmModal from '@/components/GlobalAlarmModal'
import ImageCacheModal from '@/components/ImageCacheModal'
import MaintenanceMenuModal from '@/components/MaintenanceMenuModal'
import OperationSidebar from '@/components/OperationSidebar'
import SettingsPanel from '@/components/SettingsPanel'
import SystemInfoModal from '@/components/SystemInfoModal'
import ConnectSettingsModal from '@/components/ConnectSettingsModal'
import { serviceBaseUrls, settingsApi, systemApi } from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import { QML_THEME_OPTIONS, getNextQmlTopIconThemeName, useUiSettingsStore } from '@/stores/uiSettingsStore'
import { hasTauriRuntime, tauriWindow } from '@/utils/tauriWindow'
import { buildGlobalAlarmViewModel } from '@/utils/globalAlarm'
import { buildQmlWindowTitle, getRuntimeTestMode, getTestModeLabel } from '@/utils/testMode'
import { buildApiDelayView, buildQmlGlobalServerMsgRows } from '@/utils/serviceConnection'
import { formatQmlTimeText } from '@/utils/qmlDateTime'
import './MainLayout.css'

function ServiceLight({
  label,
  state,
  title,
  serviceKey,
}: {
  label: string
  state: 'ok' | 'warn' | 'error'
  title?: string
  serviceKey?: string
}) {
  return (
    <span className={`service-light ${state}`} title={title} data-qml-service-key={serviceKey}>
      <i />
      {label}
    </span>
  )
}

function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const isDefect = location.pathname.includes('defect')
  const isSystem = location.pathname.includes('system')
  const isData = !isDefect && !isSystem
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [globalAlarmOpen, setGlobalAlarmOpen] = useState(false)
  const [algTestOpen, setAlgTestOpen] = useState(false)
  const [defectClassOpen, setDefectClassOpen] = useState(false)
  const [exportReportOpen, setExportReportOpen] = useState(false)
  const [systemInfoOpen, setSystemInfoOpen] = useState(false)
  const [apiHistoryOpen, setApiHistoryOpen] = useState(false)
  const [imageCacheOpen, setImageCacheOpen] = useState(false)
  const [maintenanceOpen, setMaintenanceOpen] = useState(false)
  const [clipSettingOpen, setClipSettingOpen] = useState(false)
  const [connectSettingsOpen, setConnectSettingsOpen] = useState(false)
  const currentCoil = useCoilStore((state) => state.currentCoil)
  const coilList = useCoilStore((state) => state.coilList)
  const coilListMode = useCoilStore((state) => state.coilListMode)
  const visibleSurfaces = useCoilStore((state) => state.visibleSurfaces)
  const imageMaskChecked = useCoilStore((state) => state.imageMaskChecked)
  const quickImageEnabled = useCoilStore((state) => state.quickImageEnabled)
  const requestReturnRealtimeMode = useCoilStore((state) => state.requestReturnRealtimeMode)
  const setSurfaceVisible = useCoilStore((state) => state.setSurfaceVisible)
  const setGlobalRootViewMode = useCoilStore((state) => state.setGlobalRootViewMode)
  const setImageMaskChecked = useCoilStore((state) => state.setImageMaskChecked)
  const setQuickImageEnabled = useCoilStore((state) => state.setQuickImageEnabled)
  const qmlThemeName = useUiSettingsStore((state) => state.qmlThemeName)
  const setQmlThemeName = useUiSettingsStore((state) => state.setQmlThemeName)
  const [currentTime, setCurrentTime] = useState(() => new Date())
  const [windowIsMaximized, setWindowIsMaximized] = useState(false)

  const activeQmlTheme = useMemo(
    () => QML_THEME_OPTIONS.find((item) => item.key === qmlThemeName) ?? QML_THEME_OPTIONS[0],
    [qmlThemeName],
  )
  const qmlThemeStyle = {
    '--qml-app-background': activeQmlTheme.backgroundColor,
    '--qml-panel-background': activeQmlTheme.panelColor,
    '--qml-panel-elevated': activeQmlTheme.panelElevatedColor,
    '--qml-header-background': activeQmlTheme.headerColor,
    '--qml-header-border': activeQmlTheme.headerBorderColor,
    '--qml-title-color': activeQmlTheme.titleColor,
    '--qml-text-color': activeQmlTheme.textColor,
    '--qml-time-color': activeQmlTheme.isDark ? '#DDEBFF' : activeQmlTheme.textColor,
    '--qml-label-color': activeQmlTheme.labelColor,
    '--qml-grid-line': activeQmlTheme.gridLineColor,
    '--qml-selection-color': activeQmlTheme.selectionColor,
    '--qml-button-hover': activeQmlTheme.key === 'blue' ? '#1e496d' : activeQmlTheme.isDark ? '#26394a' : '#dce7f1',
  } as CSSProperties
  const handleTopIconClick = () => {
    setQmlThemeName(getNextQmlTopIconThemeName(qmlThemeName))
  }
  const qmlAppTitle = '涟钢热轧1580端面缺陷检测系统'
  const refreshWindowCaptionState = async () => {
    const state = await tauriWindow.getState()
    if (!state) return
    setWindowIsMaximized(Boolean(state.maximized || state.fullscreen))
  }
  const handleWindowModelChangeClick = async () => {
    await tauriWindow.toggleMaximize()
    await refreshWindowCaptionState()
  }
  const qmlWindowModelButtonType = windowIsMaximized ? 'restore' : 'maximize'
  const qmlWindowModelTipText = windowIsMaximized ? '还原' : '最大化'

  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    void refreshWindowCaptionState()
  }, [])

  const { data: testModeStatus } = useQuery({
    queryKey: ['settings', 'testModeStatus'],
    queryFn: settingsApi.getTestModeStatus,
    retry: 1,
    staleTime: 30_000,
  })

  const testModeEnabled = getRuntimeTestMode(testModeStatus)
  useEffect(() => {
    document.title = buildQmlWindowTitle(testModeStatus)
  }, [testModeStatus])

  const { data: cameraAlarmData } = useQuery({
    queryKey: ['globalAlarm', 'cameraAlarm', 'summary'],
    queryFn: systemApi.getCameraAlarm,
    retry: 1,
    refetchInterval: 10_000,
  })
  const { data: hardwareAlarmData } = useQuery({
    queryKey: ['globalAlarm', 'hardware', 'summary'],
    queryFn: systemApi.getHardware,
    retry: 1,
    refetchInterval: 10_000,
  })
  const globalAlarmView = buildGlobalAlarmViewModel({
    cameraAlarm: cameraAlarmData,
    hardware: hardwareAlarmData,
  })
  const globalAlarmLevel = globalAlarmView.maxLevel
  const qmlGlobalErrorItem = [...globalAlarmView.cameras, ...globalAlarmView.hardware].find((item) => item.level > 1)
  const qmlGlobalErrorVisible = Boolean(qmlGlobalErrorItem)
  const apiDelayQuery = useQuery({
    queryKey: ['startup', 'apiDelay'],
    queryFn: async () => {
      const startTime = Date.now()
      await systemApi.getDelay()
      return Date.now() - startTime
    },
    retry: 1,
    refetchInterval: 8_000,
  })
  const apiDelayView = buildApiDelayView(apiDelayQuery.isError ? -1 : apiDelayQuery.data)
  const qmlGlobalServerMsgRows = buildQmlGlobalServerMsgRows(apiDelayView)
  const topMsgIsLatest = coilListMode === 'realtime' && Boolean(currentCoil && coilList[0]?.id === currentCoil.id)
  const topMsgIsLocal =
    typeof window !== 'undefined' && (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost')

  return (
    <div
      className="motion-shell"
      data-qml-theme={activeQmlTheme.key}
      data-qml-is-dark={activeQmlTheme.isDark}
      style={qmlThemeStyle}
    >
      <header className="motion-titlebar" data-tauri-drag-region onDoubleClick={handleWindowModelChangeClick}>
        <button
          className="icon-button"
          type="button"
          title="主菜单"
          aria-label="主菜单"
          data-no-drag
          data-qml-main-menu-button
          onClick={() => setMaintenanceOpen(true)}
        >
          <MenuOutlined />
        </button>
        <div className="brand-block" data-no-drag>
          <button
            className="brand-mark"
            type="button"
            title="切换深浅主题"
            aria-label="切换深浅主题"
            data-qml-top-icon
            onClick={handleTopIconClick}
          >
            MS
          </button>
          <button className="brand-copy" type="button" onClick={() => navigate('/data')}>
            <div className="brand-title">涟钢3D端面检测系统</div>
            <div className="brand-subtitle">Motion Studio · Tauri + React</div>
          </button>
        </div>

        <nav className="top-tabs" data-no-drag data-qml-top-tabbar>
          <NavLink to="/data" data-qml-app-index={0} className={({ isActive }) => (isActive || isData ? 'active' : '')}>
            数据分析
          </NavLink>
          <NavLink to="/defect" data-qml-app-index={1} className={({ isActive }) => (isActive ? 'active' : '')}>
            缺陷分析
          </NavLink>
          <NavLink to="/system" className={({ isActive }) => (isActive ? 'active' : '')}>
            系统诊断
          </NavLink>
        </nav>
        <span className="qml-header-separator" aria-hidden="true" data-qml-header-separator />

        <div className="qml-title-label" data-qml-title-label onDoubleClick={handleWindowModelChangeClick}>
          {qmlAppTitle}
        </div>

        <div className="titlebar-tools" data-no-drag>
          <div className="qml-global-server-msg" data-qml-global-server-msg data-qml-server-msg-socket>
            {qmlGlobalServerMsgRows.map((row) => (
              <ServiceLight
                key={row.key}
                data-qml-service-key={row.key}
                serviceKey={row.key}
                label={row.label}
                state={row.state}
                title={row.title}
              />
            ))}
          </div>
          <time className="qml-time-text" data-qml-time-text dateTime={currentTime.toISOString()}>
            {formatQmlTimeText(currentTime)}
          </time>
          <div className="top-tools" data-qml-top-tools>
            <button type="button" onClick={() => setDefectClassOpen(true)}>
              缺陷
            </button>
            <button type="button" onClick={() => setGlobalAlarmOpen(true)}>
              诊断
            </button>
            <button type="button" onClick={() => setExportReportOpen(true)}>
              报表
            </button>
          </div>
          <div
            className="top-msg"
            data-qml-top-msg
            data-qml-list-mode={coilListMode}
            data-qml-is-latest={topMsgIsLatest}
            data-qml-local-mode={topMsgIsLocal}
            data-qml-current-coil-no={currentCoil?.coilNo ?? ''}
          >
            {topMsgIsLatest ? <span className="top-msg-latest">最新</span> : null}
            <span className={`top-msg-mode ${coilListMode}`}>{coilListMode === 'realtime' ? '实时' : '历史'}</span>
            {topMsgIsLocal ? <span className="top-msg-local">Loc</span> : null}
            {coilListMode === 'history' ? (
              <button type="button" data-qml-return-realtime onClick={requestReturnRealtimeMode}>
                {'<-返回实时'}
              </button>
            ) : null}
            {currentCoil ? <strong className="top-msg-coil">{currentCoil.coilNo}</strong> : null}
          </div>
          <div
            className="qml-global-error-view"
            data-qml-global-error-view
            data-qml-global-error-visible={qmlGlobalErrorVisible}
            data-qml-error-code={qmlGlobalErrorItem?.key ?? ''}
            hidden={!qmlGlobalErrorVisible}
          >
            <AlertOutlined aria-hidden="true" />
            <span className="qml-global-error-code">{qmlGlobalErrorItem?.key ?? ''}</span>
            <span className="qml-global-error-text">{qmlGlobalErrorItem?.message ?? ''}</span>
          </div>
          <div className="top-coil-tools" data-qml-top-coil-tools>
            <div className="top-coil-view-buttons">
              <button type="button" data-qml-root-view-switch="2D" onClick={() => setGlobalRootViewMode('two')}>
                2D视图
              </button>
              <button type="button" data-qml-root-view-switch="3D" onClick={() => setGlobalRootViewMode('three')}>
                3D视图
              </button>
            </div>
            <label className="top-coil-check top-coil-check-mask" data-qml-image-mask="MASK">
              <input
                type="checkbox"
                checked={imageMaskChecked}
                onChange={(event) => setImageMaskChecked(event.target.checked)}
              />
              MASK
            </label>
            {!imageMaskChecked ? (
              <label className="top-coil-check top-coil-check-quick" data-qml-quick-image="QUICK">
                <input
                  type="checkbox"
                  checked={quickImageEnabled}
                  onChange={(event) => setQuickImageEnabled(event.target.checked)}
                />
                QUICK
              </label>
            ) : null}
            <span className="top-coil-separator" aria-hidden="true" />
            <label className="top-coil-check" data-qml-surface-visible="S">
              <input
                type="checkbox"
                checked={visibleSurfaces.includes('S')}
                onChange={(event) => setSurfaceVisible('S', event.target.checked)}
              />
              S端
            </label>
            <label className="top-coil-check" data-qml-surface-visible="L">
              <input
                type="checkbox"
                checked={visibleSurfaces.includes('L')}
                onChange={(event) => setSurfaceVisible('L', event.target.checked)}
              />
              L端
            </label>
          </div>
          <span className={`test-mode-badge ${testModeEnabled ? 'enabled' : 'normal'}`}>
            {getTestModeLabel(testModeStatus)}
          </span>
          <button
            className={`global-alarm level-${Math.min(Math.max(globalAlarmLevel, 1), 3)}`}
            type="button"
            title="设备报警"
            onClick={() => setGlobalAlarmOpen(true)}
          >
            <AlertOutlined />
            全局报警
          </button>
          <button className="icon-button" type="button" title="缺陷列表" onClick={() => setDefectClassOpen(true)}>
            <TagsOutlined />
          </button>
          <button className="icon-button" type="button" title="算法测试" onClick={() => setAlgTestOpen(true)}>
            <ExperimentOutlined />
          </button>
          <button className="icon-button" type="button" title="裁剪设置" onClick={() => setClipSettingOpen(true)}>
            <ScissorOutlined />
          </button>
          <button className="icon-button" type="button" title="报表导出" onClick={() => setExportReportOpen(true)}>
            <FileExcelOutlined />
          </button>
          <button className="icon-button" type="button" title="API 调用记录" onClick={() => setApiHistoryOpen(true)}>
            <ApiOutlined />
          </button>
          <button className="icon-button" type="button" title="图像缓存" onClick={() => setImageCacheOpen(true)}>
            <DatabaseOutlined />
          </button>
          <button
            className="icon-button"
            type="button"
            title="设置"
            aria-label="设置"
            data-qml-top-setting-button
            onClick={() => setSettingsOpen(true)}
          >
            <SettingOutlined />
          </button>
          <button
            className="icon-button"
            type="button"
            title="帮助"
            aria-label="帮助"
            data-qml-help-button
            onClick={() => setSystemInfoOpen(true)}
          >
            <QuestionCircleOutlined />
          </button>
          <button
            className="icon-button"
            type="button"
            title="工具"
            aria-label="工具"
            data-qml-top-tools-button
            onClick={() => setMaintenanceOpen(true)}
          >
            <ToolOutlined />
          </button>
          <div className="qml-window-controls" data-qml-window-controls>
            <button
              className="icon-button"
              type="button"
              title="最小化"
              data-qml-window-button="minimize"
              data-qml-button-type="minimize"
              onClick={() => tauriWindow.minimize()}
            >
              <MinusOutlined />
            </button>
            <button
              className="icon-button"
              type="button"
              title={qmlWindowModelTipText}
              data-qml-window-button="model-change"
              data-qml-button-type={qmlWindowModelButtonType}
              onClick={handleWindowModelChangeClick}
            >
              {windowIsMaximized ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            </button>
            <button
              className="icon-button danger"
              type="button"
              title="关闭"
              data-qml-window-button="close"
              data-qml-button-type="close"
              onClick={() => tauriWindow.close()}
            >
              <CloseOutlined />
            </button>
          </div>
        </div>
      </header>

      <main className="motion-main">
        <OperationSidebar onOpenConnectSettings={() => setConnectSettingsOpen(true)} />
        <section className="workspace">
          <Outlet />
        </section>
      </main>

      <footer className="motion-statusbar" data-qml-foot-view>
        <button
          className="statusbar-connect-url"
          type="button"
          data-qml-connect-server-url
          onClick={() => setConnectSettingsOpen(true)}
        >
          {serviceBaseUrls.apiBaseUrl}
        </button>
        <span className="statusbar-delay-label">延时：</span>
        <span className={`statusbar-delay ${apiDelayView.state}`}>{apiDelayView.label}</span>
        <span>{hasTauriRuntime() ? 'Tauri native shell' : 'Web preview mode'}</span>
        <span>图像 / 缺陷 / 3D数据 分级加载</span>
        <span>
          <BugOutlined /> 缺陷数据随卷材与表面切换刷新
        </span>
      </footer>
      <GlobalAlarmModal open={globalAlarmOpen} onClose={() => setGlobalAlarmOpen(false)} />
      <AlgTestModal open={algTestOpen} onClose={() => setAlgTestOpen(false)} />
      <ClipSettingModal open={clipSettingOpen} onClose={() => setClipSettingOpen(false)} />
      <DefectClassModal open={defectClassOpen} onClose={() => setDefectClassOpen(false)} />
      <ExportReportModal open={exportReportOpen} onClose={() => setExportReportOpen(false)} />
      <ApiHistoryModal open={apiHistoryOpen} onClose={() => setApiHistoryOpen(false)} />
      <ImageCacheModal open={imageCacheOpen} onClose={() => setImageCacheOpen(false)} />
      <MaintenanceMenuModal open={maintenanceOpen} onClose={() => setMaintenanceOpen(false)} />
      <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <SystemInfoModal open={systemInfoOpen} onClose={() => setSystemInfoOpen(false)} />
      <ConnectSettingsModal open={connectSettingsOpen} onClose={() => setConnectSettingsOpen(false)} />
    </div>
  )
}

export default MainLayout
