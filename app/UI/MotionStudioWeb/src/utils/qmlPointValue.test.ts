import { describe, expect, it } from 'vitest'

import {
  DEFAULT_SCAN_3D_SCALE_X,
  DEFAULT_SCAN_3D_SCALE_Y,
  DEFAULT_SCAN_3D_SCALE_Z,
  buildQmlHoverPointInfo,
  buildQmlPointValueText,
  buildQmlXyzListItems,
  coilInfoToQmlPointValueOptions,
  getQmlCrossViewZColor,
  qmlRawToAbsoluteMm,
  qmlRawToRelativeMm,
  qmlXToMmText,
  qmlYToMmText,
} from './qmlPointValue'

describe('QML SurfaceData point value formatting', () => {
  it('uses the QML default scan3d coordinate scales', () => {
    expect(DEFAULT_SCAN_3D_SCALE_Z).toBe(0.016229506582021713)
    expect(DEFAULT_SCAN_3D_SCALE_X).toBe(0.33693358302116394)
    expect(DEFAULT_SCAN_3D_SCALE_Y).toBe(0.33693358302116394)
  })

  it('matches zRawToMm and zRawToRelativeMm with scale, offset, and median', () => {
    expect(qmlRawToAbsoluteMm(1000, { scan3dScaleZ: 0.02, scan3dCoordinateOffsetZ: 3 })).toBe(23)
    expect(
      qmlRawToRelativeMm(1000, {
        scan3dScaleZ: 0.02,
        scan3dCoordinateOffsetZ: 3,
        medianZ: 18,
      }),
    ).toBe(5)
  })

  it('matches QML relative mm i_to_info including the low-value -inf branch', () => {
    const options = { pointValueShowType: 'mm-relative' as const, scan3dScaleZ: 0.02, medianZ: 3 }

    expect(buildQmlPointValueText(0, options)).toBe('-inf')
    expect(buildQmlPointValueText(0.009, options)).toBe('-inf')
    expect(buildQmlPointValueText(150, options)).toBe('0.00')
    expect(buildQmlPointValueText(151, options)).toBe('0.02')
  })

  it('matches QML absolute mm and raw int display modes', () => {
    expect(
      buildQmlPointValueText(1000, {
        pointValueShowType: 'mm-absolute',
        scan3dScaleZ: 0.02,
        scan3dCoordinateOffsetZ: 3,
      }),
    ).toBe('23.00')
    expect(buildQmlPointValueText('00123', { pointValueShowType: 'int-raw' })).toBe('00123')
  })

  it('formats QML x/y coordinate labels with integer millimeter precision', () => {
    expect(qmlXToMmText(300, { scan3dScaleX: 0.5 })).toBe('150')
    expect(qmlYToMmText(300, { scan3dScaleY: 0.25 })).toBe('75')
  })

  it('keeps QML fallback behavior for non-finite numeric inputs', () => {
    expect(qmlRawToAbsoluteMm('bad', { scan3dScaleZ: 0.02, scan3dCoordinateOffsetZ: 3 })).toBe(0)
    expect(qmlRawToRelativeMm('bad', { scan3dScaleZ: 0.02, medianZ: 5 })).toBe(0)
    expect(buildQmlPointValueText('bad', { pointValueShowType: 'mm-absolute', scan3dScaleZ: 0.02 })).toBe('0.00')
    expect(buildQmlPointValueText('bad', { pointValueShowType: 'mm-relative', scan3dScaleZ: 0.02 })).toBe('0.00')
  })

  it('extracts QML SurfaceData scale, offset, and median options from coilInfo', () => {
    expect(
      coilInfoToQmlPointValueOptions({
        scan3dCoordinateScaleX: '0.34',
        scan3dCoordinateScaleY: 1,
        scan3dCoordinateScaleZ: 0.016,
        scan3dCoordinateOffsetZ: 2,
        median_3d_mm: 770.9,
      }),
    ).toEqual({
      scan3dScaleX: 0.34,
      scan3dScaleY: 1,
      scan3dScaleZ: 0.016,
      scan3dCoordinateOffsetZ: 2,
      medianZ: 770.9,
    })
  })

  it('builds QML hover point HUD labels from image pixel coordinates and raw Z', () => {
    expect(
      buildQmlHoverPointInfo({
        point: { x: 120.8, y: 650.3 },
        rawValue: 48000,
        options: {
          pointValueShowType: 'mm-relative',
          scan3dScaleX: 0.5,
          scan3dScaleY: 0.25,
          scan3dScaleZ: 0.02,
          medianZ: 950,
        },
      }),
    ).toEqual({
      x: 120,
      y: 650,
      xMm: '60',
      yMm: '163',
      z: '10.00',
    })
  })

  it('matches QML CrossView parseInt z threshold coloring', () => {
    const thresholds = { thresholdDown: -100, thresholdUp: 100 }

    expect(getQmlCrossViewZColor('-101.2', thresholds)).toBe('red')
    expect(getQmlCrossViewZColor('100.9', thresholds)).toBe('green')
    expect(getQmlCrossViewZColor('101.0', thresholds)).toBe('red')
    expect(getQmlCrossViewZColor('-inf', thresholds)).toBe('green')
  })

  it('builds QML XYZ_List rows from database and user sign point records', () => {
    expect(
      buildQmlXyzListItems(
        [
          { Id: 2, x: 101.5, y: 202.25, z_mm: '16.5', type: 'inner' },
          { id: 7, p_x: '1300', p_y: '900', p_z: '51000', type: 'user' },
          { id: 8, x: 'bad', y: 1, z_mm: 22 },
        ],
        {
          scan3dScaleX: 0.5,
          scan3dScaleY: 0.25,
          scan3dScaleZ: 0.02,
          medianZ: 950,
          center: { x: 100, y: 200 },
          thresholdDown: -10,
          thresholdUp: 50,
        },
      ),
    ).toEqual([
      {
        id: '2',
        title: '点 0',
        xMm: '1',
        yMm: '1',
        zMm: '16.5',
        zColor: 'green',
        type: 'inner',
      },
      {
        id: '7',
        title: '点 1',
        xMm: '600',
        yMm: '175',
        zMm: '70.00',
        zColor: 'red',
        type: 'user',
      },
    ])
  })
})
