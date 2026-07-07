# Defect Dictionary Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Rust `/defectDict`, `/defectDictAll`, and `POST /setDefectDict` match Python API behavior while keeping production config writes safe and test-isolated.

**Architecture:** Treat `DefectClasses.json` as the source of truth for `/defectDict` and `POST /setDefectDict`, and treat the database `DefectClassDict` table as the source of truth for `/defectDictAll`. Keep React/QML-compatible direct dictionary payloads, but align the Rust POST response and config persistence semantics with Python `ApiSettings.set_defect_dict`.

**Tech Stack:** Rust, Axum, Serde JSON, existing Rust route tests, Python references `app/Server/api/ApiDataBase.py`, `app/Server/api/ApiSettings.py`, `app/Base/property/DefectClassesProperty.py`, QML references `Api_DataBase.qml` and `DefectClassPop.qml`, React `DefectClassModal`.

---

### Task 1: Align `POST /setDefectDict` response body with Python `null`

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing test**

Update or add a focused test proving Python-compatible response body. Python `ApiSettings.set_defect_dict()` does not return a value, so FastAPI returns JSON `null`.

```rust
#[tokio::test]
async fn set_defect_dict_returns_python_null_response() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("defect temp root");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        serde_json::to_vec(&json!({
            "data": {},
            "default": {"level": 4, "color": "#FFA500", "show": true}
        }))
        .expect("defect json"),
    )
    .expect("write defect config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/setDefectDict",
        json!({
            "新缺陷": {"level": "2", "color": "#00FF00", "show": "true", "name": "新缺陷", "num": 0}
        }),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = response_json(response).await;
    assert_eq!(body, Value::Null);
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test set_defect_dict_returns_python_null_response --test routes
```

Expected: FAIL because Rust currently returns `{"status":"success","count":...}`.

**Step 3: Write minimal implementation**

Change `set_defect_dict` to return `Ok(Json(Value::Null))` after writing the config. Do not change persistence in this task.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test set_defect_dict_returns_python_null_response --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: match setDefectDict response"
```

### Task 2: Preserve all non-`data` config sections during save

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Write the failing test**

Python `DefectClassesProperty.set_data()` mutates only `self.config["data"]`, then saves the whole config. That preserves `default`, `name_map`, and any future top-level metadata.

```rust
#[tokio::test]
async fn set_defect_dict_preserves_default_name_map_and_metadata() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("defect temp root");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        serde_json::to_vec(&json!({
            "data": {"旧缺陷": {"level": 1, "color": "#111111", "show": false}},
            "default": {"level": 4, "color": "#FFA500", "show": true},
            "name_map": {"c": "边部褶皱"},
            "operator_note": "keep me"
        }))
        .expect("defect json"),
    )
    .expect("write defect config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/setDefectDict",
        json!({"新缺陷": {"level": "2", "color": "#00FF00", "show": "true"}}),
    )
    .await;

    assert_eq!(response.status(), StatusCode::OK);
    let persisted: Value =
        serde_json::from_slice(&fs::read(&defect_config_path).expect("persisted config")).expect("json");
    assert_eq!(persisted["data"]["新缺陷"]["level"], "2");
    assert_eq!(persisted["default"]["level"], 4);
    assert_eq!(persisted["name_map"]["c"], "边部褶皱");
    assert_eq!(persisted["operator_note"], "keep me");
    assert!(persisted["data"].get("旧缺陷").is_none());
}
```

**Step 2: Run test to verify it fails only if preservation is incomplete**

Run:

```powershell
cd app/Server/rust_api_service
cargo test set_defect_dict_preserves_default_name_map_and_metadata --test routes
```

Expected: PASS if current implementation already preserves arbitrary top-level keys; otherwise FAIL and identify which key is lost.

**Step 3: Write minimal implementation if needed**

Keep reading the existing object, replace only `data`, and leave all other keys untouched. If the config file is missing, initialize from `default_defect_dict()`.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test set_defect_dict_preserves_default_name_map_and_metadata --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "api: preserve defect config metadata"
```

### Task 3: Match Python invalid-payload behavior deliberately

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the characterization test**

Python endpoint type is `data: dict`. FastAPI returns a 422 validation error for non-object JSON. Rust currently accepts `Json<Value>` and returns a custom 200 error object for non-object payloads. Lock the Python-compatible behavior.

```rust
#[tokio::test]
async fn set_defect_dict_rejects_non_object_payload_like_fastapi_dict() {
    let response = request_json_body(app_with_seed_data(), "POST", "/setDefectDict", json!(["bad"])).await;

    assert_eq!(response.status(), StatusCode::UNPROCESSABLE_ENTITY);
    let body = response_json(response).await;
    assert_eq!(body["detail"][0]["type"], "dict_type");
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test set_defect_dict_rejects_non_object_payload_like_fastapi_dict --test routes
```

Expected: FAIL because Rust currently returns 200 with `{"status":"error",...}`.

**Step 3: Write minimal implementation**

Return a FastAPI-style 422 body for non-object payloads:

