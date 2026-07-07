# 2D Area Processing Deep Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring Rust `/clip_config`, `/area/rejoin`, `/area/status`, and `/area/scan` to functional parity with Python's 2D AREA pipeline, including YOLO segmentation, Python-style camera intersection stitching, area image generation, defect detection integration, and safe production rollout.

**Architecture:** Keep Rust as the public API and scanner/status owner. Split the AREA execution backend into explicit modes: current Rust fallback writer for no-ML development hosts, optional Python runner/proxy mode that reuses `app/algorithm_runtime_2D` production logic, and a later native Rust image-only mode only where it can be proven byte/pixel compatible. This keeps the Tauri/React UI stable while restoring the Python algorithm behavior that depends on Ultralytics, `CameraImageGrop`, `DataIntegration`, and database defect writes.

**Tech Stack:** Rust, Axum, Tokio subprocess/proxy boundary, Python 3.11, OpenCV, NumPy, Ultralytics YOLO segmentation, existing `area_join.json`, existing React `/system` and AREA viewer routes.

---

### Task 1: Lock backend selection for AREA execution

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing test**

Add `area_rejoin_uses_python_backend_when_configured`:

```rust
#[tokio::test]
async fn area_rejoin_uses_python_backend_when_configured() {
    let temp = tempfile::tempdir().unwrap();
    let runner = temp.path().join("fake_area_runner.py");
    std::fs::write(
        &runner,
        r#"import json, pathlib, sys
coil_id = sys.argv[sys.argv.index('--coil-id') + 1]
surface = sys.argv[sys.argv.index('--surface-key') + 1]
print(json.dumps({'status':'ok','coil_id':int(coil_id),'surface_key':surface,'outputs':['jpg/AREA.jpg'],'backend':'python'}), flush=True)
"#,
    )
    .unwrap();

    let _backend = EnvGuard::set("RUST_API_AREA_BACKEND", "python");
    let _runner = EnvGuard::set("RUST_API_AREA_RUNNER", runner.to_string_lossy());
    let _python = EnvGuard::set("RUST_API_AREA_PYTHON", "python");

    let response = request_json_body(
        app_with_seed_data(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 1701, "surface_key": "S"}),
    )
    .await;

    assert_eq!(response["status"], "ok");
    assert_eq!(response["backend"], "python");
    assert_eq!(response["surface_key"], "S");
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test area_rejoin_uses_python_backend_when_configured --test routes`

Expected: FAIL because `/area/rejoin` currently always uses Rust in-process fallback output writing.

**Step 3: Write minimal implementation**

In `routes.rs`:

- Add `RUST_API_AREA_BACKEND` with values `fallback`, `python`, and `proxy`.
- Add `RUST_API_AREA_RUNNER`, defaulting to `app/algorithm_runtime_2D/area_runner.py` when present.
- Add `RUST_API_AREA_PYTHON`, defaulting to `python` and overridable to `.venv\Scripts\python.exe`.
- Keep current Rust writer as `fallback` mode.
- For `python` mode, spawn the runner with `--coil-id`, `--surface-key`, `--config`, and `--json`.
- For `proxy` mode, call the Python 2D server route if an operator configures `RUST_API_AREA_PROXY_URL`.

**Step 4: Run test to verify it passes**

Run: `cargo test area_rejoin_uses_python_backend_when_configured --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: add area processing backend selection"
```

### Task 2: Add a Python AREA runner that reuses production logic

**Files:**
- Create: `app/algorithm_runtime_2D/area_runner.py`
- Test: `test/test_alg_2d_area_runner.py`

**Step 1: Write the failing tests**

Create tests using monkeypatched light fakes instead of GPU models:

