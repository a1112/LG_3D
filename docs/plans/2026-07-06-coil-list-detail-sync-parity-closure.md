# Coil List Detail Sync Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining parity gap for coil list, incremental refresh, coil detail, and summary synchronization so Rust API behavior and the Tauri/React left-list experience are functionally equivalent to the QML/FastAPI stack.

**Architecture:** Use `app/Server/api/ApiDataBase.py` as the Python behavior contract and `app/Server/rust_api_service/src/routes.rs` plus `repository.rs` as the Rust implementation surface. React should keep the QML list model semantics in `OperationSidebar`, `coilStore`, and `coilRefresh`: first load `/coilList/80`, refresh through `/flush/{firstId-3}`, merge in place, keep realtime/history models separate, and expose the current list to dependent pages. Closure requires broader sampled evidence, not just targeted happy-path implementation.

**Tech Stack:** Rust, Axum, SQLx/MySQL, FastAPI reference service, React, TypeScript, Zustand, TanStack Query, Vitest, Playwright or browser QA when authorized.

---

### Task 1: Lock the Python route contract for list, flush, detail, and summary sync

**Files:**
- Reference: `app/Server/api/ApiDataBase.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs` only if tests reveal route metadata drift

**Step 1: Add route-contract test cases**

Cover these Python route contracts in `routes.rs`:

```rust
#[tokio::test]
async fn coil_list_flush_detail_and_sync_routes_match_fastapi_contract() {
    let app = app_with_seed_data();

    let coil_list = request_response(app.clone(), "GET", "/coilList/20").await;
    assert_eq!(coil_list.status(), StatusCode::OK);

    let invalid_list = request_response(app.clone(), "GET", "/coilList/abc").await;
    assert_eq!(invalid_list.status(), StatusCode::UNPROCESSABLE_ENTITY);

    let negative_list = request_response(app.clone(), "GET", "/coilList/-1").await;
    assert_eq!(negative_list.status(), StatusCode::INTERNAL_SERVER_ERROR);

    let flush_zero = request_json_body(app.clone(), "GET", "/flush/0").await;
    assert_eq!(flush_zero, json!({}));

    let invalid_flush = request_response(app.clone(), "GET", "/flush/abc").await;
    assert_eq!(invalid_flush.status(), StatusCode::NOT_FOUND);

    let invalid_detail = request_response(app.clone(), "GET", "/detail/abc").await;
    assert_eq!(invalid_detail.status(), StatusCode::NOT_FOUND);

    let missing_detail = request_json_body(app.clone(), "GET", "/detail/999999999").await;
    assert_eq!(missing_detail, json!({ "error": "Coil not found" }));
}
```

**Step 2: Add OpenAPI metadata guard coverage**

Assert route IDs and tags remain compatible with the FastAPI docs:

```rust
assert_operation_id(&openapi, "get", "/coilList/{number}", "get_coil_coilList__number__get");
assert_operation_id(&openapi, "post", "/sync_summaries", "sync_summaries_api_sync_summaries_post");
assert_operation_id(&openapi, "post", "/sync_summaries_range", "sync_summaries_range_api_sync_summaries_range_post");
```

**Step 3: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml coil_list_flush_detail_and_sync_routes_match_fastapi_contract
```

Expected when authorized: tests pass or expose a precise route-contract drift.

### Task 2: Broaden Rust API sampled parity for `/coilList` and `/flush`

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Modify: `docs/rust-tauri-parity.md` after authorized validation

**Step 1: Add list shape and ordering tests**

Add assertions that `/coilList/{number}` returns:

```json
{
  "value": [...],
  "Count": <same length>
}
```

Verify the rows are ordered descending by `Id`, capped at 1000, exclude rows where `HasCoil` is false, and preserve Python key order through `coil_summary_to_python_json`.

**Step 2: Add TestData fallback tests**

When developer/test mode is configured with `TestData/125143`, verify the configured TestData coil can be prepended to `/coilList` even when it is not present in MySQL. Verify `/detail/{testDataOnlyId}` still returns `{"error":"Coil not found"}`.

**Step 3: Add flush merge source tests**

For `/flush/{coil_id}` assert:
- `coil_id > 0` returns `{"coilList":[...]}`.
- rows are `Id > coil_id`.
- result limit is 10.
- ordering is descending like Python's `get_coil_list_with_summary(..., rev=True)`.
- `0` returns `{}`.
- negative and non-digit paths return FastAPI-compatible `404 {"detail":"Not Found"}`.

**Step 4: Implement only the minimal drift fix**

If tests fail, constrain changes to `coil_list`, `flush_coil_list`, `list_coils`, `list_coils_after`, or the TestData fallback helper. Do not alter unrelated search, defect, or measurement routes.

**Step 5: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml coil_list
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml flush
```