```json
{
  "detail": [
    {
      "type": "dict_type",
      "loc": ["body"],
      "msg": "Input should be a valid dictionary",
      "input": [...]
    }
  ]
}
```

Use the same helper style as other FastAPI validation mirrors in `routes.rs`.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test set_defect_dict_rejects_non_object_payload_like_fastapi_dict --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: validate defect dict payload"
```

### Task 4: Ensure `/defectDict` and `/defectDictAll` remain separate sources of truth

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Add source-separation coverage**

`/defectDict` should return `DefectClasses.json`. `/defectDictAll` should return database rows from `DefectClassDict`.

```rust
#[tokio::test]
async fn defect_dict_routes_keep_config_and_database_sources_separate() {
    let _env_lock = lock_test_env();
    let root = unique_temp_dir();
    fs::create_dir_all(&root).expect("defect temp root");
    let defect_config_path = root.join("DefectClasses.json");
    fs::write(
        &defect_config_path,
        serde_json::to_vec(&json!({
            "data": {"配置缺陷": {"level": 1, "color": "#111111", "show": true}},
            "default": {"level": 4, "color": "#FFA500", "show": true}
        }))
        .expect("defect json"),
    )
    .expect("write defect config");
    let _defect_guard = set_env_var_guard("RUST_API_DEFECT_CLASSES_CONFIG", &defect_config_path);

    let repository = InMemoryCoilRepository::new().with_defect_classes(vec![DefectClassDictRow {
        id: 9,
        defect_class: 90,
        defect_name: "数据库缺陷".to_string(),
        defect_type: Some("surface".to_string()),
        defect_color: Some("#999999".to_string()),
        defect_level: Some(3),
        visible: Some(1),
        defect_desc: None,
    }]);
    let app = build_app(ApiState::new(Arc::new(repository)));

    let (_, config_body) = request_json(app.clone(), "GET", "/defectDict").await;
    let (_, db_body) = request_json(app, "GET", "/defectDictAll").await;

    assert!(config_body["data"].get("配置缺陷").is_some());
    assert!(config_body["data"].get("数据库缺陷").is_none());
    assert_eq!(db_body[0]["defectName"], "数据库缺陷");
}
```

**Step 2: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test defect_dict_routes_keep_config_and_database_sources_separate --test routes
```

Expected: PASS if current behavior is already correct.

**Step 3: Update ledger**

Document that config and database dictionary routes intentionally use different sources, matching Python.

**Step 4: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs docs/rust-tauri-parity.md
git commit -m "api: document defect dictionary sources"
```

### Task 5: Frontend response handling smoke for Python `null`

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/components/DefectClassModal/DefectClassModal.test.tsx` or existing component test file
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts` if route builder coverage is needed

**Step 1: Write the failing frontend test if needed**

React should treat any 2xx response from `defectConfigApi.setDefectDict` as success, including `null`.

```tsx
it('treats Python null setDefectDict response as a successful save', async () => {
  // Mock defectConfigApi.setDefectDict to resolve null.
  // Open DefectClassModal, edit a row, click 保存.
  // Expect success message and refetch without reading status/count.
})
```

**Step 2: Run test to verify**

Run:

```powershell
cd app/UI/MotionStudioWeb
npm test -- src/components/DefectClassModal
```

Expected: PASS if component already ignores response body.

**Step 3: Minimal implementation if needed**

Do not parse `status` or `count`; keep success based on resolved promise.

**Step 4: Run test**

Run:

```powershell
cd app/UI/MotionStudioWeb
npm test -- src/components/DefectClassModal
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/UI/MotionStudioWeb/src/components/DefectClassModal app/UI/MotionStudioWeb/src/services/api.test.ts
git commit -m "ui: accept defect dict null save response"
```

### Task 6: Focused verification before changing status

**Files:**
- Modify only if verification exposes regressions.
- Read: `docs/rust-tauri-parity.md`

**Step 1: Run focused Rust route tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test defect_dict --test routes
cargo test set_defect_dict --test routes
```

Expected: PASS.

**Step 2: Run focused frontend tests**

Run:

```powershell
cd app/UI/MotionStudioWeb
npm test -- src/utils/defectClassConfig.test.ts src/components/DefectClassModal
```

Expected: PASS.

**Step 3: Optional safe live POST**

Only with explicit user authorization and a temp config path:

```powershell
$env:RUST_API_DEFECT_CLASSES_CONFIG='C:\Users\10428\AppData\Local\Temp\DefectClasses-test.json'
```

Start Rust API on a non-conflicting port, POST a tiny direct dictionary payload, and confirm:

- HTTP status 200.
- Body is JSON `null`.
- `data` section is replaced.
- `default`, `name_map`, and extra top-level keys are preserved.
- No production `D:\CONFIG_3D\configs\DefectClasses.json` file is touched.

**Step 4: Ledger update**

If focused tests pass and safe temp-config live POST passes, update `docs/rust-tauri-parity.md` defect dictionary row to say POST contract is verified with isolated config. Keep `Partial` unless production-config live mutation is intentionally exercised or explicitly deemed unnecessary for parity evidence.
