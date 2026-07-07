import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'

import { buildHeightPointWsPath, heightDataApi, serviceBaseUrls } from '@/services/api'
import type { DefectData, HeightLineSegment, SurfaceKey } from '@/types'
import type { QmlPointValueShowType } from '@/stores/uiSettingsStore'
import { requestHeightPointByWebSocket } from '@/utils/heightPoint'
import {
  buildQmlHoverPointInfo,
  getQmlCrossViewZColor,
  qmlXToMmText,
  qmlYToMmText,
  type QmlHoverPointInfo,
  type QmlPointValueFormatOptions,
} from '@/utils/qmlPointValue'
import {
  buildQmlAerialTargetTransform,
  buildQmlAerialView,
  buildQmlDbPointOverlay,
  buildQmlDrawViewOverlay,
  buildQmlSurveyOverlay,
  buildQmlUserPointOverlay,
  buildManualAnnotationRect,
  buildCenteredScaleTransform,
  buildDefectFocusTransform,
  buildDefectLabelText,
  buildResetTransform,
  clamp,
  getTileDebugBorderStyle,
  getVisibleTiles,
  normalizeQmlDbPoint,
  normalizeQmlCanvasScale,
  normalizeQmlImageGamma,
  type QmlDrawViewPerpendicularLine,
  type QmlScaleMetrics,
  shouldUsePreviewCache,
  type QmlDbPointInnerEllipse,
  type QmlDbPointSource,
  type Point,
  type Rect,
  type Size,
  type Tile,
} from './utils'
import './TileImageViewer.css'

const tileCache = new Map<string, HTMLImageElement>()
const tileLoading = new Set<string>()

export interface TileImageViewerTransform {
  x: number
  y: number
  scale: number
}

interface TileImageViewerProps {
  imageUrl: string
  previewUrl?: string
  defects?: DefectData[]
  selectedDefectId?: number | null
  tileCount?: number
  maxLevel?: number
  tiled?: boolean
  canvasScale?: number | null
  imageGamma?: number | null
  showTileDebugBorders?: boolean
  enable1024CacheMode?: boolean
  showDefectLabels?: boolean
  showAerialView?: boolean
  showQmlCrossView?: boolean
  enableQmlUserPoints?: boolean
  qmlUserPoints?: QmlUserPointState[]
  qmlDbPoints?: QmlDbPointSource[]
  qmlDbPointInnerEllipse?: QmlDbPointInnerEllipse | null
  qmlDrawViewLineSegments?: HeightLineSegment[]
  qmlDrawViewInnerEllipse?: QmlDbPointInnerEllipse | null
  qmlDrawViewPerpendicularLine?: QmlDrawViewPerpendicularLine | null
  qmlDrawViewTaperEnabled?: boolean
  mouseTool?: 'move' | 'survey'
  crossWarningThresholdUp?: number
  crossWarningThresholdDown?: number
  surfaceKey?: SurfaceKey
  coilId?: number
  pointValueShowType?: QmlPointValueShowType
  pointValueOptions?: QmlPointValueFormatOptions
  focusSelectedDefect?: boolean
  resetSignal?: number
  manualAnnotationMode?: boolean
  controlledTransform?: TileImageViewerTransform | null
  className?: string
  onDefectSelect?: (defect: DefectData | null) => void
  onManualAnnotation?: (rect: Rect) => void
  onTransformChange?: (transform: TileImageViewerTransform) => void
  onQmlScaleMetricsChange?: (metrics: QmlScaleMetrics) => void
  onQmlUserPointsChange?: (update: QmlUserPointUpdate) => void
}

interface ImageInfo extends Size {
  ready: boolean
}

interface HoverPointState {
  screen: Point
  point: Point
  rawValue?: number | string
  loading: boolean
}

interface QmlSurveyState {
  state: 'running' | 'end'
  start: Point
  end: Point
}

export interface QmlUserPointState {
  id: number
  point: Point
  rawValue: number | string
}

export type QmlUserPointUpdate = QmlUserPointState[] | ((points: QmlUserPointState[]) => QmlUserPointState[])

function buildTileUrl(imageUrl: string, tile: Tile, tileCount: number) {
  const url = new URL(imageUrl, window.location.origin)
  // Existing QML/backend contract uses row as the horizontal tile index and col as the vertical tile index.
  url.searchParams.set('row', tile.col.toString())
  url.searchParams.set('col', tile.row.toString())
  url.searchParams.set('count', tileCount.toString())
  url.searchParams.set('level', tile.level.toString())
  return url.toString()
}

function defectRect(defect: DefectData): Rect {
  return {
    x: defect.position.x,
    y: defect.position.y,
    width: defect.size.width,
    height: defect.size.height,
  }
}

function rectContains(rect: Rect, point: Point) {
  return point.x >= rect.x && point.x <= rect.x + rect.width && point.y >= rect.y && point.y <= rect.y + rect.height
}

function resolveLevel(scale: number, maxLevel: number) {
  if (scale >= 1.2) return maxLevel
  if (scale >= 0.75) return Math.min(maxLevel, 3)
  if (scale >= 0.38) return Math.min(maxLevel, 2)
  if (scale >= 0.2) return Math.min(maxLevel, 1)
  return 0
}

