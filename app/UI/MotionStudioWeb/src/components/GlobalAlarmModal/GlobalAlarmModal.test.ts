import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

const qmlSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/GlobalAlarm/GlobalAlarmView.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./GlobalAlarmModal.css', import.meta.url)), 'utf8')

describe('GlobalAlarmModal source wiring', () => {
  it('mirrors QML GlobalAlarmView as a 600px popup without a title label', () => {
    expect(qmlSource).toContain('PopupBase')
    expect(qmlSource).toContain('width:600')
    expect(qmlSource).toContain('height:bodyV.height+25')
    expect((qmlSource.match(/height: 100/g) ?? []).length).toBe(3)
    expect(qmlSource).not.toContain('TitleLabel')
    expect(qmlSource).not.toContain('设备报警')
    expect(source).toContain('title={null}')
    expect(source).toContain('width={600}')
    expect(source).toContain('className="global-alarm-window"')
    expect(source).toContain('data-qml-global-alarm-view')
    expect(source).not.toContain('<Modal title="设备报警"')
    expect(source).not.toContain('global-alarm-title')
    expect(styleSource).toContain('.global-alarm-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(325px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(325px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(325px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.global-alarm-window .ant-modal-body')
    expect(styleSource).toContain('height: 100%;')
    expect(styleSource).toContain('padding: 12px 5px;')
    expect(styleSource).toContain('height: calc(min(325px, calc(100vh - 32px)) - 24px);')
    expect(styleSource).toContain('grid-template-rows: repeat(3, 100px);')
    expect(styleSource).toContain('gap: 0;')
    expect(styleSource).toContain('overflow-y: auto;')
    expect(styleSource).toContain('height: 100px;')
    expect(styleSource).toContain('min-height: 25px;')

    const sectionRuleStart = styleSource.indexOf('.global-alarm-section {')
    const sectionRuleEnd = styleSource.indexOf('}', sectionRuleStart)
    const sectionRule = styleSource.slice(sectionRuleStart, sectionRuleEnd)
    expect(sectionRule).toContain('overflow-y: auto;')
    expect(sectionRule).toContain('overflow-x: hidden;')
  })

  it('exposes the QML network header remote desktop action', () => {
    expect(source).toContain('networkHeaderActions')
    expect(source).toContain('runNetworkHeaderAction')
    expect(source).toContain('<DesktopOutlined />')
    expect(source).toContain('Web 预览不启动本地命令')
  })

  it('routes QML PLC service status through the independent CoreSetting plcPort', () => {
    expect(source).toContain('const plcPort = useUiSettingsStore((state) => state.plcPort)')
    expect(source).toContain('plc: plcPort')
    expect(source).toContain('[dataPort, databasPort, plcPort]')
  })

  it('opens QML network card docs through the shared external opener instead of raw links', () => {
    const networkCardStart = source.indexOf('function NetworkCard')
    const networkCardEnd = source.indexOf('export default function GlobalAlarmModal', networkCardStart)
    const networkCardSource = source.slice(networkCardStart, networkCardEnd)

    expect(source).toContain("import { openQmlExternalUrl } from '@/utils/coilActions'")
    expect(networkCardSource).toContain("onClick={action.id === 'openApiDocs' ? () => void openQmlExternalUrl(action.href ?? '') : undefined}")
    expect(networkCardSource).not.toContain('href={item.docsUrl}')
    expect(networkCardSource).not.toContain('target="_blank"')
  })

  it('matches QML value-row separators for network and hardware cards but not camera cards', () => {
    const alarmCardStart = source.indexOf('function AlarmCard')
    const alarmCardEnd = source.indexOf('function CameraCard', alarmCardStart)
    const alarmCardSource = source.slice(alarmCardStart, alarmCardEnd)
    const cameraCardStart = source.indexOf('function CameraCard')
    const cameraCardEnd = source.indexOf('function NetworkCard', cameraCardStart)
    const cameraCardSource = source.slice(cameraCardStart, cameraCardEnd)
    const networkCardStart = source.indexOf('function NetworkCard')
    const networkCardEnd = source.indexOf('export default function GlobalAlarmModal', networkCardStart)
    const networkCardSource = source.slice(networkCardStart, networkCardEnd)

    expect(alarmCardSource).toContain('global-alarm-hardware-card')
    expect(alarmCardSource).toContain('<span className="global-alarm-separator">:</span>')
    expect(networkCardSource).toContain('<span className="global-alarm-separator">:</span>')
    expect(cameraCardSource).not.toContain('global-alarm-separator')
  })

  it('opens QML camera data through the shared external opener instead of raw links', () => {
    const cameraCardStart = source.indexOf('function CameraCard')
    const cameraCardEnd = source.indexOf('function NetworkCard', cameraCardStart)
    const cameraCardSource = source.slice(cameraCardStart, cameraCardEnd)

    expect(source).toContain("import { openQmlExternalUrl } from '@/utils/coilActions'")
    expect(cameraCardSource).toContain("void openQmlExternalUrl(cameraDataUrl ?? '')")
    expect(cameraCardSource).not.toContain('href={cameraDataUrl}')
    expect(cameraCardSource).not.toContain('target="_blank"')
  })

  it('renders the QML camera-card menu actions and wires restart through the Rust camera reconnect API', () => {
    const cameraCardStart = source.indexOf('function CameraCard')
    const cameraCardEnd = source.indexOf('function NetworkCard', cameraCardStart)
    const cameraCardSource = source.slice(cameraCardStart, cameraCardEnd)

    expect(cameraCardSource).toContain('item.actions.map((action) => (')
    expect(cameraCardSource).toContain("action.id === 'openCurrentCoilCameraData'")
    expect(cameraCardSource).toContain("action.id === 'openRawDataSavePath'")
    expect(cameraCardSource).toContain("action.id === 'restartCamera'")
    expect(cameraCardSource).toContain("if (actionId === 'openRawDataSavePath') return !enabled || !coilId || openingRawCameraKey === item.key")
    expect(cameraCardSource).toContain("if (actionId === 'restartCamera') return !enabled || restartingCameraKey === item.key")
    expect(cameraCardSource).toContain("onRestartCamera(item.key)")
    expect(source).toContain('await systemApi.reconnectCameraAdjustment(cameraKey)')
    expect(source).toContain('cameraQuery.refetch()')
    expect(cameraCardSource).toContain('`${item.title}${action.label}`')
  })

  it('opens the QML raw camera data save path through cameraData metadata and native shell open', () => {
    const cameraCardStart = source.indexOf('function CameraCard')
    const cameraCardEnd = source.indexOf('function NetworkCard', cameraCardStart)
    const cameraCardSource = source.slice(cameraCardStart, cameraCardEnd)

    expect(source).toContain("import { openNativePath } from '@/utils/nativeDialogs'")
    expect(source).toContain('const data = await systemApi.getCameraData(coilId, cameraKey)')
    expect(source).toContain('const folder = readCameraDataFolder(data)')
    expect(source).toContain('const nativeResult = await openNativePath(folder).catch')
    expect(source).toContain('await openQmlExternalUrl(buildFolderFallbackUrl(folder))')
    expect(source).toContain("message.warning('请先选择当前卷材')")
    expect(cameraCardSource).toContain('onOpenRawDataPath(item.key)')
    expect(cameraCardSource).toContain("action.id === 'openRawDataSavePath' && openingRawCameraKey === item.key")
  })

  it('renders the QML network-card menu actions including disabled restart service', () => {
    const networkCardStart = source.indexOf('function NetworkCard')
    const networkCardEnd = source.indexOf('export default function GlobalAlarmModal', networkCardStart)
    const networkCardSource = source.slice(networkCardStart, networkCardEnd)

    expect(networkCardSource).toContain('item.actions.map((action) => (')
    expect(networkCardSource).toContain("action.id === 'openApiDocs'")
    expect(networkCardSource).toContain("action.id === 'restartService'")
    expect(networkCardSource).toContain('disabled={!action.enabled}')
    expect(networkCardSource).toContain('`${item.title}${action.label}`')
  })

  it('bounds the loading spinner so the QML popup body never gains horizontal overflow', () => {
    const loadingRuleStart = styleSource.indexOf('.global-alarm-loading')
    const loadingRuleEnd = styleSource.indexOf('}', loadingRuleStart)
    const loadingRule = styleSource.slice(loadingRuleStart, loadingRuleEnd)

    expect(loadingRuleStart).toBeGreaterThanOrEqual(0)
    expect(loadingRule).toContain('width: 16px;')
    expect(loadingRule).toContain('height: 16px;')
    expect(loadingRule).toContain('overflow: hidden;')
  })
})
