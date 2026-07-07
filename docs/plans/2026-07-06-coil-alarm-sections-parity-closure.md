# Coil Alarm Sections Parity Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close `/coilAlarm/{coil_id}` and `/coilAlarm/get_info` parity by proving the Rust API and React/Tauri consumers match the Python/QML alarm-section contract across flat-roll, taper-shape, and loose-coil data.

**Architecture:** Use Python `app/Server/api/ApiDataBase.py::_load_coil_alarm_payload` as the behavioral source: `FlatRoll` always has `S` and `L` object slots, `TaperShape` and `LooseCoil` always have `S` and `L` arrays, flat-roll selects the latest row per surface from descending `Id`, taper/loose append all rows, and loose-coil `max_width` is normalized through `CoilState.scan3dCoordinateScaleX`. Rust keeps data loading in `CoilRepository`, Python-shape JSON in `routes.rs` and `models.rs`, and React consumes the same payload through `coilApi.getCoilAlarm` in both DataShow and CurrentCoilDetailModal without route-specific UI assumptions.

**Tech Stack:** Python FastAPI/SQLAlchemy reference service, Rust Axum/SQLx/serde_json API service, React/Vite/Tauri TypeScript UI, TanStack Query, Vitest, Rust `cargo test`, read-only PowerShell live parity checker.

---

### Task 1: Lock the Python payload shape for empty and populated sections

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Reference: `app/Server/api/ApiDataBase.py:311`
- Reference: `app/Server/rust_api_service/src/routes.rs:12157`

**Step 1: Add a no-data route test**

Add or tighten a test named `coil_alarm_returns_python_empty_section_shape`:

```rust
let (status, body) = request_json(app_with_seed_data(), "GET", "/coilAlarm/999999").await;
assert_eq!(status, StatusCode::OK);
assert_eq!(body, json!({
    "FlatRoll": {"S": {}, "L": {}},
    "TaperShape": {"S": [], "L": []},
    "LooseCoil": {"S": [], "L": []},
}));
```

This catches Rust regressions where `FlatRoll` is returned as `{}` or where S/L keys are omitted.

**Step 2: Run the focused test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test coil_alarm_returns_python_empty_section_shape
```

Expected before fixes: FAIL if Rust omits `FlatRoll.S` or `FlatRoll.L`; PASS if existing implementation already matches Python.

**Step 3: Implement the minimal Rust correction if required**

In `app/Server/rust_api_service/src/routes.rs`, initialize `flat_roll_info` with both surfaces before inserting rows:

```rust
let mut flat_roll_info = Map::from_iter([
    ("S".to_string(), json!({})),
    ("L".to_string(), json!({})),
]);
```

When inserting rows, only accept `S` and `L` and preserve Python's first-descending-row behavior.

**Step 4: Re-run the focused test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test coil_alarm_returns_python_empty_section_shape
```

Expected: PASS.

