import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import clipSettingModalSource from './index.tsx?raw'

const qmlSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/ClipSetting/ClipSettingView.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./ClipSettingModal.css', import.meta.url)), 'utf8')

describe('ClipSettingModal QML area clip parity', () => {
  it('mirrors QML ClipSettingView with an inner TitleLabel instead of an AntD modal title', () => {
    expect(qmlSource).toContain('width: 720')
    expect(qmlSource).toContain('height: 560')
    expect(clipSettingModalSource).toContain('title={null}')
    expect(clipSettingModalSource).not.toContain('title="裁剪设置"')
    expect(clipSettingModalSource).toContain('className="clip-setting-window"')
    expect(clipSettingModalSource).toContain('width={720}')
    expect(clipSettingModalSource).toContain('data-qml-clip-setting-view')
    expect(clipSettingModalSource).toContain('data-qml-clip-setting-title')
    expect(clipSettingModalSource).toMatch(
      /<div[\s\S]*data-qml-clip-setting-view[\s\S]*<h3[\s\S]*data-qml-clip-setting-title[\s\S]*裁剪设置[\s\S]*<Tabs/,
    )
    expect(styleSource).toContain('.clip-setting-title')
    expect(styleSource).toContain('font-size: 26px;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('text-align: center;')
    expect(styleSource).toContain('.clip-setting-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(560px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(560px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(560px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.clip-setting-window .ant-modal-body')
    expect(styleSource).toContain('height: calc(min(560px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('.clip-setting-modal .ant-tabs')
    expect(styleSource).toContain('flex: 1 1 auto;')
    expect(styleSource).toContain('.clip-setting-modal .ant-tabs-content-holder')
    expect(styleSource).toContain('overflow-y: auto;')
  })

  it('hydrates QML clip settings from the Rust area status when opened', () => {
    expect(clipSettingModalSource).toContain("import { useQuery } from '@tanstack/react-query'")
    expect(clipSettingModalSource).toContain("queryKey: ['area2d', 'clipSettingStatus']")
    expect(clipSettingModalSource).toContain('queryFn: area2dApi.getStatus')
    expect(clipSettingModalSource).toContain('enabled: open')
    expect(clipSettingModalSource).toMatch(/buildQmlAreaClipSettingsFromStatus\(\s*areaStatusData/)
    expect(clipSettingModalSource).toContain('setAreaClipSetting(setting.surfaceKey, setting)')
  })

  it('keeps QML numeric input precision for fixed and dynamic clip fields', () => {
    expect(clipSettingModalSource).toContain('precision={0}')
    expect(clipSettingModalSource.match(/precision=\{3\}/g)).toHaveLength(3)
  })

  it('keeps QML GroupBox titles inside each surface tab', () => {
    expect(qmlSource.match(/GroupBox\s*\{[\s\S]*?title:\s*qsTr\("S端"\)/)).not.toBeNull()
    expect(qmlSource.match(/GroupBox\s*\{[\s\S]*?title:\s*qsTr\("L端"\)/)).not.toBeNull()
    expect(clipSettingModalSource).toContain('data-qml-clip-group-box')
    expect(clipSettingModalSource).toContain('data-qml-clip-group-title')
    expect(clipSettingModalSource).toMatch(
      /<fieldset[\s\S]*data-qml-clip-group-box[\s\S]*<legend[\s\S]*data-qml-clip-group-title[\s\S]*\{setting\.label\}[\s\S]*<ClipSurfacePanel/,
    )
    expect(styleSource).toContain('.clip-setting-group')
    expect(styleSource).toContain('.clip-setting-group > legend')
  })

  it('keeps QML clip labels readable inside the light AntD window shell', () => {
    expect(styleSource).toContain('.clip-setting-row > span,')
    expect(styleSource).toContain('.clip-setting-formula')
    expect(styleSource).toContain('color: #31445a;')
    expect(styleSource).not.toContain('color: #c5d6e4;')
  })
})
