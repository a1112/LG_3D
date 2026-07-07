import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(() => Promise.resolve({})),
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}))

import { coilApi, defectApi, diagnosticApi } from './api'

describe('diagnostic api client', () => {
  beforeEach(() => {
    mockPost.mockClear()
  })

  it('posts speedtest upload as multipart form data', async () => {
    const formData = new FormData()

    await diagnosticApi.uploadSpeedtest(formData)

    expect(mockPost).toHaveBeenCalledWith('/speedtest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  })
})

describe('coil api search client', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('normalizes coil number search array responses like the QML search history list', async () => {
    mockGet.mockResolvedValue([
      {
        Id: 16019,
        CoilNo: '4V07441200',
        CreateTime: {
          year: 2024,
          month: 9,
          day: 12,
          hour: 18,
          minute: 26,
          second: 16,
        },
        Status_S: -3,
        Status_L: -3,
        Grade: 0,
      },
    ])

    const result = await coilApi.searchByCoilNo('4V07441200')

    expect(mockGet).toHaveBeenCalledWith('/search/coilNo/4V07441200')
    expect(result.data).toHaveLength(1)
    expect(result.data[0]).toMatchObject({
      id: 16019,
      coilNo: '4V07441200',
      dateTime: '2024-09-12 18:26:16',
      statusS: -3,
      statusL: -3,
      grade: 0,
    })
  })

  it('normalizes coil id search array responses like the QML search history list', async () => {
    mockGet.mockResolvedValue([
      {
        Id: 16019,
        CoilNo: '4V07441200',
        DetectionTime: '2025-12-05 15:01:23',
        Status_S: -3,
        Status_L: -3,
      },
    ])

    const result = await (
      coilApi as typeof coilApi & {
        searchByCoilId: (coilId: number) => Promise<{ data: unknown[] }>
      }
    ).searchByCoilId(16019)

    expect(mockGet).toHaveBeenCalledWith('/search/coilId/16019')
    expect(result.data).toHaveLength(1)
    expect(result.data[0]).toMatchObject({
      id: 16019,
      coilNo: '4V07441200',
      dateTime: '2025-12-05 15:01:23',
      statusS: -3,
      statusL: -3,
    })
  })

  it('normalizes Rust/Tauri-compatible snake and camel coil aliases', async () => {
    mockGet.mockResolvedValue([
      {
        secondary_coil_id: 1701,
        coil_no: 'LG-1701',
        createTime: {
          year: 2026,
          month: 6,
          day: 30,
          hour: 9,
          minute: 8,
          second: 7,
        },
        status_s: 2,
        status_l: 1,
        defect_count_s: 3,
        defect_count_l: '4',
        check_status: 4,
        grade: '5',
      },
    ])

    const result = await coilApi.searchByCoilNo('LG-1701')

    expect(mockGet).toHaveBeenCalledWith('/search/coilNo/LG-1701')
    expect(result.data).toHaveLength(1)
    expect(result.data[0]).toMatchObject({
      id: 1701,
      coilNo: 'LG-1701',
      dateTime: '2026-06-30 09:08:07',
      status: 4,
      statusS: 2,
      statusL: 1,
      defectCountS: 3,
      defectCountL: 4,
      grade: 5,
    })
  })

  it('infers defect counts from detail child defects when summary counters are absent', async () => {
    mockGet.mockResolvedValue({
      Id: 14852,
      CoilNo: '4V07270000',
      CreateTime: {
        year: 2024,
        month: 9,
        day: 7,
        hour: 1,
        minute: 16,
        second: 45,
      },
      childrenCoilDefect: [
        { Id: 1, secondaryCoilId: 14852, surface: 'S' },
        { Id: 2, secondaryCoilId: 14852, surface: 'S' },
        { Id: 3, secondaryCoilId: 14852, surface: 'L' },
      ],
    })

    const result = await coilApi.getCoilDetail(14852)

    expect(mockGet).toHaveBeenCalledWith('/detail/14852')
    expect(result).toMatchObject({
      id: 14852,
      coilNo: '4V07270000',
      defectCountS: 2,
      defectCountL: 1,
    })
  })

  it('normalizes date range search array responses like the QML search history list', async () => {
    mockGet.mockResolvedValue([
      {
        Id: 16020,
        CoilNo: '4V07441201',
        CreateTime: {
          year: 2026,
          month: 6,
          day: 28,
          hour: 10,
          minute: 15,
          second: 30,
        },
        Status_S: 2,
        Status_L: 1,
      },
    ])

    const result = await coilApi.searchByDateTime('202606280000', '202606282359')

    expect(mockGet).toHaveBeenCalledWith('/search/DateTime/202606280000/202606282359')
    expect(result.data).toHaveLength(1)
    expect(result.data[0]).toMatchObject({
      id: 16020,
      coilNo: '4V07441201',
      dateTime: '2026-06-28 10:15:30',
      statusS: 2,
      statusL: 1,
    })
  })

  it('normalizes QML /flush incremental coil responses', async () => {
    mockGet.mockResolvedValue({
      coilList: [
        {
          Id: 193114,
          CoilNo: '4V08010001',
          CreateTime: {
            year: 2026,
            month: 7,
            day: 1,
            hour: 9,
            minute: 30,
            second: 0,
          },
          Status_S: 1,
          Status_L: 2,
        },
      ],
    })

    const result = await coilApi.flush(193110)

    expect(mockGet).toHaveBeenCalledWith('/flush/193110')
    expect(result.data).toEqual([
      expect.objectContaining({
        id: 193114,
        coilNo: '4V08010001',
        dateTime: '2026-07-01 09:30:00',
        status: 2,
      }),
    ])
  })

  it('builds the raw coil id search URL used by the QML left-list menu', () => {
    expect(coilApi.getSearchByCoilIdUrl(16019)).toBe('/api/search/coilId/16019')
  })
})

describe('defect api client', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('normalizes defect class names from defectName before configDefectName like QML DefectCoreModel', async () => {
    mockGet.mockResolvedValue([
      {
        Id: 501,
        secondaryCoilId: 1701,
        surface: 'S',
        defectName: '边裂',
        configDefectName: '2D_边裂',
        defectX: 12,
        defectY: 34,
        defectW: 56,
        defectH: 78,
        defectSource: 0.93,
      },
    ])

    const result = await defectApi.getDefects(1701, 'S')

    expect(mockGet).toHaveBeenCalledWith('/search/defects/1701/S')
    expect(result.data).toHaveLength(1)
    expect(result.data[0]).toMatchObject({
      id: 501,
      coilId: 1701,
      surface: 'S',
      defectType: '边裂',
      position: { x: 12, y: 34 },
      size: { width: 56, height: 78 },
      confidence: 0.93,
    })
  })
})
