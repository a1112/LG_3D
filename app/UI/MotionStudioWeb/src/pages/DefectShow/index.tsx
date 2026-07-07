import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Checkbox, Dropdown, Empty, Image, Input, InputNumber, Modal, Radio, Select, Space, Spin, Tag, message } from 'antd'
import type { MenuProps } from 'antd'
import {
  AimOutlined,
  BugOutlined,
  CheckSquareOutlined,
  CloseSquareOutlined,
  DeleteOutlined,
  EditOutlined,
  ExportOutlined,
  FilterOutlined,
  FolderOpenOutlined,
  FullscreenOutlined,
  PictureOutlined,
  PlusOutlined,
  ReloadOutlined,
  SelectOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import TileImageViewer from '@/components/TileImageViewer'
import type { Rect } from '@/components/TileImageViewer/utils'
import {
  defectApi,
  defectConfigApi,
  imageApi,
  resolveImageRuntimeBaseUrl,
  resolveQmlSurfaceImageUrl,
  systemApi,
} from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import { useUiSettingsStore } from '@/stores/uiSettingsStore'
import type { DefectData } from '@/types'
import {
  buildDefectClassFilterOptions,
  countDefectsByClass,
  filterDefectsByClass,
  getQmlSelectAllDefectClasses,
  getQmlVisibleFilterOptions,
  getResetDefectClassSelection,
  reconcileQmlDefectClassSelection,
} from '@/utils/defectFilter'
import {
  DEFECT_DATA_MODE_OPTIONS,
  buildDefectDataQueryKey,
  fetchDefectsByMode,
  getDefectListRange,
  type DefectDataMode,
} from '@/utils/defectDataMode'
import { buildDefectImageFolderUrl, findDefectNavigationTarget } from '@/utils/defectNavigation'
import { openCoilSaveFolderUrl } from '@/utils/coilActions'
import {
  buildManualDefectAddPayload,
  buildManualDefectExportPayload,
  buildManualDefectUpdatePayload,
  canEditManualDefect,
  formatManualDefectExportError,
  formatManualDefectExportResult,
  getManualDefectExportCounts,
  getManualDefectFormValues,
  type ManualDefectExportScope,
  type ManualDefectFormValues,
} from '@/utils/manualDefect'
import { getNativeDefaultPicturesDirectory, selectNativeDirectory } from '@/utils/nativeDialogs'
import './DefectShow.css'

function DefectShowPage() {
  const navigate = useNavigate()
  const {
    currentCoil,
    coilList,
    currentCoilList,
    surfaceKey,
    setCurrentCoil,
    setSurfaceKey,
    setPendingDefect,
  } = useCoilStore()
  const showTileDebugBorders = useUiSettingsStore((state) => state.showTileDebugBorders)
  const showDefectLabels = useUiSettingsStore((state) => state.showDefectLabels)
  const defaultAreaTileCount = useUiSettingsStore((state) => state.defaultAreaTileCount)
  const enable1024CacheMode = useUiSettingsStore((state) => state.enable1024CacheMode)
  const useRustImageServer = useUiSettingsStore((state) => state.useRustImageServer)
  const rustImageServerPort = useUiSettingsStore((state) => state.rustImageServerPort)
  const useSharedFolder = useUiSettingsStore((state) => state.useSharedFolder)
  const sharedFolderBaseName = useUiSettingsStore((state) => state.sharedFolderBaseName)
  const showAlarmDefectClasses = useUiSettingsStore((state) => state.showAlarmDefectClasses)
  const setShowAlarmDefectClasses = useUiSettingsStore((state) => state.setShowAlarmDefectClasses)
  const [selectedDefectId, setSelectedDefectId] = useState<number | null>(null)
  const [tooltipDefectId, setTooltipDefectId] = useState<number | null>(null)
  const [selectedDefectClasses, setSelectedDefectClasses] = useState<string[]>([])
  const hasInitializedDefectClassSelectionRef = useRef(false)
  const [defectDataMode, setDefectDataMode] = useState<DefectDataMode>('range')
  const [manualDefectAddMode, setManualDefectAddMode] = useState(false)
  const [manualDefectAddOpen, setManualDefectAddOpen] = useState(false)
  const [manualDefectAddSaving, setManualDefectAddSaving] = useState(false)
  const [manualDefectAddRect, setManualDefectAddRect] = useState<Rect | null>(null)
  const [manualDefectAddForm, setManualDefectAddForm] = useState({ defectName: '', remark: '' })
  const [manualDefectEditOpen, setManualDefectEditOpen] = useState(false)
  const [manualDefectSaving, setManualDefectSaving] = useState(false)
  const [manualDefectExportOpen, setManualDefectExportOpen] = useState(false)
  const [manualDefectExporting, setManualDefectExporting] = useState(false)
  const [manualDefectProgressOpen, setManualDefectProgressOpen] = useState(false)
  const [manualDefectExportPath, setManualDefectExportPath] = useState('')
  const [manualDefectDefaultExportDirectory, setManualDefectDefaultExportDirectory] = useState<string | null>(null)
  const [manualDefectExportScope, setManualDefectExportScope] = useState<ManualDefectExportScope>('all')
  const [manualDefectExportOptions, setManualDefectExportOptions] = useState({
    groupByCategory: true,
    includeInfo: true,
    highQuality: false,
  })
  const [manualDefectForm, setManualDefectForm] = useState<ManualDefectFormValues>({
    defectName: '',
    defectX: 0,
    defectY: 0,
    defectW: 100,
    defectH: 100,
    remark: '',
  })
  const qmlCurrentCoilList = currentCoilList.length > 0 ? currentCoilList : coilList
  const defectListRange = useMemo(() => getDefectListRange(qmlCurrentCoilList), [qmlCurrentCoilList])

  const { data: defectsData, isLoading, refetch: refetchDefects } = useQuery({
    queryKey: buildDefectDataQueryKey(defectDataMode, currentCoil?.id, surfaceKey, defectListRange),
    queryFn: () => fetchDefectsByMode(defectDataMode, defectApi, currentCoil?.id || 0, surfaceKey, defectListRange),
    enabled: defectDataMode === 'range' ? defectListRange.startId > 0 : !!currentCoil,
  })

  const { data: defectDictData } = useQuery({
    queryKey: ['defect-dict'],
    queryFn: defectConfigApi.getDefectDict,
  })
  const { data: infoData } = useQuery({
    queryKey: ['system', 'info'],
    queryFn: systemApi.getInfo,
    staleTime: 60_000,
    retry: 1,
  })

  const defects = defectsData?.data ?? []
  const filterOptions = useMemo(
    () => buildDefectClassFilterOptions(defectDictData, defects),
    [defectDictData, defects],
  )
  const defectClassCounts = useMemo(() => countDefectsByClass(filterOptions, defects), [filterOptions, defects])
  const visibleFilterOptions = useMemo(
    () => getQmlVisibleFilterOptions(filterOptions, { includeHidden: showAlarmDefectClasses }),
    [filterOptions, showAlarmDefectClasses],
  )
  const filteredDefects = useMemo(
    () => (filterOptions.length > 0 ? filterDefectsByClass(defects, selectedDefectClasses) : defects),
    [defects, filterOptions.length, selectedDefectClasses],
  )
  const selectedDefect = useMemo(
    () => filteredDefects.find((defect) => defect.id === selectedDefectId) ?? filteredDefects[0] ?? null,
    [filteredDefects, selectedDefectId],
  )
  const defectListToolBoxRange = useMemo(() => {
    if (defectDataMode === 'range') return defectListRange

    const activeCoilId = selectedDefect?.coilId || currentCoil?.id || 0
    return { startId: activeCoilId, endId: activeCoilId }
  }, [currentCoil?.id, defectDataMode, defectListRange, selectedDefect?.coilId])
  const exportDefects = useMemo(
    () =>
      defects.map((defect) => ({
        ...defect,
        raw: {
          ...(defect.raw ?? {}),
          selected: defect.id === selectedDefectId,
        },
      })),
    [defects, selectedDefectId],
  )
  const manualDefectExportCounts = useMemo(() => getManualDefectExportCounts(exportDefects), [exportDefects])
  const readCurrentCoilRawValue = (keys: string[], fallback = '--') => {
    const raw = currentCoil?.raw ?? {}

    for (const key of keys) {
      const value = raw[key]
      if (value !== undefined && value !== null && value !== '') return String(value)
    }

    return fallback
  }
  const qmlDefectInfoRows = useMemo(
    () => [
      { label: '缺陷数量', value: readCurrentCoilRawValue(['coilId', 'CoilId'], String(currentCoil?.id ?? '--')) },
      { label: '卷数', value: readCurrentCoilRawValue(['nextInfo', 'NextInfo']) },
      { label: '识别率', value: currentCoil?.coilNo ?? '--' },
      { label: '卷识别率', value: readCurrentCoilRawValue(['coilType', 'CoilType']) },
    ],
    [currentCoil],
  )

  useEffect(() => {
    if (filterOptions.length === 0) return

    setSelectedDefectClasses((previous) => {
      const nextSelection = reconcileQmlDefectClassSelection(filterOptions, previous, {
        includeHidden: showAlarmDefectClasses,
        preserveEmpty: hasInitializedDefectClassSelectionRef.current,
      })
      hasInitializedDefectClassSelectionRef.current = true
      return nextSelection
    })
  }, [filterOptions, showAlarmDefectClasses])

  useEffect(() => {
    if (selectedDefectId !== null && !filteredDefects.some((defect) => defect.id === selectedDefectId)) {
      setSelectedDefectId(null)
    }
  }, [filteredDefects, selectedDefectId])

  useEffect(() => {
    if (manualDefectEditOpen && selectedDefect) {
      setManualDefectForm(getManualDefectFormValues(selectedDefect))
    }
  }, [manualDefectEditOpen, selectedDefect])

  useEffect(() => {
    let cancelled = false

    void getNativeDefaultPicturesDirectory().then((defaultDirectory) => {
      if (!cancelled) {
        setManualDefectDefaultExportDirectory(defaultDirectory)
      }
    })

    return () => {
      cancelled = true
    }
  }, [])

  const activeImageCoilId = selectedDefect?.coilId || currentCoil?.id || 0
  const activeImageSurfaceKey = selectedDefect?.surface ?? surfaceKey
  const imageRuntimeSettings = {
    useRustImageServer,
    rustImageServerPort,
    useSharedFolder,
    sharedFolderBaseName,
  }
  const imageBaseUrl = resolveImageRuntimeBaseUrl(imageRuntimeSettings)
  const areaUrl = activeImageCoilId
    ? resolveQmlSurfaceImageUrl(
        imageRuntimeSettings,
        activeImageSurfaceKey,
        activeImageCoilId,
        'AREA',
        false,
        imageBaseUrl,
      )
    : ''
  const previewUrl = activeImageCoilId
    ? resolveQmlSurfaceImageUrl(
        imageRuntimeSettings,
        activeImageSurfaceKey,
        activeImageCoilId,
        'AREA',
        true,
        imageBaseUrl,
      )
    : ''

  const defectImageUrl =
    activeImageCoilId && selectedDefect
      ? imageApi.getDefectImage(
          activeImageSurfaceKey,
          activeImageCoilId,
          'AREA',
          selectedDefect.position.x,
          selectedDefect.position.y,
          selectedDefect.size.width,
          selectedDefect.size.height,
          imageBaseUrl,
        )
      : ''

  const getDefectLevelText = (defect: DefectData) => {
    const level =
      defect.level ??
      defect.raw?.defectLevel ??
      defect.raw?.DefectLevel ??
      defect.raw?.level ??
      defect.raw?.Level

    return level === undefined || level === null || level === '' ? '--' : String(level)
  }

  const getDefectItemColor = (defect: DefectData) => {
    const raw = defect.raw ?? {}
    const colorName =
      raw.configDefectName ||
      raw.ConfigDefectName ||
      raw.defectName ||
      raw.DefectName ||
      defect.defectType

    return filterOptions.find((option) => option.name === colorName)?.color ?? '#FFF'
  }

  const getDefectThumbnailUrl = (defect: DefectData) =>
    imageApi.getDefectImage(
      defect.surface,
      defect.coilId,
      'AREA',
      defect.position.x,
      defect.position.y,
      defect.size.width,
      defect.size.height,
      imageBaseUrl,
    )

  const formatDefectItemTitle = (defect: DefectData) =>
    [
      defect.defectType,
      `Coil ID: ${defect.coilId}`,
      `Surface: ${defect.surface}`,
      `Level: ${getDefectLevelText(defect)}`,
      `Position: (${defect.position.x}, ${defect.position.y})`,
      `Size: ${defect.size.width} x ${defect.size.height}`,
    ].join('\n')

  const renderDefectItemTooltip = (defect: DefectData) => (
    <div className="defect-item-tooltip-content">
      <strong className="defect-item-tooltip-name">{defect.defectType}</strong>
      <span>Coil ID: {defect.coilId}</span>
      <span>Surface: {defect.surface}</span>
      <span>Level: {getDefectLevelText(defect)}</span>
      <span>
        Position: ({defect.position.x}, {defect.position.y})
      </span>
      <span>
        Size: {defect.size.width} x {defect.size.height}
      </span>
    </div>
  )

  const handleDefectSelect = (defect: DefectData | null) => {
    setSelectedDefectId(defect?.id ?? null)
  }

  const selectAllDefectClasses = () => {
    setSelectedDefectClasses(getQmlSelectAllDefectClasses(filterOptions, { includeHidden: showAlarmDefectClasses }))
  }

  const clearDefectClasses = () => {
    setSelectedDefectClasses([])
  }

  const toggleDefectClass = (className: string, checked: boolean) => {
    setSelectedDefectClasses((current) => {
      if (checked) return current.includes(className) ? current : [...current, className]
      return current.filter((name) => name !== className)
    })
  }

  const resetDefectClasses = () => {
    setSelectedDefectClasses(getResetDefectClassSelection(filterOptions))
  }

  const changeAlarmDefectClassVisibility = (checked: boolean) => {
    setShowAlarmDefectClasses(checked)
  }

  const switchToDefectImage = (defect: DefectData | null) => {
    const target = findDefectNavigationTarget(defect, {
      currentCoil,
      coilList,
      currentCoilList: qmlCurrentCoilList,
      realtimeCoilList: coilList,
    })
    if (!target) return

    setCurrentCoil(target.coil)
    setSurfaceKey(target.surfaceKey)
    setPendingDefect(target.pendingDefect)
    navigate('/data')
  }

  const switchToSelectedDefectImage = () => {
    switchToDefectImage(selectedDefect)
  }

  const openDefectImageFolder = (defect: DefectData | null) => {
    const url = buildDefectImageFolderUrl(defect, {
      info: infoData,
      serverHost: window.location.hostname,
      sharedFolderBaseName,
    })
    if (!url) return

    void openCoilSaveFolderUrl(url)
  }

  const openSelectedDefectImageFolder = () => {
    openDefectImageFolder(selectedDefect)
  }

  const updateManualDefectForm = (key: keyof ManualDefectFormValues, value: string | number | null) => {
    setManualDefectForm((current) => ({
      ...current,
      [key]: typeof current[key] === 'number' ? Number(value ?? 0) : String(value ?? ''),
    }))
  }

  const handleManualDefectAnnotation = (rect: Rect) => {
    const defaultDefectName = filterOptions.find((option) => option.show)?.name ?? filterOptions[0]?.name ?? ''
    setManualDefectAddRect(rect)
    setManualDefectAddForm({ defectName: defaultDefectName, remark: '' })
    setManualDefectAddMode(false)
    setManualDefectAddOpen(true)
  }

  const cancelManualDefectAdd = () => {
    setManualDefectAddOpen(false)
    setManualDefectAddRect(null)
  }

  const saveNewManualDefect = async () => {
    if (!manualDefectAddRect || !activeImageCoilId) return

    setManualDefectAddSaving(true)
    try {
      await defectApi.addManualDefect(
        buildManualDefectAddPayload({
          coilId: activeImageCoilId,
          surfaceKey: activeImageSurfaceKey,
          rect: manualDefectAddRect,
          defectName: manualDefectAddForm.defectName,
          remark: manualDefectAddForm.remark,
        }),
      )
      message.success('缺陷标注已添加')
      setManualDefectAddOpen(false)
      setManualDefectAddRect(null)
      if (defectDataMode === 'all' || defectDataMode === 'manual') {
        refetchDefects()
      } else {
        setDefectDataMode('all')
      }
    } catch {
      message.error('缺陷标注添加失败')
    } finally {
      setManualDefectAddSaving(false)
    }
  }

  const saveManualDefect = async () => {
    if (!selectedDefect || !canEditManualDefect(selectedDefect)) return

    setManualDefectSaving(true)
    try {
      await defectApi.updateManualDefect(selectedDefect.id, { ...buildManualDefectUpdatePayload(manualDefectForm) })
      message.success('缺陷标注已保存')
      setManualDefectEditOpen(false)
      refetchDefects()
    } catch {
      message.error('缺陷标注保存失败')
    } finally {
      setManualDefectSaving(false)
    }
  }

  const deleteManualDefect = async () => {
    if (!selectedDefect || !canEditManualDefect(selectedDefect)) return

    setManualDefectSaving(true)
    try {
      await defectApi.deleteManualDefect(selectedDefect.id)
      message.success('缺陷标注已删除')
      setSelectedDefectId(null)
      setManualDefectEditOpen(false)
      refetchDefects()
    } catch {
      message.error('缺陷标注删除失败')
    } finally {
      setManualDefectSaving(false)
    }
  }

  const confirmDeleteManualDefect = () => {
    if (!selectedDefect || !canEditManualDefect(selectedDefect)) return

    Modal.confirm({
      title: '确认删除',
      content: '确定要删除此缺陷标注吗？\n此操作无法撤销。',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: deleteManualDefect,
    })
  }

  const chooseManualDefectExportPath = async () => {
    const selectedPath = await selectNativeDirectory({
      defaultDirectory: manualDefectDefaultExportDirectory,
    })
    if (selectedPath) {
      setManualDefectExportPath(selectedPath)
    }
  }

  const exportManualDefects = async () => {
    if (!manualDefectExportPath.trim()) {
      message.warning('请选择导出目录')
      return
    }

    setManualDefectExporting(true)
    setManualDefectProgressOpen(true)
    try {
      const result = await defectApi.exportManualDefects(
        buildManualDefectExportPayload(
          exportDefects,
          manualDefectExportPath.trim(),
          manualDefectExportScope,
          manualDefectExportOptions,
        ),
      )
      Modal.info({
        title: '导出完成',
        okText: '确定',
        content: <pre className="manual-defect-export-result">{formatManualDefectExportResult(result as Record<string, number>)}</pre>,
      })
    } catch (error) {
      Modal.error({
        title: '导出失败',
        okText: '确定',
        content: <pre className="manual-defect-export-result">{formatManualDefectExportError(error)}</pre>,
      })
    } finally {
      setManualDefectProgressOpen(false)
      setManualDefectExporting(false)
    }
  }

  const canSwitchToImage = Boolean(
    findDefectNavigationTarget(selectedDefect, {
      currentCoil,
      coilList,
      currentCoilList: qmlCurrentCoilList,
      realtimeCoilList: coilList,
    }),
  )
  const canOpenImageFolder = Boolean(selectedDefect)
  const canEditSelectedManualDefect = canEditManualDefect(selectedDefect)
  const canExportManualDefects =
    manualDefectExportScope === 'selected' ? manualDefectExportCounts.selected > 0 : manualDefectExportCounts.total > 0

  const buildQmlDefectDataViewMenu = (defect: DefectData): MenuProps['items'] => [
    {
      key: `correct-${defect.id}`,
      label: '纠正',
      children: [
        {
          key: `correct-empty-${defect.id}`,
          label: '',
        },
      ],
    },
    {
      key: `switch-to-image-${defect.id}`,
      label: '切换到图像',
      disabled: !findDefectNavigationTarget(defect, {
        currentCoil,
        coilList,
        currentCoilList: qmlCurrentCoilList,
        realtimeCoilList: coilList,
      }),
      onClick: () => {
        setSelectedDefectId(defect.id)
        switchToDefectImage(defect)
      },
    },
    {
      key: `open-image-folder-${defect.id}`,
      label: '打开图像位置',
      onClick: () => {
        setSelectedDefectId(defect.id)
        openDefectImageFolder(defect)
      },
    },
  ]

  return (
    <div className="defect-show-page">
      <div className="defect-toolbar">
        <div className="defect-toolbar-tabbar" data-qml-defect-head-toolbox data-qml-defect-global-view-index={0}>
          <Button size="small" type="primary">
            缺陷列表
          </Button>
        </div>
        <div className="toolbar-title defect-toolbar-title-center">
          <BugOutlined />
          <span>缺陷数据分析</span>
          <Tag color="red">
            {filteredDefects.length}/{defects.length} 项
          </Tag>
          {defectDataMode === 'range' ? (
            <Tag className="defect-range-tag">
              {defectListRange.startId} — {defectListRange.endId}
            </Tag>
          ) : null}
        </div>
        <Space className="defect-toolbar-actions" size={8} wrap>
          <Checkbox
            className="defect-alarm-class-toggle"
            checked={showAlarmDefectClasses}
            onChange={(event) => changeAlarmDefectClassVisibility(event.target.checked)}
          >
            显示报警类别
          </Checkbox>
          <Select
            className="defect-data-mode"
            size="small"
            value={defectDataMode}
            onChange={setDefectDataMode}
            options={DEFECT_DATA_MODE_OPTIONS}
          />
          <Select
            className="defect-class-filter"
            mode="multiple"
            allowClear
            maxTagCount="responsive"
            size="small"
            placeholder="缺陷类别"
            value={selectedDefectClasses}
            onChange={setSelectedDefectClasses}
            suffixIcon={<FilterOutlined />}
            options={visibleFilterOptions.map((option) => ({
              value: option.name,
              label: (
                <span className="defect-class-option">
                  <span className="defect-class-swatch" style={{ backgroundColor: option.color ?? '#7ad7ec' }} />
                  {option.name}
                  <span className="defect-class-count">({defectClassCounts[option.name] ?? 0})</span>
                  {!option.show ? <Tag color="default">隐藏</Tag> : null}
                </span>
              ),
            }))}
          />
          <Button size="small" icon={<CheckSquareOutlined />} onClick={selectAllDefectClasses}>
            全选
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={resetDefectClasses}>
            重置
          </Button>
          <Button size="small" icon={<CloseSquareOutlined />} onClick={clearDefectClasses}>
            取消
          </Button>
          <Button
            size="small"
            type={manualDefectAddMode ? 'primary' : 'default'}
            icon={<PlusOutlined />}
            disabled={!activeImageCoilId}
            onClick={() => setManualDefectAddMode((enabled) => !enabled)}
          >
            新增标注
          </Button>
          <Button
            size="small"
            icon={<ExportOutlined />}
            disabled={exportDefects.length === 0}
            onClick={() => setManualDefectExportOpen(true)}
          >
            导出
          </Button>
          <Button
            className="defect-toolbar-refresh"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => void refetchDefects()}
          >
            刷新
          </Button>
          <Select
            size="small"
            value={surfaceKey}
            onChange={setSurfaceKey}
            options={[
              { value: 'S', label: 'S 面' },
              { value: 'L', label: 'L 面' },
            ]}
          />
        </Space>
      </div>

      <section className="defect-qml-info-panel" aria-label="缺陷数据概览">
        {qmlDefectInfoRows.map((row) => (
          <div className="defect-qml-info-item" key={row.label}>
            <span className="defect-qml-info-label">{row.label}:</span>
            <strong>{row.value}</strong>
          </div>
        ))}
      </section>

      <section className="defect-class-summary-panel">
        <div className="panel-title defect-class-summary-title">
          缺陷总计
        </div>
        <div className="defect-class-summary-body">
          <div className="defect-class-summary-flow">
            {visibleFilterOptions.length === 0 ? (
              <span className="defect-class-summary-empty">暂无缺陷类别</span>
            ) : (
              visibleFilterOptions.map((option) => (
                <Checkbox
                  key={option.name}
                  className={`defect-class-summary-item ${
                    selectedDefectClasses.includes(option.name) ? 'selected' : ''
                  }`}
                  style={{ '--defect-class-color': option.color ?? '#00000000' } as CSSProperties}
                  checked={selectedDefectClasses.includes(option.name)}
                  onChange={(event) => toggleDefectClass(option.name, event.target.checked)}
                >
                  <span className="defect-class-summary-content">
                    <span className="defect-class-summary-name">{option.name}</span>
                    <span className="defect-class-count">({defectClassCounts[option.name] ?? 0})</span>
                    {!option.show ? <Tag color="default">隐藏</Tag> : null}
                  </span>
                </Checkbox>
              ))
            )}
            <div className="defect-class-summary-actions">
              <Checkbox
                className="defect-class-summary-include-background"
                checked={showAlarmDefectClasses}
                onChange={(event) => changeAlarmDefectClassVisibility(event.target.checked)}
              >
                包括背景
              </Checkbox>
              <span className="defect-class-summary-spacer" />
              <Button size="small" onClick={resetDefectClasses}>
                重置
              </Button>
              <Button size="small" onClick={selectAllDefectClasses}>
                全选
              </Button>
              <Button size="small" onClick={clearDefectClasses}>
                取消
              </Button>
            </div>
          </div>
        </div>
      </section>

      <div className={`defect-content ${tooltipDefectId != null ? 'tooltip-active' : ''}`}>
        <section className="defect-list-panel">
          <div className="panel-title defect-list-title">
            <span className="defect-list-heading">
              <AimOutlined />
              缺陷列表
            </span>
            <span className="defect-list-qml-toolbar">
              <span>{defectListToolBoxRange.startId}</span>
              <span>— {defectListToolBoxRange.endId}</span>
              <span>NUM: {filteredDefects.length}</span>
              <Button
                className="defect-list-fullscreen"
                type="text"
                size="small"
                icon={<FullscreenOutlined />}
                aria-label="缺陷列表全屏"
              />
            </span>
          </div>
          <div className="defect-list-container">
            {!currentCoil ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择卷材" />
            ) : isLoading ? (
              <div className="loading-container">
                <Spin />
              </div>
            ) : defects.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无缺陷数据" />
            ) : filteredDefects.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前筛选无缺陷" />
            ) : (
              filteredDefects.map((defect) => (
                <Dropdown
                  key={defect.id}
                  trigger={['contextMenu']}
                  menu={{ items: buildQmlDefectDataViewMenu(defect), triggerSubMenuAction: 'click' }}
                >
                  <button
                    type="button"
                    className={`defect-item ${selectedDefect?.id === defect.id ? 'selected' : ''} ${
                      tooltipDefectId === defect.id ? 'tooltip-open' : ''
                    }`}
                    style={{ '--defect-item-color': getDefectItemColor(defect) } as CSSProperties}
                    title={formatDefectItemTitle(defect)}
                    onMouseEnter={() => {
                      setSelectedDefectId(defect.id)
                      setTooltipDefectId(defect.id)
                    }}
                    onMouseLeave={() =>
                      setTooltipDefectId((current) => (current === defect.id ? null : current))
                    }
                    onFocus={() => setTooltipDefectId(defect.id)}
                    onBlur={() => setTooltipDefectId((current) => (current === defect.id ? null : current))}
                    onClick={() => {
                      setSelectedDefectId(defect.id)
                      setTooltipDefectId(defect.id)
                    }}
                    onContextMenu={() => {
                      setSelectedDefectId(defect.id)
                      setTooltipDefectId(defect.id)
                    }}
                  >
                    <span className="defect-item-tooltip-trigger">
                      <span className="defect-item-thumbnail">
                        <img
                          src={getDefectThumbnailUrl(defect)}
                          alt={`${defect.defectType} ${defect.coilId}`}
                          loading="lazy"
                          decoding="async"
                        />
                        <span className="defect-item-thumbnail-labels">
                          <span className="defect-item-thumbnail-name">{defect.defectType}</span>
                          <span className="defect-item-thumbnail-id">ID:{defect.coilId}</span>
                        </span>
                      </span>
                      <span className="defect-item-main">
                        <span className="defect-type">{defect.defectType}</span>
                        <small>
                          卷 {defect.coilId} · {defect.surface} 面 · 位置 ({defect.position.x}, {defect.position.y}) · 尺寸{' '}
                          {defect.size.width} x {defect.size.height}
                        </small>
                      </span>
                      <strong className="defect-confidence">{(defect.confidence * 100).toFixed(1)}%</strong>
                    </span>
                    <span className="defect-item-hover-card">{renderDefectItemTooltip(defect)}</span>
                  </button>
                </Dropdown>
              ))
            )}
          </div>
        </section>

        <section className="surface-panel">
          <div className="panel-title">
            <PictureOutlined />
            表面全景
          </div>
          <div className="surface-body">
            {!activeImageCoilId ? (
              <Empty description="请选择卷材" />
            ) : (
              <TileImageViewer
                imageUrl={areaUrl}
                previewUrl={previewUrl}
                defects={filteredDefects}
                selectedDefectId={selectedDefect?.id ?? null}
                tileCount={defaultAreaTileCount}
                showTileDebugBorders={showTileDebugBorders}
                enable1024CacheMode={enable1024CacheMode}
                showDefectLabels={showDefectLabels}
                manualAnnotationMode={manualDefectAddMode}
                onDefectSelect={handleDefectSelect}
                onManualAnnotation={handleManualDefectAnnotation}
              />
            )}
          </div>
        </section>

        <section className="defect-detail-panel">
          <div className="panel-title defect-detail-title">
            <span>缺陷详情</span>
            <Space size={6}>
              <Button
                size="small"
                icon={<SelectOutlined />}
                disabled={!canSwitchToImage}
                onClick={switchToSelectedDefectImage}
              >
                切换到图像
              </Button>
              <Button
                size="small"
                icon={<FolderOpenOutlined />}
                disabled={!canOpenImageFolder}
                onClick={openSelectedDefectImageFolder}
              >
                打开位置
              </Button>
              <Button
                size="small"
                icon={<EditOutlined />}
                disabled={!canEditSelectedManualDefect}
                onClick={() => setManualDefectEditOpen(true)}
              >
                编辑标注
              </Button>
            </Space>
          </div>
          {selectedDefect ? (
            <div className="defect-detail">
              <div className="detail-grid">
                <span>类型</span>
                <strong>{selectedDefect.defectType}</strong>
                <span>位置</span>
                <strong>
                  {selectedDefect.position.x}, {selectedDefect.position.y}
                </strong>
                <span>尺寸</span>
                <strong>
                  {selectedDefect.size.width} x {selectedDefect.size.height}
                </strong>
                <span>置信度</span>
                <strong>{(selectedDefect.confidence * 100).toFixed(1)}%</strong>
              </div>
              <div className="defect-crop">
                {defectImageUrl ? <Image src={defectImageUrl} preview={false} /> : null}
              </div>
            </div>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择缺陷" />
          )}
        </section>
      </div>
      <Modal
        className="manual-defect-edit-modal"
        title="编辑缺陷标注"
        open={manualDefectEditOpen}
        width={450}
        okText="保存"
        cancelText="取消"
        confirmLoading={manualDefectSaving}
        okButtonProps={{ disabled: !canEditSelectedManualDefect }}
        onOk={saveManualDefect}
        onCancel={() => setManualDefectEditOpen(false)}
        destroyOnHidden
        footer={(_, { OkBtn, CancelBtn }) => (
          <div className="manual-defect-modal-footer">
            <Button
              danger
              icon={<DeleteOutlined />}
              loading={manualDefectSaving}
              disabled={!canEditSelectedManualDefect}
              onClick={confirmDeleteManualDefect}
            >
              删除缺陷
            </Button>
            <span />
            <CancelBtn />
            <OkBtn />
          </div>
        )}
      >
        {selectedDefect && !canEditSelectedManualDefect ? (
          <Tag color="warning">⚠ 此为自动检测缺陷，无法编辑</Tag>
        ) : null}
        <div className="manual-defect-form">
          <label>
            <span>缺陷类型</span>
            <Select
              value={manualDefectForm.defectName}
              disabled={!canEditSelectedManualDefect}
              onChange={(value) => updateManualDefectForm('defectName', value)}
              options={filterOptions.map((option) => ({ value: option.name, label: option.name }))}
            />
          </label>
          <label>
            <span>X 坐标</span>
            <InputNumber
              min={0}
              value={manualDefectForm.defectX}
              disabled={!canEditSelectedManualDefect}
              onChange={(value) => updateManualDefectForm('defectX', value)}
            />
          </label>
          <label>
            <span>Y 坐标</span>
            <InputNumber
              min={0}
              value={manualDefectForm.defectY}
              disabled={!canEditSelectedManualDefect}
              onChange={(value) => updateManualDefectForm('defectY', value)}
            />
          </label>
          <label>
            <span>宽度</span>
            <InputNumber
              min={1}
              value={manualDefectForm.defectW}
              disabled={!canEditSelectedManualDefect}
              onChange={(value) => updateManualDefectForm('defectW', value)}
            />
          </label>
          <label>
            <span>高度</span>
            <InputNumber
              min={1}
              value={manualDefectForm.defectH}
              disabled={!canEditSelectedManualDefect}
              onChange={(value) => updateManualDefectForm('defectH', value)}
            />
          </label>
          <label className="manual-defect-remark">
            <span>备注</span>
            <Input.TextArea
              rows={2}
              value={manualDefectForm.remark}
              placeholder="输入备注信息..."
              disabled={!canEditSelectedManualDefect}
              onChange={(event) => updateManualDefectForm('remark', event.target.value)}
            />
          </label>
          <div className="manual-defect-annotator">
            标注人: {String(selectedDefect?.raw?.annotator ?? '系统用户')}
          </div>
        </div>
      </Modal>
      <Modal
        title="添加缺陷标注"
        open={manualDefectAddOpen}
        width={420}
        okText="确定"
        cancelText="取消"
        confirmLoading={manualDefectAddSaving}
        okButtonProps={{ disabled: !manualDefectAddRect }}
        onOk={saveNewManualDefect}
        onCancel={cancelManualDefectAdd}
        destroyOnHidden
      >
        <div className="manual-defect-add-form">
          <section>
            <h3>缺陷位置</h3>
            <div className="manual-defect-add-position">
              <span>X: {manualDefectAddRect?.x ?? 0}</span>
              <span>Y: {manualDefectAddRect?.y ?? 0}</span>
              <span>宽: {manualDefectAddRect?.width ?? 0}</span>
              <span>高: {manualDefectAddRect?.height ?? 0}</span>
            </div>
          </section>
          <label>
            <span>缺陷类型</span>
            <Select
              value={manualDefectAddForm.defectName}
              onChange={(value) => setManualDefectAddForm((current) => ({ ...current, defectName: value }))}
              options={filterOptions.map((option) => ({ value: option.name, label: option.name }))}
            />
          </label>
          <label>
            <span>备注（可选）</span>
            <Input
              value={manualDefectAddForm.remark}
              placeholder="输入备注信息..."
              onChange={(event) =>
                setManualDefectAddForm((current) => ({ ...current, remark: event.target.value }))
              }
            />
          </label>
        </div>
      </Modal>
      <Modal
        className="manual-defect-export-modal"
        title="导出标记缺陷"
        open={manualDefectExportOpen}
        width={500}
        okText="导出"
        cancelText="取消"
        confirmLoading={manualDefectExporting}
        okButtonProps={{
          disabled: !manualDefectExportPath.trim() || !canExportManualDefects,
        }}
        onOk={exportManualDefects}
        onCancel={() => setManualDefectExportOpen(false)}
        destroyOnHidden
      >
        <div className="manual-defect-export-form">
          <section>
            <h3>导出范围</h3>
            <Radio.Group
              value={manualDefectExportScope}
              onChange={(event) => setManualDefectExportScope(event.target.value)}
            >
              <Radio value="all">导出所有缺陷（包括自动检测和手动标注）</Radio>
              <Radio value="manual">仅导出手动标注的缺陷 ({manualDefectExportCounts.manual} 个)</Radio>
              <Radio value="selected" disabled={manualDefectExportCounts.selected === 0}>
                导出选中的缺陷 ({manualDefectExportCounts.selected} 个)
              </Radio>
            </Radio.Group>
          </section>
          <section>
            <h3>导出路径</h3>
            <div className="manual-defect-export-path">
              <Input
                value={manualDefectExportPath}
                placeholder="选择导出目录..."
                readOnly
              />
              <Button onClick={chooseManualDefectExportPath}>浏览...</Button>
            </div>
          </section>
          <section>
            <h3>导出选项</h3>
            <div className="manual-defect-export-options">
              <Checkbox
                checked={manualDefectExportOptions.groupByCategory}
                onChange={(event) =>
                  setManualDefectExportOptions((options) => ({
                    ...options,
                    groupByCategory: event.target.checked,
                  }))
                }
              >
                按缺陷类别分类到子文件夹
              </Checkbox>
              <Checkbox
                checked={manualDefectExportOptions.includeInfo}
                onChange={(event) =>
                  setManualDefectExportOptions((options) => ({
                    ...options,
                    includeInfo: event.target.checked,
                  }))
                }
              >
                生成缺陷清单 Excel 文件
              </Checkbox>
              <Checkbox
                checked={manualDefectExportOptions.highQuality}
                onChange={(event) =>
                  setManualDefectExportOptions((options) => ({
                    ...options,
                    highQuality: event.target.checked,
                  }))
                }
              >
                导出高质量图像（原图）
              </Checkbox>
            </div>
          </section>
        </div>
      </Modal>
      <Modal
        title="正在导出..."
        open={manualDefectProgressOpen}
        width={360}
        closable={false}
        maskClosable={false}
        keyboard={false}
        footer={
          <Button onClick={() => setManualDefectProgressOpen(false)}>
            后台运行
          </Button>
        }
      >
        <div className="manual-defect-export-progress">
          <Spin />
          <span>正在准备导出...</span>
        </div>
      </Modal>
    </div>
  )
}

export default DefectShowPage
