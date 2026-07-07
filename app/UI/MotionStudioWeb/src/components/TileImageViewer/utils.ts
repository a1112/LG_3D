import type { HeightLineSegment } from '@/types'

export interface Point {
  x: number
  y: number
}

export interface Size {
  width: number
  height: number
}

export interface Rect extends Point, Size {}

export interface Tile {
  level: number
  row: number
  col: number
  x: number
  y: number
  width: number
  height: number
}

export interface ViewTransform extends Point {
  scale: number
}

export interface VisibleTileParams {
  viewRect: Rect
  imageSize: Size
  tileSize: number
  scale: number
  fixedLevel?: number
  maxLevel?: number
}

export type TileDebugBorderLabel = 'outside' | 'loading' | 'partial' | 'complete'

export interface TileDebugBorderStyle {
  color: string
  label: TileDebugBorderLabel
}

export interface DefectLabelSource {
  defectType?: string
  confidence?: number
}

export interface ResetTransformParams {
  container: Size
  image: Size
  minScale?: number
  maxScale?: number
}

export interface DefectFocusTransformParams {
  container: Size
  image: Size
  defect: Rect
  qmlMaxScale?: number
}

export interface CenteredScaleTransformParams {
  container: Size
  image: Size
  scale: number
}

export interface QmlScaleMenuOption {
  key: string
  label: string
  value: number
}

export interface QmlScaleMetrics {
  minScale: number
  scale: number
}

export interface QmlAerialViewParams {
  container: Size
  image: Size
  transform: ViewTransform
  width?: number
}

export interface QmlAerialView {
  width: number
  height: number
  viewport: Rect
}

export interface QmlAerialTargetTransformParams extends QmlAerialViewParams {
  aerial: QmlAerialView
  point: Point
}

export interface QmlSurveyOverlayParams {
  start: Point
  end: Point
  scale: number
  scan3dScaleX?: number
}

export interface QmlSurveyOverlay {
  rect: Rect
  drawWidth: number
  drawHeight: number
  diagonalRotation: number
  labels: {
    width: string
    height: string
    diagonal: string
  }
  cornerPolyline: string
  diagonalLine: {
    x1: number
    y1: number
    x2: number
    y2: number
  }
}

export type QmlUserPointValueShowType = 'mm-relative' | 'mm-absolute' | 'int-raw'

export interface QmlUserPointOverlayParams {
  point: Point
  transform: ViewTransform
  rawValue: number | string
  pointValueShowType?: QmlUserPointValueShowType
  pointValueOptions?: {
    scan3dScaleZ?: number
    scan3dCoordinateOffsetZ?: number
    medianZ?: number
  }
}

export interface QmlUserPointOverlay {
  marker: Rect
  label: Point & {
    text: string
    color: 'yellow'
  }
}

export type QmlDbPointLabelColor = 'yellow' | 'red'

export interface QmlDbPointSource {
  Id?: number | string | null
  id?: number | string | null
  x?: number | string | null
  y?: number | string | null
  z?: number | string | null
  z_mm?: number | string | null
  type?: string | null
  [key: string]: unknown
}

export interface QmlDbPointInnerEllipse {
  center: Point
  axes: Size
}

export interface ProjectQmlDbPointLabelParams {
  point: Point
  type?: string | null
  innerEllipse?: QmlDbPointInnerEllipse | null
}

export interface NormalizeQmlDbPointOptions {
  innerEllipse?: QmlDbPointInnerEllipse | null
}

export interface QmlDbPoint {
  id: string
  point: Point
  labelPoint: Point
  zMm: number
  type: string
}

export interface QmlDbPointOverlayParams {
  point: Point
  labelPoint: Point
  transform: ViewTransform
  zMm: number
}

export interface QmlDbPointOverlay {
  marker: Rect
  label: Point & {
    text: string
    color: QmlDbPointLabelColor
  }
}

