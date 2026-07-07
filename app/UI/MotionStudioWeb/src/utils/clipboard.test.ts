import { describe, expect, it, vi } from 'vitest'

import { copyTextToClipboard } from './clipboard'

describe('clipboard helper', () => {
  it('uses navigator clipboard when it resolves', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    const fallbackCopy = vi.fn()

    await expect(copyTextToClipboard('193113', { writeText, fallbackCopy })).resolves.toBe(true)

    expect(writeText).toHaveBeenCalledWith('193113')
    expect(fallbackCopy).not.toHaveBeenCalled()
  })

  it('falls back when navigator clipboard rejects', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('permission denied'))
    const fallbackCopy = vi.fn().mockReturnValue(true)

    await expect(copyTextToClipboard('193113', { writeText, fallbackCopy })).resolves.toBe(true)

    expect(fallbackCopy).toHaveBeenCalledWith('193113')
  })

  it('falls back when navigator clipboard does not settle quickly', async () => {
    const writeText = vi.fn(() => new Promise<void>(() => {}))
    const fallbackCopy = vi.fn().mockReturnValue(true)

    await expect(copyTextToClipboard('193113', { writeText, fallbackCopy, timeoutMs: 1 })).resolves.toBe(true)

    expect(fallbackCopy).toHaveBeenCalledWith('193113')
  })

  it('returns false when every copy mechanism fails', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('permission denied'))
    const fallbackCopy = vi.fn(() => {
      throw new Error('execCommand unavailable')
    })

    await expect(copyTextToClipboard('193113', { writeText, fallbackCopy })).resolves.toBe(false)
  })
})
