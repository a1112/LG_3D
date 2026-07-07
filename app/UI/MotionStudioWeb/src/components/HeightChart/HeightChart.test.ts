import { describe, expect, it } from 'vitest'
import heightChartSource from './index.tsx?raw'

describe('HeightChart QML DataShowItemCharts parity', () => {
  it('renders QML distance/z chart data with median and tower warning reference lines', () => {
    expect(heightChartSource).toContain('buildQmlHeightChartData')
    expect(heightChartSource).toContain('buildQmlHeightChartReferenceLines')
    expect(heightChartSource).toContain('innerCircleCenter?:')
    expect(heightChartSource).toContain('scan3dScaleX?: number')
    expect(heightChartSource).toContain('medianZ?: number | null')
    expect(heightChartSource).toContain('warningThresholdUp?: number')
    expect(heightChartSource).toContain('warningThresholdDown?: number')
    expect(heightChartSource).toContain('dataKey="distanceMm"')
    expect(heightChartSource).toContain('dataKey="heightMm"')
    expect(heightChartSource).toContain('ReferenceLine')
    expect(heightChartSource).toContain('y={referenceLines.median}')
    expect(heightChartSource).toContain('y={referenceLines.upper}')
    expect(heightChartSource).toContain('y={referenceLines.lower}')
  })

  it('mirrors QML ChartHead controls and mouse wheel/drag hooks for z-window control', () => {
    expect(heightChartSource).toContain('buildQmlHeightChartZDomain')
    expect(heightChartSource).toContain('buildQmlHeightChartDragOffset')
    expect(heightChartSource).toContain('nextQmlHeightChartTickSize')
    expect(heightChartSource).toContain('data-qml-height-chart-head')
    expect(heightChartSource).toContain('data-qml-height-chart-grid-size')
    expect(heightChartSource).toContain('data-qml-height-chart-offset')
    expect(heightChartSource).toContain('data-qml-height-chart-reset')
    expect(heightChartSource).toContain('onWheel={handleQmlHeightChartWheel}')
    expect(heightChartSource).toContain('onMouseDown={handleQmlHeightChartMouseDown}')
    expect(heightChartSource).toContain('onMouseMove={handleQmlHeightChartMouseMove}')
    expect(heightChartSource).toContain('onMouseUp={handleQmlHeightChartMouseUp}')
    expect(heightChartSource).toContain('domain={[qmlZDomain.minZ, qmlZDomain.maxZ]}')
    expect(heightChartSource).toContain('tickCount={qmlTickCountZ + 1}')
  })

  it('mirrors QML chart hover drag lines and z labels', () => {
    expect(heightChartSource).toContain('buildQmlHeightChartHoverOverlay')
    expect(heightChartSource).toContain('const [qmlHoverPointX, setQmlHoverPointX]')
    expect(heightChartSource).toContain('data-qml-height-chart-drag-line-h')
    expect(heightChartSource).toContain('data-qml-height-chart-drag-line-v')
    expect(heightChartSource).toContain('data-qml-height-chart-hover-distance')
    expect(heightChartSource).toContain('data-qml-height-chart-hover-value')
    expect(heightChartSource).toContain('onMouseMove={handleQmlHeightChartMouseMove}')
    expect(heightChartSource).toContain('setQmlHoverPointX')
  })

  it('mirrors QML ChartHead type menu for grid and high-low modes', () => {
    expect(heightChartSource).toContain('const [localQmlChartShowType, setLocalQmlChartShowType]')
    expect(heightChartSource).toContain('const [qmlChartShowMenuOpen, setQmlChartShowMenuOpen]')
    expect(heightChartSource).toContain("resolvedQmlChartShowType === 0 ? '网格 ▼' : '高低 ▼'")
    expect(heightChartSource).toContain('data-qml-height-chart-type-menu')
    expect(heightChartSource).toContain('data-qml-height-chart-type-option="grid"')
    expect(heightChartSource).toContain('data-qml-height-chart-type-option="height"')
    expect(heightChartSource).toContain('data-qml-height-chart-type-selected={resolvedQmlChartShowType === 0}')
    expect(heightChartSource).toContain('data-qml-height-chart-type-selected={resolvedQmlChartShowType === 1}')
  })

  it('accepts DataShow-owned chart show type state like QML DataShowCore', () => {
    expect(heightChartSource).toContain('qmlChartShowType?: 0 | 1')
    expect(heightChartSource).toContain('onQmlChartShowTypeChange?: (value: 0 | 1) => void')
    expect(heightChartSource).toContain('const resolvedQmlChartShowType = qmlChartShowType ?? localQmlChartShowType')
    expect(heightChartSource).toContain('onQmlChartShowTypeChange?.(value)')
  })

  it('closes the QML ChartHead type menu on outside pointer down like a QML popup menu', () => {
    expect(heightChartSource).toContain('const qmlChartHeadRef = useRef<HTMLDivElement | null>(null)')
    expect(heightChartSource).toContain('function closeQmlChartShowMenuOnOutsidePointerDown(event: PointerEvent)')
    expect(heightChartSource).toContain('if (!qmlChartShowMenuOpen) return undefined')
    expect(heightChartSource).toContain('qmlChartHeadRef.current?.contains(event.target as Node)')
    expect(heightChartSource).toContain(
      "document.addEventListener('pointerdown', closeQmlChartShowMenuOnOutsidePointerDown)",
    )
    expect(heightChartSource).toContain(
      "document.removeEventListener('pointerdown', closeQmlChartShowMenuOnOutsidePointerDown)",
    )
    expect(heightChartSource).toContain('ref={qmlChartHeadRef}')
  })
})
