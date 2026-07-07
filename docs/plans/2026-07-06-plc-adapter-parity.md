# PLC Adapter Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Rust PLC routes mirror Python `app/plcServer/server.py` behavior for info, connect, read, and write semantics while preserving a no-hardware test backend.

**Architecture:** Replace the current unconditional fake PLC read path with a small backend abstraction. The default test backend remains deterministic and hardware-free, while the production backend must connect/read/write through a Siemens-compatible implementation or an explicitly configured PLC proxy. Rust route contracts should match the Python FastAPI adapter, including path spelling, type names, config defaults, and error behavior where practical.

**Tech Stack:** Rust, Axum, Serde JSON, Tokio tests, existing `ApiState`, Python reference `app/plcServer/server.py`, Python config reference `app/plcServer/config.py`, optional Siemens/HSL-compatible adapter or HTTP proxy.

---

### Task 1: Lock Python route spelling and startup info contract

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing tests**

Add tests that lock both Python's literal route spelling and the current compatibility aliases.

```rust
#[tokio::test]
async fn plc_info_matches_python_startup_contract() {
    let app = build_app(ApiState::new(Arc::new(InMemoryCoilRepository::new())));

    let response = request_response(app, "GET", "/plc/info/").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = serde_json::from_slice::<Value>(&response_bytes(response).await).expect("plc info json");
    assert_eq!(body["typeList"], json!(["int", "real", "dword", "string", "bytes", "word", "bool"]));
    assert!(body.get("plc_ip").is_some());
    assert!(body.get("rack").is_some());
    assert!(body.get("slot").is_some());
}

#[tokio::test]
async fn plc_connect_supports_python_literal_parentheses_route() {
    let app = build_app(ApiState::new(Arc::new(InMemoryCoilRepository::new())));

    let response = request_response(app, "GET", "/plc/connect/(10.7.8.9)/(1)/(2)").await;

    assert_eq!(response.status(), StatusCode::OK);
    assert_eq!(response_bytes(response).await, Bytes::from_static(b"true"));
}
```

**Step 2: Run tests to verify failure**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_info_matches_python_startup_contract plc_connect_supports_python_literal_parentheses_route --test routes
```

Expected: info likely passes; literal-parentheses connect route fails if only `/plc/connect/{plc_ip}/{rack}/{slot}` is registered.

**Step 3: Write minimal implementation**

Keep existing `/plc/connect/{plc_ip}/{rack}/{slot}` alias for Rust clients, but add Python's literal route:

```rust
.route("/plc/connect/({plc_ip})/({rack})/({slot})", get(plc_connect))
```

If Axum does not support parameter captures inside literal parentheses as expected, add a route for `/plc/connect/:raw` is not acceptable because it changes route shape. Instead, add a small handler for a catch-free exact pattern supported by Axum path syntax and a test proving it matches the Python URL.

**Step 4: Run tests to verify pass**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_info_matches_python_startup_contract plc_connect_supports_python_literal_parentheses_route --test routes
```

Expected: PASS.

**Step 5: Update ledger**

Update `docs/rust-tauri-parity.md` PLC row to say route spelling parity is covered, but real connect/read/write parity remains pending.

**Step 6: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "plc: mirror adapter route spelling"
```

### Task 2: Introduce a PLC backend boundary instead of unconditional fake reads

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Optionally create: `app/Server/rust_api_service/src/plc.rs`
- Modify: `app/Server/rust_api_service/src/lib.rs` if a new module is created
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing test**

The test should prove fake reads are explicitly backend-owned, not hidden in `ApiState::plc_value_read`.

```rust
#[tokio::test]
async fn plc_get_uses_configured_backend_read_bytes() {
    let backend = Arc::new(TestPlcBackend::new().with_read("DB26.2", "int", vec![0x04, 0xD2]));
    let state = ApiState::new(Arc::new(InMemoryCoilRepository::new())).with_plc_backend(backend);
    let app = build_app(state);

    let response = request_response(app, "GET", "/plc/get/DB26.2/int/2").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body = serde_json::from_slice::<Value>(&response_bytes(response).await).expect("plc value json");
    assert_eq!(body, json!(1234));
}
```

**Step 2: Run test to verify failure**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_get_uses_configured_backend_read_bytes --test routes
```

