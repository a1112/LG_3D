import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import settingsPanelSource from './index.tsx?raw'

const settingsPanelCss = readFileSync(fileURLToPath(new URL('./SettingsPanel.css', import.meta.url)), 'utf8')
const qmlCameraSettingSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/SettingPage/CameraSetting/CameraSetting.qml', import.meta.url)),
  'utf8',
)

describe('SettingsPanel QML CoreSetting parity', () => {
  it('uses the QML SettingPage title and subtitle in the drawer header', () => {
    expect(settingsPanelSource).toContain('const settingsPanelTitle = (')
    expect(settingsPanelSource).toContain('<span>设置</span>')
    expect(settingsPanelSource).toContain('<small>系统参数与显示配置</small>')
    expect(settingsPanelSource).toContain('title={settingsPanelTitle}')
    expect(settingsPanelSource).not.toMatch(/<Drawer[^>]*title="系统设置"/)
  })

  it('places the QML SettingPage close button on the right side of the header', () => {
    expect(settingsPanelSource).toContain('function renderSettingsPanelCloseButton')
    expect(settingsPanelSource).toContain('className="settings-panel-close"')
    expect(settingsPanelSource).toContain('aria-label="关闭"')
    expect(settingsPanelSource).toContain('title="关闭"')
    expect(settingsPanelSource).toContain('onClick={onClose}')
    expect(settingsPanelSource).toContain('closable={false}')
    expect(settingsPanelSource).toContain('extra={renderSettingsPanelCloseButton(onClose)}')
    expect(settingsPanelCss).toContain('.settings-panel-close')
    expect(settingsPanelCss).toContain('width: 40px')
    expect(settingsPanelCss).toContain('height: 40px')
  })

  it('renders QML GeneralSetting sections before React-only service controls', () => {
    expect(settingsPanelSource).toMatch(
      /<QmlGeneralSettingSection title="图像服务">[\s\S]*<span>后端<\/span>[\s\S]*当前使用 Rust 图像服务[\s\S]*当前使用 Python 图像服务（5010）[\s\S]*<span>Rust 端口<\/span>[\s\S]*默认 6013，仅启用 Rust 后生效[\s\S]*<QmlGeneralSettingSection title="AREA 瓦格">[\s\S]*<span>初始分块<\/span>[\s\S]*每边块数，默认 3；加载完成后按尺寸自动调整[\s\S]*<QmlGeneralSettingSection title="缓存与显示">[\s\S]*启用 1024 缓存模式（falsecolor 缩略图）[\s\S]*显示叠加图层（塔形报警 Error 图层）[\s\S]*<div className="settings-group-title">API 服务<\/div>/,
    )
  })

  it('keeps the API service port input fallback on the non-conflicting Rust API port', () => {
    expect(settingsPanelSource).toContain('onChange={(value) => setApiServerPortDraft(value ?? 5011)}')
  })

  it('keeps the Rust 2D algorithm service folded into the non-conflicting API port', () => {
    expect(settingsPanelSource).toContain('onChange={(value) => setAlg2dPort(value ?? 5011)}')
    expect(settingsPanelSource).toContain('2D算法 5011')
    expect(settingsPanelSource).not.toContain('2D算法 6020')
  })

  it('documents the independent QML database, data, and PLC service ports', () => {
    expect(settingsPanelSource).toContain('数据库 6011、数据 6013、PLC 6014')
    expect(settingsPanelSource).toContain('网络报警和远程服务管理分别使用数据库/数据/PLC端口')
  })

  it('uses the QML GeneralSetting Section chrome for the three core groups', () => {
    expect(settingsPanelSource).toContain('function QmlGeneralSettingSection')
    expect(settingsPanelSource).toContain('className="settings-qml-section"')
    expect(settingsPanelSource).toContain('className="settings-qml-section-title"')
    expect(settingsPanelSource).toContain('className="settings-qml-section-divider"')
    expect(settingsPanelSource).toContain('className="settings-qml-section-body"')
    expect(settingsPanelCss).toContain('.settings-qml-section')
    expect(settingsPanelCss).toContain('border: 1px solid #3A5368')
    expect(settingsPanelCss).toContain('.settings-qml-section-title')
    expect(settingsPanelCss).toContain('font-size: 16px')
    expect(settingsPanelCss).toContain('.settings-qml-section-divider')
  })

  it('exposes autoKeepTimeMax as the keep-latest auto-restore setting', () => {
    expect(settingsPanelSource).toContain('const autoKeepTimeMax = useUiSettingsStore((state) => state.autoKeepTimeMax)')
    expect(settingsPanelSource).toContain(
      'const setAutoKeepTimeMax = useUiSettingsStore((state) => state.setAutoKeepTimeMax)',
    )
    expect(settingsPanelSource).toContain('保持最新自动恢复')
    expect(settingsPanelSource).toContain('value={autoKeepTimeMax}')
    expect(settingsPanelSource).toContain('onChange={(value) => setAutoKeepTimeMax(value ?? 180)}')
  })

  it('exposes QML dataHeaderHeight as a DataShow panel height setting', () => {
    expect(settingsPanelSource).toContain('const dataHeaderHeight = useUiSettingsStore((state) => state.dataHeaderHeight)')
    expect(settingsPanelSource).toContain(
      'const setDataHeaderHeight = useUiSettingsStore((state) => state.setDataHeaderHeight)',
    )
    expect(settingsPanelSource).toContain('数据头部高度')
    expect(settingsPanelSource).toContain('value={dataHeaderHeight}')
    expect(settingsPanelSource).toContain('onChange={(value) => setDataHeaderHeight(value ?? 320)}')
  })

  it('keeps the QML InfoSetting refresh action wired to live info queries', () => {
    expect(settingsPanelSource).toContain('刷新信息')
    expect(settingsPanelSource).toContain('refetchQmlInfoSetting')
    expect(settingsPanelSource).toContain('refetchTestModeStatus()')
    expect(settingsPanelSource).toContain('refetchHardwareInfo()')
  })

  it('renders QML InfoSetting system and config groups separately', () => {
    expect(settingsPanelSource).toContain('系统信息')
    expect(settingsPanelSource).toContain('配置信息')
    expect(settingsPanelSource).toContain('qmlInfoRows.system.map')
    expect(settingsPanelSource).toContain('qmlInfoRows.config.map')
    expect(settingsPanelSource).toMatch(/系统信息[\s\S]*qmlInfoRows\.system\.map[\s\S]*配置信息[\s\S]*qmlInfoRows\.config\.map/)
  })

  it('uses the QML OtherSetting test-mode hint instead of implementation details', () => {
    expect(settingsPanelSource).toContain('启用测试模式后，系统将使用测试数据')
    expect(settingsPanelSource).not.toContain('前端只读取和提交现有字段，不修改接口形状')
  })

  it('renders the QML InfoSetting run mode as a colored badge', () => {
    expect(settingsPanelSource).toContain("row.label === '运行模式：'")
    expect(settingsPanelSource).toContain('settings-mode-badge')
    expect(settingsPanelSource).toContain("row.value === '测试模式' ? 'test' : 'prod'")
    expect(settingsPanelCss).toContain('.settings-mode-badge')
    expect(settingsPanelCss).toContain('#FF6B6B')
    expect(settingsPanelCss).toContain('#51CF66')
  })

  it('renders QML CameraSetting exposure and gain field labels beside the spin boxes', () => {
    expect(settingsPanelSource).toContain('settings-camera-field')
    expect(settingsPanelSource).toContain('settings-camera-field-label')
    expect(settingsPanelSource).toContain('<span className="settings-camera-field-label">曝光时间</span>')
    expect(settingsPanelSource).toContain('<span className="settings-camera-field-label">增益</span>')
    expect(settingsPanelCss).toContain('.settings-camera-field')
    expect(settingsPanelCss).toContain('.settings-camera-field-label')
  })

  it('polls camera adjustment status every five seconds only while settings are visible like QML CameraSetting', () => {
    expect(qmlCameraSettingSource).toContain('interval: 5000')
    expect(qmlCameraSettingSource).toContain('running: root.visible')
    expect(settingsPanelSource).toContain('refetchInterval: open ? 5000 : false')
  })

  it('keeps the settings drawer inside narrow viewports', () => {
    expect(settingsPanelSource).not.toContain('width={520}')
    expect(settingsPanelSource).toContain('rootClassName="settings-panel-root"')
    expect(settingsPanelSource).toContain('width="min(520px, 100vw)"')
    expect(settingsPanelCss).toContain('.settings-panel-root .ant-drawer-content-wrapper')
    expect(settingsPanelCss).toContain('width: 100% !important')
  })

  it('mirrors QML BaseSetting placeholder text for empty Alarm and 3D tabs', () => {
    const placeholderStart = settingsPanelSource.indexOf('function QmlBaseSettingPlaceholder')
    const placeholderEnd = settingsPanelSource.indexOf('function renderQmlInfoSettingValue', placeholderStart)
    const placeholderSource = settingsPanelSource.slice(placeholderStart, placeholderEnd)
    const placeholderCssStart = settingsPanelCss.indexOf('.settings-qml-placeholder {')
    const placeholderCssEnd = settingsPanelCss.indexOf('.settings-row code', placeholderCssStart)
    const placeholderCssSource = settingsPanelCss.slice(placeholderCssStart, placeholderCssEnd)

    expect(placeholderSource).toContain('className="settings-qml-placeholder"')
    expect(placeholderSource).toContain('<span>index:0</span>')
    expect(settingsPanelSource).toMatch(
      /key: 'alarm'[\s\S]*children: QML_PLACEHOLDER_SETTINGS_TAB_KEYS\.includes\('alarm'\) \? <QmlBaseSettingPlaceholder \/> : null/,
    )
    expect(settingsPanelSource).toMatch(
      /key: 'render'[\s\S]*children: QML_PLACEHOLDER_SETTINGS_TAB_KEYS\.includes\('render'\) \? <QmlBaseSettingPlaceholder \/> : null/,
    )
    expect(placeholderCssSource).toContain('place-items: center')
    expect(placeholderCssSource).toContain('color: red')
    expect(placeholderCssSource).toContain('font-size: 40pt')
    expect(placeholderCssSource).not.toContain('color: #ff4d4f')
    expect(placeholderCssSource).not.toContain('font-size: 40px')
  })

  it('renders QML SoftwareUpdate save destination instead of the package URL row', () => {
    expect(settingsPanelSource).toContain('getNativeDefaultDownloadDirectory')
    expect(settingsPanelSource).toContain('resolveSoftwareUpdateFolderPath')
    expect(settingsPanelSource).toContain('softwareDownloadFolder')
    expect(settingsPanelSource).toContain('<span>保存到</span>')
    expect(settingsPanelSource).not.toContain('<span>下载地址</span>')
  })

  it('uses QML OtherSetting GroupBox chrome for software, debug, and system groups', () => {
    expect(settingsPanelSource).toContain('function QmlSettingGroupBox')
    expect(settingsPanelSource).toContain('className="settings-qml-groupbox"')
    expect(settingsPanelSource).toContain('className="settings-qml-groupbox-title"')
    expect(settingsPanelSource).toContain('className="settings-qml-groupbox-body"')
    expect(settingsPanelSource).toMatch(
      /<QmlSettingGroupBox title="软件更新">[\s\S]*<span>当前版本<\/span>[\s\S]*<span>保存到<\/span>[\s\S]*<QmlSettingGroupBox title="调试选项">[\s\S]*显示瓦片边框[\s\S]*显示 AREA 视图的瓦片调试边框（绿色=已完成，黄色=加载中）[\s\S]*<QmlSettingGroupBox title="系统设置">[\s\S]*测试模式[\s\S]*启用测试模式后，系统将使用测试数据/,
    )
    expect(settingsPanelCss).toContain('.settings-qml-groupbox')
    expect(settingsPanelCss).toContain('border: 1px solid #3A5368')
    expect(settingsPanelCss).toContain('.settings-qml-groupbox-title')
    expect(settingsPanelCss).toContain('.settings-qml-groupbox-body')
  })
})
