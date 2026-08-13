import { beforeAll, describe, expect, it } from 'vitest'

import defectShowSource from './index.tsx?raw'

let defectShowCss = ''
let defectExportDialogQml = ''
let manualDefectEditDialogQml = ''

beforeAll(async () => {
  const { readFileSync } = (await import('node:fs')) as {
    readFileSync: (path: URL, encoding: 'utf8') => string
  }

  defectShowCss = readFileSync(new URL('./DefectShow.css', import.meta.url), 'utf8')
  defectExportDialogQml = readFileSync(
    new URL('../../../../MotionStudio/qml/Dialogs/DefectExportDialog.qml', import.meta.url),
    'utf8',
  )
  manualDefectEditDialogQml = readFileSync(
    new URL('../../../../MotionStudio/qml/Dialogs/ManualDefectEditDialog.qml', import.meta.url),
    'utf8',
  )
})

describe('DefectShow QML class filter controls', () => {
  it('exposes the QML reset action beside all/clear class filters', () => {
    expect(defectShowSource).toContain('resetDefectClasses')
    expect(defectShowSource).toContain('ReloadOutlined')
    expect(defectShowSource).toContain('重置')
  })

  it('persists the QML include-background filter through the UI settings store', () => {
    expect(defectShowSource).toContain('state.showAlarmDefectClasses')
    expect(defectShowSource).toContain('state.setShowAlarmDefectClasses')
    expect(defectShowSource).not.toContain('const [showAlarmDefectClasses, setShowAlarmDefectClasses] = useState(false)')
  })

  it('exposes the QML DefectShow toolbar refresh action', () => {
    const toolbarStart = defectShowSource.indexOf('<div className="defect-toolbar">')
    const toolbarEnd = defectShowSource.indexOf('<section className="defect-class-summary-panel">', toolbarStart)
    const toolbarSource = defectShowSource.slice(toolbarStart, toolbarEnd)

    expect(toolbarSource).toContain('className="defect-toolbar-refresh"')
    expect(toolbarSource).toContain('onClick={() => void refetchDefects()}')
    expect(toolbarSource).toContain('刷新')
  })

  it('mirrors the QML HeadToolBox title and all-defects export action', () => {
    const toolbarStart = defectShowSource.indexOf('<div className="defect-toolbar">')
    const toolbarEnd = defectShowSource.indexOf('<section className="defect-qml-info-panel"', toolbarStart)
    const toolbarSource = defectShowSource.slice(toolbarStart, toolbarEnd)

    expect(defectExportDialogQml).toContain('title: "导出标记缺陷"')
    expect(defectExportDialogQml).toContain('width: 500')
    expect(toolbarSource).toContain('<span>缺陷数据分析</span>')
    expect(toolbarSource).toContain('icon={<ExportOutlined />}')
    expect(toolbarSource).toContain('onClick={() => setManualDefectExportOpen(true)}')
    expect(toolbarSource).toMatch(/>\s*导出\s*<\/Button>/)
    expect(defectShowSource).toContain('title="导出标记缺陷"')
    expect(defectShowSource).toContain('width={500}')
    expect(defectShowSource).not.toContain('title="导出"')
    expect(defectShowSource).toContain("useState<ManualDefectExportScope>('all')")
    expect(defectShowSource).toContain('defectApi.exportManualDefects(')
    expect(defectShowSource).toContain('buildManualDefectExportPayload(')
  })

  it('mirrors the QML DefectExportDialog 500x400 shell with an internal scrolling body', () => {
    expect(defectExportDialogQml).toContain('width: 500')
    expect(defectExportDialogQml).toContain('height: 400')
    expect(defectExportDialogQml).toContain('ColumnLayout {')
    expect(defectExportDialogQml).toContain('anchors.fill: parent')

    expect(defectShowSource).toContain('className="manual-defect-export-modal"')
    expect(defectShowSource).toContain('width={500}')
    expect(defectShowCss).toContain('.manual-defect-export-modal .ant-modal-content')
    expect(defectShowCss).toContain('height: min(400px, calc(100vh - 32px))')
    expect(defectShowCss).toContain('max-height: min(400px, calc(100vh - 32px))')
    expect(defectShowCss).toContain('overflow: hidden')
    expect(defectShowCss).toContain('.manual-defect-export-modal .ant-modal-body')
    expect(defectShowCss).toContain('overflow-y: auto')
    expect(defectShowCss).toContain('overflow-x: hidden')
    expect(defectShowCss).toContain('.manual-defect-export-form')
    expect(defectShowCss).toContain('min-height: 0')
  })

  it('mirrors the QML HeadToolBox left TabBar entry and centered title layout', () => {
    const toolbarStart = defectShowSource.indexOf('<div className="defect-toolbar">')
    const toolbarEnd = defectShowSource.indexOf('<section className="defect-qml-info-panel"', toolbarStart)
    const toolbarSource = defectShowSource.slice(toolbarStart, toolbarEnd)

    expect(toolbarSource).toContain('data-qml-defect-head-toolbox')
    expect(toolbarSource).toContain('className="defect-toolbar-tabbar"')
    expect(toolbarSource).toContain('data-qml-defect-global-view-index={0}')
    expect(toolbarSource).toContain('缺陷列表')
    expect(toolbarSource).toContain('defect-toolbar-title-center')
    expect(toolbarSource).toContain('<span>缺陷数据分析</span>')
    expect(toolbarSource).toContain('className="defect-toolbar-actions"')
    expect(defectShowCss).toContain('.defect-toolbar-tabbar')
    expect(defectShowCss).toContain('.defect-toolbar-title-center')
    expect(defectShowCss).toContain('.defect-toolbar-actions')
  })

  it('keeps the QML HeadToolBox root height at 45px', () => {
    const toolbarCssStart = defectShowCss.indexOf('.defect-toolbar {')
    const toolbarCssEnd = defectShowCss.indexOf('.defect-content {', toolbarCssStart)
    const toolbarCssSource = defectShowCss.slice(toolbarCssStart, toolbarCssEnd)

    expect(toolbarCssSource).toContain('min-height: 45px')
    expect(toolbarCssSource).not.toContain('min-height: 42px')
  })

  it('keeps the QML HeadToolBox 45px height in the mobile toolbar override', () => {
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-toolbar\s*\{[\s\S]*min-height:\s*45px/,
    )
    expect(defectShowCss).not.toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-toolbar\s*\{[\s\S]*min-height:\s*42px/,
    )
  })

  it('keeps the QML HeadToolBox title text horizontal in the desktop toolbar', () => {
    const titleCssStart = defectShowCss.indexOf('.defect-toolbar-title-center {')
    const titleCssEnd = defectShowCss.indexOf('.defect-toolbar-actions', titleCssStart)
    const titleCssSource = defectShowCss.slice(titleCssStart, titleCssEnd)

    expect(titleCssSource).toContain('white-space: nowrap')
  })

  it('keeps QML HeadToolBox export tied to all loaded defects, not filtered grid rows', () => {
    const exportStart = defectShowSource.indexOf('const exportDefects = useMemo')
    const exportEnd = defectShowSource.indexOf('const manualDefectExportCounts', exportStart)
    const exportSource = defectShowSource.slice(exportStart, exportEnd)
    const toolbarStart = defectShowSource.indexOf('<div className="defect-toolbar">')
    const toolbarEnd = defectShowSource.indexOf('<section className="defect-qml-info-panel"', toolbarStart)
    const toolbarSource = defectShowSource.slice(toolbarStart, toolbarEnd)

    expect(exportSource).toContain('defects.map((defect) => ({')
    expect(exportSource).not.toContain('filteredDefects.map((defect) => ({')
    expect(toolbarSource).toContain('disabled={exportDefects.length === 0}')
    expect(toolbarSource).not.toContain('disabled={filteredDefects.length === 0}')
  })

  it('defaults to QML ControlCore current-list range loading on the defect page', () => {
    expect(defectShowSource).toContain("useState<DefectDataMode>('range')")
    expect(defectShowSource).not.toContain("useState<DefectDataMode>('auto')")
    expect(defectShowSource).toContain('queryFn: () => fetchDefectsByMode(defectDataMode, defectApi')
    expect(defectShowSource).toContain("defectDataMode === 'range' ? defectListRange.startId > 0")
  })

  it('opens a QML DefectDataViewMenu-style context menu from each defect row', () => {
    const listContainerStart = defectShowSource.indexOf('<div className="defect-list-container">')
    const listStart = defectShowSource.indexOf('filteredDefects.map((defect) => (', listContainerStart)
    const listEnd = defectShowSource.indexOf('</section>', listStart)
    const listSource = defectShowSource.slice(listStart, listEnd)

    expect(defectShowSource).toContain('Dropdown')
    expect(defectShowSource).toContain('const buildQmlDefectDataViewMenu = (defect: DefectData)')
    expect(listSource).toContain("trigger={['contextMenu']}")
    expect(listSource).toContain("menu={{ items: buildQmlDefectDataViewMenu(defect), triggerSubMenuAction: 'click' }}")
    expect(listSource).toContain('onContextMenu={() => {')
    expect(listSource).toContain('setSelectedDefectId(defect.id)')
  })

  it('keeps QML defect-row menu labels wired to the defect row actions', () => {
    const menuStart = defectShowSource.indexOf('const buildQmlDefectDataViewMenu = (defect: DefectData)')
    const menuEnd = defectShowSource.indexOf('const canSwitchToImage', menuStart)
    const menuSource = defectShowSource.slice(menuStart, menuEnd)

    expect(menuSource).toContain("label: '纠正'")
    expect(menuSource).toContain("label: ''")
    expect(menuSource).not.toContain("label: '暂无纠正项'")
    expect(menuSource).toContain("label: '切换到图像'")
    expect(menuSource).toContain("label: '打开图像位置'")
    expect(menuSource).toContain('switchToDefectImage(defect)')
    expect(menuSource).toContain('openDefectImageFolder(defect)')
    expect(menuSource).toContain('setSelectedDefectId(defect.id)')
  })

  it('keeps QML DefectDataViewMenu row actions text-only without icons', () => {
    const menuStart = defectShowSource.indexOf('const buildQmlDefectDataViewMenu = (defect: DefectData)')
    const menuEnd = defectShowSource.indexOf('const canSwitchToImage', menuStart)
    const menuSource = defectShowSource.slice(menuStart, menuEnd)

    expect(menuSource).toContain("label: '切换到图像'")
    expect(menuSource).toContain("label: '打开图像位置'")
    expect(menuSource).not.toContain('icon: <SelectOutlined />')
    expect(menuSource).not.toContain('icon: <FolderOpenOutlined />')
  })

  it('renders the QML defect-list ToolBox range, NUM count, and fullscreen affordance', () => {
    const panelStart = defectShowSource.indexOf('<section className="defect-list-panel">')
    const panelEnd = defectShowSource.indexOf('<div className="defect-list-container">', panelStart)
    const panelSource = defectShowSource.slice(panelStart, panelEnd)
    const titleCssStart = defectShowCss.indexOf('.defect-list-title {')
    const titleCssEnd = defectShowCss.indexOf('.defect-list-heading,', titleCssStart)
    const titleCssSource = defectShowCss.slice(titleCssStart, titleCssEnd)
    const fullscreenCssStart = defectShowCss.indexOf('.defect-list-fullscreen.ant-btn {')
    const fullscreenCssEnd = defectShowCss.indexOf('.defect-list-fullscreen.ant-btn:hover', fullscreenCssStart)
    const fullscreenCssSource = defectShowCss.slice(fullscreenCssStart, fullscreenCssEnd)

    expect(defectShowSource).toContain('const defectListToolBoxRange = useMemo')
    expect(defectShowSource).toContain("defectDataMode === 'range' ? defectListRange")
    expect(defectShowSource).toContain('selectedDefect?.coilId || currentCoil?.id || 0')
    expect(panelSource).toContain('className="panel-title defect-list-title"')
    expect(panelSource).toContain('className="defect-list-qml-toolbar"')
    expect(panelSource).toContain('{defectListToolBoxRange.startId}')
    expect(panelSource).toContain('{defectListToolBoxRange.endId}')
    expect(panelSource).toContain('NUM: {filteredDefects.length}')
    expect(panelSource).toContain('aria-label="缺陷列表全屏"')
    expect(panelSource).toContain('<FullscreenOutlined />')
    expect(titleCssSource).toContain('height: 25px')
    expect(titleCssSource).toContain('min-height: 25px')
    expect(titleCssSource).toContain('flex-basis: 25px')
    expect(fullscreenCssSource).toContain('width: 25px')
    expect(fullscreenCssSource).toContain('height: 25px')
    expect(fullscreenCssSource).toContain('min-width: 25px')
  })

  it('lays out defect items like the QML DefectDataView 200px GridView cells', () => {
    const listContainerStart = defectShowCss.indexOf('.defect-list-container {')
    const listContainerEnd = defectShowCss.indexOf('.loading-container', listContainerStart)
    const listContainerSource = defectShowCss.slice(listContainerStart, listContainerEnd)

    expect(defectShowCss).toContain('grid-template-columns: repeat(auto-fill, 200px)')
    expect(defectShowCss).toContain('grid-auto-rows: 200px')
    expect(listContainerSource).toContain('gap: 0')
    expect(listContainerSource).toContain('padding: 0')
    expect(defectShowCss).toMatch(/\.defect-item\s*\{[\s\S]*width:\s*200px[\s\S]*height:\s*200px/)
    expect(defectShowCss).toMatch(
      /\.defect-item-tooltip-trigger\s*\{[\s\S]*width:\s*90%[\s\S]*height:\s*90%/,
    )
    expect(defectShowCss).toMatch(/\.defect-item-thumbnail\s*\{[\s\S]*width:\s*100%[\s\S]*height:\s*100%/)
    expect(defectShowCss).toMatch(
      /\.defect-item-main,\s*\.defect-confidence\s*\{[\s\S]*display:\s*none/,
    )
  })

  it('renders QML DefectItemShow-style defect thumbnails from the crop endpoint', () => {
    const listContainerStart = defectShowSource.indexOf('<div className="defect-list-container">')
    const listStart = defectShowSource.indexOf('filteredDefects.map((defect) => (', listContainerStart)
    const listEnd = defectShowSource.indexOf('</section>', listStart)
    const listSource = defectShowSource.slice(listStart, listEnd)

    expect(defectShowSource).toContain('const getDefectThumbnailUrl = (defect: DefectData)')
    expect(defectShowSource).toContain('imageApi.getDefectImage(')
    expect(defectShowSource).toContain("defect.surface")
    expect(defectShowSource).toContain("defect.coilId")
    expect(defectShowSource).toContain("'AREA'")
    expect(listSource).toContain('className="defect-item-thumbnail"')
    expect(listSource).toContain('src={getDefectThumbnailUrl(defect)}')
    expect(listSource).toContain('alt={`${defect.defectType} ${defect.coilId}`}')
    expect(listSource).toContain('loading="lazy"')
    expect(listSource).toContain('decoding="async"')
  })

  it('overlays the QML DefectItemShow name and coil id labels on each thumbnail', () => {
    const listContainerStart = defectShowSource.indexOf('<div className="defect-list-container">')
    const listStart = defectShowSource.indexOf('filteredDefects.map((defect) => (', listContainerStart)
    const listEnd = defectShowSource.indexOf('</section>', listStart)
    const listSource = defectShowSource.slice(listStart, listEnd)

    expect(listSource).toContain('className="defect-item-thumbnail-labels"')
    expect(listSource).toContain('className="defect-item-thumbnail-name"')
    expect(listSource).toContain('{defect.defectType}')
    expect(listSource).toContain('className="defect-item-thumbnail-id"')
    expect(listSource).toContain('ID:{defect.coilId}')
    expect(defectShowCss).toContain('.defect-item-thumbnail-labels')
    expect(defectShowCss).toContain('.defect-item-thumbnail-name')
    expect(defectShowCss).toContain('.defect-item-thumbnail-id')
    expect(defectShowCss).toContain('background: rgba(0, 0, 0, 0.53)')
  })

  it('colors QML DefectItemShow defect-name labels from the defect dictionary', () => {
    const listContainerStart = defectShowSource.indexOf('<div className="defect-list-container">')
    const listStart = defectShowSource.indexOf('filteredDefects.map((defect) => (', listContainerStart)
    const listEnd = defectShowSource.indexOf('</section>', listStart)
    const listSource = defectShowSource.slice(listStart, listEnd)
    const thumbnailNameStart = defectShowCss.indexOf('.defect-item-thumbnail-name {')
    const thumbnailNameEnd = defectShowCss.indexOf('.defect-item-thumbnail-id', thumbnailNameStart)
    const thumbnailNameSource = defectShowCss.slice(thumbnailNameStart, thumbnailNameEnd)
    const tooltipNameStart = defectShowCss.indexOf('.defect-item-tooltip-name {')
    const tooltipNameEnd = defectShowCss.indexOf('.defect-item-tooltip-content span', tooltipNameStart)
    const tooltipNameSource = defectShowCss.slice(tooltipNameStart, tooltipNameEnd)

    expect(defectShowSource).toContain('type CSSProperties')
    expect(defectShowSource).toContain('const getDefectItemColor = (defect: DefectData) =>')
    expect(defectShowSource).toContain("raw.configDefectName")
    expect(defectShowSource).toContain("raw.ConfigDefectName")
    expect(defectShowSource).toContain("raw.defectName")
    expect(defectShowSource).toContain("raw.DefectName")
    expect(defectShowSource).toContain("filterOptions.find((option) => option.name === colorName)?.color ?? '#FFF'")
    expect(listSource).toContain("style={{ '--defect-item-color': getDefectItemColor(defect) } as CSSProperties}")
    expect(thumbnailNameSource).toContain('color: var(--defect-item-color, #fff)')
    expect(tooltipNameSource).toContain('color: var(--defect-item-color, #fff)')
    expect(thumbnailNameSource).not.toContain('color: #ff4d4f')
    expect(tooltipNameSource).not.toContain('color: #ff4d4f')
  })

  it('adds QML DefectItemShow hover details to each defect row', () => {
    const listContainerStart = defectShowSource.indexOf('<div className="defect-list-container">')
    const listStart = defectShowSource.indexOf('filteredDefects.map((defect) => (', listContainerStart)
    const listEnd = defectShowSource.indexOf('</section>', listStart)
    const listSource = defectShowSource.slice(listStart, listEnd)

    expect(defectShowSource).toContain('const getDefectLevelText = (defect: DefectData)')
    expect(defectShowSource).toContain('const formatDefectItemTitle = (defect: DefectData)')
    expect(defectShowSource).toContain('`Coil ID: ${defect.coilId}`')
    expect(defectShowSource).toContain('`Surface: ${defect.surface}`')
    expect(defectShowSource).toContain('`Level: ${getDefectLevelText(defect)}`')
    expect(defectShowSource).toContain('`Position: (${defect.position.x}, ${defect.position.y})`')
    expect(defectShowSource).toContain('`Size: ${defect.size.width} x ${defect.size.height}`')
    expect(listSource).toContain('title={formatDefectItemTitle(defect)}')
  })

  it('renders a visible QML DefectItemShow-style hover detail card for defect rows', () => {
    const listContainerStart = defectShowSource.indexOf('<div className="defect-list-container">')
    const listStart = defectShowSource.indexOf('filteredDefects.map((defect) => (', listContainerStart)
    const listEnd = defectShowSource.indexOf('</section>', listStart)
    const listSource = defectShowSource.slice(listStart, listEnd)

    expect(defectShowSource).toContain('const renderDefectItemTooltip = (defect: DefectData)')
    expect(defectShowSource).toContain('const [tooltipDefectId, setTooltipDefectId] = useState<number | null>(null)')
    expect(listSource).toContain("tooltipDefectId === defect.id ? 'tooltip-open' : ''")
    expect(listSource).toContain('setTooltipDefectId(defect.id)')
    expect(listSource).toContain('onFocus={() => setTooltipDefectId(defect.id)}')
    expect(listSource).toContain('onClick={() => {')
    expect(listSource).toContain('onContextMenu={() => {')
    expect(listSource).toContain('setTooltipDefectId((current) => (current === defect.id ? null : current))')
    expect(listSource).toContain('className="defect-item-hover-card"')
    expect(defectShowSource).toContain('className="defect-item-tooltip-content"')
    expect(defectShowSource).toContain('className="defect-item-tooltip-name"')
    expect(defectShowSource).toContain('Coil ID:')
    expect(defectShowSource).toContain('Surface:')
    expect(defectShowSource).toContain('Level:')
    expect(defectShowSource).toContain('Position:')
    expect(defectShowSource).toContain('Size:')
    expect(listSource).toContain('{renderDefectItemTooltip(defect)}')
    expect(defectShowCss).toContain('.defect-item-hover-card')
    expect(defectShowCss).toContain('.defect-item:hover .defect-item-hover-card')
    expect(defectShowCss).toContain('.defect-item:focus .defect-item-hover-card')
    expect(defectShowCss).toContain('.defect-item.tooltip-open .defect-item-hover-card')
    expect(defectShowCss).toContain('background: #e8e8e8')
    expect(defectShowCss).toContain('border: 1px solid #666666')
  })

  it('positions the QML DefectItemShow hover detail card above and centered on the item', () => {
    expect(defectShowCss).toMatch(
      /\.defect-item-hover-card\s*\{[\s\S]*left:\s*50%[\s\S]*bottom:\s*calc\(100%\s*\+\s*8px\)[\s\S]*transform:\s*translateX\(-50%\)/,
    )
    expect(defectShowCss).not.toMatch(/\.defect-item-hover-card\s*\{[\s\S]*top:\s*6px/)
    expect(defectShowCss).not.toMatch(/\.defect-item-hover-card\s*\{[\s\S]*left:\s*66px/)
  })

  it('uses the QML DefectItemShow tooltip z order above regular grid delegates', () => {
    expect(defectShowCss).toMatch(/\.defect-item-hover-card\s*\{[\s\S]*z-index:\s*1000/)
  })

  it('keeps the QML hover detail card from being clipped in narrow stacked layouts', () => {
    expect(defectShowSource).toContain("className={`defect-content ${tooltipDefectId != null ? 'tooltip-active' : ''}`}")
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-content\.tooltip-active\s*\{[\s\S]*overflow:\s*visible/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-content\.tooltip-active \.defect-list-panel\s*\{[\s\S]*overflow:\s*visible/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-content\.tooltip-active \.defect-list-container\s*\{[\s\S]*overflow:\s*visible/,
    )
  })

  it('mirrors the QML DefectItemShow hover scale animation', () => {
    expect(defectShowCss).toContain('transform-origin: center')
    expect(defectShowCss).toContain('transition: transform 450ms ease')
    expect(defectShowCss).toContain('.defect-item:hover,')
    expect(defectShowCss).toContain('.defect-item.tooltip-open')
    expect(defectShowCss).toContain('transform: scale(1.2)')
    expect(defectShowCss).toContain('z-index: 10')
  })

  it('mirrors QML DefectItemShow hover currentIndex selection and GridView highlight', () => {
    const listContainerStart = defectShowSource.indexOf('<div className="defect-list-container">')
    const listStart = defectShowSource.indexOf('filteredDefects.map((defect) => (', listContainerStart)
    const listEnd = defectShowSource.indexOf('</section>', listStart)
    const listSource = defectShowSource.slice(listStart, listEnd)
    const itemCssStart = defectShowCss.indexOf('.defect-item {')
    const itemCssEnd = defectShowCss.indexOf('.defect-item:hover,', itemCssStart)
    const itemCssSource = defectShowCss.slice(itemCssStart, itemCssEnd)

    expect(listSource).toContain('onMouseEnter={() => {')
    expect(listSource).toContain('setSelectedDefectId(defect.id)')
    expect(listSource).toContain('setTooltipDefectId(defect.id)')
    expect(itemCssSource).toContain('border: 0')
    expect(itemCssSource).toContain('background: transparent')
    expect(defectShowCss).not.toContain('border-color: #ff4d4f')
    expect(defectShowCss).not.toContain('background: rgba(255, 77, 79, 0.14)')
    expect(defectShowCss).toMatch(/\.defect-item\.selected::before\s*\{[\s\S]*background:\s*lightsteelblue/)
    expect(defectShowCss).toMatch(
      /\.defect-item\.selected::before\s*\{[\s\S]*border-radius:\s*5px/,
    )
  })

  it('renders the QML DefectInfoView current-coil summary row', () => {
    const infoPanelStart = defectShowCss.indexOf('.defect-qml-info-panel {')
    const infoPanelEnd = defectShowCss.indexOf('.defect-qml-info-item {', infoPanelStart)
    const infoPanelSource = defectShowCss.slice(infoPanelStart, infoPanelEnd)

    expect(defectShowSource).toContain('const qmlDefectInfoRows = useMemo')
    expect(defectShowSource).toContain("label: '缺陷数量'")
    expect(defectShowSource).toContain("readCurrentCoilRawValue(['coilId', 'CoilId'], String(currentCoil?.id ?? '--'))")
    expect(defectShowSource).toContain("label: '卷数'")
    expect(defectShowSource).toContain("readCurrentCoilRawValue(['nextInfo', 'NextInfo']")
    expect(defectShowSource).toContain("label: '识别率'")
    expect(defectShowSource).toContain("value: currentCoil?.coilNo ?? '--'")
    expect(defectShowSource).toContain("label: '卷识别率'")
    expect(defectShowSource).toContain("readCurrentCoilRawValue(['coilType', 'CoilType']")
    expect(defectShowSource).toContain('<section className="defect-qml-info-panel" aria-label="缺陷数据概览">')
    expect(defectShowSource).toContain('qmlDefectInfoRows.map((row) => (')
    expect(defectShowSource).toContain('className="defect-qml-info-item"')
    expect(defectShowCss).toContain('.defect-qml-info-panel')
    expect(defectShowCss).toContain('.defect-qml-info-item')
    expect(infoPanelSource).toContain('grid-template-columns: repeat(2, minmax(0, 1fr))')
    expect(infoPanelSource).not.toContain('grid-template-columns: repeat(4, minmax(0, 1fr))')
    expect(defectShowCss).toContain('.defect-qml-info-item:nth-child(2n)')
    expect(defectShowCss).toContain('.defect-qml-info-item:nth-child(n + 3)')
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-qml-info-panel\s*\{[\s\S]*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\)/,
    )
  })

  it('keeps QML DefectInfoView CardBase and FlowRowItem sizing', () => {
    const infoPanelStart = defectShowCss.indexOf('.defect-qml-info-panel {')
    const infoPanelEnd = defectShowCss.indexOf('.defect-qml-info-item {', infoPanelStart)
    const infoPanelSource = defectShowCss.slice(infoPanelStart, infoPanelEnd)
    const infoItemStart = defectShowCss.indexOf('.defect-qml-info-item {')
    const infoItemEnd = defectShowCss.indexOf('.defect-qml-info-item:last-child', infoItemStart)
    const infoItemSource = defectShowCss.slice(infoItemStart, infoItemEnd)

    expect(infoPanelSource).toContain('height: 100px')
    expect(infoPanelSource).toContain('max-height: 100px')
    expect(infoPanelSource).toContain('grid-auto-rows: 30px')
    expect(infoPanelSource).toContain('align-content: start')
    expect(infoItemSource).toContain('height: 30px')
    expect(infoItemSource).toContain('padding: 0 10px')
  })

  it('mirrors QML DefectInfoView FlowRowItem label and value text styling', () => {
    const infoPanelStart = defectShowSource.indexOf('<section className="defect-qml-info-panel"')
    const infoPanelEnd = defectShowSource.indexOf('</section>', infoPanelStart)
    const infoPanelSource = defectShowSource.slice(infoPanelStart, infoPanelEnd)
    const labelCssStart = defectShowCss.indexOf('.defect-qml-info-label {')
    const labelCssEnd = defectShowCss.indexOf('.defect-qml-info-item strong {', labelCssStart)
    const labelCssSource = defectShowCss.slice(labelCssStart, labelCssEnd)
    const valueCssStart = defectShowCss.indexOf('.defect-qml-info-item strong {')
    const valueCssEnd = defectShowCss.indexOf('.defect-class-summary-panel {', valueCssStart)
    const valueCssSource = defectShowCss.slice(valueCssStart, valueCssEnd)

    expect(infoPanelSource).toContain('className="defect-qml-info-label"')
    expect(infoPanelSource).toContain('{row.label}:')
    expect(labelCssSource).toContain('opacity: 0.7')
    expect(valueCssSource).toContain('font-size: 15px')
    expect(valueCssSource).toContain('font-weight: 700')
  })

  it('uses QML showAll semantics for the all-class action', () => {
    expect(defectShowSource).toContain('getQmlSelectAllDefectClasses')
    expect(defectShowSource).toContain('includeHidden: showAlarmDefectClasses')
    expect(defectShowSource).not.toContain('setSelectedDefectClasses(filterOptionNames)')
  })

  it('hides hidden/background class options while the QML include-background toggle is off', () => {
    expect(defectShowSource).toContain('getQmlVisibleFilterOptions')
    expect(defectShowSource).toContain('visibleFilterOptions')
    expect(defectShowSource).toContain('includeHidden: showAlarmDefectClasses')
    expect(defectShowSource).toContain('options={visibleFilterOptions.map')
  })

  it('renders the QML DefectClassInfoView count flow as visible class checkboxes', () => {
    expect(defectShowSource).toContain('toggleDefectClass')
    expect(defectShowSource).toContain('className="defect-class-summary-panel"')
    expect(defectShowSource).toContain('className="panel-title defect-class-summary-title"')
    expect(defectShowSource).toContain('缺陷总计')
    expect(defectShowSource).toContain('className="defect-class-summary-flow"')
    expect(defectShowSource).toContain('visibleFilterOptions.map((option) => (')
    expect(defectShowSource).toContain('checked={selectedDefectClasses.includes(option.name)}')
    expect(defectShowSource).toContain('onChange={(event) => toggleDefectClass(option.name, event.target.checked)}')
    expect(defectShowSource).toContain('{defectClassCounts[option.name] ?? 0}')
  })

  it('colors QML DefectFlowRowItem names and counts from the dictionary while selected', () => {
    const panelStart = defectShowSource.indexOf('<section className="defect-class-summary-panel">')
    const panelEnd = defectShowSource.indexOf('<div className="defect-content">', panelStart)
    const panelSource = defectShowSource.slice(panelStart, panelEnd)
    const itemCssStart = defectShowCss.indexOf('.defect-class-summary-item {')
    const itemCssEnd = defectShowCss.indexOf('.defect-class-summary-empty', itemCssStart)
    const itemCssSource = defectShowCss.slice(itemCssStart, itemCssEnd)

    expect(panelSource).toContain("style={{ '--defect-class-color': option.color ?? '#00000000' } as CSSProperties}")
    expect(panelSource).not.toContain(
      "style={{\n                        color: selectedDefectClasses.includes(option.name)",
    )
    expect(itemCssSource).toContain('.defect-class-summary-item.selected .defect-class-summary-name')
    expect(itemCssSource).toContain('.defect-class-summary-item.selected .defect-class-count')
    expect(itemCssSource).toContain('color: var(--defect-class-color, #00000000)')
    expect(itemCssSource).toContain('.defect-class-summary-item:not(.selected) .defect-class-summary-name')
    expect(itemCssSource).toContain('.defect-class-summary-item:not(.selected) .defect-class-count')
    expect(itemCssSource).toContain('color: #ffffff')
    expect(itemCssSource).toContain('color: #aaaaaa')
  })

  it('places the QML DefectFlowRowItem checkbox after the name and count', () => {
    const panelStart = defectShowSource.indexOf('<section className="defect-class-summary-panel">')
    const panelEnd = defectShowSource.indexOf('<div className="defect-content">', panelStart)
    const panelSource = defectShowSource.slice(panelStart, panelEnd)

    expect(panelSource).not.toContain('className="defect-class-swatch"')
    expect(defectShowCss).toMatch(
      /\.defect-class-summary-item\.ant-checkbox-wrapper\s*\{[\s\S]*flex-direction:\s*row-reverse/,
    )
    expect(defectShowCss).toMatch(/\.defect-class-summary-item\s*\{[\s\S]*height:\s*25px/)
  })

  it('reserves the QML DefectFlowRowItem 40px checkbox slot', () => {
    const itemCssStart = defectShowCss.indexOf('.defect-class-summary-item.ant-checkbox-wrapper {')
    const itemCssEnd = defectShowCss.indexOf('.defect-class-summary-item.selected {', itemCssStart)
    const itemCssSource = defectShowCss.slice(itemCssStart, itemCssEnd)

    expect(itemCssSource).toContain('.defect-class-summary-item .ant-checkbox')
    expect(itemCssSource).toContain('width: 40px')
    expect(itemCssSource).toContain('height: 25px')
    expect(itemCssSource).toContain('flex: 0 0 40px')
    expect(itemCssSource).toContain('align-items: center')
    expect(itemCssSource).toContain('justify-content: center')
  })

  it('mirrors QML DefectFlowRowItem label font sizes and row spacing', () => {
    const itemCssStart = defectShowCss.indexOf('.defect-class-summary-item {')
    const itemCssEnd = defectShowCss.indexOf('.defect-class-summary-empty', itemCssStart)
    const itemCssSource = defectShowCss.slice(itemCssStart, itemCssEnd)
    const contentCssStart = defectShowCss.indexOf('.defect-class-summary-content {')
    const contentCssEnd = defectShowCss.indexOf('.defect-class-summary-name {', contentCssStart)
    const contentCssSource = defectShowCss.slice(contentCssStart, contentCssEnd)
    const nameCssStart = defectShowCss.indexOf('.defect-class-summary-name {')
    const nameCssEnd = defectShowCss.indexOf(
      '.defect-class-summary-item.selected .defect-class-summary-name',
      nameCssStart,
    )
    const nameCssSource = defectShowCss.slice(nameCssStart, nameCssEnd)
    const countCssStart = defectShowCss.indexOf('.defect-class-summary-item .defect-class-count {')
    const countCssEnd = defectShowCss.indexOf(
      '.defect-class-summary-item.selected .defect-class-summary-name',
      countCssStart,
    )
    const countCssSource = defectShowCss.slice(countCssStart, countCssEnd)

    expect(contentCssSource).toContain('gap: 4px')
    expect(nameCssSource).toContain('font-size: 12px')
    expect(countCssSource).toContain('font-size: 11px')
    expect(itemCssSource).toContain('font-size: 12px')
  })

  it('uses the QML DefectFlowRowItem defect color as the checkbox accent', () => {
    const itemCssStart = defectShowCss.indexOf('.defect-class-summary-item.ant-checkbox-wrapper {')
    const itemCssEnd = defectShowCss.indexOf('.defect-class-summary-empty', itemCssStart)
    const itemCssSource = defectShowCss.slice(itemCssStart, itemCssEnd)

    expect(itemCssSource).toContain('.defect-class-summary-item .ant-checkbox-checked .ant-checkbox-inner')
    expect(itemCssSource).toContain('background-color: var(--defect-class-color, #00000000)')
    expect(itemCssSource).toContain('border-color: var(--defect-class-color, #00000000)')
  })

  it('keeps QML DefectFlowRowItem rows unframed instead of rendering card chips', () => {
    const itemCssStart = defectShowCss.indexOf('.defect-class-summary-item {')
    const itemCssEnd = defectShowCss.indexOf('.defect-class-summary-item.ant-checkbox-wrapper', itemCssStart)
    const itemCssSource = defectShowCss.slice(itemCssStart, itemCssEnd)
    const selectedCssStart = defectShowCss.indexOf('.defect-class-summary-item.selected {')
    const selectedCssEnd = defectShowCss.indexOf('.defect-class-summary-item .ant-checkbox + span', selectedCssStart)
    const selectedCssSource = defectShowCss.slice(selectedCssStart, selectedCssEnd)

    expect(itemCssSource).toContain('padding: 0')
    expect(itemCssSource).toContain('border: 0')
    expect(itemCssSource).toContain('background: transparent')
    expect(itemCssSource).not.toContain('border-radius')
    expect(selectedCssSource).not.toContain('background:')
    expect(selectedCssSource).not.toContain('border-color:')
  })

  it('places QML DefectClassInfoView include-background and selection actions inside the summary panel', () => {
    const panelStart = defectShowSource.indexOf('<section className="defect-class-summary-panel">')
    const panelEnd = defectShowSource.indexOf('<div className="defect-content">', panelStart)
    const panelSource = defectShowSource.slice(panelStart, panelEnd)

    expect(panelSource).toContain('className="defect-class-summary-actions"')
    expect(panelSource).toContain('包括背景')
    expect(panelSource).toContain('changeAlarmDefectClassVisibility(event.target.checked)')
    expect(panelSource).toContain('onClick={resetDefectClasses}')
    expect(panelSource).toContain('onClick={selectAllDefectClasses}')
    expect(panelSource).toContain('onClick={clearDefectClasses}')
    expect(panelSource).toContain('重置')
    expect(panelSource).toContain('全选')
    expect(panelSource).toContain('取消')
  })

  it('keeps the QML DefectClassInfoView action row inside the same Flow as the class rows', () => {
    const panelStart = defectShowSource.indexOf('<section className="defect-class-summary-panel">')
    const panelEnd = defectShowSource.indexOf('<div className="defect-content">', panelStart)
    const panelSource = defectShowSource.slice(panelStart, panelEnd)
    const bodyCssStart = defectShowCss.indexOf('.defect-class-summary-body {')
    const bodyCssEnd = defectShowCss.indexOf('.defect-class-summary-flow {', bodyCssStart)
    const bodyCssSource = defectShowCss.slice(bodyCssStart, bodyCssEnd)
    const actionsCssStart = defectShowCss.indexOf('.defect-class-summary-actions {')
    const actionsCssEnd = defectShowCss.indexOf('.defect-class-summary-include-background', actionsCssStart)
    const actionsCssSource = defectShowCss.slice(actionsCssStart, actionsCssEnd)

    expect(panelSource).not.toContain('</div>\n          <div className="defect-class-summary-actions">')
    expect(bodyCssSource).not.toContain('grid-template-rows: minmax(0, 1fr) auto')
    expect(actionsCssSource).toContain('width: 100%')
    expect(actionsCssSource).not.toContain('border-top')
  })

  it('keeps QML SelectButtonBase height for DefectClassInfoView selection actions', () => {
    const actionsCssStart = defectShowCss.indexOf('.defect-class-summary-actions .ant-btn {')
    const actionsCssEnd = defectShowCss.indexOf('.defect-class-summary-include-background', actionsCssStart)
    const actionsButtonCssSource = defectShowCss.slice(actionsCssStart, actionsCssEnd)

    expect(actionsButtonCssSource).toContain('height: 35px')
    expect(actionsButtonCssSource).toContain('min-height: 35px')
  })

  it('keeps QML SelectButtonBase selection actions text-only without icons', () => {
    const panelStart = defectShowSource.indexOf('<section className="defect-class-summary-panel">')
    const panelEnd = defectShowSource.indexOf('<div className="defect-content">', panelStart)
    const panelSource = defectShowSource.slice(panelStart, panelEnd)

    expect(panelSource).toContain('重置')
    expect(panelSource).toContain('全选')
    expect(panelSource).toContain('取消')
    expect(panelSource).not.toContain('icon={<ReloadOutlined />}')
    expect(panelSource).not.toContain('icon={<CheckSquareOutlined />}')
    expect(panelSource).not.toContain('icon={<CloseSquareOutlined />}')
  })

  it('keeps the QML DefectClassInfoView expanded CardBase height at 200px', () => {
    const panelCssStart = defectShowCss.indexOf('.defect-class-summary-panel {')
    const panelCssEnd = defectShowCss.indexOf('.defect-class-summary-title {', panelCssStart)
    const panelCssSource = defectShowCss.slice(panelCssStart, panelCssEnd)
    const bodyCssStart = defectShowCss.indexOf('.defect-class-summary-body {')
    const bodyCssEnd = defectShowCss.indexOf('.defect-class-summary-flow {', bodyCssStart)
    const bodyCssSource = defectShowCss.slice(bodyCssStart, bodyCssEnd)
    const flowCssStart = defectShowCss.indexOf('.defect-class-summary-flow {')
    const flowCssEnd = defectShowCss.indexOf('.defect-class-summary-actions {', flowCssStart)
    const flowCssSource = defectShowCss.slice(flowCssStart, flowCssEnd)

    expect(panelCssSource).toContain('height: 200px')
    expect(panelCssSource).toContain('max-height: 200px')
    expect(bodyCssSource).toContain('min-height: 0')
    expect(flowCssSource).toContain('overflow: auto')
  })

  it('uses the QML CardBase top centered title layout for DefectClassInfoView', () => {
    const panelStart = defectShowSource.indexOf('<section className="defect-class-summary-panel">')
    const panelEnd = defectShowSource.indexOf('<div className="defect-content">', panelStart)
    const panelSource = defectShowSource.slice(panelStart, panelEnd)
    const panelCssStart = defectShowCss.indexOf('.defect-class-summary-panel {')
    const panelCssEnd = defectShowCss.indexOf('.defect-class-summary-title {', panelCssStart)
    const panelCssSource = defectShowCss.slice(panelCssStart, panelCssEnd)
    const titleCssStart = defectShowCss.indexOf('.defect-class-summary-title {')
    const titleCssEnd = defectShowCss.indexOf('.defect-class-summary-body {', titleCssStart)
    const titleCssSource = defectShowCss.slice(titleCssStart, titleCssEnd)

    expect(panelSource).not.toContain('<FilterOutlined />')
    expect(panelCssSource).toContain('grid-template-rows: auto minmax(0, 1fr)')
    expect(panelCssSource).toContain('grid-template-columns: minmax(0, 1fr)')
    expect(panelCssSource).not.toContain('grid-template-columns: auto minmax(0, 1fr)')
    expect(titleCssSource).toContain('justify-content: center')
    expect(titleCssSource).toContain('height: 35px')
    expect(titleCssSource).toContain('font-size: 22px')
    expect(titleCssSource).not.toContain('width: 104px')
    expect(titleCssSource).not.toContain('border-right')
  })

  it('collapses the defect content columns for narrow Tauri windows', () => {
    expect(defectShowCss).toContain('@media (max-width: 700px)')
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-content\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-content\s*\{[\s\S]*grid-template-rows:\s*minmax\(160px,\s*0\.7fr\)\s+minmax\(260px,\s*1fr\)\s+minmax\(200px,\s*0\.8fr\)/,
    )
  })

  it('lets the defect toolbar and class summary shrink inside narrow Tauri windows', () => {
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-show-page\s*\{[\s\S]*grid-template-rows:\s*auto\s+auto\s+auto\s+minmax\(0,\s*1fr\)/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-toolbar\s*\{[\s\S]*height:\s*auto[\s\S]*flex-wrap:\s*wrap/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-toolbar \.ant-space\s*\{[\s\S]*max-width:\s*100%/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-class-filter\s*\{[\s\S]*width:\s*100%[\s\S]*min-width:\s*0/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-class-summary-panel\s*\{[\s\S]*grid-template-columns:\s*minmax\(0,\s*1fr\)/,
    )
    expect(defectShowCss).toMatch(
      /@media \(max-width: 700px\)[\s\S]*\.defect-class-summary-title\s*\{[\s\S]*width:\s*auto[\s\S]*border-right:\s*0/,
    )
  })

  it('keeps include-background as row visibility instead of auto-selecting hidden classes', () => {
    expect(defectShowSource).toContain('reconcileQmlDefectClassSelection')
    expect(defectShowSource).toContain('setShowAlarmDefectClasses(checked)')
    expect(defectShowSource).not.toContain('getDefaultSelectedDefectClasses(filterOptions, { includeHidden: checked })')
    expect(defectShowSource).not.toContain('nextSelected.add(name)')
  })

  it('preserves a clear-all class selection when toggling QML include-background visibility', () => {
    expect(defectShowSource).toContain('hasInitializedDefectClassSelectionRef')
    expect(defectShowSource).toContain('preserveEmpty: hasInitializedDefectClassSelectionRef.current')
    expect(defectShowSource).toContain('hasInitializedDefectClassSelectionRef.current = true')
  })

  it('keeps the manual defect export folder input read-only like QML DefectExportDialog', () => {
    expect(defectShowSource).toContain('placeholder="选择导出目录..."')
    expect(defectShowSource).toContain('readOnly')
    expect(defectShowSource).toContain('chooseManualDefectExportPath')
    expect(defectShowSource).not.toContain('onChange={(event) => setManualDefectExportPath(event.target.value)}')
  })

  it('opens the manual defect export folder dialog from the QML pictures default location', () => {
    expect(defectShowSource).toContain('getNativeDefaultPicturesDirectory')
    expect(defectShowSource).toContain('manualDefectDefaultExportDirectory')
    expect(defectShowSource).toContain('setManualDefectDefaultExportDirectory(defaultDirectory)')
    expect(defectShowSource).toContain('selectNativeDirectory({')
    expect(defectShowSource).toContain('defaultDirectory: manualDefectDefaultExportDirectory')
  })

  it('formats manual defect export errors like QML DefectExportDialog', () => {
    expect(defectShowSource).toContain('formatManualDefectExportError(error)')
    expect(defectShowSource).toContain("title: '导出失败'")
    expect(defectShowSource).not.toContain('{JSON.stringify(error)}</pre>')
  })

  it('uses QML result dialog confirmation text for manual defect export results', () => {
    expect(defectShowSource).toContain("title: '导出完成'")
    expect(defectShowSource).toContain("title: '导出失败'")
    expect(defectShowSource.match(/okText: '确定'/g) ?? []).toHaveLength(2)
  })

  it('keeps the manual defect export dialog open after success like QML', () => {
    const successStart = defectShowSource.indexOf('Modal.info({')
    const successEnd = defectShowSource.indexOf('} catch (error)', successStart)
    const successBranch = defectShowSource.slice(successStart, successEnd)

    expect(successBranch).toContain("title: '导出完成'")
    expect(successBranch).not.toContain('setManualDefectExportOpen(false)')
    expect(defectShowSource).toContain('onCancel={() => setManualDefectExportOpen(false)}')
  })

  it('confirms manual defect deletion like QML ManualDefectEditDialog', () => {
    expect(defectShowSource).toContain('confirmDeleteManualDefect')
    expect(defectShowSource).toContain('Modal.confirm({')
    expect(defectShowSource).toContain("title: '确认删除'")
    expect(defectShowSource).toContain("content: '确定要删除此缺陷标注吗？\\n此操作无法撤销。'")
    expect(defectShowSource).toContain("okText: '删除'")
    expect(defectShowSource).toContain("cancelText: '取消'")
    expect(defectShowSource).toContain('okButtonProps: { danger: true')
    expect(defectShowSource).toContain('onOk: deleteManualDefect')
    expect(defectShowSource).toContain('onClick={confirmDeleteManualDefect}')
    expect(defectShowSource).not.toContain('onClick={deleteManualDefect}')
  })

  it('disables manual defect edit fields for auto defects like QML editGroup', () => {
    const formStart = defectShowSource.indexOf('<div className="manual-defect-form">')
    const formEnd = defectShowSource.indexOf('<div className="manual-defect-annotator">', formStart)
    const formSource = defectShowSource.slice(formStart, formEnd)

    expect(formSource.match(/disabled=\{!canEditSelectedManualDefect\}/g) ?? []).toHaveLength(6)
  })

  it('uses QML auto-defect warning text in the manual edit dialog', () => {
    expect(defectShowSource).toContain('⚠ 此为自动检测缺陷，无法编辑')
  })

  it('mirrors the QML ManualDefectEditDialog 450x400 shell with an internal scrolling body', () => {
    expect(manualDefectEditDialogQml).toContain('title: "编辑缺陷标注"')
    expect(manualDefectEditDialogQml).toContain('width: 450')
    expect(manualDefectEditDialogQml).toContain('height: 400')
    expect(manualDefectEditDialogQml).toContain('ColumnLayout {')
    expect(manualDefectEditDialogQml).toContain('anchors.fill: parent')

    expect(defectShowSource).toContain('className="manual-defect-edit-modal"')
    expect(defectShowSource).toContain('width={450}')
    expect(defectShowCss).toContain('.manual-defect-edit-modal .ant-modal-content')
    expect(defectShowCss).toContain('height: min(400px, calc(100vh - 32px))')
    expect(defectShowCss).toContain('max-height: min(400px, calc(100vh - 32px))')
    expect(defectShowCss).toContain('overflow: hidden')
    expect(defectShowCss).toContain('.manual-defect-edit-modal .ant-modal-body')
    expect(defectShowCss).toContain('overflow-y: auto')
    expect(defectShowCss).toContain('overflow-x: hidden')
    expect(defectShowCss).toContain('.manual-defect-form')
    expect(defectShowCss).toContain('min-height: 0')
  })

  it('exposes the QML manual defect add workflow from the panorama viewer', () => {
    expect(defectShowSource).toContain('manualDefectAddMode')
    expect(defectShowSource).toContain('onManualAnnotation={handleManualDefectAnnotation}')
    expect(defectShowSource).toContain('buildManualDefectAddPayload')
    expect(defectShowSource).toContain('defectApi.addManualDefect')
    expect(defectShowSource).toContain('title="添加缺陷标注"')
    expect(defectShowSource).toContain('新增标注')
  })

  it('shows a QML-style progress dialog while manual defect export is running', () => {
    expect(defectShowSource).toContain('manualDefectProgressOpen')
    expect(defectShowSource).toContain('setManualDefectProgressOpen(true)')
    expect(defectShowSource).toContain('setManualDefectProgressOpen(false)')
    expect(defectShowSource).toContain('title="正在导出..."')
    expect(defectShowSource).toContain('正在准备导出...')
    expect(defectShowSource).toContain('后台运行')
    expect(defectShowSource).toContain('closable={false}')
    expect(defectShowSource).toContain('maskClosable={false}')
  })

  it('passes the QML shared-folder base name when opening a defect image location', () => {
    const openFolderStart = defectShowSource.indexOf('const openDefectImageFolder = (defect: DefectData | null) =>')
    const openFolderEnd = defectShowSource.indexOf('const openSelectedDefectImageFolder', openFolderStart)
    const openFolderSource = defectShowSource.slice(openFolderStart, openFolderEnd)

    expect(openFolderSource).toContain('buildDefectImageFolderUrl(defect')
    expect(openFolderSource).toContain('sharedFolderBaseName,')
  })

  it('mirrors QML DefectDataViewMenu current-list then real-list image navigation lookup', () => {
    expect(defectShowSource).toContain('currentCoilList,')
    expect(defectShowSource).toContain(
      'const qmlCurrentCoilList = currentCoilList.length > 0 ? currentCoilList : coilList',
    )
    expect(defectShowSource).toContain('getDefectListRange(qmlCurrentCoilList)')
    expect(defectShowSource).toContain('currentCoilList: qmlCurrentCoilList')
    expect(defectShowSource).toContain('realtimeCoilList: coilList')
  })
})