Expected when authorized: route shape, validation behavior, ordering, and fallback behavior match the Python reference.

### Task 3: Broaden Rust API sampled parity for `/detail/{coil_id}`

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Reference: `package/CoilDataBase/CoilSummary.py` if field derivation questions appear

**Step 1: Build a detail parity assertion helper**

Create a helper that checks the detail root and child arrays at the exact granularity QML consumes:

```rust
fn assert_qml_detail_shape(body: &Value) {
    assert!(body.get("SecondaryCoilId").is_some());
    assert!(body.get("childrenCoil").unwrap().is_array());
    assert!(body.get("childrenAlarmInfo").unwrap().is_array());
    assert!(body.get("childrenCoilDefect").unwrap().is_array());
    assert!(body.get("defects").unwrap().is_array());
    assert!(body.get("childrenTaperShapePoint").unwrap().is_array());
    assert!(body.get("childrenAlarmTaperShape").unwrap().is_array());
    assert!(body.get("childrenAlarmLooseCoil").unwrap().is_array());
    assert!(body.get("childrenAlarmFlatRoll").unwrap().is_array());
    assert!(body.get("childrenCoilCheck").unwrap().is_array());
}
```

**Step 2: Add broad seeded samples**

Exercise at least these categories:
- a coil with S and L defects
- a coil with alarm info
- a coil with `childrenCoilCheck`
- a coil with no summary row but a `SecondaryCoil`/latest `Coil` child fallback
- a missing positive coil
- a TestData-only coil

**Step 3: Assert Python-specific serialization details**

Check:
- Python root member order for key QML fields.
- `SecondaryCoilId` presence.
- no Rust-only `DateTime` injected into detail responses.
- PyMySQL-style six-significant-digit float rendering for `CoilInside`, `CoilDia`, `Thickness`, `Width`, `Weight`, `ActWidth`.
- `childrenCoilDefect` uses ISO datetime strings and empty-string `defectData`.
- `defects` preserves the current FastAPI alias quirk for `defectTime`.
- `AlarmInfo.S/L`, `childrenAlarmInfo`, `hasAlarmInfo`, `NextCode`, and `NextInfo` match latest non-empty alarm behavior.

**Step 4: Implement only the minimal drift fix**

If differences appear, patch only the detail serializer, child loaders, or summary fallback. Do not change explicit `/search/defects` serialization unless the same source bug is proven there.

**Step 5: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml detail
```

Expected when authorized: seeded and live-compatible detail samples preserve QML-compatible shape and Python-specific quirks.

### Task 4: Close summary synchronization parity

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Reference: `package/CoilDataBase/CoilSummary.py`

**Step 1: Add `POST /sync_summaries` coverage**

Assert:
- default `limit=1000`
- `?limit=abc` returns FastAPI `422 int_parsing`
- `?limit=-1` returns Python-compatible `500 Internal Server Error`
- already-existing summaries are not counted as newly synced
- missing summaries are created from detected `Coil.SecondaryCoilId`

**Step 2: Add summary field derivation coverage**

For newly created rows, verify Rust copies or computes:
- `SecondaryCoil` fields
- latest child `Coil` status fields
- `DefectCountS` / `DefectCountL`
- highest visible max-defect fields from `DefectClasses.json`
- `AlarmInfo` S/L grades and next-process text
- `S_HasAlarm` / `L_HasAlarm`

**Step 3: Add `POST /sync_summaries_range` coverage**

Assert:
- `{}` returns `{"error":"coil_ids is required","synced":0}`
- empty `coil_ids` returns the same body
- only existing summary rows are updated
- no missing summary rows are inserted
- response message is `Updated {count} summaries`

**Step 4: Keep mutation behavior explicit**

Mark these tests as SQLite/in-memory safe. Live MySQL mutation validation must be opt-in and should never run against production without a backup or isolated database.

**Step 5: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml sync_summaries
```

Expected when authorized: summary sync route behavior and computed fields match Python for safe seeded data.

