# Date Search Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `/search/DateTime/{start}/{end}` parity and the React/Tauri 时间 search path by proving Python, Rust, Vite proxy, and UI history behavior match QML's minute-precision date-range workflow.

**Architecture:** Treat Python `app/Server/api/ApiDataBase.py::search_by_date_time` as the source of truth: both path segments are parsed with `datetime.datetime.strptime(value, "%Y%m%d%H%M")`, malformed values bubble to FastAPI's `500 Internal Server Error`, and valid ranges call the summary search helper with `by_coil=True`. Rust should keep malformed-date compatibility in `routes.rs`, summary filtering in `CoilRepository::search_coils_by_datetime`, and Python-shaped rows through `coil_summary_to_python_json`; React should format QML date segments with local `yyyyMMddHHmm` minute precision and write results into the same history model used by coil-number/coil-id search.

**Tech Stack:** Python FastAPI/SQLAlchemy reference service, Rust Axum/SQLx/chrono/serde_json API service, React/Vite/Tauri TypeScript UI, Ant Design DatePicker as hidden selection engine, TanStack Query, Vitest, Rust `cargo test`, read-only PowerShell live parity checker.

---

### Task 1: Lock malformed-date Python compatibility

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/routes.rs`
- Reference: `app/Server/api/ApiDataBase.py:403`

**Step 1: Expand malformed path tests**

Keep `search_datetime_invalid_format_returns_python_internal_error` and add cases:

```text
/search/DateTime/2026-01-01/2026-01-02
/search/DateTime/abc/202606282359
/search/DateTime/202606270000/abc
/search/DateTime/20260627000/202606282359
/search/DateTime/20260627000000/202606282359
/search/DateTime/202613010000/202606282359
```

Expected for all malformed cases:

```rust
assert_eq!(response.status(), StatusCode::INTERNAL_SERVER_ERROR);
assert_eq!(body_text, "Internal Server Error");
```

**Step 2: Preserve route-local 500 behavior**

Do not convert malformed values to a FastAPI 422 validation body; Python declares `start` and `end` as `str` and fails inside `strptime`, so the compatibility target is `500 Internal Server Error`.

**Step 3: Run focused malformed tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test search_datetime_invalid_format_returns_python_internal_error
```

Expected: PASS.

### Task 2: Prove summary date field and `HasCoil` semantics

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/repository.rs`
- Reference: `app/Server/rust_api_service/src/models.rs`

**Step 1: Keep CreateTime-not-DetectionTime regression**

Preserve `search_datetime_filters_by_create_time_not_detection_time` because Python summary search filters `coil_summary.CreateTime`, not latest child `DetectionTime`.

**Step 2: Add `HasCoil` exclusion fixture**

Add a row with `CreateTime` inside the requested range but `has_coil = false`.

Assert:

```rust
let (status, body) = request_json(app, "GET", "/search/DateTime/202606271235/202606271236").await;
assert_eq!(status, StatusCode::OK);
assert!(body.as_array().unwrap().iter().all(|row| row["hasCoil"] == true));
```

**Step 3: Add inclusive boundary tests**

Add rows exactly at start and end minute boundaries:

```text
CreateTime = 2026-06-27 12:35:00
CreateTime = 2026-06-27 12:36:00
```

Query `/search/DateTime/202606271235/202606271236` and verify Python-observed inclusivity. The current MySQL SQL uses `CreateTime >= start AND CreateTime <= end`; if Python helper differs, adjust Rust.

**Step 4: Add reversed range test**

Query `/search/DateTime/202606282359/202606270000` and compare live Python before locking behavior. If Python returns `[]` rather than swapping, Rust must not swap. If Python helper swaps internally, Rust must match.

**Step 5: Fix repository only if required**

The Rust MySQL query should remain aligned with Python summary search:

```sql
WHERE COALESCE(HasCoil, 0) = 1
  AND CreateTime >= STR_TO_DATE(?, '%Y%m%d%H%i')
  AND CreateTime <= STR_TO_DATE(?, '%Y%m%d%H%i')
ORDER BY Id DESC
LIMIT 500
```

In-memory filtering should use parsed `create_time` and not `detection_time`.

**Step 6: Run focused backend tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test search_datetime_
```

Expected: PASS.

### Task 3: Preserve OpenAPI schema and metadata

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Keep Python metadata stable**

Ensure OpenAPI for `GET /search/DateTime/{start}/{end}` keeps:

```text
summary: Search By Date Time
operationId: search_by_date_time_search_DateTime__start___end__get
path parameters: start string, end string, required
200 response: CoilSummaryItem[]
```

Because FastAPI sees both params as strings, do not document the route as numeric date params.

**Step 2: Add/tighten OpenAPI assertions**

Assert:

```rust
let operation = &body["paths"]["/search/DateTime/{start}/{end}"]["get"];
assert_eq!(operation["summary"], "Search By Date Time");
assert_eq!(operation["operationId"], "search_by_date_time_search_DateTime__start___end__get");
assert_eq!(operation["parameters"][0]["name"], "start");
assert_eq!(operation["parameters"][0]["schema"]["type"], "string");
assert_eq!(operation["parameters"][1]["name"], "end");
assert_eq!(operation["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"], "#/components/schemas/CoilSummaryItem");
```

