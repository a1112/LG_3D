import { create } from 'zustand'
import type { CoilData, SurfaceKey } from '@/types'

interface CoilState {
  currentCoil: CoilData | null
  coilList: CoilData[]
  surfaceKey: SurfaceKey

  // Actions
  setCurrentCoil: (coil: CoilData | null) => void
  setCoilList: (list: CoilData[]) => void
  setSurfaceKey: (key: SurfaceKey) => void
}

export const useCoilStore = create<CoilState>((set) => ({
  currentCoil: null,
  coilList: [],
  surfaceKey: 'S',

  setCurrentCoil: (coil) => set({ currentCoil: coil }),
  setCoilList: (list) => set({ coilList: list }),
  setSurfaceKey: (key) => set({ surfaceKey: key }),
}))
