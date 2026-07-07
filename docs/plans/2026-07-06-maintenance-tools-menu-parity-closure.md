# Maintenance Tools Menu Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close QML `ToolsMenuView` parity by proving the React/Tauri maintenance tools menu exposes the same operator-visible actions, safe native side effects, service-management popup, and database-backup behavior as the legacy UI.

**Architecture:** Treat `app/UI/MotionStudio/qml/PopupView/ToolsMenu/ToolsMenuView.qml` and `app/UI/MotionStudio/qml/PopupView/ServerMange/ServerMangeView.qml` as the UI source of truth. React should keep the titlebar `主菜单` entry as a compact QML-like menu, model actions in `maintenanceTools.ts`, render them through `MaintenanceMenuModal`, and route native-only side effects through Tauri commands rather than shell-concatenated strings. Dangerous/unimplemented QML actions must stay visible but disabled until their backend behavior is deliberately implemented.

**Tech Stack:** QML reference UI, React/Vite/Tauri TypeScript UI, Ant Design Modal/Button/Tag, Tauri Rust commands, Vitest source/utility tests, Rust unit tests, browser QA in Web preview, optional Tauri manual smoke.

---

### Task 1: Lock QML action inventory and grouping

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/maintenanceTools.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/maintenanceTools.test.ts`
- Reference: `app/UI/MotionStudio/qml/PopupView/ToolsMenu/ToolsMenuView.qml`

**Step 1: Add action inventory tests**

Assert the generated groups exactly mirror QML menu structure:

```ts
expect(groups.map((group) => `${group.key}:${group.title}`)).toEqual([
  'maintenance:维护',
  'feature:功能',
  'system:系统',
])
expect(maintenance.actions.map((action) => action.label)).toEqual([
  '远程到服务器',
  'Ping 服务器',
  '一键恢复',
  '重启全部服务',
  '服务管理',
  '重启服务器',
])
expect(feature.actions.map((action) => `${action.parentLabel}/${action.label}`)).toEqual([
  '数据库备份/备份到 ...',
  '数据库备份/从 备份 恢复',
  '测试/网络测速',
])
expect(system.actions.map((action) => action.label)).toEqual(['退出系统'])
```

**Step 2: Preserve disabled placeholder policy**

Assert unsafe/unimplemented actions remain visible but disabled:

```ts
for (const id of ['restore', 'restartAllServices', 'restartServer', 'restoreFromBackup']) {
  expect(actions.find((action) => action.id === id)).toMatchObject({ enabled: false, status: '待接入' })
}
```

**Step 3: Keep QML network-speed action honest**

QML `网络测速` has no `onClicked`; React may navigate to the existing diagnostics page only if the ledger documents it as a safe enhancement. Add a test that the action is labeled as QML `测试/网络测速` and routes to `/system#network-speedtest`, not a fake backend speed test mutation.

**Step 4: Run focused helper tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/maintenanceTools.test.ts
```

Expected: PASS.

### Task 2: Close compact ToolsMenu modal rendering

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.css`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts`

**Step 1: Assert compact QML menu shape**

Keep tests for:

```text
className="maintenance-menu-modal tools-menu-modal"
title={null}
width={360}
data-qml-tools-menu-view
```

Assert the menu is a single-column compact action list rather than a dashboard card grid.

**Step 2: Add action status rendering tests**

Assert every action renders:

```text
icon cell
label
parent/command preview line
status Tag: 可用 or 待接入
disabled attribute when action.enabled === false
```

**Step 3: Verify mobile bounds in CSS source tests**

Keep tests for:

```css
max-height: min(560px, calc(100vh - 32px))
overflow-y: auto
overflow-x: hidden
grid-template-columns: 1fr
```

Add a CSS assertion that long command previews ellipsize rather than causing horizontal overflow.

**Step 4: Run focused modal tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts
```

Expected: PASS.

### Task 3: Close ServerMangeView popup parity

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/maintenanceTools.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/maintenanceTools.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts`
- Reference: `app/UI/MotionStudio/qml/PopupView/ServerMange/ServerMangeView.qml`

**Step 1: Preserve service-management modal lifecycle**

Assert clicking `服务管理` closes the ToolsMenu shell and opens a separate service-management modal:

```ts
expect(branch).toMatch(/setServiceManagementOpen\(true\)[\s\S]*onClose\(\)[\s\S]*return/)
```

**Step 2: Preserve QML dimensions and title**

Assert React mirrors QML:

```text
width={600}
height/min-height: 400px constrained by viewport
data-qml-server-mange-view
data-qml-server-mange-title
远程服务管理
```

**Step 3: Preserve remote service rows and ports**

Assert rows are:

```text
采集服务 -> databasPort default 6011
数据服务 -> databasPort default 6011
3D服务 -> dataPort default 6013
PLC服务 -> plcPort default 6014
```

Configured `databasPort`, `dataPort`, and `plcPort` must override independently; PLC must not accidentally reuse `dataPort`.

**Step 4: Preserve row actions**

Each row must expose:

```text
打开接口文档 -> enabled, opens http://{host}:{port}/docs through openQmlExternalUrl
重启服务 -> visible, disabled, 待接入
```

Do not enable restart-service until an explicit backend/service-control contract exists.

**Step 5: Run focused service-management tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/maintenanceTools.test.ts src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts
```

Expected: PASS.

### Task 4: Harden Tauri native maintenance commands

