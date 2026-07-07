import { beforeEach, describe, expect, it } from 'vitest'

import { useCoilStore } from './coilStore'

describe('coilStore QML surface visibility state', () => {
  beforeEach(() => {
    useCoilStore.setState({
      currentCoil: null,
      coilList: [],
      currentCoilList: [],
      surfaceKey: 'S',
      pendingDefect: null,
      visibleSurfaces: ['S', 'L'],
      rootViewCommand: null,
      imageMaskChecked: false,
      quickImageEnabled: true,
      coilListMode: 'realtime',
      keepLatest: true,
      returnRealtimeCommand: null,
    })
  })

  it('tracks QML TopCoilTools S/L show_visible toggles', () => {
    useCoilStore.getState().setSurfaceVisible('L', false)
    expect(useCoilStore.getState().visibleSurfaces).toEqual(['S'])

    useCoilStore.getState().setSurfaceVisible('S', false)
    expect(useCoilStore.getState().visibleSurfaces).toEqual([])

    useCoilStore.getState().setSurfaceVisible('L', true)
    expect(useCoilStore.getState().visibleSurfaces).toEqual(['L'])

    useCoilStore.getState().setSurfaceVisible('S', true)
    expect(useCoilStore.getState().visibleSurfaces).toEqual(['S', 'L'])
  })

  it('emits QML TopCoilTools global 2D/3D root-view commands', () => {
    useCoilStore.getState().setGlobalRootViewMode('two')
    expect(useCoilStore.getState().rootViewCommand).toEqual({ mode: 'two', serial: 1 })

    useCoilStore.getState().setGlobalRootViewMode('three')
    expect(useCoilStore.getState().rootViewCommand).toEqual({ mode: 'three', serial: 2 })

    useCoilStore.getState().setGlobalRootViewMode('three')
    expect(useCoilStore.getState().rootViewCommand).toEqual({ mode: 'three', serial: 3 })
  })

  it('tracks QML TopCoilTools MASK and QUICK image toggles', () => {
    expect(useCoilStore.getState().imageMaskChecked).toBe(false)
    expect(useCoilStore.getState().quickImageEnabled).toBe(true)

    useCoilStore.getState().setImageMaskChecked(true)
    expect(useCoilStore.getState().imageMaskChecked).toBe(true)

    useCoilStore.getState().setQuickImageEnabled(false)
    expect(useCoilStore.getState().quickImageEnabled).toBe(false)

    useCoilStore.getState().setImageMaskChecked(false)
    useCoilStore.getState().setQuickImageEnabled(true)
    expect(useCoilStore.getState().imageMaskChecked).toBe(false)
    expect(useCoilStore.getState().quickImageEnabled).toBe(true)
  })

  it('shares QML TopMsg realtime/history list state and return command', () => {
    expect(useCoilStore.getState().coilListMode).toBe('realtime')
    expect(useCoilStore.getState().keepLatest).toBe(true)
    expect(useCoilStore.getState().returnRealtimeCommand).toBeNull()

    useCoilStore.getState().setCoilListMode('history')
    useCoilStore.getState().setKeepLatest(false)
    expect(useCoilStore.getState().coilListMode).toBe('history')
    expect(useCoilStore.getState().keepLatest).toBe(false)

    useCoilStore.getState().requestReturnRealtimeMode()
    expect(useCoilStore.getState().returnRealtimeCommand).toEqual({ serial: 1 })

    useCoilStore.getState().requestReturnRealtimeMode()
    expect(useCoilStore.getState().returnRealtimeCommand).toEqual({ serial: 2 })
  })

  it('shares the QML currentCoilListModel for pages outside the left sidebar', () => {
    const realtimeRows = [
      { id: 193113, coilNo: 'coil-193113', dateTime: '2026-06-28', status: 0, surfaceKey: 'S' as const },
    ]
    const historyRows = [
      { id: 16040, coilNo: 'coil-16040', dateTime: '2026-06-27', status: 0, surfaceKey: 'L' as const },
    ]

    expect(useCoilStore.getState().currentCoilList).toEqual([])

    useCoilStore.getState().setCurrentCoilList(realtimeRows)
    expect(useCoilStore.getState().currentCoilList).toBe(realtimeRows)

    useCoilStore.getState().setCurrentCoilList(historyRows)
    expect(useCoilStore.getState().currentCoilList).toBe(historyRows)
  })
})
