# Current Coil TCP Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Rust `GET /currentCoil` mirror Python `app/Communication/HttpServer.py` by returning the in-memory TCP-decoded coil dictionary rather than synthesizing the response from the latest database coil.

**Architecture:** Add an `ApiState`-owned current-coil memory slot and a packet decoder that mirrors `app/Communication/DecodeData.py`. The HTTP route should return `{}` until the slot is populated, then return the exact decoded dictionary shape. Keep existing database latest-coil behavior out of `/currentCoil`; if the UI needs latest DB fallback, it should use existing coil-list/detail routes rather than this communication-service route.

**Tech Stack:** Rust, Axum, Serde JSON, Tokio tests, existing `InMemoryCoilRepository`, Python reference files `app/Communication/DecodeData.py` and `app/Communication/HttpServer.py`.

---

### Task 1: Lock the startup contract and remove DB fallback from `/currentCoil`

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing test**

Add or replace the current DB-backed `/currentCoil` assertion with a test showing that even when the repository contains latest-coil rows, startup still returns `{}` because no TCP packet has been decoded.

```rust
#[tokio::test]
async fn current_coil_ignores_latest_database_coil_until_tcp_decode_state_exists() {
    let app = app_with_seed_data();

    let response = request_response(app, "GET", "/currentCoil").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body =
        serde_json::from_slice::<Value>(&response_bytes(response).await).expect("currentCoil json");
    assert_eq!(body, json!({}));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test current_coil_ignores_latest_database_coil_until_tcp_decode_state_exists --test routes
```

Expected: FAIL because the current handler reads `repository.latest_coil()` and returns a synthesized coil object when seed data exists.

**Step 3: Write minimal implementation**

Add a current-coil memory field to `ApiState`:

```rust
current_coil: Arc<Mutex<Value>>,
```

Initialize it to `json!({})` in `ApiState::new`.

Change `current_coil(State(state): State<ApiState>)` to return only a snapshot of this field:

```rust
async fn current_coil(State(state): State<ApiState>) -> Json<Value> {
    Json(state.current_coil_snapshot())
}
```

Add:

```rust
fn current_coil_snapshot(&self) -> Value {
    self.current_coil
        .lock()
        .map(|coil| coil.clone())
        .unwrap_or_else(|_| json!({}))
}
```

Do not call `repository.latest_coil()` in this route.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test current_coil_ignores_latest_database_coil_until_tcp_decode_state_exists --test routes
```

Expected: PASS.

**Step 5: Update parity ledger**

Update `docs/rust-tauri-parity.md` `/currentCoil` row to say Rust startup behavior now matches Python communication-service startup behavior and DB fallback has been removed, but packet decoding is still pending until Task 2.

**Step 6: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: align currentCoil startup contract"
```

### Task 2: Decode Python-compatible TCP coil packets into Rust state

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Optionally create: `app/Server/rust_api_service/src/tcp_decode.rs`
- Modify: `app/Server/rust_api_service/src/lib.rs` if a new module is created
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing decoder test**

Use the Python reference hex packet from `app/Communication/DecodeData.py` and assert the JSON field shape. Do not assert exact `CreateTime` content; assert it exists as a string or object depending on the chosen Rust serializer, then document the chosen compatibility shape.

```rust
#[test]
fn decodes_python_current_coil_packet_shape() {
    let packet = hex::decode(
        "6000C35DF1000000345630353139323430300000000000005132333542202020202020202020202020202020ED0400000080F744E204000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    )
    .expect("reference packet");

    let body = decode_current_coil_packet(&packet).expect("decoded packet");

    assert_eq!(body["len"], json!(96));
    assert_eq!(body["head"], json!(93));
    assert_eq!(body["Coil_ID"], json!("4V050192400"));
    assert_eq!(body["Steel_Grade"], json!("Q235B"));
    assert_eq!(body["act_w"], json!(1261));
    assert_eq!(body["coil_dia"], json!(0));
    assert_eq!(body["FM_Tar_Thickness"], json!(1.98));
    assert_eq!(body["FM_Tar_Width"], json!(1250));
    assert_eq!(body["coil_in_dia"], json!(0));
    assert_eq!(body["sp01"].as_array().expect("sp01").len(), 10);
    assert!(body.get("CreateTime").is_some());
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test decodes_python_current_coil_packet_shape --test routes
```

Expected: FAIL because no Rust decoder exists yet.

**Step 3: Write minimal implementation**

Implement Python's `DATA_PACKET_FORMAT = "3h2c16s20shhfhh10f"` equivalent as little-endian decoding:

```rust
const CURRENT_COIL_PACKET_SIZE: usize = 100;
```

Decode fields in order:

```text
i16 len
i16 head
i16 telCount
u8 outCode
u8 sp00
16 bytes Coil_ID, UTF-8 lossy, trim, remove NUL
20 bytes Steel_Grade, UTF-8 lossy, trim
i16 act_w
i16 coil_dia
f32 FM_Tar_Thickness divided by 1000.0
i16 FM_Tar_Width
i16 coil_in_dia
10 x f32 sp01
```

Return `None` or an error for invalid lengths, matching Python's `return None` on invalid packet size.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test decodes_python_current_coil_packet_shape --test routes
```

Expected: PASS.

**Step 5: Update parity ledger**

Update `docs/rust-tauri-parity.md` to say Rust has a Python-compatible packet decoder, but live TCP socket ingestion remains pending until Task 3.

**Step 6: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: decode current coil tcp packet"
```

### Task 3: Add a test-only state injection path before live TCP wiring

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing route state test**

Add a public or crate-visible method on `ApiState` to set decoded current-coil state. Keep it usable by future TCP listener code and tests; do not add a test-only HTTP endpoint.

