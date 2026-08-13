import { beforeAll, describe, expect, it } from 'vitest'

import mainLayoutSource from './MainLayout.tsx?raw'

let mainLayoutCss = ''

beforeAll(async () => {
  const { readFileSync } = (await import('node:fs')) as {
    readFileSync: (path: URL, encoding: 'utf8') => string
  }

  mainLayoutCss = readFileSync(new URL('./MainLayout.css', import.meta.url), 'utf8')
})

describe('MainLayout QML chrome parity', () => {
  it('mirrors QML mainMenuButton before TopIcon and TopTabBar', () => {
    const mainMenuButtonStart = mainLayoutSource.indexOf('data-qml-main-menu-button')
    const topIconStart = mainLayoutSource.indexOf('data-qml-top-icon')
    const topTabBarStart = mainLayoutSource.indexOf('data-qml-top-tabbar')

    expect(mainMenuButtonStart).toBeGreaterThan(-1)
    expect(topIconStart).toBeGreaterThan(-1)
    expect(topTabBarStart).toBeGreaterThan(-1)
    expect(mainMenuButtonStart).toBeLessThan(topIconStart)
    expect(topIconStart).toBeLessThan(topTabBarStart)

    const mainMenuButtonSource = mainLayoutSource.slice(mainMenuButtonStart - 260, mainMenuButtonStart + 320)

    expect(mainLayoutSource).toContain('MenuOutlined')
    expect(mainMenuButtonSource).toContain('title="主菜单"')
    expect(mainMenuButtonSource).toContain('aria-label="主菜单"')
    expect(mainMenuButtonSource).toContain('data-no-drag')
    expect(mainMenuButtonSource).toContain('data-qml-main-menu-button')
    expect(mainMenuButtonSource).toContain('onClick={() => setMaintenanceOpen(true)}')
  })

  it('mirrors QML HelpButton as a caption help button before the tools menu button', () => {
    const settingButtonStart = mainLayoutSource.indexOf('data-qml-top-setting-button')
    const helpButtonStart = mainLayoutSource.indexOf('data-qml-help-button')
    const toolsButtonStart = mainLayoutSource.indexOf('data-qml-top-tools-button')
    const windowControlsStart = mainLayoutSource.indexOf('data-qml-window-controls')

    expect(settingButtonStart).toBeGreaterThan(-1)
    expect(helpButtonStart).toBeGreaterThan(-1)
    expect(toolsButtonStart).toBeGreaterThan(-1)
    expect(windowControlsStart).toBeGreaterThan(-1)
    expect(settingButtonStart).toBeLessThan(helpButtonStart)
    expect(helpButtonStart).toBeLessThan(toolsButtonStart)
    expect(toolsButtonStart).toBeLessThan(windowControlsStart)

    const helpButtonSource = mainLayoutSource.slice(helpButtonStart - 260, helpButtonStart + 320)

    expect(mainLayoutSource).toContain('QuestionCircleOutlined')
    expect(helpButtonSource).toContain('title="帮助"')
    expect(helpButtonSource).toContain('aria-label="帮助"')
    expect(helpButtonSource).toContain('data-qml-help-button')
    expect(helpButtonSource).toContain('onClick={() => setSystemInfoOpen(true)}')
  })

  it('mirrors QML TopCoilTools S/L surface visibility toggles in the titlebar', () => {
    expect(mainLayoutSource).toContain("import { useCoilStore } from '@/stores/coilStore'")
    expect(mainLayoutSource).toContain('const visibleSurfaces = useCoilStore((state) => state.visibleSurfaces)')
    expect(mainLayoutSource).toContain('const setSurfaceVisible = useCoilStore((state) => state.setSurfaceVisible)')
    expect(mainLayoutSource).toContain('className="top-coil-tools"')
    expect(mainLayoutSource).toContain('data-qml-top-coil-tools')
    expect(mainLayoutSource).toContain('data-qml-surface-visible="S"')
    expect(mainLayoutSource).toContain("checked={visibleSurfaces.includes('S')}")
    expect(mainLayoutSource).toContain("onChange={(event) => setSurfaceVisible('S', event.target.checked)}")
    expect(mainLayoutSource).toContain('data-qml-surface-visible="L"')
    expect(mainLayoutSource).toContain("checked={visibleSurfaces.includes('L')}")
    expect(mainLayoutSource).toContain("onChange={(event) => setSurfaceVisible('L', event.target.checked)}")
    expect(mainLayoutSource).toContain('S端')
    expect(mainLayoutSource).toContain('L端')
  })

  it('mirrors QML TopCoilTools global 2D/3D root-view buttons in the titlebar', () => {
    expect(mainLayoutSource).toContain('const setGlobalRootViewMode = useCoilStore((state) => state.setGlobalRootViewMode)')
    expect(mainLayoutSource).toContain('className="top-coil-view-buttons"')
    expect(mainLayoutSource).toContain('data-qml-root-view-switch="2D"')
    expect(mainLayoutSource).toContain("onClick={() => setGlobalRootViewMode('two')}")
    expect(mainLayoutSource).toContain('2D视图')
    expect(mainLayoutSource).toContain('data-qml-root-view-switch="3D"')
    expect(mainLayoutSource).toContain("onClick={() => setGlobalRootViewMode('three')}")
    expect(mainLayoutSource).toContain('3D视图')
  })

  it('mirrors QML TopCoilTools MASK and QUICK image toggles in the titlebar', () => {
    expect(mainLayoutSource).toContain('const imageMaskChecked = useCoilStore((state) => state.imageMaskChecked)')
    expect(mainLayoutSource).toContain('const quickImageEnabled = useCoilStore((state) => state.quickImageEnabled)')
    expect(mainLayoutSource).toContain('const setImageMaskChecked = useCoilStore((state) => state.setImageMaskChecked)')
    expect(mainLayoutSource).toContain('const setQuickImageEnabled = useCoilStore((state) => state.setQuickImageEnabled)')
    expect(mainLayoutSource).toContain('data-qml-image-mask="MASK"')
    expect(mainLayoutSource).toContain('checked={imageMaskChecked}')
    expect(mainLayoutSource).toContain('onChange={(event) => setImageMaskChecked(event.target.checked)}')
    expect(mainLayoutSource).toContain('MASK')
    expect(mainLayoutSource).toContain('{!imageMaskChecked ? (')
    expect(mainLayoutSource).toContain('data-qml-quick-image="QUICK"')
    expect(mainLayoutSource).toContain('checked={quickImageEnabled}')
    expect(mainLayoutSource).toContain('onChange={(event) => setQuickImageEnabled(event.target.checked)}')
    expect(mainLayoutSource).toContain('QUICK')
  })

  it('mirrors QML TopMsg list mode, local mode, latest flag, and return-realtime action', () => {
    expect(mainLayoutSource).toContain('const currentCoil = useCoilStore((state) => state.currentCoil)')
    expect(mainLayoutSource).toContain('const coilList = useCoilStore((state) => state.coilList)')
    expect(mainLayoutSource).toContain('const coilListMode = useCoilStore((state) => state.coilListMode)')
    expect(mainLayoutSource).toContain(
      'const requestReturnRealtimeMode = useCoilStore((state) => state.requestReturnRealtimeMode)',
    )
    expect(mainLayoutSource).toContain('const topMsgIsLatest = coilListMode === \'realtime\'')
    expect(mainLayoutSource).toContain('const topMsgIsLocal =')
    expect(mainLayoutSource).toContain('data-qml-top-msg')
    expect(mainLayoutSource).toContain('data-qml-list-mode={coilListMode}')
    expect(mainLayoutSource).toContain('data-qml-is-latest={topMsgIsLatest}')
    expect(mainLayoutSource).toContain('data-qml-local-mode={topMsgIsLocal}')
    expect(mainLayoutSource).toContain('data-qml-current-coil-no={currentCoil?.coilNo ??')
    expect(mainLayoutSource).toContain('{topMsgIsLatest ? <span className="top-msg-latest">最新</span> : null}')
    expect(mainLayoutSource).toContain("{coilListMode === 'realtime' ? '实时' : '历史'}")
    expect(mainLayoutSource).toContain("{topMsgIsLocal ? <span className=\"top-msg-local\">Loc</span> : null}")
    expect(mainLayoutSource).toContain('data-qml-return-realtime')
    expect(mainLayoutSource).toContain('onClick={requestReturnRealtimeMode}')
    expect(mainLayoutSource).toContain('<-返回实时')
  })

  it('mirrors QML GlobalErrorView visibility, code, and message after TopMsg', () => {
    const topMsgStart = mainLayoutSource.indexOf('data-qml-top-msg')
    const globalErrorStart = mainLayoutSource.indexOf('data-qml-global-error-view')
    const topCoilToolsStart = mainLayoutSource.indexOf('data-qml-top-coil-tools')
    const globalErrorSource = mainLayoutSource.slice(globalErrorStart - 360, globalErrorStart + 640)

    expect(mainLayoutSource).toContain('const globalAlarmView = buildGlobalAlarmViewModel({')
    expect(mainLayoutSource).toContain('const qmlGlobalErrorItem =')
    expect(mainLayoutSource).toContain('const qmlGlobalErrorVisible = Boolean(qmlGlobalErrorItem)')
    expect(topMsgStart).toBeGreaterThan(-1)
    expect(globalErrorStart).toBeGreaterThan(-1)
    expect(topCoilToolsStart).toBeGreaterThan(-1)
    expect(topMsgStart).toBeLessThan(globalErrorStart)
    expect(globalErrorStart).toBeLessThan(topCoilToolsStart)
    expect(globalErrorSource).toContain('className="qml-global-error-view"')
    expect(globalErrorSource).toContain('data-qml-global-error-view')
    expect(globalErrorSource).toContain('data-qml-global-error-visible={qmlGlobalErrorVisible}')
    expect(globalErrorSource).toContain('data-qml-error-code={qmlGlobalErrorItem?.key ??')
    expect(globalErrorSource).toContain('hidden={!qmlGlobalErrorVisible}')
    expect(globalErrorSource).toContain('className="qml-global-error-code"')
    expect(globalErrorSource).toContain('className="qml-global-error-text"')
    expect(mainLayoutCss).toContain('.qml-global-error-view')
    expect(mainLayoutCss).toContain('flex: 0 0 min(14vw, 180px)')
    expect(mainLayoutCss).toContain('height: 30px')
    expect(mainLayoutCss).toContain('gap: 10px')
    expect(mainLayoutCss).toContain('max-width: min(24vw, 320px)')
    expect(mainLayoutCss).toContain('overflow: hidden')
    expect(mainLayoutCss).toContain('.qml-global-error-code')
    expect(mainLayoutCss).toContain('color: #faad14')
    expect(mainLayoutCss).toContain('.qml-global-error-text')
    expect(mainLayoutCss).toContain('color: #ff4d4f')
    expect(mainLayoutCss).toContain('text-overflow: ellipsis')
  })

  it('mirrors QML TopTools text actions for defect classes, diagnostics, and reports', () => {
    const topToolsStart = mainLayoutSource.indexOf('<div className="top-tools" data-qml-top-tools>')
    const topToolsEnd = mainLayoutSource.indexOf('<div', topToolsStart + 1)
    const topToolsSource = mainLayoutSource.slice(topToolsStart, topToolsEnd)

    expect(topToolsStart).toBeGreaterThan(-1)
    expect(topToolsSource).toContain('onClick={() => setDefectClassOpen(true)}')
    expect(topToolsSource).toContain('缺陷')
    expect(topToolsSource).toContain('onClick={() => setGlobalAlarmOpen(true)}')
    expect(topToolsSource).toContain('诊断')
    expect(topToolsSource).toContain('onClick={() => setExportReportOpen(true)}')
    expect(topToolsSource).toContain('报表')
    expect(mainLayoutCss).toContain('.top-tools')
    expect(mainLayoutCss).toContain('.top-tools button')
  })

  it('mirrors QML SeparatorLine between TopTabBar and TopTools', () => {
    const topTabBarStart = mainLayoutSource.indexOf('data-qml-top-tabbar')
    const separatorStart = mainLayoutSource.indexOf('data-qml-header-separator')
    const topToolsStart = mainLayoutSource.indexOf('data-qml-top-tools')
    const separatorSource = mainLayoutSource.slice(separatorStart - 180, separatorStart + 220)

    expect(topTabBarStart).toBeGreaterThan(-1)
    expect(separatorStart).toBeGreaterThan(-1)
    expect(topToolsStart).toBeGreaterThan(-1)
    expect(topTabBarStart).toBeLessThan(separatorStart)
    expect(separatorStart).toBeLessThan(topToolsStart)
    expect(separatorSource).toContain('className="qml-header-separator"')
    expect(separatorSource).toContain('aria-hidden="true"')
    expect(separatorSource).toContain('data-qml-header-separator')
    expect(mainLayoutCss).toContain('.qml-header-separator')
    expect(mainLayoutCss).toContain('width: 2px')
    expect(mainLayoutCss).toContain('height: calc(100% - 5px)')
    expect(mainLayoutCss).toContain('background: #43caf1')
  })

  it('mirrors QML TopToolsButton as a separate tools menu button near the caption controls', () => {
    const toolsButtonStart = mainLayoutSource.indexOf('data-qml-top-tools-button')
    const toolsButtonSource = mainLayoutSource.slice(toolsButtonStart - 260, toolsButtonStart + 320)
    const windowControlsStart = mainLayoutSource.indexOf('data-qml-window-controls')

    expect(mainLayoutSource).toContain('ToolOutlined')
    expect(toolsButtonStart).toBeGreaterThan(-1)
    expect(toolsButtonStart).toBeLessThan(windowControlsStart)
    expect(toolsButtonSource).toContain('title="工具"')
    expect(toolsButtonSource).toContain('aria-label="工具"')
    expect(toolsButtonSource).toContain('data-qml-top-tools-button')
    expect(toolsButtonSource).toContain('onClick={() => setMaintenanceOpen(true)}')
  })

  it('mirrors QML TopSettingButton as a dedicated settings button before the tools menu button', () => {
    const settingButtonStart = mainLayoutSource.indexOf('data-qml-top-setting-button')
    const toolsButtonStart = mainLayoutSource.indexOf('data-qml-top-tools-button')

    expect(settingButtonStart).toBeGreaterThan(-1)
    expect(toolsButtonStart).toBeGreaterThan(-1)
    expect(settingButtonStart).toBeLessThan(toolsButtonStart)

    const settingButtonSource = mainLayoutSource.slice(settingButtonStart - 260, settingButtonStart + 320)

    expect(mainLayoutSource).toContain('SettingOutlined')
    expect(settingButtonSource).toContain('title="设置"')
    expect(settingButtonSource).toContain('aria-label="设置"')
    expect(settingButtonSource).toContain('data-qml-top-setting-button')
    expect(settingButtonSource).toContain('onClick={() => setSettingsOpen(true)}')
  })

  it('mirrors QML TopTabBar labels and appIndex mapping for the two primary pages', () => {
    const topTabsStart = mainLayoutSource.indexOf('<nav className="top-tabs"')
    const topTabsEnd = mainLayoutSource.indexOf('</nav>', topTabsStart)
    const topTabsSource = mainLayoutSource.slice(topTabsStart, topTabsEnd)

    expect(topTabsSource).toContain('data-qml-top-tabbar')
    expect(topTabsSource).toContain('to="/data"')
    expect(topTabsSource).toContain('data-qml-app-index={0}')
    expect(topTabsSource).toContain('数据分析')
    expect(topTabsSource).toContain('to="/defect"')
    expect(topTabsSource).toContain('data-qml-app-index={1}')
    expect(topTabsSource).toContain('缺陷分析')
    expect(topTabsSource).not.toContain('数据展示')
    expect(topTabsSource).not.toContain('缺陷检测')
  })

  it('mirrors QML TopIcon as a theme toggle bound to coreStyle isDark state', () => {
    expect(mainLayoutSource).toContain("QML_THEME_OPTIONS")
    expect(mainLayoutSource).toContain("getNextQmlTopIconThemeName")
    expect(mainLayoutSource).toContain('const qmlThemeName = useUiSettingsStore((state) => state.qmlThemeName)')
    expect(mainLayoutSource).toContain('const setQmlThemeName = useUiSettingsStore((state) => state.setQmlThemeName)')
    expect(mainLayoutSource).toContain('const activeQmlTheme =')
    expect(mainLayoutSource).toContain('const handleTopIconClick =')
    expect(mainLayoutSource).toContain('setQmlThemeName(getNextQmlTopIconThemeName(qmlThemeName))')
    expect(mainLayoutSource).toContain('data-qml-theme={activeQmlTheme.key}')
    expect(mainLayoutSource).toContain('data-qml-is-dark={activeQmlTheme.isDark}')
    expect(mainLayoutSource).toContain('data-qml-top-icon')
    expect(mainLayoutSource).toContain('onClick={handleTopIconClick}')
    expect(mainLayoutCss).toContain('--qml-header-background')
    expect(mainLayoutCss).toContain('--qml-text-color')
    expect(mainLayoutCss).toContain('.brand-mark')
  })

  it('mirrors QML TitleLabel with the core appTitle and double-click window toggle', () => {
    expect(mainLayoutSource).toContain('const qmlAppTitle =')
    expect(mainLayoutSource).toContain('涟钢热轧1580端面缺陷检测系统')
    expect(mainLayoutSource).toContain('className="qml-title-label"')
    expect(mainLayoutSource).toContain('data-qml-title-label')
    expect(mainLayoutSource).toContain('onDoubleClick={handleWindowModelChangeClick}')
    expect(mainLayoutSource).toContain('{qmlAppTitle}')
    expect(mainLayoutCss).toContain('.qml-title-label')
    expect(mainLayoutCss).toContain('color: var(--qml-title-color)')
    expect(mainLayoutCss).toContain('font-weight: 800')
  })

  it('mirrors QML TimeText as a second-precision header clock', () => {
    expect(mainLayoutSource).toContain("import { formatQmlTimeText } from '@/utils/qmlDateTime'")
    expect(mainLayoutSource).toContain('const [currentTime, setCurrentTime] = useState(() => new Date())')
    expect(mainLayoutSource).toContain('window.setInterval(() => setCurrentTime(new Date()), 1000)')
    expect(mainLayoutSource).toContain('window.clearInterval(timer)')
    expect(mainLayoutSource).toContain('className="qml-time-text"')
    expect(mainLayoutSource).toContain('data-qml-time-text')
    expect(mainLayoutSource).toContain('{formatQmlTimeText(currentTime)}')
    expect(mainLayoutCss).toContain('.qml-time-text')
    expect(mainLayoutCss).toContain('font-size: 24px')
  })

  it('mirrors QML GlobalServerMsg as a service socket row before TimeText', () => {
    const serverMsgStart = mainLayoutSource.indexOf('<div className="qml-global-server-msg"')
    const serverMsgEnd = mainLayoutSource.indexOf('</div>', serverMsgStart)
    const serverMsgSource = mainLayoutSource.slice(serverMsgStart, serverMsgEnd)
    const timeTextStart = mainLayoutSource.indexOf('data-qml-time-text')

    expect(mainLayoutSource).toContain(
      "import { buildApiDelayView, buildQmlGlobalServerMsgRows } from '@/utils/serviceConnection'",
    )
    expect(mainLayoutSource).toContain('const qmlGlobalServerMsgRows = buildQmlGlobalServerMsgRows(apiDelayView)')
    expect(serverMsgStart).toBeGreaterThan(-1)
    expect(serverMsgStart).toBeLessThan(timeTextStart)
    expect(serverMsgSource).toContain('data-qml-global-server-msg')
    expect(serverMsgSource).toContain('data-qml-server-msg-socket')
    expect(serverMsgSource).toContain('data-qml-service-key={row.key}')
    expect(serverMsgSource).toContain('qmlGlobalServerMsgRows.map((row) =>')
    expect(serverMsgSource).toContain('label={row.label}')
    expect(serverMsgSource).toContain('state={row.state}')
    expect(serverMsgSource).toContain('title={row.title}')
    expect(mainLayoutCss).toContain('.qml-global-server-msg')
    const serverMsgRule = mainLayoutCss.match(/\.qml-global-server-msg\s*\{([^}]*)\}/)?.[1] ?? ''
    expect(serverMsgRule).toContain('flex: 0 0 auto')
  })

  it('mirrors QML FootView API URL click target that opens ConnectDialog', () => {
    const statusbarStart = mainLayoutSource.indexOf('<footer className="motion-statusbar"')
    const statusbarEnd = mainLayoutSource.indexOf('</footer>', statusbarStart)
    const statusbarSource = mainLayoutSource.slice(statusbarStart, statusbarEnd)

    expect(mainLayoutSource).toContain("import ConnectSettingsModal from '@/components/ConnectSettingsModal'")
    expect(mainLayoutSource).toContain('const [connectSettingsOpen, setConnectSettingsOpen] = useState(false)')
    expect(mainLayoutSource).toContain('<OperationSidebar onOpenConnectSettings={() => setConnectSettingsOpen(true)} />')
    expect(statusbarSource).toContain('data-qml-foot-view')
    expect(statusbarSource).toContain('data-qml-connect-server-url')
    expect(statusbarSource).toContain('onClick={() => setConnectSettingsOpen(true)}')
    expect(statusbarSource).toContain('{serviceBaseUrls.apiBaseUrl}')
    expect(statusbarSource).toContain('延时：')
    expect(mainLayoutSource).toContain(
      '<ConnectSettingsModal open={connectSettingsOpen} onClose={() => setConnectSettingsOpen(false)} />',
    )
  })

  it('mirrors QML WindowCaptionButton and TopWindowModelChangeButton state in the titlebar', () => {
    const windowControlsStart = mainLayoutSource.indexOf('<div className="qml-window-controls"')
    const windowControlsEnd = mainLayoutSource.indexOf('</div>', windowControlsStart)
    const windowControlsSource = mainLayoutSource.slice(windowControlsStart, windowControlsEnd)

    expect(mainLayoutSource).toContain('const [windowIsMaximized, setWindowIsMaximized] = useState(false)')
    expect(mainLayoutSource).toContain('const refreshWindowCaptionState = async () =>')
    expect(mainLayoutSource).toContain('await tauriWindow.getState()')
    expect(mainLayoutSource).toContain('setWindowIsMaximized(Boolean(state.maximized || state.fullscreen))')
    expect(mainLayoutSource).toContain("const qmlWindowModelButtonType = windowIsMaximized ? 'restore' : 'maximize'")
    expect(mainLayoutSource).toContain("const qmlWindowModelTipText = windowIsMaximized ? '还原' : '最大化'")
    expect(mainLayoutSource).toContain('const handleWindowModelChangeClick = async () =>')
    expect(mainLayoutSource).toContain('onDoubleClick={handleWindowModelChangeClick}')
    expect(windowControlsStart).toBeGreaterThan(-1)
    expect(windowControlsSource).toContain('data-qml-window-controls')
    expect(windowControlsSource).toContain('data-qml-window-button="minimize"')
    expect(windowControlsSource).toContain('title="最小化"')
    expect(windowControlsSource).toContain('onClick={() => tauriWindow.minimize()}')
    expect(windowControlsSource).toContain('data-qml-window-button="model-change"')
    expect(windowControlsSource).toContain('data-qml-button-type={qmlWindowModelButtonType}')
    expect(windowControlsSource).toContain('title={qmlWindowModelTipText}')
    expect(windowControlsSource).toContain('onClick={handleWindowModelChangeClick}')
    expect(windowControlsSource).toContain('data-qml-window-button="close"')
    expect(windowControlsSource).toContain('data-qml-button-type="close"')
    expect(windowControlsSource).toContain('title="关闭"')
    expect(windowControlsSource).toContain('onClick={() => tauriWindow.close()}')
    expect(mainLayoutCss).toContain('.qml-window-controls')
  })

  it('keeps the mobile chrome and workspace constrained to the Tauri viewport', () => {
    expect(mainLayoutCss).toMatch(
      /@media \(max-width: 900px\)[\s\S]*\.motion-titlebar,\s*\.motion-main,\s*\.workspace\s*\{[\s\S]*width:\s*100%[\s\S]*max-width:\s*100%[\s\S]*overflow-x:\s*hidden/,
    )
    expect(mainLayoutCss).toMatch(
      /@media \(max-width: 900px\)[\s\S]*\.motion-main\s*\{[\s\S]*min-width:\s*0/,
    )
  })

  it('keeps the desktop chrome constrained while the service row tools scroll internally', () => {
    const desktopShellRule = mainLayoutCss.match(/\.motion-shell\s*\{([^}]*)\}/)?.[1] ?? ''
    const desktopTitlebarRule = mainLayoutCss.match(/\.motion-titlebar\s*\{([^}]*)\}/)?.[1] ?? ''
    const desktopToolsRule = mainLayoutCss.match(/\.titlebar-tools\s*\{([^}]*)\}/)?.[1] ?? ''

    expect(desktopShellRule).toContain('max-width: 100vw')
    expect(desktopShellRule).toContain('grid-template-columns: minmax(0, 1fr)')
    expect(desktopTitlebarRule).toContain('width: 100%')
    expect(desktopTitlebarRule).toContain('max-width: 100%')
    expect(desktopTitlebarRule).toContain('overflow: hidden')
    expect(desktopToolsRule).toContain('flex: 1 1 auto')
    expect(desktopToolsRule).toContain('overflow-x: auto')
  })
})
