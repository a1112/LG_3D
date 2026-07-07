# Camera Service Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring Rust camera status, adjustment, reconnect, alarm, and camera-data routes to Python/QML parity with clear no-hardware tests and safe live-hardware verification boundaries.

**Architecture:** Preserve the existing Rust offline fallback and mock capture-service tests, but make the proxy contract explicit and complete. Mirror Python `app/Server/api/ApiDataBase.py` routing to the capture service, keep QML `CameraSetting.qml` save/reconnect expectations intact, and add a staged verification path that never changes real exposure/gain or reconnects hardware unless explicitly authorized.

**Tech Stack:** Rust, Axum route tests, local mock HTTP capture service, Python references `app/Server/api/ApiDataBase.py`, capture-service references `app/CapTrue/Server.py` and `app/CapTrue/CapTure.py`, QML references `Api_DataBase.qml` and `CameraSetting.qml`, React `SystemDiagnostics` / `SettingsPanel` camera adjustment UI.

---

### Task 1: Lock Python POST proxy paths for capture-service mode

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing test**

Python `_camera_service_post()` maps:

- `POST /camera_adjust/{camera_key}` to capture service `POST /cameras/{camera_key}/params`
- `POST /camera_adjust/{camera_key}/reconnect` to capture service `POST /cameras/{camera_key}/reconnect`

Add or tighten mock-service assertions that record the exact requested downstream path and JSON body.

```rust
#[tokio::test]
async fn camera_adjust_post_uses_python_capture_service_paths_and_payload() {
    let capture = spawn_mock_capture_service(vec![
        MockCaptureResponse::post_json(
            "/cameras/Cap_S_D/params",
            json!({"ok": true, "saved": true, "source": "capture"}),
        ),
        MockCaptureResponse::post_json(
            "/cameras/Cap_S_D/reconnect",
            json!({"ok": true, "message": "reconnecting"}),
        ),
    ])
    .await;
    let _env_lock = lock_test_env();
    let _config_guard = write_capture_config_with_api_server(capture.host(), capture.port());

    let params_response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/camera_adjust/Cap_S_D",
        json!({"exposureTime": 12345, "gain": 17, "save": true}),
    )
    .await;
    assert_eq!(params_response.status(), StatusCode::OK);

    let reconnect_response =
        request_json_body(app_with_seed_data(), "POST", "/camera_adjust/Cap_S_D/reconnect", json!({})).await;
    assert_eq!(reconnect_response.status(), StatusCode::OK);

    assert_eq!(capture.requests(), vec![
        ("POST".to_string(), "/cameras/Cap_S_D/params".to_string(), json!({"exposureTime": 12345, "gain": 17, "save": true})),
        ("POST".to_string(), "/cameras/Cap_S_D/reconnect".to_string(), json!({})),
    ]);
}
```

**Step 2: Run test to verify**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_adjust_post_uses_python_capture_service_paths_and_payload --test routes
```

Expected: PASS if existing mock coverage already locks this exactly, otherwise FAIL and identify the mismatch.

**Step 3: Minimal implementation if needed**

Ensure Rust `camera_service_post()` uses:

- `/cameras/{camera_key}/params` for params
- `/cameras/{camera_key}/reconnect` for reconnect

Do not change GET fallback behavior in this task.

**Step 4: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_adjust_post_uses_python_capture_service_paths_and_payload --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: lock camera adjustment proxy paths"
```

### Task 2: Lock Python legacy per-camera fallback POST behavior

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing test**

Python uses legacy per-camera `serverIp/serverPort` when the capture service base URL is unavailable:

- params -> `{legacy_base}/camera/params`
- reconnect -> `{legacy_base}/camera/reconnect`

