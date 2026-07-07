import { useEffect, useMemo, useState } from 'react'
import { Button, Empty, Input, Modal, Select, Tag } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { coilApi } from '@/services/api'
import type { CoilData } from '@/types'
import {
  buildListValueChangeInitialRange,
  buildListValueChangePoints,
  chooseListValueChangeKey,
} from '@/utils/listValueChange'
import './ListValueChangeModal.css'

interface ListValueChangeModalProps {
  open: boolean
  coilList: CoilData[]
  onClose: () => void
}

export default function ListValueChangeModal({ open, coilList, onClose }: ListValueChangeModalProps) {
  const [selectedKey, setSelectedKey] = useState<string>()
  const [startId, setStartId] = useState('')
  const [endId, setEndId] = useState('')
  const [chartVersion, setChartVersion] = useState(0)

  const { data: keys = [], isFetching, refetch } = useQuery({
    queryKey: ['coilList', 'valueChangeKeys'],
    queryFn: coilApi.getCoilListValueChangeKeys,
    enabled: open,
    staleTime: 60_000,
  })

  useEffect(() => {
    if (!open) return
    const range = buildListValueChangeInitialRange(coilList)
    setStartId(range.startId)
    setEndId(range.endId)
  }, [coilList, open])

  useEffect(() => {
    if (keys.length === 0) {
      setSelectedKey(undefined)
      return
    }

    setSelectedKey((current) => (current && keys.includes(current) ? current : chooseListValueChangeKey(keys, coilList)))
  }, [coilList, keys])

  const keyOptions = useMemo(() => keys.map((key) => ({ value: key, label: key })), [keys])
  const chartPoints = useMemo(
    () =>
      buildListValueChangePoints(coilList, selectedKey, {
        startId,
        endId,
      }),
    [chartVersion, coilList, endId, selectedKey, startId],
  )
  const chartDomain = useMemo(() => {
    if (chartPoints.length === 0) return undefined
    const values = chartPoints.map((point) => point.value)
    const min = Math.min(...values)
    const max = Math.max(...values)
    if (min === max) return [min - 1, max + 1] as [number, number]
    const padding = (max - min) * 0.12
    return [min - padding, max + padding] as [number, number]
  }, [chartPoints])

  const refreshChart = () => {
    setChartVersion((version) => version + 1)
    refetch()
  }

  return (
    <Modal
      className="list-value-change-window"
      title={null}
      open={open}
      width={850}
      footer={null}
      onCancel={onClose}
      destroyOnHidden
    >
      <div className="list-value-change-modal" data-qml-list-value-change-view>
        <h3 className="list-value-change-title" data-qml-list-value-change-title>
          列表数值变化曲线
        </h3>
        <div className="list-value-change-controls">
          <label>
            <span>数值类型：</span>
            <Select
              size="small"
              value={selectedKey}
              options={keyOptions}
              loading={isFetching}
              placeholder="请选择数值类型"
              onChange={setSelectedKey}
            />
          </label>
          <label>
            <span>起始值 ：</span>
            <Input size="small" value={startId} onChange={(event) => setStartId(event.target.value)} />
          </label>
          <label>
            <span>结束值 ：</span>
            <Input size="small" value={endId} onChange={(event) => setEndId(event.target.value)} />
          </label>
          <Button size="small" loading={isFetching} onClick={refreshChart}>
            刷新
          </Button>
        </div>

        <div className="list-value-change-body" data-qml-list-value-change-chart data-point-count={chartPoints.length}>
          {chartPoints.length > 0 ? (
            <>
              <div className="list-value-change-chart-head">
                <Tag color="blue">{selectedKey}</Tag>
                <span>
                  {chartPoints[0].coilId} - {chartPoints[chartPoints.length - 1].coilId}
                </span>
                <strong>{chartPoints.length} 点</strong>
              </div>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartPoints} margin={{ top: 12, right: 24, bottom: 8, left: 4 }}>
                  <CartesianGrid stroke="#d8e1e8" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="label"
                    minTickGap={18}
                    tick={{ fill: '#5a6b7a', fontSize: 11 }}
                    tickLine={{ stroke: '#9aa8b4' }}
                  />
                  <YAxis
                    domain={chartDomain}
                    tick={{ fill: '#5a6b7a', fontSize: 11 }}
                    tickLine={{ stroke: '#9aa8b4' }}
                    width={58}
                  />
                  <Tooltip
                    formatter={(value) => [value, selectedKey ?? '数值']}
                    labelFormatter={(label) => `流水号 ${label}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#2196f3"
                    strokeWidth={2}
                    dot={{ r: 2 }}
                    activeDot={{ r: 4 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可绘制数据" />
          )}
        </div>
      </div>
    </Modal>
  )
}
