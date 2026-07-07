import { describe, expect, it } from 'vitest'

import { buildSystemInfoViewModel } from './systemInfo'

describe('buildSystemInfoViewModel', () => {
  it('builds QML HelpPop-compatible system information fields', () => {
    const info = {
      surfaceS: {
        saveFolder: 'F:\\Save_S',
        folderList: [{ source: 'G:\\Cap_S_D' }, { source: 'G:\\Cap_S_U' }],
      },
      surfaceL: {
        saveFolder: 'F:\\Save_L',
        folderList: [{ source: 'G:\\Cap_L_D' }],
      },
    }
    const runtime = {
      python_version: '3.11.9',
      cache_mode: 'redis',
      cpu_model: 'Intel Core',
      gpus: ['RTX 4090', 'RTX 3080'],
    }
    const database = { url: 'mysql+pymysql://user:***@127.0.0.1/db' }

    expect(buildSystemInfoViewModel({ info, runtime, database, version: '0.1.1' })).toEqual({
      originalImageFolderS: 'G:\\Cap_S_D\nG:\\Cap_S_U',
      originalImageFolderL: 'G:\\Cap_L_D',
      saveImageFolderS: 'F:\\Save_S',
      saveImageFolderL: 'F:\\Save_L',
      pythonVersion: '3.11.9',
      serverVersion: '0.1.1',
      cacheMode: 'redis',
      cpuModel: 'Intel Core',
      gpuModels: 'RTX 4090\nRTX 3080',
      databaseUrl: 'mysql+pymysql://user:***@127.0.0.1/db',
    })
  })

  it('uses QML-compatible unknown labels when data is missing', () => {
    expect(buildSystemInfoViewModel({})).toEqual({
      originalImageFolderS: '未知',
      originalImageFolderL: '未知',
      saveImageFolderS: '未知',
      saveImageFolderL: '未知',
      pythonVersion: '未知',
      serverVersion: '未知',
      cacheMode: '未知',
      cpuModel: '未知',
      gpuModels: '未知',
      databaseUrl: '未知',
    })
  })

  it('renders database url arrays like QML label string conversion', () => {
    const database = { url: ['mysql+pymysql', 'root', '127.0.0.1', 3306, 'Coil'] }

    expect(buildSystemInfoViewModel({ database }).databaseUrl).toBe('mysql+pymysql,root,127.0.0.1,3306,Coil')
  })
})
