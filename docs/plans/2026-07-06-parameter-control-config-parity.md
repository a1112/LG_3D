# Parameter Control Config Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close Python-compatible behavior for `/control/config`, `POST /control/set_config`, `/control/set_property`, and the React `/system` parameter-control panel without unsafe writes to production `Control.json`.

**Architecture:** Treat `app/Server/api/ApiServerControl.py` plus `app/Base/utils/ControlManagement.py` as the contract: `get_config()` returns the in-memory `control.config`, `set_config(data)` performs a shallow `dict.update(data)`, `set_property(key, value)` writes a top-level key, and neither mutation persists back to `Control.json`. Rust must mirror this in-memory behavior while using explicit config-path overrides for tests, and React must present the operator workflow without implying nested dotted keys are deep writes unless the backend actually supports that.

**Tech Stack:** Python FastAPI reference routes, Rust Axum API state, JSON `Control.json`, React Query, Ant Design system diagnostics panel, Vitest, focused Rust route tests, isolated browser QA.

---

### Task 1: Capture Python `ControlManagement` reference semantics

**Files:**
- Create: `test/control_config_parity/test_control_management_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing Python reference tests**

Capture these exact semantics:

```python
def test_set_config_is_shallow_update():
    control = ControlManagement.__new__(ControlManagement)
    control.config = {"render": {"mode": "old", "max": 10}, "lower_limit": -75}
    result = control.set_config({"render": {"mode": "new"}})
    assert result is None
    assert control.config == {"render": {"mode": "new"}, "lower_limit": -75}
```

Required cases:
- `get_config()` returns the same in-memory config object shape.
- `set_config(data)` returns `None`, which FastAPI serializes as JSON `null`.
- `set_config(data)` is shallow and replaces a nested object at the top-level key.
- `set_property(key, value)` writes a top-level key exactly as supplied.
- `set_property("render.mode", "x")` creates/updates a literal `render.mode` key, not `config["render"]["mode"]`.
- Numeric query values arrive as strings through FastAPI query parsing.

**Step 2: Run reference tests**

Run: `pytest test/control_config_parity/test_control_management_reference.py -v`

Expected: FAIL until the tests isolate `ControlManagement` from background thread startup and encode the current Python behavior.

**Step 3: Add matching Rust tests**

Add route tests for:
- `GET /control/config` returns the initial config snapshot.
- `POST /control/set_config` returns raw JSON `null`.
- `POST /control/set_config` performs shallow top-level merge.
- `GET /control/set_property?key=render.mode&value=x` writes a literal top-level `render.mode` key.
- Missing `key` or `value` returns FastAPI-compatible `422` validation JSON.

**Step 4: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test control_config -- --nocapture`

Expected: FAIL for any mismatch with Python reference behavior.

### Task 2: Lock config-path priority and non-persistence behavior

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Create: `docs/control-config-paths.md`

**Step 1: Write failing config-path tests**

Required path priority:
- `RUST_API_CONTROL_CONFIG` explicit file wins.
- `CONFIG_3D_DIR/configs/Control.json` wins when `CONFIG_3D_DIR` is set.
- `D:\CONFIG_3D\configs\Control.json` wins in production when present.
- Repo fallback `CONFIG_3D/configs/Control.json` is used only when production config is absent.
- Missing config returns `{}` rather than failing startup.

**Step 2: Run focused path tests**

Run: `cargo test --target-dir target-codex-test control_config_path -- --nocapture`

Expected: FAIL until all path-priority cases are covered.

**Step 3: Assert no mutation persists to disk**

Write tests that:
- Seed `Control.json` on disk.
- Call `POST /control/set_config` and `/control/set_property`.
- Read the disk file after route calls.
- Assert disk content is unchanged.
- Assert subsequent `GET /control/config` in the same Rust app sees the in-memory mutation.

**Step 4: Correct Rust state behavior minimally**

Keep mutations in `ApiState` memory. Do not write to `Control.json` unless a future explicit persistence route is added.

**Step 5: Document operator implications**

In `docs/control-config-paths.md`, state that `/control/*` affects runtime process memory only, and production `Control.json` remains the startup source of truth until the service restarts.

### Task 3: Align OpenAPI and validation behavior

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing OpenAPI/validation tests**

Required cases:
- `POST /control/set_config` requestBody schema matches FastAPI's untyped object body named `Data`.
- Mutation routes document JSON `null` response.
- `GET /control/set_property` has required string query parameters `key` and `value`.
- Missing `key` or `value` returns `422` with FastAPI-compatible `missing` validation body.