export interface QmlDrawViewOverlayParams {
  lineSegments?: HeightLineSegment[]
  innerEllipse?: QmlDbPointInnerEllipse | null
  taperSegmentsEnabled?: boolean
  warningThresholdUp?: number | null
  warningThresholdDown?: number | null
  perpendicularLine?: QmlDrawViewPerpendicularLine | null
  hoverPoint?: Point | null
  transform: ViewTransform
  pointValueOptions?: {
    scan3dScaleX?: number | null
    scan3dScaleZ?: number | null
    scan3dCoordinateOffsetZ?: number | null
    medianZ?: number | null
  }
}

export interface QmlDrawViewLineOverlay {
  x1: number
  y1: number
  x2: number
  y2: number
}

export interface QmlDrawViewTaperLineOverlay extends QmlDrawViewLineOverlay {
  reverse: number
}

export interface QmlDrawViewEllipseOverlay {
  cx: number
  cy: number
  rx: number
  ry: number
}

export interface QmlDrawViewLabelOverlay extends Point {
  text: string
}

export interface QmlDrawViewPerpendicularLine {
  start: Point
  end: Point
}

export interface QmlDrawViewOverlay {
  lineSegments: QmlDrawViewLineOverlay[]
  taperSegments: QmlDrawViewTaperLineOverlay[]
  ellipse: QmlDrawViewEllipseOverlay | null
  axes: {
    major: QmlDrawViewLineOverlay
    minor: QmlDrawViewLineOverlay
  } | null
  labels: {
    major: QmlDrawViewLabelOverlay
    minor: QmlDrawViewLabelOverlay
  } | null
  perpendicularPoint: Rect | null
}

export interface ManualAnnotationRectParams {
  start: Point
  end: Point
  minSize?: number
}

const DEFAULT_SCAN_3D_SCALE_X = 0.33693358302116394
const DEFAULT_SCAN_3D_SCALE_Z = 0.016229506582021713

export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

export function buildResetTransform({
  container,
  image,
  minScale = 0.04,
  maxScale = 3,
}: ResetTransformParams): ViewTransform {
  if (container.width <= 0 || container.height <= 0 || image.width <= 0 || image.height <= 0) {
    return { x: 0, y: 0, scale: 1 }
  }

  const fittedScale = Math.min(container.width / image.width, container.height / image.height)
  const scale = clamp(fittedScale, minScale, maxScale)
  return {
    scale,
    x: Math.max(0, (container.width - image.width * scale) / 2),
    y: Math.max(0, (container.height - image.height * scale) / 2),
  }
}

export function buildDefectFocusTransform({
  container,
  image,
  defect,
  qmlMaxScale = 1,
}: DefectFocusTransformParams): ViewTransform {
  if (container.width <= 0 || container.height <= 0 || image.width <= 0 || image.height <= 0) {
    return { x: 0, y: 0, scale: 1 }
  }

  const fittedScale = Math.min(container.width / image.width, container.height / image.height)
  const scale = Math.max(fittedScale, qmlMaxScale)
  const targetCenterX = (defect.x + defect.width / 2) * scale
  const targetCenterY = (defect.y + defect.height / 2) * scale
  const minX = Math.min(0, container.width - image.width * scale)
  const minY = Math.min(0, container.height - image.height * scale)

  return {
    scale,
    x: clamp(container.width / 2 - targetCenterX, minX, 0),
    y: clamp(container.height / 2 - targetCenterY, minY, 0),
  }
}

export function normalizeQmlCanvasScale(value: number | null | undefined): number | null {
  if (value == null) return null

  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return null

  return Math.round(clamp(numberValue, 0.04, 4) * 100) / 100
}

export function buildQmlScaleMenuOptions(minScale: number): QmlScaleMenuOption[] {
  const normalizedMinScale = normalizeQmlCanvasScale(minScale)
  if (normalizedMinScale == null) {
    return [{ key: '1.00', label: '100%', value: 1 }]
  }

  return Array.from({ length: 6 }, (_, index) => {
    const value = Math.round((normalizedMinScale + ((1 - normalizedMinScale) / 5) * index) * 100) / 100
    return {
      key: value.toFixed(2),
      label: `${Math.round(value * 100)}%`,
      value,
    }
  })
}

