export type CoilCheckStatus = 0 | 1 | 2

export interface CoilCheckState {
  coilId: number
  status: CoilCheckStatus
  msg: string
}

export interface CoilCheckOption {
  status: CoilCheckStatus
  label: string
  color: 'yellow' | 'green' | 'red'
}

export type QmlCoilCheckStatusClass = 'coil-check-none' | 'coil-check-pass' | 'coil-check-rework'

export const COIL_CHECK_OPTIONS: CoilCheckOption[] = [
  { status: 2, label: '返修', color: 'red' },
  { status: 0, label: '未确认', color: 'yellow' },
  { status: 1, label: '通过', color: 'green' },
]

const QML_SELECT_MENU_COLORS: Record<CoilCheckStatus, string> = {
  2: '#f44336',
  0: '#ffeb3b',
  1: '#4caf50',
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {}
}

function normalizeStatus(value: unknown): CoilCheckStatus {
  const status = Number(value)
  if (status === 1 || status === 2) return status
  return 0
}

export function normalizeCoilCheck(value: unknown, fallbackCoilId = 0): CoilCheckState {
  const record = asRecord(value)
  return {
    coilId: Number(record.secondaryCoilId ?? record.coilId ?? record.Id ?? fallbackCoilId) || fallbackCoilId,
    status: normalizeStatus(record.status),
    msg: typeof record.msg === 'string' ? record.msg : '',
  }
}

export function resolveCoilCheck(
  remoteValue: unknown,
  fallbackCoilId = 0,
  localValue: CoilCheckState | null = null,
): CoilCheckState {
  const remote = normalizeCoilCheck(remoteValue, fallbackCoilId)
  if (localValue && localValue.coilId === remote.coilId) {
    return localValue
  }
  return remote
}

export function getCoilCheckOption(status: unknown): CoilCheckOption {
  const normalized = normalizeStatus(status)
  return COIL_CHECK_OPTIONS.find((option) => option.status === normalized) ?? COIL_CHECK_OPTIONS[1]
}

export function resolveQmlCoilCheckStatus(value: unknown): CoilCheckStatus {
  const record = asRecord(value)
  const children = record.childrenCoilCheck
  if (!Array.isArray(children) || children.length === 0) return 0

  return normalizeStatus(asRecord(children[children.length - 1]).status)
}

export function getQmlCoilCheckStatusClass(value: unknown): QmlCoilCheckStatusClass {
  const status = resolveQmlCoilCheckStatus(value)
  if (status === 1) return 'coil-check-pass'
  if (status === 2) return 'coil-check-rework'
  return 'coil-check-none'
}

export function getQmlCoilCheckSelectColor(status: unknown): string {
  return QML_SELECT_MENU_COLORS[normalizeStatus(status)]
}

export function buildCoilCheckPayload(coilId: number, status: CoilCheckStatus, msg = ''): CoilCheckState {
  return { coilId, status, msg }
}
