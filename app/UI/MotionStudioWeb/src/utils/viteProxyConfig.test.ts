import { fileURLToPath } from 'node:url'
import { beforeAll, describe, expect, it } from 'vitest'

let viteConfigSource = ''

beforeAll(async () => {
  const { readFileSync } = (await import('node:fs')) as {
    readFileSync: (path: string, encoding: 'utf8') => string
  }

  viteConfigSource = readFileSync(fileURLToPath(new URL('../../vite.config.ts', import.meta.url)), 'utf8')
})

describe('Vite proxy port defaults', () => {
  it('falls back to the non-conflicting Rust API port when env is absent', () => {
    expect(viteConfigSource).toContain("env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5011'")
    expect(viteConfigSource).not.toContain("env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5010'")
  })
})