export function normalizeQmlImageGamma(value: number | null | undefined): number | null {
  if (value == null) return null

  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return null

  const clamped = clamp(numberValue, 0.3, 1.3)
  const stepped = Math.round(clamped / 0.05) * 0.05
  return Math.round(stepped * 100) / 100
}

export function buildCenteredScaleTransform({
  container,
  image,
  scale,
}: CenteredScaleTransformParams): ViewTransform {
  const normalizedScale = normalizeQmlCanvasScale(scale) ?? 1
  if (container.width <= 0 || container.height <= 0 || image.width <= 0 || image.height <= 0) {
    return { x: 0, y: 0, scale: normalizedScale }
  }

  const scaledWidth = image.width * normalizedScale
  const scaledHeight = image.height * normalizedScale
  const minX = Math.min(0, container.width - scaledWidth)
  const minY = Math.min(0, container.height - scaledHeight)

  return {
    scale: normalizedScale,
    x: clamp((container.width - scaledWidth) / 2, minX, 0),
    y: clamp((container.height - scaledHeight) / 2, minY, 0),
  }
}

export function buildQmlAerialView({
  container,
  image,
  transform,
  width = 100,
}: QmlAerialViewParams): QmlAerialView {
  if (container.width <= 0 || container.height <= 0 || image.width <= 0 || image.height <= 0) {
    return {
      width,
      height: width,
      viewport: { x: 0, y: 0, width, height: width },
    }
  }

  const aspectRatio = image.width / image.height
  const height = width / aspectRatio
  const visibleWidth = container.width / transform.scale
  const visibleHeight = container.height / transform.scale
  const contentX = Math.max(0, -transform.x / transform.scale)
  const contentY = Math.max(0, -transform.y / transform.scale)

  return {
    width,
    height,
    viewport: {
      x: clamp((contentX / image.width) * width, 0, width),
      y: clamp((contentY / image.height) * height, 0, height),
      width: clamp((visibleWidth / image.width) * width, 0, width),
      height: clamp((visibleHeight / image.height) * height, 0, height),
    },
  }
}

export function buildQmlAerialTargetTransform({
  container,
  image,
  transform,
  aerial,
  point,
}: QmlAerialTargetTransformParams): ViewTransform {
  if (container.width <= 0 || container.height <= 0 || image.width <= 0 || image.height <= 0) {
    return transform
  }

  const visibleWidth = container.width / transform.scale
  const visibleHeight = container.height / transform.scale
  const maxContentX = Math.max(0, image.width - visibleWidth)
  const maxContentY = Math.max(0, image.height - visibleHeight)
  const contentX = clamp(((point.x - aerial.viewport.height / 2) / aerial.width) * image.width, 0, maxContentX)
  const contentY = clamp(((point.y - aerial.viewport.height / 2) / aerial.height) * image.height, 0, maxContentY)

  return {
    scale: transform.scale,
    x: -contentX * transform.scale,
    y: -contentY * transform.scale,
  }
}

export function buildQmlSurveyOverlay({
  start,
  end,
  scale,
  scan3dScaleX = DEFAULT_SCAN_3D_SCALE_X,
}: QmlSurveyOverlayParams): QmlSurveyOverlay {
  const safeScale = Number.isFinite(scale) && scale > 0 ? scale : 1
  const safeScanScaleX = Number.isFinite(scan3dScaleX) ? scan3dScaleX : DEFAULT_SCAN_3D_SCALE_X
  const drawWidth = end.x - start.x
  const drawHeight = end.y - start.y
  const width = Math.abs(drawWidth)
  const height = Math.abs(drawHeight)
  const rect = {
    x: Math.min(start.x, end.x),
    y: Math.min(start.y, end.y),
    width,
    height,
  }
  const toMmLabel = (screenPixels: number) => `${((Math.abs(screenPixels) / safeScale) * safeScanScaleX).toFixed(0)} mm`
  const diagonalPixels = Math.sqrt(drawWidth ** 2 + drawHeight ** 2)
  const sameDirection = drawWidth * drawHeight > 0
  const diagonalRotation =
    drawWidth === 0 && drawHeight === 0
      ? 0
      : Math.round(Math.atan(drawHeight / drawWidth) * (180 / Math.PI) * 100) / 100

  return {
    rect,
    drawWidth,
    drawHeight,
    diagonalRotation,
    labels: {
      width: toMmLabel(drawWidth),
      height: toMmLabel(drawHeight),
      diagonal: toMmLabel(diagonalPixels),
    },
    cornerPolyline: sameDirection
      ? `0,0 ${width},0 ${width},${height}`
      : `${width},0 ${width},${height} 0,${height}`,
    diagonalLine: sameDirection
      ? { x1: 0, y1: 0, x2: width, y2: height }
      : { x1: width, y1: 0, x2: 0, y2: height },
  }
}

