function pad2(value: number): string {
  return String(value).padStart(2, '0')
}

export function formatQmlDateTimeMinute(value: Date): string {
  return [
    value.getFullYear(),
    pad2(value.getMonth() + 1),
    pad2(value.getDate()),
    pad2(value.getHours()),
    pad2(value.getMinutes()),
  ].join('')
}

export function formatQmlTimeText(value: Date): string {
  return `${value.getFullYear()}-${pad2(value.getMonth() + 1)}-${pad2(value.getDate())} ${pad2(
    value.getHours(),
  )}:${pad2(value.getMinutes())}:${pad2(value.getSeconds())}`
}

export function getQmlCurrentDayRange(now = new Date()): [Date, Date] {
  const start = new Date(now)
  start.setHours(0, 0, 0, 0)
  return [start, new Date(now)]
}

export type QmlDateRangeSearch =
  | { kind: 'none' }
  | { kind: 'range'; start: string; end: string }

export function resolveQmlDateRangeSearch(range: [Date | null, Date | null] | null): QmlDateRangeSearch {
  if (!range?.[0] || !range[1]) return { kind: 'none' }
  return {
    kind: 'range',
    start: formatQmlDateTimeMinute(range[0]),
    end: formatQmlDateTimeMinute(range[1]),
  }
}
