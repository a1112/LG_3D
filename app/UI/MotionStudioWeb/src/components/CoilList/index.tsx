import { List, Tag, Empty } from 'antd'
import type { CoilData } from '@/types'
import './CoilList.css'

interface CoilListProps {
  coils: CoilData[]
  selectedCoil: CoilData | null
  onSelect: (coil: CoilData) => void
}

function CoilList({ coils, selectedCoil, onSelect }: CoilListProps) {
  const getStatusColor = (status: number) => {
    switch (status) {
      case 1:
        return 'processing'
      case 2:
        return 'success'
      case 3:
        return 'error'
      default:
        return 'default'
    }
  }

  const getStatusText = (status: number) => {
    switch (status) {
      case 1:
        return '处理中'
      case 2:
        return '已完成'
      case 3:
        return '错误'
      default:
        return '未知'
    }
  }

  return (
    <div className="coil-list-container">
      {coils.length === 0 ? (
        <Empty description="暂无数据" />
      ) : (
        <List
          dataSource={coils}
          renderItem={(coil) => (
            <List.Item
              key={coil.id}
              onClick={() => onSelect(coil)}
              className={`coil-list-item ${
                selectedCoil?.id === coil.id ? 'selected' : ''
              }`}
            >
              <List.Item.Meta
                title={
                  <div className="coil-item-title">
                    <span className="coil-no">{coil.coilNo}</span>
                    <Tag color={getStatusColor(coil.status)}>
                      {getStatusText(coil.status)}
                    </Tag>
                  </div>
                }
                description={
                  <div className="coil-item-description">
                    <div>时间: {coil.dateTime}</div>
                    <div>表面: {coil.surfaceKey}</div>
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </div>
  )
}

export default CoilList
