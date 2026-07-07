import { describe, expect, it } from 'vitest'

import { buildCameraAdjustmentRows, formatCameraFrameAge } from './cameraAdjustment'

describe('camera adjustment helpers', () => {
  it('maps QML CameraSetting payloads into editable camera rows', () => {
    const rows = buildCameraAdjustmentRows({
      cameras: [
        {
          key: 'Cap_S_D',
          name: 'S-D',
          sn: 'SN-1',
          serviceUrl: 'http://127.0.0.1:6100',
          status: {
            ok: true,
            connected: true,
            writable: true,
            message: 'running',
            source: 'yaml',
            paramFile: 'camera.yaml',
            lastFrameAge: 1.25,
            lastFrameAge3D: '2.5',
            lastError3D: '',
            params: {
              exposureTime: '12000',
              gain: 8,
            },
            capture: {
              captureRunning: true,
              serviceReady: true,
            },
          },
        },
      ],
    })

    expect(rows).toEqual([
      {
        key: 'Cap_S_D',
        name: 'S-D',
        sn: 'SN-1',
        serviceUrl: 'http://127.0.0.1:6100',
        ok: true,
        connected: true,
        writable: true,
        message: 'running',
        source: 'yaml',
        paramFile: 'camera.yaml',
        lastFrameAge: 1.25,
        lastFrameAge3D: 2.5,
        lastError3D: '',
        captureRunning: true,
        serviceReady: true,
        exposureTime: 12000,
        gain: 8,
      },
    ])
  })

  it('uses QML-compatible defaults for missing or invalid camera fields', () => {
    expect(
      buildCameraAdjustmentRows({
        cameras: [
          {
            key: 'Cap_L_U',
            status: {
              connected: false,
              params: {
                exposureTime: 'bad',
              },
            },
          },
        ],
      })[0],
    ).toMatchObject({
      key: 'Cap_L_U',
      ok: false,
      connected: false,
      writable: false,
      captureRunning: false,
      serviceReady: true,
      exposureTime: 0,
      gain: 0,
    })
    expect(formatCameraFrameAge(2)).toBe('2.0 s')
    expect(formatCameraFrameAge(Number.NaN)).toBe('-')
  })
})
