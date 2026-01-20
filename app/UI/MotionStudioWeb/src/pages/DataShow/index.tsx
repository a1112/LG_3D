import { useState, useEffect } from 'react'
import { Card, Row, Col, List, Select, Spin, Empty } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import Canvas3D from '@/components/Canvas3D'
import HeightChart from '@/components/HeightChart'
import CoilList from '@/components/CoilList'
import { useCoilStore } from '@/stores/coilStore'
import { coilApi, heightDataApi } from '@/services/api'
import './DataShow.css'

function DataShowPage() {
  const { currentCoil, surfaceKey, setCurrentCoil, setSurfaceKey } = useCoilStore()
  const [renderData, setRenderData] = useState<ArrayBuffer | null>(null)

  // 获取卷材列表
  const { data: coilListData, isLoading: listLoading } = useQuery({
    queryKey: ['coilList'],
    queryFn: () => coilApi.getCoilList(50),
  })

  // 获取3D渲染数据
  const { data: render3DData, isLoading: renderLoading } = useQuery({
    queryKey: ['render3D', currentCoil?.id, surfaceKey],
    queryFn: () =>
      heightDataApi.getRenderData(surfaceKey, currentCoil?.id || 0),
    enabled: !!currentCoil,
  })

  // 获取高度线数据
  const { data: heightLineData, isLoading: heightLoading } = useQuery({
    queryKey: ['heightLine', currentCoil?.id, surfaceKey],
    queryFn: () =>
      heightDataApi.getHeightLine(surfaceKey, currentCoil?.id || 0),
    enabled: !!currentCoil,
  })

  useEffect(() => {
    if (render3DData instanceof ArrayBuffer) {
      setRenderData(render3DData)
    }
  }, [render3DData])

  const handleCoilSelect = (coil: any) => {
    setCurrentCoil(coil)
  }

  const handleSurfaceChange = (value: string) => {
    setSurfaceKey(value)
  }

  return (
    <div className="data-show-page">
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

        {/* 右侧数据展示 */}
        <Col span={18}>
          <Row gutter={[16, 16]} style={{ height: '100%' }}>
            {/* 控制栏 */}
            <Col span={24}>
              <Card size="small">
                <Row align="middle" gutter={16}>
                  <Col>
                    <span>当前卷材: </span>
                    <strong>{currentCoil?.coilNo || '未选择'}</strong>
                  </Col>
                  <Col>
                    <span>表面: </span>
                    <Select
                      value={surfaceKey}
                      onChange={handleSurfaceChange}
                      style={{ width: 120 }}
                    >
                      <Select.Option value="top">上表面</Select.Option>
                      <Select.Option value="bottom">下表面</Select.Option>
                      <Select.Option value="left">左侧面</Select.Option>
                      <Select.Option value="right">右侧面</Select.Option>
                    </Select>
                  </Col>
                </Row>
              </Card>
            </Col>

            {/* 3D数据展示 */}
            <Col span={24} style={{ height: 'calc(100% - 100px)' }}>
              <Card
                title="3D数据可视化"
                className="full-height-card"
                bodyStyle={{ padding: 0, height: '100%' }}
              >
                {!currentCoil ? (
                  <Empty description="请选择卷材" />
                ) : renderLoading ? (
                  <div className="loading-container">
                    <Spin indicator={<LoadingOutlined spin />} size="large" />
                  </div>
                ) : (
                  <Canvas3D data={renderData} />
                )}
              </Card>
            </Col>

            {/* 高度曲线图 */}
            {currentCoil && (
              <Col span={24}>
                <Card
                  title="高度曲线"
                  bodyStyle={{ height: 200 }}
                >
                  {heightLoading ? (
                    <div className="loading-container">
                      <Spin indicator={<LoadingOutlined spin />} />
                    </div>
                  ) : (
                    <HeightChart data={heightLineData?.data} />
                  )}
                </Card>
              </Col>
            )}
          </Row>
        </Col>
      </Row>
    </div>
  )
}

export default DataShowPage
