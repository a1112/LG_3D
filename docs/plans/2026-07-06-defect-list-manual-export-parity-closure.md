# Defect List Manual Export Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the remaining parity gap for defect listing, aggregate defect queries, manual defect CRUD, and defect export so Rust API and Tauri/React match the QML/FastAPI workflow for automatic defects, manual annotations, image assets, and export statistics.

**Architecture:** Treat `app/Server/api/ApiDataBase.py` as the behavior contract for route paths, FastAPI path validation, manual defect asset side effects, and export image resolution. Rust owns the compatible API in `app/Server/rust_api_service/src/routes.rs` and `repository.rs`, including repository-backed auto/manual defect lists, manual crop/XML writes, and export crop lookup. React owns operator workflow parity through `DefectShow`, `DataShow`, `defectDataMode`, `manualDefect`, native directory selection, defect class filtering, image handoff, and query invalidation after manual mutations.

**Tech Stack:** Rust, Axum, SQLx/MySQL, image crate, FastAPI reference service, React, TypeScript, Zustand, TanStack Query, Ant Design, Vitest, optional browser/Tauri QA when authorized.

---

### Task 1: Freeze Python/FastAPI route contracts for defect APIs

**Files:**
- Reference: `app/Server/api/ApiDataBase.py`
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs` only if route metadata drifts

**Step 1: Add path validation tests**

Cover FastAPI `{...:int}` path converter behavior for all integer path routes:

```rust
#[tokio::test]
async fn defect_integer_path_routes_match_fastapi_not_found_behavior() {
    let app = app_with_seed_data();

    for path in [
        "/search/defects/abc/S",
        "/search/defects/-1/S",
        "/search/getDefectAll/abc/10",
        "/search/getDefectAll/-1/10",
        "/search/defects_all/abc/S",
        "/manual_defects/abc/S",
        "/manual_defect/update/abc",
        "/manual_defect/update/-1",
        "/manual_defect/delete/abc",
        "/manual_defect/delete/-1",
    ] {
        let response = request_response(app.clone(), request_method_for(path), path).await;
        assert_eq!(response.status(), StatusCode::NOT_FOUND, "{path}");
        assert_eq!(json_body(response).await, json!({"detail":"Not Found"}));
    }
}
```

**Step 2: Add OpenAPI metadata coverage**

Assert the Rust OpenAPI paths and operation IDs continue to match FastAPI-compatible names for:

```text
/search/defects/{coil_id}/{direction}
/search/getDefectAll/{start_coil_id}/{end_coil_id}
/search/defects_all/{coil_id}/{direction}
/manual_defects/{coil_id}/{direction}
/manual_defect/add
/manual_defect/update/{defect_id}
/manual_defect/delete/{defect_id}
/export_defects
```

**Step 3: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml defect_integer_path_routes_match_fastapi_not_found_behavior
```

Expected when authorized: invalid integer paths return `404 {"detail":"Not Found"}` and route docs remain stable.

### Task 2: Close auto, aggregate, manual, and combined list parity

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Reference: `package/CoilDataBase/Coil.py` if list ordering or field derivation is unclear

**Step 1: Add `/search/defects/{coil_id}/{surface}` tests**

Assert Python-compatible field names and member order for automatic defects:

```rust
let body = request_json_body(app.clone(), "GET", "/search/defects/1701/S").await;
assert!(body.as_array().is_some());
assert_defect_keys_match_python(&body[0]);
assert_eq!(body[0]["secondaryCoilId"], json!(1701));
assert_eq!(body[0]["surface"], json!("S"));
```

Cover empty results, S/L surface matching, datetime serialization, float/int coordinate behavior, and defect class/name aliases used by QML.

**Step 2: Add `/search/getDefectAll/{start}/{end}` tests**

Assert range semantics:
- start/end order matches Python for forward and reversed inputs if Python supports both
- result ordering matches Python
- only automatic rows are returned
- row shape matches `/search/defects`

