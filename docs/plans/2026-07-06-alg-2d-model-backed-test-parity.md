# 2D Algorithm Model-Backed Test Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Rust `/alg_2d/test/start`, `/alg_2d/test/stop`, and `WS /ws/alg_2d/test/progress` run real model-backed 2D detector/segment/classifier test jobs with Python-compatible output folders, labels, and progress instead of the current heuristic fallback.

**Architecture:** Keep Rust/Axum as the public API and WebSocket state owner. Add a Python runner inside the existing 2D runtime that reuses `ultralytics.YOLO`, `alg_2d.classifier`, and existing model/config paths, then connect Rust to it through a streaming JSONL subprocess protocol with the current heuristic fallback reserved for dev/test mode. This avoids reimplementing Torch/Ultralytics inference in Rust while still making the Tauri/React UI talk only to the Rust service.

**Tech Stack:** Rust, Axum, Tokio subprocess streaming, Python 3.11, Ultralytics YOLO, PIL/OpenCV-compatible image handling, existing React `AlgTestModal` UI.

---

### Task 1: Lock the Rust backend-selection contract

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing test**

Add a route test named `alg_2d_test_start_prefers_python_runner_when_model_backend_enabled`:

```rust
#[tokio::test]
async fn alg_2d_test_start_prefers_python_runner_when_model_backend_enabled() {
    let temp = tempfile::tempdir().unwrap();
    let target = temp.path().join("input");
    let output = temp.path().join("output");
    std::fs::create_dir_all(&target).unwrap();
    std::fs::write(target.join("sample.jpg"), tiny_jpeg_bytes()).unwrap();

    let runner = temp.path().join("fake_alg_runner.py");
    std::fs::write(
        &runner,
        r#"import json, pathlib, sys
args = sys.argv
out = pathlib.Path(args[args.index('--output') + 1])
(out / 'abnormal').mkdir(parents=True, exist_ok=True)
(out / 'abnormal' / 'sample.jpg').write_bytes(b'jpg')
print(json.dumps({'event':'progress','status':'运行中','done':1,'total':1,'summary':{'normal':0,'abnormal':1,'skipped':0,'empty':0},'message':'sample.jpg abnormal'}), flush=True)
print(json.dumps({'event':'finished','status':'完成','done':1,'total':1,'summary':{'normal':0,'abnormal':1,'skipped':0,'empty':0},'message':'模型测试完成'}), flush=True)
"#,
    )
    .unwrap();

    let _backend = EnvGuard::set("RUST_API_ALG_TEST_BACKEND", "python");
    let _runner = EnvGuard::set("RUST_API_ALG_TEST_RUNNER", runner.to_string_lossy());
    let _python = EnvGuard::set("RUST_API_ALG_TEST_PYTHON", "python");

    let app = app_with_seed_data();
    let (_status, body) = request_json_body(
        app.clone(),
        "POST",
        "/alg_2d/test/start",
        json!({
            "model": "detector.pt",
            "target": target,
            "output": output,
            "threshold": 0.4,
            "mode": "copy",
            "options": {"save_label": true, "classify_save": true}
        }),
    )
    .await;

    assert_eq!(body["ok"], true);
    wait_until(|| output.join("abnormal/sample.jpg").exists()).await;
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test alg_2d_test_start_prefers_python_runner_when_model_backend_enabled --test routes`

Expected: FAIL because Rust only uses `RUST_API_ALG_TEST_CMD` for external execution and otherwise starts the heuristic in-process file job.

**Step 3: Write minimal implementation**

In `routes.rs`:

- Add `RUST_API_ALG_TEST_BACKEND` with values `fallback`, `external`, and `python`.
- Add `RUST_API_ALG_TEST_RUNNER` defaulting to `app/algorithm_runtime_2D/alg_test_runner.py` when present.
- Add `RUST_API_ALG_TEST_PYTHON` defaulting to `python`.
- Keep `RUST_API_ALG_TEST_CMD` as the highest-priority explicit override.
- When backend resolves to `python`, build a subprocess command equivalent to:

```text
python app/algorithm_runtime_2D/alg_test_runner.py --model <model> --target <target> --output <output> --threshold <threshold> --mode <copy|move> --model-type <detector|segment|classifier> --classify-save <true|false> --save-label <true|false> --prioritize <true|false>
```

**Step 4: Run test to verify it passes**

Run: `cargo test alg_2d_test_start_prefers_python_runner_when_model_backend_enabled --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: add alg test python backend selection"
```

### Task 2: Stream JSONL subprocess progress into the existing WebSocket state

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing test**

Add `alg_2d_python_runner_jsonl_updates_progress_websocket_like_python`:

