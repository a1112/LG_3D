import { invoke } from '@tauri-apps/api/core'

export interface NativeWindowState {
  maximized: boolean
  fullscreen: boolean
  focused: boolean
  visible: boolean
  innerSize: string
}

export function hasTauriRuntime() {
  const internals = (window as Window & { __TAURI_INTERNALS__?: { invoke?: unknown } }).__TAURI_INTERNALS__
  return typeof internals?.invoke === 'function'
}

async function callWindowCommand(command: string) {
  if (!hasTauriRuntime()) {
    return
  }
  await invoke(command)
}

export const tauriWindow = {
  startDrag: () => callWindowCommand('start_drag_window'),
  minimize: () => callWindowCommand('minimize_window'),
  toggleMaximize: () => callWindowCommand('toggle_maximize_window'),
  close: () => callWindowCommand('close_window'),
  toggleFullscreen: () => callWindowCommand('toggle_fullscreen_window'),
  getState: async () => {
    if (!hasTauriRuntime()) {
      return null
    }
    return invoke<NativeWindowState>('window_state')
  },
}
