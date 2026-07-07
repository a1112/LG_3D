# Hardware Status Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close Python/QML-compatible behavior for `GET /hardware` and its React `/system` plus global-alarm consumers while accepting that live CPU, memory, disk, and GPU samples cannot be byte-identical across separate processes.

**Architecture:** Treat `app/Base/utils/Hardware.py` as the response contract and QML `AlarmHardware` / `AlarmItemHardwareItem` as the display contract. Rust may use `sysinfo` and `nvidia-smi` instead of Python `psutil` and `GPUtil`, but it must preserve field names, Chinese labels/messages, thresholds, percentage formatting, disk ordering, no-GPU fallback, and stable UI consumption semantics.

**Tech Stack:** Python FastAPI reference API, `psutil`, `GPUtil`, Rust Axum, `sysinfo`, `nvidia-smi`, React Query, React global alarm modal, Vitest, focused Rust route tests, bounded live smoke checks.

---

### Task 1: Capture Python hardware response contract

**Files:**
- Create: `test/hardware_parity/test_hardware_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing Python reference tests**

Use monkeypatching instead of real hardware sampling:

```python
def test_cpu_info_thresholds(monkeypatch):
    monkeypatch.setattr(Hardware.psutil, 'cpu_percent', lambda: 71.0)
    assert Hardware.get_cpu_info() == {
        'key': 'CPU',
        'value': '71.0%',
        'msg': 'CPU 使用率: 71.0%',
        'level': 2,
    }
```

Required cases:
- CPU level thresholds: `>90` level 3, `>70` level 2, otherwise level 1.
- Memory message includes available MB with two decimals.
- Disk aggregates `used / total * 100`, skips partitions whose usage raises `OSError`, and returns `0.00%` when total is zero.
- Disk line format is `分区: {device}, 总大小: ... GB, 已用: ... GB, 可用: ... GB, 使用率: {percent}%`.
- GPU no-device fallback returns `value = "0.0%"`, `msg = "未检测到 GPU"`, `level = 1`.
- GPU multi-device max load determines `value` and `level`, while each line uses two-decimal usage.

**Step 2: Run Python reference tests**

Run: `pytest test/hardware_parity/test_hardware_reference.py -v`

Expected: FAIL until mocks and assertions capture the Python contract without touching real hardware.

**Step 3: Add matching Rust pure-helper tests**

Where Rust helper functions are private, add tests in `app/Server/rust_api_service/tests/routes.rs` or a route-test-only module that verifies:
- `level_from_percent()` thresholds.
- `format_percent()` decimal behavior.
- Disk sorting helper ordering.
- `no_gpu_info()` fallback body.
- GPU CSV parsing behavior through an injectable parser.

**Step 4: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test hardware_ -- --nocapture`

Expected: FAIL for any formatting or threshold mismatch.

### Task 2: Make Rust GPU parsing testable and Python-compatible

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing GPU CSV parser tests**

Required cases:
- `"NVIDIA RTX 4090, 13"` becomes `显卡: NVIDIA RTX 4090, 使用率: 13.00%`, `value = "13.0%"`, `level = 1`.
- Multiple GPUs use the max utilization for `value` and `level`.
- Empty stdout returns the Python no-GPU fallback.
- Malformed usage values become `0.0` only for that row, matching current Rust defensive behavior if retained.
- GPU names containing commas are handled correctly by splitting from the right.

**Step 2: Run focused parser tests**

Run: `cargo test --target-dir target-codex-test gpu_info -- --nocapture`

Expected: FAIL until parsing is isolated from spawning `nvidia-smi`.

**Step 3: Extract parser without changing route output**

Keep `gpu_info()` responsible for command execution, but delegate stdout parsing:

```rust
fn gpu_info_from_nvidia_smi_csv(stdout: &str) -> Value
```

**Step 4: Preserve no-command fallback**

If `nvidia-smi` is missing, nonzero, or returns no valid rows, return Python-compatible no-GPU fallback. Do not expose Rust command errors in the operator response.

### Task 3: Lock disk formatting and ordering with fixture data

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Test: `test/hardware_parity/test_hardware_reference.py`

**Step 1: Write fixture tests for disk line formatting**

