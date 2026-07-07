import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  clearApiRequestHistory,
  getApiRequestHistory,
  openApiHistoryExternalUrl,
  recordApiRequest,
} from './apiHistory'

describe('api request history', () => {
  beforeEach(() => {
    clearApiRequestHistory()
  })

  it('records QML ApiListPop-compatible request rows with newest first', () => {
    recordApiRequest({ method: 'get', url: '/coilList/80', timestamp: 1000 })
    recordApiRequest({ method: 'post', url: '/settings/test_mode', timestamp: 2000 })

    expect(getApiRequestHistory()).toEqual([
      {
        id: '2000-post-/settings/test_mode',
        method: 'POST',
        url: '/settings/test_mode',
        timestamp: 2000,
      },
      {
        id: '1000-get-/coilList/80',
        method: 'GET',
        url: '/coilList/80',
        timestamp: 1000,
      },
    ])
  })

  it('keeps the latest 200 request rows like QML urlListModel_maxCouint', () => {
    for (let index = 0; index < 205; index += 1) {
      recordApiRequest({ method: 'get', url: `/request/${index}`, timestamp: index })
    }

    const history = getApiRequestHistory()
    expect(history).toHaveLength(200)
    expect(history[0].url).toBe('/request/204')
    expect(history[199].url).toBe('/request/5')
  })

  it('returns a stable snapshot reference until history changes', () => {
    recordApiRequest({ method: 'get', url: '/coilList/80', timestamp: 1000 })

    const firstSnapshot = getApiRequestHistory()
    const secondSnapshot = getApiRequestHistory()

    expect(secondSnapshot).toBe(firstSnapshot)

    recordApiRequest({ method: 'get', url: '/coilList/81', timestamp: 2000 })

    expect(getApiRequestHistory()).not.toBe(firstSnapshot)
  })

  it('opens history URLs externally through native opener before browser fallback like QML', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'opened', path: 'http://127.0.0.1:5011/docs' })
    const openWindow = vi.fn()

    await expect(
      openApiHistoryExternalUrl(' http://127.0.0.1:5011/docs ', { openNative, openWindow }),
    ).resolves.toBe('native')

    expect(openNative).toHaveBeenCalledWith('http://127.0.0.1:5011/docs')
    expect(openWindow).not.toHaveBeenCalled()
  })

  it('falls back to browser window when native opener is unavailable', async () => {
    const openNative = vi.fn().mockResolvedValue({ status: 'unavailable' })
    const openWindow = vi.fn()

    await expect(openApiHistoryExternalUrl('/coilList/80', { openNative, openWindow })).resolves.toBe('browser')

    expect(openWindow).toHaveBeenCalledWith('/coilList/80', '_blank', 'noopener,noreferrer')
  })
})
