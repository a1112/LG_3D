/**
 * 格式化工具函数
 */

/**
 * 格式化日期时间
 */
export function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'

  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  } catch {
    return dateStr
  }
}

/**
 * 格式化数字（保留小数位）
 */
export function formatNumber(value: number, decimals: number = 2): string {
  if (isNaN(value)) return '-'
  return value.toFixed(decimals)
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'

  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))

  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

/**
 * 格式化百分比
 */
export function formatPercent(value: number, decimals: number = 1): string {
  if (isNaN(value)) return '-'
  return (value * 100).toFixed(decimals) + '%'
}

/**
 * 格式化坐标位置
 */
export function formatPosition(x: number, y: number): string {
  return `(${formatNumber(x)}, ${formatNumber(y)})`
}

/**
 * 格式化尺寸
 */
export function formatSize(width: number, height: number): string {
  return `${formatNumber(width)} × ${formatNumber(height)}`
}

/**
 * 截断文本
 */
export function truncateText(text: string, maxLength: number = 50): string {
  if (!text || text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}