```python
def test_area_runner_calls_join_surface_pipeline(tmp_path, monkeypatch):
    from app.algorithm_runtime_2D import area_runner

    calls = []

    class FakeSurfaceWork:
        def add_work(self, coil_id, timeout=1):
            calls.append(("add", coil_id, timeout))
            return True
        def get(self):
            calls.append(("get",))
            return None

    fake_join_work = type("FakeJoinWork", (), {"surface_dict": {"S": FakeSurfaceWork()}})()
    monkeypatch.setattr(area_runner, "build_join_work", lambda *_: fake_join_work)

    result = area_runner.run_rejoin(coil_id=1701, surface_key="S", config_path=tmp_path / "area_join.json")

    assert result["status"] == "ok"
    assert result["coil_id"] == 1701
    assert result["surface_key"] == "S"
    assert calls == [("add", 1701, 1), ("get",)]
```

Add companion tests for:

- `surface_key=None`: submits every configured surface like Python `JoinWork.run()`.
- unknown surface: returns a structured error and nonzero CLI exit.
- missing camera inputs: returns `status="skipped"` and does not report output files.
- JSON CLI output: stdout contains one final JSON object for Rust to parse.

**Step 2: Run tests to verify they fail**

Run: `pytest test/test_alg_2d_area_runner.py -v`

Expected: FAIL because `app/algorithm_runtime_2D/area_runner.py` does not exist.

**Step 3: Write minimal implementation**

Implement `area_runner.py`:

```python
import argparse
import json
from pathlib import Path
from typing import Optional

from configs import CONFIG
from configs.JoinConfig import JoinConfig
from JoinService.JoinWork import JoinWork


def build_join_work(config_path: Optional[Path] = None) -> JoinWork:
    if config_path is not None:
        return JoinWork(JoinConfig(config_path))
    return JoinWork(JoinConfig(CONFIG.JOIN_CONFIG_FILE))


def run_rejoin(coil_id: int, surface_key: Optional[str], config_path: Optional[Path] = None) -> dict:
    join_work = build_join_work(config_path)
    surfaces = join_work.surface_dict
    if surface_key:
        key = surface_key.strip().upper()
        if key not in surfaces:
            return {"status": "error", "detail": f"Unknown surface_key: {key}", "coil_id": coil_id}
        selected = {key: surfaces[key]}
    else:
        selected = surfaces

    queued = []
    failed = []
    for key, surface in selected.items():
        if surface.add_work(coil_id, timeout=1):
            queued.append(key)
        else:
            failed.append(key)
    for key in queued:
        selected[key].get()
    return {"status": "ok" if not failed else "partial", "coil_id": coil_id, "surface_key": surface_key, "queued": queued, "failed": failed, "backend": "python"}
```

Then add CLI parsing for `--coil-id`, `--surface-key`, `--config`, and `--json`.

**Step 4: Run tests to verify they pass**

Run: `pytest test/test_alg_2d_area_runner.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/algorithm_runtime_2D/area_runner.py test/test_alg_2d_area_runner.py
git commit -m "algo: add python area processing runner"
```

