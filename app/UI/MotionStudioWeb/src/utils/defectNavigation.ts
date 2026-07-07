import type { CoilData, DefectData, SurfaceKey } from '@/types'
import { buildCoilSaveFolderUrl, getSurfaceSaveFolder } from './coilActions'

export interface DefectNavigationInput {
  currentCoil: CoilData | null
  coilList: CoilData[]
  currentCoilList?: CoilData[]
  realtimeCoilList?: CoilData[]
}

export interface DefectNavigationTarget {
  coil: CoilData
  surfaceKey: SurfaceKey
  pendingDefect: DefectData
}

export interface DefectImageFolderInput {
  info: unknown
  serverHost?: string
  sharedFolderBaseName?: string
}

export function findDefectNavigationTarget(
  defect: DefectData | null,
  { currentCoil, coilList, currentCoilList, realtimeCoilList }: DefectNavigationInput,
): DefectNavigationTarget | null {
  if (!defect) return null

  const findCoil = (list: CoilData[]) => list.find((item) => item.id === defect.coilId)
  const qmlCurrentCoilList = currentCoilList ?? coilList
  const qmlRealtimeCoilList = realtimeCoilList ?? coilList
  const coil =
    findCoil(qmlCurrentCoilList) ??
    findCoil(qmlRealtimeCoilList) ??
    (currentCoil?.id === defect.coilId ? currentCoil : null)
  if (!coil) return null

  return {
    coil,
    surfaceKey: defect.surface,
    pendingDefect: defect,
  }
}

export function buildDefectImageFolderUrl(defect: DefectData | null, input: DefectImageFolderInput): string {
  if (!defect) return ''

  return buildCoilSaveFolderUrl({
    coilId: defect.coilId,
    surfaceKey: defect.surface,
    saveFolder: getSurfaceSaveFolder(input.info, defect.surface),
    serverHost: input.serverHost,
    sharedFolderBaseName: input.sharedFolderBaseName,
  })
}
