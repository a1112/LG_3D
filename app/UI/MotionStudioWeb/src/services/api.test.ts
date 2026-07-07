import { describe, expect, it } from 'vitest'

import * as apiModule from './api'
import {
  buildAlg2dModelsPath,
  buildAreaRejoinPath,
  buildAreaRejoinPayload,
  buildAreaScanPath,
  buildAreaStatusPath,
  buildAlg2dTestProgressWsPath,
  buildAlg2dTestStartPath,
  buildAlg2dTestStopPath,
  buildClipConfigPath,
  buildBackupImageTaskPath,
  buildBackupImageTaskWsPath,
  buildSaveToSqlPath,
  buildCoilAlarmPath,
  buildDataHasPath,
  buildCoilDetailPath,
  buildCoilListValueChangeKeysPath,
  buildCoilStatePath,
  buildCoilStatusPath,
  buildClassifierImagePath,
  buildClipMaxImagePath,
  buildControlConfigPath,
  buildDatabaseInfoPath,
  buildSetControlConfigPath,
  buildSetControlPropertyPath,
  buildCoilDataAreaPath,
  buildCoilDataErrorPath,
  buildCoilDataRenderPath,
  buildDefaultCoilDataErrorPath,
  buildDefectAllPath,
  buildDefectImagePath,
  buildDefectDictAllPath,
  buildDefectDictPath,
  buildDefectsAllPath,
  buildDeleteManualDefectPath,
  buildDownloadTestPath,
  buildExport1hPath,
  buildExport24hPath,
  buildExportDataSimplePath,
  buildExportTodayPath,
  buildExportXlsxByDateTimePath,
  buildExportXlsxByIdPath,
  buildExportXlsxPath,
  buildFlushPath,
  buildHeightPointPath,
  buildHeightPointWsPath,
  buildHeightLinePath,
  buildHealthPath,
  buildHardwarePath,
  buildInfoPath,
  buildDelayPath,
  buildImageAreaPath,
  buildImagePreviewPath,
  buildImageSourcePath,
  buildCameraAdjustmentPath,
  buildCameraAdjustmentPayload,
  buildCameraAdjustPath,
  buildCameraStatusPath,
  buildCameraAlarmPath,
  buildCameraDataPath,
  buildCameraReconnectPath,
  buildCaptureStatusPath,
  buildCaptureStatusCompatPath,
  buildCaptureFilesPath,
  buildGetListenerAddFilePath,
  buildCamerasPath,
  buildCameraStatusByKeyPath,
  buildCameraFilesByKeyPath,
  buildCameraParamsPath,
  buildCameraReconnectCompatPath,
  buildCameraParamsByKeyPath,
  buildCameraReconnectByKeyPath,
  buildLineDataPath,
  buildManualDefectAddPath,
  buildManualDefectExportPath,
  buildManualDefectUpdatePath,
  buildManualDefectsPath,
  buildOpenApiPath,
  buildPointDataPath,
  buildPlcInfoPath,
  buildPlcConnectPath,
  buildPlcGetPath,
  buildPlcCurvePath,
  buildPlcCurveAllPath,
  buildReDetectionStartPath,
  buildReDetectionStatusPath,
  buildReDetectionWsPath,
  buildRuntimeInfoPath,
  buildServerStatePath,
  buildServerStateWsPath,
  buildSetCoilStatusPath,
  buildSetDefectDictPath,
  buildSearchCoilIdPath,
  buildSearchCoilNoPath,
  buildSearchDateTimePath,
  buildPlcDataPath,
  buildSpeedtestDownloadPath,
  buildSpeedtestUploadPath,
  buildSyncSummariesPath,
  buildSyncSummariesRangePath,
  buildSetTestModeBody,
  buildTestModePath,
  buildTestModeStatusPath,
  buildVersionPath,
  buildRuntimeConnectionBaseUrls,
  applyRuntimeConnectionSettings,
  buildRuntimeApiBaseUrl,
  applyApiBaseUrlOverride,
  joinBaseUrl,
  resolveImageRuntimeBaseUrl,
  resolveQmlSurfaceImageUrl,
  resolveServiceBaseUrls,
  serviceBaseUrls,
} from './api'