export default function TileImageViewer({
  imageUrl,
  previewUrl,
  defects = [],
  selectedDefectId,
  tileCount = 3,
  maxLevel = 4,
  tiled = true,
  canvasScale,
  imageGamma,
  showTileDebugBorders = false,
  enable1024CacheMode = false,
  showDefectLabels = true,
  showAerialView = false,
  showQmlCrossView = false,
  enableQmlUserPoints = false,
  qmlUserPoints,
  qmlDbPoints = [],
  qmlDbPointInnerEllipse = null,
  qmlDrawViewLineSegments = [],
  qmlDrawViewInnerEllipse = null,
  qmlDrawViewPerpendicularLine = null,
  qmlDrawViewTaperEnabled = false,
  mouseTool = 'move',
  crossWarningThresholdUp = 100,
  crossWarningThresholdDown = -100,
  surfaceKey,
  coilId,
  pointValueShowType = 'mm-relative',
  pointValueOptions,
  focusSelectedDefect = false,
  resetSignal,
  manualAnnotationMode = false,
  controlledTransform,
  className,
  onDefectSelect,
  onManualAnnotation,
  onTransformChange,
  onQmlScaleMetricsChange,
  onQmlUserPointsChange,
}: TileImageViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const transformRef = useRef({ x: 0, y: 0, scale: 1 })
  const draggingRef = useRef(false)
  const hoverRequestIdRef = useRef(0)
  const qmlUserPointIdRef = useRef(0)
  const manualAnnotationStartRef = useRef<Point | null>(null)
  const lastPointerRef = useRef<Point>({ x: 0, y: 0 })
  const [imageInfo, setImageInfo] = useState<ImageInfo>({ width: 0, height: 0, ready: false })
  const [level, setLevel] = useState(0)
  const [cursor, setCursor] = useState('grab')
  const [manualAnnotationDraft, setManualAnnotationDraft] = useState<Rect | null>(null)
  const [hoverPoint, setHoverPoint] = useState<HoverPointState | null>(null)
  const [qmlSurveyState, setQmlSurveyState] = useState<QmlSurveyState | null>(null)
  const [internalQmlUserPoints, setInternalQmlUserPoints] = useState<QmlUserPointState[]>([])
  const [qmlScaleMetrics, setQmlScaleMetrics] = useState<QmlScaleMetrics>({ minScale: 1, scale: 1 })
  const qmlScaleMetricsRef = useRef<QmlScaleMetrics>({ minScale: 1, scale: 1 })
  const [frame, setFrame] = useState(0)
  const isQmlSurveyActive = mouseTool === 'survey' && !manualAnnotationMode
  const isQmlUserPointsActive = enableQmlUserPoints && mouseTool === 'move' && !manualAnnotationMode
  const activeQmlUserPoints = qmlUserPoints ?? internalQmlUserPoints

  const normalizedCanvasScale = useMemo(() => normalizeQmlCanvasScale(canvasScale), [canvasScale])
  const normalizedImageGamma = useMemo(() => normalizeQmlImageGamma(imageGamma), [imageGamma])
  const worldToScreen = useCallback((point: Point): Point => {
    const transform = transformRef.current
    return {
      x: point.x * transform.scale + transform.x,
      y: point.y * transform.scale + transform.y,
    }
  }, [])
  const selectedDefect = useMemo(
    () => defects.find((defect) => defect.id === selectedDefectId) ?? null,
    [defects, selectedDefectId],
  )
  const hoverPointInfo = useMemo<QmlHoverPointInfo | null>(() => {
    if (!hoverPoint) return null

    return buildQmlHoverPointInfo({
      point: hoverPoint.point,
      rawValue: hoverPoint.rawValue ?? 0,
      options: {
        ...pointValueOptions,
        pointValueShowType,
      },
    })
  }, [hoverPoint, pointValueOptions, pointValueShowType])
  const qmlShowInfos = useMemo(() => {
    const sourceWidth = Math.trunc(imageInfo.ready ? imageInfo.width : 0)
    const sourceHeight = Math.trunc(imageInfo.ready ? imageInfo.height : 0)
    const displayRect = containerRef.current?.getBoundingClientRect()
    const displayWidth = Math.trunc(displayRect?.width ?? 0)
    const displayHeight = Math.trunc(displayRect?.height ?? 0)

    return {
      hoverX: hoverPointInfo?.x ?? 0,
      hoverY: hoverPointInfo?.y ?? 0,
      widthMm: qmlXToMmText(imageInfo.width, pointValueOptions),
      heightMm: qmlYToMmText(imageInfo.height, pointValueOptions),
      sourcePx: `${sourceWidth}x${sourceHeight}`,
      tilePx:
        sourceWidth > 0 && sourceHeight > 0
          ? `${Math.trunc(sourceWidth / tileCount)}x${Math.trunc(sourceHeight / tileCount)}`
          : '0x0',
      displayPx: `${displayWidth}x${displayHeight}`,
    }
  }, [frame, hoverPointInfo, imageInfo.height, imageInfo.ready, imageInfo.width, pointValueOptions, tileCount])
  const qmlAerialView = useMemo(() => {
    const containerRect = containerRef.current?.getBoundingClientRect()
    if (!showAerialView || !imageInfo.ready || !containerRect) return null

    return buildQmlAerialView({
      container: { width: containerRect.width, height: containerRect.height },
      image: imageInfo,
      transform: transformRef.current,
    })
  }, [frame, imageInfo, showAerialView])
  const qmlCrossViewZColor = hoverPointInfo
    ? getQmlCrossViewZColor(hoverPointInfo.z, {
        thresholdDown: crossWarningThresholdDown,
        thresholdUp: crossWarningThresholdUp,
      })
    : 'green'
  const qmlCrossViewZClass = qmlCrossViewZColor === 'red' ? 'z-warning' : 'z-safe'
  const qmlSurveyOverlay = useMemo(() => {
    if (!isQmlSurveyActive || !qmlSurveyState) return null

    const start = worldToScreen(qmlSurveyState.start)
    const end =
      qmlSurveyState.state === 'running' && hoverPoint ? hoverPoint.screen : worldToScreen(qmlSurveyState.end)

    return buildQmlSurveyOverlay({
      start,
      end,
      scale: transformRef.current.scale,
      scan3dScaleX: pointValueOptions?.scan3dScaleX,
    })
  }, [frame, hoverPoint, isQmlSurveyActive, pointValueOptions?.scan3dScaleX, qmlSurveyState, worldToScreen])
  const qmlUserPointOverlays = useMemo(
    () =>
      enableQmlUserPoints
        ? activeQmlUserPoints.map((userPoint) => ({
            id: userPoint.id,
            overlay: buildQmlUserPointOverlay({
              point: userPoint.point,
              transform: transformRef.current,
              rawValue: userPoint.rawValue,
              pointValueShowType,
              pointValueOptions,
            }),
          }))
        : [],
    [activeQmlUserPoints, enableQmlUserPoints, frame, pointValueOptions, pointValueShowType],
  )
  const qmlDbPointOverlays = useMemo(
    () =>
      qmlDbPoints.flatMap((dbPoint, index) => {
        const normalizedPoint = normalizeQmlDbPoint(dbPoint, index, {
          innerEllipse: qmlDbPointInnerEllipse,
        })
        if (!normalizedPoint) return []

        return [
          {
            id: normalizedPoint.id,
            overlay: buildQmlDbPointOverlay({
              point: normalizedPoint.point,
              labelPoint: normalizedPoint.labelPoint,
              transform: transformRef.current,
              zMm: normalizedPoint.zMm,
            }),
          },
        ]
      }),
    [frame, qmlDbPointInnerEllipse, qmlDbPoints],
  )
  const qmlDrawViewOverlay = useMemo(
    () =>
      buildQmlDrawViewOverlay({
        lineSegments: qmlDrawViewLineSegments,
        innerEllipse: qmlDrawViewInnerEllipse,
        taperSegmentsEnabled: qmlDrawViewTaperEnabled,
        warningThresholdUp: crossWarningThresholdUp,
        warningThresholdDown: crossWarningThresholdDown,
        perpendicularLine: qmlDrawViewPerpendicularLine,
        hoverPoint: hoverPoint?.point,
        transform: transformRef.current,
        pointValueOptions,
      }),
    [
      crossWarningThresholdDown,
      crossWarningThresholdUp,
      frame,
      hoverPoint?.point,
      pointValueOptions,
      qmlDrawViewInnerEllipse,
      qmlDrawViewLineSegments,
      qmlDrawViewPerpendicularLine,
      qmlDrawViewTaperEnabled,
    ],
  )

  const requestDraw = useCallback(() => {
    setFrame((frame) => frame + 1)
  }, [])

  const applyQmlUserPointsChange = useCallback(
    (update: QmlUserPointUpdate) => {
      if (onQmlUserPointsChange) {
        onQmlUserPointsChange(update)
        return
      }

      setInternalQmlUserPoints(update)
    },
    [onQmlUserPointsChange],
  )

  const applyTransform = useCallback(
    (nextTransform: TileImageViewerTransform, notify = true, minScaleOverride?: number) => {
      transformRef.current = nextTransform
      setLevel(resolveLevel(nextTransform.scale, maxLevel))
      if (notify) {
        onTransformChange?.(nextTransform)
      }
      const nextMetrics = { minScale: minScaleOverride ?? qmlScaleMetricsRef.current.minScale, scale: nextTransform.scale }
      qmlScaleMetricsRef.current = nextMetrics
      setQmlScaleMetrics(nextMetrics)
      onQmlScaleMetricsChange?.(nextMetrics)
      requestDraw()
    },
    [maxLevel, onQmlScaleMetricsChange, onTransformChange, requestDraw],
  )

  const resetView = useCallback(() => {
    const container = containerRef.current
    if (!container || !imageInfo.ready) return

    const rect = container.getBoundingClientRect()
    const nextTransform = buildResetTransform({
      container: { width: rect.width, height: rect.height },
      image: imageInfo,
    })
    applyTransform(nextTransform, true, nextTransform.scale)
  }, [applyTransform, imageInfo])

  useEffect(() => {
    if (!imageUrl) {
      setImageInfo({ width: 0, height: 0, ready: false })
      setHoverPoint(null)
      applyQmlUserPointsChange([])
      return
    }

    if (!tiled) {
      let cancelled = false
      const img = new Image()
      img.onload = () => {
        if (cancelled) return
        tileCache.set(imageUrl, img)
        setImageInfo({
          width: img.naturalWidth || img.width || 8192,
          height: img.naturalHeight || img.height || 6144,
          ready: true,
        })
      }
      img.onerror = () => {
        if (cancelled) return
        setImageInfo({ width: 8192, height: 6144, ready: true })
      }
      img.src = imageUrl
      return () => {
        cancelled = true
      }
    }

    const controller = new AbortController()
    const url = new URL(imageUrl, window.location.origin)
    url.searchParams.set('count', '0')

    fetch(url, { signal: controller.signal })
      .then((response) => response.json())
      .then((data: Partial<Size>) => {
        const width = Number(data.width)
        const height = Number(data.height)
        if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
          setImageInfo({ width, height, ready: true })
        } else {
          setImageInfo({ width: 8192, height: 6144, ready: true })
        }
      })
      .catch(() => {
        setImageInfo({ width: 8192, height: 6144, ready: true })
      })

    return () => controller.abort()
  }, [imageUrl, tiled])

  useEffect(() => {
    if (!hoverPoint || !surfaceKey || !coilId || manualAnnotationMode) return

    const requestId = hoverRequestIdRef.current + 1
    hoverRequestIdRef.current = requestId
    const point = hoverPoint.point
    const timer = window.setTimeout(() => {
      void requestHeightPointByWebSocket(
        { surfaceKey, coilId, x: point.x, y: point.y },
        {
          apiBaseUrl: serviceBaseUrls.apiBaseUrl,
          wsBaseUrl: serviceBaseUrls.apiWsBaseUrl,
          wsPath: buildHeightPointWsPath(),
        },
      )
        .catch(() => heightDataApi.getHeightPoint(surfaceKey, coilId, point))
        .then((rawValue) => {
          if (hoverRequestIdRef.current !== requestId) return
          setHoverPoint((current) => {
            if (!current || current.point.x !== point.x || current.point.y !== point.y) return current
            return { ...current, rawValue, loading: false }
          })
        })
        .catch(() => {
          if (hoverRequestIdRef.current !== requestId) return
          setHoverPoint((current) => {
            if (!current || current.point.x !== point.x || current.point.y !== point.y) return current
            return { ...current, loading: false }
          })
        })
    }, 40)

    return () => window.clearTimeout(timer)
  }, [coilId, hoverPoint?.point.x, hoverPoint?.point.y, manualAnnotationMode, surfaceKey])

  useEffect(() => {
    resetView()
  }, [resetView])

  useEffect(() => {
    if (resetSignal === undefined) return
    resetView()
  }, [resetSignal, resetView])

  useEffect(() => {
    if (!controlledTransform || !imageInfo.ready) return

    const current = transformRef.current
    if (
      current.x === controlledTransform.x &&
      current.y === controlledTransform.y &&
      current.scale === controlledTransform.scale
    ) {
      return
    }

    applyTransform(controlledTransform, false)
  }, [applyTransform, controlledTransform, imageInfo.ready])

  useEffect(() => {
    const container = containerRef.current
    if (normalizedCanvasScale == null || !container || !imageInfo.ready) return

    const rect = container.getBoundingClientRect()
    const nextTransform = buildCenteredScaleTransform({
      container: { width: rect.width, height: rect.height },
      image: imageInfo,
      scale: normalizedCanvasScale,
    })
    applyTransform(nextTransform)
  }, [applyTransform, imageInfo, normalizedCanvasScale])

  useEffect(() => {
    const container = containerRef.current
    if (!focusSelectedDefect || !selectedDefect || !container || !imageInfo.ready) return

    const rect = container.getBoundingClientRect()
    const nextTransform = buildDefectFocusTransform({
      container: { width: rect.width, height: rect.height },
      image: imageInfo,
      defect: defectRect(selectedDefect),
    })
    applyTransform(nextTransform)
  }, [applyTransform, focusSelectedDefect, imageInfo, selectedDefect])

  useEffect(() => {
    setCursor(manualAnnotationMode || isQmlSurveyActive ? 'crosshair' : 'grab')
    if (!manualAnnotationMode) {
      manualAnnotationStartRef.current = null
      setManualAnnotationDraft(null)
    } else {
      setHoverPoint(null)
    }
  }, [isQmlSurveyActive, manualAnnotationMode])

  useEffect(() => {
    if (isQmlSurveyActive) return
    setQmlSurveyState(null)
  }, [isQmlSurveyActive])

  useEffect(() => {
    setQmlSurveyState(null)
    applyQmlUserPointsChange([])
  }, [applyQmlUserPointsChange, imageUrl])

  useEffect(() => {
    if (enableQmlUserPoints) return
    applyQmlUserPointsChange([])
  }, [applyQmlUserPointsChange, enableQmlUserPoints])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container || !imageInfo.ready) return

    const dpr = window.devicePixelRatio || 1
    const rect = container.getBoundingClientRect()
    canvas.width = Math.max(1, Math.floor(rect.width * dpr))
    canvas.height = Math.max(1, Math.floor(rect.height * dpr))
    canvas.style.width = `${rect.width}px`
    canvas.style.height = `${rect.height}px`

    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, rect.width, rect.height)
    ctx.fillStyle = '#071018'
    ctx.fillRect(0, 0, rect.width, rect.height)

    const transform = transformRef.current
    if (shouldUsePreviewCache(enable1024CacheMode, previewUrl)) {
      const previewUrlToLoad = previewUrl as string
      const preview = tileCache.get(previewUrlToLoad)
      if (preview?.complete) {
        if (normalizedImageGamma != null) {
          ctx.filter = `brightness(${normalizedImageGamma})`
        }
        ctx.globalAlpha = 0.45
        ctx.drawImage(preview, transform.x, transform.y, imageInfo.width * transform.scale, imageInfo.height * transform.scale)
        ctx.globalAlpha = 1
        ctx.filter = 'none'
      } else if (!tileLoading.has(previewUrlToLoad)) {
        tileLoading.add(previewUrlToLoad)
        const img = new Image()
        img.onload = () => {
          tileCache.set(previewUrlToLoad, img)
          tileLoading.delete(previewUrlToLoad)
          requestDraw()
        }
        img.onerror = () => tileLoading.delete(previewUrlToLoad)
        img.src = previewUrlToLoad
      }
    }

    ctx.save()
    ctx.translate(transform.x, transform.y)
    ctx.scale(transform.scale, transform.scale)

    if (!tiled) {
      const sourceImage = tileCache.get(imageUrl)
      if (sourceImage?.complete) {
        if (normalizedImageGamma != null) {
          ctx.filter = `brightness(${normalizedImageGamma})`
        }
        ctx.drawImage(sourceImage, 0, 0, imageInfo.width, imageInfo.height)
        ctx.filter = 'none'
      } else if (!tileLoading.has(imageUrl)) {
        tileLoading.add(imageUrl)
        const img = new Image()
        img.onload = () => {
          tileCache.set(imageUrl, img)
          tileLoading.delete(imageUrl)
          requestDraw()
        }
        img.onerror = () => tileLoading.delete(imageUrl)
        img.src = imageUrl
      }
    }

    if (tiled) {
      const viewRect = {
        x: -transform.x / transform.scale,
        y: -transform.y / transform.scale,
        width: rect.width / transform.scale,
        height: rect.height / transform.scale,
      }
      const tiles = getVisibleTiles({
        viewRect,
        imageSize: imageInfo,
        tileSize: Math.max(imageInfo.width, imageInfo.height) / tileCount,
        scale: transform.scale,
        fixedLevel: level,
        maxLevel,
      })

      for (const tile of tiles) {
        const url = buildTileUrl(imageUrl, tile, tileCount)
        const cached = tileCache.get(url)
        ctx.fillStyle = '#0b1720'
        ctx.fillRect(tile.x, tile.y, tile.width, tile.height)
        if (cached?.complete) {
          if (normalizedImageGamma != null) {
            ctx.filter = `brightness(${normalizedImageGamma})`
          }
          ctx.drawImage(cached, tile.x, tile.y, tile.width, tile.height)
          ctx.filter = 'none'
        } else if (!tileLoading.has(url)) {
          tileLoading.add(url)
          const img = new Image()
          img.onload = () => {
            tileCache.set(url, img)
            tileLoading.delete(url)
            requestDraw()
          }
          img.onerror = () => tileLoading.delete(url)
          img.src = url
        }
        const debugBorderStyle = getTileDebugBorderStyle(
          showTileDebugBorders,
          cached?.complete ? tile.level : -1,
          level,
          true,
        )
        if (debugBorderStyle) {
          ctx.strokeStyle = debugBorderStyle.color
          ctx.lineWidth = 1 / transform.scale
          ctx.strokeRect(tile.x, tile.y, tile.width, tile.height)
        }
      }
    }

    for (const defect of defects) {
      const rectInfo = defectRect(defect)
      const isSelected = defect.id === selectedDefectId
      ctx.strokeStyle = isSelected ? '#ffb020' : '#ff4d4f'
      ctx.fillStyle = isSelected ? 'rgba(255, 176, 32, 0.16)' : 'rgba(255, 77, 79, 0.12)'
      ctx.lineWidth = (isSelected ? 3 : 2) / transform.scale
      ctx.fillRect(rectInfo.x, rectInfo.y, rectInfo.width, rectInfo.height)
      ctx.strokeRect(rectInfo.x, rectInfo.y, rectInfo.width, rectInfo.height)
      const labelText = buildDefectLabelText(defect, showDefectLabels)
      if (labelText) {
        const fontSize = 12 / transform.scale
        const paddingX = 4 / transform.scale
        const paddingY = 3 / transform.scale
        ctx.font = `${fontSize}px sans-serif`
        const textWidth = ctx.measureText(labelText).width
        const labelX = rectInfo.x
        const labelY = Math.max(0, rectInfo.y - fontSize - paddingY * 2)
        ctx.fillStyle = isSelected ? 'rgba(255, 176, 32, 0.86)' : 'rgba(255, 77, 79, 0.82)'
        ctx.fillRect(labelX, labelY, textWidth + paddingX * 2, fontSize + paddingY * 2)
        ctx.fillStyle = '#ffffff'
        ctx.fillText(labelText, labelX + paddingX, labelY + fontSize + paddingY * 0.6)
      }
    }
    if (manualAnnotationDraft) {
      ctx.strokeStyle = '#ff6b6b'
      ctx.fillStyle = 'rgba(255, 107, 107, 0.25)'
      ctx.lineWidth = 2 / transform.scale
      ctx.fillRect(
        manualAnnotationDraft.x,
        manualAnnotationDraft.y,
        manualAnnotationDraft.width,
        manualAnnotationDraft.height,
      )
      ctx.strokeRect(
        manualAnnotationDraft.x,
        manualAnnotationDraft.y,
        manualAnnotationDraft.width,
        manualAnnotationDraft.height,
      )
    }
    ctx.restore()
  })

  const screenToWorld = (clientX: number, clientY: number): Point | null => {
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return null
    const transform = transformRef.current
    return {
      x: (clientX - rect.left - transform.x) / transform.scale,
      y: (clientY - rect.top - transform.y) / transform.scale,
    }
  }

  const updateHoverPoint = (event: React.PointerEvent) => {
    if (manualAnnotationMode || draggingRef.current || !imageInfo.ready) {
      setHoverPoint(null)
      return
    }

    const rect = canvasRef.current?.getBoundingClientRect()
    const world = screenToWorld(event.clientX, event.clientY)
    if (!rect || !world || world.x < 0 || world.y < 0 || world.x >= imageInfo.width || world.y >= imageInfo.height) {
      setHoverPoint(null)
      return
    }

    const point = {
      x: Math.trunc(world.x),
      y: Math.trunc(world.y),
    }
    const screen = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    }

    setHoverPoint((current) => {
      const samePoint = current?.point.x === point.x && current.point.y === point.y
      return {
        screen,
        point,
        rawValue: samePoint ? current.rawValue : undefined,
        loading: samePoint ? current.loading : Boolean(surfaceKey && coilId),
      }
    })
  }

  const handleWheel = (event: React.WheelEvent) => {
    event.preventDefault()
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    const current = transformRef.current
    const pointer = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    }
    const world = {
      x: (pointer.x - current.x) / current.scale,
      y: (pointer.y - current.y) / current.scale,
    }
    const nextScale = clamp(current.scale * (event.deltaY < 0 ? 1.18 : 0.84), 0.04, 4)
    applyTransform({
      scale: nextScale,
      x: pointer.x - world.x * nextScale,
      y: pointer.y - world.y * nextScale,
    })
  }

  const handlePointerDown = (event: React.PointerEvent) => {
    const world = screenToWorld(event.clientX, event.clientY)
    if (manualAnnotationMode) {
      if (!world) return
      manualAnnotationStartRef.current = world
      setManualAnnotationDraft({ x: Math.round(world.x), y: Math.round(world.y), width: 0, height: 0 })
      requestDraw()
      return
    }
    if (handleQmlSurveyPointer(world, event)) return

    const defect = world ? defects.find((item) => rectContains(defectRect(item), world)) : null
    if (defect) {
      onDefectSelect?.(defect)
      requestDraw()
      return
    }
    draggingRef.current = true
    lastPointerRef.current = { x: event.clientX, y: event.clientY }
    setCursor('grabbing')
  }

  const handlePointerMove = (event: React.PointerEvent) => {
    updateHoverPoint(event)

    if (manualAnnotationMode && manualAnnotationStartRef.current) {
      const world = screenToWorld(event.clientX, event.clientY)
      if (!world) return
      setManualAnnotationDraft(
        buildManualAnnotationRect({
          start: manualAnnotationStartRef.current,
          end: world,
          minSize: 0,
        }),
      )
      requestDraw()
      return
    }

    if (!draggingRef.current) return
    const dx = event.clientX - lastPointerRef.current.x
    const dy = event.clientY - lastPointerRef.current.y
    lastPointerRef.current = { x: event.clientX, y: event.clientY }
    applyTransform({
      ...transformRef.current,
      x: transformRef.current.x + dx,
      y: transformRef.current.y + dy,
    })
  }

  const handlePointerUp = (event: React.PointerEvent) => {
    if (manualAnnotationMode && manualAnnotationStartRef.current) {
      const world = screenToWorld(event.clientX, event.clientY)
      const rect = world
        ? buildManualAnnotationRect({
            start: manualAnnotationStartRef.current,
            end: world,
          })
        : null
      manualAnnotationStartRef.current = null
      setManualAnnotationDraft(null)
      if (rect) {
        onManualAnnotation?.(rect)
      }
      requestDraw()
      return
    }

    draggingRef.current = false
    setCursor(isQmlSurveyActive ? 'crosshair' : 'grab')
  }

  const handlePointerLeave = () => {
    manualAnnotationStartRef.current = null
    setManualAnnotationDraft(null)
    draggingRef.current = false
    setHoverPoint(null)
    setCursor(manualAnnotationMode || isQmlSurveyActive ? 'crosshair' : 'grab')
  }

  const handleQmlUserPointDoubleClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isQmlUserPointsActive || !surfaceKey || !coilId || !imageInfo.ready) return

    const world = screenToWorld(event.clientX, event.clientY)
    if (!world || world.x < 0 || world.y < 0 || world.x >= imageInfo.width || world.y >= imageInfo.height) return

    event.preventDefault()
    const point = {
      x: Math.trunc(world.x),
      y: Math.trunc(world.y),
    }
    const id = qmlUserPointIdRef.current + 1
    qmlUserPointIdRef.current = id
    applyQmlUserPointsChange((points) => [...points, { id, point, rawValue: 0 }])
    void heightDataApi.getHeightPoint(surfaceKey, coilId, point)
      .then((rawValue) => {
        applyQmlUserPointsChange((points) =>
          points.map((userPoint) => (userPoint.id === id ? { ...userPoint, rawValue } : userPoint)),
        )
      })
      .catch(() => undefined)
    requestDraw()
  }

  const handleQmlSurveyPointer = (world: Point | null, event: React.PointerEvent) => {
    if (!isQmlSurveyActive) return false

    event.preventDefault()
    if (
      event.button !== 0 ||
      !world ||
      world.x < 0 ||
      world.y < 0 ||
      world.x >= imageInfo.width ||
      world.y >= imageInfo.height
    ) {
      return true
    }

    const point = {
      x: Math.trunc(world.x),
      y: Math.trunc(world.y),
    }
    setQmlSurveyState((current) => {
      if (!current) {
        return { state: 'running', start: point, end: point }
      }
      if (current.state === 'running') {
        return { ...current, state: 'end', end: point }
      }
      return null
    })
    requestDraw()
    return true
  }

  const handleAerialPointer = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!qmlAerialView || !imageInfo.ready) return

    event.preventDefault()
    event.stopPropagation()
    const containerRect = containerRef.current?.getBoundingClientRect()
    const aerialRect = event.currentTarget.getBoundingClientRect()
    if (!containerRect) return

    applyTransform(
      buildQmlAerialTargetTransform({
        container: { width: containerRect.width, height: containerRect.height },
        image: imageInfo,
        transform: transformRef.current,
        aerial: qmlAerialView,
        point: {
          x: event.clientX - aerialRect.left,
          y: event.clientY - aerialRect.top,
        },
      }),
    )
  }

  return (
    <div
      ref={containerRef}
      className={`tile-image-viewer ${className ?? ''}`}
      data-debug-borders={showTileDebugBorders ? 'true' : 'false'}
      data-defect-labels={showDefectLabels ? 'true' : 'false'}
      data-preview-cache={enable1024CacheMode ? 'true' : 'false'}
      data-manual-annotation={manualAnnotationMode ? 'true' : 'false'}
      data-point-value-show-type={pointValueShowType}
      data-point-value-hud={hoverPoint ? 'true' : 'false'}
      data-tiled={tiled ? 'true' : 'false'}
      data-tile-count={tileCount}
      data-image-url={imageUrl}
      data-preview-url={previewUrl ?? ''}
      data-canvas-scale={normalizedCanvasScale?.toFixed(2) ?? 'auto'}
      data-qml-min-scale={qmlScaleMetrics.minScale.toFixed(2)}
      data-image-gamma={normalizedImageGamma?.toFixed(2) ?? 'none'}
      data-qml-transform-controlled={controlledTransform ? 'true' : 'false'}
      data-qml-mouse-tool={mouseTool}
    >
      <canvas
        ref={canvasRef}
        className="tile-image-canvas"
        style={{ cursor }}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerLeave}
        onDoubleClick={handleQmlUserPointDoubleClick}
      />
      {qmlAerialView && previewUrl ? (
        <div
          className="tile-aerial-view"
          data-qml-aerial-view
          style={{ height: qmlAerialView.height }}
          onPointerDown={handleAerialPointer}
          onPointerMove={(event) => {
            if (event.buttons === 1) {
              handleAerialPointer(event)
            }
          }}
        >
          <img className="tile-aerial-image" src={previewUrl} alt="" draggable={false} />
          <span
            className="tile-aerial-viewport"
            data-qml-aerial-viewport
            style={{
              left: qmlAerialView.viewport.x,
              top: qmlAerialView.viewport.y,
              width: qmlAerialView.viewport.width,
              height: qmlAerialView.viewport.height,
            }}
          />
        </div>
      ) : null}
      {showQmlCrossView && hoverPoint && hoverPointInfo ? (
        <div className="tile-qml-cross-view" data-qml-cross-view>
          <span
            className="tile-qml-cross-anchor"
            style={{
              left: hoverPoint.screen.x,
              top: hoverPoint.screen.y,
            }}
          >
            <span className="tile-qml-cross-line horizontal" data-qml-cross-line="horizontal" />
            <span className="tile-qml-cross-line vertical" data-qml-cross-line="vertical" />
            <span
              className={`tile-qml-cross-label z-value ${qmlCrossViewZClass}`}
              data-qml-cross-label="z"
            >
              {hoverPointInfo.z}
            </span>
          </span>
          <span
            className="tile-qml-cross-label coordinate y-mm"
            data-qml-cross-label="y-mm"
            style={{ top: hoverPoint.screen.y }}
          >
            {hoverPointInfo.yMm} mm
          </span>
          <span
            className="tile-qml-cross-label coordinate x-mm"
            data-qml-cross-label="x-mm"
            style={{ left: hoverPoint.screen.x }}
          >
            {hoverPointInfo.xMm}  mm
          </span>
        </div>
      ) : null}
      {qmlSurveyOverlay && qmlSurveyState ? (
        <div
          className="tile-qml-survey"
          data-qml-draw-survey
          data-qml-survey-state={qmlSurveyState.state}
          style={{
            left: qmlSurveyOverlay.rect.x,
            top: qmlSurveyOverlay.rect.y,
            width: Math.max(qmlSurveyOverlay.rect.width, 1),
            height: Math.max(qmlSurveyOverlay.rect.height, 1),
          }}
        >
          <svg
            className="tile-qml-survey-svg"
            viewBox={`0 0 ${Math.max(qmlSurveyOverlay.rect.width, 1)} ${Math.max(qmlSurveyOverlay.rect.height, 1)}`}
            preserveAspectRatio="none"
          >
            <polyline
              className="tile-qml-survey-path tile-qml-survey-corner"
              data-qml-survey-corner
              points={qmlSurveyOverlay.cornerPolyline}
            />
            <line
              className="tile-qml-survey-path tile-qml-survey-diagonal"
              data-qml-survey-diagonal
              x1={qmlSurveyOverlay.diagonalLine.x1}
              y1={qmlSurveyOverlay.diagonalLine.y1}
              x2={qmlSurveyOverlay.diagonalLine.x2}
              y2={qmlSurveyOverlay.diagonalLine.y2}
            />
          </svg>
          <span className="tile-qml-survey-label width" data-qml-survey-label="width">
            {qmlSurveyOverlay.labels.width}
          </span>
          <span className="tile-qml-survey-label height" data-qml-survey-label="height">
            {qmlSurveyOverlay.labels.height}
          </span>
          <span
            className="tile-qml-survey-label diagonal"
            data-qml-survey-label="diagonal"
            style={{ '--survey-diagonal-rotation': `${qmlSurveyOverlay.diagonalRotation}deg` } as CSSProperties}
          >
            {qmlSurveyOverlay.labels.diagonal}
          </span>
        </div>
      ) : null}
      {qmlDrawViewOverlay.lineSegments.length > 0 ||
      qmlDrawViewOverlay.taperSegments.length > 0 ||
      qmlDrawViewOverlay.ellipse ||
      qmlDrawViewOverlay.perpendicularPoint ? (
        <div className="tile-qml-draw-view" data-qml-draw-view>
          <svg className="tile-qml-draw-view-svg">
            {qmlDrawViewOverlay.lineSegments.map((line, index) => (
              <line
                key={`line-${index}-${line.x1}-${line.y1}-${line.x2}-${line.y2}`}
                className="tile-qml-draw-line"
                data-qml-draw-line
                x1={line.x1}
                y1={line.y1}
                x2={line.x2}
                y2={line.y2}
              />
            ))}
            {qmlDrawViewOverlay.taperSegments.map((line, index) => (
              <line
                key={`taper-${index}-${line.x1}-${line.y1}-${line.x2}-${line.y2}-${line.reverse}`}
                className="tile-qml-draw-taper-line"
                data-qml-draw-taper-line
                data-qml-draw-taper-reverse={line.reverse}
                x1={line.x1}
                y1={line.y1}
                x2={line.x2}
                y2={line.y2}
              />
            ))}
            {qmlDrawViewOverlay.ellipse ? (
              <ellipse
                className="tile-qml-draw-ellipse"
                data-qml-draw-ellipse
                cx={qmlDrawViewOverlay.ellipse.cx}
                cy={qmlDrawViewOverlay.ellipse.cy}
                rx={qmlDrawViewOverlay.ellipse.rx}
                ry={qmlDrawViewOverlay.ellipse.ry}
              />
            ) : null}
            {qmlDrawViewOverlay.axes ? (
              <>
                <line
                  className="tile-qml-draw-axis"
                  data-qml-draw-axis="major"
                  x1={qmlDrawViewOverlay.axes.major.x1}
                  y1={qmlDrawViewOverlay.axes.major.y1}
                  x2={qmlDrawViewOverlay.axes.major.x2}
                  y2={qmlDrawViewOverlay.axes.major.y2}
                />
                <line
                  className="tile-qml-draw-axis"
                  data-qml-draw-axis="minor"
                  x1={qmlDrawViewOverlay.axes.minor.x1}
                  y1={qmlDrawViewOverlay.axes.minor.y1}
                  x2={qmlDrawViewOverlay.axes.minor.x2}
                  y2={qmlDrawViewOverlay.axes.minor.y2}
                />
              </>
            ) : null}
          </svg>
          {qmlDrawViewOverlay.labels ? (
            <>
              <span
                className="tile-qml-draw-label"
                data-qml-draw-label="major"
                style={{
                  left: qmlDrawViewOverlay.labels.major.x,
                  top: qmlDrawViewOverlay.labels.major.y,
                }}
              >
                {qmlDrawViewOverlay.labels.major.text}
              </span>
              <span
                className="tile-qml-draw-label"
                data-qml-draw-label="minor"
                style={{
                  left: qmlDrawViewOverlay.labels.minor.x,
                  top: qmlDrawViewOverlay.labels.minor.y,
                }}
              >
                {qmlDrawViewOverlay.labels.minor.text}
              </span>
            </>
          ) : null}
          {qmlDrawViewOverlay.perpendicularPoint ? (
            <span
              className="tile-qml-draw-perpendicular-point"
              data-qml-draw-perpendicular-point
              style={{
                left: qmlDrawViewOverlay.perpendicularPoint.x,
                top: qmlDrawViewOverlay.perpendicularPoint.y,
              }}
            />
          ) : null}
        </div>
      ) : null}
      {qmlDbPointOverlays.map(({ id, overlay }) => (
        <span
          key={id}
          className="tile-qml-db-point"
          data-qml-db-point
          style={{
            left: overlay.marker.x,
            top: overlay.marker.y,
          }}
        >
          <span className="tile-qml-db-point-marker" data-qml-db-point-marker />
          <span
            className={`tile-qml-db-point-label ${overlay.label.color === 'red' ? 'warning' : ''}`}
            data-qml-db-point-label
            style={{
              left: overlay.label.x - overlay.marker.x,
              top: overlay.label.y - overlay.marker.y,
            }}
          >
            {overlay.label.text}
          </span>
        </span>
      ))}
      {qmlUserPointOverlays.map(({ id, overlay }) => (
        <span
          key={id}
          className="tile-qml-user-point"
          data-qml-user-point
          style={{
            left: overlay.marker.x,
            top: overlay.marker.y,
          }}
        >
          <span className="tile-qml-user-point-marker" data-qml-user-point-marker />
          <span
            className="tile-qml-user-point-label"
            data-qml-user-point-label
            style={{
              left: overlay.label.x - overlay.marker.x,
              top: overlay.label.y - overlay.marker.y,
            }}
          >
            {overlay.label.text}
          </span>
        </span>
      ))}
      <div className="tile-show-infos" data-qml-show-infos>
        <div className="tile-show-info-row">
          <span className="tile-show-info-label">X:</span>
          <span className="tile-show-info-value" data-qml-show-info="hover-x">
            {qmlShowInfos.hoverX}
          </span>
          <span className="tile-show-info-label">Y:</span>
          <span className="tile-show-info-value" data-qml-show-info="hover-y">
            {qmlShowInfos.hoverY}
          </span>
        </div>
        <div className="tile-show-info-row">
          <span className="tile-show-info-label">宽:</span>
          <span className="tile-show-info-value" data-qml-show-info="width-mm">
            {qmlShowInfos.widthMm}
          </span>
          <span className="tile-show-info-label">mm</span>
        </div>
        <div className="tile-show-info-row">
          <span className="tile-show-info-label">高:</span>
          <span className="tile-show-info-value" data-qml-show-info="height-mm">
            {qmlShowInfos.heightMm}
          </span>
          <span className="tile-show-info-label">mm</span>
        </div>
        <div className="tile-show-info-row">
          <span className="tile-show-info-value" data-qml-show-info="source-px">
            {qmlShowInfos.sourcePx}
          </span>
          <span className="tile-show-info-label">px</span>
        </div>
        <div className="tile-show-info-row">
          <span className="tile-show-info-label">瓦片:</span>
          <span className="tile-show-info-value" data-qml-show-info="tile-px">
            {qmlShowInfos.tilePx}
          </span>
          <span className="tile-show-info-label">px</span>
        </div>
        <div className="tile-show-info-row">
          <span className="tile-show-info-label">显示:</span>
          <span className="tile-show-info-value" data-qml-show-info="display-px">
            {qmlShowInfos.displayPx}
          </span>
          <span className="tile-show-info-label">px</span>
        </div>
      </div>
      <div className="tile-image-hud">
        <span>L{level}</span>
        <span>{imageInfo.ready ? `${Math.round(imageInfo.width)} x ${Math.round(imageInfo.height)}` : '加载图像信息'}</span>
        <span>
          {manualAnnotationMode
            ? '拖拽框选标注区域'
            : isQmlSurveyActive
              ? '点击设置测量起点/终点'
              : selectedDefect
                ? `缺陷 ${selectedDefect.defectType}`
                : '滚轮缩放 / 拖拽平移'}
        </span>
      </div>
      {!showQmlCrossView && hoverPoint && hoverPointInfo ? (
        <div
          className="tile-point-value-hud"
          style={{
            left: hoverPoint.screen.x,
            top: hoverPoint.screen.y,
          }}
        >
          <span>
            X {hoverPointInfo.x} / {hoverPointInfo.xMm} mm
          </span>
          <span>
            Y {hoverPointInfo.y} / {hoverPointInfo.yMm} mm
          </span>
          <span>Z {hoverPoint.rawValue === undefined || hoverPoint.loading ? '...' : hoverPointInfo.z}</span>
        </div>
      ) : null}
    </div>
  )
}
