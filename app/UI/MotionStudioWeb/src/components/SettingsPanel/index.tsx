import { Badge, Descriptions, Drawer, Switch, Tabs, message } from 'antd'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { plcApi, settingsApi } from '@/services/api'
import './SettingsPanel.css'

interface SettingsPanelProps {
  open: boolean
  onClose: () => void
}

function readStatusField(data: unknown, keys: string[]) {
  if (!data || typeof data !== 'object') return '--'
  const record = data as Record<string, unknown>
  for (const key of keys) {
    const value = record[key]
    if (value !== undefined && value !== null) {
      return String(value)
    }
  }
  return '--'
}

function readBooleanField(data: unknown, keys: string[]) {
  if (!data || typeof data !== 'object') return false
  const record = data as Record<string, unknown>
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') return value.toLowerCase() === 'true'
  }
  return false
}

export default function SettingsPanel({ open, onClose }: SettingsPanelProps) {
  const queryClient = useQueryClient()

  const { data: testModeStatus, isFetching: testModeLoading } = useQuery({
    queryKey: ['settings', 'testModeStatus'],
    queryFn: settingsApi.getTestModeStatus,
    enabled: open,
    retry: 1,
  })

  const { data: hardwareInfo, isFetching: hardwareLoading } = useQuery({
    queryKey: ['hardware'],
    queryFn: plcApi.getHardware,
    enabled: open,
    retry: 1,
  })

  const testModeMutation = useMutation({
    mutationFn: settingsApi.setTestMode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'testModeStatus'] })
      message.success('测试模式已更新')
    },
    onError: () => {
      message.error('测试模式更新失败')
    },
  })

  const testModeEnabled = readBooleanField(testModeStatus, ['test_mode', 'testMode', 'enabled', 'developer_mode'])

  return (
    <Drawer
      className="settings-panel"
      title="系统设置"
      placement="right"
      width={520}
      open={open}
      onClose={onClose}
      destroyOnClose={false}
    >
      <Tabs
        defaultActiveKey="info"
        items={[
          {
            key: 'info',
            label: '信息',
            children: (
              <div className="settings-section">
                <div className="settings-status-row">
                  <Badge status={testModeEnabled ? 'error' : 'success'} />
                  <span>{testModeEnabled ? '测试模式' : '生产模式'}</span>
                </div>
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="数据源目录">
                    {readStatusField(testModeStatus, ['data_source', 'dataSource', 'source_dir', 'sourceDir'])}
                  </Descriptions.Item>
                  <Descriptions.Item label="存储目录">
                    {readStatusField(testModeStatus, ['storage_dir', 'storageDir', 'save_dir', 'saveDir'])}
                  </Descriptions.Item>
                  <Descriptions.Item label="主机名">
                    {readStatusField(testModeStatus, ['hostname', 'host_name', 'hostName'])}
                  </Descriptions.Item>
                  <Descriptions.Item label="数据库状态">
                    {readStatusField(testModeStatus, ['database', 'database_status', 'databaseStatus'])}
                  </Descriptions.Item>
                  <Descriptions.Item label="API状态">
                    {testModeLoading ? '刷新中' : '已连接或待后端响应'}
                  </Descriptions.Item>
                  <Descriptions.Item label="硬件信息">
                    {hardwareLoading ? '刷新中' : readStatusField(hardwareInfo, ['status', 'message', 'hardware'])}
                  </Descriptions.Item>
                </Descriptions>
              </div>
            ),
          },
          {
            key: 'general',
            label: '常规',
            children: (
              <div className="settings-section">
                <label className="settings-row">
                  <span>自动刷新卷材列表</span>
                  <Switch defaultChecked />
                </label>
                <label className="settings-row">
                  <span>显示服务状态</span>
                  <Switch defaultChecked />
                </label>
              </div>
            ),
          },
          {
            key: 'render',
            label: '3D渲染',
            children: (
              <div className="settings-section">
                <label className="settings-row">
                  <span>显示网格</span>
                  <Switch defaultChecked />
                </label>
                <label className="settings-row">
                  <span>瓦片边框</span>
                  <Switch defaultChecked />
                </label>
                <label className="settings-row">
                  <span>渐进加载</span>
                  <Switch defaultChecked />
                </label>
              </div>
            ),
          },
          {
            key: 'alarm',
            label: '报警',
            children: (
              <div className="settings-section">
                <label className="settings-row">
                  <span>全局报警提示</span>
                  <Switch defaultChecked />
                </label>
                <label className="settings-row">
                  <span>缺陷高亮</span>
                  <Switch defaultChecked />
                </label>
              </div>
            ),
          },
          {
            key: 'other',
            label: '其他',
            children: (
              <div className="settings-section">
                <label className="settings-row">
                  <span>测试模式</span>
                  <Switch
                    checked={testModeEnabled}
                    loading={testModeLoading || testModeMutation.isPending}
                    onChange={(checked) => testModeMutation.mutate(checked)}
                  />
                </label>
                <p className="settings-note">
                  测试模式状态来自现有 FastAPI 设置接口；前端只读取和提交现有字段，不修改接口形状。
                </p>
              </div>
            ),
          },
        ]}
      />
    </Drawer>
  )
}
