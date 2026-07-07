import { describe, expect, it } from 'vitest'

import {
  buildAreaClipPayloadFromSettings,
  buildQmlAreaClipSettingsFromStatus,
  buildAreaStatusView,
  buildDefaultAreaClipConfig,
  buildQmlAreaClipSettings,
  normalizeAreaSurfaceKey,
  readAreaQueueDepth,
} from './area2d'

describe('2D area diagnostics helpers', () => {
  it('normalizes UI surface choices to QML surface keys', () => {
    expect(normalizeAreaSurfaceKey('s')).toBe('S')
    expect(normalizeAreaSurfaceKey(' L ')).toBe('L')
    expect(normalizeAreaSurfaceKey('bad', 'L')).toBe('L')
  })

  it('builds the diagnostics dynamic clip payload without zeroing QML coefficients', () => {
    expect(buildDefaultAreaClipConfig('l')).toEqual({
      surface_key: 'L',
      mode: 'dynamic',
      offset: 40,
    })
  })

  it('builds QML ClipSetting defaults for S and L surfaces', () => {
    expect(buildQmlAreaClipSettings()).toEqual([
      {
        surfaceKey: 'S',
        label: 'S端',
        mode: 'fixed',
        fixed: 200,
        a: 3,
        b: 220,
        c: 2600,
      },
      {
        surfaceKey: 'L',
        label: 'L端',
        mode: 'fixed',
        fixed: 200,
        a: 3,
        b: 220,
        c: 4000,
      },
    ])
  })

  it('builds the QML ClipSetting apply payload without diagnostics-only offset', () => {
    expect(
      buildAreaClipPayloadFromSettings({
        surfaceKey: 'L',
        label: 'L端',
        mode: 'dynamic',
        fixed: 180,
        a: 2.5,
        b: 210,
        c: 3900,
      }),
    ).toEqual({
      surface_key: 'L',
      mode: 'dynamic',
      fixed: 180,
      a: 2.5,
      b: 210,
      c: 3900,
    })
  })

  it('hydrates QML ClipSetting values from Rust area status clipConfig', () => {
    expect(
      buildQmlAreaClipSettingsFromStatus({
        surfaces: {
          S: {
            clipConfig: {
              mode: 'dynamic',
              fixed: 180,
              a: 2.5,
              b: 210,
              c: 2500,
            },
          },
          L: {
            clip_config: {
              mode: 'fixed',
              fixed: 160,
              a: 4,
              b: 230,
              c: 4100,
            },
          },
        },
      }),
    ).toEqual([
      {
        surfaceKey: 'S',
        label: 'S端',
        mode: 'dynamic',
        fixed: 180,
        a: 2.5,
        b: 210,
        c: 2500,
      },
      {
        surfaceKey: 'L',
        label: 'L端',
        mode: 'fixed',
        fixed: 160,
        a: 4,
        b: 230,
        c: 4100,
      },
    ])
  })

  it('reads queue depth from Rust and Python-style status keys', () => {
    expect(readAreaQueueDepth({ queueDepth: 2 })).toBe(2)
    expect(readAreaQueueDepth({ queue_depth: 3 })).toBe(3)
    expect(readAreaQueueDepth({ queueSize: 4 })).toBe(4)
    expect(readAreaQueueDepth(null)).toBe(0)
  })

  it('prefers explicit zero queue depths over stale fallback counters', () => {
    expect(
      buildAreaStatusView(
        {
          status: 'ok',
          surfaces: { S: { queueDepth: 0 } },
          queueDepths: { S: 5, join: 7 },
          joinQueueSize: 0,
          scanner: { scanRunning: false },
        },
        'S',
      ),
    ).toEqual({
      status: 'ok',
      surfaceQueueDepth: 0,
      joinQueueDepth: 0,
      scanRunning: false,
    })
  })

  it('falls back to aggregate queue-depth counters when surface values are missing', () => {
    expect(
      buildAreaStatusView(
        {
          queueDepths: { L: 3, join: 4 },
          scanner: { running: true },
        },
        'L',
      ),
    ).toEqual({
      status: 'unknown',
      surfaceQueueDepth: 3,
      joinQueueDepth: 4,
      scanRunning: true,
    })
  })

  it('exposes the selected surface clipConfig in the diagnostics status view', () => {
    expect(
      buildAreaStatusView(
        {
          status: 'ok',
          surfaces: {
            S: {
              queueSize: 0,
              clipConfig: {
                mode: 'dynamic',
                fixed: 180,
                a: 2.5,
                b: 210,
                c: 2500,
                offset: 40,
              },
            },
          },
          queueDepths: { S: 0, join: 0 },
          scanner: { scanRunning: false },
        },
        'S',
      ).clipConfig,
    ).toEqual({
      mode: 'dynamic',
      fixed: 180,
      a: 2.5,
      b: 210,
      c: 2500,
      offset: 40,
    })
  })
})
