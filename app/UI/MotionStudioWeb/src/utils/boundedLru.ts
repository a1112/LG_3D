export class BoundedLruCache<Key, Value> {
  private readonly values = new Map<Key, Value>()

  constructor(readonly maxEntries: number) {
    if (!Number.isInteger(maxEntries) || maxEntries < 1) {
      throw new Error('maxEntries must be a positive integer')
    }
  }

  get size(): number {
    return this.values.size
  }

  get(key: Key): Value | undefined {
    const value = this.values.get(key)
    if (value === undefined) return undefined

    this.values.delete(key)
    this.values.set(key, value)
    return value
  }

  set(key: Key, value: Value): this {
    this.values.delete(key)
    this.values.set(key, value)
    while (this.values.size > this.maxEntries) {
      const oldestKey = this.values.keys().next().value as Key | undefined
      if (oldestKey === undefined) break
      this.values.delete(oldestKey)
    }
    return this
  }

  delete(key: Key): boolean {
    return this.values.delete(key)
  }

  clear(): void {
    this.values.clear()
  }
}
