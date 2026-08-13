import { beforeAll, describe, expect, it } from 'vitest'

import operationSidebarSource from './index.tsx?raw'

let operationSidebarCss = ''
let reDetectionQmlSource = ''
let qmlDataListItemBaseSource = ''
let qmlDataListItemSource = ''
let qmlListTitleViewSource = ''
let qmlHeadViewSource = ''
let qmlListToolMenuSource = ''
let qmlFootViewSource = ''
let qmlSearchViewSource = ''
let qmlFilterViewSource = ''
let qmlSearchByCoilNoSource = ''
let qmlSearchByCoilIdSource = ''
let qmlSearchByDataTimeSource = ''
let qmlDateTimeSelectLineItemSource = ''

beforeAll(async () => {
  const { readFileSync } = (await import('node:fs')) as {
    readFileSync: (path: URL, encoding: 'utf8') => string
  }
  operationSidebarCss = readFileSync(new URL('./OperationSidebar.css', import.meta.url), 'utf8')
  reDetectionQmlSource = readFileSync(
    new URL('../../../../MotionStudio/qml/PopupView/ReDetection/ReDetectionView.qml', import.meta.url),
    'utf8',
  )
  qmlDataListItemBaseSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/DataList/DataListViewItenBase.qml', import.meta.url),
    'utf8',
  )
  qmlDataListItemSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/DataList/DataListViewIten.qml', import.meta.url),
    'utf8',
  )
  qmlListTitleViewSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/DataList/ListTitleView.qml', import.meta.url),
    'utf8',
  )
  qmlHeadViewSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/DataList/HeadView.qml', import.meta.url),
    'utf8',
  )
  qmlListToolMenuSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/DataList/ListToolMenu.qml', import.meta.url),
    'utf8',
  )
  qmlFootViewSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/FootView.qml', import.meta.url),
    'utf8',
  )
  qmlSearchViewSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/SearchView/SearchView.qml', import.meta.url),
    'utf8',
  )
  qmlFilterViewSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/SearchView/FilterView.qml', import.meta.url),
    'utf8',
  )
  qmlSearchByCoilNoSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/SearchView/SearchByCoilNo.qml', import.meta.url),
    'utf8',
  )
  qmlSearchByCoilIdSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/SearchView/SearchByCoilId.qml', import.meta.url),
    'utf8',
  )
  qmlSearchByDataTimeSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/SearchView/SearchByDataTime.qml', import.meta.url),
    'utf8',
  )
  qmlDateTimeSelectLineItemSource = readFileSync(
    new URL('../../../../MotionStudio/qml/Pages/LeftPage/SearchView/DateTimeSelectLineItem.qml', import.meta.url),
    'utf8',
  )
})

function getReDetectionModalSource(): string {
  const openPropIndex = operationSidebarSource.indexOf('open={reDetectionOpen}')
  const reDetectionModalStart = operationSidebarSource.lastIndexOf('<Modal', openPropIndex)
  const reDetectionModalEnd = operationSidebarSource.indexOf('</Modal>', openPropIndex)

  expect(openPropIndex).toBeGreaterThan(-1)
  expect(reDetectionModalStart).toBeGreaterThan(-1)
  expect(reDetectionModalEnd).toBeGreaterThan(openPropIndex)

  return operationSidebarSource.slice(reDetectionModalStart, reDetectionModalEnd)
}

function getSearchFilterModalSource(): string {
  const filterPopupIndex = operationSidebarSource.indexOf('data-qml-search-filter-popup')
  const filterModalStart = operationSidebarSource.lastIndexOf('<Modal', filterPopupIndex)
  const filterModalEnd = operationSidebarSource.indexOf('</Modal>', filterPopupIndex)

  expect(filterPopupIndex).toBeGreaterThan(-1)
  expect(filterModalStart).toBeGreaterThan(-1)
  expect(filterModalEnd).toBeGreaterThan(filterPopupIndex)

  return operationSidebarSource.slice(filterModalStart, filterModalEnd)
}

function getSearchSectionSource(): string {
  const searchSectionClassIndex = operationSidebarSource.indexOf('className="sidebar-section search-panel"')
  const searchSectionStart = operationSidebarSource.lastIndexOf('<section', searchSectionClassIndex)
  const searchSectionEnd = operationSidebarSource.indexOf('</section>', searchSectionClassIndex)

  expect(searchSectionClassIndex).toBeGreaterThan(-1)
  expect(searchSectionStart).toBeGreaterThan(-1)
  expect(searchSectionEnd).toBeGreaterThan(searchSectionClassIndex)

  return operationSidebarSource.slice(searchSectionStart, searchSectionEnd)
}

