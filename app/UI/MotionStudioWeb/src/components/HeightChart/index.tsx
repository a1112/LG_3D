import { useEffect, useMemo, useRef, useState, type MouseEvent, type WheelEvent } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { HeightLineSegment } from '@/types'
import {
  buildQmlHeightChartData,
  buildQmlHeightChartDragOffset,
  buildQmlHeightChartHoverOverlay,
  buildQmlHeightChartReferenceLines,
  buildQmlHeightChartZDomain,
  nextQmlHeightChartTickSize,
  QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z,
  type QmlHeightChartCenter,
} from './utils'
import './HeightChart.css'

interface HeightChartProps {
  data?: HeightLineSegment[]
  innerCircleCenter?: QmlHeightChartCenter | null
  scan3dScaleX?: number
  scan3dScaleZ?: number
  scan3dCoordinateOffsetZ?: number
  medianZ?: number | null
  warningThresholdUp?: number
  warningThresholdDown?: number
  qmlChartShowType?: 0 | 1
  onQmlChartShowTypeChange?: (value: 0 | 1) => void
}

function HeightChart({
  data,
  innerCircleCenter,
  scan3dScaleX,
  scan3dScaleZ,
  scan3dCoordinateOffsetZ,
  medianZ,
  warningThresholdUp,
  warningThresholdDown,
  qmlChartShowType,
  onQmlChartShowTypeChange,
}: HeightChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const qmlChartHeadRef = useRef<HTMLDivElement | null>(null)
  const dragStartYRef = useRef<number | null>(null)
  const [chartSize, setChartSize] = useState({ width: 320, height: 160 })
  const [qmlTickSizeZ, setQmlTickSizeZ] = useState(QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z)
  const [qmlOffsetZ, setQmlOffsetZ] = useState(0)
  const [qmlDragOffsetZ, setQmlDragOffsetZ] = useState(0)
  const [qmlHoverPointX, setQmlHoverPointX] = useState<number | null>(null)
  const [localQmlChartShowType, setLocalQmlChartShowType] = useState<0 | 1>(0)
  const [qmlChartShowMenuOpen, setQmlChartShowMenuOpen] = useState(false)
  const resolvedQmlChartShowType = qmlChartShowType ?? localQmlChartShowType

  const chartOptions = useMemo(
    () => ({
      innerCircleCenter,
      scan3dScaleX,
      scan3dScaleZ,
      scan3dCoordinateOffsetZ,
    }),
    [innerCircleCenter, scan3dCoordinateOffsetZ, scan3dScaleX, scan3dScaleZ],
  )
  const chartData = useMemo(() => buildQmlHeightChartData(data, chartOptions), [chartOptions, data])
  const referenceLines = useMemo(
    () =>
      buildQmlHeightChartReferenceLines({
        medianZ,
        warningThresholdUp,
        warningThresholdDown,
      }),
    [medianZ, warningThresholdDown, warningThresholdUp],
  )
  const qmlInitialOffsetZ = referenceLines.median ?? chartData[0]?.heightMm ?? 0
  const qmlDrawHeight = Math.max(chartSize.height - 20, 1)
  const qmlTickCountZ = Math.max(1, Math.floor(qmlDrawHeight / 20))
  const qmlZDomain = useMemo(
    () =>
      buildQmlHeightChartZDomain({
        offsetZ: qmlOffsetZ,
        tickSizeZ: qmlTickSizeZ,
        tickCountZ: qmlTickCountZ,
        dragOffsetZ: qmlDragOffsetZ,
      }),
    [qmlDragOffsetZ, qmlOffsetZ, qmlTickCountZ, qmlTickSizeZ],
  )
  const qmlHoverOverlay = useMemo(
    () =>
      buildQmlHeightChartHoverOverlay({
        chartData,
        pointerX: qmlHoverPointX,
        chartWidth: chartSize.width,
        drawHeight: qmlDrawHeight,
        zDomain: qmlZDomain,
        medianZ: referenceLines.median,
      }),
    [chartData, chartSize.width, qmlDrawHeight, qmlHoverPointX, qmlZDomain, referenceLines.median],
  )

  useEffect(() => {
    setQmlOffsetZ(qmlInitialOffsetZ)
    setQmlTickSizeZ(QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z)
    setQmlDragOffsetZ(0)
    setQmlHoverPointX(null)
    dragStartYRef.current = null
  }, [data, qmlInitialOffsetZ])

  useEffect(() => {
    const element = containerRef.current
    if (!element) return undefined

    const updateChartSize = () => {
      const rect = element.getBoundingClientRect()
      const width = Math.max(Math.round(rect.width), 1)
      const height = Math.max(Math.round(rect.height), 160)
      setChartSize((current) => (current.width === width && current.height === height ? current : { width, height }))
    }

    updateChartSize()
    if (typeof ResizeObserver === 'undefined') return undefined

    const resizeObserver = new ResizeObserver(updateChartSize)
    resizeObserver.observe(element)
    return () => resizeObserver.disconnect()
  }, [])

  useEffect(() => {
    if (!qmlChartShowMenuOpen) return undefined

    function closeQmlChartShowMenuOnOutsidePointerDown(event: PointerEvent) {
      if (qmlChartHeadRef.current?.contains(event.target as Node)) return
      setQmlChartShowMenuOpen(false)
    }

    document.addEventListener('pointerdown', closeQmlChartShowMenuOnOutsidePointerDown)
    return () => document.removeEventListener('pointerdown', closeQmlChartShowMenuOnOutsidePointerDown)
  }, [qmlChartShowMenuOpen])

  function resetQmlHeightChart() {
    setQmlOffsetZ(qmlInitialOffsetZ)
    setQmlTickSizeZ(QML_HEIGHT_CHART_DEFAULT_TICK_SIZE_Z)
    setQmlDragOffsetZ(0)
    dragStartYRef.current = null
  }

  function selectQmlChartShowType(value: 0 | 1) {
    onQmlChartShowTypeChange?.(value)
    if (!onQmlChartShowTypeChange) {
      setLocalQmlChartShowType(value)
    }
    setQmlChartShowMenuOpen(false)
  }

  function handleQmlHeightChartWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault()
    setQmlTickSizeZ((current) => nextQmlHeightChartTickSize(current, -event.deltaY))
  }

  function handleQmlHeightChartMouseDown(event: MouseEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest('[data-qml-height-chart-head]')) return
    dragStartYRef.current = event.clientY
    setQmlDragOffsetZ(0)
  }

  function handleQmlHeightChartMouseMove(event: MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect()
    setQmlHoverPointX(event.clientX - rect.left)

    if (dragStartYRef.current == null) return
    setQmlDragOffsetZ(
      buildQmlHeightChartDragOffset({
        startY: dragStartYRef.current,
        currentY: event.clientY,
        drawWidth: chartSize.width,
        tickSizeZ: qmlTickSizeZ,
        tickCountZ: qmlTickCountZ,
      }),
    )
  }

  function handleQmlHeightChartMouseUp() {
    if (dragStartYRef.current == null) return
    setQmlOffsetZ((current) => Math.round((current + qmlDragOffsetZ) * 1000) / 1000)
    setQmlDragOffsetZ(0)
    dragStartYRef.current = null
  }

  function handleQmlHeightChartMouseLeave() {
    handleQmlHeightChartMouseUp()
    setQmlHoverPointX(null)
  }

  if (!data || chartData.length === 0) {
    return <div className="height-chart-empty">暂无高度数据</div>
  }

  return (
    <div
      className="height-chart-container"
      data-qml-height-chart
      ref={containerRef}
      onWheel={handleQmlHeightChartWheel}
      onMouseDown={handleQmlHeightChartMouseDown}
      onMouseMove={handleQmlHeightChartMouseMove}
      onMouseUp={handleQmlHeightChartMouseUp}
      onMouseLeave={handleQmlHeightChartMouseLeave}
    >
      <div className="height-chart-qml-head" data-qml-height-chart-head ref={qmlChartHeadRef}>
        <button
          type="button"
          className="height-chart-qml-head-button"
          data-qml-height-chart-show-type
          onClick={() => setQmlChartShowMenuOpen((open) => !open)}
        >
          {resolvedQmlChartShowType === 0 ? '网格 ▼' : '高低 ▼'}
        </button>
        {qmlChartShowMenuOpen ? (
          <div className="height-chart-qml-type-menu" data-qml-height-chart-type-menu>
            <button
              type="button"
              className="height-chart-qml-type-option"
              data-qml-height-chart-type-option="grid"
              data-qml-height-chart-type-selected={resolvedQmlChartShowType === 0}
              onClick={() => selectQmlChartShowType(0)}
            >
              网格类型
            </button>
            <button
              type="button"
              className="height-chart-qml-type-option"
              data-qml-height-chart-type-option="height"
              data-qml-height-chart-type-selected={resolvedQmlChartShowType === 1}
              onClick={() => selectQmlChartShowType(1)}
            >
              高低值
            </button>
          </div>
        ) : null}
        <span className="height-chart-qml-head-item">
          网格:
          <strong data-qml-height-chart-grid-size>{qmlTickSizeZ.toFixed(1)} mm</strong>
        </span>
        <span className="height-chart-qml-head-item">
          偏移:
          <strong data-qml-height-chart-offset>{(qmlOffsetZ + qmlDragOffsetZ).toFixed(1)} mm</strong>
        </span>
        <button
          type="button"
          className="height-chart-qml-head-button"
          data-qml-height-chart-reset
          onClick={resetQmlHeightChart}
        >
          重置
        </button>
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 28, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="distanceMm"
            type="number"
            domain={['dataMin', 'dataMax']}
            label={{ value: '距离 (mm)', position: 'insideBottom', offset: -5 }}
          />
          <YAxis
            domain={[qmlZDomain.minZ, qmlZDomain.maxZ]}
            tickCount={qmlTickCountZ + 1}
            allowDataOverflow
            label={{ value: '高度 (mm)', angle: -90, position: 'insideLeft' }}
          />
          <Tooltip
            formatter={(value: number, name) => [
              typeof value === 'number' ? value.toFixed(2) : value,
              name === 'heightMm' ? '高度' : name,
            ]}
            labelFormatter={(label) => `距离: ${Number(label).toFixed(1)} mm`}
          />
          <Legend />
          {referenceLines.upper == null ? null : (
            <ReferenceLine y={referenceLines.upper} stroke="#ff4d4f" strokeDasharray="4 4" />
          )}
          {referenceLines.lower == null ? null : (
            <ReferenceLine y={referenceLines.lower} stroke="#ff4d4f" strokeDasharray="4 4" />
          )}
          {referenceLines.median == null ? null : (
            <ReferenceLine y={referenceLines.median} stroke="#1677ff" strokeDasharray="4 4" />
          )}
          <Line
            type="monotone"
            dataKey="heightMm"
            stroke="#1890ff"
            name="高度值"
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
      {qmlHoverOverlay ? (
        <div className="height-chart-qml-hover" data-qml-height-chart-hover>
          <span
            className="height-chart-qml-drag-line-h"
            data-qml-height-chart-drag-line-h
            style={{
              left: qmlHoverOverlay.x,
              height: qmlHoverOverlay.verticalHeight,
            }}
          >
            <span
              className="height-chart-qml-hover-distance"
              data-qml-height-chart-hover-distance
              style={{ top: qmlHoverOverlay.y + 30 }}
            >
              {qmlHoverOverlay.distanceLabel}
            </span>
          </span>
          <span
            className="height-chart-qml-drag-line-v"
            data-qml-height-chart-drag-line-v
            style={{
              left: qmlHoverOverlay.horizontalX,
              top: qmlHoverOverlay.y,
              width: qmlHoverOverlay.horizontalWidth,
            }}
          >
            <span
              className="height-chart-qml-hover-value"
              data-qml-height-chart-hover-value
              style={{ left: qmlHoverOverlay.x + 30 }}
            >
              {qmlHoverOverlay.valueLabel}
            </span>
          </span>
        </div>
      ) : null}
    </div>
  )
}

export default HeightChart
