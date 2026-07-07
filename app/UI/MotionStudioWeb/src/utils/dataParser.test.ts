import { describe, expect, it } from 'vitest'

import {
  canvas3DDataSourceLabel,
  parseHeightLineSegmentsToPointCloud,
  resolveCanvas3DDataSource,
} from './dataParser'

describe('QML height data parser', () => {
  it('converts Python heightData line segments into point-cloud buffers', () => {
    const result = parseHeightLineSegmentsToPointCloud([
      {
        pointL: [10, 20],
        pointR: [12, 20],
        points: [
          [10, 20, 1000],
          [11, 20, 1010],
          [12, 20, 1020],
        ],
      },
      {
        pointL: [30, 21],
        pointR: [31, 21],
        points: [
          [30, 21, 980],
          [31, 21, 990],
        ],
      },
    ])

    expect(result.count).toBe(5)
    expect(Array.from(result.positions)).toEqual([
      -10.5, -0.5, 0,
      -9.5, -0.5, 10,
      -8.5, -0.5, 20,
      9.5, 0.5, -20,
      10.5, 0.5, -10,
    ])
    expect(result.colors.length).toBe(15)
    expect(Array.from(result.colors.slice(0, 3))).toEqual([1, 1, 0])
  })

  it('skips malformed points while preserving valid Python tuple data', () => {
    const result = parseHeightLineSegmentsToPointCloud([
      {
        points: [
          [1, 2, 3],
          [4, 5],
          ['x', 9, 10],
          [7, 8, 9],
        ],
      },
      null,
      { points: 'bad' },
    ])

    expect(result.count).toBe(2)
    expect(Array.from(result.positions)).toEqual([-3, -3, -3, 3, 3, 3])
  })

  it('uses heightData point cloud as the 3D canvas fallback when render data is unavailable', () => {
    const result = resolveCanvas3DDataSource(null, [
      {
        pointL: [100, 200],
        pointR: [101, 200],
        points: [
          [100, 200, 10],
          [101, 200, 12],
        ],
      },
    ])

    expect(result.kind).toBe('pointCloud')
    if (result.kind !== 'pointCloud') throw new Error('expected pointCloud data source')
    expect(result.pointCloud.count).toBe(2)
    expect(Array.from(result.pointCloud.positions)).toEqual([-0.5, 0, -1, 0.5, 0, 1])
  })

  it('keeps backend render bytes ahead of heightData fallback for the 3D canvas', () => {
    const renderData = new ArrayBuffer(8)
    const result = resolveCanvas3DDataSource(renderData, [
      {
        pointL: [1, 2],
        pointR: [3, 2],
        points: [[1, 2, 3]],
      },
    ])

    expect(result).toEqual({ kind: 'buffer', data: renderData })
  })

  it('ignores empty render bytes so heightData can supply the 3D canvas fallback', () => {
    const result = resolveCanvas3DDataSource(new ArrayBuffer(0), [
      {
        pointL: [20, 30],
        pointR: [21, 30],
        points: [
          [20, 30, 100],
          [21, 30, 104],
        ],
      },
    ])

    expect(result.kind).toBe('pointCloud')
    if (result.kind !== 'pointCloud') throw new Error('expected pointCloud fallback')
    expect(result.pointCloud.count).toBe(2)
  })

  it('describes 3D canvas data sources for the operator status bar', () => {
    expect(canvas3DDataSourceLabel({ kind: 'empty' })).toBe('等待3D数据加载')
    expect(canvas3DDataSourceLabel({ kind: 'buffer', data: new ArrayBuffer(1) })).toBe('3D高度渲染图')
    expect(
      canvas3DDataSourceLabel({
        kind: 'pointCloud',
        pointCloud: {
          positions: new Float32Array(6),
          colors: new Float32Array(6),
          count: 2,
        },
      }),
    ).toBe('高度线点云 fallback (2 点)')
  })
})
