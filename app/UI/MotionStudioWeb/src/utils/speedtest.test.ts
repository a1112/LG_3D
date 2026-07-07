import { describe, expect, it } from 'vitest'

import { formatSpeedtestUploadResult } from './speedtest'

describe('speedtest upload result formatting', () => {
  it('formats Python-compatible upload speedtest response fields for display', () => {
    expect(
      formatSpeedtestUploadResult({
        filename: 'diagnostic.bin',
        file_size_mb: 2.5,
        upload_time_seconds: 0.42,
        speed_mbps: 47.619,
      }),
    ).toEqual({
      filename: 'diagnostic.bin',
      fileSize: '2.50 MB',
      elapsed: '0.420 s',
      speed: '47.62 MB/s',
    })
  })

  it('formats live upload speedtest alias fields returned by the Rust proxy', () => {
    expect(
      formatSpeedtestUploadResult({
        filename: 'file',
        file_size_mb: 0.004,
        upload_time_s: 0.125,
        upload_speed_mb_s: 32.75,
      }),
    ).toEqual({
      filename: 'file',
      fileSize: '0.00 MB',
      elapsed: '0.125 s',
      speed: '32.75 MB/s',
    })
  })

  it('returns null for empty or malformed upload responses', () => {
    expect(formatSpeedtestUploadResult(null)).toBeNull()
    expect(formatSpeedtestUploadResult({ filename: '' })).toBeNull()
  })
})
