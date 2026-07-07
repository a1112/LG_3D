# Software Update End-to-End Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close QML-compatible software-update behavior from Rust `/software_update/manifest` and `/updates/{file_name}` through React/Tauri check, download, open-folder, open-package, and exit-and-install actions.

**Architecture:** Use QML `OtherSetting/SoftwareUpdate.qml` as the UI contract and Rust as the replacement update host. Keep the Rust manifest/package routes stable and metadata-driven, keep React browser-preview behavior safe, and validate installer-launch side effects only with controlled stub packages or harmless executables so production installers are never launched accidentally during automated checks.

**Tech Stack:** Rust Axum API, Tauri native commands, React settings drawer, Zustand persisted settings, browser `fetch` streaming, Vitest, Rust route tests, controlled manual/packaged Tauri QA.

---

### Task 1: Lock manifest field compatibility and URL derivation

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/UI/MotionStudioWeb/src/utils/softwareUpdate.ts`
- Test: `app/UI/MotionStudioWeb/src/utils/softwareUpdate.test.ts`

**Step 1: Write failing Rust manifest tests**

Cover every field shape QML accepts:

```rust
#[tokio::test]
async fn software_update_manifest_preserves_qml_alias_fields() {
    // Assert version/latest_version/latestVersion/download_url/downloadUrl/package_url/packageUrl/file_name/fileName/release_notes/releaseNotes.
}
```

Required cases:
- Explicit `RUST_API_SOFTWARE_UPDATE_URL` wins when provided.
- `RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE` derives `/updates/{file_name}` when URL is absent.
- Explicit `RUST_API_SOFTWARE_UPDATE_FILE_NAME` is sanitized but not path-expanded.
- Empty release notes stay as a string or list exactly as QML can render.
- Invalid local package path does not advertise a broken package URL unless an explicit URL was configured.

**Step 2: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test software_update_manifest -- --nocapture`

Expected: FAIL until the manifest behavior is fully encoded.

**Step 3: Correct manifest generation minimally**

Keep route shape unchanged:

```text
GET /software_update/manifest
GET /updates/{file_name}
```

Do not introduce a new update API or nested manifest format.

**Step 4: Write React normalization tests**

Assert `normalizeSoftwareUpdateManifest()` accepts Python/QML/Rust aliases:

```ts
expect(normalizeSoftwareUpdateManifest({ latestVersion: '0.2.4', packageUrl: '/updates/app.exe' })).toMatchObject({
  version: '0.2.4',
  downloadUrl: '/updates/app.exe',
})
```

**Step 5: Run focused React utility tests**

Run: `npm test -- softwareUpdate --runInBand`

Expected: PASS for alias parsing and URL derivation.

### Task 2: Close package download route semantics

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/UI/MotionStudioWeb/src/utils/softwareUpdate.ts`
- Test: `app/UI/MotionStudioWeb/src/utils/softwareUpdate.test.ts`

**Step 1: Write failing package route tests**

Required cases:
- Correct configured filename returns `application/octet-stream`.
- `Content-Length` equals the file length.
- `Content-Disposition` includes the attachment filename.
- Encoded path traversal such as `..%5Capp.exe`, `%2e%2e/app.exe`, and nested `folder/app.exe` is rejected.
- Mismatched filename returns Python/FastAPI-compatible not-found behavior rather than leaking the configured path.

**Step 2: Run focused route tests**

Run: `cargo test --target-dir target-codex-test software_update_package -- --nocapture`

Expected: FAIL until route behavior is locked.

**Step 3: Correct route behavior minimally**

Do not serve arbitrary files from a directory. Only serve the single configured `RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE` whose sanitized filename matches the path parameter.

**Step 4: Write streaming download utility tests**

Cover these UI cases:
- Progress with known `Content-Length`.
- Progress with missing `Content-Length`.
- Native direct write to default download directory.
- Save-dialog fallback.
- Browser Blob fallback.
- Download cancellation or fetch failure leaves no false saved-path state.

**Step 5: Run focused UI tests**

Run: `npm test -- softwareUpdate --runInBand`

Expected: PASS for stream, save, and fallback behavior.

### Task 3: Match QML settings-panel state and controls

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/components/SettingsPanel/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/SettingsPanel/SettingsPanel.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/stores/uiSettingsStore.ts`
- Test: `app/UI/MotionStudioWeb/src/stores/uiSettingsStore.test.ts`

**Step 1: Write failing settings UI tests**