export function buildQmlUserPointOverlay({
  point,
  transform,
  rawValue,
  pointValueShowType = 'mm-relative',
  pointValueOptions,
}: QmlUserPointOverlayParams): QmlUserPointOverlay {
  const screen = {
    x: point.x * transform.scale + transform.x,
    y: point.y * transform.scale + transform.y,
  }
  const numericRawValue = Number(rawValue)
  const safeRawValue = Number.isFinite(numericRawValue) ? numericRawValue : 0
  const scan3dScaleZ = Number.isFinite(pointValueOptions?.scan3dScaleZ)
    ? Number(pointValueOptions?.scan3dScaleZ)
    : DEFAULT_SCAN_3D_SCALE_Z
  const scan3dCoordinateOffsetZ = Number.isFinite(pointValueOptions?.scan3dCoordinateOffsetZ)
    ? Number(pointValueOptions?.scan3dCoordinateOffsetZ)
    : 0
  const medianZ = Number.isFinite(pointValueOptions?.medianZ) ? Number(pointValueOptions?.medianZ) : 0
  const absoluteMm = safeRawValue * scan3dScaleZ + scan3dCoordinateOffsetZ
  const relativeMm = (safeRawValue - medianZ) * scan3dScaleZ
  const text =
    pointValueShowType === 'int-raw'
      ? String(rawValue)
      : safeRawValue < 0.01
        ? '-inf'
        : pointValueShowType === 'mm-absolute'
          ? absoluteMm.toFixed(2)
          : relativeMm.toFixed(2)

  return {
    marker: {
      x: screen.x - 4,
      y: screen.y - 4,
      width: 8,
      height: 8,
    },
    label: {
      x: screen.x,
      y: screen.y + 4,
      text,
      color: 'yellow',
    },
  }
}

function finiteNumber(value: unknown): number | null {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function recordValue(value: unknown): Record<string, unknown> | null {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>
  }

  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value) as unknown
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
        ? (parsed as Record<string, unknown>)
        : null
    } catch {
      return null
    }
  }

  return null
}

function pointFromTupleOrObject(value: unknown): Point | null {
  if (Array.isArray(value)) {
    const x = finiteNumber(value[0])
    const y = finiteNumber(value[1])
    return x == null || y == null ? null : { x, y }
  }

  const record = recordValue(value)
  if (!record) return null

  const x = finiteNumber(record.x ?? record['0'])
  const y = finiteNumber(record.y ?? record['1'])
  return x == null || y == null ? null : { x, y }
}

function sizeFromTupleOrObject(value: unknown): Size | null {
  if (Array.isArray(value)) {
    const width = finiteNumber(value[0])
    const height = finiteNumber(value[1])
    return width == null || height == null ? null : { width, height }
  }

  const record = recordValue(value)
  if (!record) return null

  const width = finiteNumber(record.width ?? record.major_axis ?? record.majorAxis ?? record['0'])
  const height = finiteNumber(record.height ?? record.minor_axis ?? record.minorAxis ?? record['1'])
  return width == null || height == null ? null : { width, height }
}