```rust
#[tokio::test]
async fn alg_2d_python_runner_jsonl_updates_progress_websocket_like_python() {
    let temp = tempfile::tempdir().unwrap();
    let runner = write_fake_jsonl_runner(temp.path(), &[
        json!({"event":"progress","status":"运行中","done":1,"total":2,"errors":0,"skipped":0,"message":"one.jpg","summary":{"normal":1,"abnormal":0,"skipped":0,"empty":0}}),
        json!({"event":"finished","status":"完成","done":2,"total":2,"errors":0,"skipped":0,"message":"完成","summary":{"normal":1,"abnormal":1,"skipped":0,"empty":0}}),
    ]);
    let _backend = EnvGuard::set("RUST_API_ALG_TEST_BACKEND", "python");
    let _runner = EnvGuard::set("RUST_API_ALG_TEST_RUNNER", runner.to_string_lossy());

    let app = app_with_seed_data();
    let ws_url = spawn_ws_server(app.clone(), "/ws/alg_2d/test/progress").await;
    let mut ws = connect_ws(ws_url).await;

    start_alg_test_with_two_images(app).await;
    let final_payload = read_ws_until(&mut ws, |payload| payload["finished"] == true).await;

    assert_eq!(final_payload["status"], "完成");
    assert_eq!(final_payload["done"], 2);
    assert_eq!(final_payload["total"], 2);
    assert_eq!(final_payload["summary"]["normal"], 1);
    assert_eq!(final_payload["summary"]["abnormal"], 1);
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test alg_2d_python_runner_jsonl_updates_progress_websocket_like_python --test routes`

Expected: FAIL because `run_alg_test_external_command()` currently waits for process completion and does not stream JSONL updates into `AlgTestState`.

**Step 3: Write minimal implementation**

Replace the blocking external-command path with a streaming subprocess path for backend `python` and `external-jsonl`:

- Spawn with stdout piped and stderr piped.
- Parse each stdout line as JSON.
- Accept events `progress`, `warning`, `error`, and `finished`.
- Merge missing fields with current Rust defaults: `task_id`, `speed`, `eta`, `options`.
- Update `AlgTestState.last_payload` after each valid JSONL line.
- Preserve stderr in the final error message when the subprocess exits nonzero.
- On normal exit without an explicit `finished` line, emit a final `finished=true` payload with the last known summary.

**Step 4: Run test to verify it passes**

Run: `cargo test alg_2d_python_runner_jsonl_updates_progress_websocket_like_python --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: stream alg test runner progress"
```

### Task 3: Add the Python model-backed runner

**Files:**
- Create: `app/algorithm_runtime_2D/alg_test_runner.py`
- Test: `test/test_alg_2d_runner.py`

**Step 1: Write the failing tests**

Create tests that monkeypatch the model layer instead of loading real GPU models:

```python
def test_detector_runner_writes_abnormal_image_and_pascal_voc_label(tmp_path, monkeypatch):
    from app.algorithm_runtime_2D import alg_test_runner

    image = tmp_path / "input" / "bad.jpg"
    output = tmp_path / "output"
    image.parent.mkdir()
    write_test_jpeg(image)

    monkeypatch.setattr(alg_test_runner, "load_yolo_model", lambda *_: FakeDetectorModel(boxes=[FakeBox("scratch", 0.91, [1, 2, 20, 30])]))

    events = list(alg_test_runner.run_alg_test(
        model="detector.pt",
        model_type="detector",
        target=image.parent,
        output=output,
        threshold=0.4,
        mode="copy",
        classify_save=True,
        save_label=True,
        prioritize=False,
    ))

    assert (output / "abnormal" / "bad.jpg").exists()
    xml = (output / "abnormal" / "bad.xml").read_text(encoding="utf-8")
    assert "<name>scratch</name>" in xml
    assert events[-1]["event"] == "finished"
    assert events[-1]["summary"] == {"normal": 0, "abnormal": 1, "skipped": 0, "empty": 0}
```

Add companion tests for:

- classifier model: writes `normal/empty` for empty/normal results and never writes labels.
- `prioritize=true`: counts normal images as skipped and does not copy/move normal files.
- `mode=move`: removes the source file only after successful destination write.
- no images: emits Python-compatible `未找到可测试图片` and `finished=true`.

**Step 2: Run tests to verify they fail**

Run: `pytest test/test_alg_2d_runner.py -v`

Expected: FAIL because `app/algorithm_runtime_2D/alg_test_runner.py` does not exist.

**Step 3: Write minimal implementation**

Implement `alg_test_runner.py` with:

- `argparse` CLI matching the Rust subprocess args.
- `iter_images(target)` using the same extensions Rust already accepts.
- `resolve_model_path(model)` checking absolute path, cwd, `CONFIG.base_config_folder / "model"`, `RUST_API_MODEL_DIR`, `CONFIG_3D_DIR\model`, and `D:\CONFIG_3D\model`.
- `load_yolo_model(model_path)` returning `ultralytics.YOLO(model_path)`.
- detector/segment inference using `model(image_path, conf=threshold)` and `result.boxes`.
- classifier inference through `Base.alg.CoilClsModel`/`alg_2d.classifier` helpers where possible.
- output folders `normal`, `abnormal`, and `empty` matching current Rust/Python UI expectations.
- Pascal VOC XML only when `save_label=true` and detector boxes exist.
- JSONL progress events printed to stdout with `flush=True` after every image.
- nonzero exit and JSONL `error` event for unrecoverable model-load/config errors.

