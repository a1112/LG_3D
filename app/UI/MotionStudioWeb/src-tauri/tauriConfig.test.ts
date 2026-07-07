import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const tauriDir = path.dirname(fileURLToPath(import.meta.url))
const configPath = path.join(tauriDir, 'tauri.conf.json')
const cargoTomlPath = path.join(tauriDir, 'Cargo.toml')
const startupScriptPath = path.resolve(tauriDir, '..', '..', '..', '..', 'scripts', 'start_rust_motion_studio_dev.ps1')
const rustApiRoutesPath = path.resolve(tauriDir, '..', '..', '..', 'Server', 'rust_api_service', 'src', 'routes.rs')

function readTauriConfig(): Record<string, any> {
  return JSON.parse(readFileSync(configPath, 'utf8')) as Record<string, any>
}

function readBeforeDevCommand(): { script: string; cwd: string } {
  const config = readTauriConfig()
  const command = config.build?.beforeDevCommand
  expect(command && typeof command).toBe('object')
  return command as { script: string; cwd: string }
}

function readRustApiVersion(): string {
  const routes = readFileSync(rustApiRoutesPath, 'utf8')
  const match = routes.match(/async fn version\(\)[\s\S]*?Json\("([^"]+)"\)/)
  expect(match?.[1]).toBeTruthy()
  return match?.[1] ?? ''
}

describe('Tauri development startup configuration', () => {
  it('starts through the shared Rust Motion Studio dev script with a strict web port', () => {
    const config = readTauriConfig()
    const beforeDevCommand = readBeforeDevCommand().script
    const startupScript = readFileSync(startupScriptPath, 'utf8')

    expect(config.build?.devUrl).toBe('http://127.0.0.1:3015')
    expect(beforeDevCommand).toContain('start_rust_motion_studio_dev.ps1')
    expect(beforeDevCommand).toContain('-StrictWebPort')
    expect(beforeDevCommand).not.toBe('npm run dev')
    expect(startupScript).toContain('[switch]$StrictWebPort')
  })

  it('uses a beforeDevCommand script path that resolves from the src-tauri directory', () => {
    const command = readBeforeDevCommand()
    const beforeDevCommand = command.script
    const cwd = path.resolve(tauriDir, command.cwd)
    const match = beforeDevCommand.match(/-File\s+(.+?start_rust_motion_studio_dev\.ps1)\b/)

    expect(existsSync(path.join(cwd, 'package.json'))).toBe(true)
    expect(match?.[1]).toBeTruthy()
    expect(existsSync(path.resolve(cwd, match?.[1] ?? ''))).toBe(true)
  })

  it('keeps the packaged Tauri shell version aligned with the Rust API current version', () => {
    const config = readTauriConfig()
    const cargoToml = readFileSync(cargoTomlPath, 'utf8')
    const rustApiVersion = readRustApiVersion()

    expect(config.version).toBe(rustApiVersion)
    expect(cargoToml).toContain(`version = "${rustApiVersion}"`)
  })
})
