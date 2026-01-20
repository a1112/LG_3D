import { useState } from 'react'
import { Card, Row, Col, List, Tag, Image, Empty, Spin } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import CoilList from '@/components/CoilList'
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

  // 获取表面全图URL
  const getSurfaceImageUrl = () => {
    if (!currentCoil) return ''
    return imageApi.getPreview(surfaceKey, currentCoil.id, 'preview')
  }

  return (
    <div className="defect-show-page">
      <Row gutter={16} style={{ height: '100%' }}>
        {/* 左侧卷材列表 */}
        <Col span={6}>
          <Card title="卷材列表" className="full-height-card" bodyStyle={{ padding: 0 }}>
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
        <Col span={8}>
          <Card
            title={`缺陷列表 (${defects.length})`}
            className="full-height-card"
            bodyStyle={{ padding: 0 }}
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
              <List
                dataSource={defects}
                renderItem={(defect) => (
                  <List.Item
                    key={defect.id}
                    onClick={() => handleDefectSelect(defect)}
                    className={`defect-item ${
                      selectedDefect?.id === defect.id ? 'selected' : ''
                    }`}
                  >
                    <List.Item.Meta
                      title={
                        <div>
                          <Tag color="red">{defect.defectType}</Tag>
                          <span>位置: ({defect.position.x}, {defect.position.y})</span>
                        </div>
                      }
                      description={
                        <div>
                          <div>大小: {defect.size.width} x {defect.size.height}</div>
                          <div>置信度: {(defect.confidence * 100).toFixed(1)}%</div>
                          {defect.description && (
                            <div>备注: {defect.description}</div>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        {/* 右侧缺陷图像展示 */}
        <Col span={10}>
          <Card
            title={selectedDefect ? '缺陷详情' : '表面全图'}
            className="full-height-card"
          >
            {!currentCoil ? (
              <Empty description="请选择卷材" />
            ) : selectedDefect ? (
              <div className="defect-detail">
                <div className="defect-info">
                  <p><strong>缺陷类型:</strong> <Tag color="red">{selectedDefect.defectType}</Tag></p>
                  <p><strong>位置:</strong> ({selectedDefect.position.x}, {selectedDefect.position.y})</p>
                  <p><strong>大小:</strong> {selectedDefect.size.width} x {selectedDefect.size.height}</p>
                  <p><strong>置信度:</strong> {(selectedDefect.confidence * 100).toFixed(1)}%</p>
                  {selectedDefect.description && (
                    <p><strong>备注:</strong> {selectedDefect.description}</p>
                  )}
                </div>
                <div className="defect-image">
                  <Image
                    src={getDefectImageUrl(selectedDefect)}
                    alt="缺陷图像"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            ) : (
              <Image
                src={getSurfaceImageUrl()}
                alt="表面全图"
                style={{ width: '100%' }}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default DefectShowPage