```rust
#[tokio::test]
async fn current_coil_returns_decoded_tcp_state_when_populated() {
    let state = ApiState::new(Arc::new(InMemoryCoilRepository::new()));
    state.set_current_coil_for_tcp(json!({
        "len": 96,
        "Coil_ID": "4V050192400",
        "Steel_Grade": "Q235B",
        "act_w": 1261
    }));
    let app = build_app(state);

    let response = request_response(app, "GET", "/currentCoil").await;

    assert_eq!(response.status(), StatusCode::OK);
    let body =
        serde_json::from_slice::<Value>(&response_bytes(response).await).expect("currentCoil json");
    assert_eq!(body["Coil_ID"], json!("4V050192400"));
    assert_eq!(body["Steel_Grade"], json!("Q235B"));
    assert_eq!(body["act_w"], json!(1261));
}
```

**Step 2: Run test to verify it fails**

Run:

```powershell
cd app/Server/rust_api_service
cargo test current_coil_returns_decoded_tcp_state_when_populated --test routes
```

Expected: FAIL because the setter does not exist yet.

**Step 3: Write minimal implementation**

Add:

```rust
pub fn set_current_coil_for_tcp(&self, body: Value) {
    if let Ok(mut current_coil) = self.current_coil.lock() {
        *current_coil = body;
    }
}
```

This method is intentionally named for the future TCP ingester; it is not a web API.

**Step 4: Run test to verify it passes**

Run:

```powershell
cd app/Server/rust_api_service
cargo test current_coil_returns_decoded_tcp_state_when_populated --test routes
```

Expected: PASS.

**Step 5: Commit**

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs docs/rust-tauri-parity.md
git commit -m "api: expose current coil tcp state"
```

### Task 4: Wire optional Rust TCP ingestion without blocking API startup

**Files:**
- Modify: `app/Server/rust_api_service/src/main.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Optionally create: `app/Server/rust_api_service/src/tcp_decode.rs`
- Modify: `app/Server/rust_api_service/src/lib.rs`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write the failing unit test for invalid packet handling**

Test that invalid packet lengths do not replace existing current-coil state.

```rust
#[test]
fn invalid_current_coil_packet_does_not_decode() {
    assert!(decode_current_coil_packet(&[1, 2, 3]).is_none());
}
```

**Step 2: Run test to verify it fails or proves missing export**

Run:

```powershell
cd app/Server/rust_api_service
cargo test invalid_current_coil_packet_does_not_decode --test routes
```

Expected: FAIL until decoder is exported or implemented in the test-visible module.

**Step 3: Write minimal ingestion implementation**

Add an optional background TCP listener controlled by env vars so normal API startup does not require the PLC/TCP sender:

```text
RUST_API_CURRENT_COIL_TCP_ENABLED=true
RUST_API_CURRENT_COIL_TCP_HOST=0.0.0.0
RUST_API_CURRENT_COIL_TCP_PORT=6005 or another non-conflicting configured port
```

Important: do not reuse HTTP port `6005` if the legacy Python `HttpServer.py` is running. Prefer a Rust-specific default unless production deployment explicitly maps it.

For each accepted packet:

1. Read the packet bytes.
2. If `len > 50`, decode with `decode_current_coil_packet`.
3. If decode succeeds, call `state.set_current_coil_for_tcp(decoded)`.
4. Ignore heartbeat packets like Python `DecodeHeartbeat`.
5. Log invalid packet size as warning and preserve previous state.

**Step 4: Run targeted tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test current_coil --test routes
```

Expected: all current-coil focused tests pass.

**Step 5: Update parity ledger**

Update `docs/rust-tauri-parity.md` `/currentCoil` row to say:

- Startup returns `{}`.
- DB fallback has been removed from the communication route.
- Rust can decode Python-compatible current-coil TCP packets.
- Rust has optional background ingestion controlled by env vars.
- Live PLC/TCP integration remains unverified unless a real sender is exercised.

**Step 6: Commit**

```powershell
git add app/Server/rust_api_service/src/main.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/lib.rs docs/rust-tauri-parity.md
git commit -m "api: wire current coil tcp ingestion"
```

### Task 5: Focused verification before claiming parity

**Files:**
- Modify only if tests expose regressions.
- Read: `docs/rust-tauri-parity.md`

**Step 1: Run focused Rust tests**

Run:

```powershell
cd app/Server/rust_api_service
cargo test current_coil --test routes
```

Expected: PASS.

**Step 2: Run route tests that cover OpenAPI metadata**

Run:

```powershell
cd app/Server/rust_api_service
cargo test currentCoil --test routes
```

Expected: PASS for route docs/operation metadata tests.

**Step 3: Optional live smoke without hardware**

Only if the user authorizes service startup:

```powershell
cd app/Server/rust_api_service
$env:RUST_API_CURRENT_COIL_TCP_ENABLED='false'
cargo run -- --host 127.0.0.1 --port 5011
```

Then request:

```powershell
Invoke-RestMethod http://127.0.0.1:5011/currentCoil
```

Expected before TCP packet: `{}`.

**Step 4: Optional live smoke with a synthetic sender**

Only if the user authorizes opening a local TCP listener and sender:

1. Start Rust API with TCP ingestion enabled on a non-conflicting port.
2. Send the Python reference packet bytes to that port.
3. Request `/currentCoil`.
4. Expected: response contains `Coil_ID = "4V050192400"` and `Steel_Grade = "Q235B"`.

**Step 5: Final ledger update**

If all focused checks pass but real PLC sender was not exercised, mark the row as `Partial` and explicitly say live PLC/TCP hardware verification remains pending. Only move it toward complete when the real sender path has been exercised.