**Step 3: Add `/manual_defects/{coil_id}/{surface}` tests**

Assert manual rows include `type=manual`, preserve Python field names, and sort like Python's `Coil.get_manual_defect_dicts`.

**Step 4: Add `/search/defects_all/{coil_id}/{surface}` tests**

Assert combined rows preserve QML contract:
- automatic entries appear before manual entries
- manual entries include `type=manual`
- no duplicate id collision changes selection behavior
- empty auto plus manual-only result works
- auto-only result works

**Step 5: Implement only minimal drift fixes**

If tests fail, patch only the list serializers, repository ordering, or route handlers for these defect routes. Do not change defect dictionary, image rendering, or DataShow behavior unless the failing assertion proves a shared normalization bug.

**Step 6: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml defect_list
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml defects_all
```

Expected when authorized: automatic, aggregate, manual, and combined defect lists match Python/QML shape and ordering on seeded samples.

### Task 3: Close manual defect CRUD parity and asset side effects

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/src/repository.rs`
- Reference: `app/Server/api/ApiDataBase.py:1200-1299`

**Step 1: Add manual add test**

Use a temporary data root with a small GRAY source image, then post:

```json
{
  "secondaryCoilId": 1701,
  "surface": "S",
  "defectName": "压痕(轻微)",
  "defectX": 20,
  "defectY": 30,
  "defectW": 40,
  "defectH": 50,
  "remark": "operator mark",
  "annotator": "系统用户"
}
```

Assert response fields match Python and `defectData` contains `manualImagePath` and `manualXmlPath` after the asset sync.

**Step 2: Add manual crop/XML assertions**

Assert Rust writes files under:

```text
<surface_dir>/manual_defect/<safe defect name>/<coil>_<surface>_<id>_x<x>_y<y>_w<w>_h<h>.jpg
<surface_dir>/manual_defect/<safe defect name>/<coil>_<surface>_<id>_x<x>_y<y>_w<w>_h<h>.xml
```

Assert XML includes the same fields as Python `_write_manual_defect_xml`: `folder`, `filename`, `size`, `object/name`, and clipped `bndbox` coordinates local to the crop.

**Step 3: Add manual update test**

Update `defectName`, coordinates, and remark. Assert:
- existing row is updated
- defect class is recalculated from defect dictionary where supported
- asset crop/XML are regenerated
- missing `defect_id` returns `{"error":"缺陷不存在","success":false}`

**Step 4: Add manual delete test**

Assert successful delete returns:

```json
{"success": true, "message": "删除成功"}
```

Assert missing delete returns:

```json
{"error": "缺陷不存在", "success": false}
```

**Step 5: Keep side effects safe**

All manual CRUD asset tests must run against temp directories or in-memory repositories. Never point tests at production `Save_*` folders.