**Step 4: Run tests to verify they pass**

Run: `pytest test/test_alg_2d_runner.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/algorithm_runtime_2D/alg_test_runner.py test/test_alg_2d_runner.py
git commit -m "algo: add model backed 2d test runner"
```

### Task 4: Preserve React/QML-facing payload compatibility

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/algTest.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/AlgTestModal/index.tsx`
- Test: `app/UI/MotionStudioWeb/src/utils/algTest.test.ts`
- Test: `app/UI/MotionStudioWeb/src/components/AlgTestModal/AlgTestModal.test.ts`

**Step 1: Write the failing tests**

Add coverage for runner-emitted fields that are not currently surfaced strongly:

```ts
it('normalizes model-backed runner progress details without dropping QML fields', () => {
  const progress = normalizeAlgProgressMessage(JSON.stringify({
    task_id: 'task-1',
    status: '运行中',
    done: 2,
    total: 3,
    errors: 1,
    skipped: 0,
    message: 'bad.jpg abnormal scratch 0.91',
    summary: { normal: 1, abnormal: 1, skipped: 0, empty: 0 },
    current_file: 'bad.jpg',
    model_backend: 'python',
  }))

  expect(progress.taskId).toBe('task-1')
  expect(progress.summary?.abnormal).toBe(1)
  expect(progress.message).toContain('bad.jpg')
})
```

If the UI needs to display backend/current file, extend `AlgProgressMessage` with optional `currentFile` and `modelBackend`.

**Step 2: Run tests to verify they fail**

Run: `npm test -- AlgTestModal algTest`

Expected: FAIL if new fields are required and not normalized/displayed.

**Step 3: Write minimal implementation**

- Keep existing payload builder unchanged unless backend-specific options are added.
- Preserve `save_label=false` for classifier models.
- Add optional display for current file/backend only if runner emits it.
- Ensure `finished=true` still closes the socket and appends the summary log.

**Step 4: Run tests to verify they pass**

Run: `npm test -- AlgTestModal algTest`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/UI/MotionStudioWeb/src/utils/algTest.ts app/UI/MotionStudioWeb/src/components/AlgTestModal/index.tsx app/UI/MotionStudioWeb/src/utils/algTest.test.ts app/UI/MotionStudioWeb/src/components/AlgTestModal/AlgTestModal.test.ts
git commit -m "ui: surface model backed alg test progress"
```

### Task 5: Add production-safe rollout switches and docs

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/plans/2026-07-06-alg-2d-model-backed-test-parity.md`
- Optional Modify: `app/Server/rust_api_service/src/config.rs`

**Step 1: Write the failing test**

Add or extend a Rust test that proves the heuristic fallback remains available:

```rust
#[tokio::test]
async fn alg_2d_test_backend_fallback_remains_available_for_no_python_hosts() {
    let _backend = EnvGuard::set("RUST_API_ALG_TEST_BACKEND", "fallback");
    let response = start_alg_test_with_one_image(app_with_seed_data()).await;
    assert_eq!(response["ok"], true);
}
```

**Step 2: Run test to verify it fails or documents current behavior**

Run: `cargo test alg_2d_test_backend_fallback_remains_available_for_no_python_hosts --test routes`

Expected: PASS if fallback is already explicit, otherwise FAIL until backend selection is implemented.

**Step 3: Write minimal implementation/docs**

Document these rollout modes:

- `RUST_API_ALG_TEST_BACKEND=python`: use bundled Python runner and real model inference.
- `RUST_API_ALG_TEST_BACKEND=fallback`: use current deterministic heuristic for development hosts without ML dependencies.
- `RUST_API_ALG_TEST_CMD=...`: use an operator-provided command as highest priority.
- `RUST_API_ALG_TEST_PYTHON=...`: choose interpreter from `.venv\Scripts\python.exe` in production.
- `RUST_API_ALG_TEST_RUNNER=...`: override runner path for packaged deployments.

Update parity row 55 only after focused tests and one non-production model-backed smoke check pass.

**Step 4: Run final focused checks**

Run:

```bash
cargo test alg_2d_test --test routes
pytest test/test_alg_2d_runner.py -v
npm test -- AlgTestModal algTest
```

Expected: PASS.

For production-like smoke only after operator approval:

```bash
$env:RUST_API_ALG_TEST_BACKEND='python'
$env:RUST_API_ALG_TEST_PYTHON='.venv\Scripts\python.exe'
uvicorn 服务.main:app --host 127.0.0.1 --port 5010
cargo run --bin rust_api_service
```

Then use React/QML to run one small copied image folder with a non-production output directory.

**Step 5: Commit**

```bash
git add docs/rust-tauri-parity.md docs/plans/2026-07-06-alg-2d-model-backed-test-parity.md app/Server/rust_api_service/src/config.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "infra: document alg test backend rollout"
```