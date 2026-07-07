import { describe, expect, it } from 'vitest'

import { buildQmlAreaClipSettings } from '@/utils/area2d'
import * as uiSettings from './uiSettingsStore'
import uiSettingsStoreSource from './uiSettingsStore.ts?raw'
import {
  QML_DISPLAY_STYLE_OPTIONS,
  QML_THEME_OPTIONS,
  normalizeQmlDisplayStyleName,
  normalizeQmlPointValueShowType,
  normalizeQmlThemeName,
  normalizeAreaTileCount,
  normalizeApiServerIp,
  normalizeApiServerPort,
  normalizeAutoKeepTimeMax,
  normalizeDataHeaderHeight,
  normalizeHeadDateShowModel,
  normalizeTowerWarningOpacity,
  normalizeTowerWarningThresholdDown,
  normalizeTowerWarningThresholdUp,
  useUiSettingsStore,
} from './uiSettingsStore'

describe('QML settings page tabs', () => {
  it('matches the QML SettingPageView tab order including camera adjustment', () => {
    const tabs = (
      uiSettings as unknown as {
        QML_SETTINGS_TAB_OPTIONS?: Array<{ key: string; label: string }>
      }
    ).QML_SETTINGS_TAB_OPTIONS

    expect(tabs?.map((item) => item.label)).toEqual([
      '常规',
      '风格',
      '报警',
      '3D 渲染',
      '相机调整',
      '信息',
      '其他',
    ])
    expect(tabs?.map((item) => item.key)).toEqual(['general', 'style', 'alarm', 'render', 'camera', 'info', 'other'])
  })

  it('marks QML BaseSetting placeholder tabs so React does not expose fake controls', () => {
    const placeholderKeys = (
      uiSettings as unknown as {
        QML_PLACEHOLDER_SETTINGS_TAB_KEYS?: string[]
      }
    ).QML_PLACEHOLDER_SETTINGS_TAB_KEYS

    expect(placeholderKeys).toEqual(['alarm', 'render'])
  })
})

describe('QML style settings normalization', () => {
  it('exposes the same theme and display-style keys as QML CoreStyle', () => {
    expect(QML_THEME_OPTIONS.map((item) => item.key)).toEqual(['dark', 'light', 'blue'])
    expect(QML_THEME_OPTIONS.map((item) => item.name)).toEqual(['黑色主题', '白色主题', '蓝色主题'])
    expect(QML_DISPLAY_STYLE_OPTIONS.map((item) => item.key)).toEqual(['standard', 'compact', 'comfortable'])
    expect(QML_DISPLAY_STYLE_OPTIONS.map((item) => item.name)).toEqual(['标准', '紧凑', '大屏'])
  })

  it('falls back to QML CoreStyle defaults for invalid persisted values', () => {
    expect(normalizeQmlThemeName('light')).toBe('light')
    expect(normalizeQmlThemeName('unknown')).toBe('dark')
    expect(normalizeQmlDisplayStyleName('comfortable')).toBe('comfortable')
    expect(normalizeQmlDisplayStyleName('invalid')).toBe('standard')
  })

  it('derives the QML TopIcon dark-mode toggle from the current theme darkness', () => {
    const getNextQmlTopIconThemeName = (
      uiSettings as unknown as {
        getNextQmlTopIconThemeName?: (qmlThemeName: string) => string
      }
    ).getNextQmlTopIconThemeName

    expect(getNextQmlTopIconThemeName).toBeTypeOf('function')
    expect(getNextQmlTopIconThemeName?.('dark')).toBe('light')
    expect(getNextQmlTopIconThemeName?.('blue')).toBe('light')
    expect(getNextQmlTopIconThemeName?.('light')).toBe('dark')
    expect(getNextQmlTopIconThemeName?.('missing')).toBe('light')
  })
})

describe('normalizeAreaTileCount', () => {
  it('keeps AREA tile counts within the QML 1..10 SpinBox range', () => {
    expect(normalizeAreaTileCount(0)).toBe(1)
    expect(normalizeAreaTileCount(3)).toBe(3)
    expect(normalizeAreaTileCount(10.8)).toBe(10)
    expect(normalizeAreaTileCount(99)).toBe(10)
  })
})

describe('tower warning settings normalization', () => {
  it('keeps tower-warning controls within QML SpinBox and Slider ranges', () => {
    expect(normalizeTowerWarningThresholdUp(-5)).toBe(0)
    expect(normalizeTowerWarningThresholdUp(42.8)).toBe(42)
    expect(normalizeTowerWarningThresholdUp(120)).toBe(100)

    expect(normalizeTowerWarningThresholdDown(-130)).toBe(-100)
    expect(normalizeTowerWarningThresholdDown(-42.8)).toBe(-42)
    expect(normalizeTowerWarningThresholdDown(12)).toBe(0)

    expect(normalizeTowerWarningOpacity(-1)).toBe(0)
    expect(normalizeTowerWarningOpacity(50.9)).toBe(50)
    expect(normalizeTowerWarningOpacity(150)).toBe(100)
  })
})

