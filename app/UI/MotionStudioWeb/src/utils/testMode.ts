const TRUE_STRINGS = new Set(['1', 'true', 'yes', 'on'])
const FALSE_STRINGS = new Set(['0', 'false', 'no', 'off'])
const QML_WINDOW_TITLE = '涟钢3D端面检测系统'

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

export function readBooleanValue(value: unknown): boolean | null {
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase()
    if (TRUE_STRINGS.has(normalized)) return true
    if (FALSE_STRINGS.has(normalized)) return false
  }
  return null
}

function readFirstBoolean(record: Record<string, unknown>, keys: string[]): boolean | null {
  for (const key of keys) {
    const value = readBooleanValue(record[key])
    if (value !== null) return value
  }
  return null
}

function readFirstString(record: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = record[key]
    if (value === undefined || value === null) continue
    const text = String(value).trim()
    if (text) return text
  }
  return null
}

function dirname(path: string): string {
  const normalized = path.trim()
  const slashIndex = Math.max(normalized.lastIndexOf('\\'), normalized.lastIndexOf('/'))
  if (slashIndex <= 0) return normalized
  return normalized.slice(0, slashIndex)
}

export function getConfiguredTestMode(status: unknown): boolean {
  const record = asRecord(status)
  return readFirstBoolean(record, ['config_file_value', 'test_mode', 'testMode', 'enabled']) ?? false
}

export function getRuntimeTestMode(status: unknown): boolean {
  const record = asRecord(status)
  const developerMode = readFirstBoolean(record, ['developer_mode', 'developerMode'])
  return Boolean(developerMode || getConfiguredTestMode(status))
}

export function getTestModeLabel(status: unknown): string {
  if (!getRuntimeTestMode(status)) return '生产模式'
  return getConfiguredTestMode(status) ? '测试模式' : '测试模式（环境）'
}

export function buildQmlWindowTitle(status: unknown): string {
  return getRuntimeTestMode(status) ? `${QML_WINDOW_TITLE} - [测试模式]` : QML_WINDOW_TITLE
}

export interface QmlInfoSettingOptions {
  apiServerIp: string
  apiServerPort: number
  useSharedFolder: boolean
  sharedFolderBaseName: string
}

export interface QmlInfoSettingRow {
  label: string
  value: string
}

export interface QmlInfoSettingRows {
  system: QmlInfoSettingRow[]
  config: QmlInfoSettingRow[]
}

export function buildQmlInfoSettingRows(status: unknown, options: QmlInfoSettingOptions): QmlInfoSettingRows {
  const record = asRecord(status)
  const runtimeTestMode = getRuntimeTestMode(status)
  const host = readFirstString(record, ['hostname', 'host_name', 'hostName']) ?? options.apiServerIp
  const sharedRoot = `\\\\${host}/${options.sharedFolderBaseName || 'Save_'}`
  const dataSource =
    runtimeTestMode
      ? 'TestData/125143'
      : readFirstString(record, ['data_source', 'dataSource', 'source_dir', 'sourceDir']) ??
        (options.useSharedFolder ? sharedRoot : '数据库')
  const storage =
    runtimeTestMode
      ? 'TestData (测试数据)'
      : readFirstString(record, ['storage_dir', 'storageDir', 'save_dir', 'saveDir']) ??
        (options.useSharedFolder ? '共享文件夹' : '本地数据库')
  const configDir =
    readFirstString(record, ['config_dir', 'configDir']) ??
    dirname(readFirstString(record, ['config_file_path', 'configFilePath']) ?? 'D:\\CONFIG_3D\\test_mode_config.json')

  return {
    system: [
      { label: '数据源目录：', value: dataSource },
      { label: '存储目录：', value: storage },
      { label: '运行模式：', value: runtimeTestMode ? '测试模式' : '生产模式' },
      { label: '主机名：', value: host },
      { label: '数据库：', value: readFirstString(record, ['database', 'database_status', 'databaseStatus']) ?? 'Offline' },
    ],
    config: [
      { label: '配置目录：', value: configDir },
      { label: 'API端口：', value: String(options.apiServerPort) },
    ],
  }
}