### Task 3: Preserve Python intersection stitching semantics

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`
- Reference: `app/algorithm_runtime_2D/property/CameraImageGrop.py`
- Reference: `app/algorithm_runtime_2D/JoinService/cv_count_tool.py`

**Step 1: Write the failing test**

Add `area_fallback_uses_python_camera_intersections_not_fixed_hconcat`:

```rust
#[tokio::test]
async fn area_fallback_uses_python_camera_intersections_not_fixed_hconcat() {
    let temp = tempfile::tempdir().unwrap();
    let config_path = temp.path().join("area_join.json");
    write_rejoin_area_join_config_with_overlapping_camera_masks(&config_path, temp.path());
    let _config = EnvGuard::set("RUST_API_AREA_JOIN_CONFIG", config_path.to_string_lossy());
    let _backend = EnvGuard::set("RUST_API_AREA_BACKEND", "fallback");

    request_json_body(
        app_with_seed_data(),
        "POST",
        "/area/rejoin",
        json!({"coil_id": 1701, "surface_key": "S"}),
    )
    .await;

    let output = image::open(temp.path().join("save_s/1701/jpg/AREA.jpg")).unwrap().to_rgb8();
    assert_eq!(output.width(), expected_python_intersection_width());
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test area_fallback_uses_python_camera_intersections_not_fixed_hconcat --test routes`

Expected: FAIL if Rust fallback still uses simplified camera overlap logic for cases that Python `CameraImageGrop` handles differently.

**Step 3: Write minimal implementation**

In fallback-only Rust image path:

- Mirror Python camera order: `U`, `M`, `D` from `_camera_position_key()`.
- Mirror `CameraImageGrop.get_intersections()` by deriving masks and computing pair intersections with Python-compatible axis behavior.
- Preserve `left_index`/`right_index` cropping before `init_image()`/`join_image()` equivalent output.
- Keep S-surface camera reversal behavior where Python config implies it.
- Keep existing `clip_config` fixed/dynamic vertical stacking after per-camera horizontal stitch.

If exact parity becomes too large, keep fallback explicitly marked as non-authoritative and route production mode through the Python runner by default.

**Step 4: Run test to verify it passes**

Run: `cargo test area_fallback_uses_python_camera_intersections_not_fixed_hconcat --test routes`

Expected: PASS for synthetic overlap cases.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: align area fallback camera intersections"
```

### Task 4: Restore YOLO segmentation and defect database integration

**Files:**
- Modify: `app/algorithm_runtime_2D/area_runner.py`
- Modify: `app/algorithm_runtime_2D/area_alg/YoloSeg.py`
- Test: `test/test_alg_2d_area_runner.py`

**Step 1: Write the failing tests**

Add tests that monkeypatch model and database calls:

```python
def test_area_runner_invokes_detection_after_join(monkeypatch, tmp_path):
    from app.algorithm_runtime_2D import area_runner

    calls = []
    monkeypatch.setattr(area_runner, "run_surface_join", lambda *_: {"max_image": object(), "output": tmp_path / "AREA.jpg"})
    monkeypatch.setattr(area_runner, "run_detection", lambda data_integration: calls.append(data_integration))

    result = area_runner.run_rejoin(coil_id=1701, surface_key="S", config_path=tmp_path / "area_join.json")

    assert result["status"] == "ok"
    assert calls
```

Add a model-level test for `SteelSegModel.predict()` respecting `ALG_2D_YOLO_BATCH_SIZE` by monkeypatching the underlying YOLO call.

**Step 2: Run tests to verify they fail**

Run: `pytest test/test_alg_2d_area_runner.py -v`

Expected: FAIL until the runner exposes clear seams for join and detection.

**Step 3: Write minimal implementation**

- Ensure `area_runner` uses `DataIntegration.set_max_image(max_image)` then calls `alg_2d.detection.detection(di)` exactly like `SurfaceWork.run()`.
- Ensure `detection()` can load YOLO and classifier using existing config and environment.
- Return structured output describing generated `jpg/AREA.jpg`, `preview/AREA.jpg`, `cache/area/tild`, and defect write result when available.
- Treat model/database failures as `status="error"` with detail, matching Python server error behavior through Rust's `400/500` mapping decision.

**Step 4: Run tests to verify they pass**

Run: `pytest test/test_alg_2d_area_runner.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/algorithm_runtime_2D/area_runner.py app/algorithm_runtime_2D/area_alg/YoloSeg.py test/test_alg_2d_area_runner.py
git commit -m "algo: run area segmentation and defect integration"
```

### Task 5: Wire Rust status and scan behavior to backend outcomes

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Test: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing test**

Add `area_scan_clears_or_records_queue_from_python_backend_result`:

```rust
#[tokio::test]
async fn area_scan_clears_or_records_queue_from_python_backend_result() {
    let temp = tempfile::tempdir().unwrap();
    let runner = write_fake_area_runner(temp.path(), json!({
        "status": "ok",
        "coil_id": 1701,
        "surface_key": "S",
        "queued": ["S"],
        "failed": [],
        "outputs": ["jpg/AREA.jpg"]
    }));
    let _backend = EnvGuard::set("RUST_API_AREA_BACKEND", "python");
    let _runner = EnvGuard::set("RUST_API_AREA_RUNNER", runner.to_string_lossy());

    let app = app_with_seed_data();
    let scan = request_json_body(app.clone(), "POST", "/area/scan", json!({})).await;
    let status = request_json(app, "GET", "/area/status").await.1;

    assert_eq!(scan["status"], "ok");
    assert_eq!(status["queueDepths"]["S"], 0);
}
```

**Step 2: Run test to verify it fails**

Run: `cargo test area_scan_clears_or_records_queue_from_python_backend_result --test routes`

Expected: FAIL until Rust consumes backend result fields instead of assuming fallback success.

**Step 3: Write minimal implementation**

- `POST /area/rejoin`: return Python-compatible body while preserving Rust status fields needed by React.
- `POST /area/scan`: for each queued coil/surface, call the selected backend and update `Area2dState` based on `queued`, `failed`, and `outputs`.
- `GET /area/status`: include `lastScanError`, `queueFailures`, per-surface queue depth, last coil id, and configured `clipConfig` as today.
- On backend failure, keep queue entry and expose failure in `scanner.queueFailures`, matching Python's recoverable queue behavior.

**Step 4: Run test to verify it passes**

Run: `cargo test area_scan_clears_or_records_queue_from_python_backend_result --test routes`

Expected: PASS.

**Step 5: Commit**

```bash
git add app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs
git commit -m "api: reflect area backend outcomes in scanner status"
```

### Task 6: Add safe rollout documentation and UI confirmation checks

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/plans/2026-07-06-alg-2d-area-deep-parity.md`
- Optional Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Optional Test: `app/UI/MotionStudioWeb/src/services/api.test.ts`

**Step 1: Write the failing test**

Only add UI tests if response shape changes. The existing React API path tests should continue to assert:

```ts
expect(buildAreaStatusPath()).toBe('/area/status')
expect(buildAreaScanPath()).toBe('/area/scan')
expect(buildAreaRejoinPath()).toBe('/area/rejoin')
```

**Step 2: Run tests to verify current UI contract**

Run: `npm test -- api`

Expected: PASS if no UI path changes are needed.

**Step 3: Write minimal docs/config implementation**

Document rollout switches:

- `RUST_API_AREA_BACKEND=python`: production parity path using Python `area_runner.py` and real YOLO/detection/database integration.
- `RUST_API_AREA_BACKEND=fallback`: development path with Rust image-only writer and no YOLO/database defect writes.
- `RUST_API_AREA_BACKEND=proxy`: route execution to the Python 2D API service if it is already deployed.
- `RUST_API_AREA_PYTHON=.venv\Scripts\python.exe`: production interpreter.
- `RUST_API_AREA_RUNNER=app\algorithm_runtime_2D\area_runner.py`: packaged runner override.
- `RUST_API_AREA_PROXY_URL=http://127.0.0.1:6020`: proxy endpoint base when using Python service.

Keep the parity row Partial until at least one non-production coil exercises:

- `POST /area/rejoin` with `RUST_API_AREA_BACKEND=python`.
- `GET /image/area/...` reads generated AREA image/tile cache.
- database defect rows are written or explicitly disabled according to Python config.
- React/QML status panels show queue cleared or failure recorded.

**Step 4: Run final focused checks**

Run only after explicit authorization:

```bash
cargo test area_ --test routes
pytest test/test_alg_2d_area_runner.py -v
npm test -- api
```

Production-like smoke only after operator approval:

```powershell
$env:RUST_API_AREA_BACKEND='python'
$env:RUST_API_AREA_PYTHON='.venv\Scripts\python.exe'
$env:RUST_API_AREA_RUNNER='app\algorithm_runtime_2D\area_runner.py'
```

Then call `POST /area/rejoin` for a copied, non-production coil folder and inspect generated `jpg/AREA.jpg`, `preview/AREA.jpg`, `cache/area/tild`, and database side effects.

**Step 5: Commit**

```bash
git add docs/rust-tauri-parity.md docs/plans/2026-07-06-alg-2d-area-deep-parity.md app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/tests/routes.rs app/algorithm_runtime_2D/area_runner.py test/test_alg_2d_area_runner.py
git commit -m "infra: document area processing parity rollout"
```