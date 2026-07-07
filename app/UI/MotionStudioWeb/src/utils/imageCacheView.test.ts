import { describe, expect, it } from 'vitest'

import { buildImageCacheRows, formatImageCacheBytes } from './imageCacheView'

describe('image cache view helpers', () => {
  it('formats cache byte counts for operator-facing status text', () => {
    expect(formatImageCacheBytes(0)).toBe('0 B')
    expect(formatImageCacheBytes(512)).toBe('512 B')
    expect(formatImageCacheBytes(1536)).toBe('1.5 KB')
    expect(formatImageCacheBytes(1048576)).toBe('1.0 MB')
  })

  it('builds stable cache status rows from image cache stats', () => {
    expect(
      buildImageCacheRows({
        size: 3,
        totalSize: 1572864,
        totalSizeMB: '1.50',
        maxSizeMB: '100.00',
        maxItems: 15,
        usagePercent: '1.50',
      }),
    ).toEqual([
      { label: '缓存项', value: '3' },
      { label: '最大项数', value: '15' },
      { label: '占用空间', value: '1.5 MB / 100.0 MB' },
      { label: '使用率', value: '1.5%' },
    ])
  })
})
