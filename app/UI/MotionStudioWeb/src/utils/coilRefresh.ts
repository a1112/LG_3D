import type { CoilData } from '@/types'

export const QML_COIL_REFRESH_INTERVAL_MS = 8000
export const QML_MAX_REALTIME_COIL_LIST_LENGTH = 300
export const QML_KEEP_LATEST_AUTO_RESTORE_INTERVAL_MS = 7000
export const QML_KEEP_LATEST_AUTO_RESTORE_TICKS = 180

type QmlKeepLatestAutoRestoreResult = {
  autoKeepLatestTicks: number
  keepLatest: boolean
}

export function buildQmlFlushStartCoilId(coils: CoilData[]): number {
  return coils.length > 0 ? coils[0].id - 3 : 0
}

export function mergeQmlFlushCoilList(
  currentCoils: CoilData[],
  flushCoils: CoilData[],
  maxLength = QML_MAX_REALTIME_COIL_LIST_LENGTH,
): CoilData[] {
  const nextCoils = currentCoils.slice(0, maxLength)
  const indexById = new Map(nextCoils.map((coil, index) => [coil.id, index]))
  const toInsert: CoilData[] = []

  for (const coil of flushCoils) {
    const existingIndex = indexById.get(coil.id)
    if (existingIndex === undefined) {
      toInsert.push(coil)
    } else {
      nextCoils[existingIndex] = coil
    }
  }

  for (let index = toInsert.length - 1; index >= 0; index -= 1) {
    nextCoils.unshift(toInsert[index])
  }

  return nextCoils
}

export function resolveQmlRealtimeCurrentCoil(
  currentCoil: CoilData | null,
  nextCoils: CoilData[],
  keepLatest: boolean,
): CoilData | null {
  if (nextCoils.length === 0) return currentCoil
  if (!currentCoil || keepLatest) return nextCoils[0]

  return nextCoils.find((coil) => coil.id === currentCoil.id) ?? currentCoil
}

export function advanceQmlKeepLatestAutoRestoreTick(
  currentTicks: number,
  maxTicks = QML_KEEP_LATEST_AUTO_RESTORE_TICKS,
): QmlKeepLatestAutoRestoreResult {
  const nextTicks = currentTicks + 1

  if (nextTicks >= maxTicks) {
    return {
      autoKeepLatestTicks: 0,
      keepLatest: true,
    }
  }

  return {
    autoKeepLatestTicks: nextTicks,
    keepLatest: false,
  }
}
