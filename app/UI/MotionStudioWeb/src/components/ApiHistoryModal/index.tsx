import { useSyncExternalStore } from 'react'
import { Modal } from 'antd'

import {
  getApiRequestHistory,
  openApiHistoryExternalUrl,
  subscribeApiRequestHistory,
  type ApiRequestHistoryEntry,
} from '@/utils/apiHistory'
import './ApiHistoryModal.css'

interface ApiHistoryModalProps {
  open: boolean
  onClose: () => void
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp)
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function ApiHistoryRow({ entry }: { entry: ApiRequestHistoryEntry }) {
  return (
    <button className="api-history-row" type="button" onClick={() => void openApiHistoryExternalUrl(entry.url)}>
      <span className="api-history-time">{formatTime(entry.timestamp)}</span>
      <span className="api-history-method">{entry.method}</span>
      <span className="api-history-url api-history-url-link" title={entry.url} data-qml-rich-url>
        {entry.url}
      </span>
    </button>
  )
}

export default function ApiHistoryModal({ open, onClose }: ApiHistoryModalProps) {
  const history = useSyncExternalStore(subscribeApiRequestHistory, getApiRequestHistory, getApiRequestHistory)

  return (
    <Modal
      className="api-history-modal api-history-window"
      title={null}
      width={500}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnHidden
    >
      <div className="api-history-pop" data-qml-api-list-pop>
        <h3 className="api-history-title" data-qml-api-list-title>
          API 调用记录
        </h3>
        <div className="api-history-list">
          {history.length > 0 ? (
            history.map((entry) => <ApiHistoryRow key={entry.id} entry={entry} />)
          ) : (
            <div className="api-history-empty">暂无 API 调用记录</div>
          )}
        </div>
      </div>
    </Modal>
  )
}
