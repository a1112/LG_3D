/**
 * 图像加载策略工具
 * 实现基于显示器尺寸的渐进式图像加载
 */

// 缩放级别定义
export type ZoomLevel = 'thumbnail' | 'low' | 'medium' | 'high' | 'original'

// 缩放级别配置
export const ZOOM_LEVELS = {
  thumbnail: { scale: 0.1, maxSize: 200 },
  low: { scale: 0.25, maxSize: 400 },
  medium: { scale: 0.5, maxSize: 800 },
  high: { scale: 0.75, maxSize: 1200 },
  original: { scale: 1.0, maxSize: Infinity },
}

// 缩放阈值（当缩放超过这些值时切换到下一级别）
export const ZOOM_THRESHOLDS = {
  thumbnail: 0.15,
  low: 0.3,
  medium: 0.6,
  high: 0.9,
}

/**
 * 获取当前缩放级别
 */
export function getZoomLevel(zoom: number): ZoomLevel {
  if (zoom <= ZOOM_THRESHOLDS.thumbnail) return 'thumbnail'
  if (zoom <= ZOOM_THRESHOLDS.low) return 'low'
  if (zoom <= ZOOM_THRESHOLDS.medium) return 'medium'
  if (zoom <= ZOOM_THRESHOLDS.high) return 'high'
  return 'original'
}

/**
 * 根据容器尺寸和DPR计算合适的图像尺寸
 */
export function calculateImageSize(
  containerWidth: number,
  containerHeight: number,
  dpr: number = window.devicePixelRatio || 1,
  originalWidth?: number,
  originalHeight?: number
): { width: number; height: number; shouldUseOriginal: boolean } {
  // 考虑设备像素比，确保在高DPR屏幕上清晰
  const targetWidth = containerWidth * dpr
  const targetHeight = containerHeight * dpr

  // 如果没有原始尺寸，直接返回目标尺寸
  if (!originalWidth || !originalHeight) {
    return {
      width: Math.ceil(targetWidth),
      height: Math.ceil(targetHeight),
      shouldUseOriginal: false,
    }
  }

  // 如果目标尺寸接近或超过原始尺寸，使用原图
  const shouldUseOriginal =
    targetWidth >= originalWidth * 0.9 || targetHeight >= originalHeight * 0.9

  if (shouldUseOriginal) {
    return {
      width: originalWidth,
      height: originalHeight,
      shouldUseOriginal: true,
    }
  }

  // 计算缩放比例，保持宽高比
  const scaleX = targetWidth / originalWidth
  const scaleY = targetHeight / originalHeight
  const scale = Math.min(scaleX, scaleY)

  return {
    width: Math.ceil(originalWidth * scale),
    height: Math.ceil(originalHeight * scale),
    shouldUseOriginal: false,
  }
}

/**
 * 根据可视区域计算最佳图像尺寸
 */
export interface ViewportInfo {
  width: number
  height: number
  dpr: number
  zoom: number
}

export function calculateOptimalImageSize(
  viewport: ViewportInfo,
  originalWidth?: number,
  originalHeight?: number
): { width: number; height: number; level: ZoomLevel } {
  // 根据当前缩放级别计算需要的尺寸
  const level = getZoomLevel(viewport.zoom)
  const levelConfig = ZOOM_LEVELS[level]

  // 基础尺寸
  let targetWidth = viewport.width * viewport.dpr
  let targetHeight = viewport.height * viewport.dpr

  // 应用缩放级别的缩放因子
  targetWidth = Math.min(targetWidth * viewport.zoom, levelConfig.maxSize)
  targetHeight = Math.min(targetHeight * viewport.zoom, levelConfig.maxSize)

  // 如果有原始尺寸，确保不超过
  if (originalWidth && originalHeight) {
    const width = Math.min(Math.ceil(targetWidth), originalWidth)
    const height = Math.min(Math.ceil(targetHeight), originalHeight)

    // 如果接近原始尺寸，直接使用原图
    if (level === 'original' || (width / originalWidth > 0.9)) {
      return { width: originalWidth, height: originalHeight, level: 'original' }
    }

    return { width, height, level }
  }

  return {
    width: Math.ceil(targetWidth),
    height: Math.ceil(targetHeight),
    level,
  }
}

/**
 * 生成带尺寸参数的图像URL
 */
export function getSizedImageUrl(
  baseUrl: string,
  width: number,
  height: number,
  quality: number = 85
): string {
  const url = new URL(baseUrl, window.location.origin)

  // 添加尺寸参数
  url.searchParams.set('width', width.toString())
  url.searchParams.set('height', height.toString())
  url.searchParams.set('quality', quality.toString())

  return url.toString()
}

/**
 * 图像加载状态
 */
export interface ImageLoadState {
  url: string
  level: ZoomLevel
  width: number
  height: number
  loaded: boolean
  loading: boolean
  error: boolean
}

/**
 * 预加载图像
 */
export function preloadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = url
  })
}

/**
 * 批量预加载图像（用于渐进式加载）
 */
export async function progressiveImageLoad(
  urls: string[],
  onProgress?: (loaded: number, total: number) => void
): Promise<HTMLImageElement[]> {
  const images: HTMLImageElement[] = []
  const total = urls.length

  for (let i = 0; i < total; i++) {
    try {
      const img = await preloadImage(urls[i])
      images.push(img)
      onProgress?.(i + 1, total)
    } catch (error) {
      console.error(`Failed to load image: ${urls[i]}`, error)
    }
  }

  return images
}

/**
 * 计算内存使用量（用于缓存管理）
 */
export function estimateMemoryUsage(width: number, height: number): number {
  // RGBA格式，每个像素4字节
  return width * height * 4
}

/**
 * 判断是否应该加载更高质量的图像
 */
export function shouldUpgradeQuality(
  currentLevel: ZoomLevel,
  newLevel: ZoomLevel,
  currentZoom: number,
  newZoom: number
): boolean {
  // 如果缩放级别提升
  const levelOrder: ZoomLevel[] = ['thumbnail', 'low', 'medium', 'high', 'original']
  const currentIndex = levelOrder.indexOf(currentLevel)
  const newIndex = levelOrder.indexOf(newLevel)

  return newIndex > currentIndex && newZoom > currentZoom * 1.2
}
