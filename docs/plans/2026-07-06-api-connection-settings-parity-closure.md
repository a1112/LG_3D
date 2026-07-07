# API Connection Settings Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the QML-to-Tauri parity gap for API connection settings so the operator can change the service host and ports once and every Rust API, React UI, WebSocket, image, diagnostics, and footer entry follows the same connection model.

**Architecture:** Treat `CoreSetting.qml` and `ApiConfig.qml` as the parity contract: persisted settings own `server_ip`, `server_port`, `databasPort`, `dataPort`, `plcPort`, `alg2dPort`, image-server selection, and all derived HTTP/WS URLs. React keeps those values in `useUiSettingsStore`, applies them to `serviceBaseUrls` through a single runtime connection adapter, and renders both the QML-style footer `ConnectDialog` shortcut and the richer settings-page API service panel. Rust/Tauri only persists and exposes safe desktop configuration; it must not silently probe or launch native tools when validation is unavailable.

**Tech Stack:** Rust, Tauri, React, TypeScript, Zustand, Axios, TanStack Query, Vitest, React Testing Library.

---

### Task 1: Freeze the QML connection contract as tests

**Files:**
- Reference: `app/UI/MotionStudio/qml/Core/CoreSetting.qml`
- Reference: `app/UI/MotionStudio/qml/Api/ApiConfig.qml`
- Reference: `app/UI/MotionStudio/qml/Pages/LeftPage/FootView.qml`
- Reference: `app/UI/MotionStudio/qml/PopupView/Connect/ConnectDialog.qml`
- Modify: `app/UI/MotionStudioWeb/src/stores/uiSettingsStore.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/ConnectSettingsModal/ConnectSettingsModal.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/Layout/MainLayout.test.ts`

**Step 1: Add store contract coverage**

Assert that React defaults and persisted state mirror QML-compatible non-conflicting replica defaults:

```ts
expect(useUiSettingsStore.getState().apiServerIp).toBe('127.0.0.1')
expect(useUiSettingsStore.getState().apiServerPort).toBe(5011)
expect(useUiSettingsStore.getState().databasPort).toBe(6011)
expect(useUiSettingsStore.getState().dataPort).toBe(6013)
expect(useUiSettingsStore.getState().plcPort).toBe(6014)
expect(useUiSettingsStore.getState().alg2dPort).toBe(5011)
expect(useUiSettingsStore.getState().useRustImageServer).toBe(false)
expect(useUiSettingsStore.getState().rustImageServerPort).toBe(6013)
```

**Step 2: Add runtime URL derivation coverage**

In `app/UI/MotionStudioWeb/src/services/api.test.ts`, cover a full operator change:

```ts
const next = applyRuntimeConnectionSettings({
  serverIp: '192.168.99.100',
  serverPort: 5011,
  databasPort: 6011,
  dataPort: 6013,
  plcPort: 6014,
  alg2dPort: 5011,
  useRustImageServer: true,
  rustImageServerPort: 6013,
})

expect(next.apiBaseUrl).toBe('http://192.168.99.100:5011')
expect(next.databaseBaseUrl).toBe('http://192.168.99.100:6011')
expect(next.dataBaseUrl).toBe('http://192.168.99.100:6013')
expect(next.plcBaseUrl).toBe('http://192.168.99.100:6014')
expect(next.alg2dBaseUrl).toBe('http://192.168.99.100:5011')
expect(next.imageBaseUrl).toBe('http://192.168.99.100:6013')
expect(next.apiWsBaseUrl).toBe('ws://192.168.99.100:5011')
```

**Step 3: Add footer and dialog coverage**

Extend the existing `MainLayout` and `ConnectSettingsModal` tests to verify:

```ts
expect(statusbarSource).toContain('{serviceBaseUrls.apiBaseUrl}')
expect(statusbarSource).toContain('setConnectSettingsOpen(true)')
expect(connectModalSource).toContain('Apply')
expect(connectModalSource).toContain('OK')
expect(connectModalSource).toContain('127.0.0.1')
expect(connectModalSource).toContain('192.168.99.100')
```

**Step 4: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/stores/uiSettingsStore.test.ts src/services/api.test.ts src/components/ConnectSettingsModal/ConnectSettingsModal.test.ts src/components/Layout/MainLayout.test.ts
```

Expected when authorized: tests fail before implementation only for missing runtime connection derivation coverage, then pass after Tasks 2-4.

### Task 2: Centralize runtime connection settings in the API service layer

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/stores/uiSettingsStore.ts`

**Step 1: Add a complete connection settings type**

Add a single API service input type so settings, footer dialog, diagnostics, and Tauri bootstrap all apply the same fields:

