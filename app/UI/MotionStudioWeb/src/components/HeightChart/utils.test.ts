import { describe, expect, it } from 'vitest'

import {
  buildQmlHeightChartData,
  buildQmlHeightChartDragOffset,
  buildQmlHeightChartHoverOverlay,
  buildQmlHeightChartReferenceLines,
  buildQmlHeightChartZDomain,
  nextQmlHeightChartTickSize,
  normalizeQmlHeightChartInnerCircleCenter,
} from './utils'

describe('QML DataShowItemCharts helpers', () => {
  it('uses QML SurfaceData inner_circle circlex as the height chart center', () => {
    expect(
      normalizeQmlHeightChartInnerCircleCenter({
        circleConfig: {
          inner_circle: {
            circlex: [100, 200, 30],
            ellipse: [
              [110, 210],
              [300, 400],
              0,
            ],
          },
        },
      }),
    ).toEqual({ x: 100, y: 200 })
  })

  it('maps height line points to QML signed distance and absolute z millimeters', () => {
    expect(
      buildQmlHeightChartData(
        [
          {
            pointL: [80, 50],
            pointR: [120, 50],
            points: [
              [80, 50, 1000],
              [120, 50, 1100],
            ],
          },
        ],
        {
          innerCircleCenter: { x: 100, y: 50 },
          scan3dScaleX: 0.5,
          scan3dScaleZ: 0.02,
          scan3dCoordinateOffsetZ: 10,
        },
      ),
    ).toEqual([
      {
        sampleKey: '1-1',
        segmentIndex: 0,
        pointIndex: 0,
        distanceMm: -10,
        heightMm: 30,
        rawZ: 1000,
      },
      {
        sampleKey: '1-2',
        segmentIndex: 0,
        pointIndex: 1,
        distanceMm: 10,
        heightMm: 32,
        rawZ: 1100,
      },
    ])
  })

  it('filters QML chart z jumps larger than 300mm before rendering intermediate samples', () => {
    expect(
      buildQmlHeightChartData(
        [
          {
            pointL: [80, 50],
            pointR: [140, 50],
            points: [
              [80, 50, 1000],
              [120, 50, 50000],
              [140, 50, 1110],
            ],
          },
        ],
        {
          innerCircleCenter: { x: 100, y: 50 },
          scan3dScaleX: 0.5,
          scan3dScaleZ: 0.02,
          scan3dCoordinateOffsetZ: 10,
        },
      ).map((point) => point.sampleKey),
    ).toEqual(['1-1', '1-3'])
  })

  it('builds QML median and tower warning reference lines from current surface settings', () => {
    expect(
      buildQmlHeightChartReferenceLines({
        medianZ: 770,
        warningThresholdUp: 100,
        warningThresholdDown: -50,
      }),
    ).toEqual({
      median: 770,
      upper: 870,
      lower: 720,
    })
  })

  it('mirrors QML CoreCharts z domain, drag offset, and wheel grid step', () => {
    expect(
      buildQmlHeightChartZDomain({
        offsetZ: 770,
        tickSizeZ: 12,
        tickCountZ: 7,
        dragOffsetZ: 6,
      }),
    ).toEqual({
      minZ: 734,
      maxZ: 818,
      safeTickSizeZ: 12,
      safeOffsetZ: 770,
      safeDragOffsetZ: 6,
    })

    expect(
      buildQmlHeightChartDragOffset({
        startY: 10,
        currentY: 30,
        drawWidth: 200,
        tickSizeZ: 12,
        tickCountZ: 10,
      }),
    ).toBe(12)

    expect(nextQmlHeightChartTickSize(12, 120)).toBe(11.5)
    expect(nextQmlHeightChartTickSize(12, -120)).toBe(12.5)
  })

  it('mirrors QML DataShowItemCharts hover drag lines and raw/relative/absolute labels', () => {
    expect(
      buildQmlHeightChartHoverOverlay({
        chartData: [
          { sampleKey: '1-1', segmentIndex: 0, pointIndex: 0, distanceMm: -10, heightMm: 30, rawZ: 1000 },
          { sampleKey: '1-2', segmentIndex: 0, pointIndex: 1, distanceMm: 10, heightMm: 32, rawZ: 1100 },
          { sampleKey: '1-3', segmentIndex: 0, pointIndex: 2, distanceMm: 40, heightMm: 34, rawZ: 1200 },
        ],
        pointerX: 125,
        chartWidth: 240,
        drawHeight: 100,
        zDomain: {
          minZ: 20,
          maxZ: 40,
          safeTickSizeZ: 10,
          safeOffsetZ: 30,
          safeDragOffsetZ: 0,
        },
        medianZ: 30,
      }),
    ).toEqual({
      x: 125,
      y: 40,
      verticalHeight: 100,
      horizontalX: 5,
      horizontalWidth: 205,
      distanceLabel: '19.3',
      valueLabel: 'raw 1100 | rel 2.00 | abs 32.00',
    })
  })
})
