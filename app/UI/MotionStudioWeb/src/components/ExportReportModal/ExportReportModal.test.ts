import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import source from './index.tsx?raw'

const qmlSource = readFileSync(
  fileURLToPath(new URL('../../../../MotionStudio/qml/PopupView/Export/ExportView.qml', import.meta.url)),
  'utf8',
)
const styleSource = readFileSync(fileURLToPath(new URL('./ExportReportModal.css', import.meta.url)), 'utf8')

describe('ExportReportModal QML desktop save parity', () => {
  it('mirrors QML ExportView with a body BaseLabel instead of only an AntD modal title', () => {
    expect(qmlSource).toContain('width: 650')
    expect(qmlSource).toContain('height: 500')
    expect(qmlSource).toContain('title: qsTr("报表导出")')
    expect(qmlSource).toContain('text:"报表导出"')
    expect(qmlSource).toContain('color:Material.color(Material.Green)')
    expect(qmlSource).toContain('font.pointSize: 24')
    expect(qmlSource).toContain('font.bold:true')
    expect(source).toContain('title={null}')
    expect(source).not.toContain('<Modal title="报表导出"')
    expect(source).toContain('className="export-report-window"')
    expect(source).toContain('width={650}')
    expect(source).toContain('data-qml-export-view')
    expect(source).toContain('data-qml-export-title')
    expect(source).toMatch(
      /<div[\s\S]*data-qml-export-view[\s\S]*<h3[\s\S]*data-qml-export-title[\s\S]*报表导出[\s\S]*<label/,
    )
    expect(styleSource).toContain('.export-report-title')
    expect(styleSource).toContain('color: #52c41a;')
    expect(styleSource).toContain('font-size: 24pt;')
    expect(styleSource).toContain('font-weight: 700;')
    expect(styleSource).toContain('text-align: center;')
    expect(styleSource).toContain('.export-report-window .ant-modal-content')
    expect(styleSource).toContain('min-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('max-height: min(500px, calc(100vh - 32px));')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.export-report-window .ant-modal-body')
    expect(styleSource).toContain('height: calc(min(500px, calc(100vh - 32px)) - 48px);')
    expect(styleSource).toContain('overflow: hidden;')
    expect(styleSource).toContain('.export-report-modal')
    expect(styleSource).toContain('height: 100%;')
    expect(styleSource).toContain('min-height: 0;')
    expect(styleSource).toContain('display: flex;')
    expect(styleSource).toContain('flex-direction: column;')
    expect(styleSource).toContain('.export-report-actions')
    expect(styleSource).toContain('margin-top: auto;')
  })

  it('resolves the QML ExportView desktop output directory for native workbook saves', () => {
    expect(source).toContain('getNativeDefaultDesktopDirectory')
    expect(source).toContain('buildQmlExportDefaultFileName')
    expect(source).toContain('defaultDirectory: exportDefaultDirectory || undefined')
  })

  it('keeps QML DownloadingRow-style open actions after a report is saved', () => {
    expect(source).toContain('openSavedExportPath')
    expect(source).toContain('setLastExportPath(result.path)')
    expect(source).toContain("openSavedExportPath(lastExportPath, 'file')")
    expect(source).toContain("openSavedExportPath(lastExportPath, 'folder')")
    expect(source).toContain('打开位置...')
  })

  it('auto-opens the saved workbook after native save like QML onDownloadFinished', () => {
    const saveResultSource = source.slice(
      source.indexOf('const handleSaveResult'),
      source.indexOf('const openQuickExport'),
    )

    expect(saveResultSource).toContain('result.status === \'saved\'')
    expect(saveResultSource).toContain("void openSavedExportPath(result.path, 'file')")
  })

  it('keeps QML ErrorRow-style persistent export errors instead of toast-only failures', () => {
    expect(source).toContain('const [exportError, setExportError]')
    expect(source).toContain('setExportError(error instanceof Error ? error.message :')
    expect(source).toContain('className="export-report-error"')
    expect(source).toContain('数据导出错误:')
    expect(source).toContain('{exportError}')
  })

  it('keeps QML ErrorRow copy action for persistent export errors', () => {
    expect(source).toContain('copyTextToClipboard')
    expect(source).toContain('const copyExportError')
    expect(source).toContain('await copyTextToClipboard(exportError)')
    expect(source).toContain('disabled={!exportError}')
    expect(source).toContain('复制')
  })

  it('resets QML ExportStatus when the output file changes', () => {
    const updateOutputNameSource = source.slice(
      source.indexOf('const updateOutputName'),
      source.indexOf('const saveWorkbook'),
    )

    expect(updateOutputNameSource).toContain('setOutputName(value)')
    expect(updateOutputNameSource).toContain("setLastExportPath('')")
    expect(updateOutputNameSource).toContain("setExportError('')")
    expect(updateOutputNameSource).toContain('setProgress(0)')
    expect(source).toContain('onChange={(event) => updateOutputName(event.target.value)}')
  })

  it('keeps QML SimpleFileInput save-path selection before report export', () => {
    const saveWorkbookSource = source.slice(
      source.indexOf('const saveWorkbook'),
      source.indexOf('const copyExportError'),
    )

    expect(source).toContain('selectNativeSavePath')
    expect(source).toContain('writeNativeFile')
    expect(source).toContain('const selectOutputFile')
    expect(source).toContain("updateOutputName(selected.path)")
    expect(source).toContain('选择...')
    expect(saveWorkbookSource).toContain('writeNativeFile')
    expect(saveWorkbookSource).toContain("directPathResult.status === 'saved'")
    expect(saveWorkbookSource).toContain('saveNativeFile(defaultName, contents')
  })

  it('keeps QML ExportView date labels including trailing colons', () => {
    expect(source).toContain('起始导出日期:')
    expect(source).toContain('结束导出日期:')
    expect(source).toContain('快速导出:')
  })

  it('keeps the QML ExportView bottom action order and plain close button', () => {
    const actionsSource = source.slice(
      source.indexOf('<div className="export-report-actions">'),
      source.indexOf('</div>', source.indexOf('<div className="export-report-actions">')),
    )

    expect(actionsSource.indexOf('runConfigExport')).toBeGreaterThan(-1)
    expect(actionsSource.indexOf('onClose')).toBeGreaterThan(-1)
    expect(actionsSource.indexOf('runConfigExport')).toBeLessThan(actionsSource.indexOf('onClose'))
    expect(actionsSource).not.toContain('DownloadOutlined')
  })
})
