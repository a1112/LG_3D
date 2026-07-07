import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

const qmlSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/ListValueChange/ListValueChangeView.qml', import.meta.url)),
  'utf8',
)
const qmlInputSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/ListValueChange/ViewChangeInput.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./ListValueChangeModal.css', import.meta.url)), 'utf8')

describe('ListValueChangeModal QML parity', () => {
  it('mirrors QML ListValueChangeView as an 850px popup with an inner TitleLabel', () => {
    expect(qmlSource).toContain('width:850')
    expect(qmlSource).toContain('height:500')
    expect(source).toContain('width={850}')
    expect(source).toContain('title={null}')
    expect(source).not.toContain('title="列表数值变化曲线"')
    expect(source).toContain('className="list-value-change-window"')
    expect(source).toContain('data-qml-list-value-change-view')
    expect(source).toContain('data-qml-list-value-change-title')
    expect(source).toMatch(
      /<div[\s\S]*data-qml-list-value-change-view[\s\S]*<h3[\s\S]*data-qml-list-value-change-title[\s\S]*列表数值变化曲线[\s\S]*<div className="list-value-change-controls">/,
    )
    expect(styleSource).toContain('.list-value-change-title')
    expect(styleSource).toContain('font-size: 26px;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('text-align: center;')
    expect(styleSource).toContain('color: #2196f3;')
    expect(styleSource).toContain('.list-value-change-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.list-value-change-window .ant-modal-body')
    expect(styleSource).toContain('height: 100%;')
    expect(styleSource).toContain('grid-template-rows: auto auto minmax(0, 1fr);')
    expect(styleSource).toContain('height: calc(min(500px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('.list-value-change-body')
    expect(styleSource).toContain('min-height: 0;')
    expect(styleSource).toContain('overflow: hidden;')
  })

  it('fills the formerly blank QML content area with the list value-change curve', () => {
    expect(qmlSource).toMatch(/Item\s*\{[\s\S]*id:list[\s\S]*clip:true[\s\S]*\}/)
    expect(qmlInputSource).toMatch(/Button\s*\{[\s\S]*text:"刷新"[\s\S]*onClicked:\{\s*\}/)
    expect(source).toContain('data-qml-list-value-change-chart')
    expect(source).toContain('buildListValueChangePoints')
    expect(source).toContain('ResponsiveContainer')
    expect(source).toContain('LineChart')
    expect(source).toContain('Line')
    expect(source).toContain('refetch()')
    expect(source).not.toContain('data-qml-list-value-change-placeholder')
  })
})
