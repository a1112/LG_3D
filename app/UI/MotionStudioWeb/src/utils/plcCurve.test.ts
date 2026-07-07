import { describe, expect, it } from 'vitest'

import { buildDeviceCurveChart, buildDeviceCurveViewModel } from './plcCurve'

describe('plcCurve', () => {
  it('matches QML device curve total length and average error calculations', () => {
    const model = buildDeviceCurveViewModel([
      {
        coil_id: 10,
        time: '2026-06-28 10:00:00',
        location_S: 1,
        location_L: 2,
        location_laser: 3,
        width_: 1000,
        median_3d_mm_S: 110,
        median_3d_mm_L: 210,
      },
      {
        coil_id: 11,
        width_: 1200,
        median_3d_mm_S: 130,
        median_3d_mm_L: 230,
      },
    ])

    expect(model.totalLengthAvg).toBe(1440)
    expect(model.distanceSAvg).toBe(120)
    expect(model.distanceLAvg).toBe(220)
    expect(model.rows[0]).toMatchObject({
      coil_id: 10,
      total_length: 1320,
      total_error: -120,
      distance_s_error: -10,
      distance_l_error: -10,
    })
    expect(model.rows[1]).toMatchObject({
      coil_id: 11,
      total_length: 1560,
      total_error: 120,
      distance_s_error: 10,
      distance_l_error: 10,
    })
  })

  it('keeps invalid short distances out of QML averages', () => {
    const model = buildDeviceCurveViewModel([
      {
        coil_id: 12,
        width_: 1000,
        median_3d_mm_S: 99,
        median_3d_mm_L: 220,
      },
      {
        coil_id: 13,
        width_: 1000,
        median_3d_mm_S: 120,
        median_3d_mm_L: 240,
      },
    ])

    expect(model.totalLengthAvg).toBe(1360)
    expect(model.distanceSAvg).toBe(120)
    expect(model.distanceLAvg).toBe(230)
    expect(Number.isNaN(model.rows[0].total_length)).toBe(true)
    expect(model.rows[0].distance_s_error).toBe(-21)
    expect(model.rows[0].distance_l_error).toBe(-10)
  })

  it('builds QML-compatible chart series and axis ranges', () => {
    const model = buildDeviceCurveViewModel([
      {
        coil_id: 10,
        location_S: 1,
        location_L: 2,
        location_laser: 3,
        width_: 1000,
        median_3d_mm_S: 110,
        median_3d_mm_L: 210,
      },
      {
        coil_id: 12,
        location_S: 4,
        location_L: 5,
        location_laser: 6,
        width_: 1200,
        median_3d_mm_S: 130,
        median_3d_mm_L: 230,
      },
    ])

    const chart = buildDeviceCurveChart(model.rows)

    expect(chart.axis).toEqual({ minX: 10, maxX: 12, minY: 1, maxY: 1200 })
    expect(chart.series.map((series) => series.key)).toEqual([
      'location_S',
      'location_L',
      'location_laser',
      'median_3d_mm_S',
      'median_3d_mm_L',
      'width_',
    ])
    expect(chart.series[0].points).toEqual([
      { x: 10, y: 1 },
      { x: 12, y: 4 },
    ])
  })

  it('uses QML fallback chart axes when no finite points exist', () => {
    expect(buildDeviceCurveChart([]).axis).toEqual({ minX: 0, maxX: 1, minY: 0, maxY: 1 })
  })
})
