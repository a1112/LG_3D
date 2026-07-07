# Coil Search By ID Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `/search/coilId/{coil_id}` parity and the React/Tauri流水号 search path by proving Rust, Python, Vite proxy, and UI history/fallback behavior match the QML operator workflow.

**Architecture:** Treat Python `app/Server/api/ApiDataBase.py::search_by_coil_id` plus `CoilDataBase.CoilSummary.search_coils_by_id_summary(..., by_coil=True)` as the backend source of truth: the route returns a summary-array response, not a detail object, and it filters to detected/summary rows. Rust should keep path validation in `routes.rs`, summary filtering in `CoilRepository::search_coils_by_id`, and Python-shaped rows through `coil_summary_to_python_json`; React should keep `/search/coilId/{id}` as the primary流水号 query and treat `/detail/{id}` fallback as an explicit UI convenience for secondary-only/TestData rows, not backend parity.

**Tech Stack:** Python FastAPI/SQLAlchemy reference service, Rust Axum/SQLx/serde_json API service, React/Vite/Tauri TypeScript UI, TanStack Query, Vitest, Rust `cargo test`, read-only PowerShell live parity checker.

---

### Task 1: Lock Python-compatible path validation and boundary behavior

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/routes.rs`
- Reference: `app/Server/api/ApiDataBase.py`

**Step 1: Add route boundary tests**

Add or tighten tests for:

```text
GET /search/coilId/abc
GET /search/coilId/1.2
GET /search/coilId/-1
GET /search/coilId/0
GET /search/coilId/00077
```

Expected behavior must be measured against live Python before locking in:

```text
abc -> 422 int_parsing
1.2 -> 422 int_parsing
-1 -> Python-observed FastAPI integer behavior, likely 200 []
0 -> Python-observed summary result, likely 200 []
00077 -> Python-observed integer normalization, likely same as 77
```

**Step 2: Keep FastAPI error JSON byte shape**

For validation failures, assert the existing FastAPI-compatible shape:

```rust
json!({
  "detail": [{
    "type": "int_parsing",
    "loc": ["path", "coil_id"],
    "msg": "Input should be a valid integer, unable to parse string as an integer",
    "input": "abc"
  }]
})
```

**Step 3: Correct Rust parsing only if Python differs**

If Python accepts signed integers, keep `parse_i64_path`. If Python path behavior differs for signs or leading zeroes, adjust `search_coil_id` parsing only for this route; do not reuse the stricter `{coil_id:int}` converter helper used by routes that are declared with `:int` in Python.

**Step 4: Run focused route tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test search_coil_id_
```

Expected: all `/search/coilId` route validation tests pass.

### Task 2: Prove summary-only backend semantics

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/repository.rs`
- Reference: `app/Server/rust_api_service/src/models.rs`

**Step 1: Add detected-summary fixture**

Use an in-memory row with `has_coil = true`, populated alarm summary fields, defect counts, max defect fields, next-process fields, and Python datetime objects.

**Step 2: Add detected result test**

Add `search_coil_id_returns_python_summary_array_for_detected_coil`:

```rust
let (status, body) = request_json(app_with_seed_data(), "GET", "/search/coilId/42").await;
assert_eq!(status, StatusCode::OK);
assert!(body.is_array());
assert_eq!(body[0]["Id"], 42);
assert_eq!(body[0]["SecondaryCoilId"], 42);
assert_eq!(body[0]["hasCoil"], true);
assert_eq!(body[0]["AlarmInfo"].is_object(), true);
assert_eq!(body[0]["CreateTime"]["year"], 2026);
```

Assert raw JSON field order if the existing summary serializer already tracks Python order.

**Step 3: Add secondary-only exclusion test**

Keep or tighten the existing behavior where `/search/coilId/77` returns `[]` for secondary-only data while `/detail/77` returns the object:

```rust
assert_eq!(search_body, json!([]));
assert_eq!(detail_body["Id"], 77);
```

This is intentional parity because the Python search route calls the summary search helper with `by_coil=True`.

**Step 4: Fix repository filtering if required**

`MySqlCoilRepository::search_coils_by_id` should keep:

```sql
WHERE COALESCE(HasCoil, 0) = 1 AND Id = ? ORDER BY Id DESC LIMIT 200
```

The in-memory repository should mirror the same predicate:

```rust
.filter(|coil| coil.has_coil && coil.id == coil_id)
```

**Step 5: Run focused backend tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test search_coil_id_returns_python_summary_array_for_detected_coil search_coil_id_secondary_only_rows_remain_empty_while_detail_resolves
```

Expected: PASS.

### Task 3: Align OpenAPI schema and operation metadata

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Preserve Python operation metadata**

Ensure OpenAPI for `GET /search/coilId/{coil_id}` keeps:

```text
summary: Search By Coil Id
operationId: search_by_coil_id_search_coilId__coil_id__get
path parameter: coil_id integer, required
422 HTTPValidationError response
200 array response using the same summary item schema as coil list/search-by-number/date
```

