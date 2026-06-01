import { describe, expect, it } from 'vitest'

import { getVisibleTiles } from './utils'

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
