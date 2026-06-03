import { useMemo, useState } from 'react'
import { Empty, Image, Select, Spin, Tag } from 'antd'
import { AimOutlined, BugOutlined, PictureOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'

import TileImageViewer from '@/components/TileImageViewer'
import { defectApi, imageApi } from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import type { DefectData } from '@/types'
import './DefectShow.css'

function DefectShowPage() {
  const { currentCoil, surfaceKey, setSurfaceKey } = useCoilStore()
  const [selectedDefectId, setSelectedDefectId] = useState<number | null>(null)

  const { data: defectsData, isLoading } = useQuery({
    queryKey: ['defects', currentCoil?.id, surfaceKey],
    queryFn: () => defectApi.getDefects(currentCoil?.id || 0, surfaceKey),
    enabled: !!currentCoil,
  })

  const defects = defectsData?.data ?? []
  const selectedDefect = useMemo(
    () => defects.find((defect) => defect.id === selectedDefectId) ?? defects[0] ?? null,
    [defects, selectedDefectId],
  )

  const areaUrl = currentCoil ? imageApi.getArea(surfaceKey, currentCoil.id) : ''
  const previewUrl = currentCoil ? imageApi.getPreview(surfaceKey, currentCoil.id, 'AREA') : ''

  const defectImageUrl =
    currentCoil && selectedDefect
      ? imageApi.getDefectImage(
          surfaceKey,
          currentCoil.id,
          'preview',
          selectedDefect.position.x,
          selectedDefect.position.y,
          selectedDefect.size.width,
          selectedDefect.size.height,
        )
      : ''

  const handleDefectSelect = (defect: DefectData | null) => {
    setSelectedDefectId(defect?.id ?? null)
  }

  return (
    <div className="defect-show-page">
      <div className="defect-toolbar">
        <div className="toolbar-title">
          <BugOutlined />
          <span>缺陷检测</span>
          <Tag color="red">{defects.length} 项</Tag>
        </div>
        <Select
          size="small"
          value={surfaceKey}
          onChange={setSurfaceKey}
          options={[
            { value: 'S', label: 'S 面' },
            { value: 'L', label: 'L 面' },
          ]}
        />
      </div>

      <div className="defect-content">
        <section className="defect-list-panel">
          <div className="panel-title">
            <AimOutlined />
            缺陷列表
          </div>
          <div className="defect-list-container">
            {!currentCoil ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择卷材" />
            ) : isLoading ? (
              <div className="loading-container">
                <Spin />
              </div>
            ) : defects.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无缺陷数据" />
            ) : (
              defects.map((defect) => (
                <button
                  type="button"
                  key={defect.id}
                  className={`defect-item ${selectedDefect?.id === defect.id ? 'selected' : ''}`}
                  onClick={() => setSelectedDefectId(defect.id)}
                >
                  <span className="defect-type">{defect.defectType}</span>
                  <strong>{(defect.confidence * 100).toFixed(1)}%</strong>
                  <small>
                    位置 ({defect.position.x}, {defect.position.y}) · 尺寸 {defect.size.width} x {defect.size.height}
                  </small>
                </button>
              ))
            )}
          </div>
        </section>

        <section className="surface-panel">
          <div className="panel-title">
            <PictureOutlined />
            表面全景
          </div>
          <div className="surface-body">
            {!currentCoil ? (
              <Empty description="请选择卷材" />
            ) : (
              <TileImageViewer
                imageUrl={areaUrl}
                previewUrl={previewUrl}
                defects={defects}
                selectedDefectId={selectedDefect?.id ?? null}
                onDefectSelect={handleDefectSelect}
              />
            )}
          </div>
        </section>

        <section className="defect-detail-panel">
          <div className="panel-title">缺陷详情</div>
          {selectedDefect ? (
            <div className="defect-detail">
              <div className="detail-grid">
                <span>类型</span>
                <strong>{selectedDefect.defectType}</strong>
                <span>位置</span>
                <strong>
                  {selectedDefect.position.x}, {selectedDefect.position.y}
                </strong>
                <span>尺寸</span>
                <strong>
                  {selectedDefect.size.width} x {selectedDefect.size.height}
                </strong>
                <span>置信度</span>
                <strong>{(selectedDefect.confidence * 100).toFixed(1)}%</strong>
              </div>
              <div className="defect-crop">
                {defectImageUrl ? <Image src={defectImageUrl} preview={false} /> : null}
              </div>
            </div>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="请选择缺陷" />
          )}
        </section>
      </div>
    </div>
  )
}

export default DefectShowPage