function ellipseFromTupleOrObject(value: unknown): QmlDbPointInnerEllipse | null {
  if (Array.isArray(value)) {
    const center = pointFromTupleOrObject(value[0])
    const axes = sizeFromTupleOrObject(value[1])
    return center && axes ? { center, axes } : null
  }

  const record = recordValue(value)
  if (!record) return null

  const center = pointFromTupleOrObject(record.center)
  const axes = sizeFromTupleOrObject(record.axes)
  return center && axes ? { center, axes } : null
}

export function normalizeQmlDbPointInnerEllipse(source: unknown): QmlDbPointInnerEllipse | null {
  const record = recordValue(source)
  if (!record) return null

  const circleConfig = recordValue(record.circleConfig)
  const innerCircle = recordValue(circleConfig?.inner_circle) ?? recordValue(record.inner_circle)
  const ellipse = ellipseFromTupleOrObject(innerCircle?.ellipse ?? record.inner_ellipse ?? record.ellipse)
  if (ellipse) return ellipse

  const centerX = finiteNumber(record.inner_circle_center_x ?? innerCircle?.inner_circle_center_x)
  const centerY = finiteNumber(record.inner_circle_center_y ?? innerCircle?.inner_circle_center_y)
  const width = finiteNumber(record.inner_circle_width ?? innerCircle?.inner_circle_width)
  const height = finiteNumber(record.inner_circle_height ?? innerCircle?.inner_circle_height ?? width)

  if (centerX == null || centerY == null || width == null || height == null) return null
  return {
    center: { x: centerX, y: centerY },
    axes: { width, height },
  }
}

export function projectQmlDbPointLabel({
  point,
  type,
  innerEllipse,
}: ProjectQmlDbPointLabelParams): Point {
  if (!innerEllipse) return point

  const pointType = String(type ?? '')
  const center = innerEllipse.center
  const ellipseWidth = Math.min(innerEllipse.axes.width, innerEllipse.axes.height)
  const dx = point.x - center.x
  const dy = point.y - center.y
  const distance = Math.sqrt(dx ** 2 + dy ** 2)
  if (!Number.isFinite(distance) || distance === 0) return point

  let radius: number
  if (pointType === 'max_inner') {
    radius = ellipseWidth / 2 - 100
  } else if (pointType === 'min_inner') {
    radius = ellipseWidth / 2 - 200
  } else if (pointType === 'max_outer') {
    radius = distance - 100
  } else if (pointType === 'min_outer') {
    radius = distance - 200
  } else {
    return point
  }

  return {
    x: center.x + (dx / distance) * radius,
    y: center.y + (dy / distance) * radius,
  }
}

export function normalizeQmlDbPoint(
  source: QmlDbPointSource,
  index: number,
  options: NormalizeQmlDbPointOptions = {},
): QmlDbPoint | null {
  if (!source) return null

  const x = finiteNumber(source.x)
  const y = finiteNumber(source.y)
  if (x == null || y == null) return null

  const zMm = finiteNumber(source.z_mm ?? source.z)
  if (zMm == null || zMm < 15) return null

  const type = String(source.type ?? '')
  const point = { x, y }
  return {
    id: String(source.Id ?? source.id ?? index),
    point,
    labelPoint: projectQmlDbPointLabel({
      point,
      type,
      innerEllipse: options.innerEllipse,
    }),
    zMm,
    type,
  }
}

export function buildQmlDbPointOverlay({
  point,
  labelPoint,
  transform,
  zMm,
}: QmlDbPointOverlayParams): QmlDbPointOverlay {
  const markerScreen = {
    x: point.x * transform.scale + transform.x,
    y: point.y * transform.scale + transform.y,
  }
  const labelScreen = {
    x: labelPoint.x * transform.scale + transform.x,
    y: labelPoint.y * transform.scale + transform.y,
  }

  return {
    marker: {
      x: markerScreen.x - 2,
      y: markerScreen.y - 2,
      width: 4,
      height: 4,
    },
    label: {
      x: labelScreen.x,
      y: labelScreen.y,
      text: zMm.toFixed(0),
      color: zMm > 50 ? 'red' : 'yellow',
    },
  }
}

function roundOverlayNumber(value: number): number {
  return Math.round(value * 1000) / 1000
}

