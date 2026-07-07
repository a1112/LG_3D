import { create } from 'zustand'
import { createJSONStorage, persist, type StateStorage } from 'zustand/middleware'

import {
  buildQmlAreaClipSettings,
  normalizeAreaSurfaceKey,
  type AreaClipMode,
  type AreaSurfaceKey,
  type QmlAreaClipSettings,
} from '@/utils/area2d'

export type QmlThemeName = 'dark' | 'light' | 'blue'
export type QmlDisplayStyleName = 'standard' | 'compact' | 'comfortable'
export type QmlSettingsTabKey = 'general' | 'style' | 'alarm' | 'render' | 'camera' | 'info' | 'other'
export type QmlPointValueShowType = 'mm-relative' | 'mm-absolute' | 'int-raw'

export interface QmlSettingsTabOption {
  key: QmlSettingsTabKey
  label: string
}

export const QML_SETTINGS_TAB_OPTIONS: QmlSettingsTabOption[] = [
  { key: 'general', label: '常规' },
  { key: 'style', label: '风格' },
  { key: 'alarm', label: '报警' },
  { key: 'render', label: '3D 渲染' },
  { key: 'camera', label: '相机调整' },
  { key: 'info', label: '信息' },
  { key: 'other', label: '其他' },
]

export const QML_PLACEHOLDER_SETTINGS_TAB_KEYS: QmlSettingsTabKey[] = ['alarm', 'render']

export interface QmlThemeOption {
  key: QmlThemeName
  name: string
  isDark: boolean
  backgroundColor: string
  panelColor: string
  panelElevatedColor: string
  headerColor: string
  headerBorderColor: string
  titleColor: string
  textColor: string
  labelColor: string
  gridLineColor: string
  selectionColor: string
}

export interface QmlDisplayStyleOption {
  key: QmlDisplayStyleName
  name: string
  topHeight: number
  windowButtonWidth: number
  headerButtonGap: number
  controlRadius: number
  titleSize: number
}

export const QML_THEME_OPTIONS: QmlThemeOption[] = [
  {
    key: 'dark',
    name: '黑色主题',
    isDark: true,
    backgroundColor: '#090F14',
    panelColor: '#111B24',
    panelElevatedColor: '#1A2834',
    headerColor: '#0E1821',
    headerBorderColor: '#3A5368',
    titleColor: '#00BCD4',
    textColor: '#F4FAFF',
    labelColor: '#D8E7F2',
    gridLineColor: '#32475A',
    selectionColor: '#2F6F95',
  },
  {
    key: 'light',
    name: '白色主题',
    isDark: false,
    backgroundColor: '#E0E0E0',
    panelColor: '#F4F6F8',
    panelElevatedColor: '#FFFFFF',
    headerColor: '#E9EEF3',
    headerBorderColor: '#B7C2CD',
    titleColor: '#2196F3',
    textColor: '#000000',
    labelColor: '#111827',
    gridLineColor: '#22000000',
    selectionColor: '#90CAF9',
  },
  {
    key: 'blue',
    name: '蓝色主题',
    isDark: true,
    backgroundColor: '#071A2B',
    panelColor: '#0C2338',
    panelElevatedColor: '#143453',
    headerColor: '#082034',
    headerBorderColor: '#356383',
    titleColor: '#03A9F4',
    textColor: '#F2F8FF',
    labelColor: '#D5E8F7',
    gridLineColor: '#2E5574',
    selectionColor: '#2C78B2',
  },
]

export const QML_DISPLAY_STYLE_OPTIONS: QmlDisplayStyleOption[] = [
  {
    key: 'standard',
    name: '标准',
    topHeight: 45,
    windowButtonWidth: 46,
    headerButtonGap: 4,
    controlRadius: 3,
    titleSize: 22,
  },
  {
    key: 'compact',
    name: '紧凑',
    topHeight: 40,
    windowButtonWidth: 42,
    headerButtonGap: 2,
    controlRadius: 2,
    titleSize: 20,
  },
  {
    key: 'comfortable',
    name: '大屏',
    topHeight: 52,
    windowButtonWidth: 54,
    headerButtonGap: 6,
    controlRadius: 4,
    titleSize: 24,
  },
]