Expected: FAIL because `with_plc_backend` and `TestPlcBackend` do not exist.

**Step 3: Write minimal implementation**

Add a trait:

```rust
trait PlcBackend: Send + Sync {
    fn connect(&self, ip: &str, rack: i64, slot: i64) -> anyhow::Result<()>;
    fn read(&self, addr: &str, type_str: &str, length: usize, runtime: &PlcRuntimeState) -> anyhow::Result<Vec<u8>>;
    fn write(&self, addr: &str, type_str: &str, value: &Value, runtime: &PlcRuntimeState) -> anyhow::Result<Value>;
}
```

Move current fake byte generation into `FakePlcBackend`.

Add to `ApiState`:

```rust
plc_backend: Arc<dyn PlcBackend>,
```

Initialize with `FakePlcBackend` for tests/dev and add:

```rust
pub fn with_plc_backend(mut self, backend: Arc<dyn PlcBackend>) -> Self
```

**Step 4: Run test to verify pass**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_get_uses_configured_backend_read_bytes --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/lib.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "plc: isolate backend reads"
```

### Task 3: Match Python PLC value parsing exactly

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs` or `app/Server/rust_api_service/src/plc.rs`

**Step 1: Write table-driven parsing tests**

Python uses `snap7.util` helpers:

- `get_int(value, 0)`
- `get_real(value, 0)`
- `get_dword(value, 0)`
- `value.decode("utf-8")`
- `bytes(value)`
- `get_word(value, 0)`
- `get_bool(value, 0, 0)`

Add table tests for all supported types:

```rust
#[test]
fn plc_parse_values_match_snap7_big_endian_helpers() {
    assert_eq!(plc_parse_plc_value("int", &[0x04, 0xD2]), Some(json!(1234)));
    assert_eq!(plc_parse_plc_value("word", &[0xAB, 0xCD]), Some(json!(43981)));
    assert_eq!(plc_parse_plc_value("dword", &[0x00, 0x00, 0x04, 0xD2]), Some(json!(1234)));
    assert_eq!(plc_parse_plc_value("real", &123.5_f32.to_be_bytes()), Some(json!(123.5_f32)));
    assert_eq!(plc_parse_plc_value("string", b"ABC"), Some(json!("ABC")));
    assert_eq!(plc_parse_plc_value("bytes", &[1, 2, 3]), Some(json!([1, 2, 3])));
    assert_eq!(plc_parse_plc_value("bool", &[0b0000_0001]), Some(json!(true)));
}
```

**Step 2: Run test to verify failure**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_parse_values_match_snap7_big_endian_helpers --test routes
```

Expected: FAIL if any parser differs from Python/snap7 behavior.

**Step 3: Write minimal implementation**

Update parser only. Do not change route behavior in this task.

Ensure:

- unknown type produces internal-server-error-equivalent route behavior, matching Python's bare `raise`.
- negative `length` keeps Python-like 500 behavior.
- too-short byte buffers return parser failure and route 500.

**Step 4: Run test to verify pass**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_parse_values_match_snap7_big_endian_helpers --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs
git commit -m "plc: match snap7 value parsing"
```

### Task 4: Add Python-compatible write route or document absence explicitly

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Confirm desired route**

Python exposes `write_plc(addr, typeStr, value)` as a function but not as a FastAPI route in `server.py`. Before adding a public Rust route, check UI/API callers:

```powershell
rg --line-number "write_plc|plc/.*/write|/plc/set|PLC_WIDTH_ADDR|DB35.40" app test scripts
```

If no HTTP write route exists in Python callers, do not invent one for Rust.

**Step 2: Write the route-absence test**

If Python has no HTTP write endpoint, lock that Rust also has no public write endpoint:

```rust
#[tokio::test]
async fn plc_write_http_endpoint_is_not_exposed_without_python_route() {
    let app = build_app(ApiState::new(Arc::new(InMemoryCoilRepository::new())));

    let response = request_response(app, "GET", "/plc/write/DB35.40/int/123").await;

    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}
```