**Files:**
- Modify: `app/UI/MotionStudioWeb/src-tauri/src/lib.rs`
- Modify: `app/UI/MotionStudioWeb/src/utils/maintenanceTools.test.ts`

**Step 1: Preserve command specs**

Keep Rust unit tests asserting:

```rust
maintenance_command_spec("remoteDesktop", "192.168.1.20") == CommandSpec {
    program: "mstsc",
    args: vec!["/v", "192.168.1.20"],
    preview: "mstsc /v 192.168.1.20",
}
maintenance_command_spec("pingServer", "192.168.1.20").unwrap().preview == "ping 192.168.1.20 -t"
```

**Step 2: Preserve shell-injection guardrails**

Add cases for:

```rust
"bad host && del C:\\"
"127.0.0.1 & calc"
"http://[::1]:5011/path"
"server-name_01.example.com"
```

Only safe hostnames/IPs should pass. If IPv6 is unsupported, document that as a deliberate safe limitation and keep it disabled in React preview.

**Step 3: Keep unsupported actions rejected**

Assert:

```rust
assert!(maintenance_command_spec("restartServer", "192.168.1.20").is_err());
assert!(maintenance_command_spec("restartAllServices", "192.168.1.20").is_err());
```

**Step 4: Run Tauri Rust unit tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb\src-tauri
cargo test maintenance_
```

Expected: PASS.

### Task 5: Close database backup flow from ToolsMenu

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/backup.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/backup.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts`

**Step 1: Assert QML save-dialog parity**

QML `备份到 ...` calls `dialogs.save_sql`, then `api.save_to_sql(save_file)`, then `Qt.openUrlExternally(save_file)` on success. React/Tauri should assert:

```ts
selectNativeSavePath(defaultName)
runtimeApi.saveToSql(selected.path)
openNativePath(selected.path)
```

**Step 2: Cover result states**

Add tests for:

```text
selected + { state: true } -> { status: 'saved', path }
selected + { state: false } -> { status: 'failed', path }
cancelled -> { status: 'cancelled' }
unavailable -> { status: 'unavailable' }
saveToSql throws -> caller surfaces error message
```

**Step 3: Preserve Web preview fallback**

When native save dialog is unavailable, React should navigate to `/system` and show `Web 预览请在系统诊断中使用数据库备份` rather than attempting a fake browser file write.

**Step 4: Run focused backup/menu tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/backup.test.ts src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts
```

Expected: PASS.

### Task 6: Add browser and Tauri QA checklist

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Optionally create: `docs/checklists/maintenance-tools-menu-qa.md`

**Step 1: Browser QA in Web preview**

When validation is authorized and the Vite app is running, verify:

```text
Main titlebar opens 主菜单
modal has no title and width 360 on desktop
维护 / 功能 / 系统 groups visible
远程到服务器 and Ping 服务器 show command preview but do not launch in Web preview
一键恢复 / 重启全部服务 / 重启服务器 / 从 备份 恢复 are visible disabled
服务管理 opens separate 远程服务管理 modal and closes main menu
服务 rows expose docs button and disabled restart button
mobile 390px viewport has no horizontal overflow
zero fresh console warn/error logs
```

**Step 2: Tauri manual smoke for native side effects**

Only with explicit operator consent, verify:

```text
远程到服务器 invokes mstsc with sanitized host
Ping 服务器 opens a ping window
数据库备份 opens native save dialog, calls /save_to_sql/{path}, opens saved file/path on success
退出系统 closes the Tauri window
```

Do not click service restart, restart all, restart server, restore, or restore-from-backup until those actions are implemented and approved.

**Step 3: Update ledger evidence**

After tests and QA pass, update `Maintenance tools menu` from `Partial` to `Complete` only if:

```text
QML action inventory matches
safe native commands are tested
unsafe actions remain disabled
service management docs/restart row parity is verified
backup flow is verified in Tauri or explicitly documented as Web-only fallback
browser layout QA passes desktop/mobile
```

If native backup/command smoke is not performed, keep `Partial` and document the exact remaining manual verification.

### Task 7: Optional commit only when requested

**Files:**
- Stage only files changed for this plan.

**Step 1: Review changed files**

Run only when commit is requested:

```powershell
git diff -- app/UI/MotionStudioWeb/src/utils/maintenanceTools.ts app/UI/MotionStudioWeb/src/utils/maintenanceTools.test.ts app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/index.tsx app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.css app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts app/UI/MotionStudioWeb/src-tauri/src/lib.rs app/UI/MotionStudioWeb/src/utils/backup.ts app/UI/MotionStudioWeb/src/utils/backup.test.ts docs/rust-tauri-parity.md docs/checklists/maintenance-tools-menu-qa.md
```

**Step 2: Commit**

Run only when commit is requested:

```powershell
git add app/UI/MotionStudioWeb/src/utils/maintenanceTools.ts app/UI/MotionStudioWeb/src/utils/maintenanceTools.test.ts app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/index.tsx app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.css app/UI/MotionStudioWeb/src/components/MaintenanceMenuModal/MaintenanceMenuModal.test.ts app/UI/MotionStudioWeb/src-tauri/src/lib.rs app/UI/MotionStudioWeb/src/utils/backup.ts app/UI/MotionStudioWeb/src/utils/backup.test.ts docs/rust-tauri-parity.md docs/checklists/maintenance-tools-menu-qa.md

git commit -m "ui: close maintenance tools menu parity"
```
