import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import source from './index.tsx?raw'

const qmlDefectClassPopSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/DefectClass/DefectClassPop.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./DefectClassModal.css', import.meta.url)), 'utf8')

describe('DefectClassModal source wiring', () => {
  it('uses the QML DefectClassPop popup width', () => {
    expect(qmlDefectClassPopSource).toContain('width:500')
    expect(qmlDefectClassPopSource).toContain('height:500')

    expect(source).toContain('className="defect-class-window"')
    expect(source).toContain('width={500}')
    expect(source).not.toContain('width={560}')

    expect(styleSource).toContain('.defect-class-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.defect-class-window .ant-modal-body')
    expect(styleSource).toContain('height: 100%;')
    expect(styleSource).toContain('.defect-class-modal')
    expect(styleSource).toContain('grid-template-rows: auto minmax(0, 1fr) auto;')
    expect(styleSource).toContain('height: calc(min(500px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('min-height: 0;')
    expect(styleSource).toContain('.defect-class-list')
    expect(styleSource).toContain('overflow-y: auto;')
    expect(styleSource).toContain('.defect-class-actions')
    expect(styleSource).toContain('min-height: 32px;')
  })

  it('mirrors the QML DefectClassPop inner TitleLabel instead of an AntD modal title', () => {
    expect(source).toContain('title={null}')
    expect(source).not.toContain('title="缺陷列表"')
    expect(source).toContain('data-qml-defect-class-pop')
    expect(source).toContain('data-qml-defect-class-title')
    expect(source).toMatch(
      /<div[\s\S]*data-qml-defect-class-pop[\s\S]*<h3[\s\S]*data-qml-defect-class-title[\s\S]*缺陷列表[\s\S]*\{isFetching \?/,
    )
    expect(styleSource).toContain('.defect-class-title')
    expect(styleSource).toContain('font-size: 26px;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('text-align: center;')
    expect(styleSource).toContain('color: #2196f3;')
  })

  it('keeps the QML-width popup columns inside the modal body', () => {
    expect(styleSource).toContain('grid-template-columns: minmax(96px, 1fr) 76px 72px minmax(116px, 1.1fr);')
    expect(styleSource).toContain('gap: 8px;')
    expect(styleSource).not.toContain('grid-template-columns: minmax(110px, 1fr) 82px 82px minmax(150px, 1.2fr);')
  })

  it('does not add a React-only column header above the QML DefectClass ListView', () => {
    expect(qmlDefectClassPopSource).not.toContain('名称</span>')
    expect(qmlDefectClassPopSource).not.toContain('等级</span>')
    expect(qmlDefectClassPopSource).not.toContain('屏蔽</span>')
    expect(qmlDefectClassPopSource).not.toContain('颜色</span>')

    expect(source).not.toContain('className="defect-class-head"')
    expect(styleSource).not.toContain('.defect-class-head')
    expect(styleSource).toContain('grid-template-rows: auto minmax(0, 1fr) auto;')
    expect(styleSource).not.toContain('grid-template-rows: auto auto minmax(0, 1fr) auto;')
  })

  it('uses mobile row layout rules that prevent stacked controls from overflowing their row box', () => {
    expect(styleSource).toMatch(
      /@media \(max-width: 640px\)[\s\S]*\.defect-class-row \{[\s\S]*grid-template-columns: 1fr;[\s\S]*grid-auto-rows: max-content;[\s\S]*align-items: stretch;[\s\S]*flex: 0 0 auto;[\s\S]*min-height: 0;[\s\S]*gap: 6px;[\s\S]*\}/,
    )
  })

  it('renders the QML DefectClassPop bottom actions without a React-only close button', () => {
    const actionsStart = source.indexOf('<div className="defect-class-actions">')
    const actionsEnd = source.indexOf('</div>', actionsStart)
    const actionsSource = source.slice(actionsStart, actionsEnd)

    expect(actionsSource).toContain('保存')
    expect(actionsSource).toContain('添加')
    expect(actionsSource).not.toContain('关闭')
  })
})