**Step 3: Run test**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_write_http_endpoint_is_not_exposed_without_python_route --test routes
```

Expected: PASS if Rust has not invented a write endpoint. If it fails because a route exists, decide whether the route is Rust-only support and document it.

**Step 4: Update ledger**

Clarify `write parity` wording:

- Python has internal `write_plc()` helper for `writePLC.py`.
- Python does not expose a FastAPI write route in `app/plcServer/server.py`.
- Rust should not expose a public write route unless a compatible caller requires it.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs docs/rust-tauri-parity.md
git commit -m "plc: document write parity boundary"
```

### Task 5: Add production PLC backend selection

**Files:**
- Modify: `app/Server/rust_api_service/src/main.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs` or `app/Server/rust_api_service/src/plc.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write backend-selection tests**

The production service should be explicit about fake-vs-real mode:

```rust
#[test]
fn plc_backend_mode_defaults_to_fake_for_no_hardware_dev() {
    assert_eq!(resolve_plc_backend_mode(None), PlcBackendMode::Fake);
}

#[test]
fn plc_backend_mode_accepts_proxy_mode() {
    assert_eq!(resolve_plc_backend_mode(Some("proxy")), PlcBackendMode::Proxy);
}
```

**Step 2: Run tests to verify failure**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_backend_mode --test routes
```

Expected: FAIL until backend mode resolver exists.

**Step 3: Implement minimal backend modes**

Support:

```text
RUST_API_PLC_BACKEND=fake
RUST_API_PLC_BACKEND=proxy
RUST_API_PLC_PROXY_BASE_URL=http://127.0.0.1:1211
```

`proxy` mode can forward to a Python-compatible PLC adapter if direct Siemens/HSL binding from Rust is not available. It should call:

- `GET {base}/plc/connect/({ip})/({rack})/({slot})`
- `GET {base}/plc/get/{addr}/{typeStr}/{length}`

This provides a production migration path without falsely claiming native Siemens protocol parity.

**Step 4: Run tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc_backend_mode --test routes
```

Expected: PASS.

**Step 5: Update ledger**

Update PLC row to distinguish:

- startup info parity
- route spelling parity
- parser parity
- fake backend for no-hardware tests
- proxy/native backend status
- live PLC hardware verification status

**Step 6: Commit**

```powershell
git add app/Server/rust_api_service/src/main.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "plc: select runtime backend mode"
```

### Task 6: Focused verification before claiming PLC parity

**Files:**
- Modify only if verification exposes regressions.
- Read: `docs/rust-tauri-parity.md`

**Step 1: Run focused route tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test plc --test routes
```

Expected: PASS.

**Step 2: Optional no-hardware live smoke**

Only with explicit user authorization to start a service:

```powershell
cd app/Server/rust_api_service
$env:RUST_API_PLC_BACKEND='fake'
cargo run -- --host 127.0.0.1 --port 5011
```

Request:

```powershell
Invoke-RestMethod http://127.0.0.1:5011/plc/info/
Invoke-RestMethod http://127.0.0.1:5011/plc/connect/(192.168.0.1)/(0)/(0)
Invoke-RestMethod http://127.0.0.1:5011/plc/get/DB26.2/int/2
```

Expected: info shape matches Python; connect returns `true`; get returns a parsed fake value.

**Step 3: Optional proxy smoke**

Only with explicit user authorization and a running Python PLC adapter:

```powershell
$env:RUST_API_PLC_BACKEND='proxy'
$env:RUST_API_PLC_PROXY_BASE_URL='http://127.0.0.1:1211'
```

Expected: Rust forwards connect/read to the Python-compatible PLC adapter.

**Step 4: Hardware verification**

Only in a hardware-safe environment:

1. Confirm target PLC IP/rack/slot.
2. Confirm read-only test address.
3. Call Python adapter and Rust adapter for the same address/type/length.
4. Compare response type and value.

Do not mark PLC parity complete without this step for real PLC mode.
