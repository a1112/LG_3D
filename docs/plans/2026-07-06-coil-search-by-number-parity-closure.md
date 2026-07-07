# Coil Search By Number Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `/search/coilNo/{coil_no}` parity and the React/Tauri卷号 search path by proving Python, Rust, Vite proxy, and UI history behavior match QML operator expectations.

**Architecture:** Treat Python `app/Server/api/ApiDataBase.py::search_by_coil_no` plus `CoilDataBase.CoilSummary.search_coils_by_coil_no_summary(..., by_coil=True)` as the backend source of truth: the route returns a summary-array response filtered to detected/summary rows, using substring search on coil number. Rust should keep path extraction in `routes.rs`, `HasCoil` + `LIKE` filtering in `CoilRepository::search_coils_by_no`, and Python-shaped rows through `coil_summary_to_python_json`; React should keep the 卷号 page on `/search/coilNo/{coil_no}` even when the input is numeric-looking, with no `/detail/{id}` fallback.

**Tech Stack:** Python FastAPI/SQLAlchemy reference service, Rust Axum/SQLx/serde_json API service, React/Vite/Tauri TypeScript UI, TanStack Query, Vitest, Rust `cargo test`, read-only PowerShell live parity checker.

---

### Task 1: Lock backend substring-search semantics

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/repository.rs`
- Reference: `app/Server/api/ApiDataBase.py:392`

**Step 1: Add exact and partial match fixtures**

Create in-memory summary rows with:

```rust
CoilNo = "4V07441200", Id = 16039, has_coil = true
CoilNo = "4V07441201", Id = 16040, has_coil = true
CoilNo = "193113", Id = 193113, has_coil = true
CoilNo = "SECONDARY-ONLY", Id = 77, has_coil = false
```

**Step 2: Add substring search test**

Add `search_coil_no_returns_python_summary_array_for_partial_match`:

```rust
let (status, body) = request_json(app_with_search_rows(), "GET", "/search/coilNo/4V0744").await;
assert_eq!(status, StatusCode::OK);
assert_eq!(body.as_array().unwrap().len(), 2);
assert_eq!(body[0]["hasCoil"], true);
assert_eq!(body[0]["CoilNo"].as_str().unwrap().contains("4V0744"), true);
```

**Step 3: Add exact numeric-looking coil number test**

Add `search_coil_no_keeps_numeric_text_as_coil_number`:

```rust
let (status, body) = request_json(app_with_search_rows(), "GET", "/search/coilNo/193113").await;
assert_eq!(status, StatusCode::OK);
assert_eq!(body[0]["Id"], 193113);
assert_eq!(body[0]["CoilNo"], "193113");
```

This protects the QML distinction between 卷号 and 流水号 pages.

**Step 4: Add `HasCoil` exclusion test**

Add `search_coil_no_excludes_secondary_only_rows_like_python`:

```rust
let (status, body) = request_json(app_with_search_rows(), "GET", "/search/coilNo/SECONDARY").await;
assert_eq!(status, StatusCode::OK);
assert_eq!(body, json!([]));
```

**Step 5: Fix repository filtering if required**

Keep in-memory behavior equivalent to SQL:

```rust
.filter(|coil| coil.has_coil && coil.coil_no.contains(coil_no))
```

Keep MySQL behavior equivalent to Python summary search:

```sql
WHERE COALESCE(HasCoil, 0) = 1 AND CoilNo LIKE ? ORDER BY Id DESC LIMIT 200
```

**Step 6: Run focused backend tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test search_coil_no_
```

Expected: PASS.

### Task 2: Verify URL path and encoding behavior

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`
- Modify if required: `app/UI/MotionStudioWeb/src/services/api.ts`

**Step 1: Add Rust route tests for encoded text**

Add tests for:

```text
GET /search/coilNo/4V07441200
GET /search/coilNo/4V%200744%2F1200
GET /search/coilNo/%E6%B5%8B%E8%AF%95
```

Before locking expected Rust behavior, compare live Python for percent-decoded path values. FastAPI should pass the decoded string to `coil_no`.

**Step 2: Keep React path builder coverage**

Assert existing tests remain:

```ts
expect(buildSearchCoilNoPath('4V07441200')).toBe('/search/coilNo/4V07441200')
expect(buildSearchCoilNoPath('4V 0744/1200')).toBe('/search/coilNo/4V%200744%2F1200')
```

Add a non-ASCII case if Python/Rust live checks support it:

```ts
expect(buildSearchCoilNoPath('测试')).toBe('/search/coilNo/%E6%B5%8B%E8%AF%95')
```

**Step 3: Fix decoding only if required**

If Axum path extraction does not decode the same way FastAPI does for encoded slashes or non-ASCII values, add route-local decoding before calling `repository.search_coils_by_no`. Do not double-decode normal ASCII coil numbers.

**Step 4: Run focused route and UI tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test search_coil_no_encoded_path_values_match_python

cd ..\..\UI\MotionStudioWeb
npm test -- src/services/api.test.ts
```

Expected: PASS.

### Task 3: Preserve OpenAPI schema and metadata

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Keep Python metadata stable**

Ensure OpenAPI for `GET /search/coilNo/{coil_no}` keeps:

```text
summary: Search By Coil No
operationId: search_by_coil_no_search_coilNo__coil_no__get
path parameter: coil_no string, required
200 response: CoilSummaryItem[]
422 response: HTTPValidationError if generated by FastAPI-compatible parameter docs
```

