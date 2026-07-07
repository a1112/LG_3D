# Re-detection Runtime Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Rust `/reDetection/*`, `WS /ws/reDetection`, `/getServerState`, and `WS /ws/DetectionState` connect to the real Python algorithm runtime state and re-detection execution path, not only a Rust in-memory fallback.

**Architecture:** Keep Rust/Axum as the public API and WebSocket endpoint for Tauri/React. Add explicit runtime backends: `fallback` for no-algorithm development hosts, `python-runner` for spawning a local script that talks to `ImageMosaicThread` semantics, and `proxy` for deployments where the Python API server already owns `Globs.imageMosaicThread` and `Globs.serverMsg.msgList`. Stream Python JSON status into Rust state so existing React/QML routes remain unchanged.

**Tech Stack:** Rust, Axum, Tokio subprocess/proxy client, Python 3.11, existing `app/algorithm_runtime/SplicingService/ImageMosaicThread.py`, existing `app/Server/api/ApiServer.py`, React `OperationSidebar` and `SystemDiagnostics`.

---

### Task 1: Lock backend selection for re-detection runtime

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing test**

Add `re_detection_start_uses_proxy_backend_when_configured`:

```rust
#[tokio::test]
async fn re_detection_start_uses_proxy_backend_when_configured() {
    let proxy = spawn_mock_python_runtime(|request| {
        assert_eq!(request.path(), "/reDetection/start/42/44");
        json!({
            "total": 3,
            "done": 0,
            "pending": 3,
            "running": false,
            "error": "",
            "queue": [44, 43, 42],
            "messages": [{"Base":"ImageMosaicThread","msg":"set_re_detection_by_coil_id start=42 end=44 count=3","level":"DEBUG"}],
            "progress": 0.0
        })
    }).await;

    let _backend = EnvGuard::set("RUST_API_REDETECTION_BACKEND", "proxy");
    let _proxy = EnvGuard::set("RUST_API_REDETECTION_PROXY_URL", proxy.base_url());

    let (status, body) = request_json(app_with_seed_data(), "GET", "/reDetection/start/42/44").await;

    assert_eq!(status, 200);
    assert_eq!(body["queue"], json!([44, 43, 42]));
    assert_eq!(body["messages"][0]["Base"], "ImageMosaicThread");
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test re_detection_start_uses_proxy_backend_when_configured --test routes`

Expected: FAIL because Rust currently always starts local state/fallback or only uses the older blocking command hook.

**Step 3: Write minimal implementation**

In `routes.rs`:

- Add `RUST_API_REDETECTION_BACKEND` with `fallback`, `proxy`, and `python-runner`.
- Keep existing `RUST_API_REDETECTION_CMD` as explicit highest-priority override for backward compatibility.
- Add `RUST_API_REDETECTION_PROXY_URL`, default unset.
- Add `RUST_API_REDETECTION_RUNNER`, defaulting to `app/algorithm_runtime/re_detection_runner.py` when present.
- Add `RUST_API_REDETECTION_PYTHON`, defaulting to `RUST_API_PYTHON` or `python`.
- Normalize backend results through the same Python status shape: `total`, `done`, `pending`, `running`, `error`, `queue`, `messages`, `progress`.

**Step 4: Run test to verify it passes**

Run: `cargo test re_detection_start_uses_proxy_backend_when_configured --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: add re-detection runtime backend selection"
```

### Task 2: Stream runner/proxy status into Rust WebSocket state

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing test**

Add `re_detection_websocket_streams_python_status_updates`:

```rust
#[tokio::test]
async fn re_detection_websocket_streams_python_status_updates() {
    let runner = write_fake_jsonl_runner(&[
        json!({"event":"status","total":2,"done":0,"pending":2,"running":true,"error":"","queue":[2,1],"messages":[],"progress":0.0}),
        json!({"event":"status","total":2,"done":1,"pending":1,"running":true,"error":"","queue":[1],"messages":[],"progress":0.5}),
        json!({"event":"status","total":2,"done":2,"pending":0,"running":false,"error":"","queue":[],"messages":[],"progress":1.0}),
    ]);
    let _backend = EnvGuard::set("RUST_API_REDETECTION_BACKEND", "python-runner");
    let _runner = EnvGuard::set("RUST_API_REDETECTION_RUNNER", runner.to_string_lossy());

    let app = app_with_seed_data();
    let ws_url = spawn_ws_server(app.clone(), "/ws/reDetection").await;
    let mut ws = connect_ws(ws_url).await;
    ws.send_text(json!({"from_id": 1, "to_id": 2}).to_string()).await;

    let final_payload = read_ws_until(&mut ws, |payload| payload["progress"] == 1.0).await;
    assert_eq!(final_payload["running"], false);
    assert_eq!(final_payload["done"], 2);
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test re_detection_websocket_streams_python_status_updates --test routes`