describe('api service settings normalization', () => {
  it('keeps API connection settings on the non-conflicting Rust API defaults', () => {
    expect(normalizeApiServerIp(' 192.168.99.100 ')).toBe('192.168.99.100')
    expect(normalizeApiServerIp('bad host; rm -rf')).toBe('127.0.0.1')
    expect(normalizeApiServerPort(Number.NaN)).toBe(5011)
    expect(normalizeApiServerPort(0)).toBe(1)
    expect(normalizeApiServerPort(5010.8)).toBe(5010)
    expect(normalizeApiServerPort(70000)).toBe(65535)
  })

  it('migrates legacy persisted API defaults away from the conflicting port', () => {
    expect(uiSettingsStoreSource).toContain('version: 1')
    expect(uiSettingsStoreSource).toContain('apiServerPort === 5010 ? 5011')
  })
})

describe('keep-latest settings normalization', () => {
  it('keeps QML autoKeepTimeMax as a positive persisted tick count', () => {
    expect(normalizeAutoKeepTimeMax(Number.NaN)).toBe(180)
    expect(normalizeAutoKeepTimeMax(0)).toBe(1)
    expect(normalizeAutoKeepTimeMax(12.9)).toBe(12)
    expect(normalizeAutoKeepTimeMax(5000)).toBe(1440)
  })
})

describe('DataShow settings normalization', () => {
  it('keeps QML dataHeaderHeight as a bounded persisted panel height', () => {
    expect(normalizeDataHeaderHeight(Number.NaN)).toBe(320)
    expect(normalizeDataHeaderHeight(80)).toBe(120)
    expect(normalizeDataHeaderHeight(320.9)).toBe(320)
    expect(normalizeDataHeaderHeight(900)).toBe(720)
  })

  it('keeps QML headDateShowModel within the DataHeader StackLayout modes', () => {
    expect(normalizeHeadDateShowModel(Number.NaN)).toBe(0)
    expect(normalizeHeadDateShowModel(-1)).toBe(0)
    expect(normalizeHeadDateShowModel(1.9)).toBe(1)
    expect(normalizeHeadDateShowModel(9)).toBe(2)
  })

  it('keeps QML SurfaceData point value display modes on the supported enum keys', () => {
    expect(normalizeQmlPointValueShowType('mm-relative')).toBe('mm-relative')
    expect(normalizeQmlPointValueShowType('mm-absolute')).toBe('mm-absolute')
    expect(normalizeQmlPointValueShowType('int-raw')).toBe('int-raw')
    expect(normalizeQmlPointValueShowType('unknown')).toBe('mm-relative')
  })
})

