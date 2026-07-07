# Test Mode Settings and Tauri Title Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close parity for `/settings/test_mode`, `/settings/test_mode_status`, React settings/diagnostics test-mode controls, and packaged Tauri window-title behavior.

**Architecture:** Use Python `app/Server/api/ApiSettings.py` and QML `App.qml` / `OtherSetting.qml` as the reference. Rust must preserve Python's response shape, config-file write behavior, and runtime-mode semantics while React/Tauri distinguish persisted config-file state from effective runtime test mode and update the visible title/badge without unsafe writes to production config during tests.

**Tech Stack:** Rust Axum routes, Python FastAPI reference API, JSON config files, React Query, React settings drawer, Tauri packaged window title, Vitest, focused Rust route tests, browser QA, safe temporary-config harness.

---

### Task 1: Lock Python test-mode API contract

**Files:**
- Create: `test/test_mode_parity/test_api_settings_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing Python reference tests**

Capture these reference cases from `app/Server/api/ApiSettings.py`:

```python
def test_get_test_mode_reads_existing_config(tmp_path, monkeypatch):
    config = tmp_path / 'test_mode_config.json'
    config.write_text('{"test_mode": true, "other": 1}', encoding='utf-8')
    # Patch CONFIG.base_config_folder to tmp_path.
    # Assert GET /settings/test_mode returns {"test_mode": true}.
```

Required cases:
- Missing config file returns `CONFIG.developer_mode`.
- Existing config returns `config["test_mode"]` with default `false` when key is missing.
- POST creates parent directory, preserves unrelated config keys, writes `test_mode`, calls runtime developer-mode setter, and returns `{"status":"success","test_mode": enabled}`.
- `/settings/test_mode_status` returns exactly five fields in Python order: `config_file_exists`, `config_file_value`, `developer_mode`, `is_local`, `config_file_path`.
- Malformed JSON or write failure returns Python-style `500` with Chinese `detail` text.

**Step 2: Run Python reference tests**

Run: `pytest test/test_mode_parity/test_api_settings_reference.py -v`

Expected: FAIL until tests patch the Python config object correctly and encode the current contract.

**Step 3: Add matching Rust route tests**

Use `RUST_API_TEST_MODE_CONFIG` to keep writes in a temporary path. Add tests for GET, POST, status, key preservation, malformed JSON, and write failure where feasible.

**Step 4: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test settings_test_mode -- --nocapture`

Expected: FAIL for any behavior that diverges from the captured Python contract.

### Task 2: Correct Rust config path ownership and runtime semantics

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing path-priority tests**

Required cases:
- `RUST_API_TEST_MODE_CONFIG` wins for tests and isolated browser QA.
- Existing `D:\CONFIG_3D\test_mode_config.json` wins over repo-local fallback in production-like mode.
- Repo-local `CONFIG_3D/test_mode_config.json` is used only when production config is absent.
- Missing config writes to repo-local fallback only when no production config exists.
- Response `config_file_path` reports the exact selected path.

**Step 2: Run focused tests**

Run: `cargo test --target-dir target-codex-test test_mode_config_path -- --nocapture`

Expected: FAIL until path selection is unambiguous.

**Step 3: Correct path selection minimally**

Keep the existing helper names if possible:

```rust
fn test_mode_config_path(project_root: &Path) -> PathBuf
fn config_file_test_mode_enabled(project_root: &Path) -> bool
fn read_test_mode_config(path: &Path) -> Option<bool>
```

Do not add a new config file format.

**Step 4: Align effective runtime mode**

Python has two distinct ideas:
- Persisted switch: `config_file_value` from `test_mode_config.json`.
- Runtime mode: `CONFIG.developer_mode`, changed by POST in the running Python process.

Rust should make this distinction explicit in tests. If the replacement chooses effective runtime as `API_DEVELOPER_MODE || config_file_value`, document it as an intentional Rust/Tauri compatibility bridge and ensure React labels it correctly.

**Step 5: Run focused tests again**

Run: `cargo test --target-dir target-codex-test settings_test_mode test_mode_config_path -- --nocapture`

Expected: PASS for status shape, path ownership, and write semantics.

