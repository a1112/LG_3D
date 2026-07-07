import { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Descriptions, Modal, Progress, message } from 'antd'
import { DeleteOutlined, ReloadOutlined } from '@ant-design/icons'

import { globalImageCache } from '@/utils/imageCache'
import { buildImageCacheRows } from '@/utils/imageCacheView'
import './ImageCacheModal.css'

interface ImageCacheModalProps {
  open: boolean
  onClose: () => void
}

function readImageCacheStats() {
  return globalImageCache.getStats()
}

export default function ImageCacheModal({ open, onClose }: ImageCacheModalProps) {
  const [stats, setStats] = useState(readImageCacheStats)
  const rows = useMemo(() => buildImageCacheRows(stats), [stats])
  const usagePercent = Math.min(100, Math.max(0, Number(stats.usagePercent) || 0))

  const refreshStats = useCallback(() => {
    setStats(readImageCacheStats())
  }, [])

  const clearCache = useCallback(() => {
    globalImageCache.clear()
    setStats(readImageCacheStats())
    message.success('图像缓存已清空')
  }, [])

  useEffect(() => {
    if (open) {
      refreshStats()
    }
  }, [open, refreshStats])

  return (
    <Modal
      className="image-cache-modal"
      title="图像缓存"
      width={520}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnHidden
    >
      <div className="image-cache-summary">
        <Progress
          percent={usagePercent}
          size="small"
          status={usagePercent >= 90 ? 'exception' : 'normal'}
          strokeColor={usagePercent >= 90 ? '#ff4d4f' : '#7ad7ec'}
          trailColor="#263b4c"
        />
      </div>

      <Descriptions column={1} bordered size="small">
        {rows.map((row) => (
          <Descriptions.Item key={row.label} label={row.label}>
            <span className="image-cache-value">{row.value}</span>
          </Descriptions.Item>
        ))}
      </Descriptions>

      <div className="image-cache-actions">
        <Button size="small" icon={<ReloadOutlined />} onClick={refreshStats}>
          刷新
        </Button>
        <Button size="small" danger icon={<DeleteOutlined />} onClick={clearCache} disabled={stats.size === 0}>
          清空缓存
        </Button>
      </div>
    </Modal>
  )
}