**Step 2: Add or tighten OpenAPI assertion**

Extend the route metadata test:

```rust
assert_eq!(body["paths"]["/search/coilId/{coil_id}"]["get"]["parameters"][0]["name"], "coil_id");
assert_eq!(body["paths"]["/search/coilId/{coil_id}"]["get"]["parameters"][0]["schema"]["type"], "integer");
assert!(body["paths"]["/search/coilId/{coil_id}"]["get"]["responses"].get("422").is_some());
```

**Step 3: Run focused OpenAPI test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test openapi_json_describes_coil_search_response_contracts_for_qml_tauri_ui
```

Expected: PASS.

### Task 4: Close React/Tauri流水号 search behavior

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/coilSearch.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/coilSearch.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`

**Step 1: Add path-builder test coverage**

Assert:

```ts
expect(buildSearchCoilIdPath(193113)).toBe('/search/coilId/193113')
expect(buildSearchCoilIdPath(77)).toBe('/search/coilId/77')
```

Do not URL-encode the integer segment differently from QML.

**Step 2: Preserve QML page routing**

Keep `SearchMode = 'coilNo' | 'date' | 'coilId'` and assert the流水号 search page calls `coilApi.searchByCoilId`, while the卷号 page always calls `coilApi.searchByCoilNo` even for numeric-looking coil numbers.

**Step 3: Make fallback explicit and bounded**

`buildSearchResultsWithDetailFallback` should only return the detail row when all of these are true:

```ts
request.kind === 'id'
backendRows.length === 0
detailRow?.id === request.coilId
```

It must not apply to卷号 search or to mismatched detail rows.

**Step 4: Add UI history ordering tests**

`applySearchResults` currently reverses backend rows through `buildQmlHistoryCoilList`. Add tests proving this matches QML `insert(0, item)` behavior for multi-row arrays and selects the first history item.

**Step 5: Run focused UI tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/coilSearch.test.ts src/services/api.test.ts src/components/OperationSidebar/OperationSidebar.test.ts
```

Expected: PASS.

### Task 5: Add a bounded live parity checker for search-by-ID

**Files:**
- Create: `app/Server/rust_api_service/tools/check_coil_search_id_parity.ps1`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Create a read-only checker**

Create a PowerShell script that accepts:

```powershell
param(
  [string]$PythonBase = 'http://127.0.0.1:5010',
  [string]$RustBase = 'http://127.0.0.1:5011',
  [string]$ViteBase = 'http://127.0.0.1:3015/api',
  [string[]]$CoilIds = @('16019', '1701', '1800', '193113', '0', '-1', 'abc', '00077')
)
```

For each id, request:

```text
/search/coilId/<id>
```

Compare status code, content type, raw body, parsed array length, first-row key order, first-row `Id`, `CoilNo`, `hasCoil`, `AlarmInfo`, `DefectCountS`, `DefectCountL`, `MaxDefectName`, and `NextInfo`.

**Step 2: Include detail-fallback diagnostics without changing backend parity**

For ids where Python and Rust search both return `[]`, optionally request `/detail/<id>` from Rust and Vite only to document whether React fallback can populate the UI. Do not treat detail fallback as backend search parity.

**Step 3: Run checker only when services are already running and validation is authorized**

```powershell
app\Server\rust_api_service\tools\check_coil_search_id_parity.ps1 `
  -PythonBase http://127.0.0.1:5010 `
  -RustBase http://127.0.0.1:5011 `
  -ViteBase http://127.0.0.1:3015/api `
  -CoilIds 16019,1701,1800,193113,0,-1,abc,00077
```

Expected: zero backend diffs for Python/Rust/Vite search responses, with separately reported detail-fallback availability.

### Task 6: Update ledger status based on evidence

**Files:**
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Mark complete only with sufficient evidence**

After Rust tests, UI tests, and live checker pass, update the `Coil search by ID` row from `Partial` to `Complete` only if:

```text
all tested Python/Rust/Vite search responses match
OpenAPI metadata matches Python
React流水号 search and fallback tests pass
no remaining search-by-ID-specific backend or UI gap exists
```

If any edge remains, keep `Partial` and document the exact remaining gap.

### Task 7: Optional commit only when requested

**Files:**
- Stage only files changed for this plan.

**Step 1: Review changed files**

Run only when commit is requested:

```powershell
git diff -- app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/coilSearch.ts app/UI/MotionStudioWeb/src/utils/coilSearch.test.ts app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/Server/rust_api_service/tools/check_coil_search_id_parity.ps1 docs/rust-tauri-parity.md
```

**Step 2: Commit**

Run only when commit is requested:

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/coilSearch.ts app/UI/MotionStudioWeb/src/utils/coilSearch.test.ts app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/Server/rust_api_service/tools/check_coil_search_id_parity.ps1 docs/rust-tauri-parity.md

git commit -m "api: close coil-id search parity"
```
