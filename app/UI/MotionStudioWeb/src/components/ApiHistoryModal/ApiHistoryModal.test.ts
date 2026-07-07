import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

const qmlApiListPopSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/ApiListPop/ApiListPopView.qml', import.meta.url)),
  'utf8',
)
const qmlApiListItemSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/ApiListPop/ApiListItem.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./ApiHistoryModal.css', import.meta.url)), 'utf8')

describe('ApiHistoryModal QML row parity', () => {
  it('mirrors QML ApiListPop TitleLabel inside the popup body instead of an AntD modal title', () => {
    expect(source).toContain('title={null}')
    expect(source).not.toContain('title="API 调用记录"')
    expect(source).toContain('data-qml-api-list-pop')
    expect(source).toContain('data-qml-api-list-title')
    expect(source).toMatch(
      /<div[\s\S]*data-qml-api-list-pop[\s\S]*<h3[\s\S]*data-qml-api-list-title[\s\S]*API 调用记录[\s\S]*<div className="api-history-list">/,
    )
    expect(styleSource).toContain('.api-history-title')
    expect(styleSource).toContain('font-size: 26px;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('text-align: center;')
  })

  it('opens a request URL when the history row is clicked like QML ApiListItem', () => {
    expect(source).toContain('openApiHistoryExternalUrl')
    expect(source).toContain('onClick={() => void openApiHistoryExternalUrl(entry.url)}')
    expect(source).toContain('className="api-history-row"')
  })

  it('keeps the QML ApiListPop modal width and row field order', () => {
    expect(qmlApiListPopSource).toContain('width:500')
    expect(qmlApiListPopSource).toContain('height:600')
    expect(qmlApiListPopSource).toContain('height: 35')

    expect(source).toContain('className="api-history-modal api-history-window"')
    expect(source).toContain('width={500}')

    const timeIndex = source.indexOf('className="api-history-time"')
    const methodIndex = source.indexOf('className="api-history-method"')
    const urlIndex = source.indexOf('api-history-url')

    expect(timeIndex).toBeGreaterThan(-1)
    expect(methodIndex).toBeGreaterThan(timeIndex)
    expect(urlIndex).toBeGreaterThan(methodIndex)

    expect(styleSource).toContain('.api-history-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(600px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(600px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(600px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.api-history-window .ant-modal-body')
    expect(styleSource).toContain('.api-history-pop')
    expect(styleSource).toContain('height: calc(min(600px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('.api-history-list')
    expect(styleSource).toContain('min-height: 0;')
    expect(styleSource).toContain('overflow-y: auto;')
    expect(styleSource).toContain('min-height: 35px;')
  })

  it('renders the QML timeString field in green', () => {
    expect(styleSource).toMatch(/\.api-history-time\s*{[^}]*color:\s*green;/s)
  })

  it('renders the QML ApiListItem type field as plain label text instead of a React-only tag', () => {
    expect(qmlApiListItemSource).toMatch(/Label\s*{\s*text:\s*type\s*}/s)

    expect(source).not.toContain('Tag')
    expect(source).toContain('<span className="api-history-method">{entry.method}</span>')
    expect(styleSource).not.toContain('.api-history-method {')
  })

  it('renders the QML ApiListItem URL field as RichText-style link text', () => {
    expect(qmlApiListItemSource).toContain('textFormat: Text.RichText')
    expect(qmlApiListItemSource).toContain('text:\'<a href="\'+url+\'">\'+url+\'</a>\'')

    expect(source).toContain('data-qml-rich-url')
    expect(source).toContain('className="api-history-url api-history-url-link"')
    expect(styleSource).toContain('.api-history-url-link')
    expect(styleSource).toContain('text-decoration: underline;')
  })

  it('does not add a React-only clear toolbar absent from QML ApiListPop', () => {
    expect(source).not.toContain('clearApiRequestHistory')
    expect(source).not.toContain('api-history-toolbar')
    expect(source).not.toContain('<Button')
    expect(styleSource).not.toContain('.api-history-toolbar')
  })
})
