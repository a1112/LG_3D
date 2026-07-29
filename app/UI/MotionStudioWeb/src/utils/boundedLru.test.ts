import { describe, expect, it } from 'vitest'

import { BoundedLruCache } from './boundedLru'

describe('BoundedLruCache', () => {
  it('evicts the least recently used entry at the configured limit', () => {
    const cache = new BoundedLruCache<string, number>(2)
    cache.set('oldest', 1).set('recent', 2)

    expect(cache.get('oldest')).toBe(1)
    cache.set('new', 3)

    expect(cache.size).toBe(2)
    expect(cache.get('recent')).toBeUndefined()
    expect(cache.get('oldest')).toBe(1)
    expect(cache.get('new')).toBe(3)
  })

  it('rejects invalid limits', () => {
    expect(() => new BoundedLruCache(0)).toThrow('maxEntries must be a positive integer')
  })
})
