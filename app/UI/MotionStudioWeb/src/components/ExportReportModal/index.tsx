import { useEffect, useState } from 'react'
import dayjs, { type Dayjs } from 'dayjs'
import { Button, Checkbox, DatePicker, Input, Modal, Progress, message } from 'antd'
import { FileExcelOutlined, FolderOpenOutlined } from '@ant-design/icons'

import { exportApi } from '@/services/api'
import { useCoilStore } from '@/stores/coilStore'
import { copyTextToClipboard } from '@/utils/clipboard'
import {
  buildDefaultExportXlsxConfig,
  buildExportInitialDateRange,
  buildQmlExportDefaultFileName,
  buildQuickExportFileName,
  openSavedExportPath,
  resolveQuickExportUrl,
  saveExportPayload,
  type ExportSaveResult,
  type ExportOptionState,
  type QuickExportKind,
} from '@/utils/exportReport'
import {
  getNativeDefaultDesktopDirectory,
  saveNativeFile,
  selectNativeSavePath,
  writeNativeFile,
} from '@/utils/nativeDialogs'
import './ExportReportModal.css'

interface ExportReportModalProps {
  open: boolean
  onClose: () => void
}

const DEFAULT_OPTIONS: Required<ExportOptionState> = {
  detection3dInfo: true,
  defectInfo: true,
  defectShowInfo: true,
  defectUnShowInfo: false,
  exportPlcData: false,
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename || buildQmlExportDefaultFileName()
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function showSaveResult(result: ExportSaveResult) {
  if (result.status === 'saved') {
    message.success(`报表已保存到 ${result.path}`)
  } else if (result.status === 'cancelled') {
    message.info('已取消报表导出')
  } else {
    message.success('报表导出完成')
  }
}

function hasExplicitExportPath(value: string): boolean {
  return value.includes('\\') || value.includes('/')
}

export default function ExportReportModal({ open, onClose }: ExportReportModalProps) {
  const coilList = useCoilStore((state) => state.coilList)
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>(() => {
    const range = buildExportInitialDateRange([])
    return [dayjs(range.startDate), dayjs(range.endDate)]
  })
  const [outputName, setOutputName] = useState(buildQmlExportDefaultFileName)
  const [exportDefaultDirectory, setExportDefaultDirectory] = useState('')
  const [options, setOptions] = useState<Required<ExportOptionState>>(DEFAULT_OPTIONS)
  const [downloading, setDownloading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [lastExportPath, setLastExportPath] = useState('')
  const [exportError, setExportError] = useState('')

  useEffect(() => {
    if (!open) return
    const range = buildExportInitialDateRange(coilList)
    setDateRange([dayjs(range.startDate), dayjs(range.endDate)])
    setProgress(0)
    setLastExportPath('')
    setExportError('')
  }, [coilList, open])

  useEffect(() => {
    if (!open) return
    void getNativeDefaultDesktopDirectory().then((directory) => {
      if (directory) {
        setExportDefaultDirectory(directory)
      }
    })
  }, [open])

  const updateOption = (key: keyof Required<ExportOptionState>, checked: boolean) => {
    setOptions((current) => ({ ...current, [key]: checked }))
  }

  const updateOutputName = (value: string) => {
    setOutputName(value)
    setLastExportPath('')
    setExportError('')
    setProgress(0)
  }

  const saveWorkbook = async (defaultName: string, contents: Uint8Array) => {
    if (hasExplicitExportPath(defaultName)) {
      const directPathResult = await writeNativeFile(defaultName, contents)
      if (directPathResult.status === 'saved') {
        return directPathResult
      }
    }

    return saveNativeFile(defaultName, contents, {
      defaultDirectory: exportDefaultDirectory || undefined,
    })
  }

  const selectOutputFile = async () => {
    const selected = await selectNativeSavePath(outputName || buildQmlExportDefaultFileName(), {
      defaultDirectory: exportDefaultDirectory || undefined,
    })
    if (selected.status === 'selected') {
      updateOutputName(selected.path)
    } else if (selected.status === 'unavailable') {
      message.info('当前环境不支持原生文件选择')
    }
  }

  const copyExportError = async () => {
    if (!exportError) return
    const copied = await copyTextToClipboard(exportError)
    if (copied) {
      message.success('错误信息已复制')
    } else {
      message.error('复制失败')
    }
  }

  const handleSaveResult = (result: ExportSaveResult) => {
    showSaveResult(result)
    if (result.status === 'saved') {
      setLastExportPath(result.path)
      setExportError('')
      void openSavedExportPath(result.path, 'file')
    }
  }

  const openQuickExport = async (kind: QuickExportKind) => {
    setDownloading(true)
    setProgress(0.2)
    setLastExportPath('')
    setExportError('')
    try {
      const response = await fetch(resolveQuickExportUrl(kind, exportApi))
      if (!response.ok) throw new Error(`export failed: ${response.status}`)
      const payload = await response.arrayBuffer()
      setProgress(1)
      const result = await saveExportPayload(payload, buildQuickExportFileName(kind, outputName), {
        saveFile: saveWorkbook,
        downloadBlob,
      })
      handleSaveResult(result)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : '报表导出失败')
      message.error('报表导出失败')
    } finally {
      setDownloading(false)
    }
  }

  const runConfigExport = async () => {
    setDownloading(true)
    setProgress(0.2)
    setLastExportPath('')
    setExportError('')
    try {
      const config = buildDefaultExportXlsxConfig(
        {
          startDate: dateRange[0].toDate(),
          endDate: dateRange[1].toDate(),
        },
        options,
      )
      const payload = await exportApi.exportXlsx(config)
      setProgress(1)
      const result = await saveExportPayload(payload, outputName, {
        saveFile: saveWorkbook,
        downloadBlob,
      })
      handleSaveResult(result)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : '报表导出失败')
      message.error('报表导出失败')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Modal
      className="export-report-window"
      title={null}
      open={open}
      width={650}
      footer={null}
      onCancel={onClose}
      destroyOnHidden
    >
      <div className="export-report-modal" data-qml-export-view>
        <h3 className="export-report-title" data-qml-export-title>
          报表导出
        </h3>
        <label className="export-report-row">
          <span>起始导出日期:</span>
          <DatePicker
            showTime={{ format: 'HH:mm' }}
            format="YYYY-MM-DD HH:mm"
            value={dateRange[0]}
            onChange={(value) => value && setDateRange((range) => [value, range[1]])}
          />
        </label>
        <label className="export-report-row">
          <span>结束导出日期:</span>
          <DatePicker
            showTime={{ format: 'HH:mm' }}
            format="YYYY-MM-DD HH:mm"
            value={dateRange[1]}
            onChange={(value) => value && setDateRange((range) => [range[0], value])}
          />
        </label>
        <label className="export-report-row export-report-file-row">
          <span>导出文件</span>
          <Input value={outputName} onChange={(event) => updateOutputName(event.target.value)} />
          <Button disabled={downloading} onClick={() => void selectOutputFile()}>
            选择...
          </Button>
        </label>

        <div className="export-report-options">
          <Checkbox
            checked={options.detection3dInfo}
            onChange={(event) => updateOption('detection3dInfo', event.target.checked)}
          >
            3D检测信息
          </Checkbox>
          <Checkbox
            checked={options.defectInfo}
            onChange={(event) => updateOption('defectInfo', event.target.checked)}
          >
            缺陷信息
          </Checkbox>
          <Checkbox
            checked={options.defectShowInfo}
            onChange={(event) => updateOption('defectShowInfo', event.target.checked)}
          >
            缺陷检出
          </Checkbox>
          <Checkbox
            checked={options.exportPlcData}
            onChange={(event) => updateOption('exportPlcData', event.target.checked)}
          >
            plc数据
          </Checkbox>
          <Checkbox
            checked={options.defectUnShowInfo}
            onChange={(event) => updateOption('defectUnShowInfo', event.target.checked)}
          >
            缺陷屏蔽
          </Checkbox>
        </div>

        <div className="export-report-quick">
          <span>快速导出:</span>
          <Button disabled={downloading} onClick={() => openQuickExport('today')}>
            今天
          </Button>
          <Button disabled={downloading} onClick={() => openQuickExport('1h')}>
            1小时
          </Button>
          <Button disabled={downloading} onClick={() => openQuickExport('24h')}>
            24小时
          </Button>
        </div>

        <div className="export-report-actions">
          <Button type="primary" icon={<FileExcelOutlined />} loading={downloading} onClick={runConfigExport}>
            {downloading ? '导出中...' : '导出'}
          </Button>
          <Button onClick={onClose}>
            关闭
          </Button>
        </div>
        {downloading && <Progress percent={Math.round(progress * 100)} status="active" />}
        {lastExportPath && !downloading && (
          <div className="export-report-finished">
            <span>导出进度：</span>
            <Progress percent={100} size="small" />
            <Button size="small" icon={<FileExcelOutlined />} onClick={() => void openSavedExportPath(lastExportPath, 'file')}>
              打开
            </Button>
            <Button
              size="small"
              icon={<FolderOpenOutlined />}
              onClick={() => void openSavedExportPath(lastExportPath, 'folder')}
            >
              打开位置...
            </Button>
          </div>
        )}
        {exportError && !downloading && (
          <div className="export-report-error" role="alert">
            <strong>数据导出错误:</strong>
            <pre>{exportError}</pre>
            <Button disabled={!exportError} onClick={() => void copyExportError()}>
              复制
            </Button>
          </div>
        )}
      </div>
    </Modal>
  )
}
