# Diagnostic Endpoints and Speedtest Parity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close parity for `/download_test`, `/speedtest/download`, `POST /speedtest/upload`, and their React diagnostics helpers/UI consumers.

**Architecture:** Treat Python `app/Server/api/ApiTest.py` as the HTTP contract: `/download_test` serves `./test/zipdir.zip` as `downloaded_file.zip` or returns `{"error":"File not found"}`, `/speedtest/download` streams `size_in_mb` 1 MB zero chunks, and `/speedtest/upload` returns filename, MB, elapsed seconds, and MB/s. Rust should preserve Python-visible route behavior and FastAPI validation shapes while explicitly documenting the safer upload elapsed-time guard for Python's known zero-time division edge on tiny uploads.

**Tech Stack:** Python FastAPI reference routes, Rust Axum binary/multipart responses, Vite proxy, React Query/Ant Design diagnostics panel, Tauri/Web browser download behavior, Vitest, focused Rust route tests, bounded live smoke checks.

---

### Task 1: Capture Python diagnostic reference behavior

**Files:**
- Create: `test/diagnostic_parity/test_api_test_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing Python reference tests**

Use FastAPI `TestClient` and temporary cwd/config patches where possible.

Required cases:
- Missing `./test/zipdir.zip` returns `200 {"error":"File not found"}`.
- Existing `./test/zipdir.zip` returns `application/octet-stream` and attachment filename `downloaded_file.zip`.
- `/speedtest/download` default omits query and streams 10 MB.
- Positive `size_in_mb` streams `size_in_mb * 1048576` zero bytes.
- Negative `size_in_mb` yields an empty stream because `range(total_chunks)` is empty.
- Invalid `size_in_mb=abc` returns FastAPI `422 int_parsing` JSON.
- Multipart upload preserves `file.filename`.
- Missing multipart `file` returns FastAPI `422 missing` JSON.
- Tiny uploads may hit Python `ZeroDivisionError`; document this as a reference bug rather than forcing Rust to panic.

**Step 2: Run Python reference tests**

Run: `pytest test/diagnostic_parity/test_api_test_reference.py -v`

Expected: FAIL until the tests isolate cwd and capture current Python behavior.

**Step 3: Add matching Rust route tests**

Add route tests for default 10 MB metadata without materializing huge buffers when possible, positive/negative/invalid download sizes, missing file, fixture file success, upload success, missing multipart file, and filename preservation.

**Step 4: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test diagnostic_ speedtest_ -- --nocapture`

Expected: FAIL for any route-shape or validation mismatch.

### Task 2: Lock `/download_test` fixture path and binary response

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Create: `docs/diagnostic-download-test-paths.md`

**Step 1: Write failing path-priority tests**

Required path priority:
- `RUST_API_DOWNLOAD_TEST_FILE` explicit override wins for isolated tests.
- Python `Server.py` cwd-compatible `app/Server/test/zipdir.zip` wins when present.
- Repo fallback `test/zipdir.zip` is used only when the Python server path is absent.
- Missing file returns JSON error, not `404`.

**Step 2: Run focused path tests**

Run: `cargo test --target-dir target-codex-test diagnostic_download_test -- --nocapture`

Expected: PASS once path priority is locked.

**Step 3: Lock binary headers**

Assert success path includes:
- `Content-Type: application/octet-stream`.
- `Content-Disposition: attachment; filename="downloaded_file.zip"`.
- `Content-Length` when bytes are known.
- ZIP prefix preserved when fixture is a ZIP.

**Step 4: Document operator fixture behavior**

In `docs/diagnostic-download-test-paths.md`, state that production missing fixture is valid and matches Python's `{"error":"File not found"}` response.

### Task 3: Lock speedtest download semantics without memory blowups

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing download-size tests**

Required cases:
- Missing query defaults to 10 MB like Python.
- `size_in_mb=1` returns exactly 1,048,576 bytes.
- `size_in_mb=0` returns 0 bytes.
- `size_in_mb=-1` returns 0 bytes.
- `size_in_mb=abc` returns FastAPI-compatible `422 int_parsing` response.
- Very large positive values do not crash the service; define a safe streaming or bounded allocation strategy that preserves Python behavior for normal diagnostic sizes.

**Step 2: Run focused tests**

Run: `cargo test --target-dir target-codex-test speedtest_download -- --nocapture`

Expected: FAIL until size handling is locked.

**Step 3: Prefer streaming for large payloads**

If current Rust allocates a single `Vec` for the whole response, replace with a stream for large sizes while keeping headers/content type stable where feasible. Do not alter small-size behavior that tests already cover.

### Task 4: Lock speedtest upload multipart behavior

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Test: `app/UI/MotionStudioWeb/src/services/api-client.test.ts`

**Step 1: Write failing upload tests**

Required cases:
- Single `file` field returns `filename`, `file_size_mb`, `upload_time_s`, and `upload_speed_mb_s`.
- Quoted and unquoted multipart filenames are preserved.
- At least 5 MB upload succeeds.
- Empty file returns `0.0` size and finite speed metrics instead of panicking.
- Missing body returns FastAPI-compatible `422` missing-file JSON.
- Multiple file fields use the first `file` field like FastAPI's parameter binding, or document any intentional difference.