### Task 2: Prove flat-roll latest-row selection and object order

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/repository.rs`
- Modify if required: `app/Server/rust_api_service/src/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/models.rs`

**Step 1: Add a fixture with multiple flat-roll rows per surface**

Create test data with two `AlarmFlatRollRow` values for surface `S` and one for `L`, where the highest `Id` has a distinctive `inner_circle_width` and `level`.

**Step 2: Add the regression test**

Add `coil_alarm_uses_latest_flat_roll_per_surface_like_python`:

```rust
let (status, body) = request_json(app_with_alarm_rows(), "GET", "/coilAlarm/42").await;
assert_eq!(status, StatusCode::OK);
assert_eq!(body["FlatRoll"]["S"]["Id"], 1002);
assert_eq!(body["FlatRoll"]["S"]["inner_circle_width"], 681.5);
assert_eq!(body["FlatRoll"]["L"]["Id"], 1003);
```

Also assert raw JSON contains Python `tool.to_dict` key order for a populated flat-roll row:

```rust
assert!(raw.contains(r#""FlatRoll":{"S":{"secondaryCoilId":42,"#));
```

**Step 3: Fix query or iteration order if required**

Python does:

```python
session.query(AlarmFlatRoll).filter_by(secondaryCoilId=coil_id).order_by(AlarmFlatRoll.Id.desc()).all()
```

and keeps only the first row per surface. Rust should either query `ORDER BY Id DESC` and insert only when the surface slot is still `{}`, or query ascending and reverse before insert with the same first-row effect. Do not keep arbitrary non-S/L surfaces in `FlatRoll` because Python ignores them.

**Step 4: Run focused flat-roll tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test coil_alarm_uses_latest_flat_roll_per_surface_like_python
```

Expected: PASS.

### Task 3: Prove taper-shape and loose-coil arrays match Python append semantics

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/repository.rs`
- Modify if required: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Add mixed-surface and unknown-surface fixtures**

Add `AlarmTaperShapeRow` and `AlarmLooseCoilRow` fixtures for `S`, `L`, empty surface, and `X` surface.

**Step 2: Add taper append test**

Add `coil_alarm_taper_shape_appends_only_s_l_rows_like_python`:

```rust
assert_eq!(body["TaperShape"]["S"].as_array().unwrap().len(), 2);
assert_eq!(body["TaperShape"]["L"].as_array().unwrap().len(), 1);
assert!(body["TaperShape"].get("X").is_none());
```

Python only appends rows where `surface in {"S", "L"}`.

**Step 3: Add loose append test**

Add `coil_alarm_loose_coil_appends_only_s_l_rows_like_python`:

```rust
assert_eq!(body["LooseCoil"]["S"].as_array().unwrap().len(), 2);
assert_eq!(body["LooseCoil"]["L"].as_array().unwrap().len(), 1);
assert!(body["LooseCoil"].get("X").is_none());
```

**Step 4: Fix Rust filtering if required**

In `coil_alarm`, guard taper and loose insertions:

```rust
if row.surface == "S" || row.surface == "L" {
    // append
}
```

Do not create extra surface keys for unknown surfaces.

**Step 5: Run focused tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test coil_alarm_taper_shape_appends_only_s_l_rows_like_python coil_alarm_loose_coil_appends_only_s_l_rows_like_python
```

Expected: PASS.

### Task 4: Cover loose-coil width normalization edge cases

**Files:**
- Modify: `app/Server/rust_api_service/tests/routes.rs`
- Modify if required: `app/Server/rust_api_service/src/routes.rs`

**Step 1: Add normalization fixtures**

Add loose-coil rows and CoilState scale rows for these cases:

```text
data.max_width_unit = "px" with max_width_px set
stored max_width_mm equal to pixel value, requiring scale application
raw max_width > 100 with positive scan3dCoordinateScaleX
data already stores max_width_mm in mm and should not be scaled again
missing/zero scale falls back to 1.0
```

**Step 2: Add normalization test**

Add `coil_alarm_normalizes_loose_width_like_python` and assert both top-level and embedded `data` values:

```rust
let first = &body["LooseCoil"]["S"][0];
assert_eq!(first["max_width"], 12.5);
let data_text = first["data"].as_str().unwrap();
assert!(data_text.contains(r#""max_width_raw": 250.0"#));
assert!(data_text.contains(r#""max_width_mm": 12.5"#));
assert!(data_text.contains(r#""max_width_unit": "mm""#));
assert!(data_text.contains(r#""max_width_scale_axis": "x""#));
```

**Step 3: Keep Python JSON dump spacing stable**

`python_json_dumps_object` should continue to format objects like Python `json.dumps(..., ensure_ascii=False)` with `": "` and `", "` separators. If key order differs from Python, fix insertion order in `normalize_loose_alarm_json` instead of sorting keys alphabetically.

**Step 4: Run focused normalization test**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test coil_alarm_normalizes_loose_width_like_python
```

Expected: PASS.

### Task 5: Keep OpenAPI and path-converter behavior aligned

**Files:**
- Modify: `app/Server/rust_api_service/src/routes.rs`
- Modify: `app/Server/rust_api_service/tests/routes.rs`

**Step 1: Preserve FastAPI path converter behavior**

Keep or add tests for:

```text
GET /coilAlarm/abc -> 404 {"detail":"Not Found"}
GET /coilAlarm/-1 -> 404 {"detail":"Not Found"}
GET /coilAlarm/get_info -> 200 null
```

**Step 2: Preserve typed docs for UI support**

Keep `/coilAlarm/{coil_id}` response schema as `CoilAlarmResponse` and `/coilAlarm/get_info` as JSON null.

**Step 3: Run focused docs and converter tests**

Run only when validation is authorized:

```powershell
cd app\Server\rust_api_service
cargo test coil_alarm_invalid_path_segments_return_python_404 openapi_json_describes_coil_alarm_response_contracts_for_qml_tauri_ui coil_alarm_get_info_returns_null_like_python
```

Expected: PASS.

### Task 6: Close React/Tauri alarm consumers against QML behavior

**Files:**
- Modify: `app/UI/MotionStudioWeb/src/utils/dataHeaderInfo.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/dataHeaderInfo.test.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/currentCoilDetail.ts`
- Modify: `app/UI/MotionStudioWeb/src/utils/currentCoilDetail.test.ts`
- Reference: `app/UI/MotionStudio/qml/Pages/AlarmPage/CoreAlarmInfo.qml`
- Reference: `app/UI/MotionStudio/qml/DataShow/DataHeader/DataShowItem/DataShowItemInfos.qml`
- Reference: `app/UI/MotionStudio/qml/Pages/AlarmPage/AlarmItemSimple/AlarmItemSimpleView.qml`

**Step 1: Add no-data UI tests**

For `buildDataHeaderInfoSections({ FlatRoll: { S: {}, L: {} }, TaperShape: { S: [], L: [] }, LooseCoil: { S: [], L: [] } })`, assert QML-style `--` display values and level `0` or QML-observed neutral level.

For `buildCurrentCoilAlarmSections` with the same payload, assert:

```ts
expect(section.rows).toContainEqual({ key: 'S端数据', value: '无数据' })
expect(section.rows).toContainEqual({ key: 'S端塔形', value: '无数据' })
expect(section.rows).toContainEqual({ key: 'S端最大宽度', value: '无数据' })
```

**Step 2: Add populated UI tests from the Rust/Python fixture**

Use a fixture payload with:

```ts
FlatRoll.S.inner_circle_width = 680
FlatRoll.S.accuracy_x = 1.01
TaperShape.S[0].out_taper_max_value = 76
TaperShape.L[0].in_taper_max_value = 11
LooseCoil.S[0].data = '{"max_width_mm": 26, "max_width_unit": "mm"}'
```

Assert DataShow renders:

```text
塔形报警: 外塔(mm), 内塔(mm), S/L values
扁卷信息: 内径(mm), S端中心, L端中心
```

Assert CurrentCoilDetailModal utility returns:

```text
扁卷检测, 塔形检测, 松卷检测
levels matching QML threshold rules
```

**Step 3: Fix utility behavior only if tests show QML mismatch**

Do not change the visual components unless the utility output proves mismatched labels, numeric precision, or threshold levels. Prefer small changes inside `dataHeaderInfo.ts` and `currentCoilDetail.ts` so both React screens keep one parsing contract.

**Step 4: Run focused UI tests**

Run only when validation is authorized:

```powershell
cd app\UI\MotionStudioWeb
npm test -- src/utils/dataHeaderInfo.test.ts src/utils/currentCoilDetail.test.ts src/pages/DataShow/DataShow.test.ts
```

Expected: PASS.

### Task 7: Add a bounded live parity checker for `/coilAlarm`

**Files:**
- Create: `app/Server/rust_api_service/tools/check_coil_alarm_parity.ps1`
- Modify: `docs/rust-tauri-parity.md`

**Step 1: Create a read-only checker**

Create a script with:

```powershell
param(
  [string]$PythonBase = 'http://127.0.0.1:5010',
  [string]$RustBase = 'http://127.0.0.1:5011',
  [string]$ViteBase = 'http://127.0.0.1:3015/api',
  [int[]]$CoilIds = @(1701, 1702, 1710, 1753, 1800, 14852, 193113)
)
```

For each coil id, request:

```text
/coilAlarm/<id>
```

Compare status code, content type, raw body bytes, top-level key order, S/L key presence, flat-roll selected ids, taper/loose array lengths, loose `max_width`, and embedded loose `data` string.

Also check:

```text
/coilAlarm/get_info
/coilAlarm/abc
/coilAlarm/-1
```

**Step 2: Run checker only when services are already running and validation is authorized**

```powershell
app\Server\rust_api_service\tools\check_coil_alarm_parity.ps1 `
  -PythonBase http://127.0.0.1:5010 `
  -RustBase http://127.0.0.1:5011 `
  -ViteBase http://127.0.0.1:3015/api `
  -CoilIds 1701,1702,1710,1753,1800,14852,193113
```

Expected: zero diffs for all selected live samples and route edge cases.

**Step 3: Update ledger evidence**

Only after Rust tests, UI tests, and live checker pass, update `docs/rust-tauri-parity.md` from `Partial` to `Complete` for `Coil alarm sections`. If any edge case is deliberately not matched, keep `Partial` and document the exact reason with checker output.

### Task 8: Optional commit only when requested

**Files:**
- Stage only files changed for this plan.

**Step 1: Review changed files**

Run only when commit is requested:

```powershell
git diff -- app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/models.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/dataHeaderInfo.ts app/UI/MotionStudioWeb/src/utils/dataHeaderInfo.test.ts app/UI/MotionStudioWeb/src/utils/currentCoilDetail.ts app/UI/MotionStudioWeb/src/utils/currentCoilDetail.test.ts app/UI/MotionStudioWeb/src/pages/DataShow/DataShow.test.ts app/Server/rust_api_service/tools/check_coil_alarm_parity.ps1 docs/rust-tauri-parity.md
```

**Step 2: Commit**

Run only when commit is requested:

```powershell
git add app/Server/rust_api_service/tests/routes.rs app/Server/rust_api_service/src/routes.rs app/Server/rust_api_service/src/models.rs app/Server/rust_api_service/src/repository.rs app/UI/MotionStudioWeb/src/utils/dataHeaderInfo.ts app/UI/MotionStudioWeb/src/utils/dataHeaderInfo.test.ts app/UI/MotionStudioWeb/src/utils/currentCoilDetail.ts app/UI/MotionStudioWeb/src/utils/currentCoilDetail.test.ts app/UI/MotionStudioWeb/src/pages/DataShow/DataShow.test.ts app/Server/rust_api_service/tools/check_coil_alarm_parity.ps1 docs/rust-tauri-parity.md

git commit -m "api: close coil-alarm parity"
```
