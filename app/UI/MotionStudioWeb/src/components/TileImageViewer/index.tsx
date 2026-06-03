import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import type { DefectData } from '@/types'
import { clamp, getVisibleTiles, type Point, type Rect, type Size, type Tile } from './utils'
import './TileImageViewer.css'

const tileCache = new Map<string, HTMLImageElement>()
const tileLoading = new Set<string>()

interface TileImageViewerProps {
  imageUrl: string
  previewUrl?: string
  defects?: DefectData[]
  selectedDefectId?: number | null
  tileCount?: number
  maxLevel?: number
  className?: string
  onDefectSelect?: (defect: DefectData | null) => void
}

interface ImageInfo extends Size {
  ready: boolean
}

function buildTileUrl(imageUrl: string, tile: Tile, tileCount: number) {
  const url = new URL(imageUrl, window.location.origin)
  // Existing QML/backend contract uses row as the horizontal tile index and col as the vertical tile index.
  url.searchParams.set('row', tile.col.toString())
  url.searchParams.set('col', tile.row.toString())
  url.searchParams.set('count', tileCount.toString())
  url.searchParams.set('level', tile.level.toString())
  return url.toString()
}

function defectRect(defect: DefectData): Rect {
  return {
    x: defect.position.x,
    y: defect.position.y,
    width: defect.size.width,
    height: defect.size.height,
  }
}

function rectContains(rect: Rect, point: Point) {
  return point.x >= rect.x && point.x <= rect.x + rect.width && point.y >= rect.y && point.y <= rect.y + rect.height
}

function resolveLevel(scale: number, maxLevel: number) {
  if (scale >= 1.2) return maxLevel
  if (scale >= 0.75) return Math.min(maxLevel, 3)
  if (scale >= 0.38) return Math.min(maxLevel, 2)
  if (scale >= 0.2) return Math.min(maxLevel, 1)
  return 0
}

