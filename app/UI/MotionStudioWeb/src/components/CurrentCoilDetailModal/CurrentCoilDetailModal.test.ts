import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

const qmlMsgPopSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/MsgPop/MsgPopView.qml', import.meta.url)),
  'utf8',
)
const qmlRowItemSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/MsgPop/RowItemView.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./CurrentCoilDetailModal.css', import.meta.url)), 'utf8')

describe('CurrentCoilDetailModal QML MsgPopView shell parity', () => {
  it('mirrors the QML MsgPopView modal width and inner title instead of an AntD title', () => {
    expect(qmlMsgPopSource).toContain('width: 700')
    expect(qmlMsgPopSource).toContain('height: 500')
    expect(qmlMsgPopSource).toContain('text: "详细信息"')
    expect(qmlMsgPopSource).toContain('font.pointSize:24')
    expect(qmlMsgPopSource).toContain('color:Material.color(Material.Blue)')

    expect(source).toContain('title={null}')
    expect(source).toContain('width={700}')
    expect(source).toContain('className="current-detail-window"')
    expect(source).not.toContain('title="详细信息"')
    expect(source).not.toContain('width={820}')
    expect(source).toContain('data-qml-msg-pop-view')
    expect(source).toContain('data-qml-msg-pop-title')
    expect(source).toMatch(
      /<div className="current-detail-modal"[\s\S]*data-qml-msg-pop-view[\s\S]*<h3[\s\S]*data-qml-msg-pop-title[\s\S]*详细信息[\s\S]*\{loading && \(/,
    )

    expect(styleSource).toContain('.current-detail-title')
    expect(styleSource).toContain('font-size: 24pt;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('text-align: center;')
    expect(styleSource).toContain('color: #2196f3;')
    expect(styleSource).toContain('.current-detail-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.current-detail-window .ant-modal-body')
    expect(styleSource).toContain('height: 100%;')
    expect(styleSource).toContain('height: calc(min(500px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('overflow-y: auto;')
  })

  it('mirrors QML RowItemView value cells inside the detail grids', () => {
    expect(qmlRowItemSource).toContain('height: 25')
    expect(qmlRowItemSource).toContain('text:key+":"')
    expect(qmlRowItemSource).toContain('horizontalAlignment: Text.AlignHCenter')
    expect(qmlRowItemSource).toContain('color: "black"')
    expect(qmlRowItemSource).toContain('border.width: 1')
    expect(qmlRowItemSource).toContain('font.pixelSize: 16')
    expect(qmlRowItemSource).toContain('font.family: "Arial"')
    expect(qmlRowItemSource).toContain('font.bold:true')

    expect(source).toContain('<span>{row.key}:</span>')
    expect(source).toContain('data-qml-msg-row-value')
    expect(styleSource).toMatch(/\.current-detail-row\s*\{[^}]*min-height:\s*25px;/s)
    expect(styleSource).toMatch(/\.current-detail-row strong\s*\{[^}]*background:\s*black;/s)
    expect(styleSource).toMatch(/\.current-detail-row strong\s*\{[^}]*border:\s*1px solid/s)
    expect(styleSource).toMatch(/\.current-detail-row strong\s*\{[^}]*font-family:\s*Arial/s)
    expect(styleSource).toMatch(/\.current-detail-row strong\s*\{[^}]*font-size:\s*16px;/s)
    expect(styleSource).toMatch(/\.current-detail-row strong\s*\{[^}]*font-weight:\s*700;/s)
    expect(styleSource).toMatch(/\.current-detail-row strong\s*\{[^}]*text-align:\s*center;/s)
  })
})