### Task 3: Lock React status parsing, settings switch, and diagnostics display

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/testMode.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/testMode.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/SettingsPanel/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/SettingsPanel/SettingsPanel.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/index.tsx`

**Step 1: Write failing utility tests**

Required cases:
- `getConfiguredTestMode()` reads only persisted switch fields (`config_file_value`, legacy `test_mode`, `enabled`).
- `getRuntimeTestMode()` reads `developer_mode || configured`.
- `getTestModeLabel()` returns `生产模式`, `测试模式`, or `测试模式（环境）`.
- `buildQmlWindowTitle()` returns `涟钢3D端面检测系统 - [测试模式]` only when runtime test mode is effective.
- `buildQmlInfoSettingRows()` shows `TestData/125143` and `TestData (测试数据)` only in runtime test mode.

**Step 2: Run focused utility tests**

Run: `npm test -- testMode --runInBand`

Expected: PASS after parsing semantics are locked.

**Step 3: Write settings panel tests**

Assert:
- The `其他` tab contains exactly one persisted test-mode switch.
- The switch checked state comes from `config_file_value`, not `developer_mode` alone.
- The runtime badge can still show `测试模式（环境）` when env mode is active but config switch is false.
- On switch change, React posts `{enabled:boolean}` to `/settings/test_mode` and invalidates `/settings/test_mode_status`.
- Failure shows an error and does not optimistically lie about the status.

**Step 4: Run focused settings tests**

Run: `npm test -- SettingsPanel testMode --runInBand`

Expected: PASS for switch/display parity.

**Step 5: Add diagnostics display tests if current coverage is missing**

Assert `/system` uses the same status helpers for the test-mode card and runtime info row.

### Task 4: Add browser QA with isolated config ownership

**Files:**
- Create: `scripts/test_mode_parity/check_test_mode_toggle.ps1`
- Create: `docs/test-mode-browser-qa.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write an isolated toggle smoke script**

The script should start or target a Rust API instance with an explicit temporary config path:

```powershell
$env:RUST_API_TEST_MODE_CONFIG = "$env:TEMP\lg3d-test-mode\test_mode_config.json"
```

It must refuse to write `D:\CONFIG_3D\test_mode_config.json` unless `-AllowProductionConfig` is explicitly passed.

**Step 2: Check API status before UI toggle**

The script should call:

```powershell
Invoke-RestMethod http://127.0.0.1:5011/settings/test_mode_status
Invoke-RestMethod http://127.0.0.1:5011/settings/test_mode
```

Record the selected `config_file_path`, `config_file_exists`, and initial value.

**Step 3: Browser QA flow**

Using the active Vite/Tauri Web preview:
- Open settings drawer.
- Navigate to `其他`.
- Toggle `测试模式` on.
- Confirm `/settings/test_mode_status` refreshes.
- Confirm the titlebar badge changes to `测试模式` or `测试模式（环境）` as appropriate.
- Toggle it off and confirm status returns.

**Step 4: Restore temporary state**

The smoke script must restore or delete the temporary config file. It must not mutate production config during default runs.

### Task 5: Validate packaged Tauri window title and badge

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/components/Layout/MainLayout.tsx`
- Modify: `app/UI/MotionStudioWeb/src-tauri/src/main.rs`
- Create: `docs/test-mode-tauri-title-qa.md`

**Step 1: Write helper-level tests for title decisions**

The logic should remain in `buildQmlWindowTitle()` and not be duplicated in Tauri Rust. React owns the title text from `/settings/test_mode_status`.

**Step 2: Add packaged QA recipe**

Document a controlled run:

```powershell
$env:RUST_API_TEST_MODE_CONFIG = "$env:TEMP\lg3d-test-mode-tauri\test_mode_config.json"
```

Then verify:
- Production mode title is `涟钢3D端面检测系统`.
- Test mode title is `涟钢3D端面检测系统 - [测试模式]`.
- Titlebar badge matches the status helper label.
- Restarting the packaged app preserves the persisted config value.
- `API_DEVELOPER_MODE=true` shows test-mode title without flipping the persisted switch.

**Step 3: Correct title update path if needed**

If packaged Tauri does not reflect `document.title`, add or reuse a Tauri command/event to set the native window title from the React helper output. Keep browser behavior unchanged.

**Step 4: Run focused title checks**

Run: `npm test -- testMode MainLayout --runInBand`

Run packaged QA manually or through an existing safe harness.

Expected: title and badge match QML in browser and packaged shell.

### Task 6: Final evidence and ledger update

**Files:**
- Modify: `docs/test-mode-browser-qa.md`
- Modify: `docs/test-mode-tauri-title-qa.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Run focused API checks**

Run: `pytest test/test_mode_parity -v`

Run: `cargo test --target-dir target-codex-test settings_test_mode test_mode_config_path -- --nocapture`

Expected: PASS for Python/Rust API parity.

**Step 2: Run focused UI checks**

Run: `npm test -- testMode SettingsPanel MainLayout --runInBand`

Expected: PASS for parsing, settings switch, and title decisions.

**Step 3: Run isolated browser QA**

Run the new smoke script with a temporary `RUST_API_TEST_MODE_CONFIG`, then record status payloads and UI observations.

**Step 4: Run packaged Tauri title QA**

Use a temporary config path and record title/badge observations before and after restart.

**Step 5: Update parity rows only after evidence exists**

Move `Test mode settings/status` and `Test-mode window title` from Partial only after the API tests, UI tests, isolated browser QA, and packaged Tauri title QA are all documented.

**Step 6: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/test_mode_parity scripts/test_mode_parity docs

git commit -m "ui: close test mode parity"
```
