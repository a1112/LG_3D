import { afterEach, describe, expect, it, vi } from 'vitest'

import { ImageCache, loadImageWithCache } from './imageCache'

const originalCreateObjectUrl = URL.createObjectURL
const originalRevokeObjectUrl = URL.revokeObjectURL

afterEach(() => {
  vi.unstubAllGlobals()
  URL.createObjectURL = originalCreateObjectUrl
  URL.revokeObjectURL = originalRevokeObjectUrl
})

describe('ImageCache', () => {
  it('reports and updates QML-compatible maximum cache item count', () => {
    const cache = new ImageCache({ maxItems: 50 })

    expect(cache.getStats().maxItems).toBe(50)

    cache.configure({ maxItems: 15 })

    expect(cache.getStats().maxItems).toBe(15)
  })

  it('keeps QML image cache disabled by default without fetching or retaining blobs', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    URL.createObjectURL = vi.fn()
    URL.revokeObjectURL = vi.fn()
    const cache = new ImageCache()
    const imageUrl = 'http://127.0.0.1:5011/image/source/S/193113/AREA'

    const resolvedUrl = await loadImageWithCache(imageUrl, 120, 80, cache)

    expect(resolvedUrl).toBe(imageUrl)
    expect(fetchMock).not.toHaveBeenCalled()
    expect(URL.createObjectURL).not.toHaveBeenCalled()
    expect(cache.getStats()).toMatchObject({
      enabled: false,
      size: 0,
    })
  })

  it('fetches and retains blobs only when QML image cache is enabled', async () => {
    const blob = new Blob(['area'], { type: 'image/jpeg' })
    const fetchMock = vi.fn(async () => ({
      ok: true,
      blob: async () => blob,
      statusText: 'OK',
    }))
    vi.stubGlobal('fetch', fetchMock)
    URL.createObjectURL = vi.fn(() => 'blob:cached-area')
    URL.revokeObjectURL = vi.fn()
    const cache = new ImageCache({ enabled: true, maxItems: 15 })
    const imageUrl = 'http://127.0.0.1:5011/image/source/S/193113/AREA'

    const resolvedUrl = await loadImageWithCache(imageUrl, 120, 80, cache)

    expect(resolvedUrl).toBe('blob:cached-area')
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob)
    expect(cache.getStats()).toMatchObject({
      enabled: true,
      maxItems: 15,
      size: 1,
    })
  })
})
