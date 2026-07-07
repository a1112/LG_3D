import { describe, expect, it } from 'vitest'

import { buildDefectImageFolderUrl, findDefectNavigationTarget } from './defectNavigation'
import type { CoilData, DefectData } from '@/types'

const coil = (id: number): CoilData => ({
  id,
  coilNo: `coil-${id}`,
  dateTime: '2026-06-28 18:00:00',
  status: 0,
  surfaceKey: 'S',
})

const defect = (coilId: number, surface: 'S' | 'L' = 'L'): DefectData => ({
  id: 82011,
  coilId,
  surface,
  defectType: '烂边',
  position: { x: 2176, y: 578 },
  size: { width: 1087, height: 502 },
  confidence: 0.638,
})

describe('defect navigation helpers', () => {
  it('finds the matching coil from the visible list before switching to image view', () => {
    const target = findDefectNavigationTarget(defect(16040, 'L'), {
      currentCoil: coil(193113),
      coilList: [coil(193113), coil(16040), coil(16019)],
    })

    expect(target).toEqual({
      coil: coil(16040),
      surfaceKey: 'L',
      pendingDefect: defect(16040, 'L'),
    })
  })

  it('falls back to the current coil when the visible list does not contain the defect coil', () => {
    const target = findDefectNavigationTarget(defect(193113, 'S'), {
      currentCoil: coil(193113),
      coilList: [coil(16040)],
    })

    expect(target?.coil).toEqual(coil(193113))
    expect(target?.surfaceKey).toBe('S')
  })

  it('falls back from QML currentCoilListModel to realCoilListModel before switching to image view', () => {
    const target = findDefectNavigationTarget(defect(16040, 'L'), {
      currentCoil: coil(193113),
      coilList: [coil(22001)],
      realtimeCoilList: [coil(193113), coil(16040), coil(16019)],
    })

    expect(target).toEqual({
      coil: coil(16040),
      surfaceKey: 'L',
      pendingDefect: defect(16040, 'L'),
    })
  })

  it('keeps QML currentCoilListModel precedence when the defect coil also exists in realCoilListModel', () => {
    const currentListCoil = { ...coil(16040), coilNo: 'history-coil-16040' }
    const realtimeListCoil = { ...coil(16040), coilNo: 'realtime-coil-16040' }

    const target = findDefectNavigationTarget(defect(16040, 'S'), {
      currentCoil: coil(193113),
      coilList: [currentListCoil],
      realtimeCoilList: [realtimeListCoil],
    })

    expect(target?.coil).toEqual(currentListCoil)
    expect(target?.surfaceKey).toBe('S')
  })

  it('returns null when the defect coil cannot be found like the QML menu guard', () => {
    expect(
      findDefectNavigationTarget(defect(16039, 'L'), {
        currentCoil: coil(193113),
        coilList: [coil(193113), coil(16040)],
      }),
    ).toBeNull()
  })

  it('builds the local image folder URL for a defect surface like QML open image location', () => {
    expect(
      buildDefectImageFolderUrl(defect(16040, 'L'), {
        info: {
          surfaceS: { saveFolder: 'F:\\Data\\Save_S' },
          surfaceL: { saveFolder: 'F:\\Data\\Save_L' },
        },
        serverHost: '127.0.0.1',
      }),
    ).toBe('file:///F:/Data/Save_L/16040')
  })

  it('builds the shared image folder URL for a defect surface when the server is remote', () => {
    expect(
      buildDefectImageFolderUrl(defect(16040, 'S'), {
        info: {
          surfaceS: { saveFolder: 'D:\\ignored\\Save_S' },
        },
        serverHost: '10.10.2.5',
        sharedFolderBaseName: 'Save_',
      }),
    ).toBe('file:////10.10.2.5/Save_S/16040')
  })

  it('returns an empty URL when there is no defect to open', () => {
    expect(buildDefectImageFolderUrl(null, { info: {}, serverHost: '127.0.0.1' })).toBe('')
  })
})
