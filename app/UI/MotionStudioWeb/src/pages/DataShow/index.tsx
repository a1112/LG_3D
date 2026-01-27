import { useState, useEffect } from 'react'
import { Card, Row, Col, List, Select, Spin, Empty, message } from 'antd'
import { LoadingOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Canvas3D from '@/components/Canvas3D'
import HeightChart from '@/components/HeightChart'
import CoilList from '@/components/CoilList'
import { useCoilStore } from '@/stores/coilStore'
import { coilApi, heightDataApi, defectApi } from '@/services/api'
import { useDataLoader, LOAD_DELAYS } from '@/utils/dataLoader'
import './DataShow.css'

function DataShowPage() {
  const { currentCoil, surfaceKey, setCurrentCoil, setSurfaceKey } = useCoilStore()
  const queryClient = useQueryClient()
  const [renderData, setRenderData] = useState<ArrayBuffer | null>(null)
  const [loadState, setLoadState] = useState({
    imageLoaded: false,
    defectLoaded: false,
    threeDLoaded: false,
  })

  // 使用数据加载器
  const { loadImage, loadDefect, load3d, cleanup } = useDataLoader({
    coilId: currentCoil?.id || 0,
    surfaceKey: surfaceKey,
    onImageLoaded: () => {
      console.log('[DataShow] Image loaded')
      setLoadState(prev => ({ ...prev, imageLoaded: true }))

      // 延迟加载缺陷数据
      setTimeout(() => {
        loadDefect(async () => {
          const defects = await queryClient.fetchQuery({
            queryKey: ['defects', currentCoil?.id, surfaceKey],
            queryFn: () =>
              defectApi.getDefects(currentCoil?.id || 0, surfaceKey),
          })
          return defects
        })
      }, LOAD_DELAYS.imageToDefect)
    },
    onDefectLoaded: () => {
      console.log('[DataShow] Defect data loaded')
      setLoadState(prev => ({ ...prev, defectLoaded: true }))

      // 延迟加载 3D 数据
      setTimeout(() => {
        load3d(async () => {
          const data = await queryClient.fetchQuery({
            queryKey: ['heightLine', currentCoil?.id, surfaceKey],
            queryFn: () =>
              heightDataApi.getHeightLine(surfaceKey, currentCoil?.id || 0),
          })
          return data
        })
      }, LOAD_DELAYS.defectTo3d)
    },
    on3dLoaded: () => {
      console.log('[DataShow] 3D data loaded')
      setLoadState(prev => ({ ...prev, threeDLoaded: true }))
    },
    onError: (error) => {
      console.error('[DataShow] Load error:', error)
      message.error('数据加载失败: ' + error.message)
    },
  })

  // 获取卷材列表
  const { data: coilListData, isLoading: listLoading } = useQuery({
    queryKey: ['coilList'],
    queryFn: () => coilApi.getCoilList(50),
  })

  // 3D 渲染数据由加载器管理（最高优先级）
  const { data: render3DData } = useQuery({
    queryKey: ['render3D', currentCoil?.id, surfaceKey],
    queryFn: () =>
      heightDataApi.getRenderData(surfaceKey, currentCoil?.id || 0),
    enabled: false, // 禁用自动加载，由加载器控制
  })

  // 缺陷数据由加载器管理（中等优先级）
  const { data: defectsData } = useQuery({
    queryKey: ['defects', currentCoil?.id, surfaceKey],
    queryFn: () =>
      defectApi.getDefects(currentCoil?.id || 0, surfaceKey),
    enabled: false, // 禁用自动加载，由加载器控制
  })

  // 高度线数据由加载器管理（最低优先级）
  const { data: heightLineData } = useQuery({
    queryKey: ['heightLine', currentCoil?.id, surfaceKey],
    queryFn: () =>
      heightDataApi.getHeightLine(surfaceKey, currentCoil?.id || 0),
    enabled: false, // 禁用自动加载，由加载器控制
  })

  // 触发图像加载（最高优先级）
  useEffect(() => {
    if (currentCoil && surfaceKey) {
      console.log('[DataShow] Triggering image load (priority 1)')
      loadImage(async () => {
        const data = await queryClient.fetchQuery({
          queryKey: ['render3D', currentCoil.id, surfaceKey],
          queryFn: () =>
            heightDataApi.getRenderData(surfaceKey, currentCoil.id),
        })
        return data
      })
    }

    return () => {
      cleanup()
    }
  }, [currentCoil?.id, surfaceKey])

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

        {/* 右侧数据展示 */}
        <Col span={18}>
          <Row gutter={[16, 16]} style={{ height: '100%' }}>
            {/* 控制栏 + 加载状态 */}
            <Col span={24}>
              <Card size="small">
                <Row align="middle" gutter={16} justify="space-between">
                  <Col>
                    <Row align="middle" gutter={8}>
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
                  </Col>
                  <Col>
                    {/* 加载状态指示器 */}
                    {currentCoil && (
                      <Row gutter={12} align="middle">
                        <Col>
                          <span style={{ fontSize: 12, color: loadState.imageLoaded ? '#52c41a' : '#d9d9d9' }}>
                            {loadState.imageLoaded ? '✓' : '○'} 图像
                          </span>
                        </Col>
                        <Col>
                          <span style={{ fontSize: 12, color: loadState.defectLoaded ? '#52c41a' : '#d9d9d9' }}>
                            {loadState.defectLoaded ? '✓' : '○'} 缺陷
                          </span>
                        </Col>
                        <Col>
                          <span style={{ fontSize: 12, color: loadState.threeDLoaded ? '#52c41a' : '#d9d9d9' }}>
                            {loadState.threeDLoaded ? '✓' : '○'} 3D数据
                          </span>
                        </Col>
                      </Row>
                    )}
                  </Col>
                </Row>
              </Card>
            </Col>

            {/* 3D数据展示 */}
            <Col span={24} style={{ height: 'calc(100% - 100px)' }}>
              <Card
                title="3D数据可视化"
                className="full-height-card"
                styles={{ body: { padding: 0, height: '100%' } }}
              >
                {!currentCoil ? (
                  <Empty description="请选择卷材" />
                ) : !loadState.imageLoaded ? (
                  <div className="loading-container">
                    <Spin indicator={<LoadingOutlined spin />} size="large" />
                    <div style={{ marginTop: 16 }}>正在加载图像...</div>
                  </div>
                ) : (
                  <Canvas3D data={renderData} />
                )}
              </Card>
            </Col>

            {/* 高度曲线图 */}
            {currentCoil && loadState.defectLoaded && (
              <Col span={24}>
                <Card
                  title="高度曲线"
                  styles={{ body: { height: 200 } }}
                >
                  {!loadState.threeDLoaded ? (
                    <div className="loading-container">
                      <Spin indicator={<LoadingOutlined spin />} />
                      <div style={{ marginTop: 16 }}>正在加载 3D 数据...</div>
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