```ts
export interface RuntimeConnectionSettings {
  serverIp: string
  serverPort: number
  databasPort: number
  dataPort: number
  plcPort: number
  alg2dPort: number
  useRustImageServer: boolean
  rustImageServerPort: number
}
```

**Step 2: Expand `ServiceBaseUrls` only where QML has distinct service URLs**

Keep existing `apiBaseUrl` and `imageBaseUrl`, then add explicit derived bases:

```ts
export interface ServiceBaseUrls {
  apiBaseUrl: string
  imageBaseUrl: string
  databaseBaseUrl: string
  dataBaseUrl: string
  plcBaseUrl: string
  alg2dBaseUrl: string
  apiWsBaseUrl: string
  databaseWsBaseUrl: string
}
```

**Step 3: Implement a pure builder**

```ts
export function buildRuntimeConnectionBaseUrls(settings: RuntimeConnectionSettings): ServiceBaseUrls {
  const host = normalizeApiServerIp(settings.serverIp)
  const apiPort = normalizeApiServerPort(settings.serverPort)
  const databasePort = normalizeQmlServicePort(settings.databasPort, 6011)
  const dataPort = normalizeQmlServicePort(settings.dataPort, 6013)
  const plcPort = normalizeQmlServicePort(settings.plcPort, 6014)
  const alg2dPort = normalizeAlg2dServicePort(settings.alg2dPort)
  const imagePort = settings.useRustImageServer ? normalizeImageServerPort(settings.rustImageServerPort) : apiPort

  return {
    apiBaseUrl: `http://${host}:${apiPort}`,
    imageBaseUrl: `http://${host}:${imagePort}`,
    databaseBaseUrl: `http://${host}:${databasePort}`,
    dataBaseUrl: `http://${host}:${dataPort}`,
    plcBaseUrl: `http://${host}:${plcPort}`,
    alg2dBaseUrl: `http://${host}:${alg2dPort}`,
    apiWsBaseUrl: `ws://${host}:${apiPort}`,
    databaseWsBaseUrl: `ws://${host}:${databasePort}`,
  }
}
```

**Step 4: Apply the full connection atomically**

```ts
export function applyRuntimeConnectionSettings(settings: RuntimeConnectionSettings): ServiceBaseUrls {
  const nextBaseUrls = buildRuntimeConnectionBaseUrls(settings)
  Object.assign(serviceBaseUrls, nextBaseUrls)
  api.defaults.baseURL = nextBaseUrls.apiBaseUrl
  return { ...serviceBaseUrls }
}
```

Keep `applyApiBaseUrlOverride('/api')` for web preview and Vite proxy fallback. It should continue to update only `apiBaseUrl` and image base when image was previously following the main API.

**Step 5: Remove duplicated normalization**

If importing store normalizers from `uiSettingsStore.ts` would introduce a circular dependency, move these pure helpers to a new file:

```text
app/UI/MotionStudioWeb/src/utils/qmlConnectionSettings.ts
```

Then update both the store and service layer to import from that utility.

**Step 6: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/services/api.test.ts src/stores/uiSettingsStore.test.ts
```

Expected when authorized: URL builder, migration, and normalization tests pass.

### Task 3: Make settings-page API service controls apply every dependent URL

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/components/SettingsPanel/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/SettingsPanel/SettingsPanel.test.ts`

**Step 1: Replace single-base apply logic**

Change `applyRuntimeApiConnection` to call the full service-layer adapter:

```ts
const applyRuntimeApiConnection = () => {
  const normalized = {
    serverIp: normalizeApiServerIp(apiServerIpDraft),
    serverPort: normalizeApiServerPort(apiServerPortDraft),
    databasPort,
    dataPort,
    plcPort,
    alg2dPort,
    useRustImageServer,
    rustImageServerPort,
  }

  setApiServerIp(normalized.serverIp)
  setApiServerPort(normalized.serverPort)
  const nextBaseUrls = applyRuntimeConnectionSettings(normalized)
  setCurrentApiBaseUrl(nextBaseUrls.apiBaseUrl)
  queryClient.invalidateQueries()
  message.success(`API连接已切换到 ${nextBaseUrls.apiBaseUrl}`)
}
```

**Step 2: Show QML-derived service preview rows**

Add compact preview rows under the existing `API 服务` group:

```tsx
<div className="settings-service-preview">
  <span>数据库服务</span>
  <code>{runtimeConnectionPreview.databaseBaseUrl}</code>
  <span>数据服务</span>
  <code>{runtimeConnectionPreview.dataBaseUrl}</code>
  <span>PLC服务</span>
  <code>{runtimeConnectionPreview.plcBaseUrl}</code>
  <span>图像服务</span>
  <code>{runtimeConnectionPreview.imageBaseUrl}</code>
  <span>2D算法</span>
  <code>{runtimeConnectionPreview.alg2dBaseUrl}</code>
