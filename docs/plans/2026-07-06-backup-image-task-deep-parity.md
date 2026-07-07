# Backup Image Task Deep Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close Python-compatible behavior for `GET /backupImageTask/{from_id}/{to_id}/{save_folder:path}` and `WS /ws/backupImageTask`, including copy semantics, compression, WebSocket lifecycle, React/Tauri popup behavior, and production-sample verification.

**Architecture:** Treat `app/Base/utils/Backup.py` and `app/Server/api/ApiBackupServer.py` as the reference: Python creates the destination root, starts one worker thread per configured capture folder, copies existing coil folders for the half-open `[from_id, to_id)` range, runs `ZipAndDeletionCameraData` per copied camera root, joins every worker, returns JSON `null` for HTTP, and sends WebSocket text `100` only after a successful WebSocket request. Rust should preserve a safe synchronous implementation where exact thread timing is unobservable, but route status, filesystem output, copy failure behavior, compression output, and WebSocket close/progress semantics must match Python at the API boundary.

**Tech Stack:** Rust Axum, Rust filesystem/image/NPY helpers, Python FastAPI reference implementation, QML `BackupDataView`, React + Tauri `BackupImageModal`, Vitest, pytest, focused Rust route tests, explicit production-sample filesystem gates.

---

### Task 1: Capture Python backup reference behavior in fixtures

**Files:**
- Create: `test/backup_image_parity/README.md`
- Create: `test/backup_image_parity/fixtures.py`
- Create: `test/backup_image_parity/test_backup_image_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write the failing Python reference fixture test**

Create a fixture that mirrors `serverConfigProperty.surfaceConfigPropertyDict[*].folderList[*].source` with multiple capture roots:

```python
from pathlib import Path


def build_backup_source(root: Path, source_name: str, coil_ids: list[int]) -> Path:
    source = root / source_name
    for coil_id in coil_ids:
        coil = source / str(coil_id)
        (coil / '2D').mkdir(parents=True, exist_ok=True)
        (coil / '3D').mkdir(parents=True, exist_ok=True)
        (coil / 'meta.txt').write_text(f'{source_name}:{coil_id}', encoding='utf-8')
    return source
```

Assert the Python task creates:

```text
{save_folder}/{source_name}/{coil_id}/...
```

for every existing coil id in `[from_id, to_id)` and skips missing coil ids silently.

**Step 2: Run the reference test**

Run: `pytest test/backup_image_parity/test_backup_image_reference.py -v`

Expected: FAIL until the fixture patches Python config and asserts the reference output.

**Step 3: Add matching Rust fixture helpers**

Add Rust test helpers beside the existing `backup_image_task_*` tests in `app/Server/rust_api_service/tests/routes.rs` so Python and Rust fixtures use the same source-root names, coil ids, and destination expectations.

**Step 4: Run focused Rust fixture tests**

Run: `cargo test --target-dir target-codex-test backup_image_task_fixture -- --nocapture`

Expected: PASS for fixture construction only; behavior-specific assertions are added in later tasks.

### Task 2: Lock copytree and overwrite/error semantics

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Test: `test/backup_image_parity/test_backup_image_reference.py`

**Step 1: Write failing copy semantics tests**

Required cases:
- Existing source coil folders in `[from_id, to_id)` are copied.
- Missing source coil folders are skipped without failing the entire task.
- Empty range `from_id >= to_id` creates only the destination root.
- Nonexistent configured capture root does not fail the entire Python task if no coil folder exists under it.
- Existing destination coil folder behavior matches Python `shutil.copytree` failure semantics.

**Step 2: Run the reference tests**

Run: `pytest test/backup_image_parity/test_backup_image_reference.py::test_existing_destination_matches_python_copytree_failure -v`

Expected: FAIL until the Python expectation is captured. If Python raises for existing destination through HTTP, record the exact FastAPI response or WebSocket close behavior.

**Step 3: Correct Rust minimally**

Current Rust uses `copy_dir_replace`, which can be more permissive than Python `shutil.copytree`. Change only the backup-image path if tests prove Python fails on existing destination:

```rust
fn copy_backup_dir_python_like(from: &Path, to: &Path) -> std::io::Result<()> {
    if to.exists() {
        return Err(std::io::Error::new(std::io::ErrorKind::AlreadyExists, "destination exists"));
    }
    copy_dir_replace(from, to)
}
```

If production users depend on overwrite behavior, keep a temporary compatibility env switch such as `RUST_API_BACKUP_IMAGE_OVERWRITE=true`, but default to Python-compatible behavior.

**Step 4: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test backup_image_task_ -- --nocapture`

Expected: PASS for copy/skip/empty/existing-destination cases.

### Task 3: Close compression parity for copied camera payloads

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Test: `test/backup_image_parity/test_backup_image_reference.py`

**Step 1: Write failing compression parity tests**

Required cases:
- `2D/*.bmp` converts to quality-95 `.jpg` and original `.bmp` is removed.
- `3D/*.npy` converts to `.npz` with the same array entry expected by Python `ZipAndDeletionCameraData`.
- Non-BMP and non-NPY files remain untouched.
- Case variants such as `2d`/`3d` are handled only if Python handles them; otherwise Rust should not broaden behavior silently.
- Compression failure behavior matches Python thread behavior closely enough at the API boundary.

**Step 2: Run Python compression reference tests**

Run: `pytest test/backup_image_parity/test_backup_image_reference.py::test_zip_and_deletion_camera_data_contract -v`

Expected: FAIL until Python output names and deletion behavior are explicitly asserted.

