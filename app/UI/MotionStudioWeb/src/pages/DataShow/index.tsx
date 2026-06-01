import { useEffect, useState } from 'react'
import { Button, Empty, Select, Tag, message } from 'antd'
import { AppstoreOutlined, BorderOutlined, DotChartOutlined, LineChartOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'

import Canvas3D from '@/components/Canvas3D'
import HeightChart from '@/components/HeightChart'
import TileImageViewer from '@/components/TileImageViewer'
import { defectApi, heightDataApi, imageApi } from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import type { DefectData, SurfaceKey } from '@/types'
import './DataShow.css'

type ViewMode = 'area' | 'three'
const SURFACES: SurfaceKey[] = ['S', 'L']

function surfaceLabel(surface: SurfaceKey) {
  return surface === 'S' ? 'S 面' : 'L 面'
}

function DataShowPage() {
  const queryClient = useQueryClient()
  const { currentCoil, surfaceKey, setSurfaceKey } = useCoilStore()
  const [viewMode, setViewMode] = useState<ViewMode>('area')
  const [renderData, setRenderData] = useState<ArrayBuffer | null>(null)
  const [selectedDefect, setSelectedDefect] = useState<DefectData | null>(null)

  const { data: defectsSData, isFetching: defectsSLoading } = useQuery({
    queryKey: ['defects', currentCoil?.id, 'S'],
    queryFn: () => defectApi.getDefects(currentCoil?.id || 0, 'S'),
    enabled: !!currentCoil,
  })

  const { data: defectsLData, isFetching: defectsLLoading } = useQuery({
    queryKey: ['defects', currentCoil?.id, 'L'],
    queryFn: () => defectApi.getDefects(currentCoil?.id || 0, 'L'),
    enabled: !!currentCoil,
  })

  const { data: heightLineData, isFetching: heightLoading } = useQuery({
    queryKey: ['heightLine', currentCoil?.id, surfaceKey],
    queryFn: () => heightDataApi.getHeightLine(surfaceKey, currentCoil?.id || 0),
    enabled: !!currentCoil,
    retry: 1,
  })

  useEffect(() => {
    setRenderData(null)
    setSelectedDefect(null)
  }, [currentCoil?.id])

  useEffect(() => {
    if (!currentCoil || viewMode !== 'three') return
    queryClient
      .fetchQuery({
        queryKey: ['render3D', currentCoil.id, surfaceKey],
        queryFn: () => heightDataApi.getRenderData(surfaceKey, currentCoil.id),
      })
      .then(setRenderData)
      .catch(() => {
        setRenderData(null)
        message.warning(`${surfaceLabel(surfaceKey)} 3D数据暂不可用`)
      })
  }, [currentCoil, queryClient, surfaceKey, viewMode])

  const defectsBySurface: Record<SurfaceKey, DefectData[]> = {
    S: defectsSData?.data ?? [],
    L: defectsLData?.data ?? [],
  }
  const totalDefects = defectsBySurface.S.length + defectsBySurface.L.length
  const anyDefectLoading = defectsSLoading || defectsLLoading

  return (
    <div className="data-show-page">
      <div className="data-toolbar">
        <div className="toolbar-title">
          <DotChartOutlined />
          <span>数据展示</span>
          <Tag color="cyan">{currentCoil?.coilNo ?? '未选择卷材'}</Tag>
        </div>
        <div className="toolbar-controls">
          <span className="surface-select-label">当前曲线/3D</span>
          <Select
            size="small"
            value={surfaceKey}
            onChange={setSurfaceKey}
            options={[
              { value: 'S', label: 'S 面' },
              { value: 'L', label: 'L 面' },
            ]}
          />
          <Button
            size="small"
            icon={<AppstoreOutlined />}
            type={viewMode === 'area' ? 'primary' : 'default'}
            onClick={() => setViewMode('area')}
          >
            2D瓦片
          </Button>
          <Button
            size="small"
            icon={<BorderOutlined />}
            type={viewMode === 'three' ? 'primary' : 'default'}
            onClick={() => setViewMode('three')}
          >
            3D
          </Button>
        </div>
        <div className="load-state">
          <span className="ready">S图像</span>
          <span className="ready">L图像</span>
          <span className={!anyDefectLoading ? 'ready' : ''}>缺陷 {totalDefects}</span>
        </div>
      </div>

      <div className="data-content">
        <section className="main-view-panel">
          <div className="panel-title">
            {viewMode === 'area' ? 'S / L 端面区域瓦片查看' : `${surfaceLabel(surfaceKey)} 3D数据可视化`}
          </div>
          <div className="main-view-body">
            {!currentCoil ? (
              <Empty description="请选择卷材" />
            ) : viewMode === 'area' ? (
              <div className="surface-split-view">
                {SURFACES.map((surface) => (
                  <section key={surface} className="surface-view-panel">
                    <div className="surface-view-title">
                      <strong>{surfaceLabel(surface)}</strong>
                      <Tag color={surface === 'S' ? 'blue' : 'purple'}>{defectsBySurface[surface].length} 缺陷</Tag>
                    </div>
                    <div className="surface-view-body">
                      <TileImageViewer
                        imageUrl={imageApi.getArea(surface, currentCoil.id)}
                        previewUrl={imageApi.getPreview(surface, currentCoil.id, 'AREA')}
                        defects={defectsBySurface[surface]}
                        selectedDefectId={selectedDefect?.surface === surface ? selectedDefect.id : null}
                        onDefectSelect={setSelectedDefect}
                      />
                    </div>
                  </section>
                ))}
              </div>
            ) : (
              <Canvas3D data={renderData} />
            )}
          </div>
        </section>
      </div>

      <section className="chart-band">
        <div className="panel-title">
          <LineChartOutlined />
          {surfaceLabel(surfaceKey)} 高度曲线
          {selectedDefect ? <Tag color="orange">{selectedDefect.defectType}</Tag> : null}
        </div>
        <div className="chart-body">
          {currentCoil && !heightLoading ? (
            <HeightChart data={heightLineData} />
          ) : (
            <div className="chart-placeholder">等待3D数据加载</div>
          )}
        </div>
      </section>
    </div>
  )
}

export default DataShowPage
