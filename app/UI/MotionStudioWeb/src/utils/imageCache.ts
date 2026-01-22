/**
 * 图像缓存管理器
 * 实现LRU缓存策略，避免重复加载相同图像
 */

interface CacheEntry {
  blob: Blob
  url: string
  size: number
  timestamp: number
  accessCount: number
}

interface CacheOptions {
  maxSize?: number // 最大缓存大小（字节），默认100MB
  maxItems?: number // 最大缓存项数，默认50
  maxAge?: number // 最大缓存年龄（毫秒），默认30分钟
}

export class ImageCache {
  private cache = new Map<string, CacheEntry>()
  private totalSize = 0
  private options: Required<CacheOptions>

  constructor(options: CacheOptions = {}) {
    this.options = {
      maxSize: options.maxSize ?? 100 * 1024 * 1024, // 100MB
      maxItems: options.maxItems ?? 50,
      maxAge: options.maxAge ?? 30 * 60 * 1000, // 30分钟
    }

    // 定期清理过期缓存
    setInterval(() => this.cleanup(), 60 * 1000) // 每分钟清理一次
  }

  /**
   * 生成缓存键
   */
  private generateKey(url: string, width?: number, height?: number): string {
    return `${url}_${width || 'auto'}_${height || 'auto'}`
  }

  /**
   * 获取缓存的图像
   */
  get(url: string, width?: number, height?: number): string | null {
    const key = this.generateKey(url, width, height)
    const entry = this.cache.get(key)

    if (!entry) return null

    // 检查是否过期
    if (Date.now() - entry.timestamp > this.options.maxAge) {
      this.delete(key)
      return null
    }

    // 更新访问信息
    entry.accessCount++
    entry.timestamp = Date.now()

    return entry.url
  }

  /**
   * 添加图像到缓存
   */
  async set(url: string, width: number | undefined, height: number | undefined, blob: Blob): Promise<string> {
    const key = this.generateKey(url, width, height)
    const size = blob.size

    // 如果已存在，先删除旧的
    if (this.cache.has(key)) {
      this.delete(key)
    }

    // 检查是否超过单个项大小限制
    const maxItemSize = this.options.maxSize * 0.3 // 单个项不超过总大小的30%
    if (size > maxItemSize) {
      console.warn(`Image too large to cache: ${size} bytes`)
    }

    // 确保有足够空间
    while (this.totalSize + size > this.options.maxSize || this.cache.size >= this.options.maxItems) {
      const firstKey = this.cache.keys().next().value
      if (firstKey) {
        this.delete(firstKey)
      } else {
        break
      }
    }

    // 创建对象URL
    const objectUrl = URL.createObjectURL(blob)

    // 添加到缓存
    this.cache.set(key, {
      blob,
      url: objectUrl,
      size,
      timestamp: Date.now(),
      accessCount: 1,
    })

    this.totalSize += size

    return objectUrl
  }

  /**
   * 删除缓存项
   */
  private delete(key: string): void {
    const entry = this.cache.get(key)
    if (entry) {
      URL.revokeObjectURL(entry.url)
      this.cache.delete(key)
      this.totalSize -= entry.size
    }
  }

  /**
   * 清理过期和最少使用的缓存
   */
  private cleanup(): void {
    const now = Date.now()
    const entries = Array.from(this.cache.entries())

    // 按访问频率和时间排序
    entries.sort((a, b) => {
      const scoreA = a[1].accessCount / (now - a[1].timestamp)
      const scoreB = b[1].accessCount / (now - b[1].timestamp)
      return scoreA - scoreB
    })

    // 删除最少使用的和过期的
    let cleaned = 0
    for (const [key, entry] of entries) {
      if (now - entry.timestamp > this.options.maxAge || cleaned > entries.length * 0.2) {
        this.delete(key)
        cleaned++
      }
    }
  }

  /**
   * 清空缓存
   */
  clear(): void {
    for (const key of this.cache.keys()) {
      this.delete(key)
    }
    this.totalSize = 0
  }

  /**
   * 获取缓存统计信息
   */
  getStats() {
    return {
      size: this.cache.size,
      totalSize: this.totalSize,
      totalSizeMB: (this.totalSize / (1024 * 1024)).toFixed(2),
      maxSizeMB: (this.options.maxSize / (1024 * 1024)).toFixed(2),
      usagePercent: ((this.totalSize / this.options.maxSize) * 100).toFixed(2),
    }
  }

  /**
   * 预热缓存（批量加载）
   */
  async warmup(urls: string[], onProgress?: (current: number, total: number) => void): Promise<void> {
    for (let i = 0; i < urls.length; i++) {
      const url = urls[i]
      const key = this.generateKey(url)

      if (!this.cache.has(key)) {
        try {
          const response = await fetch(url)
          const blob = await response.blob()
          await this.set(url, undefined, undefined, blob)
        } catch (error) {
          console.error(`Failed to warmup cache for ${url}:`, error)
        }
      }

      onProgress?.(i + 1, urls.length)
    }
  }
}

// 创建全局缓存实例
export const globalImageCache = new ImageCache()

/**
 * 通过缓存的图像加载函数
 */
export async function loadImageWithCache(
  url: string,
  width?: number,
  height?: number,
  cache: ImageCache = globalImageCache
): Promise<string> {
  // 检查缓存
  const cachedUrl = cache.get(url, width, height)
  if (cachedUrl) {
    return cachedUrl
  }

  // 加载图像
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Failed to load image: ${response.statusText}`)
  }

  const blob = await response.blob()

  // 添加到缓存
  return cache.set(url, width, height, blob)
}