Expected: FAIL because existing external command handling waits for completion and does not stream status payloads into `ReDetectionState`.

**Step 3: Write minimal implementation**

- For `python-runner`, spawn subprocess with stdout JSONL parsing.
- Accept events `status`, `message`, `server_state`, `error`, and `finished`.
- Merge status events into `ReDetectionState` without adding Rust-only fields.
- Keep generation checks so a newer start request cancels stale updates.
- Keep `/ws/reDetection` periodic push behavior exactly as Python/QML expects.

**Step 4: Run test to verify it passes**

Run: `cargo test re_detection_websocket_streams_python_status_updates --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: stream re-detection runtime status"
```

### Task 3: Add Python runner for ImageMosaicThread-compatible re-detection

**Files:**
- Create: `app/algorithm_runtime/re_detection_runner.py`
- Test: `test/test_re_detection_runner.py`

**Step 1: Write the failing tests**

Create tests that monkeypatch `ImageMosaicThread` and database lookups:

```python
def test_runner_sets_re_detection_range_and_emits_status(monkeypatch):
    from app.algorithm_runtime import re_detection_runner

    class FakeThread:
        def __init__(self):
            self.calls = []
            self.status = {
                "total": 3,
                "done": 0,
                "pending": 3,
                "running": False,
                "error": "",
                "queue": [44, 43, 42],
                "messages": [],
                "progress": 0.0,
            }
        def set_re_detection_by_coil_id(self, start, end):
            self.calls.append((start, end))
        def get_re_detection_msg(self):
            return self.status

    fake = FakeThread()
    monkeypatch.setattr(re_detection_runner, "attach_or_create_runtime", lambda *_: fake)

    events = list(re_detection_runner.run_re_detection(42, 44, poll_interval=0.01, once=True))

    assert fake.calls == [(42, 44)]
    assert events[0]["event"] == "status"
    assert events[0]["queue"] == [44, 43, 42]
```

Add companion tests for:

- runtime unavailable emits `event="error"` with Python-like detail.
- finished status emits `progress=1.0` and `running=false`.
- CLI JSONL output flushes one JSON object per line.

**Step 2: Run tests to verify they fail**

Run: `pytest test/test_re_detection_runner.py -v`

Expected: FAIL because `app/algorithm_runtime/re_detection_runner.py` does not exist.

**Step 3: Write minimal implementation**

Implement `re_detection_runner.py`:

- Add `argparse` args: `--start-id`, `--end-id`, `--poll-interval`, `--timeout`, `--once`, `--jsonl`.
- Prefer attaching to an existing runtime when available through `Globs.imageMosaicThread`.
- If no runtime is attached and `--create-runtime` is set, instantiate `ImageMosaicThread(None, LoggerProcess(...))`; keep this opt-in because it can start real algorithm processing.
- Call `set_re_detection_by_coil_id(start_id, end_id)`.
- Poll `get_re_detection_msg()` and emit JSONL `status` events until `running=false` and `pending=0`, or until timeout/error.
- Preserve Python status keys exactly.

**Step 4: Run tests to verify they pass**

Run: `pytest test/test_re_detection_runner.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/algorithm_runtime/re_detection_runner.py test/test_re_detection_runner.py
git commit -m "algo: add re-detection runtime runner"
```

