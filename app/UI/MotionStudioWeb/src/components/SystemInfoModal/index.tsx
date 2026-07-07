import { Button, Modal, Spin } from 'antd'
import { useQuery } from '@tanstack/react-query'

import { systemApi } from '@/services/api'
import { buildSystemInfoViewModel } from '@/utils/systemInfo'
import './SystemInfoModal.css'

interface SystemInfoModalProps {
  open: boolean
  onClose: () => void
}

function Value({ children }: { children: string }) {
  return <span className="system-info-value">{children}</span>
}

export default function SystemInfoModal({ open, onClose }: SystemInfoModalProps) {
  const infoQuery = useQuery({ queryKey: ['systemInfo', 'info'], queryFn: systemApi.getInfo, enabled: open, retry: 1 })
  const runtimeQuery = useQuery({
    queryKey: ['systemInfo', 'runtime'],
    queryFn: systemApi.getRuntimeInfo,
    enabled: open,
    retry: 1,
  })
  const databaseQuery = useQuery({
    queryKey: ['systemInfo', 'database'],
    queryFn: systemApi.getDatabaseInfo,
    enabled: open,
    retry: 1,
  })
  const versionQuery = useQuery({
    queryKey: ['systemInfo', 'version'],
    queryFn: systemApi.getVersion,
    enabled: open,
    retry: 1,
  })

  const loading = infoQuery.isFetching || runtimeQuery.isFetching || databaseQuery.isFetching || versionQuery.isFetching
  const viewModel = buildSystemInfoViewModel({
    info: infoQuery.data,
    runtime: runtimeQuery.data,
    database: databaseQuery.data,
    version: versionQuery.data,
  })

  return (
    <Modal
      className="system-info-modal system-info-window"
      title={null}
      width={800}
      open={open}
      onCancel={onClose}
      footer={null}
      destroyOnHidden
    >
      <Spin spinning={loading}>
        <div className="system-info-body" data-qml-help-pop>
          <h3 className="system-info-title" data-qml-help-title>
            系统信息
          </h3>
          <div className="system-info-separator" />
          <fieldset className="system-info-group">
            <legend>图像保存路径</legend>
            <div className="system-info-path-list">
              <div className="system-info-row">
                <span className="system-info-label">原始图像 S 端:</span>
                <Value>{viewModel.originalImageFolderS}</Value>
              </div>
              <div className="system-info-row">
                <span className="system-info-label">原始图像 L 端:</span>
                <Value>{viewModel.originalImageFolderL}</Value>
              </div>
              <div className="system-info-row">
                <span className="system-info-label">保存图像 S 端:</span>
                <Value>{viewModel.saveImageFolderS}</Value>
              </div>
              <div className="system-info-row">
                <span className="system-info-label">保存图像 L 端:</span>
                <Value>{viewModel.saveImageFolderL}</Value>
              </div>
            </div>
          </fieldset>

          <fieldset className="system-info-group">
            <legend>运行环境</legend>
            <div className="system-info-grid system-info-runtime-grid">
              <span className="system-info-label">Python 版本:</span>
              <Value>{viewModel.pythonVersion}</Value>
              <span className="system-info-label">服务版本:</span>
              <Value>{viewModel.serverVersion}</Value>
              <span className="system-info-label">缓存方式:</span>
              <Value>{viewModel.cacheMode}</Value>
              <span className="system-info-label">CPU 型号:</span>
              <Value>{viewModel.cpuModel}</Value>
              <span className="system-info-label">GPU 型号:</span>
              <Value>{viewModel.gpuModels}</Value>
              <span className="system-info-label">数据库:</span>
              <Value>{viewModel.databaseUrl}</Value>
            </div>
          </fieldset>
          <div className="system-info-actions">
            <Button onClick={onClose}>关闭</Button>
          </div>
        </div>
      </Spin>
    </Modal>
  )
}
