export interface SpeedtestUploadSummary {
  filename: string
  fileSize: string
  elapsed: string
  speed: string
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function readNumber(record: Record<string, unknown>, keys: string[]): number | null {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'number' && Number.isFinite(value)) return value
    if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) return Number(value)
  }
  return null
}

function readString(record: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value
  }
  return ''
}

export function formatSpeedtestUploadResult(value: unknown): SpeedtestUploadSummary | null {
  const record = asRecord(value)
  const filename = readString(record, ['filename', 'file_name', 'name'])
  if (!filename) return null

  const fileSize = readNumber(record, ['file_size_mb', 'fileSizeMb', 'size_mb'])
  const elapsed = readNumber(record, ['upload_time_seconds', 'uploadTimeSeconds', 'elapsed_seconds', 'upload_time_s'])
  const speed = readNumber(record, ['speed_mbps', 'speedMbps', 'mbps', 'upload_speed_mb_s'])

  return {
    filename,
    fileSize: fileSize == null ? '--' : `${fileSize.toFixed(2)} MB`,
    elapsed: elapsed == null ? '--' : `${elapsed.toFixed(3)} s`,
    speed: speed == null ? '--' : `${speed.toFixed(2)} MB/s`,
  }
}