```rust
#[tokio::test]
async fn camera_adjust_post_falls_back_to_legacy_camera_service_when_capture_service_missing() {
    let legacy = spawn_mock_capture_service(vec![
        MockCaptureResponse::post_json("/camera/params", json!({"ok": true, "legacy": true})),
        MockCaptureResponse::post_json("/camera/reconnect", json!({"ok": true, "legacy": true})),
    ])
    .await;
    let _env_lock = lock_test_env();
    let _config_guard = write_capture_config_without_api_server_with_camera_port("Cap_S_D", legacy.host(), legacy.port());

    let params_response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/camera_adjust/Cap_S_D",
        json!({"exposureTime": 222, "gain": 3, "save": false}),
    )
    .await;
    assert_eq!(params_response.status(), StatusCode::OK);

    let reconnect_response =
        request_json_body(app_with_seed_data(), "POST", "/camera_adjust/Cap_S_D/reconnect", json!({})).await;
    assert_eq!(reconnect_response.status(), StatusCode::OK);

    assert_eq!(legacy.request_paths(), vec!["/camera/params", "/camera/reconnect"]);
}
```

**Step 2: Run test to verify failure or pass**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_adjust_post_falls_back_to_legacy_camera_service_when_capture_service_missing --test routes
```

Expected: FAIL if Rust only supports capture-service paths.

**Step 3: Minimal implementation**

Mirror Python `_camera_service_post()`:

- if no capture service base URL and legacy base URL exists, send to legacy path.
- if neither exists, return `502 {"detail":"相机服务端口未配置"}`.

**Step 4: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_adjust_post_falls_back_to_legacy_camera_service_when_capture_service_missing --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: proxy legacy camera adjustments"
```

### Task 3: Mirror Python POST error bodies for missing service and upstream failures

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write missing-service test**

```rust
#[tokio::test]
async fn camera_adjust_post_returns_python_502_when_no_service_port_configured() {
    let _env_lock = lock_test_env();
    let _config_guard = write_capture_config_without_api_server_and_without_camera_ports("Cap_S_D");

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/camera_adjust/Cap_S_D",
        json!({"exposureTime": 1, "gain": 0, "save": true}),
    )
    .await;

    assert_eq!(response.status(), StatusCode::BAD_GATEWAY);
    let body = response_json(response).await;
    assert_eq!(body["detail"], "相机服务端口未配置");
}
```

**Step 2: Write upstream-error test**

Mock capture service returns HTTP 400 with a JSON body, then verify Rust returns Python-style 502 with a detail string rather than silently converting to offline success.

**Step 3: Run tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_adjust_post_returns_python_502 --test routes
```

Expected: FAIL if status/detail differs.

**Step 4: Minimal implementation**

Return Python-compatible `502` for request failures and invalid JSON responses. Keep 404 behavior for missing configured camera key.

**Step 5: Run tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_adjust_post_returns_python_502 --test routes
```

Expected: PASS.

**Step 6: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: mirror camera proxy errors"
```

### Task 4: Lock live capture status shape against `app/CapTrue`

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Add mock `app/CapTrue` status payload**

Use fields from `CapTure.get_capture_status()`:

```json
{
  "key": "Cap_S_D",
  "name": "近端下方",
  "sn": "SN001",
  "cap2D": true,
  "cap3D": true,
  "captureRunning": true,
  "startedAt": 123.0,
  "lastFrameTime2D": 456.0,
  "lastFrameAge2D": 1.2,
  "lastFrameTime3D": 457.0,
  "lastFrameAge3D": 2.3,
  "lastError2D": "",
  "lastError3D": "",
  "missedInWithoutFrame": 0,
  "reconnectAttempts": 1,
  "coilId": 193113,
  "coilNo": "19311300",
  "serviceReady": true,
  "camera2D": {"ok": true, "connected": true, "message": "ok", "exposureTime": 12345, "gain": 17}
}
```

Assert `/camera_adjust` keeps nested `capture`, exposes `lastFrameAge3D`, and uses `camera2D` as the public status like Python.

**Step 2: Run focused test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_adjust_uses_captrue_status_shape --test routes
```

Expected: PASS if existing live-status mapping is complete.

**Step 3: Implement only if needed**

Patch field mapping without changing offline fallback.

