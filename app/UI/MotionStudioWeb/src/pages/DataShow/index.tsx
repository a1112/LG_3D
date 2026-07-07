import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import {
  Button,
  Checkbox,
  Dropdown,
  Empty,
  Image,
  Input,
  InputNumber,
  Modal,
  Popover,
  Select,
  Slider,
  Tag,
  message,
} from 'antd'
import type { MenuProps } from 'antd'
import {
  AppstoreOutlined,
  BorderOutlined,
  CheckSquareOutlined,
  CloseSquareOutlined,
  DotChartOutlined,
  EyeOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  LinkOutlined,
  LineChartOutlined,
  MenuOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import Canvas3D from '@/components/Canvas3D'
import { normalizeCanvas3DZScale } from '@/components/Canvas3D/utils'
import HeightChart from '@/components/HeightChart'
import {
  normalizeQmlHeightChartInnerCircleCenter,
  type QmlHeightChartCenter,
} from '@/components/HeightChart/utils'
import TileImageViewer, {
  type QmlUserPointState,
  type QmlUserPointUpdate,
  type TileImageViewerTransform,
} from '@/components/TileImageViewer'
import {
  buildQmlScaleMenuOptions,
  normalizeQmlCanvasScale,
  normalizeQmlDbPointInnerEllipse,
  normalizeQmlImageGamma,
  type QmlDbPointInnerEllipse,
  type QmlDbPointSource,
  type QmlDrawViewPerpendicularLine,
  type QmlScaleMetrics,
  type Rect,
} from '@/components/TileImageViewer/utils'
import {
  coilApi,
  defectApi,
  defectConfigApi,
  heightDataApi,
  imageApi,
  measurementDataApi,
  resolveImageRuntimeBaseUrl,
  resolveQmlSurfaceImageUrl,
  serviceBaseUrls,
  type DataAvailabilitySurface,
  type HeightLineCoords,
} from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import { useUiSettingsStore } from '@/stores/uiSettingsStore'
import type { DefectData, HeightLineSegment, SurfaceKey } from '@/types'
import {
  buildDataShowDefectClassFilterOptions,
  countDataShowDefectsByClass,
  filterDataShowDefects,
  getDefaultSelectedDefectClasses,
  getDataShowDefectClassName,
  getQmlDefectClassLevelColor,
} from '@/utils/defectFilter'
import { buildDataHeaderInfoSections } from '@/utils/dataHeaderInfo'
import {
  buildDataShowHeightDataReturnUrl,
  buildDataShowOpenUrl,
  buildDataShowRenderParams,
  buildDataShowRenderStages,
  openDataShowExternalUrl,
} from '@/utils/dataShowActions'
import { buildManualDefectAddPayload } from '@/utils/manualDefect'
import {
  buildQmlXyzListItems,
  coilInfoToQmlPointValueOptions,
  qmlXToMmText,
  qmlYToMmText,
  type QmlPointValueFormatOptions,
} from '@/utils/qmlPointValue'
import ustbDarkWatermarkUrl from '../../../../MotionStudio/resource/icon/USTB_Dark.png'
import ustbLightWatermarkUrl from '../../../../MotionStudio/resource/icon/USTB_Light.png'
import './DataShow.css'

type ViewMode = 'area' | 'gray' | 'depth' | 'three'
type DataShowMouseTool = 'move' | 'survey'
type View3DControlMode = 'rotate' | 'move'
const SURFACES: SurfaceKey[] = ['S', 'L']
const DEFAULT_LINE_COORDS: HeightLineCoords = { x1: 900, y1: 650, x2: 1000, y2: 650 }
const DEFAULT_RENDER_RANGE_Z = 20
const DATA_SHOW_HEADER_TOOLS: Array<{ key: DataShowMouseTool; title: string; description: string }> = [
  {
    key: 'move',
    title: '自由查看',
    description: '用于查看图像、定位曲线采样点。双击图像可把当前点设为曲线贯穿方向。',
  },
  {
    key: 'survey',
    title: '测量工具',
    description: '用于在图像上选择起点和终点，显示两点距离和水平/垂直偏移。',
  },
]
const VIEW_3D_CONTROL_OPTIONS: Array<{ mode: View3DControlMode; qmlKey: number; label: string }> = [
  { mode: 'rotate', qmlKey: 0, label: '自由旋转' },
  { mode: 'move', qmlKey: 1, label: '自由移动' },
]
const DATA_HEADER_MODE_OPTIONS = [
  { label: '缺陷信息', value: 0 },
  { label: '数据信息', value: 1 },
  { label: '曲线信息', value: 2 },
]
const RENDER_SCALE_OPTIONS = [
  { label: '100%', value: 1 },
  { label: '50%', value: 0.5 },
  { label: '33%', value: 1 / 3 },
]
const TWO_DIMENSIONAL_VIEW_KEYS = ['GRAY', 'JET'] as const
type TwoDimensionalViewKey = (typeof TWO_DIMENSIONAL_VIEW_KEYS)[number]

interface DataHeaderDefectInfoRow {
  label: string
  value: string
}

interface DataHeaderDefectClassMenuState {
  defectId: number
}

function surfaceLabel(surface: SurfaceKey) {
  return surface === 'S' ? 'S 面' : 'L 面'
}

function dataShowSurfaceTitle(surface: SurfaceKey) {
  return surface === 'S' ? '操作' : '传动'
}

function dataShowRootViewTitle(viewMode: ViewMode, currentTwoDimensionalViewKey: 'GRAY' | 'JET') {
  const areaTitle = viewMode === 'area' ? '2D相机' : null
  const threeTitle = viewMode === 'three' ? '3D' : null
  const twoDimensionalTitle = viewMode === 'gray' ? currentTwoDimensionalViewKey : currentTwoDimensionalViewKey
  return areaTitle ?? threeTitle ?? twoDimensionalTitle
}

function normalizeLineCoord(value: number | null): number {
  return Math.max(0, Math.trunc(value ?? 0))
}

function normalizeRenderRangeZ(value: number | null): number {
  return Math.min(Math.max(Math.trunc(value ?? DEFAULT_RENDER_RANGE_Z), 5), 100)
}

function normalizeRenderPlaneZMm(value: number | null): number | null {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return null
  return Math.min(Math.max(Math.trunc(numberValue), -9999), 9999)
}

function getCoilInfoNumber(coilInfo: unknown, key: string): number | null {
  if (!coilInfo || typeof coilInfo !== 'object') return null
  const value = Number((coilInfo as Record<string, unknown>)[key])
  return Number.isFinite(value) ? value : null
}

function qmlFootMsgText(value: unknown): string {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return '0'
  return String(Math.trunc(numberValue))
}

function getDataHeaderDefectCropUrl(
  defect: DefectData,
  currentTwoDimensionalViewKey: TwoDimensionalViewKey,
  imageBaseUrl: string,
): string {
  const viewKey = getDataShowDefectClassName(defect).startsWith('2D_') ? 'AREA' : currentTwoDimensionalViewKey
  return imageApi.getDefectImage(
    defect.surface,
    defect.coilId,
    viewKey,
    defect.position.x,
    defect.position.y,
    defect.size.width,
    defect.size.height,
    imageBaseUrl,
  )
}

function getDataHeaderDefectInfoRows(
  defect: DefectData,
  options: QmlPointValueFormatOptions,
): DataHeaderDefectInfoRow[] {
  return [
    { label: 'x', value: qmlXToMmText(defect.position.x, options) },
    { label: 'y', value: qmlYToMmText(defect.position.y, options) },
    { label: '宽', value: qmlXToMmText(defect.size.width, options) },
    { label: '高', value: qmlYToMmText(defect.size.height, options) },
  ]
}

function getDataHeaderDefectDisplayName(defect: DefectData, checkedNames: Record<number, string>): string {
  return checkedNames[defect.id] ?? defect.defectType
}

function hasQmlViewData(surfaceAvailability: DataAvailabilitySurface | undefined, viewKey: string): boolean {
  if (!surfaceAvailability) return false
  if (surfaceAvailability[viewKey] === true) return true
  if (viewKey === 'GRAY' || viewKey === 'JET' || viewKey === 'JPG') {
    return surfaceAvailability.JPG === true || surfaceAvailability['3D'] === true
  }
  if (viewKey === 'AREA' || viewKey === 'AREA_MASK') {
    return surfaceAvailability['2D'] === true
  }
  return false
}

function DataShowPage() {
  const queryClient = useQueryClient()
  const {
    currentCoil,
    surfaceKey,
    pendingDefect,
    visibleSurfaces,
    rootViewCommand,
    imageMaskChecked,
    quickImageEnabled,
    setSurfaceKey,
    clearPendingDefect,
  } = useCoilStore()
  const showTileDebugBorders = useUiSettingsStore((state) => state.showTileDebugBorders)
  const defaultAreaTileCount = useUiSettingsStore((state) => state.defaultAreaTileCount)
  const dataHeaderHeight = useUiSettingsStore((state) => state.dataHeaderHeight)
  const headDateShowModel = useUiSettingsStore((state) => state.headDateShowModel)
  const setHeadDateShowModel = useUiSettingsStore((state) => state.setHeadDateShowModel)
  const enable1024CacheMode = useUiSettingsStore((state) => state.enable1024CacheMode)
  const showErrorOverlay = useUiSettingsStore((state) => state.showErrorOverlay)
  const showDefectLabels = useUiSettingsStore((state) => state.showDefectLabels)
  const setShowDefectLabels = useUiSettingsStore((state) => state.setShowDefectLabels)
  const pointValueShowType = useUiSettingsStore((state) => state.pointValueShowType)
  const setPointValueShowType = useUiSettingsStore((state) => state.setPointValueShowType)
  const useRustImageServer = useUiSettingsStore((state) => state.useRustImageServer)
  const rustImageServerPort = useUiSettingsStore((state) => state.rustImageServerPort)
  const useSharedFolder = useUiSettingsStore((state) => state.useSharedFolder)
  const sharedFolderBaseName = useUiSettingsStore((state) => state.sharedFolderBaseName)
  const towerWarningThresholdUp = useUiSettingsStore((state) => state.towerWarningThresholdUp)
  const towerWarningThresholdDown = useUiSettingsStore((state) => state.towerWarningThresholdDown)
  const towerWarningOpacity = useUiSettingsStore((state) => state.towerWarningOpacity)
  const [viewMode, setViewMode] = useState<ViewMode>('area')
  const [renderData, setRenderData] = useState<ArrayBuffer | null>(null)
  const [renderViewKey, setRenderViewKey] = useState<'GRAY' | 'JET'>('JET')
  const [renderImageTypeText, setRenderImageTypeText] = useState('彩色显示')
  const [currentTwoDimensionalViewKey, setCurrentTwoDimensionalViewKey] = useState<'GRAY' | 'JET'>('GRAY')
  const [currentMouseTool, setCurrentMouseTool] = useState<DataShowMouseTool>('move')
  const [headerToolPopupOpen, setHeaderToolPopupOpen] = useState<DataShowMouseTool | null>(null)
  const [header2DPopupOpen, setHeader2DPopupOpen] = useState(false)
  const header2DPopupCloseTimerRef = useRef<number | null>(null)
  const [dataShowCanvasScale, setDataShowCanvasScale] = useState<number | null>(null)
  const [dataShowQmlMinScale, setDataShowQmlMinScale] = useState(1)
  const [dataShowLockControl, setDataShowLockControl] = useState(false)
  const [lockedAreaTransform, setLockedAreaTransform] = useState<TileImageViewerTransform | null>(null)
  const [imageGamma, setImageGamma] = useState(0.7)
  const [exclusiveSurface, setExclusiveSurface] = useState<SurfaceKey | null>(null)
  const [view3DZScale, setView3DZScale] = useState(0.5)
  const [view3DControlMode, setView3DControlMode] = useState<View3DControlMode>('rotate')
  const [showViewRendererListView, setShowViewRendererListView] = useState(false)
  const [showViewRendererMaxMinValue, setShowViewRendererMaxMinValue] = useState(false)
  const [taperShapeAnnotationEnabled, setTaperShapeAnnotationEnabled] = useState(true)
  const [thumbnailView3DEnabled, setThumbnailView3DEnabled] = useState(true)
  const [thumbnailView2DEnabled, setThumbnailView2DEnabled] = useState(true)
  const [qmlChartShowType, setQmlChartShowType] = useState<0 | 1>(0)
  const [autoRender, setAutoRender] = useState(false)
  const [renderPlaneZMm, setRenderPlaneZMm] = useState<number | null>(null)
  const [renderScale, setRenderScale] = useState(1)
  const [renderRangeZ, setRenderRangeZ] = useState(20)
  const [renderRefreshSignal, setRenderRefreshSignal] = useState(0)
  const [selectedDefect, setSelectedDefect] = useState<DefectData | null>(null)
  const [dataHeaderDefectCheckedNames, setDataHeaderDefectCheckedNames] = useState<Record<number, string>>({})
  const [dataHeaderDefectClassMenu, setDataHeaderDefectClassMenu] =
    useState<DataHeaderDefectClassMenuState | null>(null)
  const dataHeaderDefectClassMenuRef = useRef<HTMLSpanElement | null>(null)
  const [selectedDataShowDefectClasses, setSelectedDataShowDefectClasses] = useState<string[]>([])
  const [showAreaDefects, setShowAreaDefects] = useState(false)
  const [showHiddenDefects, setShowHiddenDefects] = useState(false)
  const [lineForm, setLineForm] = useState<HeightLineCoords>(DEFAULT_LINE_COORDS)
  const [lineCoords, setLineCoords] = useState<HeightLineCoords>(DEFAULT_LINE_COORDS)
  const [viewResetSignal, setViewResetSignal] = useState(0)
  const [manualDefectAddMode, setManualDefectAddMode] = useState(false)
  const [manualDefectAddOpen, setManualDefectAddOpen] = useState(false)
  const [manualDefectAddSaving, setManualDefectAddSaving] = useState(false)
  const [manualDefectAddSurface, setManualDefectAddSurface] = useState<SurfaceKey>('S')
  const [manualDefectAddRect, setManualDefectAddRect] = useState<Rect | null>(null)
  const [manualDefectAddForm, setManualDefectAddForm] = useState({ defectName: '', remark: '' })
  const [qmlUserPointsBySurface, setQmlUserPointsBySurface] = useState<Record<SurfaceKey, QmlUserPointState[]>>({
    S: [],
    L: [],
  })
  const dataShowScaleOptions = useMemo<MenuProps['items']>(
    () => buildQmlScaleMenuOptions(dataShowQmlMinScale).map(({ key, label }) => ({ key, label })),
    [dataShowQmlMinScale],
  )

  const handleDataShowQmlScaleMetricsChange = useCallback((metrics: QmlScaleMetrics) => {
    setDataShowQmlMinScale(metrics.minScale)
  }, [])

  const { data: defectsSData, isFetching: defectsSLoading } = useQuery({
    queryKey: ['defects', currentCoil?.id, 'S'],
    queryFn: () => defectApi.getDefects(currentCoil?.id || 0, 'S'),
    enabled: !!currentCoil,
  })

  const { data: defectsLData, isFetching: defectsLLoading } = useQuery({
    queryKey: ['defects', currentCoil?.id, 'L'],
    queryFn: () => defectApi.getDefects(currentCoil?.id || 0, 'L'),
    enabled: !!currentCoil,
  })

  const { data: defectDictData } = useQuery({
    queryKey: ['defect-dict'],
    queryFn: defectConfigApi.getDefectDict,
    enabled: !!currentCoil,
  })

  const { data: coilInfoSData } = useQuery({
    queryKey: ['coilInfo', currentCoil?.id, 'S'],
    queryFn: () => coilApi.getCoilInfo(currentCoil?.id || 0, 'S'),
    enabled: !!currentCoil,
  })

  const { data: coilInfoLData } = useQuery({
    queryKey: ['coilInfo', currentCoil?.id, 'L'],
    queryFn: () => coilApi.getCoilInfo(currentCoil?.id || 0, 'L'),
    enabled: !!currentCoil,
  })

  const { data: dataAvailabilityData } = useQuery({
    queryKey: ['data-has', currentCoil?.id],
    queryFn: () => coilApi.getDataAvailability(currentCoil?.id || 0),
    enabled: !!currentCoil,
    retry: 1,
  })

  const { data: pointSData } = useQuery({
    queryKey: ['point-data', currentCoil?.id, 'S'],
    queryFn: () => measurementDataApi.getPointData(currentCoil?.id || 0, 'S'),
    enabled: !!currentCoil,
    retry: 1,
  })

  const { data: pointLData } = useQuery({
    queryKey: ['point-data', currentCoil?.id, 'L'],
    queryFn: () => measurementDataApi.getPointData(currentCoil?.id || 0, 'L'),
    enabled: !!currentCoil,
    retry: 1,
  })

  const coilInfoBySurface = useMemo(
    () => ({
      S: coilInfoSData,
      L: coilInfoLData,
    }),
    [coilInfoLData, coilInfoSData],
  )
  const dataAvailabilityBySurface = dataAvailabilityData ?? {}
  const qmlMeshExists = dataAvailabilityBySurface[surfaceKey]?.MESH === true
  const activeCoilInfo = coilInfoBySurface[surfaceKey]
  const footMedianZIntText = qmlFootMsgText(getCoilInfoNumber(activeCoilInfo, 'median_3d'))
  const footMedianZText = qmlFootMsgText(getCoilInfoNumber(activeCoilInfo, 'median_3d_mm'))
  const activeRenderPlaneZMm = useMemo(
    () => renderPlaneZMm ?? getCoilInfoNumber(activeCoilInfo, 'median_3d_mm'),
    [activeCoilInfo, renderPlaneZMm],
  )
  const activeRenderParams = useMemo(
    () =>
      buildDataShowRenderParams({
        coilInfo: activeCoilInfo,
        planeZMm: activeRenderPlaneZMm ?? undefined,
        renderScale,
        rangeZ: renderRangeZ,
        grayscale: false,
      }),
    [activeCoilInfo, activeRenderPlaneZMm, renderRangeZ, renderScale],
  )
  const renderStages = useMemo(
    () => buildDataShowRenderStages(activeRenderParams, enable1024CacheMode),
    [activeRenderParams, enable1024CacheMode],
  )
  const renderRequestKey = useMemo(
    () => (autoRender ? JSON.stringify(renderStages) : String(renderRefreshSignal)),
    [autoRender, renderRefreshSignal, renderStages],
  )

  const { data: heightLineSData, isFetching: heightLineSLoading } = useQuery({
    queryKey: ['heightLine', currentCoil?.id, 'S', lineCoords],
    queryFn: () => heightDataApi.getHeightLine('S', currentCoil?.id || 0, lineCoords),
    enabled: !!currentCoil,
    retry: 1,
  })

  const { data: heightLineLData, isFetching: heightLineLLoading } = useQuery({
    queryKey: ['heightLine', currentCoil?.id, 'L', lineCoords],
    queryFn: () => heightDataApi.getHeightLine('L', currentCoil?.id || 0, lineCoords),
    enabled: !!currentCoil,
    retry: 1,
  })
  const heightLineDataBySurface = useMemo<Record<SurfaceKey, HeightLineSegment[]>>(
    () => ({
      S: heightLineSData ?? [],
      L: heightLineLData ?? [],
    }),
    [heightLineLData, heightLineSData],
  )
  const heightLineLoadingBySurface = useMemo<Record<SurfaceKey, boolean>>(
    () => ({
      S: heightLineSLoading,
      L: heightLineLLoading,
    }),
    [heightLineLLoading, heightLineSLoading],
  )
  const heightLineData = heightLineDataBySurface[surfaceKey]
  const heightLoading = heightLineLoadingBySurface[surfaceKey]
  const qmlDrawViewPerpendicularLine = useMemo<QmlDrawViewPerpendicularLine>(
    () => ({
      start: { x: lineCoords.x1, y: lineCoords.y1 },
      end: { x: lineCoords.x2, y: lineCoords.y2 },
    }),
    [lineCoords],
  )

  const { data: coilAlarmData } = useQuery({
    queryKey: ['coilAlarm', currentCoil?.id],
    queryFn: () => coilApi.getCoilAlarm(currentCoil?.id || 0),
    enabled: !!currentCoil && headDateShowModel === 1,
    retry: 1,
  })

  useEffect(() => {
    setRenderData(null)
    setRenderViewKey('JET')
    setRenderImageTypeText('彩色显示')
    setCurrentTwoDimensionalViewKey('GRAY')
    setShowViewRendererListView(false)
    setShowViewRendererMaxMinValue(false)
    setSelectedDefect(null)
    setLineForm(DEFAULT_LINE_COORDS)
    setLineCoords(DEFAULT_LINE_COORDS)
    setRenderPlaneZMm(null)
    setRenderScale(1)
    setRenderRangeZ(DEFAULT_RENDER_RANGE_Z)
    setRenderRefreshSignal(0)
    setAutoRender(false)
    setManualDefectAddMode(false)
    setManualDefectAddOpen(false)
    setManualDefectAddRect(null)
    setLockedAreaTransform(null)
    setDataHeaderDefectCheckedNames({})
    setDataHeaderDefectClassMenu(null)
  }, [currentCoil?.id])

  useEffect(() => {
    setRenderPlaneZMm(null)
    setRenderViewKey('JET')
    setRenderImageTypeText('彩色显示')
    setCurrentTwoDimensionalViewKey('GRAY')
    setDataHeaderDefectClassMenu(null)
  }, [surfaceKey])

  useEffect(() => {
    if (!dataHeaderDefectClassMenu) return

    const handleDataHeaderDefectMenuOutsidePointerDown = (event: PointerEvent) => {
      const menuElement = dataHeaderDefectClassMenuRef.current
      if (!menuElement || menuElement.contains(event.target as Node)) return
      setDataHeaderDefectClassMenu(null)
    }

    document.addEventListener('pointerdown', handleDataHeaderDefectMenuOutsidePointerDown)
    return () => {
      document.removeEventListener('pointerdown', handleDataHeaderDefectMenuOutsidePointerDown)
    }
  }, [dataHeaderDefectClassMenu])

  useEffect(() => {
    if (!pendingDefect || pendingDefect.coilId !== currentCoil?.id) return

    setViewMode('area')
    setSurfaceKey(pendingDefect.surface)
    setSelectedDefect(pendingDefect)
    clearPendingDefect()
  }, [clearPendingDefect, currentCoil?.id, pendingDefect, setSurfaceKey])

  useEffect(() => {
    if (!currentCoil || viewMode !== 'three' || renderStages.length === 0) return

    let cancelled = false
    const runRenderStage = (stage: (typeof renderStages)[number]) => {
      setRenderViewKey(stage.viewKey)
      setRenderImageTypeText(stage.label)
      setCurrentTwoDimensionalViewKey(stage.viewKey)
      queryClient
        .fetchQuery({
          queryKey: ['render3D', currentCoil.id, surfaceKey, renderRequestKey, stage.key],
          queryFn: () => heightDataApi.getRenderData(surfaceKey, currentCoil.id, stage.params),
        })
        .then((data) => {
          if (!cancelled) setRenderData(data)
        })
        .catch(() => {
          if (cancelled) return
          setRenderData(null)
          message.warning(`${surfaceLabel(surfaceKey)} 3D数据暂不可用`)
        })
    }

    const timers = renderStages
      .map((stage) => {
        if (stage.delayMs === 0) {
          runRenderStage(stage)
          return null
        }
        return window.setTimeout(() => runRenderStage(stage), stage.delayMs)
      })
      .filter((timer): timer is number => timer !== null)

    return () => {
      cancelled = true
      timers.forEach((timer) => window.clearTimeout(timer))
    }
  }, [currentCoil, queryClient, renderRequestKey, surfaceKey, viewMode])

  const rawDefectsBySurface: Record<SurfaceKey, DefectData[]> = {
    S: defectsSData?.data ?? [],
    L: defectsLData?.data ?? [],
  }
  const allRawDefects = useMemo(
    () => [...rawDefectsBySurface.S, ...rawDefectsBySurface.L],
    [rawDefectsBySurface.S, rawDefectsBySurface.L],
  )
  const defectFilterOptions = useMemo(
    () => buildDataShowDefectClassFilterOptions(defectDictData, allRawDefects),
    [allRawDefects, defectDictData],
  )
  const defectClassCounts = useMemo(
    () => countDataShowDefectsByClass(defectFilterOptions, allRawDefects),
    [allRawDefects, defectFilterOptions],
  )
  const dataShowDefectClassOptions = useMemo(
    () => defectFilterOptions.filter((option) => (defectClassCounts[option.name] ?? 0) > 0),
    [defectClassCounts, defectFilterOptions],
  )
  const visibleDataShowDefectClassOptions = useMemo(
    () => dataShowDefectClassOptions.filter((option) => option.show || showHiddenDefects),
    [dataShowDefectClassOptions, showHiddenDefects],
  )
  const dataShowDefectClassNames = useMemo(
    () => dataShowDefectClassOptions.map((option) => option.name),
    [dataShowDefectClassOptions],
  )
  const areaDefectClassNames = useMemo(
    () => dataShowDefectClassOptions.filter((option) => option.name.startsWith('2D_')).map((option) => option.name),
    [dataShowDefectClassOptions],
  )
  const hiddenDefectClassNames = useMemo(
    () => dataShowDefectClassOptions.filter((option) => !option.show).map((option) => option.name),
    [dataShowDefectClassOptions],
  )
  const defectsBySurface: Record<SurfaceKey, DefectData[]> = useMemo(
    () => ({
      S: filterDataShowDefects(rawDefectsBySurface.S, defectFilterOptions, {
        selectedClassNames: selectedDataShowDefectClasses,
        showArea: showAreaDefects,
        showHidden: showHiddenDefects,
      }),
      L: filterDataShowDefects(rawDefectsBySurface.L, defectFilterOptions, {
        selectedClassNames: selectedDataShowDefectClasses,
        showArea: showAreaDefects,
        showHidden: showHiddenDefects,
      }),
    }),
    [
      defectFilterOptions,
      rawDefectsBySurface.L,
      rawDefectsBySurface.S,
      selectedDataShowDefectClasses,
      showAreaDefects,
      showHiddenDefects,
    ],
  )
  const totalRawDefects = allRawDefects.length
  const totalDefects = defectsBySurface.S.length + defectsBySurface.L.length
  const activeSurfaceDefects = defectsBySurface[surfaceKey]
  const dataHeaderInfoSections = useMemo(() => buildDataHeaderInfoSections(coilAlarmData), [coilAlarmData])
  const hiddenDefectsCount = Math.max(0, totalRawDefects - totalDefects)
  const anyDefectLoading = defectsSLoading || defectsLLoading
  const errorOverlayUrl =
    currentCoil && viewMode === 'three'
      ? heightDataApi.getErrorImageUrl(surfaceKey, currentCoil.id, {
          minValue: towerWarningThresholdDown,
          maxValue: towerWarningThresholdUp,
        })
      : ''
  const imageRuntimeSettings = {
    useRustImageServer,
    rustImageServerPort,
    useSharedFolder,
    sharedFolderBaseName,
    imageMaskChecked,
    quickImageEnabled,
  }
  const pointValueOptionsBySurface = useMemo(
    () => ({
      S: coilInfoToQmlPointValueOptions(coilInfoBySurface.S),
      L: coilInfoToQmlPointValueOptions(coilInfoBySurface.L),
    }),
    [coilInfoBySurface],
  )
  const heightChartInnerCircleCenterBySurface = useMemo<Record<SurfaceKey, QmlHeightChartCenter | null>>(
    () => ({
      S: normalizeQmlHeightChartInnerCircleCenter(coilInfoBySurface.S),
      L: normalizeQmlHeightChartInnerCircleCenter(coilInfoBySurface.L),
    }),
    [coilInfoBySurface],
  )
  const pointDataBySurface = useMemo<Record<SurfaceKey, QmlDbPointSource[]>>(
    () => ({
      S: (pointSData ?? []) as QmlDbPointSource[],
      L: (pointLData ?? []) as QmlDbPointSource[],
    }),
    [pointLData, pointSData],
  )
  const dbPointInnerEllipseBySurface = useMemo<Record<SurfaceKey, QmlDbPointInnerEllipse | null>>(
    () => ({
      S: normalizeQmlDbPointInnerEllipse(coilInfoBySurface.S),
      L: normalizeQmlDbPointInnerEllipse(coilInfoBySurface.L),
    }),
    [coilInfoBySurface],
  )
  const activeXyzPointSources = useMemo(
    () => [
      ...pointDataBySurface[surfaceKey],
      ...qmlUserPointsBySurface[surfaceKey].map((userPoint) => ({
        id: userPoint.id,
        p_x: userPoint.point.x,
        p_y: userPoint.point.y,
        p_z: userPoint.rawValue,
        type: 'user',
      })),
    ],
    [pointDataBySurface, qmlUserPointsBySurface, surfaceKey],
  )
  const activeXyzListItems = useMemo(
    () =>
      buildQmlXyzListItems(activeXyzPointSources, {
        ...pointValueOptionsBySurface[surfaceKey],
        center: dbPointInnerEllipseBySurface[surfaceKey]?.center,
        thresholdDown: towerWarningThresholdDown,
        thresholdUp: towerWarningThresholdUp,
      }),
    [
      activeXyzPointSources,
      dbPointInnerEllipseBySurface,
      pointValueOptionsBySurface,
      surfaceKey,
      towerWarningThresholdDown,
      towerWarningThresholdUp,
    ],
  )
  const imageBaseUrl = resolveImageRuntimeBaseUrl(imageRuntimeSettings)
  const activeAreaViewKey = imageMaskChecked ? 'AREA_MASK' : 'AREA'
  const activeViewKey = viewMode === 'gray' ? 'GRAY' : viewMode === 'depth' ? 'JET' : 'AREA'
  const activeDataShowViewKey =
    viewMode === 'three' ? renderViewKey : viewMode === 'area' ? activeAreaViewKey : activeViewKey
  const currentTwoDimensionalViewMode = currentTwoDimensionalViewKey === 'JET' ? 'depth' : 'gray'
  const nextTwoDimensionalViewKey = currentTwoDimensionalViewKey === 'GRAY' ? 'JET' : 'GRAY'
  const showQmlViewChang3DThumbnail = Boolean(
    currentCoil && thumbnailView3DEnabled && qmlMeshExists && viewMode !== 'three',
  )
  const showQmlViewChang2DThumbnail = thumbnailView2DEnabled && Boolean(currentCoil)
  const activeView3DControlOption =
    VIEW_3D_CONTROL_OPTIONS.find((option) => option.mode === view3DControlMode) ?? VIEW_3D_CONTROL_OPTIONS[0]
  const view3DControlModeLabel = activeView3DControlOption.label
  const view3DControlQmlKey = activeView3DControlOption.qmlKey
  const view3DControlMenuItems = useMemo<MenuProps['items']>(
    () =>
      VIEW_3D_CONTROL_OPTIONS.map((option) => ({
        key: `view-3d-control-${option.qmlKey}`,
        label: option.label,
        disabled: view3DControlMode === option.mode,
        onClick: () => setView3DControlMode(option.mode),
      })),
    [view3DControlMode],
  )
  const dataShowHeaderSurfaceTitle = dataShowSurfaceTitle(surfaceKey)
  const dataShowHeaderViewTitle = dataShowRootViewTitle(viewMode, currentTwoDimensionalViewKey)
  const visibleAreaSurfaces = exclusiveSurface ? [exclusiveSurface] : SURFACES.filter((surface) => visibleSurfaces.includes(surface))
  const shouldShowDataShowWatermark = !currentCoil || visibleAreaSurfaces.length === 0
  const dataShowStyle = { '--data-header-height': `${dataHeaderHeight}px` } as CSSProperties
  const heightLineDataReturnUrl = currentCoil
    ? buildDataShowHeightDataReturnUrl({
        surfaceKey,
        coilId: currentCoil.id,
        coords: lineCoords,
        apiBaseUrl: serviceBaseUrls.apiBaseUrl,
      })
    : ''
  useEffect(() => {
    if (!rootViewCommand) return

    setViewMode(rootViewCommand.mode === 'three' ? 'three' : currentTwoDimensionalViewMode)
  }, [rootViewCommand, currentTwoDimensionalViewMode])
  const updateLineForm = (key: keyof HeightLineCoords, value: number | null) => {
    setLineForm((current) => ({ ...current, [key]: normalizeLineCoord(value) }))
  }
  const applyLineCoords = () => {
    setLineCoords(lineForm)
  }
  const resetLineCoords = () => {
    setLineForm(DEFAULT_LINE_COORDS)
    setLineCoords(DEFAULT_LINE_COORDS)
  }
  const resetDataShowView = () => {
    setLockedAreaTransform(null)
    setViewResetSignal((current) => current + 1)
  }
  const updateDataShowQmlUserPoints = useCallback((surface: SurfaceKey, update: QmlUserPointUpdate) => {
    setQmlUserPointsBySurface((current) => {
      const currentPoints = current[surface]
      const nextPoints = typeof update === 'function' ? update(currentPoints) : update
      return {
        ...current,
        [surface]: nextPoints,
      }
    })
  }, [])
  const removeDataShowQmlUserPoint = useCallback(
    (surface: SurfaceKey, id: string) => {
      updateDataShowQmlUserPoints(surface, (points) => points.filter((point) => String(point.id) !== id))
    },
    [updateDataShowQmlUserPoints],
  )
  const handleActiveQmlUserPointsChange = useCallback(
    (update: QmlUserPointUpdate) => updateDataShowQmlUserPoints(surfaceKey, update),
    [surfaceKey, updateDataShowQmlUserPoints],
  )
  const toggleDataShowSurfaceExclusive = () => {
    setExclusiveSurface((current) => (current === surfaceKey ? null : surfaceKey))
  }
  const clearHeader2DPopupCloseTimer = () => {
    if (header2DPopupCloseTimerRef.current === null) return

    window.clearTimeout(header2DPopupCloseTimerRef.current)
    header2DPopupCloseTimerRef.current = null
  }
  const openHeader2DPopup = () => {
    clearHeader2DPopupCloseTimer()
    setHeader2DPopupOpen(true)
  }
  const scheduleHeader2DPopupClose = () => {
    clearHeader2DPopupCloseTimer()
    header2DPopupCloseTimerRef.current = window.setTimeout(() => {
      setHeader2DPopupOpen(false)
      header2DPopupCloseTimerRef.current = null
    }, 300)
  }
  const selectCurrentTwoDimensionalView = (viewKey: 'GRAY' | 'JET') => {
    setCurrentTwoDimensionalViewKey(viewKey)
    setViewMode(viewKey === 'JET' ? 'depth' : 'gray')
  }
  const openNextTwoDimensionalThumbnailView = () => {
    selectCurrentTwoDimensionalView(nextTwoDimensionalViewKey)
  }
  const openCurrentTwoDimensionalView = () => {
    setViewMode(currentTwoDimensionalViewMode)
  }
  const rerenderDataShow3D = () => {
    setViewMode('three')
    setRenderData(null)
    setRenderRefreshSignal((current) => current + 1)
  }
  const openCurrentDataShowUrl = () => {
    if (!currentCoil) return

    const url = buildDataShowOpenUrl({
      mode: viewMode,
      surfaceKey,
      coilId: currentCoil.id,
      imageRuntimeSettings,
      imageBaseUrl,
      renderParams: activeRenderParams ?? undefined,
    })
    void openDataShowExternalUrl(url)
  }
  const openHeightLineDataReturnUrl = () => {
    if (!heightLineDataReturnUrl || headDateShowModel !== 2) return

    void openDataShowExternalUrl(heightLineDataReturnUrl)
  }
  const dataHeaderSelectMenuItems: MenuProps['items'] = [
    {
      key: 'height-line-return',
      label: '曲线数据返回',
      disabled: !currentCoil || headDateShowModel !== 2,
      onClick: openHeightLineDataReturnUrl,
    },
  ]
  const dataShowTitleMenuItems: MenuProps['items'] = [
    {
      key: 'title-lock-control',
      label: dataShowLockControl ? '取消锁定' : '锁定',
      onClick: () => setDataShowLockControl((locked) => !locked),
    },
    {
      key: 'title-layout',
      label: '布局',
      disabled: true,
      children: [
        { key: 'title-layout-vertical', label: '上下布局' },
        { key: 'title-layout-horizontal', label: '左右布局' },
      ],
    },
  ]
  const dataShowMenuItems: MenuProps['items'] = [
    {
      key: 'open-url',
      label: '打开URL...',
      disabled: !currentCoil,
      onClick: openCurrentDataShowUrl,
    },
    {
      key: 'reset',
      label: '重置',
      disabled: !currentCoil,
      onClick: resetDataShowView,
    },
    {
      key: 'switch',
      label: '切换',
      children: [
        { key: 'switch-2d-gray', label: '2D  -  灰度图', onClick: () => selectCurrentTwoDimensionalView('GRAY') },
        { key: 'switch-2d-depth', label: '2D  -  深度图', onClick: () => selectCurrentTwoDimensionalView('JET') },
        { key: 'switch-3d-fit', label: '3D - 拟合模型', onClick: () => setViewMode('three') },
      ],
    },
    {
      key: 'defect-view',
      label: '缺陷显示',
      children: [{ key: 'defect-view-groups', label: '显示组别' }],
    },
    {
      key: 'display',
      label: '显示',
      children: [
        {
          key: 'tower-annotation',
          label: '塔形标注',
          children: [
            {
              key: 'tower-annotation-type',
              label: '显示类型',
              children: [
                { key: 'tower-type-outer-overflow-positive', label: '外塔 + 溢出' },
                { key: 'tower-type-outer-overflow-negative', label: '外塔 - 溢出' },
                { key: 'tower-type-inner-overflow-positive', label: '内塔 + 溢出' },
                { key: 'tower-type-inner-overflow-negative', label: '内塔 - 溢出' },
              ],
            },
            {
              key: 'tower-annotation-density',
              label: '显示密度',
              children: [
                { key: 'tower-density-auto', label: '自动' },
                { key: 'tower-density-low', label: '低密度 12 点' },
                { key: 'tower-density-high', label: '高密度 72 点' },
              ],
            },
          ],
        },
        {
          key: 'defect-display',
          label: '缺陷显示',
          children: [
            {
              key: 'defect-label',
              label: '缺陷标签',
              children: [
                {
                  key: 'defect-label-show',
                  label: '显示',
                  disabled: showDefectLabels,
                  onClick: () => setShowDefectLabels(true),
                },
                {
                  key: 'defect-label-hide',
                  label: '隐藏',
                  disabled: !showDefectLabels,
                  onClick: () => setShowDefectLabels(false),
                },
              ],
            },
          ],
        },
        {
          key: 'depth-display',
          label: '深度显示',
          children: [
            {
              key: 'depth-mm-relative',
              label: 'mm 相对值',
              disabled: pointValueShowType === 'mm-relative',
              onClick: () => setPointValueShowType('mm-relative'),
            },
            {
              key: 'depth-mm-absolute',
              label: 'mm 绝对值',
              disabled: pointValueShowType === 'mm-absolute',
              onClick: () => setPointValueShowType('mm-absolute'),
            },
            {
              key: 'depth-int-raw',
              label: 'int 原始值',
              disabled: pointValueShowType === 'int-raw',
              onClick: () => setPointValueShowType('int-raw'),
            },
          ],
        },
      ],
    },
  ]
  const setDataShowClassSelection = (className: string, checked: boolean) => {
    setSelectedDataShowDefectClasses((current) => {
      const next = new Set(current)
      if (checked) {
        next.add(className)
      } else {
        next.delete(className)
      }
      return dataShowDefectClassNames.filter((name) => next.has(name))
    })
  }
  const selectAllDataShowDefectClasses = () => {
    setSelectedDataShowDefectClasses(dataShowDefectClassNames)
  }
  const clearDataShowDefectClasses = () => {
    setSelectedDataShowDefectClasses([])
  }
  const changeAreaDefectVisibility = (checked: boolean) => {
    setShowAreaDefects(checked)
    setSelectedDataShowDefectClasses((current) => {
      const next = new Set(current)
      for (const name of areaDefectClassNames) {
        if (checked) {
          next.add(name)
        } else {
          next.delete(name)
        }
      }
      return dataShowDefectClassNames.filter((name) => next.has(name))
    })
  }
  const changeHiddenDefectVisibility = (checked: boolean) => {
    setShowHiddenDefects(checked)
    setSelectedDataShowDefectClasses((current) => {
      const next = new Set(current)
      for (const name of hiddenDefectClassNames) {
        if (checked) {
          next.add(name)
        } else {
          next.delete(name)
        }
      }
      return dataShowDefectClassNames.filter((name) => next.has(name))
    })
  }
  const setDataHeaderDefectCheckedName = (defectId: number, defectName: string) => {
    setDataHeaderDefectCheckedNames((current) => ({ ...current, [defectId]: defectName }))
  }
  const handleDataShowManualAnnotation = (surface: SurfaceKey, rect: Rect) => {
    const defaultDefectName = defectFilterOptions.find((option) => option.show)?.name ?? defectFilterOptions[0]?.name ?? ''
    setManualDefectAddSurface(surface)
    setManualDefectAddRect(rect)
    setManualDefectAddForm({ defectName: defaultDefectName, remark: '' })
    setManualDefectAddMode(false)
    setManualDefectAddOpen(true)
  }
  const cancelDataShowManualDefectAdd = () => {
    setManualDefectAddOpen(false)
    setManualDefectAddRect(null)
  }
  const saveDataShowManualDefect = async () => {
    if (!currentCoil || !manualDefectAddRect) return

    setManualDefectAddSaving(true)
    try {
      await defectApi.addManualDefect(
        buildManualDefectAddPayload({
          coilId: currentCoil.id,
          surfaceKey: manualDefectAddSurface,
          rect: manualDefectAddRect,
          defectName: manualDefectAddForm.defectName,
          remark: manualDefectAddForm.remark,
        }),
      )
      message.success('缺陷标注已添加')
      setManualDefectAddOpen(false)
      setManualDefectAddRect(null)
      queryClient.invalidateQueries({ queryKey: ['defects', currentCoil.id, manualDefectAddSurface] })
    } catch {
      message.error('缺陷标注添加失败')
    } finally {
      setManualDefectAddSaving(false)
    }
  }

  useEffect(() => {
    setSelectedDataShowDefectClasses((current) => {
      const currentSet = new Set(current)
      const retained = dataShowDefectClassNames.filter((name) => currentSet.has(name))
      if (retained.length > 0 || dataShowDefectClassOptions.length === 0) {
        return retained
      }
      return getDefaultSelectedDefectClasses(dataShowDefectClassOptions)
    })
  }, [dataShowDefectClassNames, dataShowDefectClassOptions])

  useEffect(() => {
    if (viewMode !== 'area') {
      setManualDefectAddMode(false)
    }
  }, [viewMode])

  return (
    <div
      className="data-show-page"
      style={dataShowStyle}
      data-point-value-show-type={pointValueShowType}
      data-datashow-view-mode={viewMode}
      data-datashow-view-key={activeDataShowViewKey}
      data-datashow-area-view-key={activeAreaViewKey}
    >
      <div className="data-toolbar">
        <div className="toolbar-title">
          <DotChartOutlined />
          <span>数据展示</span>
          <Tag color="cyan">{currentCoil?.coilNo ?? '未选择卷材'}</Tag>
        </div>
        <Dropdown trigger={['contextMenu']} menu={{ items: dataShowTitleMenuItems }}>
          <div
            className="data-show-header-title"
            data-datashow-title-menu
            data-datashow-header-title
            data-datashow-header-surface={surfaceKey}
            data-datashow-header-view={dataShowHeaderViewTitle}
            data-datashow-lock-control={dataShowLockControl ? 'true' : 'false'}
            onDoubleClick={toggleDataShowSurfaceExclusive}
          >
            <span className="data-show-header-surface-title">{dataShowHeaderSurfaceTitle}</span>
            <span className="data-show-header-view-title">{dataShowHeaderViewTitle}</span>
          </div>
        </Dropdown>
        <div className="toolbar-controls">
          <span className="surface-select-label">当前曲线/3D</span>
          <Select
            size="small"
            value={surfaceKey}
            onChange={setSurfaceKey}
            options={[
              { value: 'S', label: 'S 面' },
              { value: 'L', label: 'L 面' },
            ]}
          />
          {viewMode !== 'three' ? (
            <Dropdown
              trigger={['click']}
              menu={{
                items: dataShowScaleOptions,
                onClick: ({ key }) => setDataShowCanvasScale(normalizeQmlCanvasScale(Number(key))),
              }}
            >
              <Button
                size="small"
                className="data-show-scale-control"
                data-datashow-scale-control
                data-datashow-canvas-scale={dataShowCanvasScale?.toFixed(2) ?? 'auto'}
              >
                缩放：{Math.round((dataShowCanvasScale ?? 1) * 100)}%
              </Button>
            </Dropdown>
          ) : null}
          {viewMode === 'gray' ? (
            <div
              className="data-show-gamma-control"
              data-datashow-gamma-control
              data-datashow-image-gamma={imageGamma.toFixed(2)}
            >
              <Slider
                min={0.3}
                max={1.3}
                step={0.05}
                value={imageGamma}
                onChange={(value) => setImageGamma(normalizeQmlImageGamma(value) ?? 0.7)}
                tooltip={{ formatter: (value) => (normalizeQmlImageGamma(value) ?? 0.7).toFixed(2) }}
              />
              <Tag color="orange">{imageGamma.toFixed(2)}</Tag>
            </div>
          ) : null}
          {viewMode !== 'three' ? (
            <div
              className="data-show-header-tool-row"
              data-datashow-header-tool-row
              data-datashow-mouse-tool={currentMouseTool}
            >
              <span className="data-show-header-tool-title">工具:</span>
              {DATA_SHOW_HEADER_TOOLS.map((tool) => {
                const selected = currentMouseTool === tool.key

                return (
                  <Popover
                    key={tool.key}
                    trigger="click"
                    placement="bottom"
                    open={headerToolPopupOpen === tool.key}
                    onOpenChange={(open) => setHeaderToolPopupOpen(open ? tool.key : null)}
                    content={
                      <div
                        className="data-show-header-tool-popover"
                        data-datashow-header-tool-popover={tool.key}
                      >
                        <div className="data-show-header-tool-popover-head">
                          <span className="data-show-header-tool-popover-icon">
                            {tool.key === 'move' ? <EyeOutlined /> : <DotChartOutlined />}
                          </span>
                          <div>
                            <strong>{tool.title}</strong>
                            <small>{selected ? '当前已启用' : '当前未启用'}</small>
                          </div>
                        </div>
                        <p>{tool.description}</p>
                        <div className="data-show-header-tool-popover-actions">
                          <Button
                            size="small"
                            type={selected ? 'primary' : 'default'}
                            onClick={() => {
                              setCurrentMouseTool(tool.key)
                              setHeaderToolPopupOpen(null)
                            }}
                          >
                            {selected ? '保持启用' : '启用工具'}
                          </Button>
                          <Button size="small" onClick={() => setHeaderToolPopupOpen(null)}>
                            关闭
                          </Button>
                        </div>
                      </div>
                    }
                  >
                    <Button
                      size="small"
                      type={selected ? 'primary' : 'default'}
                      icon={tool.key === 'move' ? <EyeOutlined /> : <DotChartOutlined />}
                      onClick={() => setCurrentMouseTool(tool.key)}
                      data-datashow-header-tool={tool.key}
                    >
                      {tool.title}
                    </Button>
                  </Popover>
                )
              })}
            </div>
          ) : null}
          {viewMode === 'three' ? (
            <div
              className="data-show-3d-header-controls"
              data-datashow-3d-header-controls
              data-datashow-3d-z-scale={view3DZScale.toFixed(2)}
              data-datashow-3d-control-mode={view3DControlMode}
            >
              <span className="data-show-3d-header-label">Z轴缩放</span>
              <Slider
                min={0.1}
                max={2}
                step={0.01}
                value={view3DZScale}
                onChange={(value) => setView3DZScale(normalizeCanvas3DZScale(value))}
                tooltip={{ formatter: (value) => normalizeCanvas3DZScale(value).toFixed(2) }}
              />
              <Tag color="cyan">{view3DZScale.toFixed(2)}</Tag>
              <Dropdown trigger={['click']} menu={{ items: view3DControlMenuItems }}>
                <button
                  type="button"
                  className="data-show-view-3d-change-item"
                  data-datashow-view-3d-change-item
                  data-datashow-view-3d-control-key={view3DControlQmlKey}
                >
                  {view3DControlModeLabel} ▼
                </button>
              </Dropdown>
            </div>
          ) : null}
          <Button
            size="small"
            icon={<AppstoreOutlined />}
            type={viewMode === 'area' ? 'primary' : 'default'}
            onClick={() => setViewMode('area')}
            data-datashow-view-switch="area"
          >
            2D瓦片
          </Button>
          <span
            className="data-show-header-popup-2d-trigger-shell"
            onMouseEnter={openHeader2DPopup}
            onMouseLeave={scheduleHeader2DPopupClose}
            onFocus={openHeader2DPopup}
            onBlur={scheduleHeader2DPopupClose}
          >
            <Popover
              trigger={['hover']}
              placement="bottomRight"
              align={{ offset: [-244, 0] }}
              open={header2DPopupOpen}
              onOpenChange={setHeader2DPopupOpen}
              content={
                currentCoil ? (
                  <div
                    className="data-show-header-popup-2d"
                    data-datashow-header-popup-2d
                    onMouseEnter={openHeader2DPopup}
                    onMouseLeave={scheduleHeader2DPopupClose}
                  >
                    <div
                      className="data-show-view-renderer-list data-show-header-popup-2d-list"
                      data-datashow-header-popup-2d-list
                    >
                      {TWO_DIMENSIONAL_VIEW_KEYS.map((viewKey) => {
                        const viewDataEnabled = hasQmlViewData(dataAvailabilityBySurface[surfaceKey], viewKey)
                        return (
                          <button
                            type="button"
                            key={`header-${viewKey}`}
                            className={`data-show-view-renderer-item ${
                              currentTwoDimensionalViewKey === viewKey ? 'selected' : ''
                            }`}
                            data-datashow-header-popup-2d-key={viewKey}
                            data-qml-view-data-enabled={viewDataEnabled}
                            disabled={!viewDataEnabled}
                            onClick={() => selectCurrentTwoDimensionalView(viewKey)}
                            onDoubleClick={() => setHeader2DPopupOpen(false)}
                          >
                            <img
                              src={resolveQmlSurfaceImageUrl(
                                imageRuntimeSettings,
                                surfaceKey,
                                currentCoil.id,
                                viewKey,
                                true,
                                imageBaseUrl,
                              )}
                              alt={`${surfaceLabel(surfaceKey)} ${viewKey}`}
                            />
                            <span>{viewKey}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ) : null
              }
            >
              <Button
                size="small"
                icon={<EyeOutlined />}
                type={viewMode === currentTwoDimensionalViewMode ? 'primary' : 'default'}
                onClick={() => {
                  openCurrentTwoDimensionalView()
                  openHeader2DPopup()
                }}
                data-datashow-view-switch="current-view-key"
                data-datashow-header-popup-2d-trigger
              >
                {currentTwoDimensionalViewKey}
              </Button>
            </Popover>
          </span>
          <Button
            size="small"
            icon={<BorderOutlined />}
            type={viewMode === 'three' ? 'primary' : 'default'}
            onClick={() => setViewMode('three')}
            data-datashow-view-switch="three"
          >
            3D
          </Button>
          <Button
            size="small"
            type={exclusiveSurface === surfaceKey ? 'primary' : 'default'}
            icon={exclusiveSurface === surfaceKey ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            title="独占/取消独占"
            aria-label="独占/取消独占"
            onClick={toggleDataShowSurfaceExclusive}
            data-datashow-show-max-toggle
            data-datashow-show-max-surface={surfaceKey}
            data-datashow-show-max-active={exclusiveSurface === surfaceKey}
          />
          <Button
            size="small"
            icon={<ReloadOutlined />}
            disabled={!currentCoil}
            onClick={resetDataShowView}
          >
            重置
          </Button>
          <Button
            size="small"
            icon={<LinkOutlined />}
            disabled={!currentCoil}
            onClick={openCurrentDataShowUrl}
          >
            打开URL...
          </Button>
          <Button
            size="small"
            type={manualDefectAddMode ? 'primary' : 'default'}
            icon={<PlusOutlined />}
            disabled={!currentCoil || viewMode !== 'area'}
            onClick={() => setManualDefectAddMode((enabled) => !enabled)}
          >
            新增标注
          </Button>
          <Dropdown trigger={['click']} menu={{ items: dataShowMenuItems, triggerSubMenuAction: 'click' }}>
            <Button size="small" icon={<MenuOutlined />}>
              功能菜单
            </Button>
          </Dropdown>
        </div>
        <div className="load-state">
          <span className="ready">S图像</span>
          <span className="ready">L图像</span>
          <span className={!anyDefectLoading ? 'ready' : ''}>缺陷 {totalDefects}</span>
          <span data-datashow-hidden-defects={hiddenDefectsCount}>隐藏 {hiddenDefectsCount}</span>
        </div>
      </div>

      <div className="data-content">
        <section className="main-view-panel">
          <div className="panel-title main-panel-heading">
            <span>
              {viewMode === 'area'
                ? 'S / L 端面区域瓦片查看'
                : viewMode === 'three'
                  ? `${surfaceLabel(surfaceKey)} 3D数据可视化`
                  : `${surfaceLabel(surfaceKey)} ${activeViewKey} 图像查看`}
            </span>
          </div>
          {viewMode === 'three' && (
            <div
              className="render-settings-bar"
              data-datashow-render-settings
              data-datashow-render-view-key={renderViewKey}
              data-datashow-render-image-type={renderImageTypeText}
            >
              <div className="render-settings-title">
                <strong>渲染设置</strong>
                <Tag color={renderViewKey === 'GRAY' ? 'default' : 'cyan'}>{renderViewKey}</Tag>
                <Tag color={renderViewKey === 'GRAY' ? 'default' : 'green'}>{renderImageTypeText}</Tag>
                <Checkbox checked={autoRender} onChange={(event) => setAutoRender(event.target.checked)}>
                  AOTO
                </Checkbox>
              </div>
              <label className="render-setting-field">
                <span>平面</span>
                <InputNumber
                  size="small"
                  min={-9999}
                  max={9999}
                  value={activeRenderPlaneZMm}
                  onChange={(value) => setRenderPlaneZMm(normalizeRenderPlaneZMm(value))}
                  controls={false}
                />
              </label>
              <label className="render-setting-field">
                <span>范围</span>
                <InputNumber
                  size="small"
                  min={5}
                  max={100}
                  value={renderRangeZ}
                  onChange={(value) => setRenderRangeZ(normalizeRenderRangeZ(value))}
                  controls={false}
                />
              </label>
              <label className="render-setting-field">
                <span>比例</span>
                <Select
                  size="small"
                  value={renderScale}
                  options={RENDER_SCALE_OPTIONS}
                  onChange={setRenderScale}
                  disabled={autoRender}
                />
              </label>
              <Button
                size="small"
                type="primary"
                disabled={!currentCoil || !activeRenderParams || autoRender}
                onClick={rerenderDataShow3D}
              >
                渲染
              </Button>
            </div>
          )}
          <div className="defect-filter-head">
            <div className="defect-class-toggle-list" data-datashow-defect-classes={visibleDataShowDefectClassOptions.length}>
              {visibleDataShowDefectClassOptions.length > 0 ? (
                visibleDataShowDefectClassOptions.map((option) => (
                  <Checkbox
                    key={option.name}
                    checked={selectedDataShowDefectClasses.includes(option.name)}
                    onChange={(event) => setDataShowClassSelection(option.name, event.target.checked)}
                  >
                    <span className="defect-class-name">{option.name}</span>
                    <span className="defect-class-count">{defectClassCounts[option.name] ?? 0}</span>
                  </Checkbox>
                ))
              ) : (
                <span className="defect-class-empty">暂无缺陷类别</span>
              )}
            </div>
            <div className="defect-show-tools">
              <Checkbox checked={showAreaDefects} onChange={(event) => changeAreaDefectVisibility(event.target.checked)}>
                2D类
              </Checkbox>
              <Checkbox checked={showHiddenDefects} onChange={(event) => changeHiddenDefectVisibility(event.target.checked)}>
                屏蔽类
              </Checkbox>
              <Tag color={hiddenDefectsCount > 0 ? 'gold' : 'default'}>隐藏 {hiddenDefectsCount}</Tag>
              <Button size="small" icon={<CloseSquareOutlined />} onClick={clearDataShowDefectClasses}>
                取消
              </Button>
              <Button size="small" icon={<CheckSquareOutlined />} onClick={selectAllDataShowDefectClasses}>
                全选
              </Button>
            </div>
          </div>
          <div className="data-defect-crop-strip" data-datashow-defect-strip={activeSurfaceDefects.length}>
            <div className="data-defect-crop-strip-head">
              <span>{surfaceLabel(surfaceKey)} 缺陷预览</span>
              <Tag color="geekblue">{activeSurfaceDefects.length}</Tag>
            </div>
            <div className="data-defect-crop-list">
              {currentCoil && activeSurfaceDefects.length > 0 ? (
                activeSurfaceDefects.map((defect) => {
                  const cropUrl = imageApi.getDefectImage(
                    surfaceKey,
                    defect.coilId || currentCoil.id,
                    'AREA',
                    defect.position.x,
                    defect.position.y,
                    defect.size.width,
                    defect.size.height,
                    imageBaseUrl,
                  )
                  return (
                    <button
                      type="button"
                      key={`${defect.surface}-${defect.id}`}
                      className={`data-defect-crop-item ${selectedDefect?.id === defect.id ? 'selected' : ''}`}
                      onClick={() => {
                        setViewMode('area')
                        setSelectedDefect(defect)
                      }}
                      onContextMenu={(event) => {
                        event.preventDefault()
                        setViewMode('area')
                        resetDataShowView()
                      }}
                    >
                      <Image src={cropUrl} preview={false} />
                      <span>{defect.defectType}</span>
                      <small>
                        {defect.position.x}, {defect.position.y}
                      </small>
                    </button>
                  )
                })
              ) : (
                <span className="data-defect-crop-empty">暂无当前面缺陷</span>
              )}
            </div>
          </div>
          <Dropdown trigger={['contextMenu']} menu={{ items: dataShowMenuItems, triggerSubMenuAction: 'click' }}>
            <div
              className="main-view-body"
              data-datashow-background-watermark={shouldShowDataShowWatermark ? 'true' : 'false'}
              data-datashow-mask-tool-menu
              data-datashow-mask-tool-context="main-show-menu"
            >
              {shouldShowDataShowWatermark ? (
                <div className="data-show-watermark" data-datashow-watermark aria-hidden="true">
                  <div className="data-show-watermark-grid">
                    {Array.from({ length: 24 }).map((_, index) => (
                      <span key={index} className="data-show-watermark-tile" data-datashow-watermark-tile>
                        <img src={ustbDarkWatermarkUrl} alt="" />
                        <img src={ustbLightWatermarkUrl} alt="" />
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
              {!currentCoil ? (
                <Empty description="请选择卷材" />
              ) : viewMode === 'area' ? (
                <div
                  className={`surface-split-view ${exclusiveSurface ? 'exclusive' : ''}`}
                  data-datashow-area-surfaces={visibleAreaSurfaces.join(',')}
                  data-datashow-area-lock-control={dataShowLockControl ? 'true' : 'false'}
                >
                  {visibleAreaSurfaces.length > 0 ? (
                    visibleAreaSurfaces.map((surface) => (
                      <section key={surface} className="surface-view-panel">
                        <div className="surface-view-title">
                          <strong>{surfaceLabel(surface)}</strong>
                          <Tag color={surface === 'S' ? 'blue' : 'purple'}>
                            {defectsBySurface[surface].length}/{rawDefectsBySurface[surface].length} 缺陷
                          </Tag>
                        </div>
                        <div className="surface-view-body">
                          <TileImageViewer
                            imageUrl={resolveQmlSurfaceImageUrl(
                              imageRuntimeSettings,
                              surface,
                              currentCoil.id,
                              activeAreaViewKey,
                              false,
                              imageBaseUrl,
                            )}
                            previewUrl={resolveQmlSurfaceImageUrl(
                              imageRuntimeSettings,
                              surface,
                              currentCoil.id,
                              activeAreaViewKey,
                              true,
                              imageBaseUrl,
                            )}
                            defects={defectsBySurface[surface]}
                            selectedDefectId={selectedDefect?.surface === surface ? selectedDefect.id : null}
                            tileCount={defaultAreaTileCount}
                            canvasScale={dataShowCanvasScale}
                            showTileDebugBorders={showTileDebugBorders}
                            enable1024CacheMode={enable1024CacheMode}
                            showDefectLabels={showDefectLabels}
                            showAerialView
                            surfaceKey={surface}
                            coilId={currentCoil.id}
                            pointValueShowType={pointValueShowType}
                            pointValueOptions={pointValueOptionsBySurface[surface]}
                            focusSelectedDefect
                            resetSignal={viewResetSignal}
                            manualAnnotationMode={manualDefectAddMode}
                            controlledTransform={dataShowLockControl ? lockedAreaTransform : null}
                            onDefectSelect={setSelectedDefect}
                            onManualAnnotation={(rect) => handleDataShowManualAnnotation(surface, rect)}
                            onTransformChange={dataShowLockControl ? setLockedAreaTransform : undefined}
                            onQmlScaleMetricsChange={
                              surface === surfaceKey ? handleDataShowQmlScaleMetricsChange : undefined
                            }
                          />
                        </div>
                      </section>
                    ))
                  ) : (
                    <div className="surface-view-empty" data-datashow-area-empty>
                      暂无可见端面
                    </div>
                  )}
                </div>
              ) : viewMode === 'gray' || viewMode === 'depth' ? (
                <section className="surface-view-panel surface-single-view-panel">
                  <div className="surface-view-title">
                    <strong>{surfaceLabel(surfaceKey)}</strong>
                    <Tag color={viewMode === 'gray' ? 'default' : 'cyan'}>{activeViewKey}</Tag>
                    <Tag color="geekblue">
                      {defectsBySurface[surfaceKey].length}/{rawDefectsBySurface[surfaceKey].length} 缺陷
                    </Tag>
                  </div>
                  <div className="surface-view-body">
                    <div className={`surface-single-view-content ${activeXyzListItems.length > 0 ? 'with-xyz' : ''}`}>
                      <div className="surface-single-image-pane">
                        <TileImageViewer
                          imageUrl={resolveQmlSurfaceImageUrl(
                            imageRuntimeSettings,
                            surfaceKey,
                            currentCoil.id,
                            activeViewKey,
                            false,
                            imageBaseUrl,
                          )}
                          previewUrl={resolveQmlSurfaceImageUrl(
                            imageRuntimeSettings,
                            surfaceKey,
                            currentCoil.id,
                            activeViewKey,
                            true,
                            imageBaseUrl,
                          )}
                          defects={defectsBySurface[surfaceKey]}
                          selectedDefectId={selectedDefect?.surface === surfaceKey ? selectedDefect.id : null}
                          tileCount={defaultAreaTileCount}
                          tiled={false}
                          canvasScale={dataShowCanvasScale}
                          imageGamma={viewMode === 'gray' ? imageGamma : null}
                          showTileDebugBorders={showTileDebugBorders}
                          enable1024CacheMode={enable1024CacheMode}
                          showDefectLabels={showDefectLabels}
                          showAerialView
                          showQmlCrossView
                          enableQmlUserPoints
                          qmlUserPoints={qmlUserPointsBySurface[surfaceKey]}
                          qmlDbPoints={pointDataBySurface[surfaceKey]}
                          qmlDbPointInnerEllipse={dbPointInnerEllipseBySurface[surfaceKey]}
                          qmlDrawViewLineSegments={heightLineDataBySurface[surfaceKey]}
                          qmlDrawViewInnerEllipse={dbPointInnerEllipseBySurface[surfaceKey]}
                          qmlDrawViewPerpendicularLine={qmlDrawViewPerpendicularLine}
                          qmlDrawViewTaperEnabled={taperShapeAnnotationEnabled}
                          mouseTool={currentMouseTool}
                          crossWarningThresholdUp={towerWarningThresholdUp}
                          crossWarningThresholdDown={towerWarningThresholdDown}
                          surfaceKey={surfaceKey}
                          coilId={currentCoil.id}
                          pointValueShowType={pointValueShowType}
                          pointValueOptions={pointValueOptionsBySurface[surfaceKey]}
                          focusSelectedDefect
                          resetSignal={viewResetSignal}
                          manualAnnotationMode={false}
                          onDefectSelect={setSelectedDefect}
                          onQmlScaleMetricsChange={handleDataShowQmlScaleMetricsChange}
                          onQmlUserPointsChange={handleActiveQmlUserPointsChange}
                        />
                      </div>
                      {activeXyzListItems.length > 0 ? (
                        <aside className="data-show-xyz-list" data-datashow-xyz-list>
                          {activeXyzListItems.map((item) => (
                            <div
                              key={item.id}
                              className="data-show-xyz-row"
                              data-datashow-xyz-row={item.type}
                            >
                              <span className="data-show-xyz-title">{item.title}</span>
                              <span className="data-show-xyz-values">
                                <span className="data-show-xyz-value">{item.xMm}</span>
                                <span className="data-show-xyz-value">{item.yMm}</span>
                                <span className="data-show-xyz-value" data-datashow-xyz-z={item.zColor}>
                                  {item.zMm}
                                </span>
                              </span>
                              <button
                                type="button"
                                className="data-show-xyz-close"
                                data-datashow-xyz-close
                                aria-label={`${item.title} close`}
                                onClick={() => removeDataShowQmlUserPoint(surfaceKey, item.id)}
                                disabled={item.type !== 'user'}
                              >
                                <CloseSquareOutlined />
                              </button>
                            </div>
                          ))}
                        </aside>
                      ) : null}
                    </div>
                  </div>
                </section>
              ) : (
                <Canvas3D
                  data={renderData}
                  heightLineSegments={heightLineData}
                  errorOverlayUrl={errorOverlayUrl}
                  showErrorOverlay={showErrorOverlay}
                  errorOverlayOpacity={towerWarningOpacity / 100}
                  resetSignal={viewResetSignal}
                  zScale={view3DZScale}
                  controlMode={view3DControlMode}
                />
              )}
              {currentCoil && (showQmlViewChang3DThumbnail || showQmlViewChang2DThumbnail) ? (
                <div className="data-show-view-chang" data-datashow-view-chang>
                  {showQmlViewChang3DThumbnail ? (
                    <button
                      type="button"
                      className="data-show-view-chang-button"
                      data-datashow-view-chang-3d
                      onClick={rerenderDataShow3D}
                    >
                      <span
                        className="data-show-view-chang-3d-preview"
                        data-datashow-view-chang-3d-canvas
                        aria-hidden="true"
                      >
                        <Canvas3D
                          data={renderData}
                          heightLineSegments={heightLineData}
                          zScale={view3DZScale}
                          controlMode={view3DControlMode}
                          thumbnail
                        />
                      </span>
                      <span className="data-show-view-chang-label">3D</span>
                    </button>
                  ) : null}
                  {showQmlViewChang2DThumbnail ? (
                    <button
                      type="button"
                      className="data-show-view-chang-button"
                      data-datashow-view-chang-2d
                      data-datashow-view-chang-2d-next-key={nextTwoDimensionalViewKey}
                      onClick={openNextTwoDimensionalThumbnailView}
                    >
                      <span className="data-show-view-chang-2d-preview">
                        <img
                          src={resolveQmlSurfaceImageUrl(
                            imageRuntimeSettings,
                            surfaceKey,
                            currentCoil.id,
                            nextTwoDimensionalViewKey,
                            true,
                            imageBaseUrl,
                          )}
                          alt={`${surfaceLabel(surfaceKey)} ${nextTwoDimensionalViewKey}`}
                          loading="lazy"
                          decoding="async"
                        />
                      </span>
                      <span className="data-show-view-chang-label">{nextTwoDimensionalViewKey}</span>
                    </button>
                  ) : null}
                </div>
              ) : null}
              <div className="data-show-mask-tool-reset-panel" data-datashow-mask-tool-reset-panel>
                <button
                  type="button"
                  className="data-show-mask-tool-reset-button"
                  data-datashow-mask-tool-reset
                  onClick={resetDataShowView}
                >
                  重置
                </button>
              </div>
            </div>
          </Dropdown>
          {showViewRendererListView && currentCoil ? (
            <div
              className="data-show-view-renderer-list"
              data-datashow-view-renderer-list={showViewRendererListView}
            >
              {TWO_DIMENSIONAL_VIEW_KEYS.map((viewKey) => {
                const viewDataEnabled = hasQmlViewData(dataAvailabilityBySurface[surfaceKey], viewKey)
                return (
                  <button
                    type="button"
                    key={viewKey}
                    className={`data-show-view-renderer-item ${
                      currentTwoDimensionalViewKey === viewKey ? 'selected' : ''
                    }`}
                    data-datashow-view-renderer-key={viewKey}
                    data-qml-view-data-enabled={viewDataEnabled}
                    disabled={!viewDataEnabled}
                    onClick={() => selectCurrentTwoDimensionalView(viewKey)}
                    onDoubleClick={() => {
                      selectCurrentTwoDimensionalView(viewKey)
                      setShowViewRendererListView(false)
                    }}
                  >
                    <img
                      src={resolveQmlSurfaceImageUrl(
                        imageRuntimeSettings,
                        surfaceKey,
                        currentCoil.id,
                        viewKey,
                        true,
                        imageBaseUrl,
                      )}
                      alt={`${surfaceLabel(surfaceKey)} ${viewKey}`}
                    />
                    <span>{viewKey}</span>
                  </button>
                )
              })}
            </div>
          ) : null}
          {showViewRendererMaxMinValue && currentCoil ? (
            <div
              className="data-show-max-min-panel"
              data-datashow-max-min-panel={showViewRendererMaxMinValue}
            >
              <div className="data-show-max-min-rectangle" data-datashow-max-min-rectangle />
            </div>
          ) : null}
          <div className="data-show-foot-toolbar" data-datashow-foot-toolbar>
            <Button
              size="small"
              type={showViewRendererListView ? 'primary' : 'default'}
              icon={<EyeOutlined />}
              disabled={!currentCoil}
              onClick={() => setShowViewRendererListView((visible) => !visible)}
              data-datashow-view-renderer-toggle
            >
              视图
            </Button>
            <Button
              size="small"
              type={showViewRendererMaxMinValue ? 'primary' : 'default'}
              icon={<LineChartOutlined />}
              disabled={!currentCoil}
              onClick={() => setShowViewRendererMaxMinValue((visible) => !visible)}
              data-datashow-max-min-toggle
            >
              高低值
            </Button>
            <div className="data-show-foot-separator" data-datashow-foot-separator />
            <div
              className="data-show-foot-msg"
              data-datashow-foot-msg
              data-datashow-foot-median-z-int={footMedianZIntText}
              data-datashow-foot-median-z={footMedianZText}
            >
              <span className="data-show-foot-median-int">{footMedianZIntText}</span>
              <span className="data-show-foot-median-mm">{footMedianZText}</span>
            </div>
            <div
              className="data-show-foot-toolbox-row"
              data-datashow-toolbox-row
              data-datashow-toolbox-taper={taperShapeAnnotationEnabled}
              data-datashow-toolbox-3d={thumbnailView3DEnabled}
              data-datashow-toolbox-3d-mesh-exists={qmlMeshExists}
              data-datashow-toolbox-2d={thumbnailView2DEnabled}
            >
              <span className="data-show-foot-toolbox-title">工具:</span>
              <Checkbox
                checked={taperShapeAnnotationEnabled}
                onChange={(event) => setTaperShapeAnnotationEnabled(event.target.checked)}
              >
                塔形标注
              </Checkbox>
              <Checkbox
                checked={thumbnailView3DEnabled}
                disabled={!qmlMeshExists}
                onChange={(event) => setThumbnailView3DEnabled(event.target.checked)}
              >
                3D预览
              </Checkbox>
              <Checkbox
                checked={thumbnailView2DEnabled}
                onChange={(event) => setThumbnailView2DEnabled(event.target.checked)}
              >
                2D预览
              </Checkbox>
            </div>
          </div>
        </section>
      </div>

      <section className="chart-band" data-datashow-header-mode={headDateShowModel}>
        <Dropdown trigger={['contextMenu']} menu={{ items: dataHeaderSelectMenuItems }}>
          <div className="data-show-item-select-view" data-datashow-item-select-view>
            {DATA_HEADER_MODE_OPTIONS.map((option) => (
              <button
                type="button"
                key={option.value}
                className="data-show-item-select-option"
                aria-label={option.label}
                title={option.label}
                data-datashow-item-select-option={option.value}
                data-datashow-item-select-selected={headDateShowModel === option.value}
                onClick={() => setHeadDateShowModel(option.value)}
              >
                <span className="data-show-item-select-text" aria-hidden="true">
                  {option.label.split('').map((letter, index) => (
                    <span key={`${option.value}-${index}`}>{letter}</span>
                  ))}
                </span>
              </button>
            ))}
          </div>
        </Dropdown>
        <div className="chart-panel">
          <div className="panel-title">
            <div className="chart-title-main">
              <LineChartOutlined />
              {headDateShowModel === 0
                ? `${surfaceLabel(surfaceKey)} 缺陷信息`
                : headDateShowModel === 1
                  ? '数据信息'
                  : `${surfaceLabel(surfaceKey)} 高度曲线`}
              {selectedDefect ? <Tag color="orange">{selectedDefect.defectType}</Tag> : null}
            </div>
            {headDateShowModel === 2 && (
              <div className="height-line-controls">
                {(['x1', 'y1', 'x2', 'y2'] as const).map((key) => (
                  <label key={key} className="height-line-field">
                    <span>{key.toUpperCase()}</span>
                    <InputNumber
                      size="small"
                      min={0}
                      value={lineForm[key]}
                      onChange={(value) => updateLineForm(key, value)}
                      controls={false}
                    />
                  </label>
                ))}
                <Button size="small" type="primary" icon={<LineChartOutlined />} onClick={applyLineCoords}>
                  应用
                </Button>
                <Button size="small" icon={<ReloadOutlined />} onClick={resetLineCoords}>
                  重置
                </Button>
              </div>
            )}
          </div>
          <div className="chart-body">
          {headDateShowModel === 0 ? (
            <div className="data-header-defect-mode">
              <div className="data-header-defect-head" data-qml-defect-show-head>
                <div className="data-header-defect-class-row" data-qml-defect-class-row>
                  {visibleDataShowDefectClassOptions.length > 0 ? (
                    visibleDataShowDefectClassOptions.map((option) => (
                      <button
                        type="button"
                        key={`header-class-${option.name}`}
                        className="data-header-defect-class-item"
                        data-qml-defect-class-item={option.name}
                        data-qml-defect-class-selected={selectedDataShowDefectClasses.includes(option.name)}
                        style={{ '--defect-class-color': option.color ?? '#FFA500' } as CSSProperties}
                        onClick={() =>
                          setDataShowClassSelection(option.name, !selectedDataShowDefectClasses.includes(option.name))
                        }
                      >
                        <span className="data-header-defect-class-count">
                          x {defectClassCounts[option.name] ?? 0}
                        </span>
                        <span className="data-header-defect-class-name">{option.name}</span>
                      </button>
                    ))
                  ) : (
                    <span className="data-header-defect-class-empty">暂无缺陷类别</span>
                  )}
                </div>
                <div className="data-header-defect-tools" data-qml-defect-show-tools>
                  <button
                    type="button"
                    className="data-header-defect-tool"
                    data-qml-defect-show-tool="area"
                    data-qml-defect-tool-checked={showAreaDefects}
                    onClick={() => changeAreaDefectVisibility(!showAreaDefects)}
                  >
                    2D类
                  </button>
                  <button
                    type="button"
                    className="data-header-defect-tool"
                    data-qml-defect-show-tool="hidden"
                    data-qml-defect-tool-checked={showHiddenDefects}
                    onClick={() => changeHiddenDefectVisibility(!showHiddenDefects)}
                  >
                    屏蔽类
                  </button>
                  <strong className="data-header-defect-hidden-count" data-qml-defect-hidden-count>
                    x {hiddenDefectsCount}
                  </strong>
                  <button type="button" className="data-header-defect-tool" onClick={clearDataShowDefectClasses}>
                    取消
                  </button>
                  <button type="button" className="data-header-defect-tool" onClick={selectAllDataShowDefectClasses}>
                    全选
                  </button>
                </div>
              </div>
              <div className="data-header-defect-content">
                <div className="data-header-crop-defect-list" data-qml-show-defect-list>
                  {currentCoil && activeSurfaceDefects.length > 0 ? (
                    activeSurfaceDefects.map((defect) => {
                      const defectIsArea = getDataShowDefectClassName(defect).startsWith('2D_')
                      const cropUrl = getDataHeaderDefectCropUrl(defect, currentTwoDimensionalViewKey, imageBaseUrl)
                      const infoRows = getDataHeaderDefectInfoRows(defect, pointValueOptionsBySurface[surfaceKey])
                      const displayDefectName = getDataHeaderDefectDisplayName(defect, dataHeaderDefectCheckedNames)
                      const defectClassMenuOpen = dataHeaderDefectClassMenu?.defectId === defect.id
                      const openDefectView = () => {
                        setViewMode(defectIsArea ? 'area' : currentTwoDimensionalViewMode)
                        setSelectedDefect(defect)
                      }

                      return (
                        <div
                          role="button"
                          tabIndex={0}
                          key={`header-${defect.surface}-${defect.id}`}
                          className={`data-header-crop-defect-card ${selectedDefect?.id === defect.id ? 'selected' : ''}`}
                          data-qml-crop-defect-show
                          data-qml-crop-defect-area={defectIsArea}
                          onClick={openDefectView}
                          onKeyDown={(event) => {
                            if (event.key !== 'Enter' && event.key !== ' ') return
                            event.preventDefault()
                            openDefectView()
                          }}
                          onContextMenu={(event) => {
                            event.preventDefault()
                            setViewMode(defectIsArea ? 'area' : currentTwoDimensionalViewMode)
                            resetDataShowView()
                          }}
                        >
                          <span className="data-header-crop-defect-image">
                            <img
                              src={cropUrl}
                              alt={`${defect.defectType} ${defect.coilId}`}
                              loading="lazy"
                              decoding="async"
                            />
                            <span className="data-header-crop-defect-focus-frame" data-qml-crop-defect-focus-frame />
                          </span>
                          <span className="data-header-crop-defect-info">
                            <span className="data-header-crop-defect-title">
                              <button
                                type="button"
                                className="data-header-crop-defect-check ok"
                                aria-label="确认缺陷"
                                data-qml-defect-check-ok
                                onClick={(event) => event.stopPropagation()}
                                onKeyDown={(event) => event.stopPropagation()}
                              >
                                √
                              </button>
                              {defectIsArea ? <span className="data-header-crop-defect-area-label">2D </span> : null}
                              <span
                                className="data-header-crop-defect-name"
                                data-qml-defect-select-name
                                onContextMenu={(event) => {
                                  event.preventDefault()
                                  event.stopPropagation()
                                  setDataHeaderDefectClassMenu({ defectId: defect.id })
                                }}
                              >
                                {displayDefectName}
                              </span>
                              <button
                                type="button"
                                className="data-header-crop-defect-check no"
                                aria-label="否定缺陷"
                                data-qml-defect-check-no
                                onClick={(event) => event.stopPropagation()}
                                onKeyDown={(event) => event.stopPropagation()}
                              >
                                ×
                              </button>
                            </span>
                            {defectClassMenuOpen ? (
                              <span
                                className="data-header-crop-defect-menu"
                                data-qml-defect-select-menu
                                ref={defectClassMenuOpen ? dataHeaderDefectClassMenuRef : undefined}
                                onClick={(event) => event.stopPropagation()}
                                onContextMenu={(event) => {
                                  event.preventDefault()
                                  event.stopPropagation()
                                }}
                              >
                                {defectFilterOptions.map((option) => (
                                  <button
                                    type="button"
                                    key={`${defect.id}-${option.name}`}
                                    className="data-header-crop-defect-menu-item"
                                    data-qml-defect-select-menu-item={option.name}
                                    data-qml-defect-class-checked={option.show}
                                    data-qml-defect-class-current={option.name === displayDefectName}
                                    data-qml-defect-class-level={option.level ?? 0}
                                    style={
                                      {
                                        '--defect-class-color': option.color ?? '#FFA500',
                                        '--defect-class-level-color': getQmlDefectClassLevelColor(option.level),
                                      } as CSSProperties
                                    }
                                    onClick={(event) => {
                                      event.stopPropagation()
                                      setDataHeaderDefectCheckedName(defect.id, option.name)
                                      setDataHeaderDefectClassMenu(null)
                                    }}
                                  >
                                    <span>{option.name}</span>
                                  </button>
                                ))}
                              </span>
                            ) : null}
                            <span className="data-header-crop-defect-info-grid" data-qml-crop-defect-info-grid>
                              {infoRows.map((row) => (
                                <span key={`${defect.id}-${row.label}`} className="data-header-crop-defect-info-row">
                                  <span>{row.label}:</span>
                                  <strong>{row.value}</strong>
                                  <span>mm</span>
                                </span>
                              ))}
                            </span>
                          </span>
                          {defectIsArea ? (
                            <span className="data-header-crop-defect-area-frame" data-qml-crop-defect-area-frame />
                          ) : null}
                        </div>
                      )
                    })
                  ) : (
                    <span className="data-header-empty">暂无当前面缺陷</span>
                  )}
                </div>
              </div>
            </div>
          ) : headDateShowModel === 1 ? (
            <div className="data-header-info-mode">
              {dataHeaderInfoSections.map((section) => (
                <section
                  key={section.title}
                  className="data-header-info-section"
                  data-alarm-level={section.level}
                >
                  <header>
                    <span className="data-header-level-dot" />
                    <strong>{section.title}</strong>
                  </header>
                  <div className="data-header-info-grid">
                    {section.fields.map((field) => (
                      <div key={`${section.title}-${field.label}`} className="data-header-info-field">
                        <span>{field.label}</span>
                        <strong>{field.value}</strong>
                      </div>
                    ))}
                  </div>
                </section>
              ))}
            </div>
          ) : currentCoil && !heightLoading ? (
            <HeightChart
              data={heightLineData}
              innerCircleCenter={heightChartInnerCircleCenterBySurface[surfaceKey]}
              scan3dScaleX={pointValueOptionsBySurface[surfaceKey].scan3dScaleX}
              scan3dScaleZ={pointValueOptionsBySurface[surfaceKey].scan3dScaleZ}
              scan3dCoordinateOffsetZ={pointValueOptionsBySurface[surfaceKey].scan3dCoordinateOffsetZ}
              medianZ={getCoilInfoNumber(activeCoilInfo, 'median_3d_mm')}
              warningThresholdUp={towerWarningThresholdUp}
              warningThresholdDown={towerWarningThresholdDown}
              qmlChartShowType={qmlChartShowType}
              onQmlChartShowTypeChange={setQmlChartShowType}
            />
          ) : (
            <div className="chart-placeholder">等待3D数据加载</div>
          )}
          </div>
        </div>
      </section>
      <Modal
        title="添加缺陷标注"
        open={manualDefectAddOpen}
        width={420}
        okText="确定"
        cancelText="取消"
        confirmLoading={manualDefectAddSaving}
        okButtonProps={{ disabled: !manualDefectAddRect }}
        onOk={saveDataShowManualDefect}
        onCancel={cancelDataShowManualDefectAdd}
        destroyOnHidden
      >
        <div className="data-manual-defect-add-form">
          <section>
            <h3>{surfaceLabel(manualDefectAddSurface)} 缺陷位置</h3>
            <div className="data-manual-defect-add-position">
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
              options={defectFilterOptions.map((option) => ({ value: option.name, label: option.name }))}
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
    </div>
  )
}

export default DataShowPage
