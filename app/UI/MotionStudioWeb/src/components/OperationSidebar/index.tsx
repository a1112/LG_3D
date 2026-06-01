import { useEffect, useMemo, useState } from 'react'
import { Badge, Button, Empty, Input, Select, Spin, Tag } from 'antd'
import { FilterOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'

import { coilApi } from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import type { CoilData } from '@/types'
import './OperationSidebar.css'

function statusColor(status: number) {
  if (status === 1) return 'processing'
  if (status === 2) return 'success'
  if (status === 3) return 'error'
  return 'default'
}

function statusText(status: number) {
  if (status === 1) return '处理中'
  if (status === 2) return '已完成'
  if (status === 3) return '错误'
  return '未知'
}

export default function OperationSidebar() {
  const { currentCoil, coilList, setCoilList, setCurrentCoil, surfaceKey, setSurfaceKey } = useCoilStore()
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState<number | 'all'>('all')

  const { data, isFetching, refetch } = useQuery({
    queryKey: ['coilList'],
    queryFn: () => coilApi.getCoilList(80),
    refetchInterval: 10000,
  })

  useEffect(() => {
    const nextList = data?.data ?? []
    setCoilList(nextList)
    if (!currentCoil && nextList.length > 0) {
      setCurrentCoil(nextList[0])
    }
  }, [currentCoil, data, setCoilList, setCurrentCoil])

  const filteredCoils = useMemo(() => {
    return coilList.filter((coil) => {
      const matchesKeyword =
        keyword.trim().length === 0 ||
        coil.coilNo?.toLowerCase().includes(keyword.trim().toLowerCase()) ||
        String(coil.id).includes(keyword.trim())
      const matchesStatus = statusFilter === 'all' || coil.status === statusFilter
      return matchesKeyword && matchesStatus
    })
  }, [coilList, keyword, statusFilter])

  return (
    <aside className="operation-sidebar">
      <section className="sidebar-section current-coil">
        <div className="section-title">当前卷材</div>
        <div className="coil-primary">{currentCoil?.coilNo ?? '未选择'}</div>
        <div className="coil-meta-grid">
          <span>ID</span>
          <strong>{currentCoil?.id ?? '--'}</strong>
          <span>表面</span>
          <Select
            size="small"
            value={surfaceKey}
            onChange={setSurfaceKey}
            options={[
              { value: 'S', label: 'S 面' },
              { value: 'L', label: 'L 面' },
            ]}
          />
          <span>状态</span>
          <Tag color={statusColor(currentCoil?.status ?? 0)}>{statusText(currentCoil?.status ?? 0)}</Tag>
        </div>
      </section>

      <section className="sidebar-section grade-panel">
        <div className="section-title">判级</div>
        <div className="grade-row">
          <Badge status={currentCoil?.status === 3 ? 'error' : 'success'} />
          <span>{currentCoil?.status === 3 ? '异常卷' : '正常监控'}</span>
        </div>
        <div className="grade-metrics">
          <div>
            <span>平整度</span>
            <strong>{currentCoil?.grade ?? '--'}</strong>
          </div>
          <div>
            <span>S缺陷</span>
            <strong>{currentCoil?.defectCountS ?? '--'}</strong>
          </div>
          <div>
            <span>L缺陷</span>
            <strong>{currentCoil?.defectCountL ?? '--'}</strong>
          </div>
        </div>
      </section>

      <section className="sidebar-section alarm-panel">
        <div className="section-title">报警</div>
        <div className="alarm-list">
          <div className="alarm-item ok">PLC 通信正常</div>
          <div className="alarm-item ok">Redis 缓存在线</div>
          <div className="alarm-item warn">图像服务待确认</div>
        </div>
      </section>

      <section className="sidebar-section search-panel">
        <div className="section-title">查询 / 过滤</div>
        <Input
          allowClear
          size="small"
          prefix={<SearchOutlined />}
          placeholder="卷号 / ID"
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <div className="filter-row">
          <Select
            size="small"
            value={statusFilter}
            onChange={setStatusFilter}
            options={[
              { value: 'all', label: '全部状态' },
              { value: 1, label: '处理中' },
              { value: 2, label: '已完成' },
              { value: 3, label: '错误' },
            ]}
          />
          <Button size="small" icon={<FilterOutlined />} />
          <Button size="small" icon={<ReloadOutlined />} loading={isFetching} onClick={() => refetch()} />
        </div>
      </section>

      <section className="sidebar-section coil-list-section">
        <div className="section-title">卷材列表</div>
        {isFetching && coilList.length === 0 ? (
          <div className="sidebar-loading">
            <Spin size="small" />
          </div>
        ) : filteredCoils.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
        ) : (
          <div className="sidebar-coil-list">
            {filteredCoils.map((coil: CoilData) => (
              <button
                type="button"
                key={coil.id}
                className={`sidebar-coil-item ${currentCoil?.id === coil.id ? 'selected' : ''}`}
                onClick={() => setCurrentCoil(coil)}
              >
                <span className="coil-no">{coil.coilNo}</span>
                <Tag color={statusColor(coil.status)}>{statusText(coil.status)}</Tag>
                <span className="coil-time">{coil.dateTime}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </aside>
  )
}
