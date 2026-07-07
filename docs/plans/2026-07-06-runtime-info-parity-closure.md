# Runtime Info Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close parity for `GET /runtime_info` and its React system diagnostics / SystemInfo consumers.

**Architecture:** Use Python `app/Server/api/ApiInfo.py::runtime_info()` as the response contract: fixed top-level fields, Python version string, cache provider mode, CPU model string, optional torch CUDA GPU names, and CONFIG-driven local/developer/offline flags. Rust should expose the same shape without Rust-only fields, make environment/config override behavior explicit, avoid GPU over-reporting when Python would return an empty list, and keep React display tolerant of empty strings/arrays.

**Tech Stack:** Python FastAPI, cache provider config, optional torch CUDA detection, Rust Axum, environment/config marker helpers, OpenAPI schema generator, React Query, SystemDiagnostics page, SystemInfo modal, Vitest, focused Rust route tests, read-only live Python/Rust/Vite smoke checks.

---

### Task 1: Capture Python `/runtime_info` reference behavior

**Files:**
- Create: `test/runtime_info_parity/test_runtime_info_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing Python reference tests**

Mock `sys.version`, `platform.processor`, `platform.machine`, `cache.get_cache_mode`, `Base.CONFIG`, and optional `torch` behavior.

Required cases:
- Response top-level field order is `python_version`, `cache_mode`, `cpu_model`, `gpus`, `is_local`, `developer_mode`, `offline_mode`.
- `cpu_model` uses `platform.processor()`, falls back to `platform.machine()`, and falls back to `""` on exception.
- Missing or failing `torch` import returns `gpus = []`.
- CUDA unavailable returns `gpus = []`.
- CUDA available returns each `torch.cuda.get_device_name(idx)`.
- `is_local` comes from `CONFIG.isLoc`.
- `developer_mode` and `offline_mode` come from CONFIG attributes with default `False`.
- `cache_mode` is exactly `get_cache_mode()`.

**Step 2: Run Python reference tests**

Run: `pytest test/runtime_info_parity/test_runtime_info_reference.py -v`

Expected: FAIL until mocks and assertions capture current Python behavior.

**Step 3: Add matching Rust route tests**

Add tests for fixed field set/order, env override behavior, defaults, and no Rust-only extra fields.

**Step 4: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test runtime_info -- --nocapture`

Expected: PASS only when field set, defaults, and override behavior are explicit.

### Task 2: Lock Rust environment/config semantics

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Create: `docs/runtime-info-env-contract.md`

**Step 1: Write failing override tests**

Required cases:
- `RUST_API_PYTHON_VERSION` overrides Python subprocess probing.
- `PYTHON_VERSION` is a fallback override only when `RUST_API_PYTHON_VERSION` is absent.
- Missing Python executable returns an empty string rather than failing the route.
- `RUST_API_CACHE_MODE`, `IMAGE_CACHE_BACKEND`, and `CACHE_BACKEND` map `redis` to `redis` and all other values to `memory`, matching current Rust compatibility policy.
- No cache env defaults to Python reference `redis`.
- `API_DEVELOPER_MODE` true strings enable `developer_mode`.
- `API_OFFLINE_MODE` true strings enable `offline_mode`.
- `developer_mode=true` and `offline_mode=true` config markers are honored.

**Step 2: Run focused tests**

Run: `cargo test --target-dir target-codex-test runtime_info_returns_python_compatible_environment_shape runtime_info_defaults_cache_mode_to_python_reference_redis -- --nocapture`

Expected: PASS after env/config semantics are stable.

**Step 3: Document the contract**

In `docs/runtime-info-env-contract.md`, explain why Rust uses environment overrides and marker files to mirror Python process state rather than exposing Rust runtime metadata.

### Task 3: Lock GPU behavior and avoid Rust over-reporting

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `docs/runtime-info-env-contract.md`

**Step 1: Write failing GPU tests**

Required cases:
- With no `RUST_API_GPU_MODELS`, Rust returns `gpus = []` even if `nvidia-smi` exists.
- `RUST_API_GPU_MODELS="A;B"` returns `["A", "B"]`.
- Empty parts are trimmed/ignored.
- GPU values are strings only.