export default function TileImageViewer({
  imageUrl,
  previewUrl,
  defects = [],
  selectedDefectId,
  tileCount = 3,
  maxLevel = 4,
  className,
  onDefectSelect,
}: TileImageViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const transformRef = useRef({ x: 0, y: 0, scale: 1 })
  const draggingRef = useRef(false)
  const lastPointerRef = useRef<Point>({ x: 0, y: 0 })
  const [imageInfo, setImageInfo] = useState<ImageInfo>({ width: 0, height: 0, ready: false })
  const [level, setLevel] = useState(0)
  const [cursor, setCursor] = useState('grab')
  const [, setFrame] = useState(0)

  const selectedDefect = useMemo(
    () => defects.find((defect) => defect.id === selectedDefectId) ?? null,
    [defects, selectedDefectId],
  )

  const requestDraw = useCallback(() => {
    setFrame((frame) => frame + 1)
  }, [])

  useEffect(() => {
    if (!imageUrl) {
      setImageInfo({ width: 0, height: 0, ready: false })
      return
    }

    const controller = new AbortController()
    const url = new URL(imageUrl, window.location.origin)
    url.searchParams.set('count', '0')

    fetch(url, { signal: controller.signal })
      .then((response) => response.json())
      .then((data: Partial<Size>) => {
        const width = Number(data.width)
        const height = Number(data.height)
        if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
          setImageInfo({ width, height, ready: true })
        } else {
          setImageInfo({ width: 8192, height: 6144, ready: true })
        }
      })
      .catch(() => {
        setImageInfo({ width: 8192, height: 6144, ready: true })
      })

    return () => controller.abort()
  }, [imageUrl])

  useEffect(() => {
    const container = containerRef.current
    if (!container || !imageInfo.ready) return

    const rect = container.getBoundingClientRect()
    const scale = Math.min(rect.width / imageInfo.width, rect.height / imageInfo.height)
    const nextScale = clamp(scale, 0.04, 3)
    transformRef.current = {
      scale: nextScale,
      x: (rect.width - imageInfo.width * nextScale) / 2,
      y: (rect.height - imageInfo.height * nextScale) / 2,
    }
    setLevel(resolveLevel(nextScale, maxLevel))
    requestDraw()
  }, [imageInfo, maxLevel, requestDraw])

  useEffect(() => {
    const canvas = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container || !imageInfo.ready) return

    const dpr = window.devicePixelRatio || 1
    const rect = container.getBoundingClientRect()
    canvas.width = Math.max(1, Math.floor(rect.width * dpr))
    canvas.height = Math.max(1, Math.floor(rect.height * dpr))
    canvas.style.width = `${rect.width}px`
    canvas.style.height = `${rect.height}px`

    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.clearRect(0, 0, rect.width, rect.height)
    ctx.fillStyle = '#071018'
    ctx.fillRect(0, 0, rect.width, rect.height)

    const transform = transformRef.current
    if (previewUrl) {
      const preview = tileCache.get(previewUrl)
      if (preview?.complete) {
        ctx.globalAlpha = 0.45
        ctx.drawImage(preview, transform.x, transform.y, imageInfo.width * transform.scale, imageInfo.height * transform.scale)
        ctx.globalAlpha = 1
      } else if (!tileLoading.has(previewUrl)) {
        tileLoading.add(previewUrl)
        const img = new Image()
        img.onload = () => {
          tileCache.set(previewUrl, img)
          tileLoading.delete(previewUrl)
          requestDraw()
        }
        img.onerror = () => tileLoading.delete(previewUrl)
        img.src = previewUrl
      }
    }

    const viewRect = {
      x: -transform.x / transform.scale,
      y: -transform.y / transform.scale,
      width: rect.width / transform.scale,
      height: rect.height / transform.scale,
    }
    const tiles = getVisibleTiles({
      viewRect,
      imageSize: imageInfo,
      tileSize: Math.max(imageInfo.width, imageInfo.height) / tileCount,
      scale: transform.scale,
      fixedLevel: level,
      maxLevel,
    })

    ctx.save()
    ctx.translate(transform.x, transform.y)
    ctx.scale(transform.scale, transform.scale)
    for (const tile of tiles) {
      const url = buildTileUrl(imageUrl, tile, tileCount)
      const cached = tileCache.get(url)
      ctx.fillStyle = '#0b1720'
      ctx.fillRect(tile.x, tile.y, tile.width, tile.height)
      if (cached?.complete) {
        ctx.drawImage(cached, tile.x, tile.y, tile.width, tile.height)
      } else if (!tileLoading.has(url)) {
        tileLoading.add(url)
        const img = new Image()
        img.onload = () => {
          tileCache.set(url, img)
          tileLoading.delete(url)
          requestDraw()
        }
        img.onerror = () => tileLoading.delete(url)
        img.src = url
      }
      ctx.strokeStyle = 'rgba(72, 126, 156, 0.35)'
      ctx.lineWidth = 1 / transform.scale
      ctx.strokeRect(tile.x, tile.y, tile.width, tile.height)
    }

    for (const defect of defects) {
      const rectInfo = defectRect(defect)
      const isSelected = defect.id === selectedDefectId
      ctx.strokeStyle = isSelected ? '#ffb020' : '#ff4d4f'
      ctx.fillStyle = isSelected ? 'rgba(255, 176, 32, 0.16)' : 'rgba(255, 77, 79, 0.12)'
      ctx.lineWidth = (isSelected ? 3 : 2) / transform.scale
      ctx.fillRect(rectInfo.x, rectInfo.y, rectInfo.width, rectInfo.height)
      ctx.strokeRect(rectInfo.x, rectInfo.y, rectInfo.width, rectInfo.height)
    }
    ctx.restore()
  })

  const screenToWorld = (clientX: number, clientY: number): Point | null => {
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return null
    const transform = transformRef.current
    return {
      x: (clientX - rect.left - transform.x) / transform.scale,
      y: (clientY - rect.top - transform.y) / transform.scale,
    }
  }

  const handleWheel = (event: React.WheelEvent) => {
    event.preventDefault()
    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    const current = transformRef.current
    const pointer = {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    }
    const world = {
      x: (pointer.x - current.x) / current.scale,
      y: (pointer.y - current.y) / current.scale,
    }
    const nextScale = clamp(current.scale * (event.deltaY < 0 ? 1.18 : 0.84), 0.04, 4)
    transformRef.current = {
      scale: nextScale,
      x: pointer.x - world.x * nextScale,
      y: pointer.y - world.y * nextScale,
    }
    setLevel(resolveLevel(nextScale, maxLevel))
    requestDraw()
  }

  const handlePointerDown = (event: React.PointerEvent) => {
    const world = screenToWorld(event.clientX, event.clientY)
    const defect = world ? defects.find((item) => rectContains(defectRect(item), world)) : null
    if (defect) {
      onDefectSelect?.(defect)
      requestDraw()
      return
    }
    draggingRef.current = true
    lastPointerRef.current = { x: event.clientX, y: event.clientY }
    setCursor('grabbing')
  }

  const handlePointerMove = (event: React.PointerEvent) => {
    if (!draggingRef.current) return
    const dx = event.clientX - lastPointerRef.current.x
    const dy = event.clientY - lastPointerRef.current.y
    lastPointerRef.current = { x: event.clientX, y: event.clientY }
    transformRef.current = {
      ...transformRef.current,
      x: transformRef.current.x + dx,
      y: transformRef.current.y + dy,
    }
    requestDraw()
  }

  const handlePointerUp = () => {
    draggingRef.current = false
    setCursor('grab')
  }

  return (
    <div ref={containerRef} className={`tile-image-viewer ${className ?? ''}`}>
      <canvas
        ref={canvasRef}
        className="tile-image-canvas"
        style={{ cursor }}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      />
      <div className="tile-image-hud">
        <span>L{level}</span>
        <span>{imageInfo.ready ? `${Math.round(imageInfo.width)} x ${Math.round(imageInfo.height)}` : '加载图像信息'}</span>
        <span>{selectedDefect ? `缺陷 ${selectedDefect.defectType}` : '滚轮缩放 / 拖拽平移'}</span>
      </div>
    </div>
  )
}
