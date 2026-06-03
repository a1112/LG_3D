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

export interface VisibleTileParams {
  viewRect: Rect
  imageSize: Size
  tileSize: number
  scale: number
  fixedLevel?: number
  maxLevel?: number
}

export function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
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
