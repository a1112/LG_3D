import { describe, expect, it } from 'vitest'

import {
  buildQmlAerialTargetTransform,
  buildQmlAerialView,
  buildCenteredScaleTransform,
  buildQmlScaleMenuOptions,
  buildQmlDbPointOverlay,
  buildQmlDrawViewOverlay,
  buildQmlSurveyOverlay,
  buildQmlUserPointOverlay,
  buildManualAnnotationRect,
  buildDefectLabelText,
  buildDefectFocusTransform,
  buildResetTransform,
  getTileDebugBorderStyle,
  getVisibleTiles,
  normalizeQmlCanvasScale,
  normalizeQmlImageGamma,
  normalizeQmlDbPoint,
  projectQmlDbPointLabel,
  shouldUsePreviewCache,
} from './utils'

describe('getVisibleTiles', () => {
  it('returns only the tiles intersecting the viewport at the requested level', () => {
    const tiles = getVisibleTiles({
      viewRect: { x: 200, y: 120, width: 420, height: 300 },
      imageSize: { width: 1024, height: 768 },
      tileSize: 256,
      scale: 1,
      fixedLevel: 0,
    })

    expect(tiles.map((tile) => [tile.row, tile.col])).toEqual([
      [0, 0],
      [0, 1],
      [0, 2],
      [1, 0],
      [1, 1],
      [1, 2],
    ])
  })

  it('clips edge tiles to the image bounds', () => {
    const tiles = getVisibleTiles({
      viewRect: { x: 760, y: 500, width: 400, height: 400 },
      imageSize: { width: 1000, height: 700 },
      tileSize: 256,
      scale: 1,
      fixedLevel: 0,
    })

    const last = tiles[tiles.length - 1]
    expect(last).toMatchObject({
      col: 3,
      row: 2,
      width: 232,
      height: 188,
    })
  })
})

describe('getTileDebugBorderStyle', () => {
  it('hides debug borders by default', () => {
    expect(getTileDebugBorderStyle(false, -1, 4, true)).toBeNull()
  })

  it('uses QML-compatible debug colors for loading and complete tiles', () => {
    expect(getTileDebugBorderStyle(true, -1, 4, true)).toEqual({
      color: '#FFA500',
      label: 'loading',
    })
    expect(getTileDebugBorderStyle(true, 2, 4, true)).toEqual({
      color: '#FFFF00',
      label: 'partial',
    })
    expect(getTileDebugBorderStyle(true, 4, 4, true)).toEqual({
      color: '#00FF00',
      label: 'complete',
    })
  })

  it('marks off-screen debug tiles as inactive', () => {
    expect(getTileDebugBorderStyle(true, 4, 4, false)).toEqual({
      color: '#33000000',
      label: 'outside',
    })
  })
})

describe('shouldUsePreviewCache', () => {
  it('matches QML default by skipping preview cache unless 1024 cache mode is enabled', () => {
    expect(shouldUsePreviewCache(false, '/image/preview/S/193113/AREA')).toBe(false)
    expect(shouldUsePreviewCache(true, '')).toBe(false)
    expect(shouldUsePreviewCache(true, '/image/preview/S/193113/AREA')).toBe(true)
  })
})

describe('buildResetTransform', () => {
  it('matches QML resetView by returning to minimum fitted scale and origin', () => {
    expect(
      buildResetTransform({
        container: { width: 1200, height: 800 },
        image: { width: 6000, height: 4000 },
      }),
    ).toEqual({
      scale: 0.2,
      x: 0,
      y: 0,
    })
  })

  it('keeps the fitted image centered when one axis has spare space', () => {
    expect(
      buildResetTransform({
        container: { width: 1000, height: 800 },
        image: { width: 4000, height: 2000 },
      }),
    ).toEqual({
      scale: 0.25,
      x: 0,
      y: 150,
    })
  })
})

