import { describe, expect, it, vi } from 'vitest'

import {
  DEFECT_DATA_MODE_OPTIONS,
  buildDefectDataQueryKey,
  getDefectListRange,
  fetchDefectsByMode,
  type DefectDataMode,
} from './defectDataMode'
import type { CoilData } from '@/types'

const coil = (id: number): CoilData => ({
  id,
  coilNo: String(id),
  dateTime: '2026-06-28 16:00:00',
  status: 0,
  surfaceKey: 'S',
})

describe('defect data mode helpers', () => {
  it('exposes auto, current-list, combined, and manual defect modes for the defect page toolbar', () => {
    expect(DEFECT_DATA_MODE_OPTIONS).toEqual([
      { value: 'auto', label: '自动' },
      { value: 'range', label: '当前列表' },
      { value: 'all', label: '自动+手动' },
      { value: 'manual', label: '手动' },
    ])
  })

  it('keeps react-query cache keys separate per mode and uses QML range keys for current-list mode', () => {
    expect(buildDefectDataQueryKey('auto', 193113, 'S')).toEqual(['defects', 'auto', 193113, 'S'])
    expect(buildDefectDataQueryKey('range', 193113, 'S', { startId: 16019, endId: 193113 })).toEqual([
      'defects',
      'range',
      16019,
      193113,
    ])
    expect(buildDefectDataQueryKey('range', 16040, 'L', { startId: 16019, endId: 193113 })).toEqual([
      'defects',
      'range',
      16019,
      193113,
    ])
    expect(buildDefectDataQueryKey('all', 193113, 'S')).toEqual(['defects', 'all', 193113, 'S'])
    expect(buildDefectDataQueryKey('manual', 193113, 'S')).toEqual(['defects', 'manual', 193113, 'S'])
  })

  it('builds the QML defect list range from visible list edges', () => {
    expect(getDefectListRange([coil(193113), coil(16040), coil(16019)])).toEqual({
      startId: 16019,
      endId: 193113,
    })
    expect(getDefectListRange([coil(16019), coil(16040), coil(193113)])).toEqual({
      startId: 16019,
      endId: 193113,
    })
    expect(getDefectListRange([])).toEqual({ startId: 0, endId: 0 })
  })

  it('uses the matching backend endpoint for each mode', async () => {
    const api = {
      getDefects: vi.fn().mockResolvedValue({ data: ['auto'] }),
      getDefectAll: vi.fn().mockResolvedValue({ data: ['range'] }),
      getDefectsAll: vi.fn().mockResolvedValue({ data: ['all'] }),
      getManualDefects: vi.fn().mockResolvedValue({ data: ['manual'] }),
    }

    await expect(fetchDefectsByMode('auto', api, 16040, 'L')).resolves.toEqual({ data: ['auto'] })
    await expect(
      fetchDefectsByMode('range', api, 16040, 'L', { startId: 16019, endId: 193113 }),
    ).resolves.toEqual({ data: ['range'] })
    await expect(fetchDefectsByMode('all', api, 16040, 'L')).resolves.toEqual({ data: ['all'] })
    await expect(fetchDefectsByMode('manual', api, 16040, 'L')).resolves.toEqual({ data: ['manual'] })

    expect(api.getDefects).toHaveBeenCalledWith(16040, 'L')
    expect(api.getDefectAll).toHaveBeenCalledWith(16019, 193113)
    expect(api.getDefectsAll).toHaveBeenCalledWith(16040, 'L')
    expect(api.getManualDefects).toHaveBeenCalledWith(16040, 'L')
  })

  it('returns an empty response for current-list mode when the visible list is empty', async () => {
    const api = {
      getDefects: vi.fn(),
      getDefectAll: vi.fn(),
      getDefectsAll: vi.fn(),
      getManualDefects: vi.fn(),
    }

    await expect(fetchDefectsByMode('range', api, 16040, 'L', { startId: 0, endId: 0 })).resolves.toEqual({
      code: 0,
      data: [],
      count: 0,
    })
    expect(api.getDefectAll).not.toHaveBeenCalled()
  })

  it('falls back to auto mode for unknown persisted values', () => {
    expect((['auto', 'range', 'all', 'manual', 'bad'] as string[]).filter((value): value is DefectDataMode =>
      DEFECT_DATA_MODE_OPTIONS.some((option) => option.value === value),
    )).toEqual(['auto', 'range', 'all', 'manual'])
  })
})