**Step 2: Add/tighten OpenAPI assertions**

Add assertions:

```rust
let operation = &body["paths"]["/search/coilNo/{coil_no}"]["get"];
assert_eq!(operation["summary"], "Search By Coil No");
assert_eq!(operation["operationId"], "search_by_coil_no_search_coilNo__coil_no__get");
assert_eq!(operation["parameters"][0]["name"], "coil_no");
assert_eq!(operation["parameters"][0]["schema"]["type"], "string");
assert_eq!(operation["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"], "#/components/schemas/CoilSummaryItem");
```

**Step 3: Run focused OpenAPI test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test openapi_json_describes_coil_search_response_contracts_for_qml_tauri_ui
```

Expected: PASS.

### Task 4: Close React/Tauri 卷号 search behavior

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/coilSearch.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/coilSearch.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api-client.test.ts`

**Step 1: Preserve page-specific routing**

Assert `resolveCoilSearch('202607030001', 'coilNo')` returns:

```ts
{ kind: 'coilNo', text: '202607030001' }
```

Assert `resolveCoilSearch('202607030001', 'coilId')` returns an id request. This protects QML behavior where 卷号 and 流水号 are separate pages.

**Step 2: Ensure no detail fallback on 卷号 search**

Add a test that the `coilNo` branch only calls:

```ts
coilApi.searchByCoilNo(request.text)
```

and does not call `coilApi.getCoilDetail`, even when the backend returns `[]`.

**Step 3: Preserve QML history ordering**

Add a multi-row test:

```ts
expect(buildQmlHistoryCoilList([{ id: 1 }, { id: 2 }, { id: 3 }])).toEqual([{ id: 3 }, { id: 2 }, { id: 1 }])
```

This matches QML `insert(0, item)` history replacement behavior.

**Step 4: Preserve normalized response aliases**

In `api-client.test.ts`, keep or add a mocked response from `searchByCoilNo` containing Python PascalCase and Rust snake/camel aliases, then assert normalized `CoilData` includes:

```ts
id
coilNo
dateTime
defectCountS
defectCountL
status
raw
```

**Step 5: Run focused UI tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/coilSearch.test.ts src/services/api.test.ts src/services/api-client.test.ts src/components/OperationSidebar/OperationSidebar.test.ts
```

Expected: PASS.

### Task 5: Add a bounded live parity checker for search-by-number

**Files:**
- Create: `app/Server/rust_api_service/tools/check_coil_search_no_parity.ps1`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Create a read-only checker**

Create a PowerShell script that accepts:

```powershell
param(
  [string]$PythonBase = 'http://127.0.0.1:5010',
  [string]$RustBase = 'http://127.0.0.1:5011',
  [string]$ViteBase = 'http://127.0.0.1:3015/api',
  [string[]]$CoilNos = @('4V', '4V07441200', '193113', '4V 0744/1200', '测试')
)
```

For each value, URL-encode with `[uri]::EscapeDataString($coilNo)` and request:

```text
/search/coilNo/<encoded>
```

Compare status code, content type, raw body, parsed array length, first-row key order, first-row `Id`, `CoilNo`, `hasCoil`, `AlarmInfo`, `DefectCountS`, `DefectCountL`, `MaxDefectName`, and `NextInfo`.

**Step 2: Run checker only when services are already running and validation is authorized**

```powershell
app\Server\rust_api_service\tools\check_coil_search_no_parity.ps1 `
  -PythonBase http://127.0.0.1:5010 `
  -RustBase http://127.0.0.1:5011 `
  -ViteBase http://127.0.0.1:3015/api `
  -CoilNos 4V,4V07441200,193113,'4V 0744/1200',测试
```

Expected: zero backend diffs for Python/Rust/Vite search responses, with empty-array cases treated as valid parity when Python is also empty.

### Task 6: Update ledger status based on evidence

**Files:**
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Mark complete only with sufficient evidence**

After Rust tests, UI tests, and live checker pass, update `Coil search by number` from `Partial` to `Complete` only if:

```text
all tested Python/Rust/Vite `/search/coilNo` responses match
OpenAPI metadata and schema match Python
React 卷号 search routes numeric-looking text to `searchByCoilNo`
no remaining search-by-number-specific backend or UI gap exists
```

If any edge remains, keep `Partial` and document the exact gap.

### Task 7: Optional commit only when requested

**Files:**
- Stage only files changed for this plan.

**Step 1: Review changed files**

Run only when commit is requested:

```powershell
git diff -- app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/coilSearch.ts app/UI/MotionStudioWeb/src/utils/coilSearch.test.ts app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts app/UI/MotionStudioWeb/src/services/api.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/UI/MotionStudioWeb/src/services/api-client.test.ts app/Server/rust_api_service/tools/check_coil_search_no_parity.ps1 docs/rust-tauri-parity.md
```

**Step 2: Commit**

Run only when commit is requested:

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/coilSearch.ts app/UI/MotionStudioWeb/src/utils/coilSearch.test.ts app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts app/UI/MotionStudioWeb/src/services/api.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/UI/MotionStudioWeb/src/services/api-client.test.ts app/Server/rust_api_service/tools/check_coil_search_no_parity.ps1 docs/rust-tauri-parity.md

git commit -m "api: close coil-number search parity"
```
