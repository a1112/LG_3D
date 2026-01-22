/**
 * 渐进式图像加载 Hook
 * 根据缩放级别和容器尺寸自动加载合适质量的图像
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ZoomLevel,
  calculateOptimalImageSize,
  getZoomLevel,
  shouldUpgradeQuality,
  preloadImage,
  type ViewportInfo,
} from '@/utils/imageLoader'
import { globalImageCache, loadImageWithCache } from '@/utils/imageCache'

interface UseProgressiveImageOptions {
  baseUrl: string
  originalWidth?: number
  originalHeight?: number
  initialZoom?: number
  quality?: number
  enableCache?: boolean
  onLoad?: (level: ZoomLevel, width: number, height: number) => void
  onError?: (error: Error) => void
}

interface ProgressiveImageState {
  currentUrl: string | null
  currentLevel: ZoomLevel
  currentWidth: number
  currentHeight: number
  isLoading: boolean
  error: Error | null
  zoom: number
}

export function useProgressiveImage(options: UseProgressiveImageOptions) {
  const {
    baseUrl,
    originalWidth,
    originalHeight,
    initialZoom = 1,
    quality = 85,
    enableCache = true,
    onLoad,
    onError,
  } = options

  const [state, setState] = useState<ProgressiveImageState>({
    currentUrl: null,
    currentLevel: 'thumbnail',
    currentWidth: 0,
    currentHeight: 0,
    isLoading: true,
    error: null,
    zoom: initialZoom,
  })

  const containerRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const loadingLevelRef = useRef<ZoomLevel | null>(null)

  /**
   * 加载指定级别的图像
   */
  const loadLevel = useCallback(
    async (level: ZoomLevel, viewport: ViewportInfo) => {
      // 避免重复加载同一级别
      if (loadingLevelRef.current === level) return
      loadingLevelRef.current = level

      // 取消之前的请求
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
      abortControllerRef.current = new AbortController()

      try {
        setState((prev) => ({ ...prev, isLoading: true }))

        // 计算最优尺寸
        const { width, height } = calculateOptimalImageSize(
          viewport,
          originalWidth,
          originalHeight
        )

        // 构建带尺寸参数的URL
        const url = new URL(baseUrl, window.location.origin)
        url.searchParams.set('width', width.toString())
        url.searchParams.set('height', height.toString())
        url.searchParams.set('quality', quality.toString())

        const finalUrl = url.toString()

        // 使用缓存加载
        let imageUrl: string
        if (enableCache) {
          imageUrl = await loadImageWithCache(finalUrl, width, height)
        } else {
          const img = await preloadImage(finalUrl)
          imageUrl = img.src
        }

        setState({
          currentUrl: imageUrl,
          currentLevel: level,
          currentWidth: width,
          currentHeight: height,
          isLoading: false,
          error: null,
          zoom: viewport.zoom,
        })

        onLoad?.(level, width, height)
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          console.error('Failed to load image:', error)
          setState((prev) => ({
            ...prev,
            isLoading: false,
            error: error as Error,
          }))
          onError?.(error as Error)
        }
      } finally {
        loadingLevelRef.current = null
      }
    },
    [baseUrl, originalWidth, originalHeight, quality, enableCache, onLoad, onError]
  )

  /**
   * 更新缩放级别
   */
  const updateZoom = useCallback(
    (newZoom: number) => {
      if (!containerRef.current) return

      const rect = containerRef.current.getBoundingClientRect()
      const viewport: ViewportInfo = {
        width: rect.width,
        height: rect.height,
        dpr: window.devicePixelRatio || 1,
        zoom: newZoom,
      }

      const newLevel = getZoomLevel(newZoom)

      // 判断是否需要升级质量
      if (shouldUpgradeQuality(state.currentLevel, newLevel, state.zoom, newZoom)) {
        loadLevel(newLevel, viewport)
      }

      setState((prev) => ({ ...prev, zoom: newZoom }))
    },
    [state.currentLevel, state.zoom, loadLevel]
  )

  /**
   * 重新加载（用于容器尺寸变化）
   */
  const reload = useCallback(() => {
    if (!containerRef.current) return

    const rect = containerRef.current.getBoundingClientRect()
    const viewport: ViewportInfo = {
      width: rect.width,
      height: rect.height,
      dpr: window.devicePixelRatio || 1,
      zoom: state.zoom,
    }

    loadLevel(state.currentLevel, viewport)
  }, [state.zoom, state.currentLevel, loadLevel])

  /**
   * 初始加载和容器尺寸变化监听
   */
  useEffect(() => {
    if (!containerRef.current) return

    // 初始加载
    const rect = containerRef.current.getBoundingClientRect()
    const viewport: ViewportInfo = {
      width: rect.width,
      height: rect.height,
      dpr: window.devicePixelRatio || 1,
      zoom: initialZoom,
    }

    const initialLevel = getZoomLevel(initialZoom)
    loadLevel(initialLevel, viewport)

    // 监听容器尺寸变化
    const resizeObserver = new ResizeObserver(() => {
      reload()
    })

    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [initialZoom, loadLevel, reload])

  return {
    ...state,
    containerRef,
    updateZoom,
    reload,
    // 预加载下一级别
    preloadNextLevel: async () => {
      const levels: ZoomLevel[] = ['thumbnail', 'low', 'medium', 'high', 'original']
      const currentIndex = levels.indexOf(state.currentLevel)
      const nextLevel = levels[currentIndex + 1]

      if (nextLevel && containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        const viewport: ViewportInfo = {
          width: rect.width,
          height: rect.height,
          dpr: window.devicePixelRatio || 1,
          zoom: state.zoom,
        }

        // 后台预加载，不更新状态
        const { width, height } = calculateOptimalImageSize(
          viewport,
          originalWidth,
          originalHeight
        )

        const url = new URL(baseUrl, window.location.origin)
        url.searchParams.set('width', width.toString())
        url.searchParams.set('height', height.toString())
        url.searchParams.set('quality', quality.toString())

        try {
          await loadImageWithCache(url.toString(), width, height)
        } catch (error) {
          console.warn('Failed to preload next level:', error)
        }
      }
    },
  }
}