**Step 2: Run focused OpenAPI tests**

Run: `cargo test --target-dir target-codex-test openapi_json_describes_control -- --nocapture`

Expected: PASS after OpenAPI and validation parity is locked.

### Task 4: Correct React service helpers and UI semantics

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/controlConfig.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/controlConfig.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/index.tsx`

**Step 1: Write failing service-helper tests**

Required cases:
- `buildControlConfigPath()` returns `/control/config`.
- `buildSetControlConfigPath()` returns `/control/set_config`.
- `buildSetControlPropertyPath('save path', 'D:\Control Data')` URL-encodes exactly like FastAPI query expectations.
- `controlApi.setConfig()` posts raw object body.
- `controlApi.setProperty()` sends stringified values.

**Step 2: Run focused service tests**

Run: `npm test -- api controlConfig --runInBand`

Expected: PASS for route construction and encoding.

**Step 3: Write UI helper tests for dotted-key risk**

Current `buildControlConfigRows()` flattens nested records into dotted keys. That is useful for display, but Python `set_property` treats dotted keys literally. Add explicit metadata:

```ts
export interface ControlConfigRow {
  key: string
  value: string
  writable: boolean
  path: string[]
}
```

Required behavior:
- Top-level scalar keys are writable through `set_property`.
- Nested scalar display rows are either marked read-only or route through `set_config` with a full shallow replacement payload.
- Object/array values are displayed as JSON but not silently sent as malformed strings unless the operator explicitly edits raw value mode.

**Step 4: Update `/system` parameter-control panel**

Keep the manual key/value entry for power users, but make the generated row list honest:
- Top-level rows can populate the send form directly.
- Nested display rows show a read-only hint unless full-config update is implemented.
- After successful mutation, invalidate `['control', 'config']` and show the returned `null` without treating it as a failed response.
- Empty `{}` still renders the existing clear empty state.

**Step 5: Run focused React tests**

Run: `npm test -- controlConfig SystemDiagnostics api --runInBand`

Expected: PASS for display, writable-row behavior, and mutation calls.

### Task 5: Add isolated browser QA for runtime-only writes

**Files:**
- Create: `scripts/control_config_parity/check_control_config_runtime.ps1`
- Create: `docs/control-config-browser-qa.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the isolated checker script**

The script must require a temporary control config path unless `-AllowProductionConfig` is passed:

```powershell
$env:RUST_API_CONTROL_CONFIG = "$env:TEMP\lg3d-control\Control.json"
```

It should seed a small config:

```json
{"lower_limit": -75, "upper_limit": 75, "render": {"mode": "prod"}}
```

**Step 2: Check API behavior before UI**

Use:

```powershell
Invoke-RestMethod http://127.0.0.1:5011/control/config
Invoke-RestMethod 'http://127.0.0.1:5011/control/set_property?key=lower_limit&value=-64.5'
```

Assert the file on disk is unchanged while same-process GET reflects the runtime mutation.

**Step 3: Browser QA flow**

In React `/system`:
- Confirm seeded rows render.
- Click a top-level row and send a changed value.
- Confirm success toast and refreshed JSON preview.
- Confirm nested rows do not imply deep-write support unless full-config update is implemented.
- Confirm empty config still shows `Control.json 暂无可显示参数`.

**Step 4: Restore state**

Stop the isolated service if started by the script and remove the temporary config directory.

### Task 6: Final evidence and ledger update

**Files:**
- Modify: `docs/control-config-paths.md`
- Modify: `docs/control-config-browser-qa.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Run focused Python reference checks**

Run: `pytest test/control_config_parity -v`

Expected: PASS for Python contract capture.

**Step 2: Run focused Rust checks**

Run: `cargo test --target-dir target-codex-test control_config control_config_path openapi_json_describes_control -- --nocapture`

Expected: PASS for path, route, non-persistence, validation, and OpenAPI behavior.

**Step 3: Run focused UI checks**

Run: `npm test -- api controlConfig SystemDiagnostics --runInBand`

Expected: PASS for React helper and panel behavior.

**Step 4: Run isolated browser QA**

Run the checker with a temporary `RUST_API_CONTROL_CONFIG` and document the before/after API payloads and UI observations.

**Step 5: Update parity rows only after evidence exists**

Move `Parameter control config` and `Parameter control API helpers` from Partial only after focused tests and isolated browser QA are documented. Do not require production `Control.json` writes because Python itself does not persist these route mutations.

**Step 6: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/control_config_parity scripts/control_config_parity docs

git commit -m "api: close parameter control parity"
```
