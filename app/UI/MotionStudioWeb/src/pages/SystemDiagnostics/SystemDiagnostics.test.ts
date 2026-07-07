import { describe, expect, it } from 'vitest'

import systemDiagnosticsSource from './index.tsx?raw'

describe('SystemDiagnostics DetectionState websocket parity', () => {
  it('uses the QML DetectionState websocket as the primary server-state source', () => {
    expect(systemDiagnosticsSource).toContain('buildServerStateWsPath')
    expect(systemDiagnosticsSource).toContain('resolveServerStateWsUrl')
    expect(systemDiagnosticsSource).toContain('parseServerStateWebSocketMessage')
    expect(systemDiagnosticsSource).toContain('new WebSocket(resolveServerStateWsUrl')
    expect(systemDiagnosticsSource).toContain('serverStateWsData ?? serverStateQuery.data')
  })

  it('keeps HTTP polling only as a fallback while the websocket is not ready', () => {
    expect(systemDiagnosticsSource).toContain('enabled: !serverStateWsReady')
    expect(systemDiagnosticsSource).toContain('refetchInterval: serverStateWsReady ? false : 1000')
  })
})

describe('SystemDiagnostics reDetection websocket parity', () => {
  it('uses the QML reDetection websocket as the primary re-detection source', () => {
    expect(systemDiagnosticsSource).toContain('buildReDetectionWsPath')
    expect(systemDiagnosticsSource).toContain('resolveReDetectionWsUrl')
    expect(systemDiagnosticsSource).toContain('parseReDetectionWebSocketMessage')
    expect(systemDiagnosticsSource).toContain('new WebSocket(resolveReDetectionWsUrl')
    expect(systemDiagnosticsSource).toContain('reDetectionWsStatus ?? reDetectionStatusQuery.data')
  })

  it('starts re-detection over websocket before falling back to HTTP', () => {
    expect(systemDiagnosticsSource).toContain('buildReDetectionWebSocketStartMessage(range, reDetectionFolder)')
    expect(systemDiagnosticsSource).toContain('socket.send(buildReDetectionWebSocketStartMessage(range, reDetectionFolder))')
    expect(systemDiagnosticsSource).toContain('enabled: !reDetectionWsReady')
    expect(systemDiagnosticsSource).toContain('refetchInterval: reDetectionWsReady ? false : 1000')
  })

  it('mirrors QML ReDetectionView websocket close, start, and failure status transitions', () => {
    const reDetectionEffectStart = systemDiagnosticsSource.indexOf('new WebSocket(resolveReDetectionWsUrl')
    const openHandlerStart = systemDiagnosticsSource.indexOf('socket.onopen = () =>', reDetectionEffectStart)
    const openHandlerEnd = systemDiagnosticsSource.indexOf('socket.onmessage =', openHandlerStart)
    const openHandlerSource = systemDiagnosticsSource.slice(openHandlerStart, openHandlerEnd)
    const closeHandlerStart = systemDiagnosticsSource.indexOf('socket.onclose = () =>', reDetectionEffectStart)
    const closeHandlerEnd = systemDiagnosticsSource.indexOf('return () =>', closeHandlerStart)
    const closeHandlerSource = systemDiagnosticsSource.slice(closeHandlerStart, closeHandlerEnd)
    const mutationStart = systemDiagnosticsSource.indexOf('const reDetectionStartMutation = useMutation')
    const mutationEnd = systemDiagnosticsSource.indexOf('const refreshAll = () =>', mutationStart)
    const mutationSource = systemDiagnosticsSource.slice(mutationStart, mutationEnd)

    expect(openHandlerSource).toContain('setReDetectionWsStatus({})')
    expect(closeHandlerSource).toContain("setReDetectionWsStatus({ error: '连接断开!' })")
    expect(mutationSource).toContain('setReDetectionWsStatus({ running: true, progress: 0, total: 0, pending: 0 })')
    expect(mutationSource.indexOf('setReDetectionWsStatus({ running: true')).toBeLessThan(
      mutationSource.indexOf('socket.send(buildReDetectionWebSocketStartMessage'),
    )
    expect(mutationSource).toContain("setReDetectionWsStatus({ error: '重新识别启动失败' })")
    expect(mutationSource.indexOf("setReDetectionWsStatus({ error: '重新识别启动失败' })")).toBeLessThan(
      mutationSource.indexOf("message.error('重新识别启动失败')"),
    )
  })

  it('mirrors QML ReDetectionView reconnect, canChange, and progress visibility in the diagnostics panel', () => {
    const reDetectionEffectStart = systemDiagnosticsSource.indexOf('new WebSocket(resolveReDetectionWsUrl')
    const reDetectionEffectEnd = systemDiagnosticsSource.indexOf('const syncMutation = useMutation', reDetectionEffectStart)
    const reDetectionEffectSource = systemDiagnosticsSource.slice(reDetectionEffectStart, reDetectionEffectEnd)
    const panelStart = systemDiagnosticsSource.indexOf('<section className="system-panel re-detection-panel">')
    const panelEnd = systemDiagnosticsSource.indexOf('<section className="system-panel server-state-panel">', panelStart)
    const panelSource = systemDiagnosticsSource.slice(panelStart, panelEnd)

    expect(systemDiagnosticsSource).toContain('const [reDetectionReconnectSerial, setReDetectionReconnectSerial] = useState(0)')
    expect(systemDiagnosticsSource).toContain('const reconnectReDetectionSocket = () =>')
    expect(systemDiagnosticsSource).toContain('setReDetectionReconnectSerial((serial) => serial + 1)')
    expect(reDetectionEffectSource).toContain('}, [reDetectionReconnectSerial])')
    expect(panelSource).toContain('disabled={!reDetectionStatus.canChange}')
    expect(panelSource).toContain('reDetectionStatus.showProgress ?')
    expect(panelSource).toContain('<Progress percent={reDetectionStatus.percent}')
    expect(panelSource).toContain('<Button size="small" onClick={reconnectReDetectionSocket}>')
    expect(panelSource).toContain('重新连接')
    expect(panelSource).toContain('!reDetectionStatus.error ? (')
  })
})

