import { describe, expect, it } from 'vitest'

import {
  buildQmlInfoSettingRows,
  buildQmlWindowTitle,
  getConfiguredTestMode,
  getRuntimeTestMode,
  getTestModeLabel,
} from './testMode'

describe('test mode helpers', () => {
  it('keeps runtime developer mode separate from the persisted QML test-mode switch', () => {
    const status = {
      developer_mode: true,
      config_file_value: false,
      data_source: 'TestData',
    }

    expect(getRuntimeTestMode(status)).toBe(true)
    expect(getConfiguredTestMode(status)).toBe(false)
    expect(getTestModeLabel(status)).toBe('测试模式（环境）')
  })

  it('uses the persisted config value as the switch state when available', () => {
    const status = {
      developer_mode: false,
      config_file_value: 'true',
    }

    expect(getRuntimeTestMode(status)).toBe(true)
    expect(getConfiguredTestMode(status)).toBe(true)
    expect(getTestModeLabel(status)).toBe('测试模式')
  })

  it('falls back to legacy test_mode and enabled fields for older services', () => {
    expect(getRuntimeTestMode({ test_mode: true })).toBe(true)
    expect(getConfiguredTestMode({ enabled: 'false' })).toBe(false)
  })

  it('matches QML window title test-mode indicator', () => {
    expect(buildQmlWindowTitle({ developer_mode: false, config_file_value: false })).toBe('涟钢3D端面检测系统')
    expect(buildQmlWindowTitle({ developer_mode: false, config_file_value: true })).toBe('涟钢3D端面检测系统 - [测试模式]')
    expect(buildQmlWindowTitle({ developer_mode: true, config_file_value: false })).toBe('涟钢3D端面检测系统 - [测试模式]')
  })

  it('builds QML InfoSetting rows from runtime test-mode and API settings', () => {
    const rows = buildQmlInfoSettingRows(
      {
        developer_mode: true,
        config_file_value: false,
        config_file_path: 'D:\\CONFIG_3D\\test_mode_config.json',
      },
      {
        apiServerIp: '10.2.3.4',
        apiServerPort: 5011,
        useSharedFolder: true,
        sharedFolderBaseName: 'Save_',
      },
    )

    expect(rows.system).toEqual([
      { label: '数据源目录：', value: 'TestData/125143' },
      { label: '存储目录：', value: 'TestData (测试数据)' },
      { label: '运行模式：', value: '测试模式' },
      { label: '主机名：', value: '10.2.3.4' },
      { label: '数据库：', value: 'Offline' },
    ])
    expect(rows.config).toEqual([
      { label: '配置目录：', value: 'D:\\CONFIG_3D' },
      { label: 'API端口：', value: '5011' },
    ])
  })

  it('matches QML shared-folder and local-database InfoSetting fallbacks', () => {
    expect(
      buildQmlInfoSettingRows(
        { developer_mode: false, config_file_value: false },
        {
          apiServerIp: '192.168.8.9',
          apiServerPort: 6005,
          useSharedFolder: true,
          sharedFolderBaseName: 'Save_',
        },
      ).system,
    ).toEqual([
      { label: '数据源目录：', value: '\\\\192.168.8.9/Save_' },
      { label: '存储目录：', value: '共享文件夹' },
      { label: '运行模式：', value: '生产模式' },
      { label: '主机名：', value: '192.168.8.9' },
      { label: '数据库：', value: 'Offline' },
    ])

    expect(
      buildQmlInfoSettingRows(
        {},
        {
          apiServerIp: '127.0.0.1',
          apiServerPort: 5010,
          useSharedFolder: false,
          sharedFolderBaseName: 'Save_',
        },
      ).system.slice(0, 2),
    ).toEqual([
      { label: '数据源目录：', value: '数据库' },
      { label: '存储目录：', value: '本地数据库' },
    ])
  })
})
