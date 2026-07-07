import { create } from 'zustand'
import type { CoilData, DefectData, SurfaceKey } from '@/types'

type GlobalRootViewMode = 'two' | 'three'
export type CoilListMode = 'realtime' | 'history'

interface CoilState {
  currentCoil: CoilData | null
  coilList: CoilData[]
  currentCoilList: CoilData[]
  coilListMode: CoilListMode
  keepLatest: boolean
  surfaceKey: SurfaceKey
  pendingDefect: DefectData | null
  visibleSurfaces: SurfaceKey[]
  rootViewCommand: { mode: GlobalRootViewMode; serial: number } | null
  returnRealtimeCommand: { serial: number } | null
  imageMaskChecked: boolean
  quickImageEnabled: boolean

  // Actions
  setCurrentCoil: (coil: CoilData | null) => void
  setCoilList: (list: CoilData[]) => void
  setCurrentCoilList: (list: CoilData[]) => void
  setCoilListMode: (mode: CoilListMode) => void
  setKeepLatest: (keepLatest: boolean) => void
  setSurfaceKey: (key: SurfaceKey) => void
  setPendingDefect: (defect: DefectData | null) => void
  setSurfaceVisible: (key: SurfaceKey, visible: boolean) => void
  setGlobalRootViewMode: (mode: GlobalRootViewMode) => void
  requestReturnRealtimeMode: () => void
  setImageMaskChecked: (checked: boolean) => void
  setQuickImageEnabled: (enabled: boolean) => void
  clearPendingDefect: () => void
}

const SURFACE_ORDER: SurfaceKey[] = ['S', 'L']

export const useCoilStore = create<CoilState>((set) => ({
  currentCoil: null,
  coilList: [],
  currentCoilList: [],
  coilListMode: 'realtime',
  keepLatest: true,
  surfaceKey: 'S',
  pendingDefect: null,
  visibleSurfaces: ['S', 'L'],
  rootViewCommand: null,
  returnRealtimeCommand: null,
  imageMaskChecked: false,
  quickImageEnabled: true,

  setCurrentCoil: (coil) => set({ currentCoil: coil }),
  setCoilList: (list) => set({ coilList: list }),
  setCurrentCoilList: (list) => set({ currentCoilList: list }),
  setCoilListMode: (mode) => set({ coilListMode: mode }),
  setKeepLatest: (keepLatest) => set({ keepLatest }),
  setSurfaceKey: (key) => set({ surfaceKey: key }),
  setPendingDefect: (defect) => set({ pendingDefect: defect }),
  setSurfaceVisible: (key, visible) =>
    set((state) => {
      const next = new Set(state.visibleSurfaces)
      if (visible) {
        next.add(key)
      } else {
        next.delete(key)
      }
      return { visibleSurfaces: SURFACE_ORDER.filter((surface) => next.has(surface)) }
    }),
  setGlobalRootViewMode: (mode) =>
    set((state) => ({
      rootViewCommand: { mode, serial: (state.rootViewCommand?.serial ?? 0) + 1 },
    })),
  requestReturnRealtimeMode: () =>
    set((state) => ({
      returnRealtimeCommand: { serial: (state.returnRealtimeCommand?.serial ?? 0) + 1 },
    })),
  setImageMaskChecked: (checked) => set({ imageMaskChecked: checked }),
  setQuickImageEnabled: (enabled) => set({ quickImageEnabled: enabled }),
  clearPendingDefect: () => set({ pendingDefect: null }),
}))