function qmlDrawLinePoint(value: unknown): Point | null {
  if (!Array.isArray(value)) return null

  const x = finiteNumber(value[0])
  const y = finiteNumber(value[1])
  return x == null || y == null ? null : { x, y }
}

function qmlDrawScreenPoint(point: Point, transform: ViewTransform): Point {
  return {
    x: roundOverlayNumber(point.x * transform.scale + transform.x),
    y: roundOverlayNumber(point.y * transform.scale + transform.y),
  }
}

function qmlDrawDimensionText(value: number, scan3dScaleX = DEFAULT_SCAN_3D_SCALE_X): string {
  const scale = Number.isFinite(scan3dScaleX) ? scan3dScaleX : DEFAULT_SCAN_3D_SCALE_X
  return (value * scale).toFixed(0)
}

function qmlDrawRelativeZValue(
  rawValue: unknown,
  pointValueOptions: QmlDrawViewOverlayParams['pointValueOptions'],
): number {
  const value = finiteNumber(rawValue)
  if (value == null || value <= 0) return 0

  const scaleZ = Number.isFinite(pointValueOptions?.scan3dScaleZ)
    ? Number(pointValueOptions?.scan3dScaleZ)
    : DEFAULT_SCAN_3D_SCALE_Z
  const offsetZ = Number.isFinite(pointValueOptions?.scan3dCoordinateOffsetZ)
    ? Number(pointValueOptions?.scan3dCoordinateOffsetZ)
    : 0
  const medianZ = Number.isFinite(pointValueOptions?.medianZ) ? Number(pointValueOptions?.medianZ) : 0
  return value * scaleZ + offsetZ - medianZ
}

function qmlDrawDistance(start: Point, end: Point): number {
  return Math.sqrt((start.x - end.x) ** 2 + (start.y - end.y) ** 2)
}

function buildQmlDrawTaperSegments({
  lineSegments,
  transform,
  pointValueOptions,
  warningThresholdUp,
  warningThresholdDown,
}: {
  lineSegments: HeightLineSegment[]
  transform: ViewTransform
  pointValueOptions: QmlDrawViewOverlayParams['pointValueOptions']
  warningThresholdUp: number
  warningThresholdDown: number
}): QmlDrawViewTaperLineOverlay[] {
  return lineSegments.flatMap((segment) => {
    if (!Array.isArray(segment.points) || segment.points.length === 0) return []

    const overlays: QmlDrawViewTaperLineOverlay[] = []
    let start: (Point & { z: number; zMm: number }) | null = null
    let reverse = 0

    for (const point of segment.points) {
      const x = finiteNumber(point?.[0])
      const y = finiteNumber(point?.[1])
      const z = finiteNumber(point?.[2])
      if (x == null || y == null || z == null) continue

      const currentPoint = { x, y, z, zMm: qmlDrawRelativeZValue(z, pointValueOptions) }
      if (currentPoint.zMm > warningThresholdUp) {
        if (reverse === 0) {
          start = currentPoint
          reverse = 1
        }
        continue
      }
      if (currentPoint.zMm < warningThresholdDown) {
        if (reverse === 0) {
          start = currentPoint
          reverse = -1
        }
        continue
      }

      if (start && reverse !== 0 && qmlDrawDistance(start, currentPoint) > 20) {
        const screenStart = qmlDrawScreenPoint(start, transform)
        const screenEnd = qmlDrawScreenPoint(currentPoint, transform)
        overlays.push({
          x1: screenStart.x,
          y1: screenStart.y,
          x2: screenEnd.x,
          y2: screenEnd.y,
          reverse,
        })
        start = null
        reverse = 0
      }
    }

    return overlays
  })
}

function qmlDrawPerpendicularPoint(line: QmlDrawViewPerpendicularLine, point: Point): Point | null {
  const dx = line.end.x - line.start.x
  const dy = line.end.y - line.start.y
  const lengthSquared = dx * dx + dy * dy
  if (lengthSquared === 0) return null

  const dx1 = line.start.x - point.x
  const dy1 = line.start.y - point.y
  const t = (dx * dx1 + dy * dy1) / lengthSquared
  return {
    x: line.start.x - t * dx,
    y: line.start.y - t * dy,
  }
}