describe('QML header image adjustment helpers', () => {
  it('normalizes QML DataShow ScaleBtn canvas scale values', () => {
    expect(normalizeQmlCanvasScale(null)).toBeNull()
    expect(normalizeQmlCanvasScale(Number.NaN)).toBeNull()
    expect(normalizeQmlCanvasScale(0.01)).toBe(0.04)
    expect(normalizeQmlCanvasScale(5)).toBe(4)
    expect(normalizeQmlCanvasScale(1.234)).toBe(1.23)
  })

  it('builds QML ScaleBtn menu options from the fitted minScale to 100 percent', () => {
    expect(buildQmlScaleMenuOptions(0.2)).toEqual([
      { key: '0.20', label: '20%', value: 0.2 },
      { key: '0.36', label: '36%', value: 0.36 },
      { key: '0.52', label: '52%', value: 0.52 },
      { key: '0.68', label: '68%', value: 0.68 },
      { key: '0.84', label: '84%', value: 0.84 },
      { key: '1.00', label: '100%', value: 1 },
    ])
    expect(buildQmlScaleMenuOptions(Number.NaN)).toEqual([{ key: '1.00', label: '100%', value: 1 }])
  })

  it('normalizes QML GammaBtn values to the slider range and step', () => {
    expect(normalizeQmlImageGamma(null)).toBeNull()
    expect(normalizeQmlImageGamma(Number.NaN)).toBeNull()
    expect(normalizeQmlImageGamma(0.1)).toBe(0.3)
    expect(normalizeQmlImageGamma(2)).toBe(1.3)
    expect(normalizeQmlImageGamma(0.68)).toBe(0.7)
  })

  it('builds a centered transform when QML ScaleBtn applies an absolute scale', () => {
    expect(
      buildCenteredScaleTransform({
        container: { width: 1200, height: 800 },
        image: { width: 6000, height: 4000 },
        scale: 0.5,
      }),
    ).toEqual({
      scale: 0.5,
      x: -900,
      y: -600,
    })
  })
})

describe('buildDefectFocusTransform', () => {
  it('matches QML setDefectShowView by zooming to 1:1 and centering the defect box', () => {
    expect(
      buildDefectFocusTransform({
        container: { width: 1200, height: 800 },
        image: { width: 6000, height: 4000 },
        defect: { x: 2176, y: 578, width: 1087, height: 502 },
      }),
    ).toEqual({
      scale: 1,
      x: -2119.5,
      y: -429,
    })
  })

  it('clamps QML defect focus to the image bounds near the lower-right edge', () => {
    expect(
      buildDefectFocusTransform({
        container: { width: 1200, height: 800 },
        image: { width: 6000, height: 4000 },
        defect: { x: 5800, y: 3900, width: 500, height: 300 },
      }),
    ).toEqual({
      scale: 1,
      x: -4800,
      y: -3200,
    })
  })
})

describe('QML AerialView helpers', () => {
  it('maps the current canvas transform into the QML AerialView viewport rectangle', () => {
    expect(
      buildQmlAerialView({
        container: { width: 1000, height: 500 },
        image: { width: 5000, height: 2500 },
        transform: { x: -500, y: -250, scale: 0.5 },
      }),
    ).toEqual({
      width: 100,
      height: 50,
      viewport: {
        x: 20,
        y: 10,
        width: 40,
        height: 20,
      },
    })
  })

  it('uses QML rec.height/2 centering when jumping from AerialView coordinates', () => {
    const aerial = buildQmlAerialView({
      container: { width: 1000, height: 500 },
      image: { width: 5000, height: 2500 },
      transform: { x: -500, y: -250, scale: 0.5 },
    })

    expect(
      buildQmlAerialTargetTransform({
        container: { width: 1000, height: 500 },
        image: { width: 5000, height: 2500 },
        transform: { x: -500, y: -250, scale: 0.5 },
        aerial,
        point: { x: 80, y: 40 },
      }),
    ).toEqual({
      scale: 0.5,
      x: -1500,
      y: -750,
    })
  })
})

