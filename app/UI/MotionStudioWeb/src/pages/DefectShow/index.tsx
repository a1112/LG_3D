import { useState } from 'react'
import { Card, Row, Col, Empty, Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import CoilList from '@/components/CoilList'
import ProgressiveImage from '@/components/ProgressiveImage'
import { useCoilStore } from '@/stores/coilStore'
import { coilApi, defectApi, imageApi } from '@/services/api'
import type { DefectData } from '@/types'
import './DefectShow.css'

function DefectShowPage() {
  const { currentCoil, surfaceKey, setCurrentCoil } = useCoilStore()
  const [selectedDefect, setSelectedDefect] = useState<DefectData | null>(null)

  // 获取卷材列表
  const { data: coilListData, isLoading: listLoading } = useQuery({
    queryKey: ['coilList'],
    queryFn: () => coilApi.getCoilList(50),
  })

  // 获取缺陷数据
  const { data: defectsData, isLoading: defectsLoading } = useQuery({
    queryKey: ['defects', currentCoil?.id, surfaceKey],
    queryFn: () =>
      defectApi.getDefects(currentCoil?.id || 0, surfaceKey),
    enabled: !!currentCoil,
  })

  const handleCoilSelect = (coil: any) => {
    setCurrentCoil(coil)
    setSelectedDefect(null)
  }

  const handleDefectSelect = (defect: DefectData) => {
    setSelectedDefect(defect)
  }

  const defects = defectsData?.data || []

  // 获取表面全图URL
  const getSurfaceImageUrl = () => {
    if (!currentCoil) return ''
    return imageApi.getPreview(surfaceKey, currentCoil.id, 'preview')
  }

  // 获取缺陷图像URL
  const getDefectImageUrl = (defect: DefectData) => {
    if (!currentCoil) return ''
    return imageApi.getDefectImage(
      surfaceKey,
      currentCoil.id,
      'preview',
      defect.position.x,
      defect.position.y,
      defect.size.width,
      defect.size.height
    )
  }

  return (
    <div className="defect-show-page">
      <Row gutter={16} style={{ height: '100%' }}>
        {/* 左侧卷材列表 */}
        <Col span={6}>
          <Card title="卷材列表" className="full-height-card" styles={{ body: { padding: 0 } }}>
            {listLoading ? (
              <div className="loading-container">
                <Spin indicator={<LoadingOutlined spin />} />
              </div>
            ) : (
              <CoilList
                coils={coilListData?.data || []}
                selectedCoil={currentCoil}
                onSelect={handleCoilSelect}
              />
            )}
          </Card>
        </Col>

        {/* 中间缺陷列表 */}
        <Col span={selectedDefect ? 6 : 18}>
          <Card
            title={`缺陷列表 (${defects.length})`}
            className="full-height-card"
            styles={{ body: { padding: 0 } }}
          >
            {!currentCoil ? (
              <Empty description="请选择卷材" />
            ) : defectsLoading ? (
              <div className="loading-container">
                <Spin indicator={<LoadingOutlined spin />} />
              </div>
            ) : defects.length === 0 ? (
              <Empty description="无缺陷数据" />
            ) : (
              <div className="defect-list-container">
                {defects.map((defect) => (
                  <div
                    key={defect.id}
                    className={`defect-item ${
                      selectedDefect?.id === defect.id ? 'selected' : ''
                    }`}
                    onClick={() => handleDefectSelect(defect)}
                  >
                    <div className="defect-header">
                      <span className="defect-type">{defect.defectType}</span>
                      <span className="defect-confidence">
                        {(defect.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="defect-position">
                      位置: ({defect.position.x}, {defect.position.y})
                    </div>
                    <div className="defect-size">
                      大小: {defect.size.width} × {defect.size.height}
                    </div>
                    {defect.description && (
                      <div className="defect-description">{defect.description}</div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </Col>

        {/* 右侧图像展示 */}
        <Col span={selectedDefect ? 12 : 0}>
          <Card
            title="表面全景"
            className="full-height-card"
            styles={{ body: { padding: 0, height: 'calc(100% - 57px)' } }}
          >
            {!currentCoil ? (
              <Empty description="请选择卷材" />
            ) : (
              <ProgressiveImage
                baseUrl={getSurfaceImageUrl()}
                initialZoom={1}
                minZoom={0.5}
                maxZoom={3}
                showControls
                enableCache
                style={{ height: '100%' }}
              />
            )}
          </Card>
        </Col>

        {/* 缺陷详情 */}
        {selectedDefect && (
          <Col span={12}>
            <Card
              title="缺陷详情"
              className="full-height-card"
              styles={{ body: { padding: 0, height: 'calc(100% - 57px)' } }}
            >
              <div className="defect-detail-panel">
                <div className="defect-info">
                  <div className="info-row">
                    <span className="label">缺陷类型:</span>
                    <span className="value">{selectedDefect.defectType}</span>
                  </div>
                  <div className="info-row">
                    <span className="label">位置:</span>
                    <span className="value">
                      ({selectedDefect.position.x}, {selectedDefect.position.y})
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="label">尺寸:</span>
                    <span className="value">
                      {selectedDefect.size.width} × {selectedDefect.size.height}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="label">置信度:</span>
                    <span className="value">
                      {(selectedDefect.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  {selectedDefect.description && (
                    <div className="info-row">
                      <span className="label">备注:</span>
                      <span className="value">{selectedDefect.description}</span>
                    </div>
                  )}
                </div>

                <div className="defect-image-container">
                  <ProgressiveImage
                    baseUrl={getDefectImageUrl(selectedDefect)}
                    originalWidth={selectedDefect.size.width}
                    originalHeight={selectedDefect.size.height}
                    initialZoom={1.5}
                    minZoom={0.5}
                    maxZoom={5}
                    showControls
                    enableCache
                    style={{ height: '100%' }}
                  />
                </div>
              </div>
            </Card>
          </Col>
        )}
      </Row>
    </div>
  )
}

export default DefectShowPage