**Step 6: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml manual_defect
```

Expected when authorized: manual CRUD response bodies, data persistence, crop creation, and XML creation match Python for safe temp data.

### Task 4: Close `/export_defects` image resolution and statistics parity

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Reference: `app/Server/api/ApiDataBase.py:1412-<export function end>`

**Step 1: Add request validation tests**

Assert Python-compatible error bodies:

```json
{"error":"请指定导出文件夹路径","exported":0}
{"error":"没有可导出的缺陷数据","exported":0}
```

**Step 2: Add manual `manualImagePath` export test**

Create a manual image path in temp data, post it in a defect payload, and assert Rust copies that image before trying classifier or source fallback.

**Step 3: Add non-2D classifier lookup tests**

Cover:
- absolute `defectData` image reference
- Python-style relative image references under every configured `saveFolder`
- saved classifier crop under `Save_*/{coil}/classifier/{defectName}`
- sibling `classifier_save/classifier/{defectName}`
- normalized defect name candidates such as `压痕` for `压痕(轻微)`
- fallback crop from GRAY source image

**Step 4: Add 2D classifier and AREA fallback tests**

Cover:
- exact `_m40` classifier crop lookup for `2D*` rows
- fallback crop from AREA source image
- fixed 40 px margin behavior
- bounds clipping near image edges

**Step 5: Add numeric coercion tests**

Assert Python-style integer truncation for JSON numeric floats and Python-style export errors for float-like coordinate strings.

**Step 6: Add statistics tests**

Assert response fields and values match Python/QML expectations:

```json
{
  "exported": <count>,
  "total": <input count>,
  "categories": <category count>
}
```

If Python also returns failed item details for partial failures, mirror that exact shape.

**Step 7: Run only when validation is authorized**

```powershell
cargo test --manifest-path app/Server/rust_api_service/Cargo.toml export_defects
```

Expected when authorized: export path resolution, crop generation, error behavior, and statistics match Python for temp assets.

### Task 5: Close React defect data-mode, filtering, and image handoff parity

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/defectDataMode.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/defectDataMode.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/defectFilter.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/defectFilter.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/defectNavigation.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/defectNavigation.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/DefectShow/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/pages/DefectShow/DefectShow.test.ts`

**Step 1: Lock data mode routing**

Assert `fetchDefectsByMode` maps modes exactly:
- `auto` -> `/search/defects/{coil}/{surface}`
- `range` -> `/search/getDefectAll/{start}/{end}` from `currentCoilList`
- `all` -> `/search/defects_all/{coil}/{surface}`
- `manual` -> `/manual_defects/{coil}/{surface}`
- empty range returns empty data without calling backend

**Step 2: Lock QML filter behavior**

Assert visible-first defect dictionary rules, hidden-class inclusion toggle, per-class counts, selected class reconciliation, reset selection, and select-all behavior all remain stable for automatic and manual rows.

**Step 3: Lock selection and image handoff**

Assert selecting a defect:
- updates selected id
- focuses the image viewer on the selected defect
- builds the QML image folder URL using active host/shared-folder settings
- can hand off to DataShow through `pendingDefect`
- uses `selectedDefect?.coilId || currentCoil?.id` for image requests

**Step 4: Add row rendering source coverage**

Assert manual rows render as editable and automatic rows render as non-editable in the manual edit modal.

**Step 5: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/defectDataMode.test.ts src/utils/defectFilter.test.ts src/utils/defectNavigation.test.ts src/pages/DefectShow/DefectShow.test.ts
```

Expected when authorized: React defect list modes and image handoff stay aligned with QML behavior.

### Task 6: Close React manual CRUD and export workflow parity

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/manualDefect.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/manualDefect.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/DefectShow/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/pages/DefectShow/DefectShow.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/pages/DataShow/index.tsx`
- Modify: `app/UI/MotionStudioWeb/src/pages/DataShow/DataShow.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/nativeDialogs.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/nativeDialogs.test.ts`

**Step 1: Lock add/update payloads**

Assert React payload builders send Python-compatible fields:

```ts
expect(buildManualDefectAddPayload(...)).toEqual({
  secondaryCoilId: 1701,
  surface: 'S',
  defectName: '压痕',
  defectX: 20,
  defectY: 30,
  defectW: 40,
  defectH: 50,
  remark: 'operator mark',
  annotator: '系统用户',
})
```

Assert update payload normalizes invalid names to `未知缺陷`, coordinates to non-negative ints, and width/height to positive ints.

**Step 2: Lock editability rules**

Assert `canEditManualDefect` returns true only for backend rows with `raw.type === 'manual'` or missing type where QML treats the row as manual, and false for automatic rows.

**Step 3: Lock export payloads**

Assert `buildManualDefectExportPayload` sends:
- `defects`
- `folder_path`
- `group_by_category`
- `include_info`
- `high_quality`

Assert scopes `all`, `manual`, and `selected` include the correct rows and `defectToPythonPayload` preserves Python field names.