**Step 3: Run focused OpenAPI test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test openapi_json_describes_coil_search_response_contracts_for_qml_tauri_ui
```

Expected: PASS.

### Task 4: Close React/Tauri 时间 search behavior

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/qmlDateTime.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/qmlDateTime.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/services/api-client.test.ts`

**Step 1: Preserve QML minute formatting**

Keep/add tests:

```ts
expect(formatQmlDateTimeMinute(new Date(2026, 5, 28, 3, 4, 59))).toBe('202606280304')
```

Seconds and milliseconds must be discarded, matching QML `DateTime.dateTimeString` minute precision.

**Step 2: Preserve current-day default range**

Keep/add tests for `getQmlCurrentDayRange(now)`:

```ts
start => same local date at 00:00:00.000
end => now
```

**Step 3: Preserve incomplete range behavior**

Keep/add tests:

```ts
expect(resolveQmlDateRangeSearch(null)).toEqual({ kind: 'none' })
expect(resolveQmlDateRangeSearch([new Date(), null])).toEqual({ kind: 'none' })
```

In UI, incomplete range should show `请选择完整时间范围` and must not call the API.

**Step 4: Preserve OperationSidebar time page wiring**

Assert the time mode renders two QML-style rows:

```text
data-qml-search-date-line="start"
data-qml-search-date-line="end"
起始:
结束:
```

Assert `runBackendSearch` calls `coilApi.searchByDateTime(request.start, request.end)` and writes results through `applySearchResults`, using the same history model as other searches.

**Step 5: Preserve service path and normalization**

Keep/add tests:

```ts
expect(buildSearchDateTimePath('202606280000', '202606282359')).toBe('/search/DateTime/202606280000/202606282359')
```

In `api-client.test.ts`, mock `searchByDateTime` response rows and assert normalized `CoilData` fields match list/search rows.

**Step 6: Run focused UI tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/qmlDateTime.test.ts src/services/api.test.ts src/services/api-client.test.ts src/components/OperationSidebar/OperationSidebar.test.ts
```

Expected: PASS.

### Task 5: Add a bounded live parity checker for DateTime search

**Files:**
- Create: `app/Server/rust_api_service/tools/check_datetime_search_parity.ps1`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Create a read-only checker**

Create a PowerShell script that accepts:

```powershell
param(
  [string]$PythonBase = 'http://127.0.0.1:5010',
  [string]$RustBase = 'http://127.0.0.1:5011',
  [string]$ViteBase = 'http://127.0.0.1:3015/api',
  [string[][]]$Ranges = @(
    @('202001010000', '209912312359'),
    @('202606270000', '202606282359'),
    @('202606282359', '202606270000'),
    @('2026-06-27', '2026-06-28'),
    @('abc', '202606282359')
  )
)
```

For each range, request:

```text
/search/DateTime/<start>/<end>
```

Compare status code, content type, raw body, parsed array length when JSON, first-row key order, first-row `Id`, `CoilNo`, `CreateTime`, `DetectionTime`, `hasCoil`, `AlarmInfo`, `DefectCountS`, `DefectCountL`, `MaxDefectName`, and `NextInfo`.

**Step 2: Run checker only when services are already running and validation is authorized**

```powershell
app\Server\rust_api_service\tools\check_datetime_search_parity.ps1 `
  -PythonBase http://127.0.0.1:5010 `
  -RustBase http://127.0.0.1:5011 `
  -ViteBase http://127.0.0.1:3015/api
```

Expected: zero backend diffs for Python/Rust/Vite DateTime search responses, including Python-compatible `500 Internal Server Error` text for malformed ranges.

### Task 6: Update ledger status based on evidence

**Files:**
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Mark complete only with sufficient evidence**

After Rust tests, UI tests, and live checker pass, update `Date search` from `Partial` to `Complete` only if:

```text
all tested Python/Rust/Vite `/search/DateTime` responses match
OpenAPI metadata and schema match Python
React 时间 search formats QML minute strings and writes history results correctly
no remaining DateTime-search-specific backend or UI gap exists
```

If any edge remains, keep `Partial` and document the exact gap.

### Task 7: Optional commit only when requested

**Files:**
- Stage only files changed for this plan.

**Step 1: Review changed files**

Run only when commit is requested:

```powershell
git diff -- app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/qmlDateTime.ts app/UI/MotionStudioWeb/src/utils/qmlDateTime.test.ts app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/UI/MotionStudioWeb/src/services/api-client.test.ts app/Server/rust_api_service/tools/check_datetime_search_parity.ps1 docs/rust-tauri-parity.md
```

**Step 2: Commit**

Run only when commit is requested:

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/qmlDateTime.ts app/UI/MotionStudioWeb/src/utils/qmlDateTime.test.ts app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts app/UI/MotionStudioWeb/src/services/api.test.ts app/UI/MotionStudioWeb/src/services/api-client.test.ts app/Server/rust_api_service/tools/check_datetime_search_parity.ps1 docs/rust-tauri-parity.md

git commit -m "api: close datetime search parity"
```