export function buildQmlDrawViewOverlay({
  lineSegments = [],
  innerEllipse,
  taperSegmentsEnabled = false,
  warningThresholdUp = 100,
  warningThresholdDown = -100,
  perpendicularLine,
  hoverPoint,
  transform,
  pointValueOptions,
}: QmlDrawViewOverlayParams): QmlDrawViewOverlay {
  const safeTransform = {
    x: Number.isFinite(transform.x) ? transform.x : 0,
    y: Number.isFinite(transform.y) ? transform.y : 0,
    scale: Number.isFinite(transform.scale) && transform.scale > 0 ? transform.scale : 1,
  }
  const screenLineSegments = lineSegments.flatMap((segment) => {
    const pointL = qmlDrawLinePoint(segment.pointL)
    const pointR = qmlDrawLinePoint(segment.pointR)
    if (!pointL || !pointR) return []

    const start = qmlDrawScreenPoint(pointL, safeTransform)
    const end = qmlDrawScreenPoint(pointR, safeTransform)
    return [
      {
        x1: start.x,
        y1: start.y,
        x2: end.x,
        y2: end.y,
      },
    ]
  })
  const taperSegments = taperSegmentsEnabled
    ? buildQmlDrawTaperSegments({
        lineSegments,
        transform: safeTransform,
        pointValueOptions,
        warningThresholdUp: Number.isFinite(warningThresholdUp) ? Number(warningThresholdUp) : 100,
        warningThresholdDown: Number.isFinite(warningThresholdDown) ? Number(warningThresholdDown) : -100,
      })
    : []
  const perpendicularScreenPoint =
    perpendicularLine && hoverPoint ? qmlDrawPerpendicularPoint(perpendicularLine, hoverPoint) : null
  const perpendicularPoint = perpendicularScreenPoint
    ? (() => {
        const screenPoint = qmlDrawScreenPoint(perpendicularScreenPoint, safeTransform)
        return {
          x: roundOverlayNumber(screenPoint.x - 2),
          y: roundOverlayNumber(screenPoint.y - 2),
          width: 4,
          height: 4,
        }
      })()
    : null

  const majorAxis = Number(innerEllipse?.axes.height)
  const minorAxis = Number(innerEllipse?.axes.width)
  if (!innerEllipse || !Number.isFinite(majorAxis) || !Number.isFinite(minorAxis) || majorAxis <= 0 || minorAxis <= 0) {
    return {
      lineSegments: screenLineSegments,
      taperSegments,
      ellipse: null,
      axes: null,
      labels: null,
      perpendicularPoint,
    }
  }

  const center = qmlDrawScreenPoint(innerEllipse.center, safeTransform)
  const rx = roundOverlayNumber((majorAxis * safeTransform.scale) / 2)
  const ry = roundOverlayNumber((minorAxis * safeTransform.scale) / 2)
  const leftX = roundOverlayNumber(center.x - rx)
  const rightX = roundOverlayNumber(center.x + rx)
  const topY = roundOverlayNumber(center.y - ry)
  const bottomY = roundOverlayNumber(center.y + ry)
  const majorWidth = majorAxis * safeTransform.scale
  const minorHeight = minorAxis * safeTransform.scale

  return {
    lineSegments: screenLineSegments,
    taperSegments,
    ellipse: {
      cx: center.x,
      cy: center.y,
      rx,
      ry,
    },
    axes: {
      major: {
        x1: leftX,
        y1: center.y,
        x2: rightX,
        y2: center.y,
      },
      minor: {
        x1: center.x,
        y1: topY,
        x2: center.x,
        y2: bottomY,
      },
    },
    labels: {
      major: {
        x: roundOverlayNumber(center.x + 5),
        y: roundOverlayNumber(center.y - minorHeight / 3),
        text: qmlDrawDimensionText(majorAxis, pointValueOptions?.scan3dScaleX ?? undefined),
      },
      minor: {
        x: roundOverlayNumber(leftX + (majorWidth * 2) / 3),
        y: roundOverlayNumber(center.y + 5),
        text: qmlDrawDimensionText(minorAxis, pointValueOptions?.scan3dScaleX ?? undefined),
      },
    },
    perpendicularPoint,
  }
}

