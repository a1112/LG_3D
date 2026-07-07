import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

const qmlHelpPopSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/HelpPop/HelpPopView.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./SystemInfoModal.css', import.meta.url)), 'utf8')

describe('SystemInfoModal QML HelpPopView shell parity', () => {
  it('mirrors the QML HelpPopView inner title and bottom close action instead of an AntD title', () => {
    expect(qmlHelpPopSource).toContain('width: 800')
    expect(qmlHelpPopSource).toContain('height: 500')
    expect(qmlHelpPopSource).toContain('text: qsTr("系统信息")')
    expect(qmlHelpPopSource).toContain('font.pixelSize: 22')
    expect(qmlHelpPopSource).toContain('color: Material.color(Material.Blue)')
    expect(qmlHelpPopSource).toMatch(/Button\s*\{[\s\S]*text: qsTr\("关闭"\)[\s\S]*onClicked: root\.close\(\)/)

    expect(source).toContain('title={null}')
    expect(source).toContain('className="system-info-modal system-info-window"')
    expect(source).toContain('width={800}')
    expect(source).not.toContain('title="系统信息"')
    expect(source).toContain('data-qml-help-pop')
    expect(source).toContain('data-qml-help-title')
    expect(source).toMatch(
      /<div className="system-info-body"[\s\S]*data-qml-help-pop[\s\S]*<h3[\s\S]*data-qml-help-title[\s\S]*系统信息[\s\S]*<div className="system-info-separator"/,
    )
    expect(source).toMatch(
      /<div className="system-info-actions"[\s\S]*<Button[\s\S]*onClick=\{onClose\}[\s\S]*关闭/,
    )

    expect(styleSource).toContain('.system-info-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.system-info-window .ant-modal-body')
    expect(styleSource).toContain('height: 100%;')
    expect(styleSource).toContain('.system-info-body')
    expect(styleSource).toContain('min-height: calc(min(500px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('height: calc(min(500px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('overflow-y: auto;')
    expect(styleSource).toContain('.system-info-title')
    expect(styleSource).toContain('font-size: 22px;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('text-align: center;')
    expect(styleSource).toContain('color: #2196f3;')
    expect(styleSource).toContain('.system-info-separator')
    expect(styleSource).toContain('.system-info-actions')
    expect(styleSource).toContain('position: sticky;')
    expect(styleSource).toContain('bottom: 0;')
    expect(styleSource).toContain('justify-content: flex-end;')
  })

  it('renders QML GroupBox-style info sections instead of AntD Descriptions tables', () => {
    expect(qmlHelpPopSource).toContain('GroupBox {')
    expect(qmlHelpPopSource).toContain('title: qsTr("图像保存路径")')
    expect(qmlHelpPopSource).toContain('title: qsTr("运行环境")')
    expect(qmlHelpPopSource).toContain('GridLayout {')
    expect(qmlHelpPopSource).toContain('columns: 2')
    expect(qmlHelpPopSource).toContain('text: qsTr("原始图像 S 端: ")')
    expect(qmlHelpPopSource).toContain('text: qsTr("Python 版本:")')

    expect(source).not.toContain('Descriptions')
    expect(source).not.toContain('<Descriptions')
    expect(source).toContain('className="system-info-group"')
    expect(source).toContain('<fieldset className="system-info-group"')
    expect(source).toContain('<legend>图像保存路径</legend>')
    expect(source).toContain('<legend>运行环境</legend>')
    expect(source).toContain('className="system-info-grid system-info-runtime-grid"')
    expect(source).toContain('<span className="system-info-label">原始图像 S 端:</span>')
    expect(source).toContain('<span className="system-info-label">Python 版本:</span>')
    expect(styleSource).toContain('.system-info-group')
    expect(styleSource).toContain('.system-info-runtime-grid')
    expect(styleSource).not.toContain('ant-descriptions')
  })
})