### Task 4: Sync Python server state messages into Rust `/getServerState`

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`
- Reference: `app/Base/utils/ServerMsg.py`
- Reference: `app/Server/api/ApiServer.py`

**Step 1: Write the failing test**

Add `server_state_proxy_returns_python_msg_list_without_rust_synthetic_entries`:

```rust
#[tokio::test]
async fn server_state_proxy_returns_python_msg_list_without_rust_synthetic_entries() {
    let proxy = spawn_mock_python_runtime(|request| {
        assert_eq!(request.path(), "/getServerState");
        json!([["camera", "等待触发"], {"key":"algorithm","level":2,"msg":"运行中"}])
    }).await;
    let _backend = EnvGuard::set("RUST_API_SERVER_STATE_BACKEND", "proxy");
    let _proxy = EnvGuard::set("RUST_API_REDETECTION_PROXY_URL", proxy.base_url());

    let (status, body) = request_json(app_with_seed_data(), "GET", "/getServerState").await;

    assert_eq!(status, 200);
    assert_eq!(body[0], json!(["camera", "等待触发"]));
    assert_eq!(body[1]["key"], "algorithm");
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test server_state_proxy_returns_python_msg_list_without_rust_synthetic_entries --test routes`

Expected: FAIL because Rust currently returns in-memory `server_state` plus synthetic re-detection status entries.

**Step 3: Write minimal implementation**

- Add `RUST_API_SERVER_STATE_BACKEND` with `fallback` and `proxy`.
- For proxy, fetch `/getServerState` from the Python runtime URL and cache the latest successful array.
- Feed `server_state` events from the Python runner into `ApiState.server_state`.
- Keep synthetic re-detection server-state entries only in `fallback` mode; do not mix them into proxied Python `Globs.serverMsg.msgList`.
- Keep `WS /ws/DetectionState` push cadence unchanged.

**Step 4: Run test to verify it passes**

Run: `cargo test server_state_proxy_returns_python_msg_list_without_rust_synthetic_entries --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: proxy python server state messages"
```

### Task 5: Preserve React/QML status normalization

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/reDetection.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/serverState.ts`
- Test: `app/UI/MotionStudioWeb/src/utils/reDetection.test.ts`
- Test: `app/UI/MotionStudioWeb/src/utils/serverState.test.ts`

**Step 1: Write the failing tests**

Add normalization tests for exact Python payloads:

```ts
it('normalizes Python ImageMosaicThread status payloads', () => {
  const view = buildReDetectionStatusView({
    total: 3,
    done: 1,
    pending: 2,
    running: true,
    error: '',
    queue: [44, 43],
    messages: [{ Base: 'ImageMosaicThread', msg: 'set_re_detection_by_coil_id start=42 end=44 count=3' }],
    progress: 1 / 3,
  })

  expect(view.running).toBe(true)
  expect(view.percent).toBe(33)
  expect(view.canChange).toBe(false)
})
```

Add server-state tests for Python tuple rows from `ServerMsg.add_msg()`:

```ts
expect(buildServerStateRows([['camera', '等待触发']])[0]).toMatchObject({ key: 'camera', message: '等待触发' })
```

**Step 2: Run tests to verify they fail if needed**

Run: `npm test -- reDetection serverState`

Expected: PASS if current normalization is already sufficient, otherwise FAIL until the next step.

**Step 3: Write minimal implementation**

- Preserve existing QML-compatible labels and progress display.
- Ensure Python status payloads do not require Rust-only wrapper fields.
- Ensure server-state tuple/object/string/scalar rows are still displayed in `SystemDiagnostics` and global status areas.

**Step 4: Run tests to verify they pass**

Run: `npm test -- reDetection serverState`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/UI/MotionStudioWeb/src/utils/reDetection.ts app/UI/MotionStudioWeb/src/utils/serverState.ts app/UI/MotionStudioWeb/src/utils/reDetection.test.ts app/UI/MotionStudioWeb/src/utils/serverState.test.ts
git commit -m "ui: normalize python runtime status payloads"
```

### Task 6: Safe rollout and parity verification gates

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/plans/2026-07-06-re-detection-runtime-parity.md`

**Step 1: Document runtime modes**

Add rollout notes:

- `RUST_API_REDETECTION_BACKEND=fallback`: current in-memory Rust progress for no-runtime development.
- `RUST_API_REDETECTION_BACKEND=proxy`: delegate start/status to Python `/reDetection/*` and server state to `/getServerState`.
- `RUST_API_REDETECTION_BACKEND=python-runner`: spawn `app/algorithm_runtime/re_detection_runner.py` and stream JSONL status.
- `RUST_API_REDETECTION_PROXY_URL=http://127.0.0.1:5010`: Python API runtime endpoint.
- `RUST_API_REDETECTION_PYTHON=.venv\Scripts\python.exe`: local interpreter for runner mode.
- `RUST_API_REDETECTION_RUNNER=app\algorithm_runtime\re_detection_runner.py`: packaged runner override.
- `RUST_API_SERVER_STATE_BACKEND=proxy`: use Python `Globs.serverMsg.msgList` as authoritative server state.

**Step 2: Run final focused checks only with explicit authorization**

```bash
cargo test re_detection server_state --test routes
pytest test/test_re_detection_runner.py -v
npm test -- reDetection serverState
```

Expected: PASS.

**Step 3: Production-like smoke only after operator approval**

- Start Python API with real `Globs.imageMosaicThread` attached.
- Start Rust with `RUST_API_REDETECTION_BACKEND=proxy` and `RUST_API_SERVER_STATE_BACKEND=proxy`.
- Trigger one copied, non-production coil range from React/QML.
- Confirm `/reDetection/status`, `WS /ws/reDetection`, `/getServerState`, and `WS /ws/DetectionState` reflect Python runtime state.
- Confirm output/database side effects match Python `ImageMosaicThread._process_secondary_coil()` behavior.

**Step 4: Update parity row only after evidence**

Keep row Partial until live or synthetic runtime evidence proves:

- Python queue order is preserved: sorted ids descending.
- Progress fields match `ImageMosaicThread.get_re_detection_msg()`.
- Server-state rows are Python `Globs.serverMsg.msgList`, not Rust synthetic entries.
- React and QML both display running/finished/error states from WebSocket without polling regressions.

**Step 5: Commit**

```bash
git add docs/rust-tauri-parity.md docs/plans/2026-07-06-re-detection-runtime-parity.md
git commit -m "infra: document re-detection runtime parity rollout"
```