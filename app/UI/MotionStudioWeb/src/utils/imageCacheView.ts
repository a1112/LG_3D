export interface ImageCacheStatsView {
  size: number
  totalSize: number
  totalSizeMB: string
  maxSizeMB: string
  maxItems?: number
  usagePercent: string
}

export interface ImageCacheRow {
  label: string
  value: string
}

export function formatImageCacheBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`
  }

  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatFixedNumber(value: string): string {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) {
    return value
  }

  return numericValue.toFixed(1)
}

export function buildImageCacheRows(stats: ImageCacheStatsView): ImageCacheRow[] {
  const rows: ImageCacheRow[] = [
    { label: '缓存项', value: String(stats.size) },
  ]

  if (typeof stats.maxItems === 'number' && Number.isFinite(stats.maxItems)) {
    rows.push({ label: '最大项数', value: String(Math.trunc(stats.maxItems)) })
  }

  rows.push(
    {
      label: '占用空间',
      value: `${formatImageCacheBytes(stats.totalSize)} / ${formatFixedNumber(stats.maxSizeMB)} MB`,
    },
    { label: '使用率', value: `${formatFixedNumber(stats.usagePercent)}%` },
  )

  return rows
}
