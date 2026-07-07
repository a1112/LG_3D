import { describe, expect, it } from 'vitest'

import { normalizeCanvas3DZScale, orbitControlFlagsForMode, shouldResetOrbitControls } from './utils'

describe('shouldResetOrbitControls', () => {
  it('does not reset on initial mount or unchanged signals', () => {
    expect(shouldResetOrbitControls(undefined, undefined)).toBe(false)
    expect(shouldResetOrbitControls(undefined, 0)).toBe(false)
    expect(shouldResetOrbitControls(3, 3)).toBe(false)
  })

  it('resets only when DataShow sends a new reset signal', () => {
    expect(shouldResetOrbitControls(0, 1)).toBe(true)
    expect(shouldResetOrbitControls(4, 5)).toBe(true)
  })
})

describe('normalizeCanvas3DZScale', () => {
  it('matches the QML View3DZScaleBtn range and step', () => {
    expect(normalizeCanvas3DZScale(null)).toBe(0.5)
    expect(normalizeCanvas3DZScale(Number.NaN)).toBe(0.5)
    expect(normalizeCanvas3DZScale(0.01)).toBe(0.1)
    expect(normalizeCanvas3DZScale(3)).toBe(2)
    expect(normalizeCanvas3DZScale(0.555)).toBe(0.56)
  })
})

describe('orbitControlFlagsForMode', () => {
  it('maps QML 3D rotate and move modes onto OrbitControls flags', () => {
    expect(orbitControlFlagsForMode('rotate')).toEqual({ enableRotate: true, enablePan: false })
    expect(orbitControlFlagsForMode('move')).toEqual({ enableRotate: false, enablePan: true })
  })
})
