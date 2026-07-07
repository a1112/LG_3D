import { fileURLToPath } from 'node:url'
import { beforeAll, describe, expect, it } from 'vitest'

const componentPath = fileURLToPath(new URL('./index.tsx', import.meta.url))
const cssPath = fileURLToPath(new URL('./ConnectSettingsModal.css', import.meta.url))
let qmlConnectDialogSource = ''
let componentExists = false
let cssExists = false
let componentSource = ''
let cssSource = ''

beforeAll(async () => {
  // @ts-expect-error Vitest runs this source check in Node; app builds intentionally omit Node typings.
  const { existsSync, readFileSync } = (await import('node:fs')) as {
    existsSync: (path: string) => boolean
    readFileSync: (path: string, encoding: 'utf8') => string
  }

  qmlConnectDialogSource = readFileSync(
    fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/Connect/ConnectDialog.qml', import.meta.url)),
    'utf8',
  )
  componentExists = existsSync(componentPath)
  cssExists = existsSync(cssPath)
  componentSource = componentExists ? readFileSync(componentPath, 'utf8') : ''
  cssSource = cssExists ? readFileSync(cssPath, 'utf8') : ''
})

describe('ConnectSettingsModal QML ConnectDialog parity', () => {
  it('mirrors the QML ConnectDialog fixed shell, title, and standard buttons', () => {
    expect(qmlConnectDialogSource).toContain('width: 500')
    expect(qmlConnectDialogSource).toContain('height: 200')
    expect(qmlConnectDialogSource).toContain('text: "连接设置"')
    expect(qmlConnectDialogSource).toContain('standardButtons: Dialog.Apply|Dialog.Ok')

    expect(componentExists).toBe(true)
    expect(cssExists).toBe(true)
    expect(componentSource).toContain('className="connect-settings-modal"')
    expect(componentSource).toContain('width={500}')
    expect(componentSource).toContain('title={null}')
    expect(componentSource).toContain('data-qml-connect-dialog')
    expect(componentSource).toContain('data-qml-connect-title')
    expect(componentSource).toContain('连接设置')
    expect(componentSource).toContain('data-qml-connect-apply')
    expect(componentSource).toContain('data-qml-connect-ok')
    expect(cssSource).toContain('.connect-settings-modal .ant-modal-content')
    expect(cssSource).toMatch(/\.connect-settings-modal \.ant-modal-content\s*\{[^}]*padding:\s*0/)
    expect(cssSource).toContain('height: min(200px, calc(100vh - 32px))')
  })

  it('mirrors QML TextFieldItem and ShowItemDelegate behavior for host shortcuts', () => {
    expect(qmlConnectDialogSource).toContain('title: "Ip 地址"')
    expect(qmlConnectDialogSource).toContain('title: "端口号"')
    expect(qmlConnectDialogSource).toContain('text:"127.0.0.1"')
    expect(qmlConnectDialogSource).toContain('text:"192.168.99.100"')

    expect(componentSource).toContain('data-qml-connect-ip-input')
    expect(componentSource).toContain('data-qml-connect-port-input')
    expect(componentSource).toContain('Ip 地址')
    expect(componentSource).toContain('端口号')
    expect(componentSource).toContain('CONNECT_HOST_SHORTCUTS')
    expect(componentSource).toContain('127.0.0.1')
    expect(componentSource).toContain('192.168.99.100')
    expect(componentSource).toContain('setIpDraft(host)')
    expect(componentSource).toContain('onChange={(value) => setPortDraft(value ?? 5011)}')
  })
})
