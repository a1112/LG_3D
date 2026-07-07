import { useEffect, useState } from 'react'
import { Button, Checkbox, Empty, Input, Modal, Select, Spin, message } from 'antd'
import { useQuery } from '@tanstack/react-query'

import { defectConfigApi } from '@/services/api'
import {
  buildDefectClassConfigPayload,
  buildDefectClassConfigRows,
  getDefectClassColorPickerValue,
  type DefectClassConfigRow,
  updateDefectClassConfigRow,
} from '@/utils/defectClassConfig'
import './DefectClassModal.css'

interface DefectClassModalProps {
  open: boolean
  onClose: () => void
}

const LEVEL_OPTIONS = ['0', '1', '2', '3', '4', '5'].map((value) => ({ value: Number(value), label: value }))

export default function DefectClassModal({ open, onClose }: DefectClassModalProps) {
  const [rows, setRows] = useState<DefectClassConfigRow[]>([])
  const [saving, setSaving] = useState(false)
  const { data, isFetching, refetch } = useQuery({
    queryKey: ['defectConfig', 'defectDict'],
    queryFn: defectConfigApi.getDefectDict,
    enabled: open,
    staleTime: 30_000,
    retry: 1,
  })

  useEffect(() => {
    if (!open) return
    setRows(buildDefectClassConfigRows(data))
  }, [data, open])

  const updateRow = (index: number, patch: Partial<DefectClassConfigRow>) => {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? updateDefectClassConfigRow(row, patch) : row)))
  }

  const saveConfig = async () => {
    setSaving(true)
    try {
      await defectConfigApi.setDefectDict(buildDefectClassConfigPayload(rows))
      message.success('缺陷配置已保存')
      refetch()
    } catch {
      message.error('缺陷配置保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      className="defect-class-window"
      title={null}
      open={open}
      width={500}
      footer={null}
      onCancel={onClose}
      destroyOnHidden
    >
      <div className="defect-class-modal" data-qml-defect-class-pop>
        <h3 className="defect-class-title" data-qml-defect-class-title>
          缺陷列表
        </h3>
        {isFetching ? (
          <div className="defect-class-loading">
            <Spin size="small" />
          </div>
        ) : rows.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无缺陷类别" />
        ) : (
          <div className="defect-class-list">
            {rows.map((row, index) => (
              <div className="defect-class-row" key={row.name}>
                <strong>{row.name}</strong>
                <Select
                  size="small"
                  value={row.level}
                  options={LEVEL_OPTIONS}
                  onChange={(value) => updateRow(index, { level: value })}
                />
                <Checkbox checked={!row.show} onChange={(event) => updateRow(index, { show: !event.target.checked })}>
                  屏蔽
                </Checkbox>
                <div className="defect-class-color">
                  <Input
                    size="small"
                    value={row.color}
                    onChange={(event) => updateRow(index, { color: event.target.value })}
                  />
                  <input
                    aria-label={`${row.name} 颜色`}
                    type="color"
                    value={getDefectClassColorPickerValue(row.color)}
                    onChange={(event) => updateRow(index, { color: event.target.value })}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="defect-class-actions">
          <Button type="primary" loading={saving} disabled={rows.length === 0} onClick={saveConfig}>
            保存
          </Button>
          <Button>添加</Button>
        </div>
      </div>
    </Modal>
  )
}