interface UiSettingsState {
  apiServerIp: string
  apiServerPort: number
  qmlThemeName: QmlThemeName
  qmlDisplayStyleName: QmlDisplayStyleName
  softwareUpdateManifestUrl: string
  softwareUpdatePackageUrl: string
  softwareUpdateAutoOpen: boolean
  useSharedFolder: boolean
  sharedFolderBaseName: string
  useRustImageServer: boolean
  rustImageServerPort: number
  databasPort: number
  dataPort: number
  plcPort: number
  alg2dPort: number
  autoKeepTimeMax: number
  headDateShowModel: number
  dataHeaderHeight: number
  showTileDebugBorders: boolean
  defaultAreaTileCount: number
  useImageCache: boolean
  maxImageCache: number
  enable1024CacheMode: boolean
  showErrorOverlay: boolean
  showDefectLabels: boolean
  pointValueShowType: QmlPointValueShowType
  showAlarmDefectClasses: boolean
  towerWarningThresholdUp: number
  towerWarningThresholdDown: number
  towerWarningOpacity: number
  areaClipSettings: QmlAreaClipSettings[]
  setApiServerIp: (apiServerIp: string) => void
  setApiServerPort: (apiServerPort: number) => void
  setQmlThemeName: (qmlThemeName: string) => void
  setQmlDisplayStyleName: (qmlDisplayStyleName: string) => void
  setSoftwareUpdateManifestUrl: (softwareUpdateManifestUrl: string) => void
  setSoftwareUpdatePackageUrl: (softwareUpdatePackageUrl: string) => void
  setSoftwareUpdateAutoOpen: (softwareUpdateAutoOpen: boolean) => void
  setUseSharedFolder: (useSharedFolder: boolean) => void
  setSharedFolderBaseName: (sharedFolderBaseName: string) => void
  setUseRustImageServer: (useRustImageServer: boolean) => void
  setRustImageServerPort: (rustImageServerPort: number) => void
  setDatabasPort: (databasPort: number) => void
  setDataPort: (dataPort: number) => void
  setPlcPort: (plcPort: number) => void
  setAlg2dPort: (alg2dPort: number) => void
  setAutoKeepTimeMax: (autoKeepTimeMax: number) => void
  setHeadDateShowModel: (headDateShowModel: number) => void
  setDataHeaderHeight: (dataHeaderHeight: number) => void
  setShowTileDebugBorders: (showTileDebugBorders: boolean) => void
  setDefaultAreaTileCount: (defaultAreaTileCount: number) => void
  setUseImageCache: (useImageCache: boolean) => void
  setMaxImageCache: (maxImageCache: number) => void
  setEnable1024CacheMode: (enable1024CacheMode: boolean) => void
  setShowErrorOverlay: (showErrorOverlay: boolean) => void
  setShowDefectLabels: (showDefectLabels: boolean) => void
  setPointValueShowType: (pointValueShowType: string) => void
  setShowAlarmDefectClasses: (showAlarmDefectClasses: boolean) => void
  setTowerWarningThresholdUp: (towerWarningThresholdUp: number) => void
  setTowerWarningThresholdDown: (towerWarningThresholdDown: number) => void
  setTowerWarningOpacity: (towerWarningOpacity: number) => void
  setAreaClipSetting: (surfaceKey: AreaSurfaceKey, settings: QmlAreaClipSettings) => void
}

export function normalizeAreaTileCount(value: number): number {
  if (!Number.isFinite(value)) return 3
  return Math.min(Math.max(Math.trunc(value), 1), 10)
}

export function normalizeMaxImageCache(value: number): number {
  if (!Number.isFinite(value)) return 15
  return Math.min(Math.max(Math.trunc(value), 1), 200)
}

export function normalizeImageServerPort(value: number): number {
  if (!Number.isFinite(value)) return 6013
  return Math.min(Math.max(Math.trunc(value), 1), 65535)
}

export function normalizeQmlServicePort(value: number, fallback: number): number {
  if (!Number.isFinite(value)) return fallback
  return Math.min(Math.max(Math.trunc(value), 1), 65535)
}

export function normalizeAlg2dServicePort(value: number): number {
  const normalizedPort = normalizeQmlServicePort(value, 5011)
  return normalizedPort === 6020 ? 5011 : normalizedPort
}

export function normalizeApiServerIp(value: string): string {
  const trimmed = value.trim()
  if (!trimmed || !/^[a-zA-Z0-9.-]+$/.test(trimmed)) return '127.0.0.1'
  return trimmed
}

export function normalizeApiServerPort(value: number): number {
  if (!Number.isFinite(value)) return 5011
  return Math.min(Math.max(Math.trunc(value), 1), 65535)
}

export function normalizeAutoKeepTimeMax(value: number): number {
  if (!Number.isFinite(value)) return 180
  return Math.min(Math.max(Math.trunc(value), 1), 1440)
}