describe('useUiSettingsStore', () => {
  it('uses QML-compatible defaults for image service and display settings', () => {
    const state = useUiSettingsStore.getState()

    expect(state.useRustImageServer).toBe(false)
    expect(state.rustImageServerPort).toBe(6013)
    expect((state as unknown as { databasPort?: number }).databasPort).toBe(6011)
    expect((state as unknown as { dataPort?: number }).dataPort).toBe(6013)
    expect((state as unknown as { plcPort?: number }).plcPort).toBe(6014)
    expect((state as unknown as { alg2dPort?: number }).alg2dPort).toBe(5011)
    expect((state as unknown as { autoKeepTimeMax?: number }).autoKeepTimeMax).toBe(180)
    expect((state as unknown as { headDateShowModel?: number }).headDateShowModel).toBe(0)
    expect((state as unknown as { dataHeaderHeight?: number }).dataHeaderHeight).toBe(320)
    expect((state as unknown as { pointValueShowType?: string }).pointValueShowType).toBe('mm-relative')
    expect(state.apiServerIp).toBe('127.0.0.1')
    expect(state.apiServerPort).toBe(5011)
    expect(state.qmlThemeName).toBe('dark')
    expect(state.qmlDisplayStyleName).toBe('standard')
    expect(state.softwareUpdateManifestUrl).toBe('')
    expect(state.softwareUpdatePackageUrl).toBe('')
    expect(state.softwareUpdateAutoOpen).toBe(false)
    expect(state.defaultAreaTileCount).toBe(3)
    expect((state as unknown as { useImageCache?: boolean }).useImageCache).toBe(false)
    expect((state as unknown as { maxImageCache?: number }).maxImageCache).toBe(15)
    expect(state.enable1024CacheMode).toBe(false)
    expect(state.showErrorOverlay).toBe(true)
    expect(state.showDefectLabels).toBe(true)
    expect((state as unknown as { showAlarmDefectClasses?: boolean }).showAlarmDefectClasses).toBe(false)
    expect(state.towerWarningThresholdUp).toBe(100)
    expect(state.towerWarningThresholdDown).toBe(-100)
    expect(state.towerWarningOpacity).toBe(50)
    expect(state.areaClipSettings).toEqual(buildQmlAreaClipSettings())
    expect(state.useSharedFolder).toBe(false)
    expect(state.sharedFolderBaseName).toBe('Save_')
  })

  it('stores QML defect-label visibility changes', () => {
    useUiSettingsStore.getState().setShowDefectLabels(false)
    expect(useUiSettingsStore.getState().showDefectLabels).toBe(false)

    useUiSettingsStore.getState().setShowDefectLabels(true)
    expect(useUiSettingsStore.getState().showDefectLabels).toBe(true)
  })

  it('stores QML SurfaceData point value display mode changes', () => {
    const state = useUiSettingsStore.getState() as unknown as {
      pointValueShowType: string
      setPointValueShowType: (pointValueShowType: string) => void
    }

    state.setPointValueShowType('mm-absolute')
    expect((useUiSettingsStore.getState() as unknown as { pointValueShowType: string }).pointValueShowType).toBe(
      'mm-absolute',
    )

    state.setPointValueShowType('int-raw')
    expect((useUiSettingsStore.getState() as unknown as { pointValueShowType: string }).pointValueShowType).toBe(
      'int-raw',
    )

    state.setPointValueShowType('bad-value')
    expect((useUiSettingsStore.getState() as unknown as { pointValueShowType: string }).pointValueShowType).toBe(
      'mm-relative',
    )
  })

  it('stores QML defect filter background visibility changes', () => {
    const state = useUiSettingsStore.getState() as unknown as {
      showAlarmDefectClasses: boolean
      setShowAlarmDefectClasses: (showAlarmDefectClasses: boolean) => void
    }

    state.setShowAlarmDefectClasses(true)
    expect((useUiSettingsStore.getState() as unknown as { showAlarmDefectClasses: boolean }).showAlarmDefectClasses).toBe(
      true,
    )

    state.setShowAlarmDefectClasses(false)
    expect((useUiSettingsStore.getState() as unknown as { showAlarmDefectClasses: boolean }).showAlarmDefectClasses).toBe(
      false,
    )
  })

  it('normalizes persisted AREA tile count changes', () => {
    useUiSettingsStore.getState().setDefaultAreaTileCount(99)
    expect(useUiSettingsStore.getState().defaultAreaTileCount).toBe(10)

    useUiSettingsStore.getState().setDefaultAreaTileCount(0)
    expect(useUiSettingsStore.getState().defaultAreaTileCount).toBe(1)
  })

  it('stores QML image-cache settings', () => {
    const state = useUiSettingsStore.getState() as unknown as {
      useImageCache: boolean
      maxImageCache: number
      setUseImageCache: (useImageCache: boolean) => void
      setMaxImageCache: (maxImageCache: number) => void
    }

    state.setUseImageCache(true)
    state.setMaxImageCache(0)

    expect(useUiSettingsStore.getState()).toMatchObject({
      useImageCache: true,
      maxImageCache: 1,
    })

    state.setMaxImageCache(500)
    expect(useUiSettingsStore.getState()).toMatchObject({ maxImageCache: 200 })

    state.setUseImageCache(false)
    state.setMaxImageCache(15)
  })

  it('normalizes API connection setting changes', () => {
    useUiSettingsStore.getState().setApiServerIp(' 192.168.99.100 ')
    useUiSettingsStore.getState().setApiServerPort(70000)

    expect(useUiSettingsStore.getState().apiServerIp).toBe('192.168.99.100')
    expect(useUiSettingsStore.getState().apiServerPort).toBe(65535)
  })

  it('stores QML service port settings for alarm and maintenance panels without reviving legacy 2D ports', () => {
    const state = useUiSettingsStore.getState() as unknown as {
      databasPort: number
      dataPort: number
      plcPort: number
      alg2dPort: number
      setDatabasPort: (port: number) => void
      setDataPort: (port: number) => void
      setPlcPort: (port: number) => void
      setAlg2dPort: (port: number) => void
    }

    state.setDatabasPort(0)
    state.setDataPort(70000)
    state.setPlcPort(6014.8)
    state.setAlg2dPort(70000)

    expect(useUiSettingsStore.getState()).toMatchObject({
      databasPort: 1,
      dataPort: 65535,
      plcPort: 6014,
      alg2dPort: 65535,
    })

    state.setAlg2dPort(6020)
    expect((useUiSettingsStore.getState() as unknown as { alg2dPort: number }).alg2dPort).toBe(5011)

    state.setDatabasPort(6011)
    state.setDataPort(6013)
    state.setPlcPort(6014)
    state.setAlg2dPort(5011)
  })

  it('stores QML keepLatest auto-restore tick settings', () => {
    const state = useUiSettingsStore.getState() as unknown as {
      autoKeepTimeMax: number
      setAutoKeepTimeMax: (autoKeepTimeMax: number) => void
    }

    state.setAutoKeepTimeMax(7.9)
    expect((useUiSettingsStore.getState() as unknown as { autoKeepTimeMax: number }).autoKeepTimeMax).toBe(7)

    state.setAutoKeepTimeMax(180)
  })

  it('stores QML DataShow data-header height settings', () => {
    const state = useUiSettingsStore.getState() as unknown as {
      dataHeaderHeight: number
      setDataHeaderHeight: (dataHeaderHeight: number) => void
    }

    state.setDataHeaderHeight(90)
    expect((useUiSettingsStore.getState() as unknown as { dataHeaderHeight: number }).dataHeaderHeight).toBe(120)

    state.setDataHeaderHeight(321.9)
    expect((useUiSettingsStore.getState() as unknown as { dataHeaderHeight: number }).dataHeaderHeight).toBe(321)

    state.setDataHeaderHeight(320)
  })

  it('stores QML DataShow header mode settings', () => {
    const state = useUiSettingsStore.getState() as unknown as {
      headDateShowModel: number
      setHeadDateShowModel: (headDateShowModel: number) => void
    }

    state.setHeadDateShowModel(2.9)
    expect((useUiSettingsStore.getState() as unknown as { headDateShowModel: number }).headDateShowModel).toBe(2)

    state.setHeadDateShowModel(-1)
    expect((useUiSettingsStore.getState() as unknown as { headDateShowModel: number }).headDateShowModel).toBe(0)
  })

  it('stores QML software update settings', () => {
    useUiSettingsStore.getState().setSoftwareUpdateManifestUrl('  http://127.0.0.1:5011/software_update/manifest  ')
    useUiSettingsStore.getState().setSoftwareUpdatePackageUrl('  http://127.0.0.1:5011/update.exe  ')
    useUiSettingsStore.getState().setSoftwareUpdateAutoOpen(true)

    expect(useUiSettingsStore.getState().softwareUpdateManifestUrl).toBe(
      'http://127.0.0.1:5011/software_update/manifest',
    )
    expect(useUiSettingsStore.getState().softwareUpdatePackageUrl).toBe('http://127.0.0.1:5011/update.exe')
    expect(useUiSettingsStore.getState().softwareUpdateAutoOpen).toBe(true)
  })

  it('stores QML image mode settings for shared-folder access', () => {
    useUiSettingsStore.getState().setUseSharedFolder(true)
    useUiSettingsStore.getState().setSharedFolderBaseName('  PlantSave_  ')

    expect(useUiSettingsStore.getState().useSharedFolder).toBe(true)
    expect(useUiSettingsStore.getState().sharedFolderBaseName).toBe('PlantSave_')
  })

  it('stores QML theme and display-style settings', () => {
    useUiSettingsStore.getState().setQmlThemeName('blue')
    useUiSettingsStore.getState().setQmlDisplayStyleName('compact')

    expect(useUiSettingsStore.getState().qmlThemeName).toBe('blue')
    expect(useUiSettingsStore.getState().qmlDisplayStyleName).toBe('compact')

    useUiSettingsStore.getState().setQmlThemeName('missing')
    useUiSettingsStore.getState().setQmlDisplayStyleName('missing')

    expect(useUiSettingsStore.getState().qmlThemeName).toBe('dark')
    expect(useUiSettingsStore.getState().qmlDisplayStyleName).toBe('standard')
  })

  it('stores QML clip-setting changes by surface', () => {
    useUiSettingsStore.getState().setAreaClipSetting('S', {
      surfaceKey: 'S',
      label: 'S端',
      mode: 'dynamic',
      fixed: 180,
      a: 2.5,
      b: 210,
      c: 2500,
    })

    expect(useUiSettingsStore.getState().areaClipSettings.find((item) => item.surfaceKey === 'S')).toMatchObject({
      surfaceKey: 'S',
      mode: 'dynamic',
      fixed: 180,
      a: 2.5,
      b: 210,
      c: 2500,
    })
  })
})