describe('api service url helpers', () => {
  it('joins relative proxy bases without double slashes', () => {
    expect(joinBaseUrl('/api/', '/coilList/20')).toBe('/api/coilList/20')
    expect(joinBaseUrl('/api', 'image/area/S/193113')).toBe('/api/image/area/S/193113')
  })

  it('joins absolute service bases without losing host information', () => {
    expect(joinBaseUrl('http://127.0.0.1:5011/', '/coilList/20')).toBe(
      'http://127.0.0.1:5011/coilList/20',
    )
  })

  it('allows image service to be split from the main api service', () => {
    const urls = resolveServiceBaseUrls({
      VITE_API_BASE_URL: '/api',
      VITE_IMAGE_BASE_URL: 'http://127.0.0.1:6013',
    })

    expect(urls.apiBaseUrl).toBe('/api')
    expect(urls.imageBaseUrl).toBe('http://127.0.0.1:6013')
  })

  it('resolves QML-compatible runtime image service base URLs', () => {
    const bases = resolveServiceBaseUrls({
      VITE_API_BASE_URL: '/api',
      VITE_IMAGE_BASE_URL: '/image-api',
    })

    expect(
      resolveImageRuntimeBaseUrl(
        {
          useRustImageServer: false,
          rustImageServerPort: 6013,
        },
        bases,
        '192.168.1.20',
      ),
    ).toBe('/api')
    expect(
      resolveImageRuntimeBaseUrl(
        {
          useRustImageServer: true,
          rustImageServerPort: 6025,
        },
        bases,
        '192.168.1.20',
      ),
    ).toBe('http://192.168.1.20:6025')
  })

  it('resolves QML shared-folder image URLs while keeping AREA on HTTP', () => {
    const settings = {
      useRustImageServer: false,
      rustImageServerPort: 6013,
      useSharedFolder: true,
      sharedFolderBaseName: 'Save_',
    }

    expect(resolveQmlSurfaceImageUrl(settings, 'S', 193113, 'GRAY', false, '/api', '10.0.0.8')).toBe(
      'file:////10.0.0.8/Save_S/193113/png/GRAY.png',
    )
    expect(resolveQmlSurfaceImageUrl(settings, 'L', 193113, 'JET', true, '/api', '10.0.0.8')).toBe(
      'file:////10.0.0.8/Save_L/193113/preView/JET.png',
    )
    expect(resolveQmlSurfaceImageUrl(settings, 'S', 193113, 'AREA', false, '/api', '10.0.0.8')).toBe(
      '/api/image/area/S/193113',
    )
    expect(resolveQmlSurfaceImageUrl(settings, 'S', 193113, 'AREA', true, '/api', '10.0.0.8')).toBe(
      '/api/image/preview/S/193113/AREA',
    )
    expect(resolveQmlSurfaceImageUrl(settings, 'S', 193113, 'AREA_MASK', false, '/api', '10.0.0.8')).toBe(
      '/api/image/area/S/193113/AREA_MASK',
    )
  })

  it('honors QML TopCoilTools MASK and QUICK image source switches', () => {
    expect(
      resolveQmlSurfaceImageUrl(
        {
          useRustImageServer: false,
          rustImageServerPort: 6013,
          imageMaskChecked: true,
          quickImageEnabled: true,
        },
        'S',
        193113,
        'GRAY',
        false,
        '/api',
        '10.0.0.8',
      ),
    ).toBe('/api/image/source/S/193113/GRAY?mask=true')

    expect(
      resolveQmlSurfaceImageUrl(
        {
          useRustImageServer: false,
          rustImageServerPort: 6013,
          imageMaskChecked: true,
          quickImageEnabled: true,
        },
        'S',
        193113,
        'AREA',
        false,
        '/api',
        '10.0.0.8',
      ),
    ).toBe('/api/image/area/S/193113/AREA_MASK')

    expect(
      resolveQmlSurfaceImageUrl(
        {
          useRustImageServer: false,
          rustImageServerPort: 6013,
          useSharedFolder: true,
          sharedFolderBaseName: 'Save_',
          imageMaskChecked: true,
          quickImageEnabled: true,
        },
        'L',
        193113,
        'JET',
        false,
        '/api',
        '10.0.0.8',
      ),
    ).toBe('file:////10.0.0.8/Save_L/193113/mask/JET.png')

    expect(
      resolveQmlSurfaceImageUrl(
        {
          useRustImageServer: false,
          rustImageServerPort: 6013,
          useSharedFolder: true,
          sharedFolderBaseName: 'Save_',
          imageMaskChecked: false,
          quickImageEnabled: true,
        },
        'L',
        193113,
        'JET',
        false,
        '/api',
        '10.0.0.8',
      ),
    ).toBe('file:////10.0.0.8/Save_L/193113/jpg/JET.jpg')
  })

  it('builds QML-compatible runtime api service base URLs', () => {
    expect(buildRuntimeApiBaseUrl({ serverIp: '127.0.0.1', serverPort: Number.NaN })).toBe(
      'http://127.0.0.1:5011',
    )
    expect(buildRuntimeApiBaseUrl({ serverIp: '127.0.0.1', serverPort: 5010 })).toBe(
      'http://127.0.0.1:5010',
    )
    expect(buildRuntimeApiBaseUrl({ serverIp: ' 192.168.99.100 ', serverPort: 70000 })).toBe(
      'http://192.168.99.100:65535',
    )
    expect(buildRuntimeApiBaseUrl({ serverIp: 'bad host; rm -rf', serverPort: 0 })).toBe(
      'http://127.0.0.1:1',
    )
  })

  it('builds complete runtime connection base URLs for all dependent services', () => {
    const next = buildRuntimeConnectionBaseUrls({
      serverIp: '192.168.99.100',
      serverPort: 5011,
      databasPort: 6011,
      dataPort: 6013,
      plcPort: 6014,
      alg2dPort: 5011,
      useRustImageServer: true,
      rustImageServerPort: 6013,
    })

    expect(next).toEqual({
      apiBaseUrl: 'http://192.168.99.100:5011',
      imageBaseUrl: 'http://192.168.99.100:6013',
      databaseBaseUrl: 'http://192.168.99.100:6011',
      dataBaseUrl: 'http://192.168.99.100:6013',
      plcBaseUrl: 'http://192.168.99.100:6014',
      alg2dBaseUrl: 'http://192.168.99.100:5011',
      apiWsBaseUrl: 'ws://192.168.99.100:5011',
      databaseWsBaseUrl: 'ws://192.168.99.100:6011',
    })
  })

  it('applies all runtime connection URLs atomically and updates axios base', () => {
    const previousBaseUrls = { ...serviceBaseUrls }

    try {
      const next = applyRuntimeConnectionSettings({
        serverIp: '10.0.0.8',
        serverPort: 5011,
        databasPort: 6011,
        dataPort: 6013,
        plcPort: 6014,
        alg2dPort: 5011,
        useRustImageServer: false,
        rustImageServerPort: 6013,
      })

      expect(next).toEqual({
        apiBaseUrl: 'http://10.0.0.8:5011',
        imageBaseUrl: 'http://10.0.0.8:5011',
        databaseBaseUrl: 'http://10.0.0.8:6011',
        dataBaseUrl: 'http://10.0.0.8:6013',
        plcBaseUrl: 'http://10.0.0.8:6014',
        alg2dBaseUrl: 'http://10.0.0.8:5011',
        apiWsBaseUrl: 'ws://10.0.0.8:5011',
        databaseWsBaseUrl: 'ws://10.0.0.8:6011',
      })
    } finally {
      Object.assign(serviceBaseUrls, previousBaseUrls)
    }
  })

  it('applies runtime api base overrides to shared urls and axios requests', () => {
    const previousBaseUrl = serviceBaseUrls.apiBaseUrl

    try {
      const next = applyApiBaseUrlOverride('http://127.0.0.1:5010')
      expect(next.apiBaseUrl).toBe('http://127.0.0.1:5010')
      expect(next.apiWsBaseUrl).toBe('ws://127.0.0.1:5010')
      expect(serviceBaseUrls.apiBaseUrl).toBe('http://127.0.0.1:5010')
    } finally {
      applyApiBaseUrlOverride(previousBaseUrl)
    }
  })

  it('builds height line route with optional QML-compatible coordinates', () => {
    expect(buildHeightLinePath('S', 193113)).toBe('/coilData/heightData/S/193113')
    expect(
      buildHeightLinePath('L', 193113, {
        x1: 10,
        y1: 20,
        x2: 130,
        y2: 20,
      }),
    ).toBe('/coilData/heightData/L/193113?x1=10&y1=20&x2=130&y2=20')
  })

  it('builds QML-compatible defect aggregation routes', () => {
    expect(buildDefectAllPath(100, 120)).toBe('/search/getDefectAll/100/120')
    expect(buildDefectsAllPath(193113, 'S')).toBe('/search/defects_all/193113/S')
    expect(buildManualDefectsPath(193113, 'L')).toBe('/manual_defects/193113/L')
  })

  it('builds QML-compatible manual defect mutation routes', () => {
    expect(buildManualDefectAddPath()).toBe('/manual_defect/add')
    expect(buildManualDefectUpdatePath(51)).toBe('/manual_defect/update/51')
    expect(buildDeleteManualDefectPath(51)).toBe('/manual_defect/delete/51')
    expect(buildManualDefectExportPath()).toBe('/export_defects')
  })

  it('builds QML-compatible coil detail route', () => {
    expect(buildCoilDetailPath(193113)).toBe('/detail/193113')
  })

  it('builds QML-compatible current coil detail data routes', () => {
    expect(buildCoilStatePath(193113)).toBe('/search/CoilState/193113')
    expect(buildPlcDataPath(193113)).toBe('/search/PlcData/193113')
  })

  it('builds QML-compatible coil alarm route', () => {
    expect(buildCoilAlarmPath(193113)).toBe('/coilAlarm/193113')
  })

  it('builds QML-compatible data availability route', () => {
    expect(buildDataHasPath(193113)).toBe('/data_has/193113')
  })

  it('builds QML-compatible coil check status routes', () => {
    expect(buildCoilStatusPath(193113)).toBe('/check/get_coil_status/193113')
    expect(buildSetCoilStatusPath(193113, 1)).toBe('/check/set_coil_status/193113/1')
    expect(buildSetCoilStatusPath(193113, 2, 'needs review')).toBe(
      '/check/set_coil_status/193113/2/needs%20review',
    )
  })

  it('builds QML-compatible incremental coil flush route', () => {
    expect(buildFlushPath(193113)).toBe('/flush/193113')
  })

  it('builds QML-compatible coil search routes', () => {
    expect(buildSearchCoilNoPath('4V07441200')).toBe('/search/coilNo/4V07441200')
    expect(buildSearchCoilNoPath('4V 0744/1200')).toBe('/search/coilNo/4V%200744%2F1200')
    expect(buildSearchCoilIdPath(16019)).toBe('/search/coilId/16019')
    expect(buildSearchDateTimePath('202606280000', '202606282359')).toBe(
      '/search/DateTime/202606280000/202606282359',
    )
  })

  it('builds QML-compatible defect dictionary config routes', () => {
    expect(buildDefectDictPath()).toBe('/defectDict')
    expect(buildDefectDictAllPath()).toBe('/defectDictAll')
    expect(buildSetDefectDictPath()).toBe('/setDefectDict')
  })

  it('builds Python-compatible control config routes', () => {
    expect(buildControlConfigPath()).toBe('/control/config')
    expect(buildSetControlConfigPath()).toBe('/control/set_config')
    expect(buildSetControlPropertyPath('lower_limit', '-64.5')).toBe(
      '/control/set_property?key=lower_limit&value=-64.5',
    )
    expect(buildSetControlPropertyPath('save path', 'D:\\Control Data')).toBe(
      '/control/set_property?key=save+path&value=D%3A%5CControl+Data',
    )
  })

  it('builds Python-compatible diagnostic and speedtest routes', () => {
    expect(buildDownloadTestPath()).toBe('/download_test')
    expect(buildSpeedtestDownloadPath()).toBe('/speedtest/download')
    expect(buildSpeedtestDownloadPath(2)).toBe('/speedtest/download?size_in_mb=2')
    expect(buildSpeedtestUploadPath()).toBe('/speedtest/upload')
  })

  it('builds QML-compatible PLC curve aggregate routes', () => {
    expect(buildPlcInfoPath()).toBe('/plc/info/')
    expect(buildPlcConnectPath('10.1.2.3', 7, 9)).toBe(
      '/plc/connect/10.1.2.3/7/9',
    )
    expect(buildPlcGetPath('DB1', 'int', 2)).toBe('/plc/get/DB1/int/2')
    expect(buildPlcCurvePath('location_S')).toBe('/plc_curve/location_S')
    expect(buildPlcCurvePath('median 3d/mm', 10, 20, 200)).toBe(
      '/plc_curve/median%203d%2Fmm?start_id=10&end_id=20&limit=200',
    )
    expect(buildPlcCurvePath('location_L', undefined, Number.NaN, 0)).toBe('/plc_curve/location_L?limit=0')
    expect(buildPlcCurveAllPath()).toBe('/plc_curve_all')
    expect(buildPlcCurveAllPath(10, 20, 200)).toBe('/plc_curve_all?start_id=10&end_id=20&limit=200')
    expect(buildPlcCurveAllPath(undefined, Number.NaN, 0)).toBe('/plc_curve_all?limit=0')
    expect(apiModule.plcApi.getInfo.toString()).toContain('buildPlcInfoPath')
    expect(apiModule.plcApi.connect.toString()).toContain('buildPlcConnectPath')
    expect(apiModule.plcApi.getValue.toString()).toContain('buildPlcGetPath')
    expect(apiModule.plcApi.getCurve.toString()).toContain('buildPlcCurvePath')
  })

  it('builds Python-compatible system diagnostics routes', () => {
    expect(buildInfoPath()).toBe('/info')
    expect(buildDatabaseInfoPath()).toBe('/database_info')
    expect(buildVersionPath()).toBe('/version')
    expect(buildHealthPath()).toBe('/health')
    expect(buildDelayPath()).toBe('/delay')
    expect(buildRuntimeInfoPath()).toBe('/runtime_info')
    expect(buildOpenApiPath()).toBe('/openapi.json')
    expect(buildHardwarePath()).toBe('/hardware')
    expect(buildCaptureStatusPath()).toBe('/capture_status')
    expect(buildCaptureStatusCompatPath()).toBe('/capture/status')
    expect(buildCaptureFilesPath()).toBe('/capture/files')
    expect(buildCaptureFilesPath(true)).toBe('/capture/files?clear=true')
    expect(buildGetListenerAddFilePath()).toBe('/getListenerAddFile')
    expect(buildGetListenerAddFilePath(true)).toBe('/getListenerAddFile?clear=true')
    expect(buildCameraStatusPath()).toBe('/camera/status')
    expect(buildCamerasPath()).toBe('/cameras')
    expect(buildCameraStatusByKeyPath('Cap S/D')).toBe('/cameras/Cap%20S%2FD/status')
    expect(buildCameraFilesByKeyPath('Cap S/D')).toBe('/cameras/Cap%20S%2FD/files')
    expect(buildCameraAdjustPath()).toBe('/camera_adjust')
    expect(buildCameraAdjustmentPath('Cap S/D')).toBe('/camera_adjust/Cap%20S%2FD')
    expect(buildCameraReconnectPath('Cap S/D')).toBe('/camera_adjust/Cap%20S%2FD/reconnect')
    expect(buildCameraParamsPath()).toBe('/camera/params')
    expect(buildCameraReconnectCompatPath()).toBe('/camera/reconnect')
    expect(buildCameraParamsByKeyPath('Cap S/D')).toBe('/cameras/Cap%20S%2FD/params')
    expect(buildCameraReconnectByKeyPath('Cap S/D')).toBe('/cameras/Cap%20S%2FD/reconnect')
    expect(buildCameraAdjustmentPayload(12000, 8, true)).toEqual({
      exposureTime: 12000,
      gain: 8,
      save: true,
    })
    expect(buildCameraAlarmPath()).toBe('/cameraAlarm')
    expect(buildCameraDataPath(193113, 'Cap_S_D')).toBe('/cameraData/193113/Cap_S_D')
    expect(buildSyncSummariesPath()).toBe('/sync_summaries')
    expect(buildSyncSummariesPath(100)).toBe('/sync_summaries?limit=100')
    expect(buildSyncSummariesRangePath()).toBe('/sync_summaries_range')
  })

  it('builds Python-compatible test-mode settings routes and body', () => {
    expect(buildTestModePath()).toBe('/settings/test_mode')
    expect(buildTestModeStatusPath()).toBe('/settings/test_mode_status')
    expect(buildSetTestModeBody(true)).toEqual({ enabled: true })
    expect(buildSetTestModeBody(false)).toEqual({ enabled: false })
  })

  it('builds QML-compatible point and line data routes', () => {
    expect(buildPointDataPath(193113, 'S')).toBe('/get_point_data/193113/S')
    expect(buildLineDataPath(193113, 'L')).toBe('/get_line_data/193113/L')
  })

  it('builds QML-compatible hover height-point routes with image pixel coordinates', () => {
    expect(buildHeightPointPath('S', 193113, { x: 120.8, y: 650.3 })).toBe(
      '/coilData/heightPoint/S/193113?x=120&y=650',
    )
    expect(buildHeightPointPath('L', 193113, { x: -4.8, y: Number.NaN })).toBe(
      '/coilData/heightPoint/L/193113?x=0&y=0',
    )
  })

  it('builds QML-compatible re-detection and server state routes', () => {
    expect(buildReDetectionStatusPath()).toBe('/reDetection/status')
    expect(buildReDetectionStartPath(100, 102)).toBe('/reDetection/start/100/102')
    expect(buildReDetectionWsPath()).toBe('/ws/reDetection')
    expect(buildHeightPointWsPath()).toBe('/ws/coilData/heightPoint')
    expect(buildServerStatePath()).toBe('/getServerState')
    expect(buildServerStateWsPath()).toBe('/ws/DetectionState')
  })

  it('builds QML-compatible 2D algorithm test routes', () => {
    expect(buildAlg2dModelsPath()).toBe('/alg_2d/models')
    expect(buildAlg2dTestStartPath()).toBe('/alg_2d/test/start')
    expect(buildAlg2dTestStopPath()).toBe('/alg_2d/test/stop')
    expect(buildAlg2dTestProgressWsPath()).toBe('/ws/alg_2d/test/progress')
  })

  it('builds QML-compatible 2D area processing routes', () => {
    expect(buildClipConfigPath()).toBe('/clip_config')
    expect(buildAreaRejoinPath()).toBe('/area/rejoin')
    expect(buildAreaStatusPath()).toBe('/area/status')
    expect(buildAreaScanPath()).toBe('/area/scan')
  })

  it('builds QML-compatible 2D area rejoin payloads', () => {
    expect(buildAreaRejoinPayload(193113)).toEqual({ coil_id: 193113 })
    expect(buildAreaRejoinPayload(193113, 'L')).toEqual({ coil_id: 193113, surface_key: 'L' })
  })

  it('builds QML-compatible image tool routes', () => {
    expect(buildClassifierImagePath(193113, 'S', '压痕', 10, 20, 30, 40)).toBe(
      '/classifier_image/193113/S/%E5%8E%8B%E7%97%95/10/20/30/40',
    )
    expect(buildDefectImagePath('S', 193113, 'GRAY', 10, 20, 30, 40)).toBe(
      '/defect_image/S/193113/GRAY/10/20/30/40',
    )
    expect(buildClipMaxImagePath(193113, 'L')).toBe('/clipMaxImage/193113/L')
    expect(buildClipMaxImagePath(193113, 'S', 'D:\\clips\\193113')).toBe(
      '/clipMaxImage/193113/S?save_url=D%3A%5Cclips%5C193113',
    )
    expect(() => buildClipMaxImagePath(0, 'S')).toThrow('valid coil id')
    expect(() => buildClipMaxImagePath(193113, 'X')).toThrow('valid surface')
  })

  it('builds QML-compatible area and error image routes', () => {
    expect(buildCoilDataRenderPath('S', 193113)).toBe('/coilData/Render/S/193113')
    expect(
      buildCoilDataRenderPath('L', 193113, {
        scale: 0.5,
        mask: true,
        minValue: -30,
        maxValue: 45,
        grayscale: true,
      }),
    ).toBe('/coilData/Render/L/193113?scale=0.5&mask=true&minValue=-30&maxValue=45&grayscale=true')
    expect(apiModule.heightDataApi.getRenderData.toString()).toContain('buildCoilDataRenderPath')
    expect(buildCoilDataAreaPath('S', 193113)).toBe('/coilData/Area/S/193113')
    expect(
      buildCoilDataAreaPath('L', 193113, {
        valueFrom: 10,
        valueTo: 30,
        r: 255,
        g: 20,
        b: 5,
        scale: 0.5,
      }),
    ).toBe('/coilData/Area/L/193113?scale=0.5&valueFrom=10&valueTo=30&r=255&g=20&b=5')
    expect(buildCoilDataErrorPath('S', 193113, { minValue: 15, maxValue: 20 })).toBe(
      '/coilData/Error/S/193113?minValue=15&maxValue=20',
    )
    expect(buildDefaultCoilDataErrorPath('s', 193113)).toBe(
      '/coilData/Error/S/193113?scale=1&mask=false&minValue=-100&maxValue=100',
    )
    expect(buildDefaultCoilDataErrorPath('S', 193113, { minValue: -45, maxValue: 75 })).toBe(
      '/coilData/Error/S/193113?scale=1&mask=false&minValue=-45&maxValue=75',
    )
  })

  it('builds QML-compatible image preview/source/area routes', () => {
    expect(buildImagePreviewPath('S', 193113, 'AREA')).toBe('/image/preview/S/193113/AREA')
    expect(buildImageSourcePath('L', 193113, 'GRAY')).toBe('/image/source/L/193113/GRAY')
    expect(buildImageAreaPath('S', 193113)).toBe('/image/area/S/193113')
    expect(buildImageAreaPath('S', 193113, 'AREA')).toBe('/image/area/S/193113')
    expect(buildImageAreaPath('L', 193113, 'AREA_MASK')).toBe('/image/area/L/193113/AREA_MASK')
  })

  it('builds Python-compatible quick xlsx export routes', () => {
    expect(buildExport1hPath()).toBe('/export_1h')
    expect(buildExport1hPath('3D')).toBe('/export_1h?export_type=3D')
    expect(buildExport24hPath()).toBe('/export_24h')
    expect(buildExportTodayPath()).toBe('/export_today')
  })

  it('builds the QML legacy simple xlsx export route', () => {
    expect(buildExportDataSimplePath()).toBe('/exportDataSimple')
    expect(apiModule.exportApi.exportDataSimple()).toBe('/api/exportDataSimple')
  })

  it('builds Python-compatible range and config xlsx export routes', () => {
    expect(buildExportXlsxByIdPath(40, 42)).toBe('/exportXlsxById/40/42')
    expect(buildExportXlsxByIdPath(40, 42, '3D')).toBe('/exportXlsxById/40/42?export_type=3D')
    expect(buildExportXlsxByDateTimePath('202606270000', '202606282359')).toBe(
      '/exportXlsxByDateTime/202606270000/202606282359',
    )
    expect(buildExportXlsxPath()).toBe('/export_xlsx')
  })

  it('builds Python-compatible backup image task routes', () => {
    expect(buildBackupImageTaskPath(40, 42, 'D:\\Backup\\Images')).toBe(
      '/backupImageTask/40/42/D:/Backup/Images',
    )
    expect(buildBackupImageTaskWsPath()).toBe('/ws/backupImageTask')
  })

  it('builds Python-compatible database backup route', () => {
    expect(buildSaveToSqlPath('D:\\Backup\\coil.sql')).toBe('/save_to_sql/D:/Backup/coil.sql')
    expect(buildSaveToSqlPath('D:\\Backup\\coil.db')).toBe('/save_to_sql/D:/Backup/coil.db')
  })

  it('builds the QML list value change key route', () => {
    expect(buildCoilListValueChangeKeysPath()).toBe('/coil_list_value_change_keys')
  })
})
