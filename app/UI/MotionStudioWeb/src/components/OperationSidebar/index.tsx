import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react'
import dayjs, { type Dayjs } from 'dayjs'
import { Badge, Button, Checkbox, DatePicker, Dropdown, Empty, Input, InputNumber, Modal, Progress, Select, Spin, Tag, Tooltip, message } from 'antd'
import type { MenuProps } from 'antd'
import {
  ClockCircleOutlined,
  CopyOutlined,
  FilterOutlined,
  FolderOpenOutlined,
  InfoCircleOutlined,
  LinkOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ScissorOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'

import BackupImageModal from '@/components/BackupImageModal'
import CurrentCoilDetailModal from '@/components/CurrentCoilDetailModal'
import ListValueChangeModal from '@/components/ListValueChangeModal'
import {
  area2dApi,
  buildReDetectionWsPath,
  coilApi,
  defectConfigApi,
  imageToolApi,
  joinBaseUrl,
  resolveImageRuntimeBaseUrl,
  runtimeApi,
  serviceBaseUrls,
  systemApi,
} from '@/services/api'
import { useCoilStore, type CoilListMode } from '@/stores/coilStore'
import { useUiSettingsStore } from '@/stores/uiSettingsStore'
import type { CoilData, SurfaceKey } from '@/types'
import { copyTextToClipboard } from '@/utils/clipboard'
import {
  buildCoilSaveFolderPath,
  buildCoilSaveFolderUrl,
  buildCoilListDataSourceUrl,
  getCoilListReDetectionRange,
  getCoilCopyText,
  getCurrentCoilReDetectionRange,
  getSurfaceSaveFolder,
  openCoilSaveFolderUrl,
  openQmlExternalUrl,
  type ReDetectionRange,
  resolveQmlCoilListDataSourceUrl,
  runClipMaxAndGetFolderUrl,
  type CoilCopyField,
} from '@/utils/coilActions'
import { getApiRequestHistory } from '@/utils/apiHistory'
import {
  buildSearchResultsWithDetailFallback,
  buildQmlHistoryCoilList,
  resolveCoilSearch,
  selectVisibleCoilList,
} from '@/utils/coilSearch'
import {
  advanceQmlKeepLatestAutoRestoreTick,
  buildQmlFlushStartCoilId,
  mergeQmlFlushCoilList,
  resolveQmlRealtimeCurrentCoil,
  QML_COIL_REFRESH_INTERVAL_MS,
  QML_KEEP_LATEST_AUTO_RESTORE_INTERVAL_MS,
} from '@/utils/coilRefresh'
import {
  buildCoilCheckPayload,
  COIL_CHECK_OPTIONS,
  getCoilCheckOption,
  getQmlCoilCheckSelectColor,
  getQmlCoilCheckStatusClass,
  normalizeCoilCheck,
  resolveCoilCheck,
  resolveQmlCoilCheckStatus,
  type CoilCheckOption,
  type CoilCheckState,
  type CoilCheckStatus,
} from '@/utils/coilCheck'
import {
  buildQmlLeftListDefectFilterOptions,
  filterQmlCoilsByDefectClasses,
  getDefaultSelectedDefectClasses,
  hasQmlLeftListVisibleDefectOptions,
} from '@/utils/defectFilter'
import { getQmlCurrentDayRange, resolveQmlDateRangeSearch } from '@/utils/qmlDateTime'
import {
  buildReDetectionWebSocketStartMessage,
  buildReDetectionStatusView,
  parseReDetectionWebSocketMessage,
  resolveReDetectionWsUrl,
} from '@/utils/reDetection'
import { buildApiDelayView, buildOperationSidebarAlarmRows, readImageServiceHealthOk } from '@/utils/serviceConnection'
import './OperationSidebar.css'

type SearchMode = 'coilNo' | 'date' | 'coilId'
type SearchDatePart = 'year' | 'month' | 'day' | 'hour' | 'minute'
type SearchDateEndpoint = 'start' | 'end'

const QML_LIST_COLUMN_GRID = '52px minmax(74px, 1.1fr) minmax(42px, 0.7fr) minmax(96px, 1.4fr)'
const SEARCH_DATE_PICKER_CLASS_NAMES = {
  popup: {
    root: 'search-date-picker-popup',
  },
}

function formatSearchDatePart(date: Dayjs | null, part: SearchDatePart) {
  if (!date) return '--'
  if (part === 'year') return String(date.year())
  if (part === 'month') return String(date.month() + 1)
  if (part === 'day') return String(date.date())
  if (part === 'hour') return String(date.hour())
  return String(date.minute())
}

function getQmlSearchPanelHeight(mode: SearchMode) {
  return mode === 'date' ? 130 : 95
}

function statusColor(status: number) {
  if (status === 1) return 'processing'
  if (status === 2) return 'success'
  if (status === 3) return 'error'
  return 'default'
}

function statusText(status: number) {
  if (status === 1) return '处理中'
  if (status === 2) return '已完成'
  if (status === 3) return '错误'
  return '未知'
}

function asQmlListRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readQmlListValue(source: unknown, keys: string[]): unknown {
  const record = asQmlListRecord(source)
  for (const key of keys) {
    const value = record[key]
    if (value !== undefined && value !== null && String(value) !== '') return value
  }
  return undefined
}

function readQmlListString(source: unknown, keys: string[], fallback = ''): string {
  const value = readQmlListValue(source, keys)
  return value === undefined ? fallback : String(value)
}

function readQmlListNumber(source: unknown, keys: string[], fallback = 0): number {
  const value = readQmlListValue(source, keys)
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : fallback
}

function getQmlListDefectItems(coil: CoilData): Record<string, unknown>[] {
  const raw = asQmlListRecord(coil.raw)
  const source = raw.childrenCoilDefect ?? raw.defects
  if (Array.isArray(source)) return source.map(asQmlListRecord)
  const record = asQmlListRecord(source)
  return Object.keys(record).length > 0 ? [record] : []
}

function getQmlListCoilMaxDefect(coil: CoilData) {
  const raw = asQmlListRecord(coil.raw)
  const rootName = readQmlListString(raw, ['maxDefectName', 'MaxDefectName'])
  if (rootName) {
    return {
      name: rootName,
      surface: readQmlListString(raw, ['maxDefectSurface', 'MaxDefectSurface']),
      level: readQmlListNumber(raw, ['maxDefectLevel', 'MaxDefectLevel']),
    }
  }

  let maxDefect = { name: '', surface: '', level: -1 }
  for (const defect of getQmlListDefectItems(coil)) {
    const name = readQmlListString(defect, [
      'defectName',
      'DefectName',
      'configDefectName',
      'ConfigDefectName',
      'name',
      'Name',
    ])
    if (!name) continue

    const level = readQmlListNumber(defect, ['defectLevel', 'DefectLevel', 'level', 'Level'])
    if (level > maxDefect.level) {
      maxDefect = {
        name,
        level,
        surface: readQmlListString(defect, ['surface', 'Surface']),
      }
    }
  }

  return maxDefect.level >= 0 ? maxDefect : { name: '', surface: '', level: 0 }
}

function formatQmlListCoilDefectStatus(coil: CoilData) {
  const total = (coil.defectCountS ?? 0) + (coil.defectCountL ?? 0)
  const maxDefect = getQmlListCoilMaxDefect(coil)
  if (!maxDefect.name) return `${total}`
  const surfacePrefix = maxDefect.surface ? `${maxDefect.surface}:` : ''
  return `${total} / ${surfacePrefix}${maxDefect.name}`
}

function buildQmlListCoilDefectTip(coil: CoilData) {
  const maxDefect = getQmlListCoilMaxDefect(coil)
  return (
    `S: ${coil.defectCountS ?? 0}  L: ${coil.defectCountL ?? 0}` +
    (maxDefect.name ? `\n最严重缺陷: ${maxDefect.name}` : '') +
    (maxDefect.surface ? ` (${maxDefect.surface})` : '') +
    (maxDefect.level > 0 ? `  等级: ${maxDefect.level}` : '')
  )
}

function getQmlListCoilDefectLevelClass(coil: CoilData) {
  const total = (coil.defectCountS ?? 0) + (coil.defectCountL ?? 0)
  if (total <= 0) return 'defect-level-none'

  const level = getQmlListCoilMaxDefect(coil).level
  if (level <= 2) return 'defect-level-low'
  if (level <= 3) return 'defect-level-warn'
  if (level <= 4) return 'defect-level-high'
  return 'defect-level-critical'
}

function buildQmlCoilCheckMenuLabel(option: CoilCheckOption, selected: boolean) {
  return (
    <span
      className={`qml-row-check-menu-item ${selected ? 'selected' : ''}`}
      data-qml-selected={selected ? 'true' : 'false'}
      style={{
        '--qml-row-check-color': getQmlCoilCheckSelectColor(option.status),
      } as CSSProperties}
    >
      {option.label}
    </span>
  )
}

interface OperationSidebarProps {
  onOpenConnectSettings: () => void
}

export default function OperationSidebar({ onOpenConnectSettings }: OperationSidebarProps) {
  const {
    currentCoil,
    coilList,
    coilListMode: listMode,
    keepLatest,
    setCoilList,
    setCurrentCoilList,
    setCoilListMode: setListMode,
    setCurrentCoil,
    setKeepLatest,
    surfaceKey,
    setSurfaceKey,
    returnRealtimeCommand,
  } = useCoilStore()
  const autoKeepTimeMax = useUiSettingsStore((state) => state.autoKeepTimeMax)
  const useRustImageServer = useUiSettingsStore((state) => state.useRustImageServer)
  const rustImageServerPort = useUiSettingsStore((state) => state.rustImageServerPort)
  const useSharedFolder = useUiSettingsStore((state) => state.useSharedFolder)
  const sharedFolderBaseName = useUiSettingsStore((state) => state.sharedFolderBaseName)
  const [keyword, setKeyword] = useState('')
  const [searchMode, setSearchMode] = useState<SearchMode>('coilNo')
  const [searchFilterOpen, setSearchFilterOpen] = useState(false)
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(() => {
    const [start, end] = getQmlCurrentDayRange()
    return [dayjs(start), dayjs(end)]
  })
  const [openSearchDatePicker, setOpenSearchDatePicker] = useState<SearchDateEndpoint | null>(null)
  const [historyCoils, setHistoryCoils] = useState<CoilData[]>([])
  const [, setAutoKeepLatestTicks] = useState(0)
  const [listDefectFilterEnabled, setListDefectFilterEnabled] = useState(false)
  const [selectedListDefectClasses, setSelectedListDefectClasses] = useState<string[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [clipMaxSurface, setClipMaxSurface] = useState<SurfaceKey | null>(null)
  const [isRejoiningArea, setIsRejoiningArea] = useState(false)
  const [currentDetailOpen, setCurrentDetailOpen] = useState(false)
  const [reDetectionOpen, setReDetectionOpen] = useState(false)
  const [backupImageOpen, setBackupImageOpen] = useState(false)
  const [listValueChangeOpen, setListValueChangeOpen] = useState(false)
  const [reDetectionRange, setReDetectionRange] = useState<ReDetectionRange>({ fromId: 0, toId: 0 })
  const [isStartingReDetection, setIsStartingReDetection] = useState(false)
  const [reDetectionWsReady, setReDetectionWsReady] = useState(false)
  const [reDetectionWsStatus, setReDetectionWsStatus] = useState<unknown>(null)
  const [reDetectionReconnectSerial, setReDetectionReconnectSerial] = useState(0)
  const reDetectionSocketRef = useRef<WebSocket | null>(null)
  const handledReturnRealtimeCommandRef = useRef(0)
  const listDefectFilterInitializedRef = useRef(false)
  const pendingHistorySelectionRef = useRef(false)
  const [localCoilCheck, setLocalCoilCheck] = useState<CoilCheckState | null>(null)
  const [coilCheckMsg, setCoilCheckMsg] = useState('')
  const [isSettingCoilCheck, setIsSettingCoilCheck] = useState(false)

  const { data, isFetching, refetch } = useQuery({
    queryKey: ['coilList'],
    queryFn: async () => {
      const realtimeCoils = useCoilStore.getState().coilList
      if (realtimeCoils.length === 0) return coilApi.getCoilList(80)

      const result = await coilApi.flush(buildQmlFlushStartCoilId(realtimeCoils))
      return {
        ...result,
        data: mergeQmlFlushCoilList(realtimeCoils, result.data),
      }
    },
    refetchInterval: QML_COIL_REFRESH_INTERVAL_MS,
  })
  const { data: infoData } = useQuery({
    queryKey: ['system', 'info'],
    queryFn: systemApi.getInfo,
    staleTime: 60_000,
    retry: 1,
  })
  const reDetectionFolder = useMemo(() => {
    const saveFolderS = getSurfaceSaveFolder(infoData, 'S')
    const saveFolderL = getSurfaceSaveFolder(infoData, 'L')
    return saveFolderS || saveFolderL
  }, [infoData])
  const { data: defectDictData } = useQuery({
    queryKey: ['defect-dict'],
    queryFn: defectConfigApi.getDefectDict,
    staleTime: 60_000,
    retry: 1,
  })
  const { data: reDetectionStatusData, refetch: refetchReDetectionStatus } = useQuery({
    queryKey: ['runtime', 'reDetectionStatus'],
    queryFn: runtimeApi.getReDetectionStatus,
    enabled: reDetectionOpen && !reDetectionWsReady,
    refetchInterval: reDetectionOpen && !reDetectionWsReady ? 1000 : false,
  })
  const { data: coilCheckData, refetch: refetchCoilCheck } = useQuery({
    queryKey: ['coil', 'checkStatus', currentCoil?.id],
    queryFn: () => coilApi.getCoilStatus(currentCoil?.id ?? 0),
    enabled: Boolean(currentCoil?.id),
    retry: 1,
  })
  const imageServiceBaseUrl = resolveImageRuntimeBaseUrl({
    useRustImageServer,
    rustImageServerPort,
    useSharedFolder,
    sharedFolderBaseName,
  })
  const { data: imageServiceHealth, isError: imageServiceHealthError } = useQuery({
    queryKey: ['operationSidebar', 'imageServiceHealth', imageServiceBaseUrl],
    queryFn: async () => {
      const response = await fetch(joinBaseUrl(imageServiceBaseUrl, '/health'))
      if (!response.ok) throw new Error(`image health ${response.status}`)
      return response.json() as Promise<unknown>
    },
    retry: 1,
    refetchInterval: 10_000,
  })
  const sidebarApiDelayQuery = useQuery({
    queryKey: ['operationSidebar', 'apiDelay'],
    queryFn: async () => {
      const startTime = Date.now()
      await systemApi.getDelay()
      return Date.now() - startTime
    },
    retry: 1,
    refetchInterval: 8_000,
  })
  const qmlCurrentCoilList = useMemo(
    () => selectVisibleCoilList(listMode, coilList, historyCoils),
    [coilList, historyCoils, listMode],
  )

  useEffect(() => {
    const nextList = data?.data ?? []
    setCoilList(nextList)
    if (pendingHistorySelectionRef.current) {
      if (listMode === 'history') {
        pendingHistorySelectionRef.current = false
      }
      return
    }
    if (listMode === 'realtime') {
      const nextCurrentCoil = resolveQmlRealtimeCurrentCoil(currentCoil, nextList, keepLatest)
      if (nextCurrentCoil && nextCurrentCoil !== currentCoil) {
        setCurrentCoil(nextCurrentCoil)
      }
    }
  }, [currentCoil, data, keepLatest, listMode, setCoilList, setCurrentCoil])

  useEffect(() => {
    setCurrentCoilList(qmlCurrentCoilList)
  }, [qmlCurrentCoilList, setCurrentCoilList])

  useEffect(() => {
    if (keepLatest) {
      setAutoKeepLatestTicks(0)
      return
    }

    const timer = window.setInterval(() => {
      setAutoKeepLatestTicks((ticks) => {
        const nextState = advanceQmlKeepLatestAutoRestoreTick(ticks, autoKeepTimeMax)
        if (nextState.keepLatest) {
          setKeepLatest(true)
        }
        return nextState.autoKeepLatestTicks
      })
    }, QML_KEEP_LATEST_AUTO_RESTORE_INTERVAL_MS)

    return () => window.clearInterval(timer)
  }, [autoKeepTimeMax, keepLatest])

  const remoteCoilCheck = normalizeCoilCheck(coilCheckData, currentCoil?.id ?? 0)
  const coilCheck = resolveCoilCheck(coilCheckData, currentCoil?.id ?? 0, localCoilCheck)
  const coilCheckOption = getCoilCheckOption(coilCheck.status)

  useEffect(() => {
    setCoilCheckMsg(coilCheck.msg)
  }, [coilCheck.coilId, coilCheck.msg])

  useEffect(() => {
    if (!reDetectionOpen) {
      setReDetectionWsReady(false)
      setReDetectionWsStatus(null)
      return
    }

    let closed = false
    const socket = new WebSocket(resolveReDetectionWsUrl(serviceBaseUrls.apiWsBaseUrl, buildReDetectionWsPath()))
    reDetectionSocketRef.current = socket
    setReDetectionWsReady(false)
    setReDetectionWsStatus(null)

    socket.onopen = () => {
      if (!closed) {
        setReDetectionWsReady(true)
        setReDetectionWsStatus({})
      }
    }
    socket.onmessage = (event) => {
      if (!closed) setReDetectionWsStatus(parseReDetectionWebSocketMessage(String(event.data)))
    }
    socket.onerror = () => {
      if (!closed) setReDetectionWsStatus({ error: '连接断开!' })
    }
    socket.onclose = () => {
      if (!closed) {
        setReDetectionWsReady(false)
        setReDetectionWsStatus({ error: '连接断开!' })
      }
    }

    return () => {
      closed = true
      setReDetectionWsReady(false)
      if (reDetectionSocketRef.current === socket) {
        reDetectionSocketRef.current = null
      }
      socket.close()
    }
  }, [reDetectionOpen, reDetectionReconnectSerial])

  useEffect(() => {
    if (
      localCoilCheck &&
      localCoilCheck.coilId === remoteCoilCheck.coilId &&
      localCoilCheck.status === remoteCoilCheck.status &&
      localCoilCheck.msg === remoteCoilCheck.msg
    ) {
      setLocalCoilCheck(null)
    }
  }, [localCoilCheck, remoteCoilCheck.coilId, remoteCoilCheck.msg, remoteCoilCheck.status])

  const listDefectFilterOptions = useMemo(
    () => buildQmlLeftListDefectFilterOptions(defectDictData),
    [defectDictData],
  )

  useEffect(() => {
    if (listDefectFilterOptions.length === 0 || !hasQmlLeftListVisibleDefectOptions(listDefectFilterOptions)) return

    const optionNames = new Set(listDefectFilterOptions.map((option) => option.name))
    if (!listDefectFilterInitializedRef.current) {
      setSelectedListDefectClasses(getDefaultSelectedDefectClasses(listDefectFilterOptions))
      listDefectFilterInitializedRef.current = true
      return
    }

    setSelectedListDefectClasses((current) => current.filter((name) => optionNames.has(name)))
  }, [listDefectFilterOptions])

  const filteredCoils = useMemo(() => {
    const source = filterQmlCoilsByDefectClasses(
      qmlCurrentCoilList,
      selectedListDefectClasses,
      listDefectFilterEnabled,
    )
    const localKeyword = listMode === 'history' ? '' : keyword.trim().toLowerCase()
    return source.filter(
      (coil) =>
        localKeyword.length === 0 ||
        coil.coilNo?.toLowerCase().includes(localKeyword) ||
        String(coil.id).includes(localKeyword),
    )
  }, [keyword, listDefectFilterEnabled, listMode, qmlCurrentCoilList, selectedListDefectClasses])

  const changeKeepLatest = (checked: boolean) => {
    setAutoKeepLatestTicks(0)
    setKeepLatest(checked)
  }

  const selectCoilFromList = (coil: CoilData) => {
    setCurrentCoil(coil)
    changeKeepLatest(false)
  }

  const exitHistoryListMode = () => {
    pendingHistorySelectionRef.current = false
    setKeyword('')
    setListMode('realtime')
    setCurrentCoil(coilList[0] ?? null)
  }

  useEffect(() => {
    if (!returnRealtimeCommand) return
    if (handledReturnRealtimeCommandRef.current === returnRealtimeCommand.serial) return
    handledReturnRealtimeCommandRef.current = returnRealtimeCommand.serial
    exitHistoryListMode()
  }, [returnRealtimeCommand])

  const selectQmlListMode = (nextMode: CoilListMode) => {
    pendingHistorySelectionRef.current = false
    setListMode(nextMode)
    const nextList = selectVisibleCoilList(nextMode, coilList, historyCoils)
    setCurrentCoil(nextList[0] ?? null)
  }

  const switchQmlListMode = () => {
    selectQmlListMode(listMode === 'realtime' ? 'history' : 'realtime')
  }

  const toggleListDefectClass = (className: string, checked: boolean) => {
    setSelectedListDefectClasses((current) => {
      if (checked) return current.includes(className) ? current : [...current, className]
      return current.filter((name) => name !== className)
    })
  }

  const selectAllListDefectClasses = () => {
    setSelectedListDefectClasses(listDefectFilterOptions.map((option) => option.name))
  }

  const clearListDefectClasses = () => {
    setSelectedListDefectClasses([])
  }

  const applySearchResults = (nextResults: CoilData[]) => {
    const nextHistory = buildQmlHistoryCoilList(nextResults)
    pendingHistorySelectionRef.current = true
    changeKeepLatest(false)
    setHistoryCoils(nextHistory)
    setListMode('history')
    setCurrentCoil(nextHistory[0] ?? null)
    if (nextResults.length === 0) {
      message.info('未找到匹配卷材')
    }
  }

  const runBackendSearch = async () => {
    if (searchMode === 'date') {
      const request = resolveQmlDateRangeSearch(
        dateRange ? [dateRange[0]?.toDate() ?? null, dateRange[1]?.toDate() ?? null] : null
      )
      if (request.kind === 'none') {
        message.warning('请选择完整时间范围')
        return
      }

      setIsSearching(true)
      try {
        const result = await coilApi.searchByDateTime(request.start, request.end)
        applySearchResults(result.data)
      } catch {
        setHistoryCoils([])
        setListMode('history')
        message.error('卷材查询失败')
      } finally {
        setIsSearching(false)
      }
      return
    }

    const request = resolveCoilSearch(keyword, searchMode)
    if (request.kind === 'none') {
      setListMode('realtime')
      return
    }

    setIsSearching(true)
    try {
      if (request.kind === 'id') {
        const result = await coilApi.searchByCoilId(request.coilId)
        let rows = result.data
        if (rows.length === 0) {
          try {
            const detailRow = await coilApi.getCoilDetail(request.coilId)
            rows = buildSearchResultsWithDetailFallback(request, rows, detailRow)
          } catch {
            rows = []
          }
        }
        applySearchResults(rows)
      } else {
        const result = await coilApi.searchByCoilNo(request.text)
        applySearchResults(result.data)
      }
    } catch {
      setHistoryCoils([])
      setListMode('history')
      message.error('卷材查询失败')
    } finally {
      setIsSearching(false)
    }
  }

  const clearSearchAndRefresh = () => {
    setKeyword('')
    pendingHistorySelectionRef.current = false
    const [start, end] = getQmlCurrentDayRange()
    setDateRange([dayjs(start), dayjs(end)])
    setListMode('realtime')
    setCurrentCoil(coilList[0] ?? null)
    refetch()
  }

  const refreshQmlCoilList = () => {
    clearSearchAndRefresh()
  }

  const copyCoilField = async (coil: CoilData, field: CoilCopyField, label: string) => {
    if (await copyTextToClipboard(getCoilCopyText(coil, field))) {
      message.success(`已复制${label}`)
      return
    }

    message.error(`${label}复制失败`)
  }

  const copyCurrentCoilField = async (field: CoilCopyField, label: string) => {
    if (!currentCoil) return

    await copyCoilField(currentCoil, field, label)
  }

  const openCoilRawData = (coil: CoilData) => {
    void openQmlExternalUrl(coilApi.getSearchByCoilIdUrl(coil.id))
  }

  const openCurrentCoilRawData = () => {
    if (!currentCoil) return
    openCoilRawData(currentCoil)
  }

  const openCoilListDataSource = () => {
    void openQmlExternalUrl(
      resolveQmlCoilListDataSourceUrl(
        getApiRequestHistory(),
        buildCoilListDataSourceUrl(80, serviceBaseUrls.apiBaseUrl),
      ),
    )
  }

  const getCoilSaveFolderUrl = (coil: CoilData, targetSurface: SurfaceKey) => {
    return buildCoilSaveFolderUrl({
      coilId: coil.id,
      surfaceKey: targetSurface,
      saveFolder: getSurfaceSaveFolder(infoData, targetSurface),
      serverHost: window.location.hostname,
    })
  }

  const copyCoilSaveFolder = async (coil: CoilData, targetSurface: SurfaceKey) => {
    const url = getCoilSaveFolderUrl(coil, targetSurface)
    const label = `${targetSurface}端保存位置`
    if (await copyTextToClipboard(buildCoilSaveFolderPath(url))) {
      message.success(`已复制${label}`)
      return
    }

    message.error(`${label}复制失败`)
  }

  const copyCurrentCoilSaveFolder = async (targetSurface: SurfaceKey) => {
    if (!currentCoil) return

    await copyCoilSaveFolder(currentCoil, targetSurface)
  }

  const openCoilSaveFolder = (coil: CoilData, targetSurface: SurfaceKey) => {
    const url = getCoilSaveFolderUrl(coil, targetSurface)
    void openCoilSaveFolderUrl(url)
  }

  const openCurrentCoilSaveFolder = (targetSurface: SurfaceKey) => {
    if (!currentCoil) return
    openCoilSaveFolder(currentCoil, targetSurface)
  }

  const generateClipMaxImages = async (targetSurface: SurfaceKey, sourceCoil = currentCoil) => {
    if (!sourceCoil) return

    setClipMaxSurface(targetSurface)
    try {
      const folderUrl = await runClipMaxAndGetFolderUrl({
        coilId: sourceCoil.id,
        surfaceKey: targetSurface,
        saveFolder: getSurfaceSaveFolder(infoData, targetSurface),
        serverHost: window.location.hostname,
        clipMaxImage: imageToolApi.clipMaxImage,
      })
      message.success(`已生成${targetSurface}端分割小图`)
      void openCoilSaveFolderUrl(folderUrl)
    } catch {
      message.error(`${targetSurface}端分割小图生成失败`)
    } finally {
      setClipMaxSurface(null)
    }
  }

  const rejoinCoilArea = async (coil: CoilData) => {
    setIsRejoiningArea(true)
    try {
      await area2dApi.rejoin(coil.id)
      message.success('已提交AREA图像重新拼接')
    } catch {
      message.error('AREA图像重新拼接提交失败')
    } finally {
      setIsRejoiningArea(false)
    }
  }

  const rejoinCurrentArea = async () => {
    if (!currentCoil) return

    await rejoinCoilArea(currentCoil)
  }

  const setCoilCheckStatus = async (coil: CoilData, status: CoilCheckStatus) => {
    setIsSettingCoilCheck(true)
    try {
      const msg = currentCoil?.id === coil.id ? coilCheckMsg : ''
      const payload = buildCoilCheckPayload(coil.id, status, msg)
      await coilApi.setCoilStatus(payload.coilId, payload.status, payload.msg)
      if (currentCoil?.id === coil.id) {
        setLocalCoilCheck(payload)
      }
      message.success('判级已更新')
      refetchCoilCheck()
      refetch()
    } catch {
      message.error('判级更新失败')
    } finally {
      setIsSettingCoilCheck(false)
    }
  }

  const setCurrentCoilCheckStatus = async (status: CoilCheckStatus) => {
    if (!currentCoil) return

    await setCoilCheckStatus(currentCoil, status)
  }

  const openReDetection = (range: ReDetectionRange) => {
    setReDetectionRange(range)
    setReDetectionOpen(true)
  }

  const openListBackupImage = () => {
    setBackupImageOpen(true)
  }

  const openListReDetection = () => {
    openReDetection(getCoilListReDetectionRange(filteredCoils))
  }

  const openListValueChange = () => {
    setListValueChangeOpen(true)
  }

  const startReDetection = async () => {
    setIsStartingReDetection(true)
    try {
      const socket = reDetectionSocketRef.current
      setReDetectionWsStatus({ running: true, progress: 0, total: 0, pending: 0 })
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(buildReDetectionWebSocketStartMessage(reDetectionRange, reDetectionFolder))
        message.success('已启动重新识别')
        return
      }

    await runtimeApi.startReDetection(reDetectionRange.fromId, reDetectionRange.toId)
    message.success('已启动重新识别')
    refetchReDetectionStatus()
  } catch {
    setReDetectionWsStatus({ error: '重新识别启动失败' })
    message.error('重新识别启动失败')
  } finally {
      setIsStartingReDetection(false)
    }
  }

  const reconnectReDetectionSocket = () => {
    reDetectionSocketRef.current?.close()
    setReDetectionWsReady(false)
    setReDetectionWsStatus(null)
    setReDetectionReconnectSerial((serial) => serial + 1)
    refetchReDetectionStatus()
  }

  const reDetectionStatusSource = reDetectionWsStatus ?? reDetectionStatusData
  const reDetectionStatus = buildReDetectionStatusView(reDetectionStatusSource)
  const reDetectionStartDisabled = reDetectionRange.fromId <= 0 || reDetectionRange.toId <= 0
  const imageServiceHealthOk = imageServiceHealthError
    ? false
    : imageServiceHealth
      ? readImageServiceHealthOk(imageServiceHealth)
      : undefined
  const alarmRows = buildOperationSidebarAlarmRows({ imageHealthOk: imageServiceHealthOk })
  const sidebarApiDelayView = buildApiDelayView(sidebarApiDelayQuery.isError ? -1 : sidebarApiDelayQuery.data)
  const sidebarApiDelayText = sidebarApiDelayView.label.startsWith('API ')
    ? sidebarApiDelayView.label.slice(4)
    : sidebarApiDelayView.label
  const listTitle = listMode === 'history' ? `历史: ${historyCoils.length}` : `实时: ${coilList.length}`
  const listCurrentCoil = currentCoil ? {
    coilNo: currentCoil.coilNo,
    coilId: currentCoil.id,
  } : null
  const qmlSearchPanelHeight = getQmlSearchPanelHeight(searchMode)
  const buildQmlListToolMenuItems = (): MenuProps['items'] => [
    {
      key: 'switch-list-mode',
      label: listMode === 'realtime' ? '>历史模式' : '>实时模式',
      onClick: switchQmlListMode,
    },
    {
      key: 'data-source',
      label: '查看数据源',
      onClick: openCoilListDataSource,
    },
    {
      key: 'backup-image',
      label: '图像备份',
      disabled: filteredCoils.length === 0,
      onClick: openListBackupImage,
    },
    {
      key: 're-detect-all',
      label: '全部重新识别',
      disabled: filteredCoils.length === 0,
      onClick: openListReDetection,
    },
    {
      key: 'list-value-change',
      label: '变化曲线',
      disabled: filteredCoils.length === 0,
      onClick: openListValueChange,
    },
  ]
  const buildQmlDataListItemMenu = (coil: CoilData): MenuProps['items'] => {
    const rowCoilCheckStatus = resolveQmlCoilCheckStatus(coil.raw)

    return [
      {
        key: 'copy-coil-no-root',
        label: '复制卷号',
        onClick: () => void copyCoilField(coil, 'coilNo', '卷号'),
      },
      {
        key: 'open',
        label: '打开...',
        children: [
          {
            key: 'open-save-s',
            label: '打开 S端 保存位置',
            onClick: () => openCoilSaveFolder(coil, 'S'),
          },
          {
            key: 'open-save-l',
            label: '打开 L端 保存位置',
            onClick: () => openCoilSaveFolder(coil, 'L'),
          },
          { type: 'divider' },
          {
            key: 'copy-save-location',
            label: '复制保存位置',
            children: [
              {
                key: 'copy-save-s',
                label: 'S端',
                onClick: () => void copyCoilSaveFolder(coil, 'S'),
              },
              {
                key: 'copy-save-l',
                label: 'L端',
                onClick: () => void copyCoilSaveFolder(coil, 'L'),
              },
            ],
          },
        ],
      },
      {
        key: 'copy',
        label: '复制...',
        children: [
          {
            key: 'copy-coil-no',
            label: '卷号',
            onClick: () => void copyCoilField(coil, 'coilNo', '卷号'),
          },
          {
            key: 'copy-coil-id',
            label: '流水号',
            onClick: () => void copyCoilField(coil, 'coilId', '流水号'),
          },
          {
            key: 'copy-coil-time',
            label: '时间',
            onClick: () => void copyCoilField(coil, 'dateTime', '时间'),
          },
        ],
      },
      {
        key: 'judge',
        label: '判断',
        children: COIL_CHECK_OPTIONS.map((option) => ({
          key: `judge-${option.status}`,
          label: buildQmlCoilCheckMenuLabel(option, rowCoilCheckStatus === option.status),
        })),
      },
      {
        key: 'tools',
        label: '工具',
        children: [
          {
            key: 'clip-max',
            label: '分割小图',
            children: [
              {
                key: 'clip-max-s',
                label: 'S端',
                onClick: () => void generateClipMaxImages('S', coil),
              },
              {
                key: 'clip-max-l',
                label: 'L端',
                onClick: () => void generateClipMaxImages('L', coil),
              },
            ],
          },
          {
            key: 'rejoin-area',
            label: '重新拼接AREA图像',
            onClick: () => void rejoinCoilArea(coil),
          },
          {
            key: 're-detect-current',
            label: '重新检测该卷',
            onClick: () => openReDetection(getCurrentCoilReDetectionRange(coil)),
          },
          {
            key: 're-detect-all',
            label: '全部重新识别',
            onClick: () => openReDetection(getCoilListReDetectionRange(filteredCoils)),
          },
          {
            key: 'raw-data',
            label: '查看原始返回数据',
            onClick: () => openCoilRawData(coil),
          },
        ],
      },
    ]
  }

  return (
    <>
    <aside className="operation-sidebar">
      <section className="sidebar-section current-coil">
        <div className="section-title">当前卷材</div>
        <div className="coil-primary">{currentCoil?.coilNo ?? '未选择'}</div>
        <div className="current-coil-actions">
          <Tooltip title="复制卷号">
            <Button
              aria-label="复制卷号"
              size="small"
              icon={<CopyOutlined />}
              disabled={!currentCoil}
              onClick={() => copyCurrentCoilField('coilNo', '卷号')}
            />
          </Tooltip>
          <Tooltip title="复制流水号">
            <Button
              aria-label="复制流水号"
              size="small"
              icon={<CopyOutlined />}
              disabled={!currentCoil}
              onClick={() => copyCurrentCoilField('coilId', '流水号')}
            />
          </Tooltip>
          <Tooltip title="复制时间">
            <Button
              aria-label="复制时间"
              size="small"
              icon={<ClockCircleOutlined />}
              disabled={!currentCoil}
              onClick={() => copyCurrentCoilField('dateTime', '时间')}
            />
          </Tooltip>
          <Tooltip title="查看原始返回数据">
            <Button
              aria-label="查看原始返回数据"
              size="small"
              icon={<LinkOutlined />}
              disabled={!currentCoil}
              onClick={openCurrentCoilRawData}
            />
          </Tooltip>
          <Tooltip title="更多信息">
            <Button
              aria-label="更多信息"
              size="small"
              icon={<InfoCircleOutlined />}
              disabled={!currentCoil}
              onClick={() => setCurrentDetailOpen(true)}
            />
          </Tooltip>
          <Tooltip title="复制 S端保存位置">
            <Button
              aria-label="复制 S端保存位置"
              size="small"
              icon={<CopyOutlined />}
              disabled={!currentCoil}
              onClick={() => copyCurrentCoilSaveFolder('S')}
            />
          </Tooltip>
          <Tooltip title="复制 L端保存位置">
            <Button
              aria-label="复制 L端保存位置"
              size="small"
              icon={<CopyOutlined />}
              disabled={!currentCoil}
              onClick={() => copyCurrentCoilSaveFolder('L')}
            />
          </Tooltip>
          <Tooltip title="打开 S端保存位置">
            <Button
              aria-label="打开 S端保存位置"
              size="small"
              icon={<FolderOpenOutlined />}
              disabled={!currentCoil}
              onClick={() => openCurrentCoilSaveFolder('S')}
            />
          </Tooltip>
          <Tooltip title="打开 L端保存位置">
            <Button
              aria-label="打开 L端保存位置"
              size="small"
              icon={<FolderOpenOutlined />}
              disabled={!currentCoil}
              onClick={() => openCurrentCoilSaveFolder('L')}
            />
          </Tooltip>
          <Tooltip title="生成 S端分割小图">
            <Button
              aria-label="生成 S端分割小图"
              size="small"
              icon={<ScissorOutlined />}
              loading={clipMaxSurface === 'S'}
              disabled={!currentCoil || clipMaxSurface !== null}
              onClick={() => generateClipMaxImages('S')}
            />
          </Tooltip>
          <Tooltip title="生成 L端分割小图">
            <Button
              aria-label="生成 L端分割小图"
              size="small"
              icon={<ScissorOutlined />}
              loading={clipMaxSurface === 'L'}
              disabled={!currentCoil || clipMaxSurface !== null}
              onClick={() => generateClipMaxImages('L')}
            />
          </Tooltip>
          <Tooltip title="重新拼接AREA图像">
            <Button
              aria-label="重新拼接AREA图像"
              size="small"
              icon={<SyncOutlined />}
              loading={isRejoiningArea}
              disabled={!currentCoil || isRejoiningArea}
              onClick={rejoinCurrentArea}
            />
          </Tooltip>
          <Tooltip title="重新检测该卷">
            <Button
              aria-label="重新检测该卷"
              size="small"
              icon={<PlayCircleOutlined />}
              disabled={!currentCoil}
              onClick={() => openReDetection(getCurrentCoilReDetectionRange(currentCoil))}
            />
          </Tooltip>
          <Tooltip title="全部重新识别">
            <Button
              aria-label="全部重新识别"
              size="small"
              icon={<SyncOutlined />}
              disabled={filteredCoils.length === 0}
              onClick={() => openReDetection(getCoilListReDetectionRange(filteredCoils))}
            />
          </Tooltip>
        </div>
        <div className="coil-meta-grid">
          <span>ID</span>
          <strong>{currentCoil?.id ?? '--'}</strong>
          <span>表面</span>
          <Select
            size="small"
            value={surfaceKey}
            onChange={setSurfaceKey}
            options={[
              { value: 'S', label: 'S 面' },
              { value: 'L', label: 'L 面' },
            ]}
          />
          <span>状态</span>
          <Tag color={statusColor(currentCoil?.status ?? 0)}>{statusText(currentCoil?.status ?? 0)}</Tag>
        </div>
      </section>

      <section className="sidebar-section grade-panel">
        <div className="section-title">判级</div>
        <div className="grade-row">
          <Badge status={coilCheck.status === 2 ? 'error' : coilCheck.status === 1 ? 'success' : 'warning'} />
          <span>{coilCheckOption.label}</span>
          <Tag color={coilCheckOption.color}>{currentCoil?.status === 3 ? '异常卷' : '正常监控'}</Tag>
        </div>
        <div className="coil-check-panel">
          <div className="coil-check-buttons">
            {COIL_CHECK_OPTIONS.map((option) => (
              <Button
                key={option.status}
                size="small"
                type={coilCheck.status === option.status ? 'primary' : 'default'}
                danger={option.status === 2}
                disabled={!currentCoil || isSettingCoilCheck}
                loading={isSettingCoilCheck && coilCheck.status === option.status}
                onClick={() => setCurrentCoilCheckStatus(option.status)}
              >
                {option.label}
              </Button>
            ))}
          </div>
          <Input.TextArea
            className="coil-check-message"
            rows={2}
            value={coilCheckMsg}
            placeholder="判级备注"
            disabled={!currentCoil}
            onChange={(event) => setCoilCheckMsg(event.target.value)}
          />
        </div>
        <div className="grade-metrics">
          <div>
            <span>平整度</span>
            <strong>{currentCoil?.grade ?? '--'}</strong>
          </div>
          <div>
            <span>S缺陷</span>
            <strong>{currentCoil?.defectCountS ?? '--'}</strong>
          </div>
          <div>
            <span>L缺陷</span>
            <strong>{currentCoil?.defectCountL ?? '--'}</strong>
          </div>
        </div>
      </section>

      <section className="sidebar-section alarm-panel">
        <div className="section-title">报警</div>
        <div className="alarm-list">
          {alarmRows.map((row) => (
            <div className={`alarm-item ${row.state}`} key={row.key} title={row.title}>
              {row.label}
            </div>
          ))}
        </div>
      </section>

      <section
        className="sidebar-section search-panel"
        data-qml-search-panel-height={qmlSearchPanelHeight}
        style={{ '--qml-search-panel-height': `${qmlSearchPanelHeight}px` } as CSSProperties}
      >
        <div className="section-title search-title-row">
          <span>查询</span>
          <div className="search-title-actions">
            <Select<SearchMode>
              size="small"
              className="search-mode-combo"
              data-qml-search-mode-combo
              value={searchMode}
              options={[
                { label: '卷号', value: 'coilNo' },
                { label: '时间', value: 'date' },
                { label: '流水号', value: 'coilId' },
              ]}
              onChange={setSearchMode}
            />
            <Tooltip title="筛选">
              <Button
                size="small"
                aria-label="筛选查询条件"
                data-qml-search-filter-button
                icon={<FilterOutlined />}
                onClick={() => setSearchFilterOpen(true)}
              />
            </Tooltip>
          </div>
        </div>
        {searchMode === 'coilNo' || searchMode === 'coilId' ? (
          <div className="search-text-line" data-qml-search-text-line={searchMode}>
            <span data-qml-search-text-label>{searchMode === 'coilId' ? '流水号:' : '卷号:'}</span>
            <Input
              allowClear
              size="small"
              className="search-text-input"
              placeholder={searchMode === 'coilId' ? '请输入流水号' : '请输入卷号'}
              value={keyword}
              onChange={(event) => {
                setKeyword(event.target.value)
                if (event.target.value.trim().length === 0) {
                  setListMode('realtime')
                }
              }}
              onPressEnter={runBackendSearch}
            />
            <Button
              size="small"
              className="search-text-submit"
              data-qml-search-text-submit
              autoInsertSpace={false}
              loading={isSearching}
              onClick={runBackendSearch}
            >
              查询
            </Button>
          </div>
        ) : (
          <div className="search-date-lines" data-qml-search-date-lines>
            <label className="search-date-line" data-qml-search-date-line="start">
              <span>起始:</span>
              <div className="search-date-segments">
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="year"
                  onClick={() => setOpenSearchDatePicker('start')}
                >
                  {formatSearchDatePart(dateRange?.[0] ?? null, 'year')}
                </button>
                <span className="search-date-unit">年</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="month"
                  onClick={() => setOpenSearchDatePicker('start')}
                >
                  {formatSearchDatePart(dateRange?.[0] ?? null, 'month')}
                </button>
                <span className="search-date-unit">月</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="day"
                  onClick={() => setOpenSearchDatePicker('start')}
                >
                  {formatSearchDatePart(dateRange?.[0] ?? null, 'day')}
                </button>
                <span className="search-date-unit">日</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="hour"
                  onClick={() => setOpenSearchDatePicker('start')}
                >
                  {formatSearchDatePart(dateRange?.[0] ?? null, 'hour')}
                </button>
                <span className="search-date-unit">时</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="minute"
                  onClick={() => setOpenSearchDatePicker('start')}
                >
                  {formatSearchDatePart(dateRange?.[0] ?? null, 'minute')}
                </button>
                <span className="search-date-unit">分</span>
              </div>
              <DatePicker
                className="search-date-picker"
                classNames={SEARCH_DATE_PICKER_CLASS_NAMES}
                size="small"
                format="YYYY-MM-DD HH:mm"
                showTime={{ format: 'HH:mm' }}
                open={openSearchDatePicker === 'start'}
                value={dateRange?.[0] ?? null}
                onOpenChange={(open) => setOpenSearchDatePicker(open ? 'start' : null)}
                onChange={(value) => setDateRange((range) => [value, range?.[1] ?? null])}
              />
            </label>
            <label className="search-date-line" data-qml-search-date-line="end">
              <span>结束:</span>
              <div className="search-date-segments">
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="year"
                  onClick={() => setOpenSearchDatePicker('end')}
                >
                  {formatSearchDatePart(dateRange?.[1] ?? null, 'year')}
                </button>
                <span className="search-date-unit">年</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="month"
                  onClick={() => setOpenSearchDatePicker('end')}
                >
                  {formatSearchDatePart(dateRange?.[1] ?? null, 'month')}
                </button>
                <span className="search-date-unit">月</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="day"
                  onClick={() => setOpenSearchDatePicker('end')}
                >
                  {formatSearchDatePart(dateRange?.[1] ?? null, 'day')}
                </button>
                <span className="search-date-unit">日</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="hour"
                  onClick={() => setOpenSearchDatePicker('end')}
                >
                  {formatSearchDatePart(dateRange?.[1] ?? null, 'hour')}
                </button>
                <span className="search-date-unit">时</span>
                <button
                  type="button"
                  className="search-date-part"
                  data-qml-search-date-part="minute"
                  onClick={() => setOpenSearchDatePicker('end')}
                >
                  {formatSearchDatePart(dateRange?.[1] ?? null, 'minute')}
                </button>
                <span className="search-date-unit">分</span>
              </div>
              <DatePicker
                className="search-date-picker"
                classNames={SEARCH_DATE_PICKER_CLASS_NAMES}
                size="small"
                format="YYYY-MM-DD HH:mm"
                showTime={{ format: 'HH:mm' }}
                open={openSearchDatePicker === 'end'}
                value={dateRange?.[1] ?? null}
                onOpenChange={(open) => setOpenSearchDatePicker(open ? 'end' : null)}
                onChange={(value) => setDateRange((range) => [range?.[0] ?? null, value])}
              />
            </label>
            <div className="search-date-action-row">
              <Button
                size="small"
                className="search-text-submit"
                data-qml-search-date-submit
                autoInsertSpace={false}
                loading={isSearching}
                onClick={runBackendSearch}
              >
                查询
              </Button>
            </div>
          </div>
        )}
      </section>

      <section className="sidebar-section coil-list-section">
        <Dropdown
          trigger={['contextMenu']}
          menu={{ items: buildQmlListToolMenuItems(), triggerSubMenuAction: 'click' }}
        >
          <div className="section-title list-title-row">
            <span className={`list-title-count ${listMode}`}>{listTitle}</span>
            {listCurrentCoil ? (
              <span className="list-current-coil" title={`${listCurrentCoil.coilNo} ${listCurrentCoil.coilId}`}>
                <strong>{listCurrentCoil.coilNo}</strong>
                <span>{listCurrentCoil.coilId}</span>
              </span>
            ) : null}
            {listMode === 'history' ? (
              <Button size="small" aria-label="退出历史模式" onClick={exitHistoryListMode}>
                退出
              </Button>
            ) : null}
            <Tooltip title="筛选">
              <Button
                aria-label="筛选"
                size="small"
                type={listDefectFilterEnabled ? 'primary' : 'default'}
                icon={<FilterOutlined />}
                onClick={() => setListDefectFilterEnabled((enabled) => !enabled)}
              />
            </Tooltip>
            <Tooltip title="刷新">
              <Button
                aria-label="刷新列表"
                size="small"
                icon={<ReloadOutlined />}
                loading={isFetching}
                onClick={refreshQmlCoilList}
              />
            </Tooltip>
          </div>
        </Dropdown>
        {listDefectFilterEnabled ? (
          <div
            className="list-defect-filter-panel"
            data-list-defect-filter-enabled="true"
            data-list-defect-filter-count={selectedListDefectClasses.length}
          >
            <div className="list-defect-filter-classes">
              {listDefectFilterOptions.length === 0 ? (
                <span className="list-defect-filter-empty">暂无缺陷类别</span>
              ) : (
                listDefectFilterOptions.map((option) => (
                  <Checkbox
                    key={option.name}
                    checked={selectedListDefectClasses.includes(option.name)}
                    onChange={(event) => toggleListDefectClass(option.name, event.target.checked)}
                  >
                    <span className="list-defect-filter-name">{option.name}</span>
                  </Checkbox>
                ))
              )}
            </div>
            <div className="list-defect-filter-actions">
              <Button size="small" onClick={clearListDefectClasses}>
                取消
              </Button>
              <Button size="small" onClick={selectAllListDefectClasses}>
                全选
              </Button>
            </div>
          </div>
        ) : null}
        <div className="sidebar-coil-list" style={{ paddingRight: 0 }}>
          <div className="list-column-header" aria-label="卷材列表列标题" style={{ gridTemplateColumns: QML_LIST_COLUMN_GRID }}>
            <span>Id</span>
            <span>卷号</span>
            <span>钢种</span>
            <span>缺陷/最严重</span>
          </div>
          {(isFetching && coilList.length === 0) || isSearching ? (
            <div className="sidebar-loading">
              <Spin size="small" />
            </div>
          ) : filteredCoils.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={listMode === 'history' ? '暂无历史结果' : '暂无数据'} />
          ) : (
            filteredCoils.map((coil: CoilData) => (
              <Dropdown
                key={coil.id}
                trigger={['contextMenu']}
                menu={{ items: buildQmlDataListItemMenu(coil), triggerSubMenuAction: 'click' }}
              >
                <button
                  type="button"
                  className={`sidebar-coil-item ${currentCoil?.id === coil.id ? 'selected' : ''}`}
                  style={{ gridTemplateColumns: QML_LIST_COLUMN_GRID }}
                  onClick={() => selectCoilFromList(coil)}
                >
                  <span className="coil-current-accent" aria-hidden="true" />
                  <span className="coil-id">{coil.id}</span>
                  <span className={`coil-no ${getQmlCoilCheckStatusClass(coil.raw)}`}>{coil.coilNo}</span>
                  <span className="coil-grade">{coil.grade ?? '--'}</span>
                  <span
                    className={`coil-defect-summary ${getQmlListCoilDefectLevelClass(coil)}`}
                    title={buildQmlListCoilDefectTip(coil)}
                  >
                    {formatQmlListCoilDefectStatus(coil)}
                  </span>
                </button>
              </Dropdown>
            ))
          )}
        </div>
      </section>
      <footer
        className="sidebar-foot-view"
        data-qml-left-foot-view
        data-qml-api-url={serviceBaseUrls.apiBaseUrl}
        data-qml-api-delay-state={sidebarApiDelayView.state}
      >
        <button
          className={`sidebar-foot-api-url ${sidebarApiDelayView.state}`}
          type="button"
          title={serviceBaseUrls.apiBaseUrl}
          data-qml-footer-connect-server-url
          onClick={onOpenConnectSettings}
        >
          {serviceBaseUrls.apiBaseUrl}
        </button>
        <span className="sidebar-foot-delay-label">延时：</span>
        <span className={`sidebar-foot-delay-value ${sidebarApiDelayView.state}`} title={sidebarApiDelayView.title}>
          {sidebarApiDelayText}
        </span>
        <span className="sidebar-foot-spacer" aria-hidden="true" />
        <Checkbox
          className="sidebar-foot-keep-latest"
          data-qml-footer-keep-latest
          checked={keepLatest}
          onChange={(event) => changeKeepLatest(event.target.checked)}
        >
          保持最新
        </Checkbox>
      </footer>
    </aside>
    <CurrentCoilDetailModal
      open={currentDetailOpen}
      coil={currentCoil}
      onClose={() => setCurrentDetailOpen(false)}
    />
    <BackupImageModal open={backupImageOpen} coilList={filteredCoils} onClose={() => setBackupImageOpen(false)} />
    <ListValueChangeModal
      open={listValueChangeOpen}
      coilList={filteredCoils}
      onClose={() => setListValueChangeOpen(false)}
    />
    <Modal
      className="search-filter-modal"
      title={null}
      open={searchFilterOpen}
      width={350}
      footer={null}
      onCancel={() => setSearchFilterOpen(false)}
      destroyOnHidden={false}
    >
      <section className="search-filter-popup" data-qml-search-filter-popup>
        <h3>查询条件</h3>
        <div className="search-filter-popup-body" />
        <div className="search-filter-popup-actions">
          <Button className="search-filter-reset" autoInsertSpace={false}>
            重置
          </Button>
          <Button className="search-filter-confirm" autoInsertSpace={false}>
            确认
          </Button>
        </div>
      </section>
    </Modal>
    <Modal
      title={null}
      open={reDetectionOpen}
      width={590}
      footer={null}
      onCancel={() => setReDetectionOpen(false)}
      destroyOnHidden
    >
      <div className="re-detection-form" data-qml-re-detection-view>
        <div className="re-detection-header">
          <h3 className="re-detection-title" data-qml-re-detection-title>
            重新识别
          </h3>
          {reDetectionStatus.error ? (
            <Button size="small" onClick={reconnectReDetectionSocket}>
              重新连接
            </Button>
          ) : null}
        </div>
        <label className="re-detection-row">
          <span>起始流水号</span>
          <InputNumber
            min={0}
            disabled={!reDetectionStatus.canChange}
            value={reDetectionRange.fromId}
            onChange={(value) => setReDetectionRange((range) => ({ ...range, fromId: Number(value ?? 0) }))}
          />
        </label>
        <label className="re-detection-row">
          <span>结束流水号</span>
          <InputNumber
            min={0}
            disabled={!reDetectionStatus.canChange}
            value={reDetectionRange.toId}
            onChange={(value) => setReDetectionRange((range) => ({ ...range, toId: Number(value ?? 0) }))}
          />
        </label>
        <div className="re-detection-action-row">
          <div className="re-detection-status">
            {reDetectionStatus.error ? (
              <span className="re-detection-error">{reDetectionStatus.error}</span>
            ) : reDetectionStatus.showProgress ? (
              <>
                <Progress percent={reDetectionStatus.percent} status={reDetectionStatus.running ? 'active' : 'normal'} />
                <div>
                  <Tag color={reDetectionStatus.color}>{reDetectionStatus.label}</Tag>
                  <span>
                    总数 {reDetectionStatus.total} / 待处理 {reDetectionStatus.pending}
                  </span>
                </div>
              </>
            ) : (
              null
            )}
          </div>
          {!reDetectionStatus.error ? (
            <Button
              className="re-detection-start-button"
              type="primary"
              loading={isStartingReDetection}
              disabled={reDetectionStartDisabled}
              onClick={startReDetection}
            >
              识别
            </Button>
          ) : null}
        </div>
      </div>
    </Modal>
    </>
  )
}
