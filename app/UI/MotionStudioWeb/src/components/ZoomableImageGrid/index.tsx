/**
 * 可缩放的图像网格组件
 * 用于缺陷检测页面的图像展示
 */

import React, { useState, useRef } from 'react'
import { Card, Row, Col, Tag, Button } from 'antd'
import { FullscreenOutlined } from '@ant-design/icons'
import ProgressiveImage from '../ProgressiveImage'
import type { DefectData } from '@/types'
import './ZoomableImageGrid.css'

interface ZoomableImageGridProps {
  defects: DefectData[]
  surfaceImageUrl: string
  surfaceImageWidth?: number
  surfaceImageHeight?: number
  onDefectClick?: (defect: DefectData) => void
}

function ZoomableImageGrid({
  defects,
  surfaceImageUrl,
  surfaceImageWidth,
  surfaceImageHeight,
  onDefectClick,
}: ZoomableImageGridProps) {
  const [selectedDefect, setSelectedDefect] = useState<DefectData | null>(null)
  const [showFullscreen, setShowFullscreen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleDefectClick = (defect: DefectData) => {
    setSelectedDefect(defect)
    onDefectClick?.(defect)
  }

  const handleFullscreen = () => {
    setShowFullscreen(true)
  }

  return (
    <div ref={containerRef} className="zoomable-image-grid">
      <Row gutter={16}>
        {/* 表面全景图 */}
        <Col span={selectedDefect ? 12 : 24}>
          <Card
            title="表面全景"
            className="image-card"
            bodyStyle={{ padding: 0, height: 500 }}
          >
            <ProgressiveImage
              baseUrl={surfaceImageUrl}
              originalWidth={surfaceImageWidth}
              originalHeight={surfaceImageHeight}
              initialZoom={1}
              minZoom={0.5}
              maxZoom={3}
              showControls
              enableCache
            />
            {!showFullscreen && (
              <Button
                type="primary"
                icon={<FullscreenOutlined />}
                onClick={handleFullscreen}
                style={{
                  position: 'absolute',
                  top: 60,
                  right: 24,
                  zIndex: 10,
                }}
              >
                全屏查看
              </Button>
            )}
          </Card>
        </Col>

        {/* 缺陷详情 */}
        {selectedDefect && (
          <Col span={12}>
            <Card
              title="缺陷详情"
              className="image-card"
              extra={
                <Button
                  size="small"
                  onClick={() => setSelectedDefect(null)}
                >
                  关闭
                </Button>
              }
              bodyStyle={{ padding: 0, height: 500 }}
            >
              <div className="defect-detail">
                <div className="defect-info">
                  <div className="info-item">
                    <span className="label">缺陷类型:</span>
                    <Tag color="red">{selectedDefect.defectType}</Tag>
                  </div>
                  <div className="info-item">
                    <span className="label">位置:</span>
                    <span>
                      ({selectedDefect.position.x}, {selectedDefect.position.y})
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="label">尺寸:</span>
                    <span>
                      {selectedDefect.size.width} × {selectedDefect.size.height}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="label">置信度:</span>
                    <span>{(selectedDefect.confidence * 100).toFixed(1)}%</span>
                  </div>
                  {selectedDefect.description && (
                    <div className="info-item">
                      <span className="label">备注:</span>
                      <span>{selectedDefect.description}</span>
                    </div>
                  )}
                </div>

                <div className="defect-image">
                  <ProgressiveImage
                    baseUrl={`${surfaceImageUrl}/defect/${selectedDefect.id}`}
                    originalWidth={selectedDefect.size.width}
                    originalHeight={selectedDefect.size.height}
                    initialZoom={1.5}
                    minZoom={0.5}
                    maxZoom={5}
                    showControls
                    enableCache
                  />
                </div>
              </div>
            </Card>
          </Col>
        )}
      </Row>

      {/* 缺陷标记列表 */}
      <Card title="缺陷列表" style={{ marginTop: 16 }}>
        <div className="defect-list">
          {defects.map((defect) => (
            <div
              key={defect.id}
              className={`defect-item ${
                selectedDefect?.id === defect.id ? 'selected' : ''
              }`}
              onClick={() => handleDefectClick(defect)}
            >
              <Tag color="red">{defect.defectType}</Tag>
              <span className="defect-position">
                位置: ({defect.position.x}, {defect.position.y})
              </span>
              <span className="defect-confidence">
                置信度: {(defect.confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default ZoomableImageGrid