describe('QML DrawSurvey helpers', () => {
  it('maps QML survey screen points into SelectItem geometry and millimeter labels', () => {
    expect(
      buildQmlSurveyOverlay({
        start: { x: 100, y: 50 },
        end: { x: 250, y: 170 },
        scale: 0.5,
        scan3dScaleX: 0.5,
      }),
    ).toEqual({
      rect: { x: 100, y: 50, width: 150, height: 120 },
      drawWidth: 150,
      drawHeight: 120,
      diagonalRotation: 38.66,
      labels: {
        width: '150 mm',
        height: '120 mm',
        diagonal: '192 mm',
      },
      cornerPolyline: '0,0 150,0 150,120',
      diagonalLine: { x1: 0, y1: 0, x2: 150, y2: 120 },
    })
  })

  it('matches QML DrawSelectItem opposite-quadrant path selection', () => {
    expect(
      buildQmlSurveyOverlay({
        start: { x: 250, y: 50 },
        end: { x: 100, y: 170 },
        scale: 1,
        scan3dScaleX: 1,
      }),
    ).toMatchObject({
      rect: { x: 100, y: 50, width: 150, height: 120 },
      drawWidth: -150,
      drawHeight: 120,
      cornerPolyline: '150,0 150,120 0,120',
      diagonalLine: { x1: 150, y1: 0, x2: 0, y2: 120 },
    })
  })
})

describe('QML UserPointShow helpers', () => {
  it('maps a QML user sign point into an 8px green marker and z label', () => {
    expect(
      buildQmlUserPointOverlay({
        point: { x: 200, y: 100 },
        transform: { x: 10, y: 20, scale: 0.5 },
        rawValue: 48000,
        pointValueShowType: 'mm-relative',
        pointValueOptions: {
          scan3dScaleZ: 0.02,
          medianZ: 47000,
        },
      }),
    ).toEqual({
      marker: { x: 106, y: 66, width: 8, height: 8 },
      label: {
        x: 110,
        y: 74,
        text: '20.00',
        color: 'yellow',
      },
    })
  })

  it('keeps QML user sign point labels yellow even above the 50mm threshold', () => {
    expect(
      buildQmlUserPointOverlay({
        point: { x: 200, y: 100 },
        transform: { x: 0, y: 0, scale: 1 },
        rawValue: 5100,
        pointValueShowType: 'mm-relative',
        pointValueOptions: {
          scan3dScaleZ: 0.01,
          medianZ: 0,
        },
      }).label,
    ).toMatchObject({
      text: '51.00',
      color: 'yellow',
    })
  })
})

describe('QML DbPointShow helpers', () => {
  it('filters QML database points the same way PointTool.addDbPoint does', () => {
    expect(normalizeQmlDbPoint({ x: 10, y: 20, z_mm: 14, type: 'max_inner' }, 0)).toBeNull()
    expect(normalizeQmlDbPoint({ y: 20, z_mm: 30, type: 'max_inner' }, 1)).toBeNull()
    expect(normalizeQmlDbPoint({ x: 10, y: 20, z_mm: 30, type: 'max_inner' }, 2)).toMatchObject({
      id: '2',
      point: { x: 10, y: 20 },
      labelPoint: { x: 10, y: 20 },
      zMm: 30,
      type: 'max_inner',
    })
  })

  it('projects QML database point labels against inner_ellipse and type', () => {
    const innerEllipse = {
      center: { x: 100, y: 100 },
      axes: { width: 400, height: 300 },
    }

    expect(projectQmlDbPointLabel({ point: { x: 500, y: 100 }, type: 'max_inner', innerEllipse })).toEqual({
      x: 150,
      y: 100,
    })
    expect(projectQmlDbPointLabel({ point: { x: 500, y: 100 }, type: 'min_outer', innerEllipse })).toEqual({
      x: 300,
      y: 100,
    })
  })

  it('maps QML database points into 4px red markers and threshold-colored labels', () => {
    expect(
      buildQmlDbPointOverlay({
        point: { x: 200, y: 100 },
        labelPoint: { x: 200, y: 100 },
        transform: { x: 10, y: 20, scale: 0.5 },
        zMm: 42,
      }),
    ).toEqual({
      marker: { x: 108, y: 68, width: 4, height: 4 },
      label: {
        x: 110,
        y: 70,
        text: '42',
        color: 'yellow',
      },
    })

    expect(
      buildQmlDbPointOverlay({
        point: { x: 10, y: 10 },
        labelPoint: { x: 10, y: 10 },
        transform: { x: 0, y: 0, scale: 1 },
        zMm: 51,
      }).label,
    ).toMatchObject({
      text: '51',
      color: 'red',
    })
  })
})