**Step 2: Run focused Rust upload tests**

Run: `cargo test --target-dir target-codex-test speedtest_upload -- --nocapture`

Expected: FAIL until multipart parsing and metrics are locked.

**Step 3: Lock React upload client**

Assert `diagnosticApi.uploadSpeedtest(formData)` posts multipart form data to `/speedtest/upload` and does not manually corrupt browser/Tauri multipart boundaries. If Axios sets boundaries automatically, remove any header that breaks native multipart behavior.

**Step 4: Run focused client tests**

Run: `npm test -- api-client api --runInBand`

Expected: PASS for upload route and request body behavior.

### Task 5: Lock React `/system` network-speed panel behavior

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/SystemDiagnostics.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`

**Step 1: Write failing UI tests**

Required cases:
- `/system` exposes a visible network speed-test section with download and upload controls.
- Download control uses `diagnosticApi.getSpeedtestDownloadUrl(size)` or direct URL construction for `/speedtest/download?size_in_mb=...`.
- Upload control builds `FormData` with key `file`.
- Upload result formatter accepts Python/Rust live field names: `upload_time_s`, `upload_speed_mb_s`, plus documented aliases if present.
- Upload failures show an error without clearing the previous successful result.
- The panel remains usable in Web preview through the Vite `/api` proxy.

**Step 2: Run focused UI tests**

Run: `npm test -- SystemDiagnostics api --runInBand`

Expected: PASS after network-speed UI parity is locked.

**Step 3: Keep maintenance-menu QML behavior separate**

QML `ToolsMenuView.qml` shows `网络测速` but has no `onClicked`. If React keeps that action disabled, document it as QML parity. Do not re-enable navigation from the titlebar maintenance menu unless QML grows an action.

### Task 6: Lock OpenAPI response/body schemas

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing OpenAPI tests**

Required cases:
- `/download_test` documents binary `application/octet-stream` and JSON missing-file response reality where supported by the generator.
- `/speedtest/download` documents `size_in_mb` integer query default `10` and binary octet-stream response.
- `/speedtest/upload` requestBody matches FastAPI multipart schema for required `file`.
- `/speedtest/upload` response schema includes `filename`, `file_size_mb`, `upload_time_s`, and `upload_speed_mb_s`.
- Shared Python/Rust response/requestBody schema diff remains zero for these routes.

**Step 2: Run focused OpenAPI tests**

Run: `cargo test --target-dir target-codex-test openapi_json_describes_diagnostic_and_image_response_contracts_for_qml_tauri_ui -- --nocapture`

Expected: PASS for diagnostic route docs.

### Task 7: Add bounded live smoke checker

**Files:**
- Create: `scripts/diagnostic_parity/check_diagnostic_endpoints.py`
- Create: `docs/diagnostic-endpoints-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write a side-effect-bounded checker**

The checker should accept explicit URLs and create only temporary upload/ZIP fixtures under a temp directory:

```bash
python scripts/diagnostic_parity/check_diagnostic_endpoints.py --python-url http://127.0.0.1:5010 --rust-url http://127.0.0.1:5011 --vite-url http://127.0.0.1:3015/api
```

**Step 2: Check stable invariants**

Assert:
- Missing `/download_test` JSON matches when fixture is absent.
- Temporary ZIP fixture success path returns stable content type, disposition, length, and ZIP prefix.
- `/speedtest/download?size_in_mb=1` returns 1 MB on Python/Rust/Vite.
- Negative and invalid query cases match.
- 5 MB upload succeeds on Python/Rust/Vite and preserves filename.
- Missing upload body returns FastAPI-compatible `422`.

**Step 3: Record accepted Python edge**

Document that tiny uploads can produce Python `500` due to zero elapsed time; Rust keeps finite guarded metrics and should be judged on successful practical upload sizes.

**Step 4: Remove temporary artifacts**

The checker must remove temporary ZIP and upload files after the run.

### Task 8: Final evidence and ledger update

**Files:**
- Modify: `docs/diagnostic-download-test-paths.md`
- Modify: `docs/diagnostic-endpoints-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Run focused Python reference tests**

Run: `pytest test/diagnostic_parity -v`

Expected: PASS for captured Python route behavior.

**Step 2: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test diagnostic_ speedtest_ openapi_json_describes_diagnostic_and_image_response_contracts_for_qml_tauri_ui -- --nocapture`

Expected: PASS for route behavior and OpenAPI docs.

**Step 3: Run focused React tests**

Run: `npm test -- SystemDiagnostics api api-client --runInBand`

Expected: PASS for service helpers and network-speed panel behavior.

**Step 4: Run bounded live smoke**

Run the checker against Python, Rust, and Vite proxy URLs. Record stable invariants and accepted tiny-upload edge behavior.

**Step 5: Update parity row only after evidence exists**

Move `Diagnostic test endpoints` from Partial only after Python/Rust/UI tests and bounded live smoke are documented.

**Step 6: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/diagnostic_parity scripts/diagnostic_parity docs

git commit -m "api: close diagnostic endpoint parity"
```