export function normalizeDataHeaderHeight(value: number): number {
  if (!Number.isFinite(value)) return 320
  return Math.min(Math.max(Math.trunc(value), 120), 720)
}

export function normalizeHeadDateShowModel(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(Math.max(Math.trunc(value), 0), 2)
}

export function normalizeQmlPointValueShowType(value: string): QmlPointValueShowType {
  return value === 'mm-absolute' || value === 'int-raw' ? value : 'mm-relative'
}

export function normalizeQmlThemeName(value: string): QmlThemeName {
  return QML_THEME_OPTIONS.some((item) => item.key === value) ? (value as QmlThemeName) : 'dark'
}

export function getNextQmlTopIconThemeName(qmlThemeName: string): QmlThemeName {
  const normalizedThemeName = normalizeQmlThemeName(qmlThemeName)
  const currentTheme = QML_THEME_OPTIONS.find((item) => item.key === normalizedThemeName) ?? QML_THEME_OPTIONS[0]

  return currentTheme.isDark ? 'light' : 'dark'
}

export function normalizeQmlDisplayStyleName(value: string): QmlDisplayStyleName {
  return QML_DISPLAY_STYLE_OPTIONS.some((item) => item.key === value)
    ? (value as QmlDisplayStyleName)
    : 'standard'
}

function normalizeOptionalUrl(value: string): string {
  return value.trim()
}

function normalizeSharedFolderBaseName(value: string): string {
  return value.trim() || 'Save_'
}

export function normalizeTowerWarningThresholdUp(value: number): number {
  if (!Number.isFinite(value)) return 100
  return Math.min(Math.max(Math.trunc(value), 0), 100)
}

export function normalizeTowerWarningThresholdDown(value: number): number {
  if (!Number.isFinite(value)) return -100
  return Math.min(Math.max(Math.trunc(value), -100), 0)
}

export function normalizeTowerWarningOpacity(value: number): number {
  if (!Number.isFinite(value)) return 50
  return Math.min(Math.max(Math.trunc(value), 0), 100)
}

function normalizeClipMode(value: unknown): AreaClipMode {
  return value === 'dynamic' ? 'dynamic' : 'fixed'
}

function normalizeClipFixedValue(value: unknown, fallback: number): number {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return fallback
  return Math.min(Math.max(Math.trunc(numberValue), 0), 10000)
}

function normalizeClipDynamicValue(value: unknown, fallback: number): number {
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return fallback
  return Math.min(Math.max(numberValue, -100000), 100000)
}

function normalizeAreaClipSetting(
  surfaceKey: AreaSurfaceKey,
  value: Partial<QmlAreaClipSettings> | undefined,
): QmlAreaClipSettings {
  const defaultSetting = buildQmlAreaClipSettings().find((item) => item.surfaceKey === surfaceKey)!

  return {
    surfaceKey,
    label: defaultSetting.label,
    mode: normalizeClipMode(value?.mode),
    fixed: normalizeClipFixedValue(value?.fixed, defaultSetting.fixed),
    a: normalizeClipDynamicValue(value?.a, defaultSetting.a),
    b: normalizeClipDynamicValue(value?.b, defaultSetting.b),
    c: normalizeClipDynamicValue(value?.c, defaultSetting.c),
  }
}

function normalizeAreaClipSettings(value: unknown): QmlAreaClipSettings[] {
  const items = Array.isArray(value) ? value : []
  const bySurface = new Map(
    items
      .filter((item): item is Partial<QmlAreaClipSettings> => item !== null && typeof item === 'object')
      .map((item) => [normalizeAreaSurfaceKey(item.surfaceKey), item]),
  )

  return buildQmlAreaClipSettings().map((defaultSetting) =>
    normalizeAreaClipSetting(defaultSetting.surfaceKey, bySurface.get(defaultSetting.surfaceKey)),
  )
}

const memoryStorage = new Map<string, string>()

const fallbackStorage: StateStorage = {
  getItem: (name) => memoryStorage.get(name) ?? null,
  setItem: (name, value) => {
    memoryStorage.set(name, value)
  },
  removeItem: (name) => {
    memoryStorage.delete(name)
  },
}

function getUiSettingsStorage(): StateStorage {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage
  }
  return fallbackStorage
}

function migrateLegacyUiSettings(persistedState: unknown): unknown {
  if (!persistedState || typeof persistedState !== 'object') return persistedState

  const nextState = { ...(persistedState as Partial<UiSettingsState>) }
  if ('apiServerPort' in nextState) {
    nextState.apiServerPort = nextState.apiServerPort === 5010 ? 5011 : nextState.apiServerPort
  }
  if ('alg2dPort' in nextState) {
    nextState.alg2dPort = normalizeAlg2dServicePort(Number(nextState.alg2dPort))
  }

  return nextState
}