describe('QML DrawView helpers', () => {
  it('maps QML DrawView height lines and inner ellipse into screen overlays', () => {
    expect(
      buildQmlDrawViewOverlay({
        lineSegments: [
          {
            pointL: [10, 20],
            pointR: [30, 20],
            points: [],
          },
        ],
        innerEllipse: {
          center: { x: 100, y: 200 },
          axes: { width: 80, height: 120 },
        },
        transform: { x: 5, y: 6, scale: 2 },
        pointValueOptions: {
          scan3dScaleX: 0.5,
        },
      }),
    ).toEqual({
      lineSegments: [
        {
          x1: 25,
          y1: 46,
          x2: 65,
          y2: 46,
        },
      ],
      taperSegments: [],
      ellipse: {
        cx: 205,
        cy: 406,
        rx: 120,
        ry: 80,
      },
      axes: {
        major: {
          x1: 85,
          y1: 406,
          x2: 325,
          y2: 406,
        },
        minor: {
          x1: 205,
          y1: 326,
          x2: 205,
          y2: 486,
        },
      },
      labels: {
        major: {
          x: 210,
          y: 352.667,
          text: '60',
        },
        minor: {
          x: 245,
          y: 411,
          text: '40',
        },
      },
      perpendicularPoint: null,
    })
  })

  it('mirrors QML DrawView txModel taper lines and perpendicular point marker', () => {
    expect(
      buildQmlDrawViewOverlay({
        lineSegments: [
          {
            pointL: [0, 0],
            pointR: [100, 0],
            points: [
              [0, 0, 100],
              [30, 0, 1000],
              [60, 0, 0],
            ],
          },
        ],
        transform: { x: 5, y: 6, scale: 2 },
        taperSegmentsEnabled: true,
        warningThresholdUp: 50,
        warningThresholdDown: -50,
        perpendicularLine: {
          start: { x: 0, y: 0 },
          end: { x: 100, y: 0 },
        },
        hoverPoint: { x: 60, y: 40 },
        pointValueOptions: {
          scan3dScaleZ: 0.1,
          scan3dCoordinateOffsetZ: 0,
          medianZ: 0,
        },
      }),
    ).toMatchObject({
      taperSegments: [
        {
          x1: 65,
          y1: 6,
          x2: 125,
          y2: 6,
          reverse: 1,
        },
      ],
      perpendicularPoint: {
        x: 123,
        y: 4,
        width: 4,
        height: 4,
      },
    })
  })
})

describe('buildDefectLabelText', () => {
  it('matches QML defect-label visibility by hiding or showing defect names', () => {
    const defect = {
      defectType: '烂边',
      confidence: 0.703,
    }

    expect(buildDefectLabelText(defect, false)).toBe('')
    expect(buildDefectLabelText(defect, true)).toBe('烂边 70%')
  })
})

describe('buildManualAnnotationRect', () => {
  it('maps a QML-style drag into a rounded image rectangle', () => {
    expect(
      buildManualAnnotationRect({
        start: { x: 100.2, y: 120.8 },
        end: { x: 80.1, y: 160.4 },
      }),
    ).toEqual({
      x: 80,
      y: 121,
      width: 20,
      height: 40,
    })
  })

  it('ignores selected rectangles smaller than the QML 10px threshold', () => {
    expect(
      buildManualAnnotationRect({
        start: { x: 100, y: 100 },
        end: { x: 109, y: 140 },
      }),
    ).toBeNull()
  })
})
