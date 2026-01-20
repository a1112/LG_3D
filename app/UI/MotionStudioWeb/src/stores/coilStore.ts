import { create } from 'zustand'
import type { CoilData } from '@/types'

interface CoilState {
  currentCoil: CoilData | null
  coilList: CoilData[]
  surfaceKey: string

  // Actions
  setCurrentCoil: (coil: CoilData | null) => void
  setCoilList: (list: CoilData[]) => void
  setSurfaceKey: (key: string) => void
}

export const useCoilStore = create<CoilState>((set) => ({
  currentCoil: null,
  coilList: [],
  surfaceKey: 'top',

  setCurrentCoil: (coil) => set({ currentCoil: coil }),
  setCoilList: (list) => set({ coilList: list }),
  setSurfaceKey: (key) => set({ surfaceKey: key }),
}))
