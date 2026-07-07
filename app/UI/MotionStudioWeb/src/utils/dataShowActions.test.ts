import { describe, expect, it, vi } from 'vitest'

import {
  buildDataShowHeightDataReturnUrl,
  buildDataShowOpenUrl,
  buildDataShowRenderParams,
  buildDataShowRenderStages,
  openDataShowExternalUrl,
  type DataShowOpenUrlMode,
} from './dataShowActions'

const imageSettings = {
  useRustImageServer: false,
  rustImageServerPort: 6013,
  useSharedFolder: false,
  sharedFolderBaseName: 'Save_',
}

describe('DataShow QML action helpers', () => {
  it('builds QML Render params from coilInfo plane/range settings', () => {
    expect(
      buildDataShowRenderParams({
        coilInfo: {
          median_3d: 47837.4,
          median_3d_mm: 770.9,
          scan3dCoordinateScaleZ: 0.02,
        },
      }),
    ).toEqual({
      scale: 1,
      mask: true,
      minValue: 46837,
      maxValue: 48837,
      grayscale: false,
    })

    expect(
      buildDataShowRenderParams({
        coilInfo: {
          median_3d: 47837.4,
          median_3d_mm: 770.9,
          scan3dCoordinateScaleZ: 0.02,
        },
        renderScale: 0.5,
        rangeZ: 10,
        grayscale: true,
      }),
    ).toEqual({
      scale: 0.5,
      mask: true,
      minValue: 47337,
      maxValue: 48337,
      grayscale: true,
    })

    expect(buildDataShowRenderParams({ coilInfo: { median_3d: 47837.4 } })).toBeNull()
  })

  it('uses the QML RenderSetting plane value as the render center when provided', () => {
    const renderInput = {
      coilInfo: {
        median_3d: 47837.4,
        median_3d_mm: 770.9,
        scan3dCoordinateScaleZ: 0.02,
      },
      planeZMm: 780.9,
      rangeZ: 10,
    } as Parameters<typeof buildDataShowRenderParams>[0] & { planeZMm: number }

    expect(buildDataShowRenderParams(renderInput)).toEqual({
      scale: 1,
      mask: true,
      minValue: 47837,
      maxValue: 48837,
      grayscale: false,
    })
  })

  it('builds QML 1024-cache Render stages from gray preview to delayed color render', () => {
    const baseParams = {
      scale: 0.5,
      mask: true,
      minValue: 47837,
      maxValue: 48837,
      grayscale: false,
    }

    expect(buildDataShowRenderStages(baseParams, true)).toEqual([
      {
        key: 'gray-preview',
        viewKey: 'GRAY',
        label: '灰度预览',
        delayMs: 0,
        params: { ...baseParams, grayscale: true },
      },
      {
        key: 'color-render',
        viewKey: 'JET',
        label: '彩色显示',
        delayMs: 500,
        params: { ...baseParams, grayscale: false },
      },
    ])

    expect(buildDataShowRenderStages(baseParams, false)).toEqual([
      {
        key: 'color-render',
        viewKey: 'JET',
        label: '彩色显示',
        delayMs: 0,
        params: { ...baseParams, grayscale: false },
      },
    ])

    expect(buildDataShowRenderStages(null, true)).toEqual([])
  })

  it('builds the QML 打开URL source for AREA and 3D modes', () => {
    expect(
      buildDataShowOpenUrl({
        mode: 'area' satisfies DataShowOpenUrlMode,
        surfaceKey: 'L',
        coilId: 193113,
        imageRuntimeSettings: imageSettings,
        imageBaseUrl: '/api',
      }),
    ).toBe('/api/image/area/L/193113')

    expect(
      buildDataShowOpenUrl({
        mode: 'three',
        surfaceKey: 'S',
        coilId: 193113,
        imageRuntimeSettings: imageSettings,
        imageBaseUrl: '/api',
        renderParams: {
          scale: 1,
          mask: true,
          minValue: 46837,
          maxValue: 48837,
          grayscale: false,
        },
      }),
    ).toBe('/api/coilData/Render/S/193113?scale=1&mask=true&minValue=46837&maxValue=48837&grayscale=false')
  })

  it('builds QML 2D gray/depth source URLs from the current surface view key', () => {
    expect(
      buildDataShowOpenUrl({
        mode: 'gray' as DataShowOpenUrlMode,
        surfaceKey: 'S',
        coilId: 193113,
        imageRuntimeSettings: imageSettings,
        imageBaseUrl: '/api',
      }),
    ).toBe('/api/image/source/S/193113/GRAY')

    expect(
      buildDataShowOpenUrl({
        mode: 'depth' as DataShowOpenUrlMode,
        surfaceKey: 'L',
        coilId: 193113,
        imageRuntimeSettings: imageSettings,
        imageBaseUrl: '/api',
      }),
    ).toBe('/api/image/source/L/193113/JET')
  })

  it('builds QML 打开URL image sources with TopCoilTools MASK state', () => {
    const maskedSettings = {
      ...imageSettings,
      imageMaskChecked: true,
      quickImageEnabled: true,
    }

    expect(
      buildDataShowOpenUrl({
        mode: 'area' satisfies DataShowOpenUrlMode,
        surfaceKey: 'L',
        coilId: 193113,
        imageRuntimeSettings: maskedSettings,
        imageBaseUrl: '/api',
      }),
    ).toBe('/api/image/area/L/193113/AREA_MASK')

    expect(
      buildDataShowOpenUrl({
        mode: 'gray' as DataShowOpenUrlMode,
        surfaceKey: 'S',
        coilId: 193113,
        imageRuntimeSettings: maskedSettings,
        imageBaseUrl: '/api',
      }),
    ).toBe('/api/image/source/S/193113/GRAY?mask=true')
  })

  it('builds the QML 曲线数据返回 URL from the last applied height-line coordinates', () => {
    expect(
      buildDataShowHeightDataReturnUrl({
        surfaceKey: 'L',
        coilId: 193113.9,
        coords: { x1: 10, y1: 20, x2: 130, y2: 20 },
        apiBaseUrl: '/api',
      }),
    ).toBe('/api/coilData/heightData/L/193113?x1=10&y1=20&x2=130&y2=20')

    expect(
      buildDataShowHeightDataReturnUrl({
        surfaceKey: 'unknown',
        coilId: 42,
        coords: { x1: 900, y1: 650, x2: 1000, y2: 650 },
        apiBaseUrl: 'http://127.0.0.1:5011/',
      }),
    ).toBe('http://127.0.0.1:5011/coilData/heightData/S/42?x1=900&y1=650&x2=1000&y2=650')
  })

  it('keeps shared-folder mode on HTTP for AREA and opens Render through the API route', () => {
    const sharedSettings = {
      ...imageSettings,
      useSharedFolder: true,
    }

    expect(
      buildDataShowOpenUrl({
        mode: 'area',
        surfaceKey: 'S',
        coilId: 42,
        imageRuntimeSettings: sharedSettings,
        imageBaseUrl: '/image-api',
      }),
    ).toBe('/image-api/image/area/S/42')

    expect(
      buildDataShowOpenUrl({
        mode: 'three',
        surfaceKey: 'L',
        coilId: 42,
        imageRuntimeSettings: sharedSettings,
        imageBaseUrl: '/api',
        renderParams: {
          scale: 0.5,
          mask: true,
          minValue: 1,
          maxValue: 2,
          grayscale: true,
        },
      }),
    ).toBe('/api/coilData/Render/L/42?scale=0.5&mask=true&minValue=1&maxValue=2&grayscale=true')
  })

  it('opens absolute DataShow URLs through the Tauri/native opener before browser fallback like Qt.openUrlExternally', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'opened', path: 'http://127.0.0.1:5011/image/area/S/42/AREA' })
    const openWindow = vi.fn()

    await expect(
      openDataShowExternalUrl('http://127.0.0.1:5011/image/area/S/42/AREA', { openNative, openWindow }),
    ).resolves.toBe('native')

    expect(openNative).toHaveBeenCalledWith('http://127.0.0.1:5011/image/area/S/42/AREA')
    expect(openWindow).not.toHaveBeenCalled()
  })

  it('keeps relative DataShow API URLs inside the webview instead of native path opening', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'opened', path: '/api/image/area/S/42/AREA' })
    const openWindow = vi.fn()

    await expect(openDataShowExternalUrl('/api/image/area/S/42/AREA', { openNative, openWindow })).resolves.toBe(
      'browser',
    )

    expect(openNative).not.toHaveBeenCalled()
    expect(openWindow).toHaveBeenCalledWith('/api/image/area/S/42/AREA', '_blank', 'noopener,noreferrer')
  })

  it('falls back to browser window opening when absolute native URL opening is unavailable', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'unavailable' })
    const openWindow = vi.fn()

    await expect(
      openDataShowExternalUrl('http://127.0.0.1:5011/coilData/Render/L/42', { openNative, openWindow }),
    ).resolves.toBe('browser')

    expect(openNative).toHaveBeenCalledWith('http://127.0.0.1:5011/coilData/Render/L/42')
    expect(openWindow).toHaveBeenCalledWith(
      'http://127.0.0.1:5011/coilData/Render/L/42',
      '_blank',
      'noopener,noreferrer',
    )
  })
})
