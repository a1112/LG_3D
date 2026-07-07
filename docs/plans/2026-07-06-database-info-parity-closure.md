# Database Info Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close parity for `GET /database_info` and its React SystemInfo/diagnostics consumers, including nullable latest-coil behavior and stable live regression evidence.

**Architecture:** Treat Python `app/Server/api/ApiInfo.py::database_info()` as the contract: it returns `url`, `echo`, and `coil_last`; `coil_last` is `to_dict(get_coil(1)[0])` or `null` when the lookup fails. Rust must preserve the Python/FastAPI JSON shape, URL tuple/object serialization, latest `Coil` table source, `DetectionTime` object shape, and field order, while React should only display the database URL and tolerate `coil_last = null`.

**Tech Stack:** Python FastAPI, CoilDataBase SQLAlchemy `engine.url`, Rust Axum/repository layer, OpenAPI schema generator, React Query, React SystemInfo modal, Vitest, focused Rust route tests, bounded live Python/Rust/Vite smoke checks.

---

### Task 1: Capture Python `/database_info` reference behavior

**Files:**
- Create: `test/database_info_parity/test_database_info_reference.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing Python reference tests**

Mock `engine`, `get_coil`, and `to_dict` so no real database is required.

Required cases:
- Successful latest coil returns top-level keys in Python order: `url`, `echo`, `coil_last`.
- `coil_last` is the `Coil` table row from `get_coil(1)[0]`, not a `coil_summary` row.
- `DetectionTime` serializes through FastAPI/Pydantic into Python datetime object fields when using the real response serialization path.
- If `get_coil(1)` raises or returns no first row, `coil_last` becomes `null` and route still returns `200`.
- `engine.echo` is returned as a boolean.
- `engine.url` serializes into the same JSON shape FastAPI currently emits.

**Step 2: Run Python reference tests**

Run: `pytest test/database_info_parity/test_database_info_reference.py -v`

Expected: FAIL until mocks and FastAPI serialization assertions capture current Python behavior.

**Step 3: Add matching Rust tests**

Add route tests for success, no latest coil, repository error, and field order. Use the in-memory repository to avoid live DB dependency.

**Step 4: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test database_info -- --nocapture`

Expected: PASS only after nullable/latest-coil and field-order cases match Python.

### Task 2: Lock latest `Coil` table source and datetime JSON shape

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Modify: `app/Server/rust_api_service/src/models.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing source-selection tests**

Required cases:
- Repository has a `coil_summary` row but no latest `Coil` table child: `coil_last` is `null` or follows Python `get_coil(1)` behavior, not summary fallback.
- Repository has latest `Coil` child with a different `Id` than `SecondaryCoilId`: `coil_last.Id` is the child `Coil.Id`.
- `CoilNo` and summary-only fields are absent from `coil_last`.
- `DetectionTime` is serialized as `{year, month, weekday, day, hour, minute, second}`.

**Step 2: Run focused tests**

Run: `cargo test --target-dir target-codex-test database_info_coil_last -- --nocapture`

Expected: FAIL for any accidental summary fallback or wrong datetime shape.

**Step 3: Correct mapping minimally**

Keep `latest_coil_to_python_json()` as the single mapper for this route. Avoid reusing detail/list mappers that include summary fields.

**Step 4: Preserve Python field order**

Lock raw JSON order for `coil_last`:

```text
SecondaryCoilId, DetectionTime, DefectCountL, Status_L, Grade, DefectCountS, Id, CheckStatus, Status_S, Msg
```

### Task 3: Lock database URL serialization and config source

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Create: `docs/database-info-url-contract.md`

**Step 1: Write failing URL-shape tests**

Required cases:
- MySQL URL with username, password, host, port, database, and query charset serializes like Python/FastAPI `engine.url` response.
- Password handling matches the current Python exposure behavior. If Python exposes masked password or URL parts, Rust must match that, not invent a new security shape for this compatibility route.
- Missing `COIL_DATABASE_URL` falls back to the same default metadata Rust uses elsewhere, and this fallback is documented.
- `echo` defaults to `false` unless a real config source says otherwise.

**Step 2: Run focused URL tests**

Run: `cargo test --target-dir target-codex-test database_info_returns_python_compatible_startup_shape -- --nocapture`

Expected: PASS after URL shape is stable.

**Step 3: Document the contract**

In `docs/database-info-url-contract.md`, record the exact JSON shape and any accepted masking/exposure behavior so UI code does not guess.

### Task 4: Lock OpenAPI response contract

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Write failing OpenAPI schema tests**

Required cases:
- `/database_info` operation metadata matches Python summary, description, tags, and operationId.
- `200` response schema is `DatabaseInfoResponse`.
- `DatabaseInfoResponse` requires `url`, `echo`, and `coil_last`.
- `coil_last` is nullable.
- Latest-coil schema contains only Python `Coil` table fields used by this route.

**Step 2: Run focused OpenAPI tests**

Run: `cargo test --target-dir target-codex-test openapi_json_describes_startup_info_response_contracts_for_tauri_ui openapi_json_preserves_python_basic_operation_metadata -- --nocapture`

Expected: PASS for database-info docs.

### Task 5: Lock React SystemInfo and service helper consumption

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/services/api.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/systemInfo.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/systemInfo.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/SystemInfoModal/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/SystemInfoModal/SystemInfoModal.test.ts`