**Step 4: Lock native directory fallback**

Assert browser preview returns `null` when native directory APIs are unavailable and does not call `/export_defects` until an explicit folder path is present.

**Step 5: Lock query invalidation after mutations**

Assert after add/update/delete, React invalidates the affected defect queries for the active coil/surface and does not silently leave stale manual rows visible.

**Step 6: Lock DataShow manual annotation parity**

Assert DataShow `新增标注` is only active in AREA mode, rectangle selection opens the same add modal shape, and successful save calls `defectApi.addManualDefect` with the same payload builder used by DefectShow.

**Step 7: Run only when validation is authorized**

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/manualDefect.test.ts src/utils/nativeDialogs.test.ts src/pages/DefectShow/DefectShow.test.ts src/pages/DataShow/DataShow.test.ts
```

Expected when authorized: manual add/edit/delete/export workflows remain Python-compatible and safe in web preview.

### Task 7: Browser and Tauri smoke gates

**Files:**
- No source changes unless smoke checks reveal a defect.

**Step 1: Browser preview smoke, only when authorized**

```powershell
cd app\UI\MotionStudioWeb
npm run dev
```

Check:
- Defect page switches between `自动`, `当前列表`, `自动+手动`, and `手动` modes.
- Current-list range follows the left sidebar visible list.
- Class filter counts update when switching mode/surface.
- Automatic defect selection focuses the image viewer.
- Manual defect edit/delete controls are disabled for automatic rows.
- Export modal does not call backend until a folder path is selected.
- Browser preview directory selection fallback is non-fatal.

**Step 2: Tauri desktop smoke, only when authorized**

```powershell
cd app\UI\MotionStudioWeb
npm run tauri dev
```

Check:
- Native directory picker fills the export path.
- Export calls `/export_defects` only after operator confirmation.
- Defect image handoff opens folders/URLs through native opener where available.
- DataShow AREA manual rectangle annotation creates a manual defect and refreshes the affected surface list.
- No PLC, re-detection, camera, or database backup side effects are triggered by defect browsing/export setup.

**Step 3: Live API comparison, only when authorized and safe**

Compare Python `5010`, Rust `5011`, and Vite proxy `/api` for sampled routes:

```text
/search/defects/{coil}/S
/search/defects/{coil}/L
/search/getDefectAll/{start}/{end}
/search/defects_all/{coil}/S
/manual_defects/{coil}/S
/export_defects with temp folder and temp assets only
```

Do not run live manual add/update/delete or export against production folders unless a disposable dataset is configured.

### Task 8: Documentation and completion criteria

**Files:**
- Modify: `docs/rust-tauri-parity.md`
- Modify: `docs/plans/2026-07-06-defect-list-manual-export-parity-closure.md` if implementation scope changes

**Step 1: Keep the row `Partial` until evidence is broad enough**

Do not mark this row complete until current evidence proves:
- defect list, aggregate, combined, and manual GET routes match Python shape, ordering, and path validation
- manual add/update/delete responses and side effects match Python on safe temp data
- manual crop JPG and XML outputs match Python structure
- export handles manual image paths, classifier crops, relative/absolute references, GRAY/AREA fallback, 2D `_m40`, numeric coercion, and statistics
- React mode switching, filtering, selection, image handoff, DataShow add, native directory selection, and export confirmation match QML intent
- browser/Tauri smoke gates are passed or explicitly documented as pending

**Step 2: Record exact validation commands**

After authorized validation, append commands, sample coil IDs, temp asset roots, and skipped production-side-effect checks to `docs/rust-tauri-parity.md`.

**Step 3: Commit only if requested**

```powershell
git add app/Server/rust_api_service app/UI/MotionStudioWeb/src docs/rust-tauri-parity.md docs/plans/2026-07-06-defect-list-manual-export-parity-closure.md
git commit -m "api: close defect manual export parity"
```