**Step 2: Run focused GPU tests**

Run: `cargo test --target-dir target-codex-test runtime_info_defaults_to_python_empty_gpu_list_without_explicit_models -- --nocapture`

Expected: PASS with no live GPU dependency.

**Step 3: Keep `/hardware` separate**

Do not use `/hardware` GPU detection to fill `/runtime_info.gpus`; Python uses torch CUDA here, not GPUtil/nvidia-smi.

### Task 4: Lock OpenAPI response schema

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing OpenAPI tests**

Required cases:
- `/runtime_info` operation metadata matches Python tags/summary/description/operationId.
- `200` response schema is `RuntimeInfoResponse`.
- Required fields match the Python field set.
- `gpus` is an array of strings.
- No Rust-only properties appear in schema.

**Step 2: Run focused OpenAPI tests**

Run: `cargo test --target-dir target-codex-test openapi_json_describes_runtime_info_response_contract_for_tauri_ui -- --nocapture`

Expected: PASS for runtime schema.

### Task 5: Lock React SystemDiagnostics and SystemInfo consumption

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/systemInfo.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/systemInfo.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/pages/SystemDiagnostics/SystemDiagnostics.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/SystemInfoModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/SystemInfoModal/SystemInfoModal.test.ts`

**Step 1: Write service-helper tests**

Assert `buildRuntimeInfoPath()` returns `/runtime_info` and `systemApi.getRuntimeInfo()` calls that route.

**Step 2: Write SystemInfo view-model tests**

Required cases:
- `python_version`, `cache_mode`, `cpu_model` render as strings.
- Empty `gpus = []` renders the established unknown label in HelpPop and `--` in SystemDiagnostics.
- Multiple GPU strings render one per line in HelpPop/SystemDiagnostics.
- Missing runtime response does not break the modal.

**Step 3: Write SystemDiagnostics tests**

Assert the runtime panel renders Python/cache/CPU/GPU/is_local/developer/offline rows and survives partial responses.

**Step 4: Run focused UI tests**

Run: `npm test -- systemInfo SystemInfoModal SystemDiagnostics api --runInBand`

Expected: PASS for runtime consumption.

### Task 6: Add read-only live regression checker

**Files:**
- Create: `scripts/runtime_info_parity/check_runtime_info.py`
- Create: `docs/runtime-info-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write a read-only checker**

The checker should accept explicit URLs and never mutate service state:

```bash
python scripts/runtime_info_parity/check_runtime_info.py --python-url http://127.0.0.1:5010 --rust-url http://127.0.0.1:5011 --vite-url http://127.0.0.1:3015/api
```

**Step 2: Compare stable invariants**

Assert:
- Same top-level key set across Python/Rust/Vite.
- Value types match for each field.
- `cache_mode` matches or is documented via explicit Rust override.
- `gpus` is `[]` unless explicit mirrored GPU override is configured.
- Vite proxy preserves Rust response exactly.
- No Rust-only fields appear.

**Step 3: Document sample results**

Record Python version shape, cache mode, mode flags, GPU behavior, and any intentional environment overrides.

### Task 7: Final evidence and ledger update

**Files:**
- Modify: `docs/runtime-info-env-contract.md`
- Modify: `docs/runtime-info-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Run focused Python reference tests**

Run: `pytest test/runtime_info_parity -v`

Expected: PASS for Python contract capture.

**Step 2: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test runtime_info openapi_json_describes_runtime_info_response_contract_for_tauri_ui -- --nocapture`

Expected: PASS for route behavior and OpenAPI schema.

**Step 3: Run focused UI tests**

Run: `npm test -- systemInfo SystemInfoModal SystemDiagnostics api --runInBand`

Expected: PASS for React consumption.

**Step 4: Run live read-only checker**

Run the checker against Python, Rust, and Vite proxy services and record results in `docs/runtime-info-parity-samples.md`.

**Step 5: Update parity row only after evidence exists**

Move `Runtime info` from Partial only after Python/Rust/UI tests plus live read-only checker are documented.

**Step 6: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/runtime_info_parity scripts/runtime_info_parity docs

git commit -m "api: close runtime info parity"
```