describe('OperationSidebar re-detection websocket parity', () => {
  it('refreshes the realtime coil list through QML /flush polling', () => {
    expect(operationSidebarSource).toContain('buildQmlFlushStartCoilId')
    expect(operationSidebarSource).toContain('mergeQmlFlushCoilList')
    expect(operationSidebarSource).toContain('resolveQmlRealtimeCurrentCoil')
    expect(operationSidebarSource).toContain('QML_COIL_REFRESH_INTERVAL_MS')
    expect(operationSidebarSource).toContain('coilApi.flush')
    expect(operationSidebarSource).toContain('refetchInterval: QML_COIL_REFRESH_INTERVAL_MS')
  })

  it('exposes the QML keepLatest toggle for realtime list selection', () => {
    expect(operationSidebarSource).toContain('coilListMode: listMode')
    expect(operationSidebarSource).toContain('keepLatest')
    expect(operationSidebarSource).toContain('setCoilListMode: setListMode')
    expect(operationSidebarSource).toContain('setKeepLatest')
    expect(operationSidebarSource).toContain('autoKeepLatestTicks')
    expect(operationSidebarSource).toContain('checked={keepLatest}')
    expect(operationSidebarSource).toContain('onChange={(event) => changeKeepLatest(event.target.checked)}')
    expect(operationSidebarSource).toContain('保持最新')
  })

  it('mirrors the QML keepLatest auto-restore timer', () => {
    expect(operationSidebarSource).toContain('QML_KEEP_LATEST_AUTO_RESTORE_INTERVAL_MS')
    expect(operationSidebarSource).toContain('useUiSettingsStore((state) => state.autoKeepTimeMax)')
    expect(operationSidebarSource).toContain('advanceQmlKeepLatestAutoRestoreTick')
    expect(operationSidebarSource).toContain('advanceQmlKeepLatestAutoRestoreTick(ticks, autoKeepTimeMax)')
    expect(operationSidebarSource).toContain('window.setInterval')
    expect(operationSidebarSource).toContain('setKeepLatest(true)')
    expect(operationSidebarSource).toContain('setAutoKeepLatestTicks(0)')
  })

  it('turns off QML keepLatest when a list row is selected manually', () => {
    expect(operationSidebarSource).toContain('const selectCoilFromList = (coil: CoilData) => {')
    expect(operationSidebarSource).toContain('changeKeepLatest(false)')
    expect(operationSidebarSource).toContain('onClick={() => selectCoilFromList(coil)}')
    expect(operationSidebarSource).not.toContain('onClick={() => setCurrentCoil(coil)}')
  })

  it('turns off QML keepLatest when backend search selects a history row', () => {
    const applySearchResultsStart = operationSidebarSource.indexOf('const applySearchResults = (nextResults: CoilData[]) => {')
    const runBackendSearchStart = operationSidebarSource.indexOf('const runBackendSearch = async () => {')
    const applySearchResultsSource = operationSidebarSource.slice(applySearchResultsStart, runBackendSearchStart)

    expect(applySearchResultsSource).toContain('changeKeepLatest(false)')
    expect(applySearchResultsSource.indexOf('changeKeepLatest(false)')).toBeLessThan(
      applySearchResultsSource.indexOf('setCurrentCoil(nextHistory[0] ?? null)'),
    )
  })

  it('guards history-search selection from the realtime refresh effect while local mode catches up', () => {
    const refreshEffectStart = operationSidebarSource.indexOf('useEffect(() => {\n    const nextList = data?.data ?? []')
    const keepLatestEffectStart = operationSidebarSource.indexOf('useEffect(() => {\n    if (keepLatest) {')
    const refreshEffectSource = operationSidebarSource.slice(refreshEffectStart, keepLatestEffectStart)

    expect(operationSidebarSource).toContain('const pendingHistorySelectionRef = useRef(false)')
    expect(refreshEffectSource).toContain('pendingHistorySelectionRef.current')
    expect(refreshEffectSource.indexOf('pendingHistorySelectionRef.current')).toBeLessThan(
      refreshEffectSource.indexOf("if (listMode === 'realtime')"),
    )
  })

  it('exposes the QML history-list exit action that returns to realtime rows', () => {
    const exitHistoryStart = operationSidebarSource.indexOf('const exitHistoryListMode = () => {')
    const toggleListDefectStart = operationSidebarSource.indexOf('const toggleListDefectClass =')
    const exitHistorySource = operationSidebarSource.slice(exitHistoryStart, toggleListDefectStart)

    expect(exitHistorySource).toContain('pendingHistorySelectionRef.current = false')
    expect(exitHistorySource).toContain("setKeyword('')")
    expect(exitHistorySource).toContain("setListMode('realtime')")
    expect(exitHistorySource).toContain('setCurrentCoil(coilList[0] ?? null)')
    expect(operationSidebarSource).toContain("{listMode === 'history' ? (")
    expect(operationSidebarSource).toContain('aria-label="退出历史模式"')
    expect(operationSidebarSource).toContain('onClick={exitHistoryListMode}')
    expect(operationSidebarSource).toContain('退出')
  })

  it('handles the QML TopMsg return-realtime command through the existing history exit path', () => {
    expect(operationSidebarSource).toContain('returnRealtimeCommand')
    expect(operationSidebarSource).toContain('const handledReturnRealtimeCommandRef = useRef(0)')
    expect(operationSidebarSource).toContain('if (!returnRealtimeCommand)')
    expect(operationSidebarSource).toContain(
      'if (handledReturnRealtimeCommandRef.current === returnRealtimeCommand.serial) return',
    )
    expect(operationSidebarSource).toContain('handledReturnRealtimeCommandRef.current = returnRealtimeCommand.serial')
    expect(operationSidebarSource).toContain('exitHistoryListMode()')
  })

  it('renders the QML left-list title with realtime or history model counts', () => {
    expect(operationSidebarSource).toContain("const listTitle = listMode === 'history' ? `历史: ${historyCoils.length}` : `实时: ${coilList.length}`")
    expect(operationSidebarSource).toContain('<span className={`list-title-count ${listMode}`}>{listTitle}</span>')
    expect(operationSidebarSource).not.toContain("listMode === 'history' ? '历史结果' : '卷材列表'")
  })

  it('publishes QML currentCoilListModel so DefectShow can search history rows before realtime rows', () => {
    expect(operationSidebarSource).toContain('setCurrentCoilList,')
    expect(operationSidebarSource).toContain('const qmlCurrentCoilList = useMemo(')
    expect(operationSidebarSource).toContain('selectVisibleCoilList(listMode, coilList, historyCoils)')
    expect(operationSidebarSource).toContain('setCurrentCoilList(qmlCurrentCoilList)')
  })

  it('renders the QML current coil number and serial id inside the left-list title row', () => {
    expect(operationSidebarSource).toContain('const listCurrentCoil = currentCoil ? {')
    expect(operationSidebarSource).toContain('coilNo: currentCoil.coilNo')
    expect(operationSidebarSource).toContain('coilId: currentCoil.id')
    expect(operationSidebarSource).toContain('className="list-current-coil"')
    expect(operationSidebarSource).toContain('<strong>{listCurrentCoil.coilNo}</strong>')
    expect(operationSidebarSource).toContain('<span>{listCurrentCoil.coilId}</span>')
  })

  it('exposes the QML left-list header refresh action', () => {
    const refreshHandlerStart = operationSidebarSource.indexOf('const refreshQmlCoilList = () => {')
    const copyActionStart = operationSidebarSource.indexOf('const copyCurrentCoilField =')
    const refreshHandlerSource = operationSidebarSource.slice(refreshHandlerStart, copyActionStart)

    const clearRefreshStart = operationSidebarSource.indexOf('const clearSearchAndRefresh = () => {')
    const headerRefreshStart = operationSidebarSource.indexOf('const refreshQmlCoilList = () => {')
    const clearRefreshSource = operationSidebarSource.slice(clearRefreshStart, headerRefreshStart)

    expect(clearRefreshSource).toContain('setCurrentCoil(coilList[0] ?? null)')
    expect(refreshHandlerSource).toContain('clearSearchAndRefresh()')
    expect(operationSidebarSource).toContain('aria-label="刷新列表"')
    expect(operationSidebarSource).toContain('icon={<ReloadOutlined />}')
    expect(operationSidebarSource).toContain('onClick={refreshQmlCoilList}')
  })

  it('keeps QML ListToolMenu actions on the title context menu instead of visible title buttons', () => {
    const listTitleStart = operationSidebarSource.indexOf('<div className="section-title list-title-row">')
    const listDefectPanelStart = operationSidebarSource.indexOf('{listDefectFilterEnabled ? (', listTitleStart)
    const listTitleSource = operationSidebarSource.slice(listTitleStart, listDefectPanelStart)

    expect(qmlHeadViewSource).toContain('MouseArea{')
    expect(qmlHeadViewSource).toContain('listToolMenu.popup()')
    expect(qmlHeadViewSource).toContain('FliterBtn{')
    expect(qmlHeadViewSource).toContain('FlushButton{')
    expect(qmlListToolMenuSource).toContain('text: "查看数据源"')
    expect(qmlListToolMenuSource).toContain('text: "图像备份"')
    expect(qmlListToolMenuSource).toContain('text: "全部重新识别"')
    expect(qmlListToolMenuSource).toContain('text: "变化曲线"')
    expect(listTitleStart).toBeGreaterThan(-1)
    expect(listTitleSource).not.toContain('aria-label="查看数据源"')
    expect(listTitleSource).not.toContain('aria-label="图像备份"')
    expect(listTitleSource).not.toContain('aria-label="列表全部重新识别"')
    expect(listTitleSource).not.toContain('aria-label="列表数值变化曲线"')
    expect(listTitleSource).not.toContain('<Segmented')
  })

  it('keeps QML FootView keepLatest out of the HeadView title row', () => {
    const listTitleStart = operationSidebarSource.indexOf('<div className="section-title list-title-row">')
    const listDefectPanelStart = operationSidebarSource.indexOf('{listDefectFilterEnabled ? (', listTitleStart)
    const listTitleSource = operationSidebarSource.slice(listTitleStart, listDefectPanelStart)
    const footerStart = operationSidebarSource.indexOf('<footer')
    const footerEnd = operationSidebarSource.indexOf('</footer>', footerStart)
    const footerSource = operationSidebarSource.slice(footerStart, footerEnd)

    expect(qmlHeadViewSource).not.toContain('保持最新')
    expect(qmlFootViewSource).toContain('text: "保持最新"')
    expect(listTitleStart).toBeGreaterThan(-1)
    expect(footerStart).toBeGreaterThan(-1)
    expect(listTitleSource).not.toContain('保持最新')
    expect(listTitleSource).not.toContain('className="keep-latest-toggle"')
    expect(footerSource).toContain('data-qml-footer-keep-latest')
    expect(footerSource).toContain('保持最新')
  })

  it('opens the QML ListToolMenu actions from the left-list title context menu', () => {
    const listToolMenuStart = operationSidebarSource.indexOf('const buildQmlListToolMenuItems = (): MenuProps[\'items\'] =>')
    const rowMenuStart = operationSidebarSource.indexOf('const buildQmlDataListItemMenu = (coil: CoilData): MenuProps[\'items\'] =>')
    const listToolMenuSource = operationSidebarSource.slice(listToolMenuStart, rowMenuStart)

    expect(listToolMenuStart).toBeGreaterThan(-1)
    expect(listToolMenuSource).toContain("label: listMode === 'realtime' ? '>历史模式' : '>实时模式'")
    expect(listToolMenuSource).toContain('onClick: switchQmlListMode')
    expect(listToolMenuSource).toContain("label: '查看数据源'")
    expect(listToolMenuSource).toContain('onClick: openCoilListDataSource')
    expect(listToolMenuSource).toContain("label: '图像备份'")
    expect(listToolMenuSource).toContain('onClick: openListBackupImage')
    expect(listToolMenuSource).toContain("label: '全部重新识别'")
    expect(listToolMenuSource).toContain('onClick: openListReDetection')
    expect(listToolMenuSource).toContain("label: '变化曲线'")
    expect(listToolMenuSource).toContain('onClick: openListValueChange')
    expect(operationSidebarSource).toContain("trigger={['contextMenu']}")
    expect(operationSidebarSource).toContain("menu={{ items: buildQmlListToolMenuItems(), triggerSubMenuAction: 'click' }}")
  })

  it('exposes the QML left-list defect-class filter', () => {
    expect(operationSidebarSource).toContain('defectConfigApi.getDefectDict')
    expect(operationSidebarSource).toContain('listDefectFilterEnabled')
    expect(operationSidebarSource).toContain('selectedListDefectClasses')
    expect(operationSidebarSource).toContain('buildQmlLeftListDefectFilterOptions(defectDictData)')
    expect(operationSidebarSource).toContain('hasQmlLeftListVisibleDefectOptions(listDefectFilterOptions)')
    expect(operationSidebarSource).toContain('filterQmlCoilsByDefectClasses')
    expect(operationSidebarSource).toContain('aria-label="筛选"')
  })

  it('renders QML left-list row columns for id, grade, and defect status', () => {
    expect(operationSidebarSource).toContain('function formatQmlListCoilDefectStatus(coil: CoilData)')
    expect(operationSidebarSource).toContain('function buildQmlListCoilDefectTip(coil: CoilData)')
    expect(operationSidebarSource).toContain('className="coil-id"')
    expect(operationSidebarSource).toContain('{coil.id}')
    expect(operationSidebarSource).toContain('className="coil-grade"')
    expect(operationSidebarSource).toContain("{coil.grade ?? '--'}")
    expect(operationSidebarSource).toContain('className={`coil-defect-summary ${getQmlListCoilDefectLevelClass(coil)}`}')
    expect(operationSidebarSource).toContain('title={buildQmlListCoilDefectTip(coil)}')
    expect(operationSidebarSource).toContain('{formatQmlListCoilDefectStatus(coil)}')
  })

  it('renders the QML coil-check status underline on list row coil numbers', () => {
    expect(operationSidebarSource).toContain('getQmlCoilCheckStatusClass')
    expect(operationSidebarSource).toContain('className={`coil-no ${getQmlCoilCheckStatusClass(coil.raw)}`}')
  })

  it('uses QML StatusMsg content for the list status surface instead of a separate AntD row status', () => {
    expect(qmlDataListItemBaseSource).toContain('height: 25')
    expect(qmlDataListItemBaseSource).toContain('Rectangle{')
    expect(qmlDataListItemBaseSource).toContain('width: 3')
    expect(qmlDataListItemBaseSource).toContain('height: parent.height')
    expect(qmlDataListItemSource).toContain('StatusMsg{')

    const listRowsStart = operationSidebarSource.indexOf('filteredCoils.map((coil: CoilData) => (')
    const listRowsEnd = operationSidebarSource.indexOf('</Dropdown>', listRowsStart)
    const listRowsSource = operationSidebarSource.slice(listRowsStart, listRowsEnd)

    expect(listRowsStart).toBeGreaterThan(-1)
    expect(listRowsSource).not.toContain('<Tag')
    expect(listRowsSource).not.toContain('coil-status-label')
    expect(listRowsSource).not.toContain('statusText(coil.status)')
    expect(listRowsSource).toContain('className={`coil-defect-summary ${getQmlListCoilDefectLevelClass(coil)}`}')
    expect(listRowsSource).toContain('{formatQmlListCoilDefectStatus(coil)}')
    expect(operationSidebarCss).not.toContain('.sidebar-coil-item .coil-status-label')
    expect(operationSidebarCss).toContain('min-height: 25px;')
  })

  it('keeps left-list rows single-line like QML without an extra time row', () => {
    expect(qmlDataListItemBaseSource).toContain('height: 25')
    expect(qmlDataListItemSource).toContain('RowLayout{')
    expect(qmlDataListItemSource).not.toContain('TimeLabel')

    const listRowsStart = operationSidebarSource.indexOf('filteredCoils.map((coil: CoilData) => (')
    const listRowsEnd = operationSidebarSource.indexOf('</Dropdown>', listRowsStart)
    const listRowsSource = operationSidebarSource.slice(listRowsStart, listRowsEnd)

    expect(listRowsStart).toBeGreaterThan(-1)
    expect(listRowsSource).not.toContain('className="coil-time"')
    expect(listRowsSource).not.toContain('{coil.dateTime}')
    expect(operationSidebarCss).not.toContain('.sidebar-coil-item .coil-time')
  })

  it('uses QML fixed 25px delegate height for left-list rows', () => {
    expect(qmlDataListItemBaseSource).toContain('height: 25')

    const rowRuleStart = operationSidebarCss.indexOf('.sidebar-coil-item {')
    const rowRuleEnd = operationSidebarCss.indexOf('}', rowRuleStart)
    const rowRuleSource = operationSidebarCss.slice(rowRuleStart, rowRuleEnd)

    expect(rowRuleStart).toBeGreaterThan(-1)
    expect(rowRuleSource).toMatch(/\n\s+height: 25px;/)
    expect(rowRuleSource).toMatch(/\n\s+min-height: 25px;/)
    expect(rowRuleSource).toContain('padding: 0 8px;')
    expect(rowRuleSource).not.toContain('padding: 8px;')
    expect(operationSidebarCss).toContain('line-height: 1;')
  })

  it('renders the QML current-row left accent strip on coil list rows', () => {
    expect(operationSidebarSource).toContain('className="coil-current-accent"')
    expect(operationSidebarSource).toContain('aria-hidden="true"')
  })

  it('opens a QML DataListItemMenu-style context menu from each coil row', () => {
    expect(operationSidebarSource).toContain('Dropdown')
    expect(operationSidebarSource).toContain('const buildQmlDataListItemMenu = (coil: CoilData)')
    expect(operationSidebarSource).toContain('trigger={[\'contextMenu\']}')
    expect(operationSidebarSource).toContain("triggerSubMenuAction: 'click'")
    expect(operationSidebarSource).toContain("menu={{ items: buildQmlDataListItemMenu(coil), triggerSubMenuAction: 'click' }}")
  })

  it('keeps QML row-menu action labels available on the React row context menu', () => {
    expect(operationSidebarSource).toContain("label: '复制卷号'")
    expect(operationSidebarSource).toContain("label: '打开...'")
    expect(operationSidebarSource).toContain("label: '复制保存位置'")
    expect(operationSidebarSource).toContain("label: '复制...'")
    expect(operationSidebarSource).toContain("label: '工具'")
    expect(operationSidebarSource).toContain("label: '重新拼接AREA图像'")
    expect(operationSidebarSource).toContain("label: '重新检测该卷'")
    expect(operationSidebarSource).toContain("label: '全部重新识别'")
    expect(operationSidebarSource).toContain("label: '查看原始返回数据'")
  })

  it('marks row-menu judgment choices like QML SelectMenuItem', () => {
    expect(operationSidebarSource).toContain('const rowCoilCheckStatus = resolveQmlCoilCheckStatus(coil.raw)')
    expect(operationSidebarSource).toContain('buildQmlCoilCheckMenuLabel(option, rowCoilCheckStatus === option.status)')
    expect(operationSidebarSource).toContain("data-qml-selected={selected ? 'true' : 'false'}")
    expect(operationSidebarSource).toContain("'--qml-row-check-color': getQmlCoilCheckSelectColor(option.status)")
    expect(operationSidebarSource).not.toContain('onClick: () => void setCoilCheckStatus(coil, option.status)')
  })

  it('renders the QML ListTitleView column header above coil rows', () => {
    expect(operationSidebarSource).toContain('className="list-column-header"')
    expect(operationSidebarSource).toContain('<span>Id</span>')
    expect(operationSidebarSource).toContain('<span>卷号</span>')
    expect(operationSidebarSource).toContain('<span>钢种</span>')
    expect(operationSidebarSource).toContain('<span>缺陷/最严重</span>')
  })

  it('keeps QML list header and row columns aligned without a separate coil-status column', () => {
    const sharedGridStyle = 'style={{ gridTemplateColumns: QML_LIST_COLUMN_GRID }}'
    const listHeaderStart = operationSidebarSource.indexOf('<div className="list-column-header"')
    const listHeaderEnd = operationSidebarSource.indexOf('</div>', listHeaderStart)
    const listHeaderSource = operationSidebarSource.slice(listHeaderStart, listHeaderEnd)
    const listRowsStart = operationSidebarSource.indexOf('filteredCoils.map((coil: CoilData) => (')
    const listRowsEnd = operationSidebarSource.indexOf('</Dropdown>', listRowsStart)
    const listRowsSource = operationSidebarSource.slice(listRowsStart, listRowsEnd)

    expect(qmlListTitleViewSource).toContain('text: " 缺陷/最严重"')
    expect(qmlListTitleViewSource).not.toContain('状态')
    expect(qmlDataListItemSource).toContain('StatusMsg{')
    expect(operationSidebarSource).toContain(
      "const QML_LIST_COLUMN_GRID = '52px minmax(74px, 1.1fr) minmax(42px, 0.7fr) minmax(96px, 1.4fr)'",
    )
    expect(operationSidebarSource.split(sharedGridStyle).length - 1).toBe(2)
    expect(listHeaderSource).not.toContain('<span>状态</span>')
    expect(listRowsSource).not.toContain('coil-status-label')
    expect(listRowsSource).not.toContain('statusText(coil.status)')
    expect(operationSidebarCss).not.toContain('.sidebar-coil-item .coil-status-label')
  })

  it('keeps the QML list scroll container from narrowing row columns against the header', () => {
    expect(operationSidebarSource).toContain('<div className="sidebar-coil-list" style={{ paddingRight: 0 }}>')
  })

  it('places the QML list header inside the same scroll container as rows', () => {
    const listStart = operationSidebarSource.indexOf('<div className="sidebar-coil-list" style={{ paddingRight: 0 }}>')
    const headerAfterList = operationSidebarSource.indexOf('<div className="list-column-header"', listStart)
    const rowAfterHeader = operationSidebarSource.indexOf('<button', headerAfterList)

    expect(listStart).toBeGreaterThan(-1)
    expect(headerAfterList).toBeGreaterThan(listStart)
    expect(rowAfterHeader).toBeGreaterThan(headerAfterList)
  })

  it('keeps QML coil-number and serial-number search pages separate', () => {
    expect(operationSidebarSource).toContain("type SearchMode = 'coilNo' | 'date' | 'coilId'")
    expect(operationSidebarSource).toContain("const [searchMode, setSearchMode] = useState<SearchMode>('coilNo')")
    expect(operationSidebarSource).toContain("{ label: '卷号', value: 'coilNo' }")
    expect(operationSidebarSource).toContain("{ label: '时间', value: 'date' }")
    expect(operationSidebarSource).toContain("{ label: '流水号', value: 'coilId' }")
    expect(operationSidebarSource).toContain('resolveCoilSearch(keyword, searchMode)')
    expect(operationSidebarSource).not.toContain('卷号/ID')
  })

  it('mirrors the QML SearchView header ComboBox instead of an in-body Segmented switch', () => {
    const searchSectionSource = getSearchSectionSource()

    expect(qmlSearchViewSource).toContain('title: qsTr("     查询      ")')
    expect(qmlSearchViewSource).toContain('max_height: 95')
    expect(qmlSearchViewSource).toContain('max_height = [95,130,95][currentIndex]')
    expect(qmlSearchViewSource).toContain('content_head_tool:')
    expect(qmlSearchViewSource).toContain('ComboBox{')
    expect(operationSidebarSource).toContain('function getQmlSearchPanelHeight(mode: SearchMode)')
    expect(searchSectionSource).toContain('data-qml-search-panel-height={qmlSearchPanelHeight}')
    expect(searchSectionSource).toContain("'--qml-search-panel-height': `${qmlSearchPanelHeight}px`")
    expect(operationSidebarCss).toContain('height: var(--qml-search-panel-height);')
    expect(operationSidebarCss).toContain('min-height: var(--qml-search-panel-height);')
    expect(searchSectionSource).toContain('className="section-title search-title-row"')
    expect(searchSectionSource).toContain('<span>查询</span>')
    expect(searchSectionSource).toContain('data-qml-search-mode-combo')
    expect(searchSectionSource).toContain('<Select<SearchMode>')
    expect(searchSectionSource).not.toContain('查询 / 过滤')
    expect(searchSectionSource).not.toContain('<Segmented')
  })

  it('opens the QML SearchView FilterView from a header filter button', () => {
    const searchSectionSource = getSearchSectionSource()
    const searchFilterModalSource = getSearchFilterModalSource()

    expect(qmlSearchViewSource).toContain('ImageButton{')
    expect(qmlSearchViewSource).toContain('tipText:qsTr("筛选")')
    expect(qmlSearchViewSource).toContain('fliterView.open()')
    expect(qmlFilterViewSource).toContain('Popup {')
    expect(qmlFilterViewSource).toContain('width:350')
    expect(qmlFilterViewSource).toContain('height:400')
    expect(qmlFilterViewSource).toContain('text: qsTr("查询条件")')
    expect(qmlFilterViewSource).toContain('Item{')
    expect(qmlFilterViewSource).toContain('Layout.fillHeight:true')
    expect(qmlFilterViewSource).not.toContain('ComboBox')
    expect(qmlFilterViewSource).not.toContain('TextField')
    expect(qmlFilterViewSource).not.toContain('CheckBox')
    expect(qmlFilterViewSource).toContain('text: "   重置   "')
    expect(qmlFilterViewSource).toContain('Material.background: Material.color(Material.Green)')
    expect(qmlFilterViewSource).toContain('text: "   确认   "')
    expect(qmlFilterViewSource).toContain('Material.background: Material.color(Material.Blue)')
    expect(operationSidebarSource).toContain('const [searchFilterOpen, setSearchFilterOpen] = useState(false)')
    expect(searchSectionSource).toContain('data-qml-search-filter-button')
    expect(searchSectionSource).toContain('aria-label="筛选查询条件"')
    expect(searchSectionSource).toContain('onClick={() => setSearchFilterOpen(true)}')
    expect(searchFilterModalSource).toContain('data-qml-search-filter-popup')
    expect(searchFilterModalSource).toContain('查询条件')
    expect(searchFilterModalSource).toContain('className="search-filter-popup-body"')
    expect(searchFilterModalSource).not.toContain('search-filter-status-row')
    expect(searchFilterModalSource).not.toContain('全部状态')
    expect(searchFilterModalSource).not.toContain('<Select')
    expect(searchFilterModalSource).toContain('className="search-filter-reset"')
    expect(searchFilterModalSource).toContain('className="search-filter-confirm"')
    expect(operationSidebarCss).toContain('.search-filter-reset')
    expect(operationSidebarCss).toContain('background: #4caf50 !important;')
    expect(operationSidebarCss).toContain('.search-filter-confirm')
    expect(operationSidebarCss).toContain('background: #2196f3 !important;')
  })

  it('keeps the QML page search action distinct from the SearchView filter popup action', () => {
    const searchSectionSource = getSearchSectionSource()

    expect(qmlSearchByCoilNoSource).toContain('text: qsTr("查询")')
    expect(searchSectionSource).toContain('data-qml-search-text-submit')
    expect(searchSectionSource).toContain('data-qml-search-date-submit')
    expect(searchSectionSource).not.toContain('<Button size="small" icon={<FilterOutlined />} loading={isSearching} onClick={runBackendSearch} />')
  })

  it('does not render React-only status and icon search controls inside the QML SearchView card', () => {
    const searchSectionSource = getSearchSectionSource()

    expect(qmlSearchViewSource).not.toContain('全部状态')
    expect(qmlSearchViewSource).not.toContain('statusFilter')
    expect(qmlSearchViewSource).not.toContain('ReloadOutlined')
    expect(searchSectionSource).not.toContain('className="filter-row"')
    expect(searchSectionSource).not.toContain('全部状态')
    expect(searchSectionSource).not.toContain('statusFilter')
    expect(searchSectionSource).not.toContain('aria-label="执行查询"')
    expect(operationSidebarSource).not.toContain('const [statusFilter, setStatusFilter]')
    expect(operationSidebarCss).not.toContain('.filter-row')
  })

  it('renders QML text and date search pages with body labels and query buttons', () => {
    const searchSectionSource = getSearchSectionSource()

    expect(qmlSearchByCoilNoSource).toContain('text: qsTr("卷号:")')
    expect(qmlSearchByCoilNoSource).toContain('placeholderText : qsTr("请输入卷号")')
    expect(qmlSearchByCoilNoSource).toContain('text: qsTr("查询")')
    expect(qmlSearchByCoilNoSource).toContain('coreModel.searchByCoilNo(textField.text)')
    expect(qmlSearchByCoilIdSource).toContain('text: "流水号:"')
    expect(qmlSearchByCoilIdSource).toContain('placeholderText : "请输入流水号"')
    expect(qmlSearchByCoilIdSource).toContain('text: qsTr("查询")')
    expect(qmlSearchByCoilIdSource).toContain('coreModel.searchByCoilId(textField.text)')
    expect(qmlSearchByDataTimeSource).toContain('text: qsTr("查询")')
    expect(qmlSearchByDataTimeSource).toContain('coreModel.searchByCoilDateTime')

    expect(searchSectionSource).toContain('className="search-text-line"')
    expect(searchSectionSource).toContain('data-qml-search-text-line={searchMode}')
    expect(searchSectionSource).toContain('data-qml-search-text-label')
    expect(searchSectionSource).toContain("searchMode === 'coilId' ? '流水号:' : '卷号:'")
    expect(searchSectionSource).toContain('data-qml-search-text-submit')
    expect(searchSectionSource).toContain('className="search-text-submit"')
    expect(searchSectionSource).toContain('autoInsertSpace={false}')
    expect(searchSectionSource).toContain('className="search-date-action-row"')
    expect(searchSectionSource).toContain('data-qml-search-date-submit')
    expect(operationSidebarCss).toContain('.search-text-line')
    expect(operationSidebarCss).toContain('.search-text-submit')
    expect(operationSidebarCss).toContain('.search-date-action-row')
  })

  it('renders the QML time-search page as two start/end DateTimeSelectLineItem rows', () => {
    const searchSectionSource = getSearchSectionSource()

    expect(qmlSearchByDataTimeSource).toContain('DateTimeSelectLineItem{')
    expect(qmlSearchByDataTimeSource).toContain('title_:"起始:"')
    expect(qmlSearchByDataTimeSource).toContain('title_:"结束:"')
    expect(qmlDateTimeSelectLineItemSource).toContain('RowLayout {')
    expect(qmlDateTimeSelectLineItemSource).toContain('height: 20')
    expect(qmlDateTimeSelectLineItemSource).toContain('CheckRecTimeItem{')
    expect(qmlDateTimeSelectLineItemSource).toContain('TimeSelectPop{')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: root.dateTime_.fullYear')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: root.dateTime_.month')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: root.dateTime_.day')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: root.dateTime_.hour')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: root.dateTime_.minute')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: "年"')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: "月"')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: "日  "')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: "时"')
    expect(qmlDateTimeSelectLineItemSource).toContain('text: "分"')
    expect(operationSidebarSource).toContain("type SearchDatePart = 'year' | 'month' | 'day' | 'hour' | 'minute'")
    expect(operationSidebarSource).toContain('function formatSearchDatePart(date: Dayjs | null, part: SearchDatePart)')
    expect(searchSectionSource).toContain('data-qml-search-date-lines')
    expect(searchSectionSource).toContain('data-qml-search-date-line="start"')
    expect(searchSectionSource).toContain('data-qml-search-date-line="end"')
    expect(searchSectionSource).toContain('<span>起始:</span>')
    expect(searchSectionSource).toContain('<span>结束:</span>')
    expect(searchSectionSource).toContain('className="search-date-segments"')
    expect(searchSectionSource).toContain('data-qml-search-date-part="year"')
    expect(searchSectionSource).toContain('data-qml-search-date-part="month"')
    expect(searchSectionSource).toContain('data-qml-search-date-part="day"')
    expect(searchSectionSource).toContain('data-qml-search-date-part="hour"')
    expect(searchSectionSource).toContain('data-qml-search-date-part="minute"')
    expect(searchSectionSource).toContain('<span className="search-date-unit">年</span>')
    expect(searchSectionSource).toContain('<span className="search-date-unit">月</span>')
    expect(searchSectionSource).toContain('<span className="search-date-unit">日</span>')
    expect(searchSectionSource).toContain('<span className="search-date-unit">时</span>')
    expect(searchSectionSource).toContain('<span className="search-date-unit">分</span>')
    expect(operationSidebarSource).toContain('const SEARCH_DATE_PICKER_CLASS_NAMES = {')
    expect(operationSidebarSource).toContain("root: 'search-date-picker-popup'")
    expect(searchSectionSource).toContain('className="search-date-picker"')
    expect(searchSectionSource).toContain('classNames={SEARCH_DATE_PICKER_CLASS_NAMES}')
    expect(searchSectionSource).not.toContain('popupClassName=')
    expect(searchSectionSource).not.toContain('DatePicker.RangePicker')
    expect(searchSectionSource).not.toContain('className="date-range-picker"')
    expect(operationSidebarCss).toContain('.search-date-part')
    expect(operationSidebarCss).toContain('.search-date-picker-popup')
  })

  it('opens the QML latest coilList URL for the list data source action', () => {
    expect(operationSidebarSource).toContain('getApiRequestHistory')
    expect(operationSidebarSource).toContain('resolveQmlCoilListDataSourceUrl')
    expect(operationSidebarSource).toContain('buildCoilListDataSourceUrl(80, serviceBaseUrls.apiBaseUrl)')
  })

  it('uses a Tauri/native external opener for QML backend URL actions', () => {
    expect(operationSidebarSource).toContain('openQmlExternalUrl')
    expect(operationSidebarSource).toContain('void openQmlExternalUrl(coilApi.getSearchByCoilIdUrl(coil.id))')
    expect(operationSidebarSource).toContain('openCoilRawData(currentCoil)')
    expect(operationSidebarSource).toContain('const openCoilListDataSource = () =>')
    expect(operationSidebarSource.indexOf('resolveQmlCoilListDataSourceUrl')).toBeLessThan(
      operationSidebarSource.lastIndexOf('openQmlExternalUrl('),
    )
    expect(operationSidebarSource).not.toContain('window.open(')
  })

  it('uses the QML websocket route to receive pushed re-detection status', () => {
    expect(operationSidebarSource).toContain('buildReDetectionWsPath')
    expect(operationSidebarSource).toContain('resolveReDetectionWsUrl')
    expect(operationSidebarSource).toContain('parseReDetectionWebSocketMessage')
    expect(operationSidebarSource).toContain('new WebSocket(resolveReDetectionWsUrl')
    expect(operationSidebarSource).toContain('reDetectionWsStatus ?? reDetectionStatusData')
  })

  it('mirrors QML ReDetectionView WebSocket.Closed by entering connection error state', () => {
    const reDetectionEffectStart = operationSidebarSource.indexOf('new WebSocket(resolveReDetectionWsUrl')
    const openHandlerStart = operationSidebarSource.indexOf('socket.onopen = () =>', reDetectionEffectStart)
    const openHandlerEnd = operationSidebarSource.indexOf('socket.onmessage =', openHandlerStart)
    const openHandlerSource = operationSidebarSource.slice(openHandlerStart, openHandlerEnd)
    const closeHandlerStart = operationSidebarSource.indexOf('socket.onclose = () =>', reDetectionEffectStart)
    const closeHandlerEnd = operationSidebarSource.indexOf('return () =>', closeHandlerStart)
    const closeHandlerSource = operationSidebarSource.slice(closeHandlerStart, closeHandlerEnd)

    expect(openHandlerSource).toContain('setReDetectionWsStatus({})')
    expect(closeHandlerSource).toContain("setReDetectionWsStatus({ error: '连接断开!' })")
    expect(closeHandlerSource.indexOf('setReDetectionWsReady(false)')).toBeLessThan(
      closeHandlerSource.indexOf("setReDetectionWsStatus({ error: '连接断开!' })"),
    )
  })

  it('sends the QML websocket start payload before falling back to the HTTP start route', () => {
    expect(operationSidebarSource).toContain('buildReDetectionWebSocketStartMessage(reDetectionRange, reDetectionFolder)')
    expect(operationSidebarSource).toContain('socket.send')
    expect(operationSidebarSource.indexOf('socket.send')).toBeLessThan(
      operationSidebarSource.indexOf('runtimeApi.startReDetection'),
    )
  })

  it('mirrors QML ReDetectionStatus.strat by entering running state immediately on start', () => {
    const startReDetectionStart = operationSidebarSource.indexOf('const startReDetection = async () =>')
    const startReDetectionEnd = operationSidebarSource.indexOf('const reconnectReDetectionSocket = () =>', startReDetectionStart)
    const startReDetectionSource = operationSidebarSource.slice(startReDetectionStart, startReDetectionEnd)

    expect(startReDetectionSource).toContain('setReDetectionWsStatus({ running: true, progress: 0, total: 0, pending: 0 })')
    expect(startReDetectionSource.indexOf('setReDetectionWsStatus({ running: true')).toBeLessThan(
      startReDetectionSource.indexOf('socket.send(buildReDetectionWebSocketStartMessage'),
    )
    expect(startReDetectionSource.indexOf('setReDetectionWsStatus({ running: true')).toBeLessThan(
      startReDetectionSource.indexOf('runtimeApi.startReDetection'),
    )
  })

  it('mirrors QML ReDetectionStatus.setError when start fails after entering running state', () => {
    const startReDetectionStart = operationSidebarSource.indexOf('const startReDetection = async () =>')
    const startReDetectionEnd = operationSidebarSource.indexOf('const reconnectReDetectionSocket = () =>', startReDetectionStart)
    const startReDetectionSource = operationSidebarSource.slice(startReDetectionStart, startReDetectionEnd)

    expect(startReDetectionSource).toContain("setReDetectionWsStatus({ error: '重新识别启动失败' })")
    expect(startReDetectionSource.indexOf("setReDetectionWsStatus({ error: '重新识别启动失败' })")).toBeLessThan(
      startReDetectionSource.indexOf("message.error('重新识别启动失败')"),
    )
  })

  it('mirrors QML ReDetectionView shell, title row, and inline action layout', () => {
    expect(reDetectionQmlSource).toContain('width: 590')
    expect(reDetectionQmlSource).toContain('TitleLabel{')
    expect(reDetectionQmlSource).toContain('text: "重新识别"')
    expect(reDetectionQmlSource).toContain('color: Material.color(Material.Brown)')
    expect(reDetectionQmlSource).toContain('text: "重新连接"')
    expect(reDetectionQmlSource).toContain('visible:root.reDetectionStatus.isError')
    expect(reDetectionQmlSource).toContain('text: "识别"')
    expect(reDetectionQmlSource).toContain('visible: !root.reDetectionStatus.isError')

    const reDetectionModalSource = getReDetectionModalSource()

    expect(operationSidebarSource).not.toContain('title="重新识别"')
    expect(operationSidebarSource).toContain('width={590}')
    expect(reDetectionModalSource).toContain('footer={null}')
    expect(reDetectionModalSource).not.toContain('okText="识别"')
    expect(reDetectionModalSource).not.toContain('cancelText="关闭"')
    expect(reDetectionModalSource).toContain('data-qml-re-detection-view')
    expect(reDetectionModalSource).toContain('data-qml-re-detection-title')
    expect(reDetectionModalSource).toContain('className="re-detection-header"')
    expect(reDetectionModalSource).toContain('className="re-detection-action-row"')
    expect(reDetectionModalSource).toContain('className="re-detection-start-button"')
    expect(reDetectionModalSource).toContain('{!reDetectionStatus.error ? (')
    expect(reDetectionModalSource).toMatch(
      /<h3[\s\S]*data-qml-re-detection-title[\s\S]*重新识别[\s\S]*reDetectionStatus\.error \? \([\s\S]*重新连接/,
    )
    expect(reDetectionModalSource).toMatch(
      /<div className="re-detection-action-row"[\s\S]*<div className="re-detection-status">[\s\S]*<Button[\s\S]*className="re-detection-start-button"[\s\S]*识别/,
    )
    expect(operationSidebarCss).toContain('.re-detection-title')
    expect(operationSidebarCss).toContain('color: #795548')
    expect(operationSidebarCss).toContain('font-size: 25pt')
    expect(operationSidebarCss).toContain('.re-detection-action-row')
  })

  it('mirrors QML ReDetectionView error state by showing the error and hiding the 识别 action', () => {
    const reDetectionModalSource = getReDetectionModalSource()

    expect(operationSidebarSource).toContain('buildReDetectionStatusView')
    expect(operationSidebarSource).toContain('const reDetectionStatus = buildReDetectionStatusView(reDetectionStatusSource)')
    expect(reDetectionModalSource).toContain('reDetectionStatus.error')
    expect(reDetectionModalSource).toContain('className="re-detection-error"')
    expect(reDetectionModalSource).toContain('{!reDetectionStatus.error ? (')
    expect(reDetectionModalSource).toContain('className="re-detection-start-button"')
    expect(reDetectionModalSource).not.toContain('okButtonProps={reDetectionOkButtonProps}')
  })

  it('mirrors QML ReDetectionView error reconnect action by rebuilding the websocket', () => {
    const reDetectionModalSource = getReDetectionModalSource()

    expect(operationSidebarSource).toContain('const [reDetectionReconnectSerial, setReDetectionReconnectSerial] = useState(0)')
    expect(operationSidebarSource).toContain('const reconnectReDetectionSocket = () =>')
    expect(operationSidebarSource).toContain('setReDetectionReconnectSerial((serial) => serial + 1)')
    expect(operationSidebarSource).toContain('}, [reDetectionOpen, reDetectionReconnectSerial])')
    expect(reDetectionModalSource).toContain('<Button size="small" onClick={reconnectReDetectionSocket}>')
    expect(reDetectionModalSource).toContain('重新连接')
  })

  it('mirrors QML ReDetectionView idle and canChange behavior for range inputs and status rows', () => {
    const reDetectionModalSource = getReDetectionModalSource()

    expect(reDetectionModalSource).toContain('disabled={!reDetectionStatus.canChange}')
    expect(reDetectionModalSource).toContain('reDetectionStatus.showProgress ?')
    expect(reDetectionModalSource).toContain('<Progress percent={reDetectionStatus.percent}')
    expect(reDetectionModalSource).toMatch(/reDetectionStatus\.showProgress \? \([\s\S]*<Progress[\s\S]*\) : \(\s*null/)
  })

  it('styles the QML ReDetectionView ErrorLabel equivalent locally in the sidebar modal', () => {
    expect(operationSidebarCss).toContain('.re-detection-error')
    expect(operationSidebarCss).toContain('color: #ff9b9b')
    expect(operationSidebarCss).toContain('font-weight: 600')
  })

  it('uses live image-service health for the sidebar alarm row instead of a static pending label', () => {
    expect(operationSidebarSource).toContain('buildOperationSidebarAlarmRows')
    expect(operationSidebarSource).toContain('imageServiceHealthOk')
    expect(operationSidebarSource).toContain("joinBaseUrl(imageServiceBaseUrl, '/health')")
    expect(operationSidebarSource).toContain("alarmRows.map((row) =>")
    expect(operationSidebarSource).not.toContain('<div className="alarm-item warn">图像服务待确认</div>')
  })

  it('renders the QML left FootView API url, delay, and keepLatest footer', () => {
    expect(operationSidebarSource).toContain("queryKey: ['operationSidebar', 'apiDelay']")
    expect(operationSidebarSource).toContain('await systemApi.getDelay()')
    expect(operationSidebarSource).toContain('const sidebarApiDelayView = buildApiDelayView(')
    expect(operationSidebarSource).toContain(
      "const sidebarApiDelayText = sidebarApiDelayView.label.startsWith('API ')",
    )
    expect(operationSidebarSource).toContain('data-qml-left-foot-view')
    expect(operationSidebarSource).toContain('data-qml-api-url={serviceBaseUrls.apiBaseUrl}')
    expect(operationSidebarSource).toContain('{serviceBaseUrls.apiBaseUrl}')
    expect(operationSidebarSource).toContain('延时：')
    expect(operationSidebarSource).toContain('{sidebarApiDelayText}')
    expect(operationSidebarSource).toContain('data-qml-footer-keep-latest')
    expect(operationSidebarSource).toContain('checked={keepLatest}')
    expect(operationSidebarSource).toContain('onChange={(event) => changeKeepLatest(event.target.checked)}')
  })

  it('opens the QML ConnectDialog from the left FootView API url', () => {
    const footerStart = operationSidebarSource.indexOf('<footer')
    const footerEnd = operationSidebarSource.indexOf('</footer>', footerStart)
    const footerSource = operationSidebarSource.slice(footerStart, footerEnd)
    const apiUrlRuleStart = operationSidebarCss.indexOf('.sidebar-foot-api-url {')
    const apiUrlRuleEnd = operationSidebarCss.indexOf('}', apiUrlRuleStart)
    const apiUrlRuleSource = operationSidebarCss.slice(apiUrlRuleStart, apiUrlRuleEnd)

    expect(qmlFootViewSource).toContain('ItemDelegate{')
    expect(qmlFootViewSource).toContain('popManage.popupConnectDialog()')
    expect(operationSidebarSource).toContain('interface OperationSidebarProps')
    expect(operationSidebarSource).toContain('onOpenConnectSettings: () => void')
    expect(operationSidebarSource).toContain('export default function OperationSidebar({ onOpenConnectSettings }')
    expect(footerSource).toContain('data-qml-footer-connect-server-url')
    expect(footerSource).toContain('type="button"')
    expect(footerSource).toContain('onClick={onOpenConnectSettings}')
    expect(apiUrlRuleSource).toContain('border: 0;')
    expect(apiUrlRuleSource).toContain('background: transparent;')
    expect(apiUrlRuleSource).toContain('padding: 0;')
    expect(apiUrlRuleSource).toContain('cursor: pointer;')
  })

  it('keeps the QML left FootView fixed at 25px tall', () => {
    const footerRuleStart = operationSidebarCss.indexOf('.sidebar-foot-view {')
    const footerRuleEnd = operationSidebarCss.indexOf('}', footerRuleStart)
    const footerRuleSource = operationSidebarCss.slice(footerRuleStart, footerRuleEnd)

    expect(qmlFootViewSource).toContain('height: 25')
    expect(qmlFootViewSource).toContain('CheckDelegate{')
    expect(footerRuleStart).toBeGreaterThan(-1)
    expect(footerRuleSource).toMatch(/\n\s+height: 25px;/)
    expect(footerRuleSource).toContain('min-height: 25px;')
    expect(footerRuleSource).toContain('box-sizing: border-box;')
    expect(footerRuleSource).toContain('padding: 0 7px;')
    expect(footerRuleSource).not.toContain('padding: 4px 7px;')
  })
})
