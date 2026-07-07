import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import source from './index.tsx?raw'

const cssSource = readFileSync(fileURLToPath(new URL('./MaintenanceMenuModal.css', import.meta.url)), 'utf8')
const qmlToolsMenuSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/ToolsMenu/ToolsMenuView.qml', import.meta.url)),
  'utf8',
)
const qmlServerMangeSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/ServerMange/ServerMangeView.qml', import.meta.url)),
  'utf8',
)

describe('MaintenanceMenuModal source wiring', () => {
  it('mirrors QML ToolsMenuView as a titleless compact menu instead of a React dashboard modal', () => {
    expect(qmlToolsMenuSource).toContain('Menu {')
    expect(qmlToolsMenuSource).toContain('title:qsTr("维护")')
    expect(qmlToolsMenuSource).toContain('title: "功能"')
    expect(qmlToolsMenuSource).toContain('text:qsTr("退出系统")')

    expect(source).toContain('className="maintenance-menu-modal tools-menu-modal"')
    expect(source).toContain('title={null}')
    expect(source).toContain('width={360}')
    expect(source).toContain('data-qml-tools-menu-view')
    expect(source).not.toContain('title="主菜单"')
    expect(source).not.toContain('className="maintenance-host-row"')
    expect(cssSource).toContain('.tools-menu-modal .ant-modal-content')
    expect(cssSource).toContain('max-height: min(560px, calc(100vh - 32px))')
    expect(cssSource).toContain('overflow: hidden')
    expect(cssSource).toContain('max-height: calc(min(560px, calc(100vh - 32px)) - 16px)')
    expect(cssSource).toContain('overflow-y: auto')
    expect(cssSource).toContain('grid-template-columns: 1fr')
  })

  it('exposes QML remote-service row actions from each service row', () => {
    expect(source).toContain('buildRemoteServiceRows({ databasPort, dataPort, plcPort, host })')
    expect(source).toContain('row.actions.map((action) => (')
    expect(source).toContain('aria-label={`${row.title}${action.label}`}')
    expect(source).toContain("action.id === 'openApiDocs' ? <ApiOutlined /> : <RedoOutlined />")
    expect(source).toContain('disabled={!action.enabled}')
  })

  it('routes QML PLC service management through the independent CoreSetting plcPort', () => {
    expect(source).toContain('const plcPort = useUiSettingsStore((state) => state.plcPort)')
    expect(source).toContain('buildRemoteServiceRows({ databasPort, dataPort, plcPort, host })')
    expect(source).toContain('[dataPort, databasPort, plcPort, host]')
  })

  it('opens remote-service docs through the QML external opener instead of a raw anchor', () => {
    const rowViewStart = source.indexOf('function RemoteServiceRowView')
    const rowViewEnd = source.indexOf('export default function MaintenanceMenuModal', rowViewStart)
    const rowViewSource = source.slice(rowViewStart, rowViewEnd)

    expect(source).toContain("import { openQmlExternalUrl } from '@/utils/coilActions'")
    expect(rowViewSource).toContain("action.id === 'openApiDocs'")
    expect(rowViewSource).toContain(
      "onClick={action.id === 'openApiDocs' ? () => void openQmlExternalUrl(action.href ?? '') : undefined}",
    )
    expect(rowViewSource).not.toContain('href={action.enabled ? action.href : undefined}')
    expect(rowViewSource).not.toContain("target={action.href ? '_blank' : undefined}")
  })

  it('mirrors QML ServerMangeView as a fixed service-management popup with an inner title', () => {
    expect(qmlServerMangeSource).toContain('width:600')
    expect(qmlServerMangeSource).toContain('height:400')
    expect(qmlServerMangeSource).toContain('text:"远程服务管理"')
    expect(qmlServerMangeSource).toContain('Layout.fillHeight:true')
    expect(qmlServerMangeSource).toContain('ListView{')

    expect(source).toContain('className="maintenance-menu-modal service-management-modal"')
    expect(source).toContain('width={600}')
    expect(source).toContain('data-qml-server-mange-view')
    expect(source).toContain('data-qml-server-mange-title')
    expect(source).toMatch(
      /<section[\s\S]*data-qml-server-mange-view[\s\S]*<h3[\s\S]*data-qml-server-mange-title[\s\S]*远程服务管理[\s\S]*maintenance-service-list/,
    )
    expect(cssSource).toContain('.service-management-modal .ant-modal-content')
    expect(cssSource).toContain('min-height: min(400px, calc(100vh - 32px))')
    expect(cssSource).toContain('height: min(400px, calc(100vh - 32px))')
    expect(cssSource).toContain('max-height: min(400px, calc(100vh - 32px))')
    expect(cssSource).toContain('overflow: hidden')
    expect(cssSource).toContain('.service-management-modal .ant-modal-body')
    expect(cssSource).toContain('height: calc(min(400px, calc(100vh - 32px)) - 48px)')
    expect(cssSource).toContain('.service-management-panel')
    expect(cssSource).toContain('height: 100%')
    expect(cssSource).toContain('grid-template-rows: auto minmax(0, 1fr)')
    expect(cssSource).toContain('.service-management-panel .maintenance-service-list')
    expect(cssSource).toContain('overflow-y: auto')
  })

  it('keeps the QML ToolsMenu service list out of the main menu until 服务管理 opens ServerMangeView', () => {
    expect(source).toContain("action.id === 'serviceManagement'")
    expect(source).toContain('setServiceManagementOpen(true)')
    expect(source).not.toMatch(
      /<section className="maintenance-service-panel">\s*<h3>[\s\S]*远程服务管理[\s\S]*serviceRows\.map/,
    )
  })

  it('closes the QML ToolsMenu shell when 服务管理 opens ServerMangeView', () => {
    const serviceManagementBranchStart = source.indexOf("if (action.id === 'serviceManagement')")
    const serviceManagementBranchEnd = source.indexOf("if (action.id === 'backupToFile')", serviceManagementBranchStart)
    const serviceManagementBranch = source.slice(serviceManagementBranchStart, serviceManagementBranchEnd)

    expect(serviceManagementBranch).toContain('setServiceManagementOpen(true)')
    expect(serviceManagementBranch).toMatch(/setServiceManagementOpen\(true\)[\s\S]*onClose\(\)[\s\S]*return/)
  })

  it('routes QML network speedtest to the existing SystemDiagnostics page without pretending restore is implemented', () => {
    expect(qmlToolsMenuSource).toMatch(/MenuItem\s*{\s*text:"网络测速"\s*}/)
    expect(qmlToolsMenuSource).toMatch(/MenuItem\s*{\s*text:"从 备份 恢复"\s*}/)
    expect(source).toContain("if (action.id === 'networkSpeedtest')")
    expect(source).toContain("navigate('/system#network-speedtest')")
    expect(source).toContain('已打开系统诊断，请在网络测速区执行测试')
    expect(source).not.toContain("action.id === 'restoreFromBackup' || action.id === 'networkSpeedtest'")
  })
})