**Step 1: Write service-helper tests**

Assert `buildDatabaseInfoPath()` returns `/database_info` and `systemApi.getDatabaseInfo()` calls that path.

**Step 2: Write SystemInfo view-model tests**

Required cases:
- Database URL array/object/string formats render as the QML-style comma/string display currently used by HelpPop.
- `coil_last = null` does not break SystemInfo modal rendering.
- Missing `/database_info` response falls back to `未知` or the current established unknown label.
- The modal requests `/database_info` only while open.

**Step 3: Run focused UI tests**

Run: `npm test -- systemInfo SystemInfoModal api --runInBand`

Expected: PASS for database-info consumption.

### Task 6: Add bounded live regression checker

**Files:**
- Create: `scripts/database_info_parity/check_database_info.py`
- Create: `docs/database-info-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Write a read-only checker**

The checker should accept explicit URLs and never mutate the database:

```bash
python scripts/database_info_parity/check_database_info.py --python-url http://127.0.0.1:5010 --rust-url http://127.0.0.1:5011 --vite-url http://127.0.0.1:3015/api
```

**Step 2: Compare stable invariants**

Assert:
- Python/Rust/Vite top-level key sets match.
- `echo` values match.
- `url` JSON values match exactly or match documented normalization.
- If Python `coil_last` is not null, Rust/Vite `coil_last` raw JSON is byte-identical or field-by-field identical including field order.
- If Python `coil_last` is null, Rust/Vite also return null.

**Step 3: Document sample results**

Record latest coil ids, `DetectionTime` shape, URL shape, and whether raw JSON was byte-identical.

### Task 7: Final evidence and ledger update

**Files:**
- Modify: `docs/database-info-url-contract.md`
- Modify: `docs/database-info-parity-samples.md`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Run focused Python reference tests**

Run: `pytest test/database_info_parity -v`

Expected: PASS for Python contract capture.

**Step 2: Run focused Rust tests**

Run: `cargo test --target-dir target-codex-test database_info openapi_json_describes_startup_info_response_contracts_for_tauri_ui -- --nocapture`

Expected: PASS for route, mapper, and OpenAPI behavior.

**Step 3: Run focused UI tests**

Run: `npm test -- systemInfo SystemInfoModal api --runInBand`

Expected: PASS for React consumption.

**Step 4: Run live read-only checker**

Run the checker against Python, Rust, and Vite proxy services, then record the result in `docs/database-info-parity-samples.md`.

**Step 5: Update parity row only after evidence exists**

Move `Database info` from Partial only after the no-row/error/null cases, OpenAPI schema, React consumption, and live read-only checker are documented.

**Step 6: Optional commit only when requested by repository owner**

Do not commit automatically in this workspace. If requested, use:

```bash
git add app/Server/rust_api_service app/UI/MotionStudioWeb test/database_info_parity scripts/database_info_parity docs

git commit -m "api: close database info parity"
```