export const useUiSettingsStore = create<UiSettingsState>()(
  persist(
    (set) => ({
      apiServerIp: '127.0.0.1',
      apiServerPort: 5011,
      qmlThemeName: 'dark',
      qmlDisplayStyleName: 'standard',
      softwareUpdateManifestUrl: '',
      softwareUpdatePackageUrl: '',
      softwareUpdateAutoOpen: false,
      useSharedFolder: false,
      sharedFolderBaseName: 'Save_',
      useRustImageServer: false,
      rustImageServerPort: 6013,
      databasPort: 6011,
      dataPort: 6013,
      plcPort: 6014,
      alg2dPort: 5011,
      autoKeepTimeMax: 180,
      headDateShowModel: 0,
      dataHeaderHeight: 320,
      showTileDebugBorders: false,
      defaultAreaTileCount: 3,
      useImageCache: false,
      maxImageCache: 15,
      enable1024CacheMode: false,
      showErrorOverlay: true,
      showDefectLabels: true,
      pointValueShowType: 'mm-relative',
      showAlarmDefectClasses: false,
      towerWarningThresholdUp: 100,
      towerWarningThresholdDown: -100,
      towerWarningOpacity: 50,
      areaClipSettings: buildQmlAreaClipSettings(),
      setApiServerIp: (apiServerIp) => set({ apiServerIp: normalizeApiServerIp(apiServerIp) }),
      setApiServerPort: (apiServerPort) => set({ apiServerPort: normalizeApiServerPort(apiServerPort) }),
      setQmlThemeName: (qmlThemeName) => set({ qmlThemeName: normalizeQmlThemeName(qmlThemeName) }),
      setQmlDisplayStyleName: (qmlDisplayStyleName) =>
        set({ qmlDisplayStyleName: normalizeQmlDisplayStyleName(qmlDisplayStyleName) }),
      setSoftwareUpdateManifestUrl: (softwareUpdateManifestUrl) =>
        set({ softwareUpdateManifestUrl: normalizeOptionalUrl(softwareUpdateManifestUrl) }),
      setSoftwareUpdatePackageUrl: (softwareUpdatePackageUrl) =>
        set({ softwareUpdatePackageUrl: normalizeOptionalUrl(softwareUpdatePackageUrl) }),
      setSoftwareUpdateAutoOpen: (softwareUpdateAutoOpen) => set({ softwareUpdateAutoOpen }),
      setUseSharedFolder: (useSharedFolder) => set({ useSharedFolder }),
      setSharedFolderBaseName: (sharedFolderBaseName) =>
        set({ sharedFolderBaseName: normalizeSharedFolderBaseName(sharedFolderBaseName) }),
      setUseRustImageServer: (useRustImageServer) => set({ useRustImageServer }),
      setRustImageServerPort: (rustImageServerPort) =>
        set({ rustImageServerPort: normalizeImageServerPort(rustImageServerPort) }),
      setDatabasPort: (databasPort) => set({ databasPort: normalizeQmlServicePort(databasPort, 6011) }),
      setDataPort: (dataPort) => set({ dataPort: normalizeQmlServicePort(dataPort, 6013) }),
      setPlcPort: (plcPort) => set({ plcPort: normalizeQmlServicePort(plcPort, 6014) }),
      setAlg2dPort: (alg2dPort) => set({ alg2dPort: normalizeAlg2dServicePort(alg2dPort) }),
      setAutoKeepTimeMax: (autoKeepTimeMax) =>
        set({ autoKeepTimeMax: normalizeAutoKeepTimeMax(autoKeepTimeMax) }),
      setHeadDateShowModel: (headDateShowModel) =>
        set({ headDateShowModel: normalizeHeadDateShowModel(headDateShowModel) }),
      setDataHeaderHeight: (dataHeaderHeight) =>
        set({ dataHeaderHeight: normalizeDataHeaderHeight(dataHeaderHeight) }),
      setShowTileDebugBorders: (showTileDebugBorders) => set({ showTileDebugBorders }),
      setDefaultAreaTileCount: (defaultAreaTileCount) =>
        set({ defaultAreaTileCount: normalizeAreaTileCount(defaultAreaTileCount) }),
      setUseImageCache: (useImageCache) => set({ useImageCache }),
      setMaxImageCache: (maxImageCache) => set({ maxImageCache: normalizeMaxImageCache(maxImageCache) }),
      setEnable1024CacheMode: (enable1024CacheMode) => set({ enable1024CacheMode }),
      setShowErrorOverlay: (showErrorOverlay) => set({ showErrorOverlay }),
      setShowDefectLabels: (showDefectLabels) => set({ showDefectLabels }),
      setPointValueShowType: (pointValueShowType) =>
        set({ pointValueShowType: normalizeQmlPointValueShowType(pointValueShowType) }),
      setShowAlarmDefectClasses: (showAlarmDefectClasses) => set({ showAlarmDefectClasses }),
      setTowerWarningThresholdUp: (towerWarningThresholdUp) =>
        set({ towerWarningThresholdUp: normalizeTowerWarningThresholdUp(towerWarningThresholdUp) }),
      setTowerWarningThresholdDown: (towerWarningThresholdDown) =>
        set({ towerWarningThresholdDown: normalizeTowerWarningThresholdDown(towerWarningThresholdDown) }),
      setTowerWarningOpacity: (towerWarningOpacity) =>
        set({ towerWarningOpacity: normalizeTowerWarningOpacity(towerWarningOpacity) }),
      setAreaClipSetting: (surfaceKey, settings) =>
        set((state) => {
          const normalizedSurfaceKey = normalizeAreaSurfaceKey(surfaceKey)
          const nextSetting = normalizeAreaClipSetting(normalizedSurfaceKey, settings)
          const currentSettings = normalizeAreaClipSettings(state.areaClipSettings)

          return {
            areaClipSettings: currentSettings.map((item) =>
              item.surfaceKey === normalizedSurfaceKey ? nextSetting : item,
            ),
          }
        }),
    }),
    {
      name: 'motion-studio-ui-settings',
      version: 1,
      storage: createJSONStorage(getUiSettingsStorage),
      migrate: migrateLegacyUiSettings,
      partialize: (state) => ({
        apiServerIp: normalizeApiServerIp(state.apiServerIp),
        apiServerPort: normalizeApiServerPort(state.apiServerPort),
        qmlThemeName: normalizeQmlThemeName(state.qmlThemeName),
        qmlDisplayStyleName: normalizeQmlDisplayStyleName(state.qmlDisplayStyleName),
        softwareUpdateManifestUrl: normalizeOptionalUrl(state.softwareUpdateManifestUrl),
        softwareUpdatePackageUrl: normalizeOptionalUrl(state.softwareUpdatePackageUrl),
        softwareUpdateAutoOpen: state.softwareUpdateAutoOpen,
        useSharedFolder: state.useSharedFolder,
        sharedFolderBaseName: normalizeSharedFolderBaseName(state.sharedFolderBaseName),
        useRustImageServer: state.useRustImageServer,
        rustImageServerPort: normalizeImageServerPort(state.rustImageServerPort),
        databasPort: normalizeQmlServicePort(state.databasPort, 6011),
        dataPort: normalizeQmlServicePort(state.dataPort, 6013),
        plcPort: normalizeQmlServicePort(state.plcPort, 6014),
        alg2dPort: normalizeAlg2dServicePort(state.alg2dPort),
        autoKeepTimeMax: normalizeAutoKeepTimeMax(state.autoKeepTimeMax),
        headDateShowModel: normalizeHeadDateShowModel(state.headDateShowModel),
        dataHeaderHeight: normalizeDataHeaderHeight(state.dataHeaderHeight),
        showTileDebugBorders: state.showTileDebugBorders,
        defaultAreaTileCount: normalizeAreaTileCount(state.defaultAreaTileCount),
        useImageCache: state.useImageCache,
        maxImageCache: normalizeMaxImageCache(state.maxImageCache),
        enable1024CacheMode: state.enable1024CacheMode,
        showErrorOverlay: state.showErrorOverlay,
        showDefectLabels: state.showDefectLabels,
        pointValueShowType: normalizeQmlPointValueShowType(state.pointValueShowType),
        showAlarmDefectClasses: state.showAlarmDefectClasses,
        towerWarningThresholdUp: normalizeTowerWarningThresholdUp(state.towerWarningThresholdUp),
        towerWarningThresholdDown: normalizeTowerWarningThresholdDown(state.towerWarningThresholdDown),
        towerWarningOpacity: normalizeTowerWarningOpacity(state.towerWarningOpacity),
        areaClipSettings: normalizeAreaClipSettings(state.areaClipSettings),
      }),
    },
  ),
)