</div>
```

**Step 3: Preserve the default proxy button**

`恢复默认代理` must remain available in web preview mode and must not erase persisted operator host/port settings. It only switches active Axios routing back to `/api`.

**Step 4: Add tests for full apply intent**

Assert that `SettingsPanel` imports and calls `applyRuntimeConnectionSettings`, renders database/data/PLC/image/2D preview labels, and keeps the 5011 fallback for the main API and 2D algorithm port.

**Step 5: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/components/SettingsPanel/SettingsPanel.test.ts
```

Expected when authorized: source-level parity tests pass.

### Task 4: Make the footer ConnectDialog use the same connection adapter

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/components/ConnectSettingsModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/ConnectSettingsModal/ConnectSettingsModal.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/Layout/MainLayout.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/Layout/MainLayout.test.ts`

**Step 1: Keep the QML shell but route through the full adapter**

`ConnectSettingsModal` should stay QML-like: fixed `500x200`, titleless shell, `连接设置`, `Ip 地址`, `端口号`, shortcut buttons, `Apply`, and `OK`. Its apply handler should still update only the main `server_ip/server_port` fields, but it must call `applyRuntimeConnectionSettings` with the current database/data/PLC/image/2D settings from the store.

**Step 2: Keep `Apply` open and `OK` closing**

```ts
const handleApply = () => applyConnection({ closeAfterApply: false })
const handleOk = () => applyConnection({ closeAfterApply: true })
```

**Step 3: Sync footer text after runtime changes**

`MainLayout` and `OperationSidebar` footer labels should render `serviceBaseUrls.apiBaseUrl` after the adapter mutates the active base. If React does not re-render because `serviceBaseUrls` is a mutable singleton, lift the active base URL into a small Zustand or React state hook that the adapter updates.

**Step 4: Add regression coverage**

Assert that footer click opens `ConnectSettingsModal`, `Apply` does not close, `OK` closes, and shortcut host buttons update the draft IP.

**Step 5: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/components/ConnectSettingsModal/ConnectSettingsModal.test.ts src/components/Layout/MainLayout.test.ts src/components/OperationSidebar/OperationSidebar.test.ts
```

Expected when authorized: QML footer and dialog parity tests pass.

### Task 5: Route all connection-dependent features through derived bases

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/heightPoint.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/reDetection.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/serverState.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/backupImage.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/algTest.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/globalAlarm.ts`
- Modify: related `*.test.ts` files beside each utility

**Step 1: Keep main Rust API endpoints on `apiBaseUrl`**

Core API calls remain on `serviceBaseUrls.apiBaseUrl` unless QML explicitly used `serverUrlDaaBase`, `serverUrlData`, `serverUrlImage`, `serverUrlAlg2D`, or `wsServerUrlDaaBase`.

**Step 2: Move QML database endpoints to `databaseBaseUrl` where split service mode is active**

Paths copied from `Api_DataBase.qml` that are served by the database microservice should use `serviceBaseUrls.databaseBaseUrl` when the Rust API compatibility router does not intentionally proxy them. Keep the Rust API unified route as fallback if the local replica uses a consolidated service.

**Step 3: Move data and image routes to QML-derived bases**

Height line/point, render/error images, classifier image, preview/source/area image helpers, and image health checks should use `dataBaseUrl` or `imageBaseUrl` according to `ApiConfig.qml`.

**Step 4: Move WebSocket builders to QML-derived WS bases**

Use `apiWsBaseUrl` for QML `wsServerUrl` features and `databaseWsBaseUrl` for QML `wsServerUrlDaaBase` features like backup image task progress.

**Step 5: Add targeted tests per route family**

Use table-driven tests with a direct host such as `http://192.168.99.100:5011` to prove each helper emits the same host with the expected QML port.

**Step 6: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/services/api.test.ts src/utils/heightPoint.test.ts src/utils/reDetection.test.ts src/utils/serverState.test.ts src/utils/backupImage.test.ts src/utils/algTest.test.ts src/utils/globalAlarm.test.ts
```

Expected when authorized: every direct-host and Vite-proxy URL test passes.

### Task 6: Persist and bootstrap settings in the Tauri desktop shell

**Files:**
- Modify: `app/UI/MotionStudioWeb/src-tauri/src/main.rs`
- Modify: `app/UI/MotionStudioWeb/src-tauri/src/settings.rs` if it exists; otherwise create it
- Modify: `app/UI/MotionStudioWeb/src/utils/nativeSettings.ts` if it exists; otherwise create it
- Modify: `app/UI/MotionStudioWeb/src/App.tsx` or the nearest bootstrap file

**Step 1: Add safe Tauri commands**

Implement commands that read and write only the desktop replica connection settings file. Do not touch Python QML `settings.ini` unless the operator explicitly chooses an import/export action.

```rust
#[tauri::command]
fn read_connection_settings() -> Result<Option<ConnectionSettings>, String> { ... }