Required controls and states:
- Current version displays the Rust/Tauri app version used by the shell.
- Manifest URL defaults to active API base plus `/software_update/manifest`.
- Optional package URL overrides manifest download URL only when non-empty.
- Latest version displays `未获取` before check.
- Release notes render after check.
- `下载更新` is enabled when either a checked manifest or manual package URL exists.
- `打开目录` is available before package download and opens the default download directory.
- `打开安装包` and `退出并安装` stay disabled until a native saved path exists.

**Step 2: Run focused settings tests**

Run: `npm test -- SettingsPanel softwareUpdate uiSettingsStore --runInBand`

Expected: FAIL until the UI state machine is fully encoded.

**Step 3: Correct UI state minimally**

Keep the existing `软件更新` group under `其他`. Do not move this into a new route or titlebar action.

**Step 4: Run focused tests again**

Run: `npm test -- SettingsPanel softwareUpdate uiSettingsStore --runInBand`

Expected: PASS for settings-state parity.

### Task 4: Validate Tauri native open/install behavior with safe targets

**Files:**
- Modify: `app/UI/MotionStudioWeb/src-tauri/src/main.rs`
- Modify: `app/UI/MotionStudioWeb/src/utils/softwareUpdate.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/softwareUpdate.test.ts`
- Create: `docs/software-update-tauri-qa.md`

**Step 1: Write failing native-command tests or command-level assertions**

If current Tauri tests exist, add cases for:
- `open_path` accepts a downloaded `.exe`, `.msi`, or `.zip` path.
- `open_path` rejects empty paths and clearly unsafe path strings.
- `close_app` is called only after `open_path` succeeds for `install` target.
- `folder` target resolves the containing folder for a saved package path.
- Empty saved path plus `folder` opens the default download directory.

**Step 2: Run focused tests**

Run: `npm test -- softwareUpdate --runInBand`

Run Tauri-side focused tests only if they already exist and can be run without launching the real app.

Expected: FAIL until install sequencing is encoded.

**Step 3: Correct open/install sequencing**

The helper contract should stay simple:

```ts
await openPath(packagePath)
if (target === 'install') {
  await closeApp()
}
```

Do not close the app when `openPath` fails.

**Step 4: Add safe packaged QA notes**

Document a manual/controlled QA recipe that uses a harmless stub executable or `.zip`, not a production installer:

```text
1. Start Rust API with RUST_API_SOFTWARE_UPDATE_PACKAGE_FILE pointing at a harmless test package.
2. Open packaged Tauri app.
3. Check update.
4. Download update.
5. Click 打开目录.
6. Click 打开安装包.
7. Click 退出并安装 and confirm the app window exits only after the open command succeeds.
```

### Task 5: Add end-to-end checker for API-to-UI update flow

**Files:**
- Create: `scripts/software_update_parity/check_software_update_flow.py`
- Create: `docs/software-update-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the bounded checker script**

The script should accept explicit API URL and package path. It must not download or launch arbitrary internet URLs.

```bash
python scripts/software_update_parity/check_software_update_flow.py --api http://127.0.0.1:5011 --package D:\Temp\MotionStudio_test.zip
```

**Step 2: Check stable API behavior**

Verify:
- Manifest status `200`.
- Alias fields are present.
- Resolved package URL is same-origin or explicitly allowed.
- Package route returns expected content type, length, and filename headers.
- Package bytes match the configured local file for the controlled sample.

**Step 3: Document accepted samples**

Record package file type, size, manifest URL, package URL, response headers, and whether UI/Tauri side-effect actions were manually exercised.

**Step 4: Update parity rows only after evidence exists**

Rows `Software update manifest/package` and `Software update settings` can move from Partial only after focused route tests, UI tests, the checker, and safe packaged-Tauri QA are documented.

### Task 6: Final focused verification gates

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/software-update-tauri-qa.md`
- Modify: `docs/software-update-parity-samples.md`

**Step 1: Run focused API checks**

Run: `cargo test --target-dir target-codex-test software_update -- --nocapture`

Expected: PASS for manifest and package route tests.

**Step 2: Run focused UI checks**

Run: `npm test -- softwareUpdate SettingsPanel uiSettingsStore --runInBand`

Expected: PASS for normalization, download, persisted settings, and SettingsPanel controls.

**Step 3: Run bounded checker**

Run the checker with a harmless local package and explicit API URL.

Expected: PASS with documented manifest/package metadata.

**Step 4: Run packaged Tauri QA manually or through an existing safe harness**

Do not use a production installer for this gate. The final evidence must show that `打开安装包` launches the saved package and `退出并安装` closes the Tauri app only after launch succeeds.

**Step 5: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb scripts/software_update_parity docs

git commit -m "ui: close software update parity"
```
