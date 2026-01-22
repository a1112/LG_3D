/**
 * 渐进式图像组件
 * 支持缩放、自动质量调整、缓存
 */

import React, { useState, useRef, useEffect } from 'react'
import { Spin, Alert } from 'antd'
import { ZoomInOutlined, ZoomOutOutlined, ReloadOutlined } from '@ant-design/icons'
import { useProgressiveImage } from '@/hooks/useProgressiveImage'
import type { ZoomLevel } from '@/utils/imageLoader'
import './ProgressiveImage.css'

interface ProgressiveImageProps {
  baseUrl: string
  originalWidth?: number
  originalHeight?: number
  initialZoom?: number
  minZoom?: number
  maxZoom?: number
  showControls?: boolean
  enableCache?: boolean
  className?: string
  style?: React.CSSProperties
  onLoad?: (level: ZoomLevel, width: number, height: number) => void
  onError?: (error: Error) => void
}

function ProgressiveImage({
  baseUrl,
  originalWidth,
  originalHeight,
  initialZoom = 1,
  minZoom = 0.1,
  maxZoom = 5,
  showControls = true,
  enableCache = true,
  className = '',
  style,
  onLoad,
  onError,
}: ProgressiveImageProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  const {
    currentUrl,
    currentLevel,
    currentWidth,
    currentHeight,
    isLoading,
    error,
    zoom,
    updateZoom,
    reload,
  } = useProgressiveImage({
    baseUrl,
    originalWidth,
    originalHeight,
    initialZoom,
    enableCache,
    onLoad,
    onError,
  })

  /**
   * 处理滚轮缩放
   */
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.1 : 0.1
    const newZoom = Math.max(minZoom, Math.min(maxZoom, zoom + delta))
    updateZoom(newZoom)
  }

  /**
   * 处理拖拽平移
   */
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) {
      setIsDragging(true)
      setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  /**
   * 重置位置和缩放
   */
  const handleReset = () => {
    setPosition({ x: 0, y: 0 })
    updateZoom(initialZoom)
  }

  /**
   * 缩放按钮处理
   */
  const handleZoomIn = () => {
    updateZoom(Math.min(maxZoom, zoom + 0.2))
  }

  const handleZoomOut = () => {
    updateZoom(Math.max(minZoom, zoom - 0.2))
  }

  // 鼠标松开时停止拖拽
  useEffect(() => {
    const handleMouseUpGlobal = () => setIsDragging(false)
    window.addEventListener('mouseup', handleMouseUpGlobal)
    return () => window.removeEventListener('mouseup', handleMouseUpGlobal)
  }, [])

  return (
    <div
      ref={containerRef}
      className={`progressive-image-container ${className} ${isDragging ? 'dragging' : ''}`}
      style={style}
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* 图像容器 */}
      <div
        className="image-viewport"
        style={{
          transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`,
        }}
      >
        {currentUrl && (
          <img
            src={currentUrl}
            alt="Progressive loaded"
            style={{
              width: originalWidth ? 'auto' : '100%',
              height: originalHeight ? 'auto' : '100%',
              maxWidth: 'none',
            }}
            draggable={false}
          />
        )}
      </div>

      {/* 加载指示器 */}
      {isLoading && !currentUrl && (
        <div className="loading-overlay">
          <Spin size="large" />
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="error-overlay">
          <Alert
            message="加载失败"
            description={error.message}
            type="error"
            showIcon
            action={
              <a onClick={reload} className="retry-link">
                <ReloadOutlined /> 重试
              </a>
            }
          />
        </div>
      )}

      {/* 控制栏 */}
      {showControls && currentUrl && !error && (
        <div className="image-controls">
          <div className="control-group">
            <button onClick={handleZoomOut} disabled={zoom <= minZoom}>
              <ZoomOutOutlined />
            </button>
            <span className="zoom-level">{Math.round(zoom * 100)}%</span>
            <button onClick={handleZoomIn} disabled={zoom >= maxZoom}>
              <ZoomInOutlined />
            </button>
          </div>

          <div className="control-group">
            <button onClick={handleReset} title="重置视图">
              <ReloadOutlined />
            </button>
          </div>

          <div className="info-group">
            <span className="quality-level">{currentLevel}</span>
            {currentWidth > 0 && currentHeight > 0 && (
              <span className="image-size">
                {currentWidth} × {currentHeight}
              </span>
            )}
          </div>
        </div>
      )}

      {/* 操作提示 */}
      {showControls && currentUrl && !error && !isDragging && (
        <div className="image-hint">
          滚轮缩放 • 拖拽平移
        </div>
      )}
    </div>
  )
}

export default ProgressiveImage