Python uses `partition.device` while Rust currently uses mount labels from `sysinfo`. Define a compatibility rule in tests:
- Windows labels should appear as `C:\`, `D:\`, etc.
- Rows are sorted by mount label for stable parity with psutil on Windows.
- Percent values use one decimal in each partition line and two decimals for aggregate `disk.value`.

**Step 2: Run focused disk tests**

Run: `cargo test --target-dir target-codex-test disk_status_lines_are_sorted_by_mount_label_like_python -- --nocapture`

Expected: PASS for existing sort coverage, then add missing format cases.

**Step 3: Add injectable disk fixture helper if needed**

Avoid broad refactors. A small helper is enough:

```rust
fn disk_info_from_samples(samples: &[DiskStatusSample]) -> Value
```

Keep the route path using real `Disks::new_with_refreshed_list()`.

### Task 4: Lock `/hardware` route and OpenAPI response contract

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing route-shape tests**

Required cases:
- `GET /hardware` returns only `cpu`, `memory`, `disk`, and `gpu` top-level keys.
- Each item has `key`, `value`, `msg`, and `level`.
- `value` fields are strings ending in `%` for cpu/memory/disk/gpu fallback.
- `level` fields are numbers `1..3`.
- Route does not panic if CPU, disk, or GPU samples are absent.

**Step 2: Run focused route tests**

Run: `cargo test --target-dir target-codex-test hardware_returns_python_compatible_status_objects -- --nocapture`

Expected: PASS after the route is stable.

**Step 3: Lock OpenAPI schema**

Ensure `/hardware` response points to `HardwareStatusResponse`, and `HardwareStatusItem` includes `key`, `value`, `msg`, and `level` as required fields.

**Step 4: Run focused OpenAPI tests**

Run: `cargo test --target-dir target-codex-test openapi_json_describes_camera_and_hardware_status_contracts_for_tauri_ui -- --nocapture`

Expected: PASS.

### Task 5: Lock React `/system` and global-alarm hardware consumption

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/utils/globalAlarm.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/globalAlarm.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/GlobalAlarmModal/GlobalAlarmModal.test.ts`

**Step 1: Write service route tests**

Assert `buildHardwarePath()` and both hardware API client aliases call `/hardware`. If there are duplicate clients, document why both exist or consolidate carefully without breaking imports.

**Step 2: Write global-alarm tests**

QML server-status cards use only `key`, `value`, and `msg`; the delegate level stays at default `1`. Required cases:
- Backend `level: 2` or `level: 3` does not change hardware card view-model level.
- Camera and network card levels still contribute normally.
- Hardware cards render `title : value` with the QML colon separator.
- Missing hardware data renders the existing empty server-status state.

**Step 3: Write `/system` display tests**

If current tests only assert JSON preview exists, add cases for:
- Hardware panel queries `/hardware`.
- The panel remains visible when hardware query fails or returns partial data.
- Refresh actions that include hardware do not trigger side-effect routes.

**Step 4: Run focused React tests**

Run: `npm test -- globalAlarm SystemDiagnostics api --runInBand`

Expected: PASS for UI consumption parity.

### Task 6: Add bounded live smoke documentation

**Files:**
- Create: `scripts/hardware_parity/check_hardware_status.py`
- Create: `docs/hardware-status-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write a comparison script that tolerates live sampling drift**

The script should compare Python and Rust only for stable invariants:

```bash
python scripts/hardware_parity/check_hardware_status.py --python-url http://127.0.0.1:5010 --rust-url http://127.0.0.1:5011 --vite-url http://127.0.0.1:3015/api
```

**Step 2: Compare stable invariants only**

Accept drift in numeric samples. Assert:
- Same top-level key set.
- Same per-item required key set.
- Same Chinese labels for `key` fields.
- Disk partition labels are in the same sorted order when both services see the same disks.
- No-GPU fallback text matches if both services report no GPU.
- Percent fields parse as percentages.
- Vite proxy preserves Rust shape.

**Step 3: Document sample output**

In `docs/hardware-status-parity-samples.md`, record:
- Host name or anonymized hardware class.
- Whether NVIDIA GPU was present.
- Python/Rust/Vite stable invariant results.
- Any allowed sample drift, such as CPU percent differences.

**Step 4: Do not require byte equality**

Hardware status is sampled live by separate processes. Completion must be based on stable contract invariants and UI behavior, not raw byte equality.

### Task 7: Final evidence and ledger update

**Files:**
- Modify: `docs/hardware-status-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Run focused Python reference tests**

Run: `pytest test/hardware_parity -v`

Expected: PASS for mocked Python contract tests.

**Step 2: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test hardware_ gpu_info disk_status openapi_json_describes_camera_and_hardware_status_contracts_for_tauri_ui -- --nocapture`

Expected: PASS for route, helper, disk, GPU, and OpenAPI contracts.

**Step 3: Run focused React tests**

Run: `npm test -- globalAlarm SystemDiagnostics api --runInBand`

Expected: PASS for system diagnostics and global-alarm hardware consumption.

**Step 4: Run bounded live smoke**

Run the comparison script against active Python/Rust/Vite services. Record stable invariant results and any accepted live-sampling drift.

**Step 5: Update parity row only after evidence exists**

Move `Hardware status` from Partial only when reference tests, Rust tests, UI tests, and live invariant smoke are documented.

**Step 6: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/hardware_parity scripts/hardware_parity docs

git commit -m "api: close hardware status parity"
```