describe('SystemDiagnostics database backup parity', () => {
  it('offers a native save-path picker before running /save_to_sql like the QML backup menu', () => {
    expect(systemDiagnosticsSource).toContain('selectNativeSavePath')
    expect(systemDiagnosticsSource).toContain('chooseDatabaseBackupPath')
    expect(systemDiagnosticsSource).toContain('选择保存路径')
  })

  it('opens the selected backup target after /save_to_sql succeeds like QML Qt.openUrlExternally', () => {
    expect(systemDiagnosticsSource).toContain('openNativePath')
    expect(systemDiagnosticsSource).toContain('onSuccess: (result, path)')
    expect(systemDiagnosticsSource).toContain('void openNativePath(path)')
  })
})

describe('SystemDiagnostics network speedtest parity', () => {
  it('exposes a stable anchor for the QML tools menu network speedtest action', () => {
    expect(systemDiagnosticsSource).toContain('id="network-speedtest"')
    expect(systemDiagnosticsSource).toContain('useLocation')
    expect(systemDiagnosticsSource).toContain("location.hash !== '#network-speedtest'")
    expect(systemDiagnosticsSource).toContain("document.getElementById('network-speedtest')?.scrollIntoView")
    expect(systemDiagnosticsSource).toContain('上传测速')
  })

  it('opens the download speedtest URL through the shared QML external opener', () => {
    expect(systemDiagnosticsSource).toContain('const openSpeedtestDownload = () =>')
    expect(systemDiagnosticsSource).toContain('void openQmlExternalUrl(diagnosticApi.getSpeedtestDownloadUrl(1))')
    expect(systemDiagnosticsSource).toContain('onClick={openSpeedtestDownload}')
    expect(systemDiagnosticsSource).not.toContain('href={diagnosticApi.getSpeedtestDownloadUrl(1)}')
  })
})

describe('SystemDiagnostics API docs parity', () => {
  it('opens API docs through the shared QML external opener instead of a raw browser anchor', () => {
    expect(systemDiagnosticsSource).toContain("import { openQmlExternalUrl } from '@/utils/coilActions'")
    expect(systemDiagnosticsSource).toContain("void openQmlExternalUrl(joinBaseUrl(serviceBaseUrls.apiBaseUrl, '/docs'))")
    expect(systemDiagnosticsSource).toContain('onClick={openApiDocs}')
    expect(systemDiagnosticsSource).not.toContain('href="/api/docs" target="_blank"')
  })
})

describe('SystemDiagnostics 2D AREA status parity', () => {
  it('shows the active Rust area clip config beside queue status', () => {
    expect(systemDiagnosticsSource).toContain('const areaClipConfig = areaStatusView.clipConfig')
    expect(systemDiagnosticsSource).toContain('className="area2d-clip-config-row"')
    expect(systemDiagnosticsSource).toContain('当前裁剪')
    expect(systemDiagnosticsSource).toContain('模式 {areaClipConfig.mode}')
    expect(systemDiagnosticsSource).toContain('fixed {areaClipConfig.fixed}')
    expect(systemDiagnosticsSource).toContain('c {areaClipConfig.c}')
    expect(systemDiagnosticsSource).toContain('a {areaClipConfig.a}')
    expect(systemDiagnosticsSource).toContain('b {areaClipConfig.b}')
  })
})

describe('SystemDiagnostics PLC adapter info parity', () => {
  it('fetches and renders the startup-safe PLC adapter info route', () => {
    expect(systemDiagnosticsSource).toContain("queryKey: ['system', 'plcInfo']")
    expect(systemDiagnosticsSource).toContain('queryFn: plcApi.getInfo')
    expect(systemDiagnosticsSource).toContain('const plcInfo = asRecord(plcInfoQuery.data)')
    expect(systemDiagnosticsSource).toContain('PLC连接信息')
    expect(systemDiagnosticsSource).toContain("readText(plcInfo, ['plc_ip']")
    expect(systemDiagnosticsSource).toContain("readText(plcInfo, ['rack']")
    expect(systemDiagnosticsSource).toContain("readText(plcInfo, ['slot']")
    expect(systemDiagnosticsSource).toContain('plcTypeList.join')
  })
})