### Task 5: Close React realtime/history list parity

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/coilRefresh.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/coilRefresh.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/stores/coilStore.ts`
- Modify: `app/UI/MotionStudioWeb/src/stores/coilStore.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/components/OperationSidebar/OperationSidebar.test.ts`

**Step 1: Add helper tests for QML model semantics**

Cover:
- first refresh start id is `firstCoil.id - 3`
- empty realtime list uses `/coilList/80`
- merge updates duplicate ids in place
- merge inserts new ids at the top in backend order
- merge trims to `300`
- `keepLatest=true` selects the first row
- `keepLatest=false` preserves the selected row when refreshed
- `keepLatest=false` preserves an out-of-list selected row until the QML auto-restore timer fires
- manual row selection disables `keepLatest`
- history search selection also disables `keepLatest`

**Step 2: Add current-list publication coverage**

Assert `currentCoilList` always follows the QML-visible model:
- realtime mode publishes realtime rows
- history mode publishes history rows
- defect page consumes `currentCoilList` before fallback to realtime `coilList`

**Step 3: Add list header and footer parity tests**

Assert the left panel renders:
- `实时: count` / `历史: count`
- current coil number and serial id
- realtime/history color states
- footer API URL
- footer delay
- footer `保持最新` checkbox

**Step 4: Implement only minimal UI drift fixes**

If tests fail, patch `OperationSidebar`, `coilRefresh`, or `coilStore` only. Do not change DataShow, DefectShow, export, or image backup behavior unless the failing test proves a shared model bug.

**Step 5: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/coilRefresh.test.ts src/stores/coilStore.test.ts src/components/OperationSidebar/OperationSidebar.test.ts src/pages/DefectShow/DefectShow.test.ts
```

Expected when authorized: React list behavior remains QML-compatible across realtime refresh, history search, and dependent pages.

### Task 6: Add end-to-end browser and Tauri smoke gates

**Files:**
- Create: `app/UI/MotionStudioWeb/src/e2e/coil-list-parity.spec.ts` if the project already has browser e2e structure; otherwise document this as a manual QA checklist in the PR
- Modify: `docs/rust-tauri-parity.md` after authorized validation

**Step 1: Browser preview smoke, only when authorized**

```powershell
cd app\UI\MotionStudioWeb
npm run dev
```

Check:
- initial load calls `/coilList/80`
- list title shows `实时: <count>`
- row click selects the coil and disables `保持最新`
- refresh keeps selected row while `保持最新` is off
- `退出` from history restores realtime rows
- list data source opens the latest `/coilList/{limit}` URL, not `/flush/...`

**Step 2: Tauri desktop smoke, only when authorized**

```powershell
cd app\UI\MotionStudioWeb
npm run tauri dev
```

Check:
- left list loads against the active Rust API base
- no horizontal overflow in the left panel at desktop and 390px mobile widths
- native external opener is used for data-source URLs when available
- no PLC, camera, backup, re-detection, or summary-sync write action is triggered by passive list browsing

**Step 3: Live API comparison, only when authorized and safe**

Use a temporary output directory and compare Python `5010`, Rust `5011`, and Vite proxy `/api` for sampled coils:

```powershell
$ids = @(1701, 1702, 1710, 1800, 193113)
# Fetch /coilList/20, /flush/{id}, /detail/{id}, then compare key order and values.
```

Expected when authorized: no focused value/key-order diffs for the selected samples, and any skipped mutation checks are documented.

### Task 7: Documentation and completion criteria

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/plans/2026-07-06-coil-list-detail-sync-parity-closure.md` if implementation scope changes

**Step 1: Keep the row `Partial` until evidence is broad enough**

Do not mark this row complete until all of the following have current evidence:
- `/coilList/{number}` matches Python validation, fallback, ordering, shape, count, and cap behavior.
- `/flush/{coil_id}` matches Python path validation, zero behavior, result shape, ordering, and limit.
- `/detail/{coil_id}` matches Python/QML full-object shape, child arrays, key order, float/date serialization, alarm/defect/check fields, missing behavior, and TestData exclusion.
- `POST /sync_summaries` and `POST /sync_summaries_range` match Python result bodies and mutation semantics in safe seeded data.
- React realtime/history list behavior matches QML timers, merge rules, selection rules, visible current list publication, header/footer UI, and external data-source behavior.
- Browser/Tauri smoke gates have either passed or are explicitly documented as pending.

**Step 2: Record exact validation commands**

When validation is authorized and complete, append the commands and sampled coil IDs to `docs/rust-tauri-parity.md`.

**Step 3: Commit only if requested**

```powershell
git add app/Server/rust_api_service app/UI/MotionStudioWeb/src docs/rust-tauri-parity.md docs/plans/2026-07-06-coil-list-detail-sync-parity-closure.md
git commit -m "api: close coil list detail sync parity"
```