**Step 4: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs docs/rust-tauri-parity.md
git commit -m "api: lock captrue camera status shape"
```

### Task 5: Add safe live-hardware verification checklist

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Create: `docs/plans/2026-07-06-camera-service-parity.md` already in this plan

**Step 1: Document read-only live checks**

Read-only checks that are safe without changing camera state:

```powershell
Invoke-RestMethod http://127.0.0.1:5011/capture_status
Invoke-RestMethod http://127.0.0.1:5011/camera_adjust
Invoke-RestMethod http://127.0.0.1:5011/cameraAlarm
Invoke-RestMethod http://127.0.0.1:5011/cameraData/193113/S_D
```

Expected:

- same configured camera keys as Python
- no Rust-only fields in Python-compatible offline status
- live capture payload returned as-is for `/capture_status` when capture service is online
- `/camera_adjust` rows expose QML fields used by `CameraSetting.qml`

**Step 2: Document write-hazard checks**

Do not run without explicit operator approval:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:5011/camera_adjust/S_D -Body '{"exposureTime":12345,"gain":17,"save":false}' -ContentType 'application/json'
Invoke-RestMethod -Method Post http://127.0.0.1:5011/camera_adjust/S_D/reconnect -Body '{}' -ContentType 'application/json'
```

Risks:

- exposure/gain changes may affect production images
- reconnect may interrupt capture
- `save=true` may persist hardware parameter files

**Step 3: Ledger update**

Keep status `Partial` until:

- mock capture-service POST tests pass
- read-only live checks pass
- write-hazard checks are explicitly authorized and pass against a non-production or maintenance-window camera service

### Task 6: Frontend UI contract check for POST response body agnosticism

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/SystemDiagnostics.test.ts` or related camera UI tests
- Modify: `app/UI/MotionStudioWeb/src/components/SettingsPanel/SettingsPanel.test.tsx` if present

**Step 1: Write response-body-agnostic test**

QML ignores POST response body and refreshes after success. React should do the same.

```tsx
it('refreshes camera rows after a successful save regardless of response body shape', async () => {
  // mock camera adjust POST to resolve either null or {ok:true}
  // click 保存
  // expect camera_adjust query invalidated/refetched and success state rendered
})
```

**Step 2: Run focused frontend test**

Run:

```powershell
cd app/UI/MotionStudioWeb
npm test -- src/pages/SystemDiagnostics src/components/SettingsPanel
```

Expected: PASS if current UI already ignores body shape.

**Step 3: Minimal implementation if needed**

Do not branch on `ok` or `status` from POST response unless Python/QML does. Treat resolved promise as success and refresh.

**Step 4: Commit**

```powershell
git add app/UI/MotionStudioWeb/src/pages/SystemDiagnostics app/UI/MotionStudioWeb/src/components/SettingsPanel
git commit -m "ui: refresh camera settings after save"
```

### Task 7: Focused verification before changing status

**Files:**
- Modify only if verification exposes regressions.
- Read: `docs/rust-tauri-parity.md`

**Step 1: Run focused Rust tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test camera_ --test routes
cargo test capture_ --test routes
```

Expected: PASS.

**Step 2: Run focused frontend tests**

Run:

```powershell
cd app/UI/MotionStudioWeb
npm test -- src/services/api.test.ts src/utils/globalAlarm.test.ts src/pages/SystemDiagnostics src/components/SettingsPanel
```

Expected: PASS.

**Step 3: Optional live read-only smoke**

Only with explicit user authorization to query running services:

1. Compare Python and Rust `/capture_status`.
2. Compare Python and Rust `/camera_adjust`.
3. Compare Python and Rust `/cameraAlarm`.
4. Confirm `cameraData` resolves a valid current-coil folder for at least one configured key.

**Step 4: Optional live write smoke**

Only with explicit operator approval and non-production-safe target:

1. Send `save=false` parameter update to one test camera.
2. Send reconnect to one test camera only during a safe maintenance window.
3. Confirm QML/React status refresh behavior.

Do not mark camera service parity complete without either approved live write verification or explicit decision that mock-service write verification is sufficient for the current deployment phase.
