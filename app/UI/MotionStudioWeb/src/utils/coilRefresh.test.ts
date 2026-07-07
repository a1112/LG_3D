import { describe, expect, it } from 'vitest'

import {
  advanceQmlKeepLatestAutoRestoreTick,
  buildQmlFlushStartCoilId,
  mergeQmlFlushCoilList,
  resolveQmlRealtimeCurrentCoil,
  QML_COIL_REFRESH_INTERVAL_MS,
  QML_KEEP_LATEST_AUTO_RESTORE_INTERVAL_MS,
  QML_KEEP_LATEST_AUTO_RESTORE_TICKS,
} from './coilRefresh'
import type { CoilData } from '@/types'

const baseCoil = (id: number, coilNo = `coil-${id}`): CoilData => ({
  id,
  coilNo,
  dateTime: '2026-07-01 10:00:00',
  status: 2,
  surfaceKey: 'S',
  defectCountS: 0,
  defectCountL: 0,
})

describe('QML coil realtime refresh helpers', () => {
  it('uses the QML CoreTimer interval and flush start id', () => {
    expect(QML_COIL_REFRESH_INTERVAL_MS).toBe(8000)
    expect(buildQmlFlushStartCoilId([baseCoil(193113), baseCoil(193112)])).toBe(193110)
    expect(buildQmlFlushStartCoilId([])).toBe(0)
  })

  it('uses the QML keepLatest auto-restore timer settings', () => {
    expect(QML_KEEP_LATEST_AUTO_RESTORE_INTERVAL_MS).toBe(7000)
    expect(QML_KEEP_LATEST_AUTO_RESTORE_TICKS).toBe(180)
  })

  it('merges /flush rows like QML CoreModel.updateData', () => {
    const current = [baseCoil(103), baseCoil(102), baseCoil(101)]
    const updates = [baseCoil(102, 'updated-102'), baseCoil(104), baseCoil(105)]

    expect(mergeQmlFlushCoilList(current, updates).map((coil) => [coil.id, coil.coilNo])).toEqual([
      [104, 'coil-104'],
      [105, 'coil-105'],
      [103, 'coil-103'],
      [102, 'updated-102'],
      [101, 'coil-101'],
    ])
  })

  it('trims the realtime list to QML maxCoilListModelLen before applying flush updates', () => {
    const current = Array.from({ length: 302 }, (_, index) => baseCoil(500 - index))

    const next = mergeQmlFlushCoilList(current, [baseCoil(501)])

    expect(next).toHaveLength(301)
    expect(next[0].id).toBe(501)
    expect(next[next.length - 1]?.id).toBe(201)
  })

  it('keeps or releases the selected coil like QML keepLatest', () => {
    const previousCurrent = baseCoil(102, 'old-current')
    const nextCoils = [baseCoil(104), baseCoil(103), baseCoil(102, 'updated-current')]

    expect(resolveQmlRealtimeCurrentCoil(null, nextCoils, true)?.id).toBe(104)
    expect(resolveQmlRealtimeCurrentCoil(previousCurrent, nextCoils, true)?.id).toBe(104)
    expect(resolveQmlRealtimeCurrentCoil(previousCurrent, nextCoils, false)).toMatchObject({
      id: 102,
      coilNo: 'updated-current',
    })
    expect(resolveQmlRealtimeCurrentCoil(baseCoil(99), nextCoils, false)?.id).toBe(99)
  })

  it('restores keepLatest after QML autoKeepTime reaches the configured max', () => {
    expect(advanceQmlKeepLatestAutoRestoreTick(0)).toEqual({
      autoKeepLatestTicks: 1,
      keepLatest: false,
    })
    expect(advanceQmlKeepLatestAutoRestoreTick(QML_KEEP_LATEST_AUTO_RESTORE_TICKS - 1)).toEqual({
      autoKeepLatestTicks: 0,
      keepLatest: true,
    })
  })
})