**Step 3: Correct Rust compression semantics**

Adjust only these helpers as needed:
- `compress_backup_camera_data`
- `compress_backup_camera_coil`
- `compress_bmp_to_jpeg`
- `compress_npy_to_npz`

Do not change unrelated `/coilData` or image-service compression paths.

**Step 4: Run focused Rust compression tests**

Run: `cargo test --target-dir target-codex-test backup_image_task_compresses -- --nocapture`

Expected: PASS and generated output matches Python path/name/delete semantics.

### Task 4: Match WebSocket request, progress, close, and malformed-payload behavior

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/UI/MotionStudioWeb/src/utils/backupImage.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/BackupImageModal/index.tsx`
- Test: `app/UI/MotionStudioWeb/src/utils/backupImage.test.ts`
- Test: `app/UI/MotionStudioWeb/src/components/BackupImageModal/BackupImageModal.test.ts`

**Step 1: Write failing WebSocket route tests**

Required cases:
- Valid JSON `{from_id,to_id,folder}` sends exactly text `100` after successful backup.
- Malformed JSON closes the connection without sending a Rust-only error payload.
- Missing `from_id`, `to_id`, or `folder` closes like Python's `KeyError` path.
- Filesystem failure closes without sending `100`.
- Multiple valid messages on one open socket are handled sequentially like Python's `while True` loop.

**Step 2: Run focused WebSocket tests**

Run: `cargo test --target-dir target-codex-test backup_image_task_websocket -- --nocapture`

Expected: FAIL for any mismatch in close or multi-message behavior.

**Step 3: Implement minimal Rust WebSocket corrections**

Keep the protocol text-only. Do not add JSON progress messages unless the Python reference adds them. Preserve the current `100` completion marker for UI compatibility.

**Step 4: Write React lifecycle tests**

Assert the modal:
- Opens the WebSocket when the modal opens.
- Reuses the existing WebSocket when the operator clicks `备份`.
- Does not create a second socket per click.
- Shows `连接断开!` on early close before completion.
- Treats numeric messages `>= 100` as finished.
- Allows reconnect after an error.

**Step 5: Run focused React tests**

Run: `npm test -- BackupImageModal backupImage --runInBand`

Expected: PASS for QML-compatible WebSocket lifecycle behavior.

### Task 5: Preserve QML range and destination defaults in React/Tauri

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/backupImage.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/BackupImageModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Test: `app/UI/MotionStudioWeb/src/utils/backupImage.test.ts`
- Test: `app/UI/MotionStudioWeb/src/services/api.test.ts`

**Step 1: Write failing UI helper tests**

Required cases:
- Initial range is `min(Id)..max(Id)` from the current visible coil list, matching QML's current list source.
- Empty list initializes to `0..0` without starting backup work.
- Default name is `备份_yyyy_MM_dd hh_mm_ss`.
- Tauri desktop directory replaces the fallback `桌面` once available.
- Windows path segments keep Python-compatible path routing through `/backupImageTask/{...}/{save_folder:path}`.
- `openBackupImageFolder` uses native `open_path` first and browser `file:///...` fallback second.

**Step 2: Run helper tests**

Run: `npm test -- backupImage api --runInBand`

Expected: PASS after helper parity is locked.

**Step 3: Correct only helper and modal behavior**

Do not introduce a new backup API shape. Keep the QML-compatible field names exactly as `{from_id,to_id,folder}`.

### Task 6: Add a production-sample safe checker

**Files:**
- Create: `scripts/backup_image_parity/check_backup_image_parity.py`
- Create: `docs/backup-image-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write a bounded checker script**

The script must require explicit source and destination roots. It must refuse to run against broad roots like `D:\`, `/`, or the repository root.

```bash
python scripts/backup_image_parity/check_backup_image_parity.py --from-id 193113 --to-id 193114 --source-root D:\Capture\S_D --rust-url http://127.0.0.1:5011 --dest D:\Temp\backup-parity
```

**Step 2: Compare stable filesystem output**

Record:
- Created source-name folders.
- Copied coil folder names.
- Count of copied files by extension.
- BMP-to-JPG deletion/conversion result.
- NPY-to-NPZ deletion/conversion result.
- Presence of untouched sidecar files.

Do not compare JPEG bytes if Python and Rust encoders differ; compare dimensions and readable format instead.

**Step 3: Document representative samples**

In `docs/backup-image-parity-samples.md`, record the exact source roots, coil id range, file-type mix, route used, and whether the checker used HTTP, WebSocket, or both.

**Step 4: Update the parity ledger only after evidence exists**

Change the `Backup image task` row from Partial to Complete only after fixture tests and at least one bounded production-like sample prove parity.

### Task 7: Add rollout safety gates

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/UI/MotionStudioWeb/src/components/BackupImageModal/index.tsx`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Keep writes explicit and operator-triggered**

Do not run backup copy work on modal open. Modal open may create the WebSocket only; copy work starts only after the operator clicks `备份`.

**Step 2: Keep destructive behavior limited to the destination folder**

BMP/NPY deletion must happen only inside copied backup output, never inside configured capture source roots.

**Step 3: Run final focused checks**

Run: `pytest test/backup_image_parity -v`

Run: `cargo test --target-dir target-codex-test backup_image_task_ -- --nocapture`

Run: `npm test -- BackupImageModal backupImage api --runInBand`

Run the bounded sample checker with an explicit temporary destination.

Expected: all focused checks pass, and no source capture files are modified.

**Step 4: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/backup_image_parity scripts/backup_image_parity docs

git commit -m "api: close backup image parity"
```
