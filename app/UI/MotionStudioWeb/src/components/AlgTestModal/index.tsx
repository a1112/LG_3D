import { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Checkbox, Empty, Input, Modal, Progress, Radio, Select, Slider, Spin, message } from 'antd'
import { PlayCircleOutlined, ReloadOutlined, StopOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'

import { algTestApi, serviceBaseUrls } from '@/services/api'
import {
  buildAlgTestPayload,
  clampAlgThreshold,
  formatAlgEta,
  formatAlgProgressSocketErrorLog,
  formatAlgTestFailureLog,
  normalizeAlgModels,
  normalizeAlgProgressMessage,
  resolveAlgProgressWsUrl,
  type AlgProgressSummary,
  type AlgTestModel,
} from '@/utils/algTest'
import { selectNativeDirectory } from '@/utils/nativeDialogs'
import './AlgTestModal.css'

interface AlgTestModalProps {
  open: boolean
  onClose: () => void
}

function stamp(): string {
  const now = new Date()
  return [now.getHours(), now.getMinutes(), now.getSeconds()].map((value) => String(value).padStart(2, '0')).join(':')
}

function appendBoundedLog(current: string[], text: string): string[] {
  const next = [...current, `${stamp()}  ${text}`]
  return next.length > 200 ? next.slice(next.length - 200) : next
}

export default function AlgTestModal({ open, onClose }: AlgTestModalProps) {
  const [selectedModel, setSelectedModel] = useState<AlgTestModel | null>(null)
  const [targetFolder, setTargetFolder] = useState('')
  const [outputFolder, setOutputFolder] = useState('')
  const [threshold, setThreshold] = useState(0.4)
  const [mode, setMode] = useState<'copy' | 'move'>('copy')
  const [classifySave, setClassifySave] = useState(true)
  const [saveLabel, setSaveLabel] = useState(false)
  const [prioritize, setPrioritize] = useState(false)
  const [running, setRunning] = useState(false)
  const [taskId, setTaskId] = useState('')
  const [done, setDone] = useState(0)
  const [total, setTotal] = useState(0)
  const [speed, setSpeed] = useState(0)
  const [eta, setEta] = useState(0)
  const [statusText, setStatusText] = useState('')
  const [errors, setErrors] = useState(0)
  const [summary, setSummary] = useState<AlgProgressSummary | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const socketRef = useRef<WebSocket | null>(null)
  const runningRef = useRef(false)

  const modelsQuery = useQuery({
    queryKey: ['algTest', 'models'],
    queryFn: algTestApi.getModels,
    enabled: open,
    retry: 1,
    staleTime: 30_000,
  })

  const models = useMemo(() => normalizeAlgModels(modelsQuery.data), [modelsQuery.data])
  const selectedIsClassifier = selectedModel?.type === 'classifier'

  useEffect(() => {
    if (!open || selectedModel || models.length === 0) return
    setSelectedModel(models[0])
    setStatusText(`可用模型: ${models.length}`)
  }, [models, open, selectedModel])

  useEffect(() => {
    if (selectedIsClassifier && saveLabel) {
      setSaveLabel(false)
    }
  }, [saveLabel, selectedIsClassifier])

  useEffect(() => {
    runningRef.current = running
  }, [running])

  useEffect(() => {
    if (!open) {
      runningRef.current = false
      socketRef.current?.close()
      socketRef.current = null
      setRunning(false)
      setErrors(0)
      setSummary(null)
    }
  }, [open])

  const addLog = (text: string) => setLogs((current) => appendBoundedLog(current, text))

  const refreshModels = () => {
    setStatusText('正在获取模型列表...')
    modelsQuery.refetch().then((result) => {
      const refreshed = normalizeAlgModels(result.data)
      if (refreshed.length > 0) {
        setSelectedModel(refreshed[0])
        setStatusText(`可用模型: ${refreshed.length}`)
      } else {
        setSelectedModel(null)
        setStatusText('未找到模型')
      }
    })
  }

  const chooseFolder = async (target: 'target' | 'output') => {
    try {
      const selected = await selectNativeDirectory()
      if (!selected) {
        setStatusText('可手动输入文件夹路径')
        return
      }
      if (target === 'target') {
        setTargetFolder(selected)
      } else {
        setOutputFolder(selected)
      }
    } catch {
      setStatusText('目录选择失败，可手动输入路径')
    }
  }

  const openProgressSocket = () => {
    socketRef.current?.close()
    const socket = new WebSocket(resolveAlgProgressWsUrl(serviceBaseUrls.apiWsBaseUrl, algTestApi.progressWsPath()))
    socketRef.current = socket
    socket.onmessage = (event) => {
      const progress = normalizeAlgProgressMessage(String(event.data))
      if (progress.taskId && !taskId) setTaskId(progress.taskId)
      if (progress.speed !== undefined) setSpeed(progress.speed)
      if (progress.done !== undefined) setDone(progress.done)
      if (progress.total !== undefined) setTotal(progress.total)
      if (progress.eta !== undefined) setEta(progress.eta)
      if (progress.errors !== undefined) setErrors(progress.errors)
      if (progress.message) addLog(progress.message)
      if (progress.status) setStatusText(progress.status)
      const completeSummary = progress.summary
        ? {
            normal: progress.summary.normal ?? 0,
            abnormal: progress.summary.abnormal ?? 0,
            skipped: progress.summary.skipped ?? 0,
            empty: progress.summary.empty ?? 0,
          }
        : null
      if (completeSummary) setSummary(completeSummary)
      if (progress.finished) {
        runningRef.current = false
        setRunning(false)
        if (progress.summary) {
          if (completeSummary) {
            addLog('任务完成')
            addLog(
              `summary: normal=${completeSummary.normal} abnormal=${completeSummary.abnormal} skipped=${completeSummary.skipped} empty=${completeSummary.empty}`,
            )
          }
        }
        socket.close()
      }
    }
    socket.onerror = (event) => {
      addLog(formatAlgProgressSocketErrorLog(event))
      setStatusText(formatAlgProgressSocketErrorLog(event))
    }
    socket.onclose = () => {
      if (socketRef.current === socket) {
        if (runningRef.current) {
          addLog('进度连接已关闭')
        }
        socketRef.current = null
      }
    }
  }

  const startTest = async () => {
    if (!selectedModel) {
      setStatusText('请选择模型')
      return
    }
    if (!targetFolder.trim()) {
      setStatusText('请选择目标文件夹')
      return
    }
    if (!outputFolder.trim()) {
      setStatusText('请选择输出文件夹')
      return
    }

    runningRef.current = true
    setRunning(true)
    setDone(0)
    setTotal(0)
    setSpeed(0)
    setEta(0)
    setTaskId('')
    setErrors(0)
    setSummary(null)
    setLogs([])
    setStatusText('正在启动算法测试...')
    addLog(`开始执行: ${selectedModel.displayName}`)
    openProgressSocket()

    try {
      const response = await algTestApi.start(
        buildAlgTestPayload({
          model: selectedModel,
          targetFolder,
          outputFolder,
          threshold,
          mode,
          classifySave,
          saveLabel,
          prioritize,
        }),
      )
      const maybeTaskId = (response as Record<string, unknown> | null | undefined)?.task_id
      if (maybeTaskId) setTaskId(String(maybeTaskId))
      setStatusText('任务已启动')
    } catch (error) {
      runningRef.current = false
      setRunning(false)
      socketRef.current?.close()
      setStatusText('启动失败')
      addLog(formatAlgTestFailureLog('启动失败', error))
      message.error('算法测试启动失败')
    }
  }

  const stopTest = async () => {
    runningRef.current = false
    setRunning(false)
    setStatusText('已请求停止')
    socketRef.current?.close()
    try {
      await algTestApi.stop(taskId)
      addLog('服务端已确认停止')
    } catch (error) {
      addLog(formatAlgTestFailureLog('停止失败', error))
      message.error('停止算法测试失败')
    }
  }

  const progressPercent = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <Modal
      className="alg-test-modal-window"
      title={null}
      open={open}
      width={900}
      footer={null}
      onCancel={onClose}
      destroyOnHidden
    >
      <div className="alg-test-modal" data-qml-alg-test-dialog>
        <h3 className="alg-test-title" data-qml-alg-test-title>
          算法测试
        </h3>
        <div className="alg-test-grid">
          <label>模型</label>
          <Select
            value={selectedModel?.name}
            placeholder="请选择模型"
            loading={modelsQuery.isFetching}
            options={models.map((model) => ({ value: model.name, label: model.displayName }))}
            onChange={(value) => setSelectedModel(models.find((model) => model.name === value) ?? null)}
          />
          <div className="alg-test-inline">
            <Button icon={<ReloadOutlined />} disabled={modelsQuery.isFetching} onClick={refreshModels}>
              刷新
            </Button>
            {modelsQuery.isFetching && <Spin size="small" />}
          </div>

          <label>目标文件夹</label>
          <Input
            value={targetFolder}
            placeholder="递归扫描的图像根目录"
            onChange={(event) => setTargetFolder(event.target.value)}
          />
          <Button onClick={() => chooseFolder('target')}>选择</Button>

          <label>输出文件夹</label>
          <Input
            value={outputFolder}
            placeholder="保存检测结果的目录"
            onChange={(event) => setOutputFolder(event.target.value)}
          />
          <Button onClick={() => chooseFolder('output')}>选择</Button>

          <label>低置信度阈值</label>
          <div className="alg-test-threshold">
            <Slider
              min={0}
              max={100}
              step={1}
              value={threshold * 100}
              onChange={(value) => setThreshold(clampAlgThreshold(value / 100))}
            />
            <Input
              value={threshold.toFixed(2)}
              onChange={(event) => setThreshold(clampAlgThreshold(Number(event.target.value)))}
            />
          </div>
          <span />

          <label>模式</label>
          <Radio.Group value={mode} onChange={(event) => setMode(event.target.value)}>
            <Radio value="copy">复制</Radio>
            <Radio value="move">移动</Radio>
          </Radio.Group>
          <span />
        </div>

        <div className="alg-test-options">
          <span>选项</span>
          <Checkbox checked={classifySave} onChange={(event) => setClassifySave(event.target.checked)}>
            分类保存
          </Checkbox>
          <Checkbox
            checked={!selectedIsClassifier && saveLabel}
            disabled={selectedIsClassifier}
            onChange={(event) => setSaveLabel(!selectedIsClassifier && event.target.checked)}
          >
            保存标注文件
          </Checkbox>
          <Checkbox
            checked={prioritize}
            onChange={(event) => setPrioritize(event.target.checked)}
          >
            prioritize
          </Checkbox>
        </div>

        <div className="alg-test-actions">
          <Button type="primary" icon={<PlayCircleOutlined />} disabled={running} onClick={startTest}>
            {running ? '执行中...' : '开始测试'}
          </Button>
          <Button icon={<StopOutlined />} disabled={!running} onClick={stopTest}>
            停止
          </Button>
          <Button onClick={onClose}>关闭</Button>
          <span className="alg-test-status">{statusText}</span>
        </div>

        <Progress percent={progressPercent} status={running ? 'active' : 'normal'} />
        <div className="alg-test-metrics">
          <span>{done} / {total || '未知'} 张</span>
          <span>速度 {speed.toFixed(2)} 张/秒</span>
          <span>预计 {formatAlgEta(eta)}</span>
          <span>错误 {errors}</span>
          <span>
            正常 {summary?.normal ?? 0} | 异常 {summary?.abnormal ?? 0} | 跳过 {summary?.skipped ?? 0} | 空图 {summary?.empty ?? 0}
          </span>
        </div>

        <div className="alg-test-log">
          {logs.length > 0 ? logs.map((line) => <div key={line}>{line}</div>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无日志" />}
        </div>
      </div>
    </Modal>
  )
}