export function getVisibleTiles({
  viewRect,
  imageSize,
  tileSize,
  scale,
  fixedLevel,
  maxLevel,
}: VisibleTileParams): Tile[] {
  if (imageSize.width <= 0 || imageSize.height <= 0 || tileSize <= 0) {
    return []
  }

  const computedMaxLevel = Math.max(0, Math.ceil(Math.log2(Math.max(imageSize.width, imageSize.height) / tileSize)))
  const resolvedMaxLevel = typeof maxLevel === 'number' ? Math.max(0, Math.floor(maxLevel)) : computedMaxLevel
  const resolvedLevel =
    typeof fixedLevel === 'number'
      ? clamp(Math.floor(fixedLevel), 0, resolvedMaxLevel)
      : clamp(Math.floor(Math.log2(1 / Math.max(scale, 0.001))), 0, resolvedMaxLevel)

  const virtualTileSize = tileSize * 2 ** resolvedLevel
  const startCol = Math.max(0, Math.floor(viewRect.x / virtualTileSize))
  const startRow = Math.max(0, Math.floor(viewRect.y / virtualTileSize))
  const endCol = Math.min(
    Math.ceil(imageSize.width / virtualTileSize) - 1,
    Math.floor((viewRect.x + viewRect.width) / virtualTileSize),
  )
  const endRow = Math.min(
    Math.ceil(imageSize.height / virtualTileSize) - 1,
    Math.floor((viewRect.y + viewRect.height) / virtualTileSize),
  )

  if (endCol < startCol || endRow < startRow) {
    return []
  }

  const tiles: Tile[] = []
  for (let row = startRow; row <= endRow; row += 1) {
    for (let col = startCol; col <= endCol; col += 1) {
      const x = col * virtualTileSize
      const y = row * virtualTileSize
      tiles.push({
        level: resolvedLevel,
        row,
        col,
        x,
        y,
        width: Math.min(virtualTileSize, imageSize.width - x),
        height: Math.min(virtualTileSize, imageSize.height - y),
      })
    }
  }

  return tiles
}

export function getTileDebugBorderStyle(
  showTileDebugBorders: boolean,
  loadedLevel: number,
  targetLevel: number,
  isInViewport: boolean,
): TileDebugBorderStyle | null {
  if (!showTileDebugBorders) return null
  if (!isInViewport) return { color: '#33000000', label: 'outside' }
  if (loadedLevel < 0) return { color: '#FFA500', label: 'loading' }
  if (loadedLevel >= targetLevel) return { color: '#00FF00', label: 'complete' }
  return { color: '#FFFF00', label: 'partial' }
}

export function shouldUsePreviewCache(enable1024CacheMode: boolean, previewUrl?: string): boolean {
  return enable1024CacheMode && Boolean(previewUrl?.trim())
}

export function buildDefectLabelText(defect: DefectLabelSource, showDefectLabels: boolean): string {
  if (!showDefectLabels) return ''

  const name = defect.defectType?.trim() || '缺陷'
  const confidence = Number(defect.confidence)
  if (!Number.isFinite(confidence)) return name

  const percent = Math.round(Math.min(Math.max(confidence, 0), 1) * 100)
  return `${name} ${percent}%`
}

export function buildManualAnnotationRect({ start, end, minSize = 10 }: ManualAnnotationRectParams): Rect | null {
  const rect = {
    x: Math.round(Math.min(start.x, end.x)),
    y: Math.round(Math.min(start.y, end.y)),
    width: Math.round(Math.abs(end.x - start.x)),
    height: Math.round(Math.abs(end.y - start.y)),
  }

  if (rect.width < minSize || rect.height < minSize) {
    return null
  }

  return rect
}
