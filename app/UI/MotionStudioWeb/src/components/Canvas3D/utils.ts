export function shouldResetOrbitControls(previousSignal: number | undefined, nextSignal: number | undefined): boolean {
  return previousSignal !== undefined && nextSignal !== undefined && previousSignal !== nextSignal
}

export type Canvas3DControlMode = 'rotate' | 'move'

export function normalizeCanvas3DZScale(value: number | null | undefined): number {
  if (value == null) return 0.5
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 0.5
  const clamped = Math.min(Math.max(numberValue, 0.1), 2)
  return Math.round(clamped * 100) / 100
}

export function orbitControlFlagsForMode(mode: Canvas3DControlMode): { enableRotate: boolean; enablePan: boolean } {
  return {
    enableRotate: mode === 'rotate',
    enablePan: mode === 'move',
  }
}