#[tauri::command]
fn write_connection_settings(settings: ConnectionSettings) -> Result<(), String> { ... }
```

**Step 2: Store settings in the app config directory**

Use Tauri's app config directory and a JSON file such as `connection-settings.json`. Validate host strings and clamp ports to `1..=65535` before writing.

**Step 3: Add web preview fallback**

The TypeScript wrapper should return `null` when Tauri APIs are unavailable so browser development continues to use Zustand/localStorage only.

**Step 4: Bootstrap before first API query**

On app start, load Tauri settings, hydrate `useUiSettingsStore`, then call `applyRuntimeConnectionSettings`. Avoid firing data queries against stale `/api` if desktop settings are present.

**Step 5: Add tests where feasible without launching Tauri**

Use TypeScript source tests for the wrapper and Rust unit tests for normalization if the project already has Rust test scaffolding.

**Step 6: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/nativeSettings.test.ts src/stores/uiSettingsStore.test.ts
cargo test --manifest-path src-tauri/Cargo.toml connection_settings
```

Expected when authorized: web fallback tests pass and Rust normalization tests pass.

### Task 7: Add operator-facing diagnostics for the active connection profile

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/serviceConnection.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/globalAlarm.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/GlobalAlarmModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/index.tsx`
- Modify: related tests beside each file

**Step 1: Build per-port probe rows from the active profile**

Represent QML network alarm cards for API, database, data, PLC, image, and 2D algorithm services. Use labels that match operator vocabulary:

```ts
API 5011
数据库 6011
数据 6013
PLC 6014
图像 6013
2D算法 5011
```

**Step 2: Keep probes safe in browser preview**

HTTP health probes should use lightweight endpoints where available. If a service does not expose health, show `未验证` rather than marking it online.

**Step 3: Link docs to the active main API**

The `API 文档` action must open `joinBaseUrl(serviceBaseUrls.apiBaseUrl, '/docs')`, not a hard-coded port.

**Step 4: Add tests**

Assert that changing the connection profile changes all diagnostic URLs and labels.

**Step 5: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/serviceConnection.test.ts src/utils/globalAlarm.test.ts src/components/GlobalAlarmModal/GlobalAlarmModal.test.ts src/pages/SystemDiagnostics/SystemDiagnostics.test.ts
```

Expected when authorized: diagnostic cards and docs links follow the active connection profile.

### Task 8: Manual desktop QA checklist

**Files:**
- No source changes after implementation unless this checklist finds a bug.

**Step 1: Browser preview smoke, only when authorized**

```powershell
cd app\UI\MotionStudioWeb
npm run dev
```

Check:
- Footer URL shows `/api` initially in Vite preview.
- Clicking the footer URL opens the QML-style `连接设置` modal.
- `Apply` changes the active API preview but keeps the modal open.
- `OK` changes the active API preview and closes the modal.
- `恢复默认代理` returns active routing to `/api` without deleting the saved host/port values.

**Step 2: Tauri desktop smoke, only when authorized**

```powershell
cd app\UI\MotionStudioWeb
npm run tauri dev
```

Check:
- Saved host and port are restored after closing and reopening the app.
- API docs opens on the active main API port.
- Image preview and height WebSocket URLs use the derived image/data ports.
- Backup image task WebSocket uses the database WS port when split service mode is active.
- Invalid host strings and invalid ports are normalized rather than persisted raw.

**Step 3: Side-effect guardrails**

Do not run PLC, camera reconnect, backup, database export, or native maintenance actions as part of this connection-settings QA unless separately authorized by the operator.

### Task 9: Documentation and parity ledger closure

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/plans/2026-07-06-api-connection-settings-parity-closure.md` if implementation reveals scope changes

**Step 1: Update the parity row**

After implementation and authorized validation, change the `API connection settings` row from `Partial` to `Complete` only if:
- Main API host/port can be changed from both the settings page and QML-style footer dialog.
- Database, data, PLC, image, 2D, HTTP, and WS derived URLs follow the active host/port settings.
- Tauri desktop restores the same settings on restart.
- Browser preview still supports `/api` proxy mode.
- Diagnostics and API docs links use the active profile.

**Step 2: Record validation commands**

Add the exact commands run and any skipped hardware-side-effect checks to the row notes or PR description.

**Step 3: Commit only if requested**

```powershell
git add app/UI/MotionStudioWeb/src docs/rust-tauri-parity.md docs/plans/2026-07-06-api-connection-settings-parity-closure.md
git commit -m "ui: close api connection settings parity"
```
